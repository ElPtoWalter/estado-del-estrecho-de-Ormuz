#!/usr/bin/env python3
"""Motor conservador para estimar el estado operativo del estrecho de Ormuz.

Principios:
- Una declaración política de cierre NO equivale a un cierre operativo.
- CERRADO exige evidencia de interrupción efectiva del tráfico.
- ABIERTO exige evidencia de tránsito o de una ruta operativa.
- Las señales contradictorias se publican como INCIERTO.
- Si fallan las fuentes, se conserva la última confirmación válida y se marca
  la comprobación como fallida, sin inventar un nuevo estado.

El script usa únicamente la biblioteca estándar de Python y actualiza:
- status.json
- history.json
- feed.xml
- snapshots HTML de portada e historial (ES/EN)

También escribe un archivo temporal de cambios cuando la variable de entorno
CHANGE_FILE está definida. Ese archivo lo usa el workflow para IndexNow y las
alertas opcionales.
"""
from __future__ import annotations

import argparse
import email.utils
import hashlib
import html
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
STATUS_FILE = ROOT / "status.json"
HISTORY_FILE = ROOT / "history.json"
CONFIG_FILE = ROOT / "config.json"
FEED_FILE = ROOT / "feed.xml"
SITEMAP_FILE = ROOT / "sitemap.xml"
INDEX_ES = ROOT / "index.html"
INDEX_EN = ROOT / "en.html"
HISTORY_ES = ROOT / "historial.html"
HISTORY_EN = ROOT / "en-history.html"
ENGINE_VERSION = 3

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "Chrome/126.0 Safari/537.36 estado-ormuz/3.0"
)

VALID_STATUS = {"ABIERTO", "CERRADO", "INCIERTO"}
VALID_CONFIDENCE = {"ALTA", "MEDIA", "BAJA"}
VALID_OPERATIONAL = {
    "OPEN_NORMAL",
    "OPEN_RESTRICTED",
    "CLOSED_CONFIRMED",
    "CLOSURE_DECLARED_UNCONFIRMED",
    "HIGH_RISK_UNCONFIRMED",
    "CONTRADICTORY",
    "NO_RECENT_CONFIRMATION",
    "MANUAL_OVERRIDE",
}

OPERATIONAL_LABELS = {
    "OPEN_NORMAL": ("Tránsito operativo", "Operational transit"),
    "OPEN_RESTRICTED": ("Abierto con restricciones", "Open with restrictions"),
    "CLOSED_CONFIRMED": ("Cierre operativo confirmado", "Operational closure confirmed"),
    "CLOSURE_DECLARED_UNCONFIRMED": (
        "Cierre declarado, no confirmado",
        "Closure declared, not operationally confirmed",
    ),
    "HIGH_RISK_UNCONFIRMED": ("Riesgo elevado, estado no confirmado", "High risk, status unconfirmed"),
    "CONTRADICTORY": ("Fuentes contradictorias", "Conflicting sources"),
    "NO_RECENT_CONFIRMATION": ("Sin confirmación reciente", "No recent confirmation"),
    "MANUAL_OVERRIDE": ("Estado fijado manualmente", "Manually set status"),
}

MONTHS_ES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


@dataclass(frozen=True)
class SourceProfile:
    source_id: str
    name: str
    tier: int
    weight: float
    domains: tuple[str, ...]
    aliases: tuple[str, ...]
    official: bool = False


SOURCE_PROFILES = (
    SourceProfile("ukmto", "UKMTO", 5, 5.0, ("ukmto.org",), ("ukmto", "uk maritime trade operations"), True),
    SourceProfile("imo", "IMO", 5, 5.0, ("imo.org",), ("imo", "international maritime organization"), True),
    SourceProfile("marad", "U.S. MARAD", 5, 5.0, ("maritime.dot.gov",), ("u.s. marad", "marad", "us maritime administration"), True),
    SourceProfile("jmic", "JMIC", 5, 5.0, ("combinedmaritimeforces.com",), ("jmic", "joint maritime information center"), True),
    SourceProfile("centcom", "U.S. CENTCOM", 5, 4.8, ("centcom.mil",), ("u.s. centcom", "centcom"), True),
    SourceProfile("us_navy", "U.S. Navy", 5, 4.8, ("navy.mil",), ("u.s. navy", "us navy"), True),
    SourceProfile("oman_news", "Oman News Agency", 4, 4.0, ("omannews.gov.om",), ("oman news agency", "ona"), True),
    SourceProfile("reuters", "Reuters", 4, 4.0, ("reuters.com",), ("reuters",)),
    SourceProfile("ap", "Associated Press", 4, 4.0, ("apnews.com",), ("associated press", "the associated press", "ap news")),
    SourceProfile("bbc", "BBC", 3, 3.2, ("bbc.com", "bbc.co.uk"), ("bbc", "bbc news", "bbc.com")),
    SourceProfile("ft", "Financial Times", 3, 3.2, ("ft.com",), ("financial times",)),
    SourceProfile("bloomberg", "Bloomberg", 3, 3.2, ("bloomberg.com",), ("bloomberg",)),
    SourceProfile("guardian", "The Guardian", 3, 2.9, ("theguardian.com",), ("the guardian", "guardian")),
    SourceProfile("cnn", "CNN", 2, 2.5, ("cnn.com",), ("cnn",)),
    SourceProfile("cnbc", "CNBC", 2, 2.5, ("cnbc.com",), ("cnbc",)),
    SourceProfile("aljazeera", "Al Jazeera", 2, 2.4, ("aljazeera.com",), ("al jazeera",)),
    SourceProfile("euronews", "Euronews", 2, 2.2, ("euronews.com",), ("euronews",)),
)

PROFILE_BY_ALIAS: dict[str, SourceProfile] = {}
for _profile in SOURCE_PROFILES:
    PROFILE_BY_ALIAS[_profile.name.lower()] = _profile
    for _alias in _profile.aliases:
        PROFILE_BY_ALIAS[_alias.lower()] = _profile

OFFICIAL_ATTRIBUTIONS = (
    "ukmto",
    "uk maritime trade operations",
    "international maritime organization",
    " imo ",
    "marad",
    "u.s. maritime administration",
    "us maritime administration",
    "jmic",
    "joint maritime information center",
    "centcom",
    "u.s. navy",
    "us navy",
    "oman maritime",
)

# Señales operativas fuertes. Estas expresiones buscan hechos observables, no
# meras intenciones políticas.
OPEN_PATTERNS = (
    r"\bstrait of hormuz (?:is |remains |has remained )?(?:open|navigable)\b",
    r"\b(?:southern|safe|alternative) (?:route|corridor|lane) (?:through|in|across)? ?(?:the )?strait of hormuz (?:is |remains )?open\b",
    r"\b(?:shipping|maritime traffic|vessel traffic|traffic) (?:continues|continued|is continuing|resumes|resumed) (?:through|across|in) (?:the )?strait of hormuz\b",
    r"\bvessels? (?:continue|continued|are continuing) to transit (?:the )?strait of hormuz\b",
    r"\bships? (?:continue|continued|are continuing) to (?:pass|transit) (?:through )?(?:the )?strait of hormuz\b",
    r"\b(?:reopens|reopened|re-opens|re-opened) (?:the )?strait of hormuz\b",
    r"\b(?:the )?strait of hormuz (?:has )?(?:reopened|re-opened)\b",
    r"\bnot (?:fully )?closed\b.{0,90}\bstrait of hormuz\b",
    r"\bstrait of hormuz\b.{0,90}\bnot (?:fully )?closed\b",
    r"\bopen to (?:commercial |merchant )?(?:shipping|traffic|vessels)\b",
    r"\bstrait of hormuz\b.{0,120}\b(?:southern )?(?:route|corridor)\b.{0,60}\b(?:remains available|is available|available for transit)\b",
    r"\b(?:southern )?(?:route|corridor)\b.{0,60}\b(?:remains available|is available|available for transit)\b.{0,120}\bstrait of hormuz\b",
    r"\bsome (?:commercial |maritime )?(?:traffic|vessels?|shipping) (?:continues|continue)\b",
)

CLOSED_OPERATIONAL_PATTERNS = (
    r"\bstrait of hormuz (?:is |remains |has been )?closed to (?:all )?(?:shipping|maritime traffic|vessel traffic|commercial vessels)\b",
    r"\b(?:shipping|maritime traffic|vessel traffic|traffic) (?:has been |is |was )?(?:halted|stopped|suspended|shut down) (?:through|across|in) (?:the )?strait of hormuz\b",
    r"\bno (?:commercial )?vessels? (?:are |were )?(?:transiting|passing through) (?:the )?strait of hormuz\b",
    r"\b(?:passage|navigation) (?:through|across) (?:the )?strait of hormuz (?:is |was |remains )?(?:blocked|impossible|impassable)\b",
    r"\b(?:blockade|minefield|mines) (?:has |have )?(?:blocked|stopped|halted) (?:all )?(?:shipping|traffic|navigation)\b",
    r"\bcomplete operational closure of (?:the )?strait of hormuz\b",
    r"\b(?:ukmto|imo|marad|jmic).{0,120}\b(?:confirms?|confirmed|reports?|reported)\b.{0,100}\b(?:closed to shipping|traffic halted|no safe transit)\b",
    r"\bno safe transit through (?:the )?strait of hormuz\b",
)

DECLARATION_PATTERNS = (
    r"\biran (?:declares?|declared|announces?|announced|orders?|ordered) (?:the )?(?:closure|closing) of (?:the )?strait of hormuz\b",
    r"\biran (?:closes|closed|shuts|shut) (?:the )?strait of hormuz\b",
    r"\birgc (?:declares?|declared|announces?|announced|closes|closed) (?:the )?strait of hormuz\b",
    r"\bclosure of (?:the )?strait of hormuz (?:declared|announced|ordered)\b",
    r"\b(?:parliament|government) (?:votes?|voted|approves?|approved) to close (?:the )?strait of hormuz\b",
    r"\bpurported closure of (?:the )?strait of hormuz\b",
)

RISK_PATTERNS = (
    r"\b(?:mine|mines|minefield|mined waters)\b",
    r"\b(?:attack|attacks|attacked|strike|strikes|struck|projectile|explosion)\b",
    r"\b(?:critical|severe|substantial|high|elevated) (?:maritime )?(?:risk|threat level|threat)\b",
    r"\b(?:restrictions?|restricted|congestion|delays?|rerout(?:e|ed|ing))\b",
    r"\b(?:safe|alternative|southern) (?:route|corridor|lane)\b",
    r"\b(?:avoid|stay away from) iranian waters\b",
    r"\bnaval presence\b",
    r"\bdegraded navigation conditions\b",
    r"\bawait further instructions\b",
)

HYPOTHETICAL_PATTERNS = (
    r"\b(?:could|might|may|would|can) close\b",
    r"\b(?:threatens?|threatened|warning|warns?|warned) to close\b",
    r"\b(?:risk|fear|prospect|possibility|scenario) of (?:a )?closure\b",
    r"\bif (?:iran )?(?:closes|closed)\b",
    r"\bplans? to close\b",
    r"\bconsider(?:s|ed|ing)? closing\b",
    r"\burges? (?:iran )?to (?:close|reopen)\b",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    try:
        parsed = email.utils.parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return datetime.min.replace(tzinfo=timezone.utc)


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default.copy() if isinstance(default, dict) else list(default) if isinstance(default, list) else default


def atomic_write_text(path: Path, content: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def write_json(path: Path, payload: Any) -> None:
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def normalize_text(value: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    return re.sub(r"\s+", " ", text).strip()


def normalized_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", normalize_text(value).lower()).strip()


def source_profile(source_name: str = "", source_url: str = "", article_url: str = "") -> SourceProfile | None:
    for url in (source_url, article_url):
        host = urlparse(url).netloc.lower().removeprefix("www.")
        if not host:
            continue
        for profile in SOURCE_PROFILES:
            if any(host == domain or host.endswith("." + domain) for domain in profile.domains):
                return profile
    normalized = normalized_key(source_name)
    if normalized in PROFILE_BY_ALIAS:
        return PROFILE_BY_ALIAS[normalized]
    for alias, profile in PROFILE_BY_ALIAS.items():
        if alias and alias in normalized:
            return profile
    return None


def request_bytes(url: str, *, accept: str, attempts: int = 3, timeout: int = 30, max_bytes: int = 2_000_000) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": accept,
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read(max_bytes + 1)[:max_bytes]
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    assert last_error is not None
    raise last_error


def fetch_gdelt(hours: int, max_records: int) -> list[dict[str, Any]]:
    end = utc_now()
    start = end - timedelta(hours=hours)
    params = {
        "query": '"Strait of Hormuz"',
        "mode": "ArtList",
        "maxrecords": str(max_records),
        "format": "json",
        "sort": "DateDesc",
        "startdatetime": start.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end.strftime("%Y%m%d%H%M%S"),
    }
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode(params)
    raw = request_bytes(url, accept="application/json,text/plain;q=0.9,*/*;q=0.8")
    payload = json.loads(raw.decode("utf-8-sig"))
    articles: list[dict[str, Any]] = []
    for item in payload.get("articles", []):
        article_url = str(item.get("url", ""))
        profile = source_profile(article_url=article_url)
        if not profile:
            continue
        articles.append(
            {
                "title": normalize_text(str(item.get("title", ""))),
                "description": "",
                "url": article_url,
                "source_name": profile.name,
                "source_id": profile.source_id,
                "tier": profile.tier,
                "base_weight": profile.weight,
                "official": profile.official,
                "published_at": iso_z(parse_datetime(item.get("seendate"))),
                "provider": "GDELT",
            }
        )
    return articles


ENGLISH_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def date_from_result_text(value: str) -> datetime:
    """Extract a document date from search-result text without trusting crawl time."""
    text = normalize_text(value).lower()
    month_first = re.search(
        r"\b(" + "|".join(ENGLISH_MONTHS) + r")\s+(\d{1,2})(?:st|nd|rd|th)?[,]?\s+(20\d{2})\b",
        text,
    )
    day_first = re.search(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(" + "|".join(ENGLISH_MONTHS) + r")[,]?\s+(20\d{2})\b",
        text,
    )
    try:
        if month_first:
            return datetime(
                int(month_first.group(3)),
                ENGLISH_MONTHS[month_first.group(1)],
                int(month_first.group(2)),
                12,
                tzinfo=timezone.utc,
            )
        if day_first:
            return datetime(
                int(day_first.group(3)),
                ENGLISH_MONTHS[day_first.group(2)],
                int(day_first.group(1)),
                12,
                tzinfo=timezone.utc,
            )
    except ValueError:
        pass
    iso_match = re.search(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b", text)
    if iso_match:
        try:
            return datetime(
                int(iso_match.group(1)),
                int(iso_match.group(2)),
                int(iso_match.group(3)),
                12,
                tzinfo=timezone.utc,
            )
        except ValueError:
            pass
    return datetime.min.replace(tzinfo=timezone.utc)


def bing_web_feed_url(query: str) -> str:
    params = {"q": query, "format": "rss", "setlang": "en-US", "cc": "US"}
    return "https://www.bing.com/search?" + urllib.parse.urlencode(params)


def fetch_official_web_search(hours: int) -> list[dict[str, Any]]:
    """Search official maritime domains through Bing's web-result RSS view.

    This complements news aggregators: official advisories are often PDFs and may
    never appear as news articles. Results without an explicit document date are
    rejected so a newly crawled old PDF cannot masquerade as fresh evidence.
    """
    current_year = utc_now().year
    queries = (
        f'site:ukmto.org "Strait of Hormuz" (open OR "remains available" OR closed OR "no safe transit") {current_year}',
        f'site:maritime.dot.gov "Strait of Hormuz" (open OR closed OR advisory) {current_year}',
        f'site:imo.org "Strait of Hormuz" (open OR closed OR navigation) {current_year}',
        f'site:combinedmaritimeforces.com "Strait of Hormuz" (open OR closed OR transit) {current_year}',
    )
    cutoff = utc_now() - timedelta(hours=hours + 12)
    articles: list[dict[str, Any]] = []
    errors: list[Exception] = []
    for query in queries:
        try:
            raw = request_bytes(
                bing_web_feed_url(query),
                accept="application/rss+xml,application/xml,text/xml;q=0.9,*/*;q=0.8",
                attempts=2,
                timeout=25,
            )
            root = ET.fromstring(raw)
        except (urllib.error.URLError, TimeoutError, OSError, ET.ParseError) as exc:
            errors.append(exc)
            continue
        for item in root.findall("./channel/item"):
            title = normalize_text(item.findtext("title") or "")
            description = normalize_text(item.findtext("description") or "")
            link = normalize_text(item.findtext("link") or "")
            profile = source_profile(article_url=link)
            if not profile or not profile.official:
                continue
            if "strait of hormuz" not in f"{title} {description}".lower():
                continue
            document_date = date_from_result_text(f"{title}. {description}")
            if document_date == datetime.min.replace(tzinfo=timezone.utc):
                # Some feeds expose a true publication date. Use it only when it
                # is plausible and not merely today's crawl timestamp.
                published = parse_datetime(item.findtext("pubDate") or "")
                if published < cutoff or published > utc_now() + timedelta(hours=3):
                    continue
                document_date = published
            if document_date < cutoff:
                continue
            articles.append(
                {
                    "title": title,
                    "description": description,
                    "url": link,
                    "source_name": profile.name,
                    "source_id": profile.source_id,
                    "tier": profile.tier,
                    "base_weight": profile.weight,
                    "official": True,
                    "published_at": iso_z(document_date),
                    "provider": "Bing official web RSS",
                }
            )
    if not articles and len(errors) == len(queries):
        raise errors[-1]
    return articles


def google_news_feed_url(query: str) -> str:
    params = {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)


def fetch_google_news(hours: int) -> list[dict[str, Any]]:
    days = max(1, math.ceil(hours / 24))
    queries = (
        f'"Strait of Hormuz" (open OR reopened OR "remains open" OR "shipping continues" OR "traffic resumes") when:{days}d',
        f'"Strait of Hormuz" (closed OR closure OR blocked OR "traffic halted" OR "no safe transit") when:{days}d',
        f'"Strait of Hormuz" (restrictions OR mines OR attacks OR corridor OR congestion) when:{days}d',
        f'"Strait of Hormuz" (UKMTO OR IMO OR MARAD OR JMIC) when:{days}d',
    )
    articles: list[dict[str, Any]] = []
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
            title = normalize_text(item.findtext("title") or "")
            description = normalize_text(item.findtext("description") or "")
            link = normalize_text(item.findtext("link") or "")
            published = normalize_text(item.findtext("pubDate") or "")
            source_node = item.find("source")
            source_name = normalize_text(source_node.text or "") if source_node is not None else ""
            source_url = source_node.attrib.get("url", "") if source_node is not None else ""
            profile = source_profile(source_name, source_url, link)
            if not profile:
                continue
            # Google News suele repetir el título dentro de description; no aporta valor.
            if normalized_key(description) == normalized_key(title) or len(description) < 20:
                description = ""
            articles.append(
                {
                    "title": title,
                    "description": description,
                    "url": link,
                    "source_name": profile.name,
                    "source_id": profile.source_id,
                    "tier": profile.tier,
                    "base_weight": profile.weight,
                    "official": profile.official,
                    "published_at": iso_z(parse_datetime(published)),
                    "provider": "Google News RSS",
                }
            )
    if not articles and len(errors) == len(queries):
        raise errors[-1]
    return articles


def extract_meta_description(raw: bytes) -> tuple[str, str | None]:
    text = raw.decode("utf-8", errors="ignore")
    patterns = (
        r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:description["\']',
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
    )
    description = ""
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            description = normalize_text(match.group(1))
            break
    published_match = re.search(
        r'<meta[^>]+(?:property|name)=["\'](?:article:published_time|datePublished)["\'][^>]+content=["\']([^"\']+)',
        text,
        flags=re.IGNORECASE,
    )
    return description[:700], normalize_text(published_match.group(1)) if published_match else None


def enrich_articles(articles: list[dict[str, Any]], limit: int) -> None:
    candidates = sorted(articles, key=lambda item: parse_datetime(item["published_at"]), reverse=True)
    used = 0
    seen_urls: set[str] = set()
    for article in candidates:
        if used >= limit:
            break
        url = article.get("url", "")
        host = urlparse(url).netloc.lower()
        if not url or url in seen_urls or "news.google.com" in host:
            continue
        seen_urls.add(url)
        if article.get("description") and len(article["description"]) > 80:
            continue
        try:
            raw = request_bytes(url, accept="text/html,application/xhtml+xml;q=0.9,*/*;q=0.7", attempts=1, timeout=12)
            description, published = extract_meta_description(raw)
            if description:
                article["description"] = description
            if published and parse_datetime(published) > datetime.min.replace(tzinfo=timezone.utc):
                article["published_at"] = iso_z(parse_datetime(published))
        except Exception:
            pass
        used += 1


def freshness_factor(published_at: str, now: datetime) -> float:
    age_hours = max(0.0, (now - parse_datetime(published_at)).total_seconds() / 3600)
    if age_hours <= 6:
        return 1.0
    if age_hours <= 18:
        return 0.9
    if age_hours <= 36:
        return 0.75
    if age_hours <= 72:
        return 0.55
    return 0.35


def contains_official_attribution(text: str) -> bool:
    padded = f" {text.lower()} "
    return any(term in padded for term in OFFICIAL_ATTRIBUTIONS)


def classify_text(title: str, description: str = "") -> set[str]:
    text = normalize_text(f"{title}. {description}").lower()
    signals: set[str] = set()
    hypothetical = any(re.search(pattern, text) for pattern in HYPOTHETICAL_PATTERNS)

    if any(re.search(pattern, text) for pattern in OPEN_PATTERNS):
        signals.add("OPEN_OPERATIONAL")
    if any(re.search(pattern, text) for pattern in CLOSED_OPERATIONAL_PATTERNS):
        signals.add("CLOSED_OPERATIONAL")
    if any(re.search(pattern, text) for pattern in DECLARATION_PATTERNS) and not hypothetical:
        signals.add("CLOSURE_DECLARED")
    if any(re.search(pattern, text) for pattern in RISK_PATTERNS):
        signals.add("RISK_RESTRICTION")

    # Un titular genérico como "Iran closes..." es una declaración política,
    # no una confirmación de que todo el tráfico se haya detenido.
    if "CLOSURE_DECLARED" in signals and "CLOSED_OPERATIONAL" in signals:
        strong_operational_terms = (
            "closed to shipping",
            "traffic halted",
            "traffic stopped",
            "no vessels",
            "no safe transit",
            "passage blocked",
            "impassable",
        )
        if not any(term in text for term in strong_operational_terms):
            signals.discard("CLOSED_OPERATIONAL")

    return signals


def deduplicate_articles(articles: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(articles, key=lambda item: parse_datetime(item.get("published_at")), reverse=True)
    result: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    seen_source_title: set[tuple[str, str]] = set()
    for article in ordered:
        key = normalized_key(article.get("title", ""))
        if not key:
            continue
        source_key = (article.get("source_id", ""), key)
        if source_key in seen_source_title:
            continue
        # Titulares idénticos sindicados cuentan una sola vez: evita inflar el
        # consenso con la misma pieza republicada.
        if key in seen_titles:
            continue
        seen_source_title.add(source_key)
        seen_titles.add(key)
        result.append(article)
    return result


def evidence_from_articles(articles: list[dict[str, Any]], now: datetime, cutoff: datetime) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for article in deduplicate_articles(articles):
        published = parse_datetime(article.get("published_at"))
        if published < cutoff:
            continue
        signals = classify_text(article.get("title", ""), article.get("description", ""))
        if not signals:
            continue
        attribution = contains_official_attribution(
            f"{article.get('title', '')} {article.get('description', '')}"
        )
        base = float(article.get("base_weight", 2.0))
        bonus = 1.0 if attribution and not article.get("official") else 0.0
        score = round((base + bonus) * freshness_factor(article.get("published_at", ""), now), 3)
        for signal in sorted(signals):
            evidence.append(
                {
                    "signal": signal,
                    "title": article.get("title", ""),
                    "description": article.get("description", "")[:500],
                    "source_name": article.get("source_name", ""),
                    "source_id": article.get("source_id", ""),
                    "source_url": article.get("url", ""),
                    "published_at": iso_z(published),
                    "provider": article.get("provider", ""),
                    "tier": int(article.get("tier", 1)),
                    "official": bool(article.get("official")),
                    "official_attribution": attribution,
                    "score": score,
                }
            )
    return evidence


def select_unique_evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    sources: set[str] = set()
    for item in sorted(items, key=lambda x: (x["score"], parse_datetime(x["published_at"])), reverse=True):
        source_id = item["source_id"]
        if source_id in sources:
            continue
        sources.add(source_id)
        selected.append(item)
    return selected


def confirmed(items: list[dict[str, Any]]) -> bool:
    unique = select_unique_evidence(items)
    if not unique:
        return False
    total = sum(item["score"] for item in unique)
    if any(item["official"] and item["score"] >= 3.0 for item in unique):
        return True
    if any(item["official_attribution"] and item["tier"] >= 3 for item in unique) and total >= 4.2:
        return True
    return len(unique) >= 2 and total >= 6.0 and max(item["tier"] for item in unique) >= 3


def confidence_for(items: list[dict[str, Any]], contradictory: bool = False) -> str:
    unique = select_unique_evidence(items)
    total = sum(item["score"] for item in unique)
    if not unique:
        return "BAJA"
    if contradictory:
        return "MEDIA" if len(unique) >= 3 and total >= 10 else "BAJA"
    if any(item["official"] for item in unique) or (len(unique) >= 3 and total >= 10):
        return "ALTA"
    if len(unique) >= 2 or any(item["official_attribution"] for item in unique):
        return "MEDIA"
    return "BAJA"


def newest_time(items: list[dict[str, Any]]) -> datetime:
    return max((parse_datetime(item["published_at"]) for item in items), default=datetime.min.replace(tzinfo=timezone.utc))


def previous_is_carryable(previous: dict[str, Any], now: datetime, carry_hours: int) -> bool:
    if previous.get("engine_version") != ENGINE_VERSION:
        return False
    if previous.get("status") not in {"ABIERTO", "CERRADO"}:
        return False
    last_valid = previous.get("last_valid_confirmation") or {}
    at = parse_datetime(last_valid.get("at"))
    return at > datetime.min.replace(tzinfo=timezone.utc) and now - at <= timedelta(hours=carry_hours)


def decision_summaries(status: str, operational: str) -> tuple[str, str]:
    messages = {
        ("ABIERTO", "OPEN_NORMAL"): (
            "Hay evidencia reciente de que el tráfico marítimo continúa o de que el paso está operativo.",
            "Recent evidence indicates that maritime traffic continues or that the passage is operational.",
        ),
        ("ABIERTO", "OPEN_RESTRICTED"): (
            "Hay evidencia reciente de una ruta operativa, pero persisten restricciones, incidentes o un riesgo marítimo elevado.",
            "Recent evidence indicates an operational route, but restrictions, incidents or elevated maritime risk remain.",
        ),
        ("CERRADO", "CLOSED_CONFIRMED"): (
            "La interrupción efectiva del tráfico está confirmada por una fuente operativa o por consenso independiente suficiente.",
            "An effective interruption of traffic is confirmed by an operational source or sufficient independent consensus.",
        ),
        ("INCIERTO", "CLOSURE_DECLARED_UNCONFIRMED"): (
            "Existe una declaración de cierre, pero no hay confirmación suficiente de que todo el tráfico marítimo esté detenido.",
            "A closure has been declared, but there is not enough confirmation that all maritime traffic has stopped.",
        ),
        ("INCIERTO", "HIGH_RISK_UNCONFIRMED"): (
            "Las fuentes describen riesgo elevado o restricciones, pero no permiten confirmar de forma fiable si el paso está abierto o cerrado.",
            "Sources describe elevated risk or restrictions, but do not reliably confirm whether the passage is open or closed.",
        ),
        ("INCIERTO", "CONTRADICTORY"): (
            "Hay señales operativas recientes contradictorias; se mantiene un estado prudente hasta disponer de una confirmación más sólida.",
            "Recent operational signals conflict; a cautious status is kept until stronger confirmation is available.",
        ),
        ("INCIERTO", "NO_RECENT_CONFIRMATION"): (
            "No se ha encontrado una confirmación operativa reciente y suficientemente sólida.",
            "No sufficiently strong and recent operational confirmation has been found.",
        ),
    }
    return messages.get(
        (status, operational),
        (
            "El estado requiere revisión adicional.",
            "The status requires additional review.",
        ),
    )


def analyze_evidence(
    evidence: list[dict[str, Any]],
    previous: dict[str, Any],
    now: datetime,
    carry_hours: int,
) -> dict[str, Any]:
    groups = {
        signal: [item for item in evidence if item["signal"] == signal]
        for signal in ("OPEN_OPERATIONAL", "CLOSED_OPERATIONAL", "CLOSURE_DECLARED", "RISK_RESTRICTION")
    }
    open_items = groups["OPEN_OPERATIONAL"]
    closed_items = groups["CLOSED_OPERATIONAL"]
    declared_items = groups["CLOSURE_DECLARED"]
    risk_items = groups["RISK_RESTRICTION"]
    open_ok = confirmed(open_items)
    closed_ok = confirmed(closed_items)

    status = "INCIERTO"
    operational = "NO_RECENT_CONFIRMATION"
    confidence = "BAJA"
    chosen: list[dict[str, Any]] = []

    if open_ok and closed_ok:
        open_time = newest_time(open_items)
        closed_time = newest_time(closed_items)
        open_score = sum(item["score"] for item in select_unique_evidence(open_items))
        closed_score = sum(item["score"] for item in select_unique_evidence(closed_items))
        if open_time - closed_time >= timedelta(hours=8) and open_score >= closed_score * 1.15:
            status = "ABIERTO"
            operational = "OPEN_RESTRICTED" if risk_items or declared_items else "OPEN_NORMAL"
            chosen = open_items + risk_items + declared_items
            confidence = confidence_for(open_items, contradictory=True)
        elif closed_time - open_time >= timedelta(hours=8) and closed_score >= open_score * 1.15:
            status = "CERRADO"
            operational = "CLOSED_CONFIRMED"
            chosen = closed_items
            confidence = confidence_for(closed_items, contradictory=True)
        else:
            operational = "CONTRADICTORY"
            chosen = open_items + closed_items
            confidence = "BAJA"
    elif closed_ok:
        status = "CERRADO"
        operational = "CLOSED_CONFIRMED"
        chosen = closed_items
        confidence = confidence_for(closed_items)
    elif open_ok:
        status = "ABIERTO"
        operational = "OPEN_RESTRICTED" if risk_items or declared_items else "OPEN_NORMAL"
        chosen = open_items + risk_items + declared_items
        confidence = confidence_for(open_items)
    elif declared_items:
        operational = "CLOSURE_DECLARED_UNCONFIRMED"
        chosen = declared_items + risk_items
        confidence = confidence_for(declared_items)
    elif risk_items:
        if previous_is_carryable(previous, now, carry_hours):
            status = previous["status"]
            operational = "OPEN_RESTRICTED" if status == "ABIERTO" else "HIGH_RISK_UNCONFIRMED"
            confidence = "BAJA"
            chosen = risk_items
        else:
            operational = "HIGH_RISK_UNCONFIRMED"
            chosen = risk_items
            confidence = confidence_for(risk_items)
    elif previous_is_carryable(previous, now, carry_hours):
        status = previous["status"]
        operational = previous.get("operational_status", "NO_RECENT_CONFIRMATION")
        confidence = "BAJA"
        chosen = []

    summary_es, summary_en = decision_summaries(status, operational)
    top = select_unique_evidence(chosen)[:6]
    return {
        "status": status,
        "operational_status": operational,
        "confidence": confidence,
        "summary_es": summary_es,
        "summary_en": summary_en,
        "evidence": top,
        "scores": {
            "open": round(sum(item["score"] for item in select_unique_evidence(open_items)), 3),
            "closed": round(sum(item["score"] for item in select_unique_evidence(closed_items)), 3),
            "declared": round(sum(item["score"] for item in select_unique_evidence(declared_items)), 3),
            "risk": round(sum(item["score"] for item in select_unique_evidence(risk_items)), 3),
        },
        "independent_sources": {
            "open": len(select_unique_evidence(open_items)),
            "closed": len(select_unique_evidence(closed_items)),
            "declared": len(select_unique_evidence(declared_items)),
            "risk": len(select_unique_evidence(risk_items)),
        },
    }


def manual_override_payload(config: dict[str, Any], previous: dict[str, Any], now: datetime) -> dict[str, Any] | None:
    override = config.get("manual_override")
    if isinstance(override, str) and override in VALID_STATUS:
        override = {"status": override}
    if not isinstance(override, dict):
        return None
    status = override.get("status")
    if status not in VALID_STATUS:
        return None
    expires = parse_datetime(override.get("expires_at"))
    if override.get("expires_at") and expires <= now:
        return None
    operational = override.get("operational_status")
    if operational not in VALID_OPERATIONAL:
        operational = "MANUAL_OVERRIDE"
    confidence = override.get("confidence") if override.get("confidence") in VALID_CONFIDENCE else "ALTA"
    reason_es = normalize_text(override.get("reason_es") or "Estado fijado manualmente por el responsable del sitio.")
    reason_en = normalize_text(override.get("reason_en") or "Status manually set by the site operator.")
    return finalize_payload(
        previous=previous,
        now=now,
        status=status,
        operational=operational,
        confidence=confidence,
        summary_es=reason_es,
        summary_en=reason_en,
        evidence=[],
        verification_ok=True,
        diagnostics={"manual_override": True},
    )


def clean_public_evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    public: list[dict[str, Any]] = []
    for item in items[:6]:
        public.append(
            {
                "signal": item.get("signal"),
                "title": item.get("title"),
                "source_name": item.get("source_name"),
                "source_url": item.get("source_url"),
                "published_at": item.get("published_at"),
                "tier": item.get("tier"),
                "official": item.get("official", False),
            }
        )
    return public


def finalize_payload(
    *,
    previous: dict[str, Any],
    now: datetime,
    status: str,
    operational: str,
    confidence: str,
    summary_es: str,
    summary_en: str,
    evidence: list[dict[str, Any]],
    verification_ok: bool,
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    if status not in VALID_STATUS:
        status = "INCIERTO"
    if operational not in VALID_OPERATIONAL:
        operational = "NO_RECENT_CONFIRMATION"
    if confidence not in VALID_CONFIDENCE:
        confidence = "BAJA"

    now_iso = iso_z(now)
    meaningful_changed = (
        previous.get("status") != status
        or previous.get("operational_status") != operational
    )
    last_change_at = now_iso if meaningful_changed else previous.get("last_change_at", now_iso)

    last_valid = previous.get("last_valid_confirmation") if isinstance(previous.get("last_valid_confirmation"), dict) else None
    if status in {"ABIERTO", "CERRADO"} and evidence:
        main = evidence[0]
        last_valid = {
            "status": status,
            "at": main.get("published_at") or now_iso,
            "source_name": main.get("source_name"),
            "source_url": main.get("source_url"),
            "title": main.get("title"),
        }

    last_success_at = now_iso if verification_ok else previous.get("last_success_at")
    stale = not verification_ok
    if last_success_at:
        stale = stale or now - parse_datetime(last_success_at) > timedelta(hours=4)

    return {
        "engine_version": ENGINE_VERSION,
        "status": status,
        "operational_status": operational,
        "operational_label_es": OPERATIONAL_LABELS[operational][0],
        "operational_label_en": OPERATIONAL_LABELS[operational][1],
        "confidence": confidence,
        "checked_at": now_iso,
        "last_success_at": last_success_at,
        "last_change_at": last_change_at,
        "verification_ok": verification_ok,
        "stale": stale,
        "summary_es": summary_es,
        "summary_en": summary_en,
        "last_valid_confirmation": last_valid,
        "evidence": clean_public_evidence(evidence),
        "diagnostics": diagnostics,
    }


def network_failure_payload(previous: dict[str, Any], now: datetime, errors: list[str]) -> dict[str, Any]:
    if previous.get("engine_version") == ENGINE_VERSION and previous.get("status") in VALID_STATUS:
        payload = dict(previous)
        payload.update(
            {
                "checked_at": iso_z(now),
                "verification_ok": False,
                "stale": True,
                "diagnostics": {"providers_failed": errors, "network_failure": True},
            }
        )
        return payload
    summary_es = "No se pudo completar la primera comprobación automática. El estado permanece sin confirmar."
    summary_en = "The first automatic check could not be completed. The status remains unconfirmed."
    return finalize_payload(
        previous=previous,
        now=now,
        status="INCIERTO",
        operational="NO_RECENT_CONFIRMATION",
        confidence="BAJA",
        summary_es=summary_es,
        summary_en=summary_en,
        evidence=[],
        verification_ok=False,
        diagnostics={"providers_failed": errors, "network_failure": True},
    )


def event_from_payload(payload: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    evidence = payload.get("evidence") or []
    main = evidence[0] if evidence else {}
    digest_source = f"{payload.get('last_change_at')}|{payload.get('status')}|{payload.get('operational_status')}"
    return {
        "id": hashlib.sha256(digest_source.encode("utf-8")).hexdigest()[:16],
        "at": payload.get("last_change_at") or payload.get("checked_at"),
        "previous_status": previous.get("status"),
        "status": payload.get("status"),
        "operational_status": payload.get("operational_status"),
        "operational_label_es": payload.get("operational_label_es"),
        "operational_label_en": payload.get("operational_label_en"),
        "confidence": payload.get("confidence"),
        "summary_es": payload.get("summary_es"),
        "summary_en": payload.get("summary_en"),
        "source_name": main.get("source_name"),
        "source_url": main.get("source_url"),
        "source_title": main.get("title"),
    }


def update_history(payload: dict[str, Any], previous: dict[str, Any], max_events: int) -> tuple[list[dict[str, Any]], bool]:
    history = load_json(HISTORY_FILE, [])
    if not isinstance(history, list):
        history = []
    meaningful = (
        not history
        or previous.get("engine_version") != ENGINE_VERSION
        or previous.get("status") != payload.get("status")
        or previous.get("operational_status") != payload.get("operational_status")
    )
    if meaningful and payload.get("verification_ok"):
        event = event_from_payload(payload, previous)
        if not history or history[0].get("id") != event["id"]:
            history.insert(0, event)
            history = history[:max_events]
            write_json(HISTORY_FILE, history)
            return history, True
    if not HISTORY_FILE.exists():
        write_json(HISTORY_FILE, history)
    return history, False


def format_es(value: Any, include_time: bool = True) -> str:
    dt = parse_datetime(value)
    if dt == datetime.min.replace(tzinfo=timezone.utc):
        return "fecha no disponible"
    local = dt.astimezone(ZoneInfo("Europe/Madrid"))
    base = f"{local.day} de {MONTHS_ES[local.month - 1]} de {local.year}"
    return f"{base}, {local:%H:%M}" if include_time else base


def format_en(value: Any, include_time: bool = True) -> str:
    dt = parse_datetime(value)
    if dt == datetime.min.replace(tzinfo=timezone.utc):
        return "date unavailable"
    local = dt.astimezone(ZoneInfo("UTC"))
    month = local.strftime("%B")
    base = f"{month} {local.day}, {local.year}"
    return f"{base}, {local:%H:%M} UTC" if include_time else base


def status_css(status: str) -> str:
    return {"ABIERTO": "is-open", "CERRADO": "is-closed", "INCIERTO": "is-uncertain"}.get(status, "is-uncertain")


def confidence_css(confidence: str) -> str:
    return {"ALTA": "confidence-high", "MEDIA": "confidence-medium", "BAJA": "confidence-low"}.get(confidence, "confidence-low")


def evidence_html(payload: dict[str, Any], lang: str) -> str:
    items = payload.get("evidence") or []
    if not items:
        empty = "No hay pruebas públicas suficientes para mostrar." if lang == "es" else "There is not enough public evidence to display."
        return f'<p class="empty-state">{html.escape(empty)}</p>'
    signal_labels_es = {
        "OPEN_OPERATIONAL": "Tránsito operativo",
        "CLOSED_OPERATIONAL": "Interrupción operativa",
        "CLOSURE_DECLARED": "Declaración de cierre",
        "RISK_RESTRICTION": "Riesgo o restricción",
    }
    signal_labels_en = {
        "OPEN_OPERATIONAL": "Operational transit",
        "CLOSED_OPERATIONAL": "Operational interruption",
        "CLOSURE_DECLARED": "Closure declaration",
        "RISK_RESTRICTION": "Risk or restriction",
    }
    rows: list[str] = []
    for item in items[:4]:
        title = html.escape(str(item.get("title") or ""))
        source = html.escape(str(item.get("source_name") or "Fuente"))
        url = html.escape(str(item.get("source_url") or "#"), quote=True)
        date = format_es(item.get("published_at")) if lang == "es" else format_en(item.get("published_at"))
        label = (signal_labels_es if lang == "es" else signal_labels_en).get(item.get("signal"), "Signal")
        official = " · oficial" if lang == "es" and item.get("official") else " · official" if item.get("official") else ""
        rows.append(
            f'''<article class="evidence-card">
              <div class="evidence-meta"><span>{html.escape(label)}{official}</span><time>{html.escape(date)}</time></div>
              <h3><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></h3>
              <p>{source}</p>
            </article>'''
        )
    return "\n".join(rows)


def snapshot_html(payload: dict[str, Any], lang: str) -> str:
    status = payload.get("status", "INCIERTO")
    labels = {"es": {"ABIERTO": "ABIERTO", "CERRADO": "CERRADO", "INCIERTO": "INCIERTO"}, "en": {"ABIERTO": "OPEN", "CERRADO": "CLOSED", "INCIERTO": "UNCERTAIN"}}
    checked_label = "Última comprobación" if lang == "es" else "Last check"
    valid_label = "Última confirmación válida" if lang == "es" else "Last valid confirmation"
    confidence_label = "Confianza" if lang == "es" else "Confidence"
    confidence_value = {"es": {"ALTA": "Alta", "MEDIA": "Media", "BAJA": "Baja"}, "en": {"ALTA": "High", "MEDIA": "Medium", "BAJA": "Low"}}[lang].get(payload.get("confidence"), "Low")
    checked = format_es(payload.get("checked_at")) if lang == "es" else format_en(payload.get("checked_at"))
    last_valid = payload.get("last_valid_confirmation") or {}
    last_valid_text = (
        format_es(last_valid.get("at")) if lang == "es" else format_en(last_valid.get("at"))
    ) if last_valid else ("No disponible" if lang == "es" else "Unavailable")
    summary = payload.get("summary_es" if lang == "es" else "summary_en") or ""
    operational = payload.get("operational_label_es" if lang == "es" else "operational_label_en") or ""
    if payload.get("stale"):
        if last_valid:
            stale_note = "<span class=\"stale-note\">Comprobación incompleta: se conserva el último estado válido.</span>" if lang == "es" else "<span class=\"stale-note\">Incomplete check: the last valid status is retained.</span>"
        else:
            stale_note = "<span class=\"stale-note\">Pendiente de la primera comprobación automática.</span>" if lang == "es" else "<span class=\"stale-note\">Awaiting the first automatic check.</span>"
    else:
        stale_note = ""
    return f'''<!-- STATUS_SNAPSHOT_START -->
      <div id="statusHero" class="status-hero {status_css(status)}" data-status="{status}">
        <div class="status-kicker"><span class="status-dot" aria-hidden="true"></span><span id="operationalLabel">{html.escape(operational)}</span></div>
        <div class="status-word" id="statusWord" aria-live="polite">{labels[lang].get(status, labels[lang]["INCIERTO"])}</div>
        <p class="status-summary" id="statusSummary">{html.escape(str(summary))}</p>
        {stale_note}
      </div>
      <div class="status-facts">
        <div><span>{checked_label}</span><strong id="checkedAt">{html.escape(checked)}</strong></div>
        <div><span>{confidence_label}</span><strong id="confidence" class="{confidence_css(payload.get('confidence', 'BAJA'))}">{html.escape(confidence_value)}</strong></div>
        <div><span>{valid_label}</span><strong id="lastValidAt">{html.escape(last_valid_text)}</strong></div>
      </div>
      <div class="evidence-section">
        <div class="section-heading">
          <h2>{"Evidencias recientes" if lang == "es" else "Recent evidence"}</h2>
          <p>{"Se muestran señales independientes y relevantes, no una lista completa de noticias." if lang == "es" else "Independent, relevant signals are shown rather than a complete news list."}</p>
        </div>
        <div id="evidenceList" class="evidence-grid">
          {evidence_html(payload, lang)}
        </div>
      </div>
      <!-- STATUS_SNAPSHOT_END -->'''


def replace_marker(path: Path, marker: str, replacement: str) -> None:
    try:
        document = path.read_text(encoding="utf-8")
    except OSError:
        return
    start = f"<!-- {marker}_START -->"
    end = f"<!-- {marker}_END -->"
    pattern = re.escape(start) + r".*?" + re.escape(end)
    updated, count = re.subn(pattern, replacement, document, count=1, flags=re.DOTALL)
    if count and updated != document:
        atomic_write_text(path, updated)


def history_snapshot(history: list[dict[str, Any]], lang: str, limit: int = 20) -> str:
    title_none = "Todavía no hay cambios registrados." if lang == "es" else "No changes have been recorded yet."
    if not history:
        body = f'<p class="empty-state">{title_none}</p>'
    else:
        rows: list[str] = []
        labels = {"es": {"ABIERTO": "Abierto", "CERRADO": "Cerrado", "INCIERTO": "Incierto"}, "en": {"ABIERTO": "Open", "CERRADO": "Closed", "INCIERTO": "Uncertain"}}
        for event in history[:limit]:
            status = event.get("status", "INCIERTO")
            date = format_es(event.get("at")) if lang == "es" else format_en(event.get("at"))
            summary = event.get("summary_es" if lang == "es" else "summary_en") or ""
            op = event.get("operational_label_es" if lang == "es" else "operational_label_en") or ""
            source = event.get("source_name")
            source_url = event.get("source_url")
            source_html = ""
            if source and source_url:
                source_label = "Fuente" if lang == "es" else "Source"
                source_html = f'<a href="{html.escape(str(source_url), quote=True)}" target="_blank" rel="noopener noreferrer">{source_label}: {html.escape(str(source))}</a>'
            rows.append(
                f'''<article class="timeline-item {status_css(status)}">
                  <div class="timeline-marker" aria-hidden="true"></div>
                  <div class="timeline-content">
                    <div class="timeline-head"><strong>{labels[lang].get(status, labels[lang]["INCIERTO"])}</strong><time>{html.escape(date)}</time></div>
                    <p class="timeline-operation">{html.escape(str(op))}</p>
                    <p>{html.escape(str(summary))}</p>
                    {source_html}
                  </div>
                </article>'''
            )
        body = "\n".join(rows)
    return f'''<!-- HISTORY_SNAPSHOT_START -->
      <div id="historyTimeline" class="timeline">{body}</div>
      <!-- HISTORY_SNAPSHOT_END -->'''


def update_html(payload: dict[str, Any], history: list[dict[str, Any]]) -> None:
    replace_marker(INDEX_ES, "STATUS_SNAPSHOT", snapshot_html(payload, "es"))
    replace_marker(INDEX_EN, "STATUS_SNAPSHOT", snapshot_html(payload, "en"))
    replace_marker(HISTORY_ES, "HISTORY_SNAPSHOT", history_snapshot(history, "es"))
    replace_marker(HISTORY_EN, "HISTORY_SNAPSHOT", history_snapshot(history, "en"))


def xml_escape(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def build_feed(history: list[dict[str, Any]], base_url: str) -> str:
    updated = history[0].get("at") if history else iso_z(utc_now())
    entries: list[str] = []
    for event in history[:50]:
        event_id = event.get("id") or hashlib.sha256(str(event).encode()).hexdigest()[:16]
        link = f"{base_url}historial.html#{event_id}"
        title = f"{event.get('status', 'INCIERTO')} · {event.get('operational_label_es', '')}"
        entries.append(
            f'''  <entry>
    <id>{xml_escape(base_url + 'event/' + event_id)}</id>
    <title>{xml_escape(title)}</title>
    <link href="{xml_escape(link)}" />
    <updated>{xml_escape(event.get('at'))}</updated>
    <summary>{xml_escape(event.get('summary_es'))}</summary>
  </entry>'''
        )
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="es">
  <id>{xml_escape(base_url + 'feed.xml')}</id>
  <title>Alertas del estado del estrecho de Ormuz</title>
  <subtitle>Cambios registrados en el estado operativo del estrecho de Ormuz.</subtitle>
  <link href="{xml_escape(base_url + 'feed.xml')}" rel="self" />
  <link href="{xml_escape(base_url)}" />
  <updated>{xml_escape(updated)}</updated>
{chr(10).join(entries)}
</feed>
'''



def build_sitemap(base_url: str, dynamic_lastmod: str) -> str:
    pages = (
        ("", dynamic_lastmod, "daily", "1.0"),
        ("en.html", dynamic_lastmod, "daily", "0.9"),
        ("historial.html", dynamic_lastmod, "daily", "0.9"),
        ("en-history.html", dynamic_lastmod, "daily", "0.8"),
        ("metodologia.html", "2026-07-12", "monthly", "0.8"),
        ("en-methodology.html", "2026-07-12", "monthly", "0.7"),
        ("importancia.html", "2026-07-12", "monthly", "0.8"),
        ("en-importance.html", "2026-07-12", "monthly", "0.7"),
        ("fuentes.html", "2026-07-12", "monthly", "0.7"),
        ("en-sources.html", "2026-07-12", "monthly", "0.6"),
        ("alertas.html", "2026-07-12", "monthly", "0.7"),
        ("en-alerts.html", "2026-07-12", "monthly", "0.6"),
        ("privacidad.html", "2026-07-12", "yearly", "0.3"),
        ("en-privacy.html", "2026-07-12", "yearly", "0.3"),
    )
    rows = []
    for path, lastmod, changefreq, priority in pages:
        rows.append(
            f"  <url>\n"
            f"    <loc>{xml_escape(base_url + path)}</loc>\n"
            f"    <lastmod>{lastmod}</lastmod>\n"
            f"    <changefreq>{changefreq}</changefreq>\n"
            f"    <priority>{priority}</priority>\n"
            f"  </url>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(rows)
        + '\n</urlset>\n'
    )

def write_change_file(previous: dict[str, Any], payload: dict[str, Any], history_changed: bool, config: dict[str, Any]) -> None:
    path_value = os.environ.get("CHANGE_FILE")
    if not path_value:
        return
    meaningful = (
        previous.get("status") != payload.get("status")
        or previous.get("operational_status") != payload.get("operational_status")
    ) and payload.get("verification_ok", False)
    base_url = str(config.get("base_url") or "").rstrip("/") + "/"
    data = {
        "meaningful_change": meaningful,
        "history_changed": history_changed,
        "previous_status": previous.get("status"),
        "status": payload.get("status"),
        "operational_status": payload.get("operational_status"),
        "confidence": payload.get("confidence"),
        "summary_es": payload.get("summary_es"),
        "summary_en": payload.get("summary_en"),
        "checked_at": payload.get("checked_at"),
        "base_url": base_url,
        "urls": [
            base_url,
            base_url + "en.html",
            base_url + "historial.html",
            base_url + "en-history.html",
            base_url + "feed.xml",
        ],
    }
    write_json(Path(path_value), data)


def run_update() -> int:
    now = utc_now()
    previous = load_json(STATUS_FILE, {})
    config = load_json(CONFIG_FILE, {})
    override = manual_override_payload(config, previous, now)
    if override:
        payload = override
        providers_ok: list[str] = ["manual_override"]
        providers_failed: list[str] = []
    else:
        hours = int(config.get("lookback_hours", 96))
        max_records = int(config.get("gdelt_max_records", 250))
        meta_limit = int(config.get("article_meta_fetch_limit", 12))
        carry_hours = int(config.get("carry_forward_hours", 18))
        articles: list[dict[str, Any]] = []
        providers_ok = []
        providers_failed = []
        for name, fetcher in (
            ("Official maritime web search", lambda: fetch_official_web_search(hours)),
            ("GDELT", lambda: fetch_gdelt(hours, max_records)),
            ("Google News RSS", lambda: fetch_google_news(hours)),
        ):
            try:
                fetched = fetcher()
                articles.extend(fetched)
                providers_ok.append(name)
                print(f"{name}: {len(fetched)} artículos aceptados.")
            except Exception as exc:
                message = f"{name}: {type(exc).__name__}: {exc}"
                providers_failed.append(message)
                print(message, file=sys.stderr)
        if not articles and not providers_ok:
            payload = network_failure_payload(previous, now, providers_failed)
        else:
            enrich_articles(articles, meta_limit)
            cutoff = now - timedelta(hours=hours + 2)
            evidence = evidence_from_articles(articles, now, cutoff)
            decision = analyze_evidence(evidence, previous, now, carry_hours)
            payload = finalize_payload(
                previous=previous,
                now=now,
                status=decision["status"],
                operational=decision["operational_status"],
                confidence=decision["confidence"],
                summary_es=decision["summary_es"],
                summary_en=decision["summary_en"],
                evidence=decision["evidence"],
                verification_ok=bool(providers_ok),
                diagnostics={
                    "providers_ok": providers_ok,
                    "providers_failed": providers_failed,
                    "scores": decision["scores"],
                    "independent_sources": decision["independent_sources"],
                    "articles_considered": len(articles),
                    "signals_considered": len(evidence),
                },
            )

    write_json(STATUS_FILE, payload)
    history, history_changed = update_history(payload, previous, int(config.get("history_max_events", 365)))
    base_url = str(config.get("base_url") or "https://elptowalter.github.io/estado-del-estrecho-de-Ormuz/")
    if not base_url.endswith("/"):
        base_url += "/"
    atomic_write_text(FEED_FILE, build_feed(history, base_url))
    atomic_write_text(SITEMAP_FILE, build_sitemap(base_url, str(payload.get("checked_at", ""))[:10]))
    update_html(payload, history)
    write_change_file(previous, payload, history_changed, config)

    if not payload.get("verification_ok"):
        print("::warning::La comprobación no se completó; se conserva el último estado válido.", file=sys.stderr)
    print(
        f"Resultado: {payload.get('status')} / {payload.get('operational_status')} / confianza {payload.get('confidence')}"
    )
    return 0


def demo_articles() -> list[dict[str, Any]]:
    now = utc_now()
    return [
        {
            "title": "UKMTO says a southern route through the Strait of Hormuz remains open",
            "description": "Mariners face congestion and mine risk, but vessels continue to transit the designated corridor.",
            "url": "https://www.ukmto.org/example",
            "source_name": "UKMTO",
            "source_id": "ukmto",
            "tier": 5,
            "base_weight": 5.0,
            "official": True,
            "published_at": iso_z(now - timedelta(hours=1)),
            "provider": "fixture",
        },
        {
            "title": "Iran declares closure of Strait of Hormuz",
            "description": "The announcement comes amid attacks and maritime restrictions.",
            "url": "https://www.reuters.com/example",
            "source_name": "Reuters",
            "source_id": "reuters",
            "tier": 4,
            "base_weight": 4.0,
            "official": False,
            "published_at": iso_z(now - timedelta(hours=2)),
            "provider": "fixture",
        },
    ]


def run_demo() -> int:
    now = utc_now()
    evidence = evidence_from_articles(demo_articles(), now, now - timedelta(hours=96))
    result = analyze_evidence(evidence, {}, now, 18)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Actualiza el estado del estrecho de Ormuz")
    parser.add_argument("--demo", action="store_true", help="Ejecuta un escenario local sin conexión")
    args = parser.parse_args()
    return run_demo() if args.demo else run_update()


if __name__ == "__main__":
    raise SystemExit(main())
