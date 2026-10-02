"""Versioned, deterministic voice configuration. No credentials in identities."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from phase2_video.schema import canonical_json

VOICE_SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "3.1.0"  # Approved regional voice; existing v1 artifacts remain valid.
VALIDATOR_VERSION = "1.0.0"
CASTILIAN_VOICE = "es-es-advisor-2"
DEFAULT_VOICES = {"es": CASTILIAN_VOICE, "en": "Charon"}
ALLOWED_MODELS = {"gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts"}
ALLOWED_VOICES = {
    "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede",
    "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba",
    "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar",
    "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
    "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat",
    CASTILIAN_VOICE,
}
PROFILES = {
    "es": {
        "profile_id": "straitwatch_es_v1", "locale": "es-ES",
        "intended_identity": "Adult masculine, neutral professional Spain Spanish news narrator; not an imitation.",
        "style": "Español de España. Locución informativa seria, natural y sobria. Autoridad moderada, tono neutral, dicción clara, ritmo controlado. Sin dramatización, sin tono publicitario ni imitación de personas.",
    },
    "en": {
        "profile_id": "straitwatch_en_v1", "locale": "en-GB",
        "intended_identity": "Adult masculine, neutral professional news narrator; not an imitation. Not auditioned.",
        "style": "Neutral British English news narration. Serious, natural, clear diction, controlled pace and moderate authority. No drama, advertising delivery or imitation of a person.",
    },
}
CASTILIAN_PROFILE = {
    "profile_id": "straitwatch_es_v2", "locale": "es-ES",
    "intended_identity": "Adult masculine neutral Spain Spanish newsroom narrator, using the approved prebuilt Castilian regional voice. Not a person imitation.",
    "style": "Locución informativa neutral, seria, sobria y natural. Dicción clara y ritmo controlado. Sin dramatización ni tono publicitario.",
}
# Retain the exact audited profile so the accepted WAV can still be validated
# without relabelling its job/hash or requiring a new synthesis request.
CASTILIAN_AUDITION_PROFILE = {
    "profile_id": "straitwatch_es_castilian_audition_v1", "locale": "es-ES",
    "intended_identity": "Adult masculine neutral Spain Spanish newsroom narrator, using a prebuilt regional catalog voice. Not a person imitation; audition pending.",
    "style": CASTILIAN_PROFILE["style"],
}
DEFAULT_RULES = Path(__file__).resolve().parent.parent / "voice-pronunciation.json"


class VoiceError(Exception):
    """Only a closed, non-sensitive code can leave the provider boundary."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def voice_config(language: str, *, model: str | None = None, voice: str | None = None, profile_id: str | None = None) -> dict:
    if language not in PROFILES:
        raise VoiceError("UNSUPPORTED_LANGUAGE")
    model = model or os.getenv("GEMINI_TTS_MODEL") or "gemini-3.8-flash-tts"
    voice = voice or os.getenv(f"GEMINI_TTS_VOICE_{language.upper()}") or DEFAULT_VOICES[language]
    if model not in ALLOWED_MODELS:
        raise VoiceError("MODEL_NOT_ALLOWED")
    if voice not in ALLOWED_VOICES:
        raise VoiceError("VOICE_NOT_ALLOWED")
    if voice == CASTILIAN_VOICE:
        if language != "es":
            raise VoiceError("VOICE_LANGUAGE_MISMATCH")
        profile = CASTILIAN_PROFILE
        if profile_id == CASTILIAN_AUDITION_PROFILE["profile_id"]:
            profile = CASTILIAN_AUDITION_PROFILE
    else:
        profile = PROFILES[language]
    if profile_id is not None and profile_id != profile["profile_id"]:
        raise VoiceError("PROFILE_NOT_ALLOWED_FOR_VOICE")
    return {
        "provider": "gemini", "model": model, "voice": voice,
        "language": language, **profile,
        "request_version": "gemini-interactions-tts-v1",
        "output_format": "wav_pcm16_native", "automatic_model_fallback": False,
        "local_fallback": "deferred-not-configured",
    }


def validate_config(config: dict, language: str) -> None:
    if not isinstance(config, dict):
        raise VoiceError("INVALID_CONFIG")
    expected = voice_config(language, model=config.get("model", "invalid"), voice=config.get("voice", "invalid"), profile_id=config.get("profile_id", "invalid"))
    if config != expected:
        raise VoiceError("INVALID_CONFIG")


def load_pronunciation(path: Path = DEFAULT_RULES) -> dict:
    try:
        rules = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise VoiceError("INVALID_PRONUNCIATION_RULES") from None
    validate_pronunciation(rules)
    return rules


def validate_pronunciation(rules: dict) -> None:
    if not isinstance(rules, dict) or set(rules) != {"schema_version", "version", "review_terms", "overrides"}:
        raise VoiceError("INVALID_PRONUNCIATION_RULES")
    if rules["schema_version"] != "1.0.0" or not isinstance(rules["version"], str) or not rules["version"]:
        raise VoiceError("INVALID_PRONUNCIATION_RULES")
    if not isinstance(rules["review_terms"], list) or not all(isinstance(term, str) and term for term in rules["review_terms"]):
        raise VoiceError("INVALID_PRONUNCIATION_RULES")
    if not isinstance(rules["overrides"], list):
        raise VoiceError("INVALID_PRONUNCIATION_RULES")
    seen = set()
    for row in rules["overrides"]:
        if not isinstance(row, dict) or set(row) != {"language", "term", "spoken", "human_reviewed", "review_note"}:
            raise VoiceError("INVALID_PRONUNCIATION_RULES")
        if row["language"] not in PROFILES or row["human_reviewed"] is not True:
            raise VoiceError("PRONUNCIATION_NOT_REVIEWED")
        if not all(isinstance(row[key], str) and row[key].strip() for key in ("term", "spoken", "review_note")):
            raise VoiceError("INVALID_PRONUNCIATION_RULES")
        # Overrides are pronunciation, never facts, numerals or provider markup.
        if any(char.isdigit() or char in "<>`:/\\" for char in row["term"] + row["spoken"]):
            raise VoiceError("UNSAFE_PRONUNCIATION_OVERRIDE")
        pair = (row["language"], row["term"].casefold())
        if pair in seen:
            raise VoiceError("DUPLICATE_PRONUNCIATION_OVERRIDE")
        seen.add(pair)
