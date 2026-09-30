"""Versioned schemas and canonical identifiers for Phase 2B voice."""

from __future__ import annotations

import copy
import hashlib
import re
from typing import Any

from phase2_video.schema import canonical_json


VOICE_PACKAGE_SCHEMA_VERSION = "1.0.0"
AUDIO_MANIFEST_SCHEMA_VERSION = "1.0.0"
VOICE_VALIDATOR_VERSION = "1.0.0"
VOICE_RENDERER_VERSION = "1.0.0"
VOICE_RULE_VERSION = "VOICE_RULESET_V1"

VOICE_PACKAGE_KEYS = {
    "schema_version", "voice_package_id", "video_package_id",
    "video_content_hash", "script_id", "script_schema_version", "site",
    "language", "video_type", "generated_at", "voice_profile", "narration",
    "audio_constraints", "human_review_required", "publication_allowed",
    "content_hash",
}
VOICE_PROFILE_KEYS = {
    "engine", "voice", "speed_wpm", "pitch", "word_gap_ms", "amplitude",
    "deterministic_mode", "cloning", "network_required", "license",
}
NARRATION_KEYS = {"text", "text_sha256", "segments"}
NARRATION_SEGMENT_KEYS = {
    "segment_id", "text", "text_sha256", "fact_ids", "statement_ids",
    "source_ids",
}
AUDIO_CONSTRAINT_KEYS = {
    "format", "channels", "sample_width_bits", "min_sample_rate_hz",
    "max_sample_rate_hz", "minimum_duration_seconds",
    "maximum_duration_seconds",
}
AUDIO_MANIFEST_KEYS = {
    "schema_version", "renderer_version", "voice_package_id",
    "voice_content_hash", "script_id", "text_sha256", "engine", "voice",
    "audio_file", "audio_sha256", "audio_bytes", "duration_seconds",
    "sample_rate_hz", "channels", "sample_width_bits", "rendered_at",
    "network_used", "cloning_used",
}


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def voice_hash_basis(package: dict[str, Any]) -> dict[str, Any]:
    basis = copy.deepcopy(package)
    basis.pop("voice_package_id", None)
    basis.pop("content_hash", None)
    return basis


def voice_content_hash(package: dict[str, Any]) -> str:
    return sha256_text(canonical_json(voice_hash_basis(package)))


def voice_package_id(site: str, language: str, content_hash: str) -> str:
    if site not in {"ormuz", "gibraltar"}:
        raise ValueError("invalid-site")
    if language not in {"es", "en"}:
        raise ValueError("invalid-language")
    if not re.fullmatch(r"[0-9a-f]{64}", content_hash or ""):
        raise ValueError("invalid-content-hash")
    return f"voice-package:{site}:{language}:{content_hash}"
