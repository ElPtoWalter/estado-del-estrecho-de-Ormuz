#!/usr/bin/env python3
"""Check public HTML after deployment, never unpublished internal endpoints."""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from adsense_checks import publisher_id, validate_ads_txt
from datetime import datetime, timezone

BASE = "https://estrechoormuz.com/"


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
        raw, content_type = fetch("ads.txt", token, timeout)
        errors.extend(validate_ads_txt(raw, publisher_id(Path(__file__).parent)))
        if 'text/plain' not in content_type.lower():
            errors.append('ads.txt: expected text/plain')
    except Exception as exc:
        errors.append(f"ads.txt: {exc}")
    try:
        raw, _ = fetch("sitemap.xml", token, timeout)
        root = ET.fromstring(raw)
        if not root.tag.endswith("urlset"):
            errors.append("sitemap.xml no tiene raíz urlset")
    except Exception as exc:
        errors.append(f"sitemap.xml: {exc}")
    for page in ("index.html", "evidencias.html", "en-evidence.html", "historial.html", "parte-diario.html", "diario.html"):
        try:
            raw, _ = fetch(page, token, timeout)
            text = raw.decode("utf-8", errors="replace").lower()
            if "<html" not in text or "</html>" not in text:
                errors.append(f"{page}: respuesta HTML incompleta")
            if page in {"evidencias.html", "en-evidence.html"}:
                if 'data-archive-empty' not in text or 'archive-loading' in text:
                    errors.append(f"{page}: archivo público no preparado")
            if '/public-ui.min.js' not in text:
                errors.append(f"{page}: faltan interacciones públicas")
        except Exception as exc:
            errors.append(f"{page}: {exc}")
    return errors


def history_attempt(timeout: int) -> list[str]:
    """Opt-in post-deployment verification of the sealed PR #22 release."""
    import history_release as release
    import history_public_candidate as candidate
    from publication_quality import HISTORY_ARTICLES, HISTORY_REFERENCES
    files, reviews = release.verify()
    expected = release.render(files, reviews)
    errors = []
    token = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')
    for name, data in expected.items():
        try:
            raw, _ = fetch(name, token, timeout)
            if candidate.sha(raw) != candidate.sha(data):
                errors.append(f'{name}: release hash mismatch')
        except Exception as exc:
            errors.append(f'{name}: {exc}')
    try:
        raw, _ = fetch('sitemap.xml', token, timeout)
        urls = {node.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc').text for node in ET.fromstring(raw)}
        for name in HISTORY_ARTICLES | HISTORY_REFERENCES:
            if ((BASE+name) in urls) != (name in HISTORY_ARTICLES):
                errors.append(f'{name}: incorrect deployed sitemap selection')
    except Exception as exc:
        errors.append(f'history sitemap: {exc}')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempts", type=int, default=8)
    parser.add_argument("--delay", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument('--history-release', action='store_true')
    args = parser.parse_args()
    last: list[str] = []
    for attempt in range(1, max(1, args.attempts) + 1):
        last = one_attempt(args.timeout)
        if args.history_release:
            last.extend(history_attempt(args.timeout))
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
