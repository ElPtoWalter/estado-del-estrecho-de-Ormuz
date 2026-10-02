"""Single bounded, stateless TTS request. Sanitized failures, no retries/upgrades."""

from __future__ import annotations

import base64
import binascii
import json
import os
import socket
import urllib.error
import urllib.request

from .audio import MAX_AUDIO_BYTES, native_wav
from .input import validate_voice_input
from .schema import VoiceError

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"
MAX_RESPONSE_BYTES = 30 * 1024 * 1024
HTTP_CODES = {400: "BAD_REQUEST", 401: "AUTHENTICATION_FAILED", 403: "ACCESS_DENIED", 404: "MODEL_UNAVAILABLE", 429: "QUOTA_EXHAUSTED", 500: "PROVIDER_ERROR", 503: "PROVIDER_UNAVAILABLE"}


def request_payload(value: dict) -> dict:
    config = value["voice_config"]
    words = len(value["full_text_for_tts"].split())
    pace = round(words * 60 / value["target_seconds"])
    timing = (f" Duración orientativa {value['target_seconds']} segundos, aproximadamente {pace} palabras por minuto. Leer el texto íntegro sin añadir ni omitir palabras." if value["language"] == "es" else f" Target about {value['target_seconds']} seconds, approximately {pace} words per minute. Read the entire transcript without adding or omitting words.")
    return {
        "model": config["model"], "store": False,
        "input": [{"type": "user_input", "content": [{
            "type": "text", "text": value["full_text_for_tts"],
            "annotations": [{"type": "speech_metadata", "style": config["style"] + timing}],
        }]}],
        "response_format": {"type": "audio", "mime_type": "audio/wav"},
        "generation_config": {"speech_config": [{"voice": config["voice"]}]},
    }


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise VoiceError("PROVIDER_REDIRECT_REJECTED")


def render_gemini(package: dict, script: dict, value: dict, *, pronunciation: dict | None = None, opener=None) -> bytes:
    # Revalidate at the last network boundary, even when the caller says PASS.
    validate_voice_input(package, script, value, pronunciation=pronunciation)
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise VoiceError("MISSING_API_KEY")
    request = urllib.request.Request(ENDPOINT, data=json.dumps(request_payload(value), ensure_ascii=False).encode("utf-8"), headers={"Content-Type": "application/json", "x-goog-api-key": key}, method="POST")
    open_request = opener or urllib.request.build_opener(NoRedirect()).open
    try:
        with open_request(request, timeout=120) as response:
            raw_response = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw_response) > MAX_RESPONSE_BYTES:
            raise VoiceError("PROVIDER_RESPONSE_TOO_LARGE")
        result = json.loads(raw_response)
    except urllib.error.HTTPError as exc:
        raise VoiceError(HTTP_CODES.get(exc.code, "PROVIDER_HTTP_ERROR")) from None
    except (TimeoutError, socket.timeout):
        raise VoiceError("PROVIDER_TIMEOUT") from None
    except urllib.error.URLError:
        raise VoiceError("PROVIDER_NETWORK_ERROR") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise VoiceError("CORRUPT_PROVIDER_RESPONSE") from None
    except VoiceError:
        raise
    except (OSError, ValueError):
        raise VoiceError("PROVIDER_NETWORK_ERROR") from None
    try:
        if not isinstance(result, dict) or result.get("status", "completed") != "completed":
            raise VoiceError("INCOMPLETE_PROVIDER_RESPONSE")
        blocks = [block for step in result.get("steps", []) if step.get("type") == "model_output" for block in step.get("content", []) if block.get("type") == "audio"]
        if len(blocks) != 1:
            raise VoiceError("EMPTY_OR_AMBIGUOUS_AUDIO")
        encoded = blocks[0].get("data")
        if not isinstance(encoded, str) or len(encoded) > (MAX_AUDIO_BYTES * 4 // 3 + 8):
            raise VoiceError("CORRUPT_AUDIO")
        audio = base64.b64decode(encoded, validate=True)
        return native_wav(audio, blocks[0].get("mime_type", ""))
    except (KeyError, TypeError, AttributeError, binascii.Error, ValueError):
        raise VoiceError("CORRUPT_PROVIDER_RESPONSE") from None
