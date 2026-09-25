#!/usr/bin/env python3
"""Read-only Gemini connectivity check for the manual phase-1 pilot."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from free_editorial_ai import GEMINI_API_BASE, free_gemini_model_name


def main() -> int:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        print("Gemini API: clave no disponible")
        return 2

    model = free_gemini_model_name(os.getenv("GEMINI_MODEL"))
    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": 'Devuelve exclusivamente este JSON: {"ok":true}'}],
        }],
        "generationConfig": {
            "maxOutputTokens": 32,
        },
    }
    request = urllib.request.Request(
        f"{GEMINI_API_BASE}/{model}:generateContent",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-goog-api-key": key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            envelope = json.loads(response.read().decode("utf-8"))
        candidates = envelope.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            print("Gemini API: respuesta no válida")
            return 3
        print("Gemini API: conexión correcta")
        return 0
    except urllib.error.HTTPError as exc:
        print(f"Gemini API: HTTP {exc.code}")
        return 4
    except (urllib.error.URLError, TimeoutError):
        print("Gemini API: error de red")
        return 5
    except (ValueError, json.JSONDecodeError):
        print("Gemini API: respuesta no válida")
        return 6


if __name__ == "__main__":
    raise SystemExit(main())
