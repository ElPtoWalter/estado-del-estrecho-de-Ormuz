#!/usr/bin/env python3
"""Prueba remota con cache-busting y reintentos tras el push de GitHub Pages."""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

BASE = "https://estrechoormuz.com/"
REQUIRED_STATUS = {"status", "operational_status", "confidence", "checked_at", "verification_ok", "stale"}


def fetch(path: str, token: str, timeout: int) -> tuple[bytes, str]:
    separator = "&" if "?" in path else "?"
    url = urllib.parse.urljoin(BASE, path) + f"{separator}healthcheck={token}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "estrechoormuz-deployment-check/2.0", "Cache-Control": "no-cache"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(), response.headers.get("Content-Type", "")


def one_attempt(timeout: int) -> list[str]:
    token = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    errors: list[str] = []
    try:
        raw, _ = fetch("status.json", token, timeout)
        payload = json.loads(raw.decode("utf-8-sig"))
        missing = REQUIRED_STATUS - set(payload) if isinstance(payload, dict) else REQUIRED_STATUS
        if missing:
            errors.append(f"status.json carece de: {', '.join(sorted(missing))}")
    except Exception as exc:
        errors.append(f"status.json: {exc}")
    try:
        raw, _ = fetch("sitemap.xml", token, timeout)
        root = ET.fromstring(raw)
        if not root.tag.endswith("urlset"):
            errors.append("sitemap.xml no tiene raíz urlset")
    except Exception as exc:
        errors.append(f"sitemap.xml: {exc}")
    for page in ("evidencias.html", "historial.html"):
        try:
            raw, _ = fetch(page, token, timeout)
            text = raw.decode("utf-8", errors="replace").lower()
            if "<html" not in text or "</html>" not in text:
                errors.append(f"{page}: respuesta HTML incompleta")
        except Exception as exc:
            errors.append(f"{page}: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempts", type=int, default=8)
    parser.add_argument("--delay", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()
    last: list[str] = []
    for attempt in range(1, max(1, args.attempts) + 1):
        last = one_attempt(args.timeout)
        if not last:
            print(f"Despliegue remoto correcto en el intento {attempt}.")
            return 0
        print(f"Intento remoto {attempt}/{args.attempts} no válido:")
        for error in last:
            print(f"  - {error}")
        if attempt < args.attempts:
            time.sleep(max(0, args.delay))
    print("ERROR: el despliegue remoto no superó la prueba tras los reintentos.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
