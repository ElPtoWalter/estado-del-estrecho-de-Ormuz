"""Render a validated voice package with the local eSpeak NG executable."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

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


def render_voice_package(
    voice_package: dict[str, Any],
    output_path: Path | str,
    *,
    executable: str = "espeak-ng",
    timeout: float = 120.0,
    rendered_at: datetime | None = None,
    which: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    """Synthesize exact package text; there is no network or silent fallback."""
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
        profile.get("engine") != "espeak-ng"
        or profile.get("network_required") is not False
        or profile.get("cloning") is not False
        or profile.get("deterministic_mode") is not True
        or voice_package.get("human_review_required") is not True
        or voice_package.get("publication_allowed") is not False
    ):
        raise ValueError("unsafe-voice-package")
    resolved = which(executable)
    if not resolved:
        raise RuntimeError("voice-engine-unavailable:espeak-ng")
    output = Path(output_path).resolve()
    if output.suffix.casefold() != ".wav":
        raise ValueError("voice-output-must-be-wav")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        resolved,
        "-b", "1",
        "-v", str(profile["voice"]),
        "-s", str(int(profile["speed_wpm"])),
        "-p", str(int(profile["pitch"])),
        "-a", str(int(profile["amplitude"])),
        "-g", str(int(profile["word_gap_ms"])),
        "-w", str(output),
        "--stdin",
    ]
    result = runner(
        command,
        input=str(narration.get("text") or ""),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=timeout,
        check=False,
        shell=False,
    )
    if result.returncode != 0:
        detail = str(result.stderr or "").strip().replace("\n", " ")[:200]
        raise RuntimeError(f"voice-render-failed:{result.returncode}:{detail}")
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
        "voice": profile["voice"],
        "audio_file": output.name,
        "audio_sha256": _audio_sha256(output),
        "audio_bytes": output.stat().st_size,
        "duration_seconds": audio["duration_seconds"],
        "sample_rate_hz": audio["sample_rate_hz"],
        "channels": audio["channels"],
        "sample_width_bits": audio["sample_width_bits"],
        "rendered_at": utc_iso(timestamp),
        "network_used": False,
        "cloning_used": False,
    }
