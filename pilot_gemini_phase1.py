#!/usr/bin/env python3
"""Non-publishing connectivity pilot for the Phase 1 Gemini path."""
from __future__ import annotations

from free_editorial_ai import probe_gemini_connection


def main() -> int:
    ok, status = probe_gemini_connection()
    if ok:
        print("Gemini API: conexión correcta")
        return 0
    if status.startswith("http-"):
        print(f"Gemini API: HTTP {status.removeprefix('http-')}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
