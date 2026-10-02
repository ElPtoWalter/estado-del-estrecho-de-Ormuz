"""Native PCM WAV decoding and signal checks; no edits, resampling or speed-up."""

from __future__ import annotations

import array
import io
import math
import struct
import sys
import wave

from .schema import VoiceError

MAX_AUDIO_BYTES = 20 * 1024 * 1024


def wrap_pcm(raw: bytes, *, rate: int = 24000, channels: int = 1) -> bytes:
    if not raw or len(raw) % (2 * channels) or rate not in (24000, 48000) or channels != 1:
        raise VoiceError("CORRUPT_AUDIO")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(raw)
    return buffer.getvalue()


def native_wav(raw: bytes, mime_type: str) -> bytes:
    if not raw or len(raw) > MAX_AUDIO_BYTES:
        raise VoiceError("EMPTY_OR_OVERSIZE_AUDIO")
    if mime_type in ("audio/wav", "audio/x-wav"):
        if raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
            raise VoiceError("CORRUPT_AUDIO")
        return raw
    if mime_type in ("audio/l16;codec=pcm;rate=24000", "audio/l16;rate=24000;channels=1"):
        # Google's TTS audio/l16 payload is native signed little-endian PCM16.
        if raw.startswith(b"RIFF"):
            raise VoiceError("AUDIO_FORMAT_MISMATCH")
        return wrap_pcm(raw)
    raise VoiceError("UNSUPPORTED_AUDIO_FORMAT")


def inspect_audio(data: bytes, target_seconds: float) -> tuple[dict, list[str]]:
    errors = []
    if not isinstance(data, bytes) or len(data) < 48044 or len(data) > MAX_AUDIO_BYTES:
        return {}, ["AUDIO_SIZE_INVALID"]
    try:
        if data[:4] != b"RIFF" or data[8:12] != b"WAVE" or struct.unpack("<I", data[4:8])[0] != len(data) - 8:
            return {}, ["CORRUPT_AUDIO"]
        offset, data_sizes = 12, []
        while offset < len(data):
            if offset + 8 > len(data):
                return {}, ["CORRUPT_AUDIO"]
            chunk_size = struct.unpack("<I", data[offset + 4:offset + 8])[0]
            chunk_end = offset + 8 + chunk_size
            if chunk_end > len(data):
                return {}, ["CORRUPT_AUDIO"]
            if data[offset:offset + 4] == b"data":
                data_sizes.append(chunk_size)
            offset = chunk_end + (chunk_size % 2)
        if offset != len(data) or len(data_sizes) != 1:
            return {}, ["CORRUPT_AUDIO"]
        with wave.open(io.BytesIO(data), "rb") as audio:
            channels, width, rate, frames = audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getnframes()
            if audio.getcomptype() != "NONE" or width != 2 or channels != 1 or rate not in (24000, 48000):
                return {}, ["AUDIO_FORMAT_INVALID"]
            pcm = audio.readframes(frames)
            if data_sizes[0] != frames * channels * width or len(pcm) != frames * channels * width or audio.readframes(1):
                return {}, ["CORRUPT_AUDIO"]
    except (wave.Error, EOFError, ValueError, struct.error):
        return {}, ["CORRUPT_AUDIO"]
    samples = array.array("h", pcm)
    if sys.byteorder != "little":
        samples.byteswap()
    if not samples:
        return {}, ["EMPTY_AUDIO"]
    peak = max(abs(sample) for sample in samples) / 32768
    rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples)) / 32768
    silent = sum(abs(sample) <= 3 for sample in samples) / len(samples)
    clipped = sum(abs(sample) >= 32760 for sample in samples) / len(samples)
    longest, streak = 0, 0
    for sample in samples:
        streak = streak + 1 if abs(sample) >= 32760 else 0
        longest = max(longest, streak)
    duration = frames / rate
    if not isinstance(target_seconds, (int, float)) or not math.isfinite(target_seconds) or target_seconds <= 0:
        errors.append("INVALID_DURATION_TARGET")
    elif not target_seconds * 0.8 <= duration <= target_seconds * 1.2:
        errors.append("DURATION_MISMATCH")
    if rms < 0.0001 or silent >= 0.98:
        errors.append("SILENT_AUDIO")
    if clipped >= 0.01 or longest / rate >= 0.02:
        errors.append("SEVERE_CLIPPING")
    return {
        "format": "PCM_WAV", "channels": channels, "sample_rate_hz": rate, "bits_per_sample": width * 8,
        "frames": frames, "duration_seconds": round(duration, 6), "size_bytes": len(data),
        "peak_amplitude": round(peak, 6), "rms_dbfs": round(20 * math.log10(max(rms, 1e-12)), 4),
        "silence_fraction": round(silent, 6), "clipped_fraction": round(clipped, 6),
        "longest_clipped_seconds": round(longest / rate, 6),
    }, errors
