#!/usr/bin/env python3
"""Actualiza status.json a partir de noticias recientes.

Usa dos vías independientes:
1. GDELT DOC API.
2. Google News RSS como respaldo.

La decisión es conservadora: solo publica ABIERTO o CERRADO cuando un titular
reciente de una fuente seleccionada lo afirma de forma explícita. Si las
fuentes se contradicen, publica INCIERTO. Si fallan todas las conexiones,
conserva el último estado publicado en vez de cambiarlo por un error temporal.
"""
from __future__ import annotations

import email.utils
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
STATUS_FILE = ROOT / "status.json"
CONFIG_FILE = ROOT / "config.json"
INDEX_FILE = ROOT / "index.html"

TRUSTED_DOMAINS = {
    "reuters.com": "Reuters",
    "apnews.com": "Associated Press",
    "bbc.com": "BBC",
    "bbc.co.uk": "BBC",
    "theguardian.com": "The Guardian",
    "ft.com": "Financial Times",
    "bloomberg.com": "Bloomberg",
    "cnn.com": "CNN",
    "cnbc.com": "CNBC",
    "navy.mil": "U.S. Navy",
    "imo.org": "IMO",
}

TRUSTED_SOURCE_NAMES = {
    "reuters": "Reuters",
    "associated press": "Associated Press",
    "the associated press": "Associated Press",
    "ap news": "Associated Press",
    "bbc": "BBC",
    "bbc.com": "BBC",
    "bbc news": "BBC",
    "the guardian": "The Guardian",
    "financial times": "Financial Times",
    "bloomberg": "Bloomberg",
    "cnn": "CNN",
    "cnbc": "CNBC",
}

CLOSED_PATTERNS = [
    r"\bstrait of hormuz (?:is |has been |was |remains |will remain )?(?:closed|shut|sealed|blocked)\b",
    r"\b(?:closes|closed|shuts|shut|blocks|blocked) (?:the )?strait of hormuz\b",
    r"\bclosure of (?:the )?strait of hormuz\b",
]
OPEN_PATTERNS = [
    r"\bstrait of hormuz (?:is |has been |remains )?(?:open|reopened|re-opened)\b",
    r"\b(?:reopens|reopened|re-opens|re-opened) (?:the )?strait of hormuz\b",
    r"\btraffic (?:resumes|resumed) (?:through|in) (?:the )?strait of hormuz\b",
    r"\bshipping (?:resumes|resumed) (?:through|in) (?:the )?strait of hormuz\b",
]

# Titulares hipotéticos, peticiones políticas o desmentidos no cuentan como
# confirmación del estado.
NEGATION_OR_HYPOTHETICAL = [
    r"\bnot closed\b",
    r"\bden(?:y|ies|ied|ial)\b",
    r"\bcould\b",
    r"\bmight\b",
    r"\bmay\b",
    r"\bif\b",
    r"\brisk\b",
    r"\bfear(?:s|ed)?\b",
    r"\bthreat(?:s|ens|ened)?\b",
    r"\bwarn(?:s|ed|ing)?\b",
    r"\bdemand(?:s|ed|ing)?\b",
    r"\burge(?:s|d|ing)?\b",
    r"\bcall(?:s|ed|ing)? (?:on|for)\b",
    r"\bwant(?:s|ed|ing)?\b",
    r"\bask(?:s|ed|ing)?\b",
    r"\bpledge(?:s|d|ing)?\b",
    r"\bpromise(?:s|d|ing)?\b",
    r"\bagree(?:s|d|ment)? to (?:open|reopen|close|shut)\b",
    r"\bplan(?:s|ned|ning)? to (?:open|reopen|close|shut)\b",
]

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "Chrome/126.0 Safari/537.36 estado-ormuz/2.0"
)


def load_json(path: Path, default: dict) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default.copy()


def domain_name(url: str) -> tuple[str | None, str | None]:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    for domain, name in TRUSTED_DOMAINS.items():
        if host == domain or host.endswith("." + domain):
            return domain, name
    return None, None


def trusted_source(source_name: str, source_url: str = "") -> str | None:
    normalized = re.sub(r"\s+", " ", source_name.lower()).strip()
    if normalized in TRUSTED_SOURCE_NAMES:
        return TRUSTED_SOURCE_NAMES[normalized]
    _, outlet = domain_name(source_url)
    return outlet


def parse_date(value: str) -> datetime:
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return datetime.min.replace(tzinfo=timezone.utc)


def classify(title: str) -> str | None:
    text = re.sub(r"\s+", " ", title.lower()).strip()
    if any(re.search(pattern, text) for pattern in NEGATION_OR_HYPOTHETICAL):
        return None
    if any(re.search(pattern, text) for pattern in OPEN_PATTERNS):
        return "ABIERTO"
    if any(re.search(pattern, text) for pattern in CLOSED_PATTERNS):
        return "CERRADO"
    return None


def request_bytes(url: str, *, accept: str, attempts: int = 3) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": accept,
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    assert last_error is not None
    raise last_error


def fetch_gdelt(hours: int) -> list[dict]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    params = {
        "query": '"Strait of Hormuz"',
        "mode": "ArtList",
        "maxrecords": "250",
        "format": "json",
        "sort": "DateDesc",
        "startdatetime": start.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end.strftime("%Y%m%d%H%M%S"),
    }
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode(params)
    raw = request_bytes(url, accept="application/json,text/plain;q=0.9,*/*;q=0.8")
    payload = json.loads(raw.decode("utf-8-sig"))

    articles: list[dict] = []
    for item in payload.get("articles", []):
        url = item.get("url", "")
        _, outlet = domain_name(url)
        if not outlet:
            continue
        articles.append(
            {
                "title": item.get("title", ""),
                "url": url,
                "outlet": outlet,
                "date": parse_date(item.get("seendate", "")),
                "provider": "GDELT",
            }
        )
    return articles


def google_news_feed_url(query: str) -> str:
    params = {
        "q": query,
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
    }
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)


def fetch_google_news(hours: int) -> list[dict]:
    # Dos búsquedas separadas mejoran la cobertura y evitan depender de una
    # única consulta demasiado compleja.
    days = max(1, (hours + 23) // 24)
    queries = [
        f'"Strait of Hormuz" (closed OR shut OR blocked) when:{days}d',
        f'"Strait of Hormuz" (open OR reopened OR "traffic resumes") when:{days}d',
    ]

    articles: list[dict] = []
    errors: list[Exception] = []
    for query in queries:
        try:
            raw = request_bytes(
                google_news_feed_url(query),
                accept="application/rss+xml,application/xml,text/xml;q=0.9,*/*;q=0.8",
            )
            root = ET.fromstring(raw)
        except (urllib.error.URLError, TimeoutError, OSError, ET.ParseError) as exc:
            errors.append(exc)
            continue

        for item in root.findall("./channel/item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            published = (item.findtext("pubDate") or "").strip()
            source_node = item.find("source")
            source_name = (source_node.text or "").strip() if source_node is not None else ""
            source_url = source_node.attrib.get("url", "") if source_node is not None else ""
            outlet = trusted_source(source_name, source_url)
            if not outlet:
                continue
            articles.append(
                {
                    "title": title,
                    "url": link,
                    "outlet": outlet,
                    "date": parse_date(published),
                    "provider": "Google News RSS",
                }
            )

    if not articles and len(errors) == len(queries):
        raise errors[-1]
    return articles


MONTHS_ES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def format_checked_at_for_html(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        local = parsed.astimezone(ZoneInfo("Europe/Madrid"))
        return f"{local.day} de {MONTHS_ES[local.month - 1]} de {local.year}, {local:%H:%M}"
    except (TypeError, ValueError, OSError, KeyError):
        return "fecha no disponible"


def update_html_snapshot(payload: dict) -> None:
    # Escribe el estado en el HTML para buscadores y usuarios sin JavaScript.
    try:
        document = INDEX_FILE.read_text(encoding="utf-8")
    except OSError:
        return

    valid_states = {"ABIERTO", "CERRADO", "INCIERTO"}
    state = payload.get("status") if payload.get("status") in valid_states else "INCIERTO"
    css_class = {"ABIERTO": "open", "CERRADO": "closed", "INCIERTO": "uncertain"}[state]
    checked = html.escape(format_checked_at_for_html(str(payload.get("checked_at", ""))))
    message = html.escape(str(payload.get("message") or "Sin confirmación concluyente."))
    source_url = payload.get("source_url")
    source_name = html.escape(str(payload.get("source_name") or "Ver fuente"))

    if source_url:
        safe_url = html.escape(str(source_url), quote=True)
        source_line = (
            f'      <p id="sourceWrap"><a id="source" href="{safe_url}" '
            f'target="_blank" rel="noopener noreferrer">Fuente: {source_name}</a></p>'
        )
    else:
        source_line = (
            '      <p id="sourceWrap" hidden><a id="source" target="_blank" '
            'rel="noopener noreferrer">Ver fuente</a></p>'
        )

    snapshot = f'''    <!-- STATUS_SNAPSHOT_START -->
    <div id="status" class="status {css_class}" aria-live="polite">
      <span class="dot" aria-hidden="true"></span><span id="statusText">{state}</span>
    </div>
    <div class="details">
      <p id="updated">Última comprobación: {checked}</p>
      <p id="evidence">{message}</p>
{source_line}
    </div>
    <!-- STATUS_SNAPSHOT_END -->'''

    updated_document, count = re.subn(
        r"    <!-- STATUS_SNAPSHOT_START -->.*?    <!-- STATUS_SNAPSHOT_END -->",
        lambda _: snapshot,
        document,
        count=1,
        flags=re.DOTALL,
    )
    if count:
        INDEX_FILE.write_text(updated_document, encoding="utf-8")


def write_status(
    status: str,
    message: str,
    source_name: str | None = None,
    source_url: str | None = None,
    *,
    previous: dict | None = None,
    verification_ok: bool = True,
) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    payload = {
        "status": status,
        "checked_at": now,
        "message": message,
        "source_name": source_name,
        "source_url": source_url,
        "verification_ok": verification_ok,
    }
    if verification_ok:
        payload["last_success_at"] = now
    elif previous:
        payload["last_success_at"] = previous.get("last_success_at")
    STATUS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    update_html_snapshot(payload)


def preserve_previous_after_network_failure(previous: dict, errors: list[str]) -> None:
    previous_state = previous.get("status")
    if previous_state not in {"ABIERTO", "CERRADO", "INCIERTO"}:
        previous_state = "INCIERTO"
    message = "No se pudo renovar la comprobación; se conserva el último estado publicado."
    write_status(
        previous_state,
        message,
        previous.get("source_name"),
        previous.get("source_url"),
        previous=previous,
        verification_ok=False,
    )
    print("::warning::Fallaron todas las fuentes: " + " | ".join(errors), file=sys.stderr)


def main() -> int:
    previous = load_json(STATUS_FILE, {})
    config = load_json(CONFIG_FILE, {"manual_override": None, "lookback_hours": 72})
    override = config.get("manual_override")
    if override in {"ABIERTO", "CERRADO", "INCIERTO"}:
        write_status(override, "Estado fijado manualmente en config.json.")
        return 0

    hours = int(config.get("lookback_hours", 72))
    all_articles: list[dict] = []
    errors: list[str] = []

    for source_name, fetcher in (
        ("GDELT", fetch_gdelt),
        ("Google News RSS", fetch_google_news),
    ):
        try:
            articles = fetcher(hours)
            all_articles.extend(articles)
            print(f"{source_name}: {len(articles)} artículos aceptados.")
        except Exception as exc:  # una fuente puede fallar sin tumbar la otra
            errors.append(f"{source_name}: {type(exc).__name__}: {exc}")
            print(f"{source_name} falló: {exc}", file=sys.stderr)

    if not all_articles and len(errors) == 2:
        preserve_previous_after_network_failure(previous, errors)
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours + 2)
    seen_titles: set[str] = set()
    signals: list[dict] = []
    for article in all_articles:
        title_key = re.sub(r"\W+", " ", article["title"].lower()).strip()
        if not title_key or title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        if article["date"] < cutoff:
            continue
        state = classify(article["title"])
        if state:
            signals.append({**article, "state": state})

    signals.sort(key=lambda item: item["date"], reverse=True)
    if not signals:
        write_status(
            "INCIERTO",
            "No hay una confirmación explícita reciente en las fuentes seleccionadas.",
        )
        return 0

    newest = signals[0]
    recent_window = newest["date"] - timedelta(hours=12)
    recent_states = {item["state"] for item in signals if item["date"] >= recent_window}
    if len(recent_states) > 1:
        write_status(
            "INCIERTO",
            "Las fuentes recientes ofrecen señales contradictorias; se requiere confirmación.",
        )
        return 0

    message = f'Confirmación detectada: “{newest["title"]}”.'
    write_status(newest["state"], message, newest["outlet"], newest["url"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
