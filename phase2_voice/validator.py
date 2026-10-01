"""Technical validation is not a transcript or artistic approval."""

from __future__ import annotations

import hashlib

from phase2_video.schema import parse_utc
from .audio import inspect_audio
from .input import validate_voice_input
from .schema import VALIDATOR_VERSION, VoiceError, digest

IDENTITY_KEYS = ("voice_job_id", "package_id", "package_content_hash", "script_id", "script_content_hash", "language", "video_type", "target_seconds", "voice_config_hash", "pronunciation_version", "pronunciation_hash")
METADATA_KEYS = {*IDENTITY_KEYS, "schema_version", "provider", "model", "voice", "profile_id", "locale", "input_hash", "audio_sha256", "generated_at", "audio_filename", "audio_metrics", "segment_map", "alignment", "human_review_required", "human_review_status", "transcript_validation", "billing", "generation_trace"}


def segment_map(value: dict, duration: float) -> list[dict]:
    weights = [max(1, len(segment["text_for_tts"].split())) for segment in value["segments"]]
    start, total = 0, sum(weights)
    rows = []
    for segment, weight in zip(value["segments"], weights):
        end = start + weight
        rows.append({"segment_id": segment["segment_id"], "scene_id": segment["scene_id"], "estimated_start_seconds": round(duration * start / total, 6), "estimated_end_seconds": round(duration * end / total, 6), **{key: segment[key] for key in ("fact_ids", "statement_ids", "source_ids")}})
        start = end
    return rows


def validate_audio(package: dict, script: dict, value: dict, data: bytes, metadata: dict, *, pronunciation: dict | None = None) -> dict:
    errors = []
    valid_input = False
    try:
        validate_voice_input(package, script, value, pronunciation=pronunciation)
        valid_input = True
    except VoiceError as exc:
        errors.append(exc.code)
    target = value.get("target_seconds") if isinstance(value, dict) else None
    metrics, audio_errors = inspect_audio(data, target)
    errors.extend(audio_errors)
    if not valid_input or not isinstance(metadata, dict) or set(metadata) != METADATA_KEYS:
        errors.append("METADATA_SCHEMA_MISMATCH")
    else:
        if any(metadata[key] != value.get(key) for key in IDENTITY_KEYS) or metadata["input_hash"] != digest(value):
            errors.append("METADATA_IDENTITY_MISMATCH")
        config = value.get("voice_config", {})
        if any(metadata[key] != config.get(key) for key in ("provider", "model", "voice", "profile_id", "locale")):
            errors.append("METADATA_CONFIG_MISMATCH")
        if metadata["schema_version"] != "1.0.0" or metadata["audio_filename"] != "audio-gemini.wav":
            errors.append("METADATA_SCHEMA_MISMATCH")
        if metadata["audio_sha256"] != hashlib.sha256(data).hexdigest():
            errors.append("AUDIO_HASH_MISMATCH")
        if metadata["audio_metrics"] != metrics:
            errors.append("METADATA_AUDIO_MISMATCH")
        if metadata["alignment"] != "structural-proportional-estimate-not-ASR" or metadata["segment_map"] != segment_map(value, metrics.get("duration_seconds", 0)):
            errors.append("METADATA_SEGMENTS_MISMATCH")
        if metadata["human_review_required"] is not True or metadata["human_review_status"] != "PENDING" or metadata["transcript_validation"] != "NOT_RUN":
            errors.append("HUMAN_REVIEW_BYPASS")
        if metadata["billing"] != {"enabled_by_pipeline": False, "model_free_tier_documented": True, "account_tier_verified": False, "automatic_upgrade": False}:
            errors.append("BILLING_POLICY_MISMATCH")
        if metadata["generation_trace"] != [{"provider": "gemini", "attempts": 1, "fallback_used": False}]:
            errors.append("GENERATION_TRACE_MISMATCH")
        try:
            parse_utc(metadata["generated_at"])
        except (ValueError, TypeError):
            errors.append("METADATA_TIMESTAMP_INVALID")
    return {
        "validator_version": VALIDATOR_VERSION, "voice_job_id": value.get("voice_job_id") if isinstance(value, dict) else None,
        "validation_status": "FAIL" if errors else "PASS", "validation_errors": sorted(set(errors)),
        "audio_metrics": metrics, "human_review_required": True, "human_review_status": "PENDING",
        "transcript_validation": "NOT_RUN", "pronunciation_review": "PENDING", "publication": "DISABLED",
    }
