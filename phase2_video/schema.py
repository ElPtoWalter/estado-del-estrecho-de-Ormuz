"""Versioned schemas and canonical identifiers for Phase 2A."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import date, datetime, timezone
from typing import Any


PACKAGE_SCHEMA_VERSION = "2.0.0"
SCRIPT_SCHEMA_VERSION = "1.0.0"
VALIDATOR_VERSION = "1.0.0"
RULE_VERSION = "VIDEO_RULESET_V1"

SITES = {"ormuz", "gibraltar"}
CONTENT_KINDS = {"event", "daily_summary"}
VIDEO_TYPES = {"breaking", "explainer", "daily_summary"}
VISUAL_INTENTS = {
    "presenter", "map", "chart", "timeline", "source-card",
    "status-card", "text-card",
}
ASSET_TYPES = {"map", "chart", "photo", "video", "logo"}
CONFIDENCE_VALUES = {"high", "medium", "low"}
HEALTH_VALUES = {"healthy", "degraded", "stale"}

# This is the sole Phase 1 -> Phase 2 verification adapter.  Callers must not
# invent aliases or treat non-verified Phase 1 states as audiovisual facts.
PHASE1_TO_PHASE2_VERIFICATION: dict[str, str | None] = {
    "CONFIRMED_PRIMARY": "VERIFIED_PRIMARY",
    "CONFIRMED_MULTI_SOURCE": "VERIFIED_MULTISOURCE",
    "DECLARATION_ONLY": None,
    "SINGLE_SOURCE": None,
    "UNCONFIRMED": None,
    "CONFLICTING": None,
}
VERIFIED_STATUSES = {"VERIFIED_PRIMARY", "VERIFIED_MULTISOURCE"}

PACKAGE_KEYS = {
    "schema_version", "package_id", "site", "language_set", "generated_at",
    "edition_date", "content_kind", "event_id", "importance",
    "video_recommended", "video_recommendation", "video_type", "headlines",
    "verified_facts", "statements", "sources", "operational_context",
    "what_changed", "what_we_know", "what_we_dont_know", "watch_next_24h",
    "visual_assets", "content_hash",
}
SCRIPT_KEYS = {
    "schema_version", "script_id", "package_id", "package_content_hash",
    "language", "video_type", "target_seconds", "estimated_words", "headline",
    "hook", "scenes", "outro", "generated_by",
}
SCENE_KEYS = {
    "scene_id", "voiceover", "fact_ids", "statement_ids", "source_ids",
    "visual_intent", "on_screen_text",
}


def phase2_verification(value: Any) -> str | None:
    """Map a Phase 1 verification state without weakening it."""
    key = str(value or "").strip().upper()
    if key not in PHASE1_TO_PHASE2_VERIFICATION:
        raise ValueError(f"unknown-phase1-verification:{key or 'empty'}")
    return PHASE1_TO_PHASE2_VERIFICATION[key]


def parse_utc(value: Any) -> datetime:
    """Parse an ISO-8601 UTC timestamp and reject local or naive dates."""
    text = str(value or "").strip()
    if not text:
        raise ValueError("missing-utc-timestamp")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("timestamp-not-utc")
    return parsed.astimezone(timezone.utc)


def utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("naive-datetime")
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_edition_date(value: Any) -> str:
    text = str(value or "")
    if date.fromisoformat(text).isoformat() != text:
        raise ValueError("invalid-edition-date")
    return text


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def hash_basis(package: dict[str, Any]) -> dict[str, Any]:
    """Return the v2.0.0 hash basis, excluding both derived envelope fields."""
    basis = copy.deepcopy(package)
    basis.pop("content_hash", None)
    basis.pop("package_id", None)
    return basis


def package_content_hash(package: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(hash_basis(package)).encode("utf-8")).hexdigest()


def package_id(site: str, edition_date: str, content_hash: str) -> str:
    if site not in SITES:
        raise ValueError("invalid-site")
    validate_edition_date(edition_date)
    if not re.fullmatch(r"[0-9a-f]{64}", content_hash or ""):
        raise ValueError("invalid-content-hash")
    return f"video-package:{site}:{edition_date}:{content_hash}"


def script_id(script: dict[str, Any]) -> str:
    basis = copy.deepcopy(script)
    basis.pop("script_id", None)
    digest = hashlib.sha256(canonical_json(basis).encode("utf-8")).hexdigest()
    return f"video-script:{digest}"


def normalize_confidence(value: Any) -> str:
    aliases = {
        "ALTA": "high", "HIGH": "high",
        "MEDIA": "medium", "MEDIUM": "medium",
        "BAJA": "low", "LOW": "low",
    }
    normalized = aliases.get(str(value or "").strip().upper(), str(value or "").strip().lower())
    if normalized not in CONFIDENCE_VALUES:
        raise ValueError("invalid-confidence")
    return normalized


def normalize_health(value: Any) -> str:
    aliases = {
        "HEALTHY": "healthy", "OK": "healthy", "FRESH": "healthy",
        "DEGRADED": "degraded", "WARNING": "degraded", "HISTORICAL": "degraded",
        "STALE": "stale", "ERROR": "stale", "FAILED": "stale",
    }
    normalized = aliases.get(str(value or "").strip().upper(), str(value or "").strip().lower())
    if normalized not in HEALTH_VALUES:
        raise ValueError("invalid-health")
    return normalized
