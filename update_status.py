#!/usr/bin/env python3
"""Actualiza status.json a partir de noticias recientes.

Fuentes:
1. GDELT DOC API.
2. Google News RSS.

Criterio:
- ABIERTO/CERRADO solo con afirmaciones operativas explícitas.
- Las noticias de riesgo se contabilizan y diagnostican, pero no cambian por sí
  solas el estado a ABIERTO o CERRADO.
- Si fallan todas las fuentes, conserva el último estado válido.
"""
from __future__ import annotations

import email.utils
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
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
    "theguardian.com": "The Guardian",
    "ft.com": "Financial Times",
    "bloomberg.com": "Bloomberg",
    "cnn.com": "CNN",
    "cnbc.com": "CNBC",
    "aljazeera.com": "Al Jazeera",
    "euronews.com": "Euronews",
    "navy.mil": "U.S. Navy",
    "imo.org": "IMO",
    "maritime.dot.gov": "MARAD",
    "ukmto.org": "UKMTO",
    "centcom.mil": "CENTCOM",
    "tradewindsnews.com": "TradeWinds",
    "lloydslist.com": "Lloyd's List",
    "marinelink.com": "MarineLink",
    "splash247.com": "Splash247",
    "seatrade-maritime.com": "Seatrade Maritime News",
    "argusmedia.com": "Argus Media",
    "spglobal.com": "S&P Global",
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
    "al jazeera": "Al Jazeera",
    "euronews": "Euronews",
    "u.s. navy": "U.S. Navy",
    "us navy": "U.S. Navy",
    "international maritime organization": "IMO",
    "imo": "IMO",
    "marad": "MARAD",
    "ukmto": "UKMTO",
    "centcom": "CENTCOM",
    "tradewinds": "TradeWinds",
    "tradewinds news": "TradeWinds",
    "lloyd's list": "Lloyd's List",
    "lloyds list": "Lloyd's List",
    "marinelink": "MarineLink",
    "splash247": "Splash247",
    "splash 247": "Splash247",
    "seatrade maritime news": "Seatrade Maritime News",
    "seatrade maritime": "Seatrade Maritime News",
    "argus": "Argus Media",
    "argus media": "Argus Media",
    "s&p global": "S&P Global",
    "sp global": "S&P Global",
    "platts": "S&P Global",
}

CLOSED_PATTERNS = [
    r"\bstrait of hormuz (?:is |has been |was |remains |will remain )?(?:closed|shut|sealed|blocked)\b",
    r"\b(?:closes|closed|shuts|shut|blocks|blocked) (?:the )?strait of hormuz\b",
    r"\bclosure of (?:the )?strait of hormuz\b",
    r"\btraffic (?:is |was |has been )?(?:halted|stopped|suspended) (?:through|in) (?:the )?strait of hormuz\b",
    r"\bshipping (?:is |was |has been )?(?:halted|stopped|suspended) (?:through|in) (?:the )?strait of hormuz\b",
    r"\bno (?:commercial )?(?:ships|vessels|tankers) (?:are )?(?:transiting|passing through) (?:the )?strait of hormuz\b",
]

OPEN_PATTERNS = [
    r"\bstrait of hormuz (?:is |has been |remains )?(?:open|reopened|re-opened)\b",
    r"\b(?:reopens|reopened|re-opens|re-opened) (?:the )?strait of hormuz\b",
    r"\btraffic (?:resumes|resumed) (?:through|in) (?:the )?strait of hormuz\b",
    r"\bshipping (?:resumes|resumed) (?:through|in) (?:the )?strait of hormuz\b",
    r"\b(?:ships|vessels|tankers) (?:continue|continued) to transit (?:the )?strait of hormuz\b",
    r"\bcommercial traffic (?:continues|continued) (?:through|in) (?:the )?strait of hormuz\b",
]

RISK_PATTERNS = [
    r"\btransits?\s+(?:fall|fell|drop|dropped|decline|declined|slowed)\b",
    r"\bshipping\s+(?:disrupted|reduced|suspended|slowed)\b",
    r"\bvessels?\s+(?:waiting|holding|diverted|rerouted|avoiding)\b",
    r"\btankers?\s+(?:waiting|diverted|rerouted|halted|avoiding)\b",
    r"\btraffic\s+(?:falls|fell|drops|dropped|declines|declined|slows|slowed)\b",
    r"\bwar risk premiums?\b",
    r"\bnaval escorts?\b",
    r"\bconvoys?\b",
    r"\bshipping companies?\s+(?:suspend|suspended|halt|halted|avoid|avoided)\b",
    r"\bmarine insurers?\b",
    r"\bsecurity advisory\b",
    r"\bmaritime warning\b",
    r"\battack(?:s|ed)?\b",
    r"\bmine(?:s|d)?\b",
    r"\bblockade\b",
    r"\bcongestion\b",
]

NEGATION_OR_HYPOTHETICAL = [
    r"\bnot closed\b",
    r"\bden(?:y|ies|ied|ial)\b",
    r"\bcould\b",
    r"\bmight\b",
    r"\bmay\b",
    r"\bif\b",
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
    "Chrome/126.0 Safari/537.36 estado-ormuz/3.0"
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


def is_risk_signal(title: str) -> bool:
    text = re.sub(r"\s+", " ", title.lower()).strip()
    return any(re.search(pattern, text) for pattern in RISK_PATTERNS)


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


def fetch_gdelt(hours: int) -> tuple[list[dict], dict]:
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

    stats = Counter(raw_results=0, accepted=0, unknown_source=0)
    articles: list[dict] = []
    for item in payload.get("articles", []):
        stats["raw_results"] += 1
        article_url = item.get("url", "")
        _, outlet = domain_name(article_url)
        if not outlet:
            stats["unknown_source"] += 1
            continue
        articles.append(
            {
                "title": item.get("title", ""),
                "url": article_url,
                "outlet": outlet,
                "date": parse_date(item.get("seendate", "")),
                "provider": "GDELT",
            }
        )
        stats["accepted"] += 1
    return articles, dict(stats)


def google_news_feed_url(query: str) -> str:
    params = {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)


def fetch_google_news(hours: int) -> tuple[list[dict], dict]:
    days = max(1, (hours + 23) // 24)
    queries = (
        f'"Strait of Hormuz" (open OR reopened OR transit OR shipping OR vessels OR tankers) when:{days}d',
        f'"Strait of Hormuz" (closed OR closure OR blocked OR halted OR suspended OR disrupted) when:{days}d',
        f'"Strait of Hormuz" (attack OR attacks OR mines OR escort OR convoy OR warning OR advisory) when:{days}d',
        f'"Strait of Hormuz" (traffic OR transits OR tanker OR LNG OR oil OR shipping) when:{days}d',
        f'"Hormuz" ("ships diverted" OR "vessels waiting" OR "transits fall" OR "traffic drops") when:{days}d',
        f'"Hormuz" (UKMTO OR IMO OR MARAD OR JMIC OR CENTCOM) when:{days}d',
    )

    stats = Counter(
        queries=len(queries),
        successful_queries=0,
        raw_results=0,
        accepted=0,
        unknown_source=0,
    )
    articles: list[dict] = []
    errors: list[Exception] = []

    for query in queries:
        try:
            raw = request_bytes(
                google_news_feed_url(query),
                accept="application/rss+xml,application/xml,text/xml;q=0.9,*/*;q=0.8",
            )
            root = ET.fromstring(raw)
            stats["successful_queries"] += 1
        except (urllib.error.URLError, TimeoutError, OSError, ET.ParseError) as exc:
            errors.append(exc)
            continue

        for item in root.findall("./channel/item"):
            stats["raw_results"] += 1
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            published = (item.findtext("pubDate") or "").strip()
            source_node = item.find("source")
            source_name = (source_node.text or "").strip() if source_node is not None else ""
            source_url = source_node.attrib.get("url", "") if source_node is not None else ""
            outlet = trusted_source(source_name, source_url)
            if not outlet:
                stats["unknown_source"] += 1
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
            stats["accepted"] += 1

    if stats["successful_queries"] == 0 and errors:
        raise errors[-1]
    return articles, dict(stats)


def write_status(
    status: str,
    message: str,
    source_name: str | None = None,
    source_url: str | None = None,
    *,
    previous: dict | None = None,
    verification_ok: bool = True,
    diagnostics: dict | None = None,
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
    if diagnostics:
        payload["diagnostics"] = diagnostics
    if verification_ok:
        payload["last_success_at"] = now
    elif previous:
        payload["last_success_at"] = previous.get("last_success_at")
    STATUS_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def preserve_previous_after_network_failure(
    previous: dict,
    errors: list[str],
    diagnostics: dict,
) -> None:
    previous_state = previous.get("status")
    if previous_state not in {"ABIERTO", "CERRADO", "INCIERTO"}:
        previous_state = "INCIERTO"
    write_status(
        previous_state,
        "No se pudo renovar la comprobación; se conserva el último estado publicado.",
        previous.get("source_name"),
        previous.get("source_url"),
        previous=previous,
        verification_ok=False,
        diagnostics=diagnostics,
    )
    print("::warning::Fallaron todas las fuentes: " + " | ".join(errors), file=sys.stderr)


def print_stats(name: str, stats: dict) -> None:
    fields = ", ".join(f"{key}={value}" for key, value in stats.items())
    print(f"{name}: {fields}")


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
    provider_stats: dict[str, dict] = {}

    for source_name, fetcher in (
        ("GDELT", fetch_gdelt),
        ("Google News RSS", fetch_google_news),
    ):
        try:
            articles, stats = fetcher(hours)
            provider_stats[source_name] = stats
            all_articles.extend(articles)
            print_stats(source_name, stats)
        except Exception as exc:
            errors.append(f"{source_name}: {type(exc).__name__}: {exc}")
            provider_stats[source_name] = {"error": f"{type(exc).__name__}: {exc}"}
            print(f"{source_name} falló: {exc}", file=sys.stderr)

    diagnostics = {
        "lookback_hours": hours,
        "providers": provider_stats,
        "accepted_before_dedup": len(all_articles),
    }

    if not all_articles and len(errors) == 2:
        preserve_previous_after_network_failure(previous, errors, diagnostics)
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours + 2)
    seen_titles: set[str] = set()
    explicit_signals: list[dict] = []
    risk_signals: list[dict] = []
    discarded_old = 0
    discarded_duplicate = 0
    discarded_without_signal = 0

    for article in all_articles:
        title_key = re.sub(r"\W+", " ", article["title"].lower()).strip()
        if not title_key or title_key in seen_titles:
            discarded_duplicate += 1
            continue
        seen_titles.add(title_key)

        if article["date"] < cutoff:
            discarded_old += 1
            continue

        state = classify(article["title"])
        if state:
            explicit_signals.append({**article, "state": state})
        elif is_risk_signal(article["title"]):
            risk_signals.append(article)
        else:
            discarded_without_signal += 1

    explicit_signals.sort(key=lambda item: item["date"], reverse=True)
    risk_signals.sort(key=lambda item: item["date"], reverse=True)

    diagnostics.update(
        {
            "unique_articles": len(seen_titles),
            "discarded_duplicates": discarded_duplicate,
            "discarded_old": discarded_old,
            "discarded_without_signal": discarded_without_signal,
            "explicit_operational_signals": len(explicit_signals),
            "risk_signals": len(risk_signals),
            "independent_outlets": len(
                {item["outlet"] for item in explicit_signals + risk_signals}
            ),
        }
    )

    print(
        "Resumen: "
        f"aceptados={len(all_articles)}, únicos={len(seen_titles)}, "
        f"explícitos={len(explicit_signals)}, riesgo={len(risk_signals)}, "
        f"antiguos={discarded_old}, sin_señal={discarded_without_signal}"
    )

    if not explicit_signals:
        if risk_signals:
            newest_risk = risk_signals[0]
            message = (
                "No hay una confirmación explícita reciente de apertura o cierre. "
                f"Se detectaron {len(risk_signals)} señales recientes de riesgo o restricción; "
                f'la más reciente es “{newest_risk["title"]}”.'
            )
            write_status(
                "INCIERTO",
                message,
                newest_risk["outlet"],
                newest_risk["url"],
                diagnostics=diagnostics,
            )
        else:
            write_status(
                "INCIERTO",
                "No hay una confirmación explícita reciente en las fuentes seleccionadas.",
                diagnostics=diagnostics,
            )
        return 0

    newest = explicit_signals[0]
    recent_window = newest["date"] - timedelta(hours=12)
    recent_states = {
        item["state"] for item in explicit_signals if item["date"] >= recent_window
    }

    if len(recent_states) > 1:
        write_status(
            "INCIERTO",
            "Las fuentes recientes ofrecen señales contradictorias; se requiere confirmación.",
            diagnostics=diagnostics,
        )
        return 0

    message = f'Confirmación operativa detectada: “{newest["title"]}”.'
    write_status(
        newest["state"],
        message,
        newest["outlet"],
        newest["url"],
        diagnostics=diagnostics,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
