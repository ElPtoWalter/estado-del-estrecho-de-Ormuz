#!/usr/bin/env python3
"""Genera health.json público, mínimo y sin secretos."""
from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from maintenance_common import atomic_write_json, load_json

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def xml_ok(path: Path) -> bool:
    try:
        ET.parse(path)
        return True
    except (OSError, ET.ParseError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    root = args.root.resolve()
    status = load_json(root / "status.json", {})
    if not isinstance(status, dict):
        print("ERROR: no se puede generar health.json sin status.json válido.")
        return 1
    sitemap_count = 0
    sitemap_valid = xml_ok(root / "sitemap.xml")
    if sitemap_valid:
        tree = ET.parse(root / "sitemap.xml")
        sitemap_count = len(tree.getroot().findall(f"{{{SITEMAP_NS}}}url"))
    operational = status.get("operational_intelligence")
    if not isinstance(operational, dict) or not operational.get("state"):
        operational = load_json(root / "operational-intelligence.json", {})
    if not isinstance(operational, dict):
        operational = {}
    events = load_json(root / "events.json", {})
    if not isinstance(events, dict):
        events = {}
    source_state = (
        "STALE" if status.get("stale")
        else "DEGRADED" if not status.get("verification_ok")
        else "HEALTHY"
    )
    publication_ok = sitemap_valid and xml_ok(root / "feed.xml")
    pipeline_state = "HEALTHY" if events.get("schema_version") and operational.get("version") == 7 else "DEGRADED"
    overall = "ERROR" if not isinstance(status, dict) else (
        "STALE" if source_state == "STALE"
        else "DEGRADED" if "DEGRADED" in {source_state, pipeline_state} or not publication_ok
        else "HEALTHY"
    )
    payload: dict[str, Any] = {
        "version": 2,
        "generated_at": operational.get("generated_at") or status.get("checked_at"),
        "overall": overall,
        "source_health": {
            "state": source_state,
            "checked_at": status.get("checked_at"),
            "last_success_at": status.get("last_success_at"),
            "verification_ok": status.get("verification_ok"),
            "stale": status.get("stale"),
        },
        "pipeline_health": {
            "state": pipeline_state,
            "events_schema_valid": bool(events.get("schema_version")),
            "event_count": events.get("event_count", 0),
            "verification_summary": events.get("verification_summary", {}),
            "canonical_engine": "operational-intelligence-v7",
        },
        "operational_assessment": {
            "state": operational.get("state"),
            "family": operational.get("family"),
            "label_es": operational.get("label_es"),
            "label_en": operational.get("label_en"),
            "confidence": operational.get("confidence"),
            "generated_at": operational.get("generated_at"),
            "carried_forward": bool(operational.get("carried_forward")),
        },
        "legacy_monitor": {
            "role": "internal_diagnostic",
            "status": status.get("status"),
            "operational_status": status.get("operational_status"),
            "confidence": status.get("confidence"),
            "checked_at": status.get("checked_at"),
            "last_change_at": status.get("last_change_at"),
            "verification_ok": status.get("verification_ok"),
            "stale": status.get("stale"),
            "editorial_review_required": bool(status.get("editorial_review_required")),
        },
        "publication_health": {
            "state": "HEALTHY" if publication_ok else "ERROR",
            "status_json_valid": True,
            "sitemap_valid": sitemap_valid,
            "sitemap_urls": sitemap_count,
            "feed_valid": xml_ok(root / "feed.xml"),
        },
    }
    atomic_write_json(root / "health.json", payload)
    print(f"health.json generado: overall={overall}, sitemap_valid={sitemap_valid}, URLs={sitemap_count}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
