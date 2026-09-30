"""Structural and acoustic validation for Phase 2B voice artefacts."""

from __future__ import annotations

import hashlib
import re
import wave
from pathlib import Path
from typing import Any

from phase2_video.schema import SCRIPT_SCHEMA_VERSION, parse_utc
from phase2_video.validator import validate_package, validate_script

from .package import load_voice_rules, narration_segments
from .render import inspect_wav
from .schema import (
    AUDIO_MANIFEST_KEYS,
    AUDIO_MANIFEST_SCHEMA_VERSION,
    AUDIO_CONSTRAINT_KEYS,
    NARRATION_KEYS,
    NARRATION_SEGMENT_KEYS,
    VOICE_RENDERER_VERSION,
    VOICE_PACKAGE_KEYS,
    VOICE_PACKAGE_SCHEMA_VERSION,
    VOICE_PROFILE_KEYS,
    VOICE_VALIDATOR_VERSION,
    sha256_text,
    voice_content_hash,
    voice_package_id,
)


def _report(kind: str, errors: list[str], **details: Any) -> dict[str, Any]:
    unique = sorted(set(errors))
    return {
        "validator_version": VOICE_VALIDATOR_VERSION,
        "validation_kind": kind,
        "validation_status": "PASS" if not unique else "FAIL",
        "validation_errors": unique,
        **details,
    }


def _exact_keys(value: Any, expected: set[str], code: str, errors: list[str]) -> bool:
    if not isinstance(value, dict):
        errors.append(code)
        return False
    if set(value) != expected:
        errors.append(code)
        return False
    return True


def validate_voice_package(
    video_package: dict[str, Any],
    script: dict[str, Any],
    voice_package: dict[str, Any],
    *,
    rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = rules or load_voice_rules()
    errors: list[str] = []
    if validate_package(video_package)["validation_status"] != "PASS":
        errors.append("VIDEO_PACKAGE_INVALID")
    if validate_script(video_package, script)["validation_status"] != "PASS":
        errors.append("VIDEO_SCRIPT_INVALID")
    if not _exact_keys(voice_package, VOICE_PACKAGE_KEYS, "VOICE_PACKAGE_SCHEMA", errors):
        return _report("voice-package", errors)
    if voice_package.get("schema_version") != VOICE_PACKAGE_SCHEMA_VERSION:
        errors.append("VOICE_PACKAGE_VERSION")
    expected_links = {
        "video_package_id": video_package.get("package_id"),
        "video_content_hash": video_package.get("content_hash"),
        "script_id": script.get("script_id"),
        "script_schema_version": SCRIPT_SCHEMA_VERSION,
        "site": video_package.get("site"),
        "language": script.get("language"),
        "video_type": script.get("video_type"),
        "generated_at": video_package.get("generated_at"),
    }
    for key, expected in expected_links.items():
        if voice_package.get(key) != expected:
            errors.append("UPSTREAM_LINK_MISMATCH")
    try:
        parse_utc(voice_package.get("generated_at"))
    except (TypeError, ValueError):
        errors.append("GENERATED_AT_INVALID")

    profile = voice_package.get("voice_profile")
    if _exact_keys(profile, VOICE_PROFILE_KEYS, "VOICE_PROFILE_SCHEMA", errors):
        expected_profile = (config.get("profiles") or {}).get(str(script.get("language") or ""))
        if profile != expected_profile:
            errors.append("VOICE_PROFILE_CHANGED")
        if profile.get("engine") != "espeak-ng":
            errors.append("VOICE_ENGINE_NOT_ALLOWED")
        if profile.get("cloning") is not False:
            errors.append("VOICE_CLONING_ENABLED")
        if profile.get("network_required") is not False:
            errors.append("VOICE_NETWORK_ENABLED")
        if profile.get("deterministic_mode") is not True:
            errors.append("VOICE_NONDETERMINISTIC")

    expected_segments = narration_segments(script)
    narration = voice_package.get("narration")
    if _exact_keys(narration, NARRATION_KEYS, "NARRATION_SCHEMA", errors):
        segments = narration.get("segments")
        if not isinstance(segments, list) or not segments:
            errors.append("NARRATION_SEGMENTS")
        else:
            for segment in segments:
                _exact_keys(segment, NARRATION_SEGMENT_KEYS, "NARRATION_SEGMENT_SCHEMA", errors)
            if segments != expected_segments:
                errors.append("NARRATION_TRACE_CHANGED")
        expected_text = "\n".join(segment["text"] for segment in expected_segments)
        if narration.get("text") != expected_text:
            errors.append("NARRATION_TEXT_CHANGED")
        if narration.get("text_sha256") != sha256_text(str(narration.get("text") or "")):
            errors.append("NARRATION_HASH")

    constraints = voice_package.get("audio_constraints")
    if _exact_keys(constraints, AUDIO_CONSTRAINT_KEYS, "AUDIO_CONSTRAINT_SCHEMA", errors):
        expected_audio = config.get("audio") or {}
        if constraints.get("format") != "wav":
            errors.append("AUDIO_FORMAT")
        for key in ("channels", "sample_width_bits", "min_sample_rate_hz", "max_sample_rate_hz"):
            if constraints.get(key) != expected_audio.get(key):
                errors.append("AUDIO_CONSTRAINT_CHANGED")
        duration = (config.get("duration") or {}).get(str(script.get("video_type") or ""), {})
        if constraints.get("minimum_duration_seconds") != float(duration.get("minimum_seconds", -1)):
            errors.append("AUDIO_DURATION_CONSTRAINT")
        if constraints.get("maximum_duration_seconds") != float(duration.get("maximum_seconds", -1)):
            errors.append("AUDIO_DURATION_CONSTRAINT")

    if voice_package.get("human_review_required") is not True:
        errors.append("HUMAN_REVIEW_DISABLED")
    if voice_package.get("publication_allowed") is not False:
        errors.append("PUBLICATION_ENABLED")
    digest = voice_content_hash(voice_package)
    if voice_package.get("content_hash") != digest:
        errors.append("VOICE_CONTENT_HASH")
    try:
        expected_id = voice_package_id(
            str(voice_package.get("site") or ""),
            str(voice_package.get("language") or ""),
            digest,
        )
    except ValueError:
        expected_id = ""
        errors.append("VOICE_PACKAGE_ID")
    if voice_package.get("voice_package_id") != expected_id:
        errors.append("VOICE_PACKAGE_ID")
    return _report(
        "voice-package",
        errors,
        voice_package_id=str(voice_package.get("voice_package_id") or ""),
        content_hash=str(voice_package.get("content_hash") or ""),
        script_id=str(voice_package.get("script_id") or ""),
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_audio(
    voice_package: dict[str, Any],
    manifest: dict[str, Any],
    audio_path: Path | str,
) -> dict[str, Any]:
    errors: list[str] = []
    path = Path(audio_path)
    voice_digest = voice_content_hash(voice_package)
    try:
        expected_voice_id = voice_package_id(
            str(voice_package.get("site") or ""),
            str(voice_package.get("language") or ""),
            voice_digest,
        )
    except ValueError:
        expected_voice_id = ""
    narration = voice_package.get("narration") or {}
    if (
        voice_package.get("content_hash") != voice_digest
        or voice_package.get("voice_package_id") != expected_voice_id
        or narration.get("text_sha256") != sha256_text(str(narration.get("text") or ""))
    ):
        errors.append("VOICE_PACKAGE_INTEGRITY")
    if not _exact_keys(manifest, AUDIO_MANIFEST_KEYS, "AUDIO_MANIFEST_SCHEMA", errors):
        return _report("audio", errors)
    if manifest.get("schema_version") != AUDIO_MANIFEST_SCHEMA_VERSION:
        errors.append("AUDIO_MANIFEST_VERSION")
    if manifest.get("renderer_version") != VOICE_RENDERER_VERSION:
        errors.append("AUDIO_RENDERER_VERSION")
    if not isinstance(manifest.get("engine_version"), str) or not manifest["engine_version"].strip():
        errors.append("AUDIO_ENGINE_VERSION")
    expected = {
        "voice_package_id": voice_package.get("voice_package_id"),
        "voice_content_hash": voice_package.get("content_hash"),
        "script_id": voice_package.get("script_id"),
        "text_sha256": (voice_package.get("narration") or {}).get("text_sha256"),
        "engine": (voice_package.get("voice_profile") or {}).get("engine"),
        "voice": (voice_package.get("voice_profile") or {}).get("voice"),
        "audio_file": path.name,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            errors.append("AUDIO_MANIFEST_LINK_MISMATCH")
    if manifest.get("network_used") is not False:
        errors.append("AUDIO_NETWORK_USED")
    if manifest.get("cloning_used") is not False:
        errors.append("AUDIO_CLONING_USED")
    try:
        parse_utc(manifest.get("rendered_at"))
    except (TypeError, ValueError):
        errors.append("AUDIO_RENDERED_AT")
    if not path.is_file():
        errors.append("AUDIO_FILE_MISSING")
        return _report("audio", errors)
    if manifest.get("audio_bytes") != path.stat().st_size:
        errors.append("AUDIO_SIZE")
    if manifest.get("audio_sha256") != _file_sha256(path):
        errors.append("AUDIO_HASH")
    try:
        audio = inspect_wav(path)
    except (OSError, EOFError, wave.Error):
        errors.append("AUDIO_WAV_INVALID")
        return _report("audio", errors)
    constraints = voice_package.get("audio_constraints") or {}
    if audio["channels"] != constraints.get("channels"):
        errors.append("AUDIO_CHANNELS")
    if audio["sample_width_bits"] != constraints.get("sample_width_bits"):
        errors.append("AUDIO_SAMPLE_WIDTH")
    rate = audio["sample_rate_hz"]
    if not int(constraints.get("min_sample_rate_hz") or 0) <= rate <= int(constraints.get("max_sample_rate_hz") or 0):
        errors.append("AUDIO_SAMPLE_RATE")
    duration = audio["duration_seconds"]
    if not float(constraints.get("minimum_duration_seconds") or 0) <= duration <= float(constraints.get("maximum_duration_seconds") or 0):
        errors.append("AUDIO_DURATION")
    if not audio["non_silent"]:
        errors.append("AUDIO_SILENT")
    if manifest.get("duration_seconds") != duration:
        errors.append("AUDIO_DURATION_MANIFEST")
    for key in ("channels", "sample_width_bits", "sample_rate_hz"):
        if manifest.get(key) != audio[key]:
            errors.append("AUDIO_TECHNICAL_MANIFEST")
    return _report(
        "audio",
        errors,
        voice_package_id=str(voice_package.get("voice_package_id") or ""),
        audio_sha256=str(manifest.get("audio_sha256") or ""),
        duration_seconds=duration,
        semantic_listening_required=True,
        publication_allowed=False,
    )
