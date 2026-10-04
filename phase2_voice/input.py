"""Convert already validated Phase 2A material, without writing into it."""

from __future__ import annotations

import copy
import re

from phase2_video.validator import validate_package, validate_script
from .schema import VOICE_SCHEMA_VERSION, VoiceError, digest, load_pronunciation, validate_config, validate_pronunciation, voice_config

UNSPOKEN = re.compile(
    r"https?://|www\.|\[[^\]]+\]\(|[<>`]|"
    r"\b(?:video-package:|video-script:|voice-job:|fact[-_:]|statement[-_:]|scene[-_:]|source[-_:]|evt[-_:])|"
    r"\b(?:GEMINI_API_KEY|API_KEY|schema_version|system prompt|developer message|"
    r"ignore previous instructions|ignora las instrucciones)\b|AIza[\w-]{20,}", re.I,
)


def validate_upstream(package: dict, script: dict) -> None:
    try:
        package_ok = validate_package(package)["validation_status"] == "PASS"
        script_ok = validate_script(package, script)["validation_status"] == "PASS"
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        raise VoiceError("INVALID_UPSTREAM_INPUT") from None
    if not package_ok or package.get("video_recommended") is not True:
        raise VoiceError("INVALID_VIDEO_PACKAGE")
    if not script_ok:
        raise VoiceError("INVALID_SCRIPT")


def speech_safe(text: str) -> None:
    if not isinstance(text, str) or not text.strip() or UNSPOKEN.search(text):
        raise VoiceError("UNSAFE_SPOKEN_TEXT")
    if any(ord(char) < 32 and char not in "\n\t" for char in text):
        raise VoiceError("UNSAFE_SPOKEN_TEXT")


def default_pronunciation(script: dict) -> dict:
    """Reviewed h-mute rule for new Spanish scripts; legacy hashes stay intact."""
    rules = load_pronunciation()
    if script.get("schema_version") != "1.1.0" or script.get("language") != "es":
        return rules
    # Explicit dictionaries and historical jobs remain authoritative. Never
    # replace a configured rule or use phonetic spelling in editorial text.
    if any(row["language"] == "es" and row["term"].casefold() == "hutíes" for row in rules["overrides"]):
        return rules
    rules["version"] = "STRAITWATCH_HUTIES_USER_RULE_20261004"
    rules["review_terms"] = sorted(set(rules["review_terms"]) | {"utíes"})
    rules["overrides"].append({
        "language": "es", "term": "hutíes", "spoken": "utíes", "human_reviewed": True,
        "review_note": "El usuario rechazó jutíes y pidió utíes, con h muda, el 04/10/2026. Regla fonética revisada por el usuario; audio candidato NO aprobado.",
    })
    return rules


def pronunciation_text(text: str, rules: dict, language: str) -> tuple[str, list[dict]]:
    """One-pass substitution; an override cannot cascade into another override."""
    rows = [row for row in rules["overrides"] if row["language"] == language]
    if not rows:
        return text, []
    lookup = {row["term"].casefold(): row for row in rows}
    pattern = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(row["term"]) for row in sorted(rows, key=lambda row: -len(row["term"]))) + r")(?!\w)", re.I)
    changes = []

    def replace(match):
        row = lookup[match.group().casefold()]
        changes.append({"original": match.group(), "spoken": row["spoken"], "start": match.start(), "end": match.end(), "review_note": row["review_note"]})
        return row["spoken"]

    return pattern.sub(replace, text), changes


def build_voice_input(package: dict, script: dict, *, config: dict | None = None, pronunciation: dict | None = None) -> dict:
    validate_upstream(package, script)
    language = script["language"]
    config = copy.deepcopy(config if config is not None else voice_config(language))
    validate_config(config, language)
    rules = copy.deepcopy(pronunciation if pronunciation is not None else default_pronunciation(script))
    validate_pronunciation(rules)
    all_refs = {key: sorted({ref for scene in script["scenes"] for ref in scene[key]}) for key in ("fact_ids", "statement_ids", "source_ids")}
    raw = [
        {"segment_id": "hook", "kind": "hook", "scene_id": None, "editorial_text": script["hook"], **all_refs},
        *[{"segment_id": f"scene-{index}", "kind": "scene", "scene_id": scene["scene_id"], "editorial_text": scene["voiceover"], **{key: scene[key] for key in all_refs}} for index, scene in enumerate(script["scenes"], 1)],
        {"segment_id": "outro", "kind": "outro", "scene_id": None, "editorial_text": script["outro"], **all_refs},
    ]
    segments, changes = [], []
    for segment in raw:
        speech_safe(segment["editorial_text"])
        tts_text, substitutions = pronunciation_text(segment["editorial_text"], rules, language)
        speech_safe(tts_text)
        segments.append({**copy.deepcopy(segment), "text_for_tts": tts_text})
        changes.extend({"segment_id": segment["segment_id"], **row} for row in substitutions)
    full_text = "\n".join(segment["text_for_tts"] for segment in segments)
    if len(full_text) > 6000:
        raise VoiceError("TEXT_LIMIT_EXCEEDED")
    value = {
        "schema_version": VOICE_SCHEMA_VERSION, "package_id": package["package_id"],
        "package_content_hash": package["content_hash"], "script_id": script["script_id"],
        "script_content_hash": digest(script), "language": language, "video_type": script["video_type"],
        "target_seconds": script["target_seconds"], "voice_config": config, "voice_config_hash": digest(config),
        "pronunciation_version": rules["version"], "pronunciation_hash": digest(rules),
        "segments": segments, "full_editorial_text": "\n".join(segment["editorial_text"] for segment in segments),
        "full_text_for_tts": full_text, "pronunciation_changes": changes,
        "pending_pronunciation_review": [term for term in rules["review_terms"] if re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", full_text, re.I)],
        "human_review_required": True,
    }
    # Opt-in only for new scripts: legacy pronunciation hashes/cache keys are
    # unchanged. Keep background citations separate from news in voice input.
    if script.get("schema_version") == "1.1.0":
        value["schema_version"] = "1.1.0"
        value["editorial_context"] = copy.deepcopy(script["editorial_context"])
        value["scene_evidence"] = [{
            "scene_id": scene["scene_id"], "evidence_kind": scene["evidence_kind"],
            "context_ids": list(scene["context_ids"]), "package_fields": list(scene["package_fields"]),
        } for scene in script["scenes"]]
        if re.search(r"\bhut[ií]es\b", full_text, re.I):
            value["pending_pronunciation_review"] = sorted(set(value["pending_pronunciation_review"]) | {"hutíes"})
    return {**value, "voice_job_id": "voice-job:" + digest(value)}


def validate_voice_input(package: dict, script: dict, value: dict, *, pronunciation: dict | None = None) -> None:
    if not isinstance(value, dict):
        raise VoiceError("INVALID_VOICE_INPUT")
    expected = build_voice_input(package, script, config=value.get("voice_config"), pronunciation=pronunciation)
    if value != expected:
        raise VoiceError("VOICE_INPUT_MISMATCH")

