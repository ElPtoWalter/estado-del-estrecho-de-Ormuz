"""Independent HTTP watchdog, runnable outside GitHub Actions. GET-only by default."""
from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from canonical_publication import ENGINE, MAX_AGE_HOURS, age_hours
from canonical_notifications import fetch_public


def check(body, *, now=None, max_age_hours=MAX_AGE_HOURS):
    doc = ET.fromstring(body)
    errors = []
    if doc.tag != "publication" or doc.get("engine") != ENGINE:
        return ["Invalid public publication contract"]
    for field, limit in (("verified_at", max_age_hours), ("brief_source_checked_at", max_age_hours),
                         ("journal_edition_at", 36)):
        age = age_hours(doc.findtext(field), now)
        if age is None or age < -0.1 or age > limit:
            errors.append(f"{field}: missing, future or older than {limit} hours")
    if not doc.findtext("assessment_id") or doc.findtext("assessment_id") != doc.findtext("brief_assessment_id"):
        errors.append("Public monitor and daily brief do not share an assessment")
    if not doc.findtext("source_commit"):
        errors.append("Missing deployed revision")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://estrechoormuz.com/publication-health.xml")
    parser.add_argument("--max-age-hours", type=float, default=MAX_AGE_HOURS)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--fixture", type=Path)
    args = parser.parse_args()
    try:
        body = args.fixture.read_bytes() if args.fixture else fetch_public(args.url)
        errors = check(body, max_age_hours=args.max_age_hours)
    except Exception as exc:
        errors = ["Publication unreachable or invalid: " + type(exc).__name__]
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "errors": errors, "ok": not errors}
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
