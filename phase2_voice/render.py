"""Render a validated voice package through the ElevenLabs TTS API."""

from __future__ import annotations

import hashlib
import json
import os
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from phase2_video.schema import utc_iso

from .schema import (
    AUDIO_MANIFEST_SCHEMA_VERSION,
    VOICE_PACKAGE_SCHEMA_VERSION,
    VOICE_RENDERER_VERSION,
    sha256_text,
    voice_content_hash,
    voice_package_id,
)


def inspect_wav(path: Path | str) -> dict[str, Any]:
    audio_path = Path(path)
    with wave.open(str(audio_path), "rb") as stream:
        channels = stream.getnchannels()
        sample_width_bits = stream.getsampwidth() * 8
        sample_rate_hz = stream.getframerate()
        frame_count = stream.getnframes()
        duration_seconds = frame_count / sample_rate_hz if sample_rate_hz else 0.0
        non_silent = False
        while True:
            frames = stream.readframes(8192)
            if not frames:
                break
            if any(frames):
                non_silent = True
                break
    return {
        "channels": channels,
        "sample_width_bits": sample_width_bits,
        "sample_rate_hz": sample_rate_hz,
        "frame_count": frame_count,
        "duration_seconds": round(duration_seconds, 6),
        "non_silent": non_silent,
    }


def _audio_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"
ELEVENLABS_API_VERSION = "v1"


def _request_elevenlabs(
    url: str,
    body: bytes,
    headers: dict[str, str],
    timeout: float,
) -> tuple[int, dict[str, str], bytes]:
    request = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            response_headers = {key.casefold(): value for key, value in response.headers.items()}
            return int(response.status), response_headers, response.read()
    except HTTPError as exc:
        return int(exc.code), {}, exc.read()
    except (OSError, URLError) as exc:
        raise RuntimeError("voice-provider-unavailable:elevenlabs") from exc


def _elevenlabs_error_code(response_body: bytes) -> str:
    """Return only a provider error identifier, never its free-form message."""
    try:
        payload = json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ""
    detail = payload.get("detail") if isinstance(payload, dict) else None
    if not isinstance(detail, dict):
        return ""
    for key in ("status", "code", "type"):
        value = detail.get(key)
        if isinstance(value, str) and value:
            safe = "".join(character for character in value if character.isalnum() or character in "_-")
            return safe[:80]
    return ""


def render_voice_package(
    voice_package: dict[str, Any],
    output_path: Path | str,
    *,
    timeout: float = 120.0,
    rendered_at: datetime | None = None,
    api_key: str | None = None,
    requester: Callable[[str, bytes, dict[str, str], float], tuple[int, dict[str, str], bytes]] = _request_elevenlabs,
) -> dict[str, Any]:
    """Synthesize exact package text; credentials are never serialized."""
    profile = voice_package.get("voice_profile") or {}
    narration = voice_package.get("narration") or {}
    digest = voice_content_hash(voice_package)
    try:
        expected_id = voice_package_id(
            str(voice_package.get("site") or ""),
            str(voice_package.get("language") or ""),
            digest,
        )
    except ValueError as exc:
        raise ValueError("invalid-voice-package-identity") from exc
    if (
        voice_package.get("schema_version") != VOICE_PACKAGE_SCHEMA_VERSION
        or voice_package.get("content_hash") != digest
        or voice_package.get("voice_package_id") != expected_id
        or narration.get("text_sha256") != sha256_text(str(narration.get("text") or ""))
    ):
        raise ValueError("invalid-voice-package-integrity")
    if (
        profile.get("engine") != "elevenlabs"
        or profile.get("network_required") is not True
        or profile.get("cloning") is not False
        or profile.get("deterministic_mode") is not False
        or voice_package.get("human_review_required") is not True
        or voice_package.get("publication_allowed") is not False
    ):
        raise ValueError("unsafe-voice-package")
    output = Path(output_path).resolve()
    if output.suffix.casefold() != ".wav":
        raise ValueError("voice-output-must-be-wav")
    credential = str(api_key or os.environ.get("ELEVENLABS_API_KEY") or "").strip()
    if len(credential) < 12:
        raise RuntimeError("voice-provider-credential-missing:elevenlabs")
    voice_id = str(profile.get("voice") or "")
    output_format = str(profile.get("output_format") or "")
    if output_format != "pcm_24000" or int(profile.get("sample_rate_hz") or 0) != 24000:
        raise ValueError("unsupported-elevenlabs-output-format")

    query = urlencode({"output_format": output_format})
    url = f"{ELEVENLABS_API_BASE}/text-to-speech/{quote(voice_id, safe='')}?{query}"
    payload = {
        "text": str(narration.get("text") or ""),
        "model_id": str(profile.get("model_id") or ""),
        "voice_settings": {
            "stability": float(profile.get("stability")),
            "similarity_boost": float(profile.get("similarity_boost")),
            "style": float(profile.get("style")),
            "use_speaker_boost": bool(profile.get("use_speaker_boost")),
        },
    }
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    status, response_headers, pcm = requester(
        url,
        body,
        {
            "Accept": "audio/pcm",
            "Content-Type": "application/json",
            "xi-api-key": credential,
        },
        timeout,
    )
    if status != 200:
        error_code = _elevenlabs_error_code(pcm)
        suffix = f":{error_code}" if error_code else ""
        raise RuntimeError(f"voice-provider-http-error:elevenlabs:{status}{suffix}")
    content_type = str(response_headers.get("content-type") or "").casefold()
    if content_type and not (
        content_type.startswith("audio/") or content_type.startswith("application/octet-stream")
    ):
        raise RuntimeError("voice-provider-invalid-content-type:elevenlabs")
    encoded_magic = pcm.startswith(b"ID3") or pcm[:2] in {b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"}
    if not pcm or len(pcm) % 2 or pcm.startswith(b"RIFF") or encoded_magic:
        raise RuntimeError("voice-provider-invalid-pcm:elevenlabs")

    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(int(profile["sample_rate_hz"]))
        stream.writeframes(pcm)
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("voice-render-missing-audio")
    audio = inspect_wav(output)
    timestamp = rendered_at or datetime.now(timezone.utc).replace(microsecond=0)
    return {
        "schema_version": AUDIO_MANIFEST_SCHEMA_VERSION,
        "renderer_version": VOICE_RENDERER_VERSION,
        "voice_package_id": voice_package["voice_package_id"],
        "voice_content_hash": voice_package["content_hash"],
        "script_id": voice_package["script_id"],
        "text_sha256": voice_package["narration"]["text_sha256"],
        "engine": profile["engine"],
        "engine_version": ELEVENLABS_API_VERSION,
        "voice": profile["voice"],
        "model_id": profile["model_id"],
        "output_format": profile["output_format"],
        "audio_file": output.name,
        "audio_sha256": _audio_sha256(output),
        "audio_bytes": output.stat().st_size,
        "duration_seconds": audio["duration_seconds"],
        "sample_rate_hz": audio["sample_rate_hz"],
        "channels": audio["channels"],
        "sample_width_bits": audio["sample_width_bits"],
        "rendered_at": utc_iso(timestamp),
        "network_used": True,
        "cloning_used": False,
    }
