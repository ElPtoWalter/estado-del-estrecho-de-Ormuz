"""One V7 snapshot for live surfaces; no classification is calculated here."""
from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ENGINE = "operational-intelligence-v7"
DIMENSIONS = ("passage", "traffic", "access", "risk")
MAX_AGE_HOURS = 3


def read(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def timestamp(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (ValueError, TypeError):
        return None


def assessment_id(assessment):
    fields = {k: assessment.get(k) for k in ("state", "family", "confidence", "dimensions", "generated_at")}
    return hashlib.sha256(json.dumps(fields, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]


def material_key(assessment):
    return (assessment.get("state"), assessment.get("confidence"),
            *(assessment.get("dimensions", {}).get(k) for k in DIMENSIONS))


def canonical(root):
    root = Path(root)
    status = read(root / "status.json", {})
    separate = read(root / "operational-intelligence.json", {})
    embedded = status.get("operational_intelligence") or {}
    if not separate.get("state") or separate.get("version") != 7:
        raise ValueError("Missing canonical V7 assessment")
    if embedded and assessment_id(embedded) != assessment_id(separate):
        raise ValueError("Embedded and standalone V7 assessments disagree")
    if not timestamp(separate.get("generated_at")):
        raise ValueError("Invalid canonical verification timestamp")
    return separate


def history_rows(root):
    """Adapt preserved V7 records for the public timeline, without rewriting history."""
    rows = []
    for a in read(Path(root) / "operational-intelligence-history.json", []) or []:
        if not isinstance(a, dict) or not a.get("state"):
            continue
        rows.append({**a, "id": "v7-" + assessment_id(a), "at": a.get("generated_at"),
                     "status": "ABIERTO" if a.get("family") == "OPEN" else "CERRADO" if a.get("family") == "CLOSED" else "INCIERTO",
                     "operational_label_es": a.get("label_es"), "operational_label_en": a.get("label_en")})
    current = canonical(root)
    if not rows or material_key(rows[0]) != material_key(current):
        a = current
        rows.insert(0, {**a, "id": "v7-" + assessment_id(a), "at": a.get("generated_at"),
                        "status": "ABIERTO" if a.get("family") == "OPEN" else "CERRADO" if a.get("family") == "CLOSED" else "INCIERTO",
                        "operational_label_es": a.get("label_es"), "operational_label_en": a.get("label_en")})
    return rows


def age_hours(value, now=None):
    dt = timestamp(value)
    if dt is None:
        return None
    return ((now or datetime.now(timezone.utc)) - dt).total_seconds() / 3600


def health_xml(root, commit=""):
    """Explicit, bounded public contract: facts already visible in HTML; no internal data."""
    root = Path(root)
    a = canonical(root)
    brief = read(root / "daily-brief.json", {})
    journal = read(root / "journal-latest.json", {})
    doc = ET.Element("publication", version="1", engine=ENGINE)
    values = {"assessment_id": assessment_id(a), "source_commit": commit,
              "state": a.get("state"), "confidence": a.get("confidence"),
              "verified_at": a.get("verified_at") or a.get("generated_at"),
              "evaluated_at": a.get("generated_at"),
              "carried_forward": str(bool(a.get("carried_forward"))).lower(),
              "last_confirmed_transit_at": a.get("latest_confirmed_transit_at"),
              "brief_source_checked_at": brief.get("source_checked_at"),
              "brief_assessment_id": brief.get("assessment_id"),
              "journal_edition_at": journal.get("generated_at"),
              "journal_source_checked_at": journal.get("source_checked_at") or (journal.get("fingerprint") or {}).get("generated_at"),
              "max_age_hours": MAX_AGE_HOURS}
    for key, value in values.items():
        ET.SubElement(doc, key).text = str(value or "")
    for key in DIMENSIONS:
        ET.SubElement(doc, key).text = str(a.get("dimensions", {}).get(key) or "")
    return ET.tostring(doc, encoding="unicode", xml_declaration=True) + "\n"


def validate(root, *, require_fresh=False, now=None):
    a = canonical(root)
    brief = read(Path(root) / "daily-brief.json", {})
    errors = []
    if brief.get("assessment_id") != assessment_id(a):
        errors.append("Daily brief does not match the canonical assessment")
    if brief.get("source_checked_at") != (a.get("verified_at") or a.get("generated_at")):
        errors.append("Daily brief source timestamp differs from V7")
    age = age_hours(a.get("verified_at") or a.get("generated_at"), now)
    if age is None or age < -0.1:
        errors.append("Missing or future canonical verification time")
    elif require_fresh and age > MAX_AGE_HOURS:
        errors.append(f"Canonical assessment is {age:.2f} hours old; limit {MAX_AGE_HOURS}")
    return errors


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--require-fresh", action="store_true")
    args = parser.parse_args()
    errors = validate(args.root, require_fresh=args.require_fresh)
    for error in errors:
        print("ERROR:", error)
    raise SystemExit(bool(errors))
