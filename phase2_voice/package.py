"""Build a closed voice package from one validated Phase 2A script."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from phase2_video.schema import SCRIPT_SCHEMA_VERSION, parse_utc, utc_iso
from phase2_video.validator import validate_package, validate_script

from .schema import (
    VOICE_PACKAGE_SCHEMA_VERSION,
    VOICE_RULE_VERSION,
    sha256_text,
    voice_content_hash,
    voice_package_id,
)


RULES_PATH = Path(__file__).resolve().parent.parent / "voice-rules.json"


def load_voice_rules(path: Path | str = RULES_PATH) -> dict[str, Any]:
    rules = json.loads(Path(path).read_text(encoding="utf-8"))
    if rules.get("rule_id") != VOICE_RULE_VERSION:
        raise ValueError("unsupported-voice-rules")
    return rules


def narration_segments(script: dict[str, Any]) -> list[dict[str, Any]]:
    """Preserve the exact spoken order and Phase 2A traceability."""
    segments: list[dict[str, Any]] = []
    hook = str(script.get("hook") or "").strip()
    if hook:
        segments.append({
            "segment_id": "hook",
            "text": hook,
            "text_sha256": sha256_text(hook),
            "fact_ids": [],
            "statement_ids": [],
            "source_ids": [],
        })
    for scene in script.get("scenes") or []:
        if not isinstance(scene, dict):
            continue
        text = str(scene.get("voiceover") or "").strip()
        if not text:
            continue
        segments.append({
            "segment_id": str(scene.get("scene_id") or ""),
            "text": text,
            "text_sha256": sha256_text(text),
            "fact_ids": list(scene.get("fact_ids") or []),
            "statement_ids": list(scene.get("statement_ids") or []),
            "source_ids": list(scene.get("source_ids") or []),
        })
    outro = str(script.get("outro") or "").strip()
    if outro:
        segments.append({
            "segment_id": "outro",
            "text": outro,
            "text_sha256": sha256_text(outro),
            "fact_ids": [],
            "statement_ids": [],
            "source_ids": [],
        })
    return segments


def build_voice_package(
    video_package: dict[str, Any],
    script: dict[str, Any],
    *,
    rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a deterministic package; invalid upstream data is never repaired."""
    config = rules or load_voice_rules()
    package_report = validate_package(video_package)
    script_report = validate_script(video_package, script)
    if package_report["validation_status"] != "PASS":
        raise ValueError("invalid-video-package:" + ",".join(package_report["validation_errors"]))
    if script_report["validation_status"] != "PASS":
        raise ValueError("invalid-video-script:" + ",".join(script_report["validation_errors"]))
    if video_package.get("video_recommended") is not True:
        raise ValueError("video-not-recommended")

    language = str(script.get("language") or "")
    profile_source = (config.get("profiles") or {}).get(language)
    if not isinstance(profile_source, dict):
        raise ValueError("unsupported-voice-language")
    profile = copy.deepcopy(profile_source)
    if (
        profile.get("engine") != "espeak-ng"
        or profile.get("cloning") is not False
        or profile.get("network_required") is not False
    ):
        raise ValueError("unsafe-voice-profile")

    segments = narration_segments(script)
    text = "\n".join(segment["text"] for segment in segments)
    if not text:
        raise ValueError("empty-narration")
    duration = (config.get("duration") or {}).get(str(script.get("video_type") or ""))
    if not isinstance(duration, dict):
        raise ValueError("unsupported-video-type")

    package: dict[str, Any] = {
        "schema_version": VOICE_PACKAGE_SCHEMA_VERSION,
        "voice_package_id": "",
        "video_package_id": str(video_package.get("package_id") or ""),
        "video_content_hash": str(video_package.get("content_hash") or ""),
        "script_id": str(script.get("script_id") or ""),
        "script_schema_version": SCRIPT_SCHEMA_VERSION,
        "site": str(video_package.get("site") or ""),
        "language": language,
        "video_type": str(script.get("video_type") or ""),
        "generated_at": utc_iso(parse_utc(video_package.get("generated_at"))),
        "voice_profile": profile,
        "narration": {
            "text": text,
            "text_sha256": sha256_text(text),
            "segments": segments,
        },
        "audio_constraints": {
            "format": "wav",
            "channels": 1,
            "sample_width_bits": 16,
            "min_sample_rate_hz": int(config["audio"]["min_sample_rate_hz"]),
            "max_sample_rate_hz": int(config["audio"]["max_sample_rate_hz"]),
            "minimum_duration_seconds": float(duration["minimum_seconds"]),
            "maximum_duration_seconds": float(duration["maximum_seconds"]),
        },
        "human_review_required": True,
        "publication_allowed": False,
        "content_hash": "",
    }
    digest = voice_content_hash(package)
    package["content_hash"] = digest
    package["voice_package_id"] = voice_package_id(package["site"], language, digest)
    return package
