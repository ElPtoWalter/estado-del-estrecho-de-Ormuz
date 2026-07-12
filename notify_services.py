#!/usr/bin/env python3
"""Notifica cambios significativos a IndexNow y canales opcionales.

Variables opcionales del workflow:
- TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID
- NTFY_TOPIC_URL

IndexNow se configura en config.json. Los errores se muestran como advertencias y
no interrumpen la actualización principal.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
CONFIG_FILE = ROOT / "config.json"
USER_AGENT = "estado-ormuz/3.0 IndexNow notifier"


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def post_json(url: str, payload: dict, timeout: int = 25) -> tuple[int, str]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json,text/plain,*/*",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.read(1000).decode("utf-8", errors="replace")


def post_form(url: str, payload: dict, timeout: int = 25) -> tuple[int, str]:
    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.read(1000).decode("utf-8", errors="replace")


def notify_indexnow(change: dict, config: dict) -> None:
    settings = config.get("indexnow") or {}
    if not settings.get("enabled", True):
        print("IndexNow desactivado en config.json.")
        return
    key = str(settings.get("key") or "").strip()
    key_location = str(settings.get("key_location") or "").strip()
    urls = [str(url) for url in change.get("urls", []) if str(url).startswith("https://")]
    if not key or not key_location or not urls:
        print("::warning::IndexNow no está completamente configurado.", file=sys.stderr)
        return
    host = urlparse(change.get("base_url") or urls[0]).netloc
    payload = {"host": host, "key": key, "keyLocation": key_location, "urlList": urls[:10000]}
    endpoint = str(settings.get("endpoint") or "https://api.indexnow.org/indexnow")
    try:
        status, body = post_json(endpoint, payload)
        print(f"IndexNow: HTTP {status} {body[:200]}")
    except urllib.error.HTTPError as exc:
        body = exc.read(1000).decode("utf-8", errors="replace")
        print(f"::warning::IndexNow HTTP {exc.code}: {body[:300]}", file=sys.stderr)
    except Exception as exc:
        print(f"::warning::IndexNow falló: {type(exc).__name__}: {exc}", file=sys.stderr)


def telegram_text(change: dict) -> str:
    status_map = {"ABIERTO": "🟢 ABIERTO", "CERRADO": "🔴 CERRADO", "INCIERTO": "🟠 INCIERTO"}
    status = status_map.get(change.get("status"), "🟠 INCIERTO")
    previous = change.get("previous_status") or "sin registro"
    return (
        f"Estado del estrecho de Ormuz: {status}\n"
        f"Estado anterior: {previous}\n"
        f"Confianza: {change.get('confidence', 'BAJA')}\n"
        f"{change.get('summary_es', '')}\n"
        f"{change.get('base_url', '')}"
    )


def notify_telegram(change: dict) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("Telegram: sin configurar; se omite.")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        status, _ = post_form(
            url,
            {
                "chat_id": chat_id,
                "text": telegram_text(change),
                "disable_web_page_preview": "true",
            },
        )
        print(f"Telegram: HTTP {status}")
    except Exception as exc:
        print(f"::warning::Telegram falló: {type(exc).__name__}: {exc}", file=sys.stderr)


def notify_ntfy(change: dict) -> None:
    topic_url = os.environ.get("NTFY_TOPIC_URL", "").strip()
    if not topic_url:
        print("ntfy: sin configurar; se omite.")
        return
    body = telegram_text(change).encode("utf-8")
    request = urllib.request.Request(
        topic_url,
        data=body,
        headers={
            "User-Agent": USER_AGENT,
            "Title": "Cambio en el estrecho de Ormuz",
            "Tags": "warning,ship",
            "Click": change.get("base_url", ""),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            print(f"ntfy: HTTP {response.status}")
    except Exception as exc:
        print(f"::warning::ntfy falló: {type(exc).__name__}: {exc}", file=sys.stderr)


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso: notify_services.py <change.json>", file=sys.stderr)
        return 2
    change = load_json(Path(sys.argv[1]))
    if not change.get("meaningful_change"):
        print("No hay cambio significativo; no se envían alertas ni IndexNow.")
        return 0
    config = load_json(CONFIG_FILE)
    # GitHub Pages puede tardar unos segundos en desplegar el commit recién creado.
    time.sleep(int(config.get("post_deploy_notification_delay_seconds", 15)))
    notify_indexnow(change, config)
    notify_telegram(change)
    notify_ntfy(change)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
