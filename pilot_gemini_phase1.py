#!/usr/bin/env python3
"""Isolated, non-publishing Phase 1 pilot using the repository's real data.

The pilot builds one closed factual packet, produces a deterministic LOCAL
edition and asks Gemini to edit the same packet. Both outputs pass through the
production validator. Nothing is written to the website or journal archive.
"""
from __future__ import annotations

import argparse
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import generate_daily_journal as journal
from free_editorial_ai import editorial_quality_report, _validate_candidate
from publication_quality import apply_policy
import re


@contextmanager
def temporary_environment(values: dict[str, str | None]) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in values}
    try:
        for key, value in values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def load_news(latest: dict[str, Any]) -> list[journal.NewsItem]:
    output: list[journal.NewsItem] = []
    for raw in latest.get("news", []):
        if not isinstance(raw, dict):
            continue
        values = {
            key: raw[key]
            for key in journal.NewsItem.__dataclass_fields__
            if key in raw
        }
        try:
            output.append(journal.NewsItem(**values))
        except TypeError:
            continue
    return journal.dedupe_news(output)


def run_pilot(root: Path) -> dict[str, Any]:
    status = journal.load_json(root / "status.json", {})
    operational = journal.get_operational(status, root) if isinstance(status, dict) else {}
    event_store = journal.load_json(root / "events.json", {"events": [], "verification_summary": {}})
    latest = journal.load_json(root / "journal-latest.json", {})
    state = journal.load_json(root / "journal-state.json", {})
    if not isinstance(status, dict) or not operational:
        raise RuntimeError("Missing current monitor or canonical operational assessment")
    if not isinstance(event_store, dict) or not event_store.get("events"):
        raise RuntimeError("Missing real event store; run the monitor before the pilot")
    now = datetime.now(timezone.utc).astimezone(journal.MADRID)
    news = journal.dedupe_news(journal.evidence_as_news(status, now) + load_news(latest if isinstance(latest, dict) else {}))
    seen = set(state.get('seen_keys', []) if isinstance(state, dict) else [])
    seen.update(journal.article_key(item) for item in load_news(latest if isinstance(latest, dict) else {}))
    new_items = [item for item in news if journal.article_key(item) not in seen]
    if not news:
        raise RuntimeError("Missing real newsroom references; run the daily generator before the pilot")

    previous_fp = state.get("fingerprint", {}) if isinstance(state, dict) else {}
    current_fp = journal.state_fingerprint(status, operational, event_store)
    editorial = journal.build_editorial_context(root, news, new_items, now)

    with temporary_environment({"GEMINI_API_KEY": None, "OPENROUTER_API_KEY": None}):
        local_drafts, local_engine, local_status, local_trace = journal.editorial_drafts(
            status, operational, news, new_items, previous_fp, current_fp, now, editorial, event_store
        )

    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not gemini_key:
        raise RuntimeError("GEMINI_API_KEY is not configured for the isolated pilot")
    validation_inputs = {}
    response_capture = {}
    with temporary_environment({"OPENROUTER_API_KEY": None}):
        gemini_drafts, gemini_engine, gemini_status, gemini_trace = journal.editorial_drafts(
            status, operational, news, new_items, previous_fp, current_fp, now, editorial, event_store,
            packet_capture=validation_inputs,
            response_capture=response_capture,
        )

    local_hash = local_trace.get("factual_packet_hash") or local_trace.get("factual_packet_sha256")
    gemini_hash = gemini_trace.get("factual_packet_hash") or gemini_trace.get("factual_packet_sha256")
    revalidated = (_validate_candidate(gemini_drafts, **validation_inputs)[0] is not None
                   if validation_inputs else bool(gemini_trace.get('full_output_validated', gemini_status == 'ok')))
    quality = {lang: editorial_quality_report(gemini_drafts[lang], local_drafts[lang]) for lang in ('es', 'en')}
    checks = {
        "same_factual_packet": bool(local_hash and local_hash == gemini_hash),
        "local_rules_ok": local_engine == "rules",
        "gemini_selected": gemini_engine == "gemini" and gemini_status in {"ok", "partial-fallback"},
        "full_output_validated": revalidated,
        "validator_same_version": local_trace.get("validator_version") == gemini_trace.get("validator_version"),
        "event_ids_same": local_trace.get("event_ids") == gemini_trace.get("event_ids"),
        "source_ids_same": local_trace.get("source_ids") == gemini_trace.get("source_ids"),
        "canonical_state_preserved": current_fp.get("v7_state") == operational.get("state"),
        "bilingual_output": all(lang in gemini_drafts for lang in ("es", "en")),
    }
    return {
        "schema_version": 1,
        "site": "Estrecho Ormuz",
        "timestamp": journal.iso_z(now.astimezone(timezone.utc)),
        "published": False,
        "canonical_state": operational.get("state"),
        "factual_packet_hash": local_hash,
        "checks": checks,
        "passed": all(checks.values()),
        "editorial_quality": quality,
        "style_checks_passed": all(item['style_checks_passed'] for item in quality.values()),
        "validation_inputs": validation_inputs,
        "unaccepted_generation_for_diagnosis_only": response_capture,
        "preview_snapshot": {'status': status, 'operational': operational, 'previous': previous_fp,
                             'fingerprint': current_fp, 'news': [journal.asdict(item) for item in news],
                             'new_items': [journal.asdict(item) for item in new_items],
                             'editorial': {key: value for key, value in editorial.items() if key != 'signal'}},
        "local": {
            "engine": local_engine,
            "assistant_status": local_status,
            "fallback_used": local_trace.get("fallback_used"),
            "drafts": local_drafts,
        },
        "gemini": {
            "engine": gemini_engine,
            "assistant_status": gemini_status,
            "fallback_used": gemini_trace.get("fallback_used"),
            "attempts": gemini_trace.get("attempts", []),
            "validation_diagnostics": gemini_trace.get("validation_diagnostics", {}),
            "field_fallbacks": gemini_trace.get("field_fallbacks", []),
            "drafts": gemini_drafts,
        },
        "trace": {
            "validator_version": gemini_trace.get("validator_version"),
            "event_ids": gemini_trace.get("event_ids", []),
            "source_ids": gemini_trace.get("source_ids", []),
            "verification_summary": gemini_trace.get("verification_summary", {}),
        },
    }


def safe_failure_diagnostics(report: dict[str, Any]) -> dict[str, Any]:
    """Return actionable pilot metadata without prompts, responses or secrets."""
    checks = report.get("checks") if isinstance(report.get("checks"), dict) else {}
    gemini = report.get("gemini") if isinstance(report.get("gemini"), dict) else {}
    attempts = gemini.get("attempts") if isinstance(gemini.get("attempts"), list) else []
    safe_attempts = [
        {key: str(item[key]) for key in ("provider", "model") if key in item}
        for item in attempts
        if isinstance(item, dict)
    ]
    return {
        "failed_checks": sorted(str(key) for key, passed in checks.items() if not passed),
        "gemini_engine": str(gemini.get("engine") or ""),
        "gemini_status": str(gemini.get("assistant_status") or ""),
        "validation_diagnostics": gemini.get("validation_diagnostics")
        if isinstance(gemini.get("validation_diagnostics"), dict)
        else {},
        "attempts": safe_attempts,
    }


def write_previews(report: dict[str, Any], root: Path, output: Path) -> None:
    """Render the pilot as standalone HTML, away from the source/publication tree."""
    output = output.resolve()
    if output.is_relative_to(root.resolve()):
        raise ValueError("Pilot previews must be outside the source repository")
    output.mkdir(parents=True, exist_ok=True)
    snapshot = report.get('preview_snapshot', {})
    status = snapshot['status'] if 'status' in snapshot else journal.load_json(root / 'status.json', {})
    operational = snapshot['operational'] if 'operational' in snapshot else journal.get_operational(status, root)
    previous = snapshot['previous'] if 'previous' in snapshot else journal.load_json(root / 'journal-state.json', {}).get('fingerprint', {})
    fingerprint = snapshot['fingerprint'] if 'fingerprint' in snapshot else journal.state_fingerprint(status, operational, journal.load_json(root / 'events.json', {}))
    now = journal.parse_date(report['timestamp']).astimezone(journal.MADRID)
    news = load_news({'news': snapshot['news']} if 'news' in snapshot else journal.load_json(root / 'journal-latest.json', {}))
    context = snapshot['editorial'] if 'editorial' in snapshot else journal.build_editorial_context(root, news, [], now)
    new_items = load_news({'news': snapshot.get('new_items', [])})
    styles = '\n'.join((root / name).read_text(encoding='utf-8') for name in ('styles.css', 'v11.css', 'diario-v8.css'))
    for lang in ('es', 'en'):
        page = journal.render_page(status=status, operational=operational, news=news, new_items=new_items,
            previous_fp=previous, current_fp=fingerprint, local_dt=now, lang=lang,
            canonical=journal.BASE_URL + ('/diario.html' if lang == 'es' else '/en-diary.html'),
            archive=False, material_score_value=0, material_reasons=[], editorial=context,
            draft=report['gemini']['drafts'][lang], editor_engine=report['gemini']['engine'])
        page = apply_policy(page, 'diario/preview.html')
        page = re.sub(r'<link\b[^>]*rel="stylesheet"[^>]*>', '', page)
        page = page.replace('</head>', '<style>' + styles + '</style></head>', 1)
        page = re.sub(r'href="/(?!/)([^\"]*)"', lambda match: 'href="' + journal.BASE_URL + '/' + match.group(1) + '"', page)
        for peer in ('es', 'en'):
            published = '/diario.html' if peer == 'es' else '/en-diary.html'
            page = re.sub(r'(<a\b[^>]*\bhref=")' + re.escape(journal.BASE_URL + published) + '"',
                          lambda match: match.group(1) + 'preview-' + peer + '.html"', page)
        label = 'PRUEBA NO PUBLICADA' if lang == 'es' else 'UNPUBLISHED PREVIEW'
        page = page.replace('<main id="contenido" class="journal-main">', f'<main id="contenido" class="journal-main"><p role="note"><strong>{label}</strong> · {report["timestamp"]}</p>', 1)
        (output / f'preview-{lang}.html').write_text(page, encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--preview-dir", type=Path)
    args = parser.parse_args()
    try:
        report = run_pilot(args.root.resolve())
    except RuntimeError as exc:
        print(f"Piloto Gemini: ERROR · {exc}")
        return 1
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    if args.preview_dir:
        write_previews(report, args.root.resolve(), args.preview_dir)
    print(
        "Piloto Gemini: "
        + ("OK" if report["passed"] else "FALLO")
        + f" · packet={report['factual_packet_hash']} · publicación=no"
    )
    if not report["passed"]:
        print("Diagnóstico seguro: " + json.dumps(safe_failure_diagnostics(report), ensure_ascii=False, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
