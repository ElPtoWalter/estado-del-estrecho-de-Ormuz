#!/usr/bin/env python3
"""Cortafuegos editorial entre el motor y la publicación pública.

Funciones:
- Corrige atribuciones RSS claramente erróneas mediante el sufijo editorial.
- Impide que un único titular hipotético, antiguo o mal atribuido cambie la
  clasificación pública a ABIERTO/CERRADO.
- Ante una transición no respaldada, restaura la clasificación anterior,
  conserva la nueva evidencia para revisión y deja un informe de diagnóstico.
- Puede restaurar desde Git los HTML/feed/history modificados por el motor para
  que una transición no validada no quede publicada indirectamente.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from typing import Any

from maintenance_common import (
    VALID_CONFIDENCE,
    VALID_OPERATIONAL,
    VALID_STATUS,
    atomic_write_json,
    evidence_key,
    iso_z,
    iter_evidence,
    load_json,
    load_publishers,
    normalize_evidence_source,
    normalized_key,
    normalized_space,
    parse_iso,
    utc_now,
)

QUESTIONABLE_RE = re.compile(
    r"(?:\?|\bwhy\b|\bcould\b|\bmay\b|\bmight\b|\bwould\b|\bcan(?:not|'t)?\b|"
    r"\bif\b.{0,35}\bclosed?\b|\bscenario\b|\bopinion\b|\banalysis\b)",
    re.I,
)
OPEN_EXPLICIT_RE = re.compile(
    r"(?:\breopen(?:ed|s|ing)?\b|\bopen(?:ed)?\s+(?:to|for)\s+(?:shipping|traffic|vessels)|"
    r"\btraffic\s+(?:is\s+)?(?:flowing|moving|transiting|resumed)|"
    r"\bships?\s+(?:are\s+)?(?:passing|crossing|transiting)|"
    r"\btransit(?:s|ing)?\s+(?:continues?|resumed|confirmed)|"
    r"\bcommercial\s+(?:shipping|traffic)\s+(?:continues?|resumed|is operating))",
    re.I,
)
CLOSED_EXPLICIT_RE = re.compile(
    r"(?:\bclosed?\s+(?:to|for)\s+(?:shipping|traffic|vessels)|"
    r"\bshipping\s+(?:has\s+)?(?:stopped|halted|ceased)|"
    r"\btraffic\s+(?:has\s+)?(?:stopped|halted|ceased)|"
    r"\bno\s+(?:ships?|vessels?|commercial traffic)\s+(?:are\s+)?(?:passing|crossing|transiting)|"
    r"\boperational\s+closure\b|\btransit\s+(?:is\s+)?suspended)",
    re.I,
)

STATEFUL_FILES = (
    "history.json",
    "feed.xml",
    "index.html",
    "en.html",
    "historial.html",
    "en-history.html",
)


def status_tuple(payload: dict[str, Any]) -> tuple[str, str]:
    return (str(payload.get("status") or ""), str(payload.get("operational_status") or ""))


def recent_enough(item: dict[str, Any], checked_at: Any, hours: int = 48) -> bool:
    checked = parse_iso(checked_at) or utc_now()
    published = parse_iso(item.get("published_at")) or parse_iso(item.get("observed_at"))
    if published is None:
        return False
    return checked - timedelta(hours=hours) <= published <= checked + timedelta(hours=2)


def direct_evidence(item: dict[str, Any], desired_status: str, checked_at: Any) -> tuple[bool, str]:
    title = normalized_space(item.get("title"))
    if not title:
        return False, "sin título"
    if QUESTIONABLE_RE.search(title):
        return False, "titular hipotético, interrogativo o analítico"
    if not recent_enough(item, checked_at):
        return False, "evidencia demasiado antigua o sin fecha fiable"
    signal = normalized_key(item.get("signal")).upper()
    if desired_status == "ABIERTO":
        if signal != "OPEN_OPERATIONAL":
            return False, "señal distinta de OPEN_OPERATIONAL"
        if not OPEN_EXPLICIT_RE.search(title):
            return False, "el texto no confirma tránsito operativo"
    elif desired_status == "CERRADO":
        if signal != "CLOSED_OPERATIONAL":
            return False, "señal distinta de CLOSED_OPERATIONAL"
        if not CLOSED_EXPLICIT_RE.search(title):
            return False, "el texto no confirma cierre operativo"
    else:
        return True, "estado conservador"
    try:
        tier = int(item.get("tier", 0))
    except (TypeError, ValueError):
        tier = 0
    if tier < 3:
        return False, "fuente por debajo del umbral de reputación"
    return True, "evidencia operativa explícita"


def support_transition(payload: dict[str, Any], desired_status: str) -> tuple[bool, list[dict[str, Any]], list[str]]:
    if desired_status == "INCIERTO":
        return True, [], ["La transición a INCIERTO es conservadora y no requiere prueba de apertura/cierre."]
    valid: list[dict[str, Any]] = []
    rejected: list[str] = []
    dedup: set[str] = set()
    for item in iter_evidence(payload):
        key = evidence_key(item)
        if not key or key in dedup:
            continue
        dedup.add(key)
        ok, reason = direct_evidence(item, desired_status, payload.get("checked_at"))
        if ok:
            valid.append(item)
        else:
            rejected.append(f"{normalized_space(item.get('source_name'))}: {reason}")

    official = [item for item in valid if bool(item.get("official")) and int(item.get("tier", 0)) >= 4]
    high_reputation_sources = {
        normalized_key(item.get("source_name"))
        for item in valid
        if int(item.get("tier", 0)) >= 4 and normalized_key(item.get("source_name"))
    }
    # Un comunicado oficial explícito o dos medios de alta reputación e independientes.
    supported = bool(official) or len(high_reputation_sources) >= 2
    if not supported:
        rejected.append(
            "Se exige una fuente oficial explícita o dos fuentes independientes de tier 4 o superior."
        )
    return supported, valid, rejected


def normalize_sources(payload: dict[str, Any], aliases_path: Path) -> list[str]:
    aliases = load_publishers(aliases_path)
    notes: list[str] = []
    for item in iter_evidence(payload):
        changed, reason = normalize_evidence_source(item, aliases)
        if changed and reason:
            notes.append(f"{normalized_space(item.get('title'))[:110]}: {reason}")
    return notes


def restore_stateful_files(root: Path) -> list[str]:
    restored: list[str] = []
    for name in STATEFUL_FILES:
        path = root / name
        try:
            check = subprocess.run(
                ["git", "cat-file", "-e", f"HEAD:{name}"],
                cwd=root,
                check=False,
                capture_output=True,
                timeout=10,
            )
            if check.returncode != 0:
                continue
            subprocess.run(
                ["git", "checkout", "HEAD", "--", name],
                cwd=root,
                check=True,
                capture_output=True,
                timeout=15,
            )
            if path.exists():
                restored.append(name)
        except (OSError, subprocess.SubprocessError):
            continue
    return restored


def write_github_output(review_required: bool, normalized_count: int) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if not output:
        return
    with open(output, "a", encoding="utf-8") as handle:
        handle.write(f"review_required={'true' if review_required else 'false'}\n")
        handle.write(f"normalized_sources={normalized_count}\n")


def safe_previous_classification(current: dict[str, Any], previous: dict[str, Any]) -> None:
    for key in ("status", "operational_status", "last_change_at"):
        if key in previous:
            current[key] = previous[key]
    previous_conf = previous.get("confidence")
    current["confidence"] = previous_conf if previous_conf in VALID_CONFIDENCE else "BAJA"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", type=Path, default=Path("status.json"))
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--review", type=Path, default=Path("editorial-review.json"))
    parser.add_argument("--aliases", type=Path, default=Path("source_aliases.json"))
    parser.add_argument("--change-file", type=Path)
    parser.add_argument("--rollback-unsafe", action="store_true", default=True)
    parser.add_argument("--fail-unsafe", action="store_true")
    parser.add_argument("--no-restore-generated", action="store_true")
    args = parser.parse_args()

    current = load_json(args.status, {})
    previous = load_json(args.previous, {})
    if not isinstance(current, dict) or not isinstance(previous, dict):
        print("ERROR: status actual o anterior no es un objeto JSON válido.")
        return 2

    for key, allowed in (
        ("status", VALID_STATUS),
        ("operational_status", VALID_OPERATIONAL),
        ("confidence", VALID_CONFIDENCE),
    ):
        if current.get(key) not in allowed:
            print(f"ERROR: {key} contiene un valor no permitido: {current.get(key)!r}")
            return 2

    notes = normalize_sources(current, args.aliases)
    changed_state = status_tuple(current) != status_tuple(previous)
    desired = str(current.get("status"))
    supported, supporting, reasons = support_transition(current, desired) if changed_state else (True, [], [])
    review_required = changed_state and not supported

    if review_required:
        candidate = {
            "status": current.get("status"),
            "operational_status": current.get("operational_status"),
            "confidence": current.get("confidence"),
            "last_change_at": current.get("last_change_at"),
        }
        previous_public = {
            "status": previous.get("status"),
            "operational_status": previous.get("operational_status"),
            "confidence": previous.get("confidence"),
            "last_change_at": previous.get("last_change_at"),
        }
        report = {
            "version": 2,
            "generated_at": iso_z(utc_now()),
            "decision": "BLOCKED_AND_ROLLED_BACK" if not args.fail_unsafe else "BLOCKED",
            "candidate": candidate,
            "preserved_public_classification": previous_public,
            "reasons": reasons[:20],
            "source_normalizations": notes[:30],
            "supporting_evidence": supporting[:6],
        }
        atomic_write_json(args.review, report)

        restored: list[str] = []
        if not args.fail_unsafe:
            if not args.no_restore_generated:
                restored = restore_stateful_files(args.status.resolve().parent)
            safe_previous_classification(current, previous)
            current["editorial_review_required"] = True
            current["candidate_classification"] = candidate
            diagnostics = current.setdefault("diagnostics", {})
            if not isinstance(diagnostics, dict):
                diagnostics = {}
                current["diagnostics"] = diagnostics
            diagnostics["editorial_guard"] = {
                "blocked": True,
                "checked_at": iso_z(utc_now()),
                "reasons": reasons[:8],
                "restored_files": restored,
            }
            atomic_write_json(args.status, current, compact=False)
            if args.change_file and args.change_file.exists():
                args.change_file.unlink(missing_ok=True)
            print("AVISO: transición no respaldada; se restauró la clasificación pública anterior.")
            for reason in reasons[:8]:
                print(f"  - {reason}")
        write_github_output(True, len(notes))
        return 1 if args.fail_unsafe else 0

    current.pop("editorial_review_required", None)
    current.pop("candidate_classification", None)
    diagnostics = current.get("diagnostics")
    if isinstance(diagnostics, dict):
        diagnostics.pop("editorial_guard", None)
    atomic_write_json(args.status, current, compact=False)
    if args.review.exists():
        args.review.unlink(missing_ok=True)
    write_github_output(False, len(notes))
    if notes:
        print(f"Fuentes normalizadas de forma conservadora: {len(notes)}")
    if changed_state:
        print(f"Transición {status_tuple(previous)} → {status_tuple(current)} respaldada editorialmente.")
    else:
        print("Sin cambio de clasificación; metadatos revisados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
