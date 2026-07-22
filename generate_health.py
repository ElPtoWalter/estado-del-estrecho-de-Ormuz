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
    payload: dict[str, Any] = {
        "version": 1,
        "generated_at": status.get("checked_at"),
        "monitor": {
            "status": status.get("status"),
            "operational_status": status.get("operational_status"),
            "confidence": status.get("confidence"),
            "checked_at": status.get("checked_at"),
            "last_change_at": status.get("last_change_at"),
            "verification_ok": status.get("verification_ok"),
            "stale": status.get("stale"),
            "editorial_review_required": bool(status.get("editorial_review_required")),
        },
        "publication": {
            "status_json_valid": True,
            "sitemap_valid": sitemap_valid,
            "sitemap_urls": sitemap_count,
            "feed_valid": xml_ok(root / "feed.xml"),
        },
    }
    atomic_write_json(root / "health.json", payload)
    print(f"health.json generado: sitemap_valid={sitemap_valid}, URLs={sitemap_count}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
