#!/usr/bin/env python3
"""Actualiza status.json usando titulares recientes obtenidos mediante GDELT.

Diseño conservador: solo cambia a ABIERTO/CERRADO con un titular explícito de
un dominio seleccionado. Ante señales contradictorias o falta de confirmación,
publica INCIERTO.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
STATUS_FILE = ROOT / "status.json"
CONFIG_FILE = ROOT / "config.json"

TRUSTED_DOMAINS = {
    "reuters.com": "Reuters",
    "apnews.com": "Associated Press",
    "bbc.com": "BBC",
    "bbc.co.uk": "BBC",
    "aljazeera.com": "Al Jazeera",
    "theguardian.com": "The Guardian",
    "ft.com": "Financial Times",
    "bloomberg.com": "Bloomberg",
    "cnn.com": "CNN",
    "cnbc.com": "CNBC",
    "navy.mil": "U.S. Navy",
    "imo.org": "IMO"
}

# Se evalúan titulares, no el cuerpo completo, para reducir falsos positivos.
CLOSED_PATTERNS = [
    r"\bstrait of hormuz (?:is |has been |was )?(?:closed|shut|sealed|blocked)\b",
    r"\b(?:closes|closed|shuts|shut|blocks|blocked) (?:the )?strait of hormuz\b",
    r"\bclosure of (?:the )?strait of hormuz\b",
]
OPEN_PATTERNS = [
    r"\bstrait of hormuz (?:is |has been )?(?:open|reopened|re-opened)\b",
    r"\b(?:reopens|reopened|re-opens|re-opened) (?:the )?strait of hormuz\b",
    r"\btraffic (?:resumes|resumed) (?:through|in) (?:the )?strait of hormuz\b",
]
NEGATIONS = ("could", "might", "may", "threat", "threatens", "warns", "if ", "risk", "fear", "deny", "denies", "not closed")


def load_json(path: Path, default: dict) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def domain_name(url: str) -> tuple[str | None, str | None]:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    for domain, name in TRUSTED_DOMAINS.items():
        if host == domain or host.endswith("." + domain):
            return domain, name
    return None, None


def parse_date(value: str) -> datetime:
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass
    return datetime.min.replace(tzinfo=timezone.utc)


def classify(title: str) -> str | None:
    text = re.sub(r"\s+", " ", title.lower()).strip()
    if any(term in text for term in NEGATIONS):
        return None
    if any(re.search(pattern, text) for pattern in OPEN_PATTERNS):
        return "ABIERTO"
    if any(re.search(pattern, text) for pattern in CLOSED_PATTERNS):
        return "CERRADO"
    return None


def fetch_articles(hours: int) -> list[dict]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    params = {
        "query": '"Strait of Hormuz"',
        "mode": "ArtList",
        "maxrecords": "250",
        "format": "json",
        "sort": "HybridRel",
        "startdatetime": start.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end.strftime("%Y%m%d%H%M%S"),
    }
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": "estado-ormuz/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    return payload.get("articles", [])


def write_status(status: str, message: str, source_name=None, source_url=None) -> None:
    payload = {
        "status": status,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "message": message,
        "source_name": source_name,
        "source_url": source_url,
    }
    STATUS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    config = load_json(CONFIG_FILE, {"manual_override": None, "lookback_hours": 72})
    override = config.get("manual_override")
    if override in {"ABIERTO", "CERRADO", "INCIERTO"}:
        write_status(override, "Estado fijado manualmente en config.json.")
        return 0

    try:
        articles = fetch_articles(int(config.get("lookback_hours", 72)))
    except Exception as exc:  # Mantiene la web operativa aunque falle la fuente.
        write_status("INCIERTO", f"No se pudo completar la comprobación automática: {type(exc).__name__}.")
        print(f"Error consultando GDELT: {exc}", file=sys.stderr)
        return 0

    signals = []
    for article in articles:
        url = article.get("url", "")
        _, outlet = domain_name(url)
        if not outlet:
            continue
        title = article.get("title", "")
        state = classify(title)
        if state:
            signals.append({
                "state": state,
                "title": title,
                "url": url,
                "outlet": outlet,
                "date": parse_date(article.get("seendate", "")),
            })

    signals.sort(key=lambda item: item["date"], reverse=True)
    if not signals:
        write_status("INCIERTO", "No hay una confirmación explícita reciente en las fuentes seleccionadas.")
        return 0

    newest = signals[0]
    recent_window = newest["date"] - timedelta(hours=12)
    recent_states = {item["state"] for item in signals if item["date"] >= recent_window}
    if len(recent_states) > 1:
        write_status("INCIERTO", "Las fuentes recientes ofrecen señales contradictorias; se requiere confirmación.")
        return 0

    message = f'Confirmación detectada: “{newest["title"]}”.'
    write_status(newest["state"], message, newest["outlet"], newest["url"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
