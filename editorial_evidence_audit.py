"""Non-destructive evidence provenance audit. No classification or historical edits."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from canonical_publication import read, timestamp
from straitwatch_core import SourceRegistry, canonical_url, normalize_title

DIRECT = re.compile(r"\b(?:hormuz|ormuz|ukmto|jmic|qeshm)\b", re.I)
REGIONAL = re.compile(r"\b(?:gulf|golfo|iran|iranian|oman|omán)\b", re.I)
MARITIME = re.compile(r"\b(?:ship\w*|vessels?|tankers?|transit\w*|shipping|buques?|marítim\w*)\b", re.I)


def confidence_errors(assessment):
    """Minimum structural gate, not an independent verification of the source claims."""
    if assessment.get("confidence") != "ALTA":
        return []
    counts = assessment.get("source_counts") or {}
    family = assessment.get("family")
    if family == "OPEN" and (int(counts.get("passage") or 0) >= 2 or int(counts.get("primary_sources") or 0) >= 1):
        return []
    if family == "CLOSED" and int(counts.get("closure") or 0) >= 2:
        return []
    return ["High confidence lacks the engine's required source-count support; review evidence before publication"]


def evidence_record(raw, registry):
    title = str(raw.get("title") or "")
    text = title + " " + str(raw.get("description") or raw.get("details") or "")
    url = canonical_url(raw.get("source_url") or raw.get("url"))
    source = registry.resolve(raw.get("source_name") or raw.get("source"), url)
    published = raw.get("published_at")
    event_at = raw.get("event_at") or raw.get("occurred_at")
    relevance = "DIRECT" if DIRECT.search(text) else "REGIONAL_MARITIME_CONTEXT" if REGIONAL.search(text) and MARITIME.search(text) else "UNESTABLISHED"
    flags = []
    if relevance == "UNESTABLISHED":
        flags.append("RELEVANCE_REQUIRES_REVIEW")
    if not timestamp(event_at):
        flags.append("EVENT_TIME_UNKNOWN")
    if not timestamp(published):
        flags.append("PUBLICATION_TIME_UNKNOWN")
    if not url.startswith("https://"):
        flags.append("UNSAFE_OR_MISSING_URL")
    if source.source_id == "unknown":
        flags.append("SOURCE_NOT_IN_REGISTRY")
    kind = raw.get("kind") or raw.get("signal")
    measurement = all(raw.get(k) is not None for k in ("traffic_count", "traffic_average")) and bool(raw.get("measurement_period"))
    return {"id": hashlib.sha256((url + "|" + normalize_title(title)).encode()).hexdigest()[:20],
            "url": url, "title": title, "source_id": source.source_id, "source_type": "PRIMARY" if source.official else "SECONDARY_OR_UNRESOLVED",
            "published_at": published, "event_at": event_at, "event_time_inferred": False,
            "relevance": relevance, "kind": kind, "volume_measurement_documented": measurement,
            "publication_is_not_event_time": True, "flags": flags}


def audit(root):
    root = Path(root)
    registry = SourceRegistry.from_path(root / "source-registry.json")
    a = read(root / "operational-intelligence.json", {})
    records = [evidence_record(x, registry) for x in a.get("evidence", [])]
    seen = set()
    for record in records:
        if record["id"] in seen:
            record["flags"].append("DUPLICATE_REFERENCE")
        seen.add(record["id"])
    summary = a.get("source_counts") or {}
    return {"schema_version": 1, "assessment_at": a.get("generated_at"), "state_unchanged": a.get("state"),
            "scope": "Selected V7 references, not a new factual verification or a rights clearance",
            "records": records, "source_counts_claimed_by_engine": summary,
            "confidence_requires_trace_review": a.get("confidence") == "ALTA" and any(
                r["relevance"] == "UNESTABLISHED" or "SOURCE_NOT_IN_REGISTRY" in r["flags"] for r in records),
            "source_conflicts": [e for e in (read(root / "events.json", {}) or {}).get("events", [])
                                 if e.get("verification_status") == "CONFLICTING"],
            "changes": [], "human_review_recorded": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.root)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Evidence references: {len(report['records'])}; flags: {sum(len(x['flags']) for x in report['records'])}; classification unchanged")
