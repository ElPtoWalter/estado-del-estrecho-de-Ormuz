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
    news = load_news(latest if isinstance(latest, dict) else {})
    if not news:
        raise RuntimeError("Missing real newsroom references; run the daily generator before the pilot")

    now = datetime.now(timezone.utc).astimezone(journal.MADRID)
    previous_fp = state.get("fingerprint", {}) if isinstance(state, dict) else {}
    current_fp = journal.state_fingerprint(status, operational, event_store)
    editorial = journal.build_editorial_context(root, news, [], now)

    with temporary_environment({"GEMINI_API_KEY": None, "OPENROUTER_API_KEY": None}):
        local_drafts, local_engine, local_status, local_trace = journal.editorial_drafts(
            status, operational, news, [], previous_fp, current_fp, now, editorial, event_store
        )

    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not gemini_key:
        raise RuntimeError("GEMINI_API_KEY is not configured for the isolated pilot")
    with temporary_environment({"OPENROUTER_API_KEY": None}):
        gemini_drafts, gemini_engine, gemini_status, gemini_trace = journal.editorial_drafts(
            status, operational, news, [], previous_fp, current_fp, now, editorial, event_store
        )

    local_hash = local_trace.get("factual_packet_hash") or local_trace.get("factual_packet_sha256")
    gemini_hash = gemini_trace.get("factual_packet_hash") or gemini_trace.get("factual_packet_sha256")
    checks = {
        "same_factual_packet": bool(local_hash and local_hash == gemini_hash),
        "local_rules_ok": local_engine == "rules",
        "gemini_selected": gemini_engine == "gemini" and gemini_status == "ok",
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
        "attempts": safe_attempts,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path)
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
