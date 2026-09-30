from __future__ import annotations

import copy
import hashlib
import wave
from datetime import datetime, timezone
from pathlib import Path

from phase2_video.script import generate_local_script
from phase2_voice.package import build_voice_package
from phase2_voice.render import inspect_wav
from phase2_voice.schema import AUDIO_MANIFEST_SCHEMA_VERSION, VOICE_RENDERER_VERSION
from test_video_support import package


def voice_fixture(language: str = "es"):
    video = package()
    script = generate_local_script(video, language=language)
    voice = build_voice_package(video, script)
    return video, script, voice


def write_wav(path: Path, *, duration: float = 21.0, channels: int = 1, silent: bool = False) -> None:
    sample_rate = 22050
    frame_count = int(sample_rate * duration)
    sample = b"\x00\x00" if silent else b"\xe8\x03"
    frame = sample * channels
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(channels)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate)
        block = frame * 4096
        complete, remainder = divmod(frame_count, 4096)
        for _ in range(complete):
            stream.writeframesraw(block)
        stream.writeframesraw(frame * remainder)


def audio_manifest(voice: dict, path: Path) -> dict:
    audio = inspect_wav(path)
    return {
        "schema_version": AUDIO_MANIFEST_SCHEMA_VERSION,
        "renderer_version": VOICE_RENDERER_VERSION,
        "voice_package_id": voice["voice_package_id"],
        "voice_content_hash": voice["content_hash"],
        "script_id": voice["script_id"],
        "text_sha256": voice["narration"]["text_sha256"],
        "engine": voice["voice_profile"]["engine"],
        "voice": voice["voice_profile"]["voice"],
        "audio_file": path.name,
        "audio_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "audio_bytes": path.stat().st_size,
        "duration_seconds": audio["duration_seconds"],
        "sample_rate_hz": audio["sample_rate_hz"],
        "channels": audio["channels"],
        "sample_width_bits": audio["sample_width_bits"],
        "rendered_at": "2026-09-30T10:00:00Z",
        "network_used": False,
        "cloning_used": False,
    }


def fake_render_runner(command, **kwargs):
    output = Path(command[command.index("-w") + 1])
    write_wav(output)

    class Result:
        returncode = 0
        stderr = ""

    return Result()
