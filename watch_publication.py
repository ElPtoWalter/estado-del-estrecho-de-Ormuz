"""Independent HTTP watchdog, runnable outside GitHub Actions. GET-only by default."""
from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from canonical_publication import ENGINE, MAX_AGE_HOURS, age_hours
from canonical_notifications import fetch_public


def diagnose(body, *, now=None, max_age_hours=MAX_AGE_HOURS):
    doc = ET.fromstring(body)
    errors = []
    warnings = []
    if doc.tag != "publication" or doc.get("engine") != ENGINE:
        return {"errors": ["Invalid public publication contract"], "warnings": []}
    for field, limit in (("verified_at", max_age_hours), ("brief_source_checked_at", max_age_hours)):
        age = age_hours(doc.findtext(field), now)
        if age is None or age < -0.1 or age > limit:
            errors.append(f"{field}: missing, future or older than {limit} hours")
    if not doc.findtext("assessment_id") or doc.findtext("assessment_id") != doc.findtext("brief_assessment_id"):
        errors.append("Public monitor and daily brief do not share an assessment")
    if not doc.findtext("source_commit"):
        errors.append("Missing deployed revision")
    # An old edition is not evidence of a failed technical job. Only an actual
    # generator heartbeat can establish when the newsroom last checked.
    edition_age = age_hours(doc.findtext("journal_edition_at"), now)
    if edition_age is not None and edition_age < -0.1:
        errors.append("Journal edition has a future timestamp")
    elif edition_age is None or edition_age > 36:
        warnings.append("No recent journal edition; editorial status only, not proof of technical failure")
    heartbeat = doc.findtext("journal_checked_at")
    newsroom_status = "unknown"
    if not heartbeat:
        warnings.append("Newsroom technical check unknown; edition date is not a heartbeat")
    else:
        age = age_hours(heartbeat, now)
        newsroom_status = "fresh"
        if age is None or age < -0.1 or age > 36:
            newsroom_status = "stale_or_invalid"
            errors.append("journal_checked_at: missing, future or older than 36 hours")
        if doc.findtext("journal_check_outcome") not in {"published", "edition_already_exists", "not_due"}:
            newsroom_status = "stale_or_invalid"
            errors.append("Unknown newsroom check outcome")
    return {"errors": errors, "warnings": warnings, "newsroom": {
        "technical_status": newsroom_status,
        "check_outcome": doc.findtext("journal_check_outcome") or None,
        "edition_age_hours": edition_age,
    }}


def check(body, *, now=None, max_age_hours=MAX_AGE_HOURS):
    return diagnose(body, now=now, max_age_hours=max_age_hours)["errors"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://estrechoormuz.com/publication-health.xml")
    parser.add_argument("--max-age-hours", type=float, default=MAX_AGE_HOURS)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--fixture", type=Path)
    args = parser.parse_args()
    try:
        body = args.fixture.read_bytes() if args.fixture else fetch_public(args.url)
        result = diagnose(body, max_age_hours=args.max_age_hours)
    except Exception as exc:
        result = {"errors": ["Publication unreachable or invalid: " + type(exc).__name__], "warnings": []}
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), **result, "ok": not result["errors"]}
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    return int(bool(result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
