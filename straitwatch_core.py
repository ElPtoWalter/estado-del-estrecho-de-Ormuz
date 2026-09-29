#!/usr/bin/env python3
"""Shared Phase 1 primitives for StraitWatch.

The module is deliberately dependency-free.  It turns publisher records into
canonical sources, removes article duplicates, groups related coverage into
stable events and assigns an auditable verification status.  It never decides
the public operational state and it never calls an AI provider.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


SCHEMA_VERSION = 1
VERIFICATION_STATUSES = {
    "CONFIRMED_PRIMARY",
    "CONFIRMED_MULTI_SOURCE",
    "SINGLE_SOURCE",
    "DECLARATION_ONLY",
    "UNCONFIRMED",
    "CONFLICTING",
}
CLASSIFICATIONS = {
    "FACT",
    "OFFICIAL_NOTICE",
    "OPERATIONAL_SIGNAL",
    "DECLARATION",
    "ANALYSIS",
    "OPINION",
    "RUMOR",
    "UNCONFIRMED",
}

PUBLIC_SIGNAL_LABELS = {
    "OPEN_OPERATIONAL": ("Paso operativo confirmado", "Operational passage confirmed"),
    "CLOSED_OPERATIONAL": ("Interrupción operativa", "Operational interruption"),
    "CLOSURE_DECLARED": ("Declaración de cierre", "Closure declaration"),
    "RISK_RESTRICTION": ("Riesgo o restricción", "Risk or restriction"),
    "TRANSIT_CONFIRMED": ("Tránsito confirmado", "Confirmed transit"),
    "TRAFFIC_PRESENT": ("Tráfico observado", "Observed traffic"),
    "TRAFFIC_REDUCED": ("Tráfico reducido", "Reduced traffic"),
    "TRAFFIC_SEVERELY_REDUCED": ("Tráfico muy reducido", "Severely reduced traffic"),
    "TRAFFIC_NORMAL": ("Tráfico próximo a normalidad", "Traffic near normal"),
    "CLOSURE_EFFECTIVE": ("Interrupción efectiva", "Effective interruption"),
    "FORMAL_CLOSURE_CLAIM": ("Declaración de cierre", "Closure declaration"),
    "ACCESS_RESTRICTED": ("Acceso restringido", "Restricted access"),
    "NEUTRAL_TRANSIT_PERMITTED": ("Tránsito neutral permitido", "Neutral transit permitted"),
    "RISK_SEVERE": ("Riesgo severo", "Severe risk"),
    "RISK_ELEVATED": ("Riesgo elevado", "Elevated risk"),
}

_TRACKING_QUERY_KEYS = {
    "fbclid", "gclid", "mc_cid", "mc_eid", "oc", "ref", "source",
    "utm_campaign", "utm_content", "utm_medium", "utm_source", "utm_term",
}
_TITLE_SUFFIX_RE = re.compile(
    r"\s+(?:-|–|—|\||:)\s+(?:www\.)?[a-z0-9][a-z0-9 .&'’_-]*\.(?:com|org|net|co\.uk|es)\s*$",
    re.I,
)
_WORDS_RE = re.compile(r"[a-z0-9áéíóúüñ]+", re.I)
_STOPWORDS = {
    "a", "about", "after", "amid", "an", "and", "are", "as", "at", "be",
    "by", "de", "del", "el", "en", "for", "from", "hormuz", "in", "is",
    "la", "las", "los", "of", "on", "or", "para", "por", "strait", "that",
    "the", "to", "un", "una", "y", "with",
}
_TOKEN_CANON = {
    "cross": "transit", "crossed": "transit", "crosses": "transit", "crossing": "transit",
    "passed": "transit", "passes": "transit", "passing": "transit",
    "transited": "transit", "transiting": "transit", "transits": "transit",
    "ship": "vessel", "ships": "vessel", "vessels": "vessel",
    "restricted": "restriction", "restrictions": "restriction",
    "halted": "halt", "stopped": "halt", "interrupted": "halt",
}
_ANALYSIS_RE = re.compile(r"\b(analysis|análisis|explainer|what we know|why|how)\b|\?", re.I)
_OPINION_RE = re.compile(r"\b(opinion|editorial|commentary|column|tribuna|opinión)\b", re.I)
_RUMOR_RE = re.compile(r"\b(rumou?r|unverified|reportedly|allegedly|trascendido|sin confirmar)\b", re.I)
_DECLARATION_RE = re.compile(
    r"\b(says?|said|claims?|claimed|declares?|declared|announces?|announced|"
    r"threatens?|threatened|vows?|warns?|urges?|stated|statement|dice|afirma|"
    r"declaró|declara|anuncia|amenaza|advierte)\b",
    re.I,
)
_OPERATIONAL_RE = re.compile(
    r"\b(transit(?:ed|ing|s)?|cross(?:ed|ing)?|pass(?:ed|ing)?|traffic|vessels?|"
    r"ships?|tankers?|ferr(?:y|ies)|port|navigation|navigational|corridor|route|"
    r"closed to shipping|halted|stopped|reopened|aviso a los navegantes|"
    r"radioaviso|tráfico|buques?|puerto|ferris?)\b",
    re.I,
)
_CLOSURE_RE = re.compile(r"\b(closed|closure|halted|stopped|blocked|impassable|cierre|cerrado|interrumpido)\b", re.I)
_OPEN_RE = re.compile(r"\b(open|reopened|transit(?:ed|ing|s)?|cross(?:ed|ing)?|pass(?:ed|ing)?|abierto|operativo)\b", re.I)


def _ascii(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def normalize_text(value: Any) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))
    return re.sub(r"\s+", " ", text).strip()


def normalized_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _ascii(normalize_text(value)).casefold()).strip()


def normalize_title(value: Any) -> str:
    title = normalize_text(value)
    title = _TITLE_SUFFIX_RE.sub("", title)
    return normalized_key(title)


def canonical_url(value: Any) -> str:
    raw = normalize_text(value)
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
    except ValueError:
        return raw
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return raw
    host = parsed.netloc.casefold().removeprefix("www.")
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/":
        path = path.rstrip("/")
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.casefold() not in _TRACKING_QUERY_KEYS and not key.casefold().startswith("utm_")
    ]
    return urlunparse((parsed.scheme.casefold(), host, path, "", urlencode(query), ""))


def parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = normalize_text(value)
    if not text:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    canonical_name: str
    aliases: tuple[str, ...]
    domains: tuple[str, ...]
    tier: int
    official: bool
    weight: float

    @property
    def domain(self) -> str:
        return self.domains[0] if self.domains else ""

    def public_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "canonical_name": self.canonical_name,
            "domain": self.domain,
            "tier": self.tier,
            "official": self.official,
            "weight": self.weight,
        }


UNKNOWN_SOURCE = SourceRecord("unknown", "Unknown source", (), (), 1, False, 1.0)


class SourceRegistry:
    def __init__(self, records: Iterable[SourceRecord]):
        self.records = tuple(records)
        self._by_id = {item.source_id: item for item in self.records}
        self._by_alias: dict[str, SourceRecord] = {}
        self._by_domain: dict[str, SourceRecord] = {}
        for item in self.records:
            names = {item.canonical_name, item.source_id, *item.aliases, *item.domains}
            for name in names:
                key = normalized_key(name)
                if key:
                    self._by_alias[key] = item
            for domain in item.domains:
                clean = domain.casefold().removeprefix("www.")
                if clean:
                    self._by_domain[clean] = item

    @classmethod
    def from_payload(cls, payload: Any) -> "SourceRegistry":
        rows = payload.get("sources", []) if isinstance(payload, dict) else payload if isinstance(payload, list) else []
        records: list[SourceRecord] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            source_id = normalized_key(row.get("source_id") or row.get("id")).replace(" ", "_")
            canonical_name = normalize_text(row.get("canonical_name") or row.get("name"))
            aliases = tuple(normalize_text(x) for x in row.get("aliases", []) if normalize_text(x))
            raw_domains = row.get("domains") or ([row.get("domain")] if row.get("domain") else [])
            domains = tuple(str(x).casefold().removeprefix("www.") for x in raw_domains if normalize_text(x))
            if not source_id or not canonical_name:
                continue
            tier = max(1, min(5, int(row.get("tier") or 1)))
            records.append(SourceRecord(
                source_id=source_id,
                canonical_name=canonical_name,
                aliases=aliases,
                domains=domains,
                tier=tier,
                official=bool(row.get("official")),
                weight=float(row.get("weight") or tier),
            ))
        return cls(records)

    @classmethod
    def from_path(cls, path: Path) -> "SourceRegistry":
        try:
            return cls.from_payload(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return cls(())

    def by_id(self, source_id: str) -> SourceRecord | None:
        return self._by_id.get(normalized_key(source_id).replace(" ", "_"))

    def resolve(self, name: Any = "", url: Any = "") -> SourceRecord:
        raw_url = normalize_text(url)
        if raw_url:
            try:
                host = urlparse(raw_url).netloc.casefold().removeprefix("www.")
            except ValueError:
                host = ""
            if host:
                for domain, record in self._by_domain.items():
                    if host == domain or host.endswith("." + domain):
                        return record
        key = normalized_key(name).removeprefix("www ")
        if key in self._by_alias:
            return self._by_alias[key]
        # Publisher names in RSS often append a domain after a dash.  Match
        # complete tokens only; never match short aliases inside another word.
        padded = f" {key} "
        for alias in sorted(self._by_alias, key=len, reverse=True):
            if len(alias) >= 4 and f" {alias} " in padded:
                return self._by_alias[alias]
        return UNKNOWN_SOURCE


def public_signal_label(code: Any, lang: str = "es") -> str:
    pair = PUBLIC_SIGNAL_LABELS.get(normalize_text(code).upper())
    if pair:
        return pair[0 if lang == "es" else 1]
    value = normalize_text(code).replace("_", " ").strip()
    return value.title() if value else ("Sin clasificar" if lang == "es" else "Unclassified")


def _article_source_fields(raw: dict[str, Any]) -> tuple[str, str]:
    return (
        normalize_text(raw.get("source_name") or raw.get("source") or raw.get("publisher")),
        normalize_text(raw.get("source_url") or raw.get("url") or raw.get("link")),
    )


def _topic(raw: dict[str, Any], title: str) -> str:
    explicit = normalized_key(raw.get("topic") or raw.get("category") or raw.get("signal") or raw.get("kind"))
    if explicit:
        return explicit.replace(" ", "_")
    low = normalized_key(title)
    if any(word in low for word in ("attack", "strike", "security", "risk", "mine", "naval")):
        return "security"
    if any(word in low for word in ("oil", "lng", "price", "energy", "freight", "insurance")):
        return "energy"
    if any(word in low for word in ("talk", "deal", "diplomatic", "minister", "government", "sanction")):
        return "diplomacy"
    if _OPERATIONAL_RE.search(title):
        return "maritime"
    return "other"


def classify_article(raw: dict[str, Any], source: SourceRecord) -> str:
    title = normalize_text(raw.get("title"))
    description = normalize_text(raw.get("description") or raw.get("summary") or raw.get("details"))
    text = f"{title}. {description}"
    signal = normalize_text(raw.get("signal") or raw.get("kind")).upper()
    if _OPINION_RE.search(text):
        return "OPINION"
    if _ANALYSIS_RE.search(title):
        return "ANALYSIS"
    if _RUMOR_RE.search(text):
        return "RUMOR"
    if source.official and (signal or _OPERATIONAL_RE.search(text)):
        return "OFFICIAL_NOTICE"
    if signal in {
        "OPEN_OPERATIONAL", "CLOSED_OPERATIONAL", "TRANSIT_CONFIRMED",
        "TRAFFIC_PRESENT", "TRAFFIC_REDUCED", "TRAFFIC_SEVERELY_REDUCED",
        "TRAFFIC_NORMAL", "CLOSURE_EFFECTIVE", "ACCESS_RESTRICTED",
        "NEUTRAL_TRANSIT_PERMITTED", "RISK_SEVERE", "RISK_ELEVATED",
    } or _OPERATIONAL_RE.search(text):
        return "OPERATIONAL_SIGNAL"
    if signal in {"CLOSURE_DECLARED", "FORMAL_CLOSURE_CLAIM"} or _DECLARATION_RE.search(text):
        return "DECLARATION"
    if source.source_id == "unknown" or source.tier <= 1:
        return "UNCONFIRMED"
    return "FACT"


def _article_id(url: str, title_key: str, source_id: str, published_at: str) -> str:
    day = parse_datetime(published_at).date().isoformat()
    seed = url or f"{source_id}|{title_key}|{day}"
    return "art_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def normalize_article(raw: dict[str, Any], registry: SourceRegistry) -> dict[str, Any]:
    title = normalize_text(raw.get("title"))
    source_name, raw_url = _article_source_fields(raw)
    source = registry.resolve(source_name, raw_url)
    url = canonical_url(raw_url)
    title_key = normalize_title(title)
    for outlet_name in (source.canonical_name, *source.aliases):
        outlet_key = normalized_key(outlet_name)
        if outlet_key and title_key.endswith(" " + outlet_key):
            title_key = title_key[: -(len(outlet_key) + 1)].strip()
            break
    published_at = normalize_text(raw.get("published_at") or raw.get("observed_at") or raw.get("first_seen"))
    if parse_datetime(published_at).year > 1970:
        published_at = iso_z(parse_datetime(published_at))
    classification = normalize_text(raw.get("classification")).upper()
    if classification not in CLASSIFICATIONS:
        classification = classify_article(raw, source)
    signal = normalize_text(raw.get("signal") or raw.get("kind")).upper()
    result = {
        "article_id": normalize_text(raw.get("article_id")) or _article_id(url, title_key, source.source_id, published_at),
        "title": title,
        "title_key": title_key,
        "url": url,
        "published_at": published_at,
        "observed_at": normalize_text(raw.get("observed_at")),
        "source_id": source.source_id,
        "source_name": source.canonical_name,
        "source_domain": source.domain,
        "tier": source.tier,
        "official": source.official,
        "weight": source.weight,
        "topic": _topic(raw, title),
        "classification": classification,
        "signal": signal,
        "description": normalize_text(raw.get("description") or raw.get("summary") or raw.get("details")),
    }
    return result


def _content_tokens(title_key: str) -> set[str]:
    return {
        _TOKEN_CANON.get(token, token)
        for token in _WORDS_RE.findall(title_key)
        if len(token) > 2 and token not in _STOPWORDS
    }


def title_similarity(left: str, right: str) -> float:
    a = normalize_title(left)
    b = normalize_title(right)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    ta, tb = _content_tokens(a), _content_tokens(b)
    jaccard = len(ta & tb) / len(ta | tb) if ta | tb else 0.0
    return max(jaccard, SequenceMatcher(None, a, b).ratio())


def deduplicate_articles(raw_articles: Iterable[dict[str, Any]], registry: SourceRegistry) -> list[dict[str, Any]]:
    normalized = [normalize_article(item, registry) for item in raw_articles if isinstance(item, dict) and normalize_text(item.get("title"))]
    output: list[dict[str, Any]] = []
    seen_url_signals: set[tuple[str, str]] = set()
    for article in sorted(normalized, key=lambda item: parse_datetime(item.get("published_at")), reverse=True):
        url = article["url"]
        url_signal = (url, article.get("signal") or article["title_key"])
        if url and url_signal in seen_url_signals:
            continue
        duplicate = False
        for previous in output:
            if article["source_id"] != previous["source_id"]:
                continue
            delta = abs((parse_datetime(article["published_at"]) - parse_datetime(previous["published_at"])).total_seconds())
            if delta <= 96 * 3600 and title_similarity(article["title"], previous["title"]) >= 0.90:
                duplicate = True
                break
        if duplicate:
            continue
        if url:
            seen_url_signals.add(url_signal)
        output.append(article)
    return output


def _polarity(article: dict[str, Any]) -> str:
    signal = normalize_text(article.get("signal")).upper()
    text = f"{article.get('title', '')} {article.get('description', '')}"
    if signal in {"CLOSED_OPERATIONAL", "CLOSURE_EFFECTIVE"}:
        return "closed"
    if signal in {"OPEN_OPERATIONAL", "TRANSIT_CONFIRMED", "TRAFFIC_PRESENT", "NEUTRAL_TRANSIT_PERMITTED"}:
        return "open"
    if _CLOSURE_RE.search(text) and not _DECLARATION_RE.search(text):
        return "closed"
    if _OPEN_RE.search(text) and _OPERATIONAL_RE.search(text):
        return "open"
    return "neutral"


def _verification(articles: list[dict[str, Any]]) -> str:
    polarities = {_polarity(item) for item in articles} - {"neutral"}
    if len(polarities) > 1:
        return "CONFLICTING"
    factual = [item for item in articles if item["classification"] not in {"ANALYSIS", "OPINION", "RUMOR", "UNCONFIRMED"}]
    if factual and all(item["classification"] == "DECLARATION" for item in factual):
        return "DECLARATION_ONLY"
    if any(item["official"] and item["tier"] >= 4 and item["classification"] in {"OFFICIAL_NOTICE", "OPERATIONAL_SIGNAL", "FACT"} for item in factual):
        return "CONFIRMED_PRIMARY"
    independent = {item["source_id"] for item in factual if item["tier"] >= 3 and item["source_id"] != "unknown"}
    if len(independent) >= 2:
        return "CONFIRMED_MULTI_SOURCE"
    if factual and any(item["tier"] >= 2 for item in factual):
        return "SINGLE_SOURCE"
    return "UNCONFIRMED"


def _event_classification(articles: list[dict[str, Any]]) -> str:
    present = {item["classification"] for item in articles}
    for value in ("OFFICIAL_NOTICE", "OPERATIONAL_SIGNAL", "FACT", "DECLARATION", "ANALYSIS", "OPINION", "RUMOR", "UNCONFIRMED"):
        if value in present:
            return value
    return "UNCONFIRMED"


def _event_match(article: dict[str, Any], members: list[dict[str, Any]]) -> bool:
    article_time = parse_datetime(article["published_at"])
    member_times = [parse_datetime(item["published_at"]) for item in members]
    valid_times = [value for value in member_times if value.year > 1970]
    if valid_times and article_time.year > 1970:
        combined_times = [*valid_times, article_time]
        if max(combined_times) - min(combined_times) > timedelta(hours=72):
            return False
    for existing in members:
        if article["url"] and article["url"] == existing["url"]:
            return True
        if article["topic"] != existing["topic"]:
            continue
        delta = abs((parse_datetime(article["published_at"]) - parse_datetime(existing["published_at"])).total_seconds())
        if delta > 72 * 3600:
            continue
        score = title_similarity(article["title"], existing["title"])
        shared = _content_tokens(article["title_key"]) & _content_tokens(existing["title_key"])
        if score >= 0.64 or len(shared) >= 3:
            return True
    return False


def _prior_event_id(members: list[dict[str, Any]], previous_events: Iterable[dict[str, Any]]) -> tuple[str, str] | None:
    member_urls = {item["url"] for item in members if item["url"]}
    member_titles = [item["title"] for item in members]
    for previous in previous_events:
        if not isinstance(previous, dict):
            continue
        prior_articles = previous.get("articles") if isinstance(previous.get("articles"), list) else []
        prior_urls = {canonical_url(item.get("url")) for item in prior_articles if isinstance(item, dict) and item.get("url")}
        if member_urls & prior_urls:
            return normalize_text(previous.get("event_id")), normalize_text(previous.get("first_seen"))
        prior_titles = [normalize_text(item.get("title")) for item in prior_articles if isinstance(item, dict)]
        if any(title_similarity(left, right) >= 0.78 for left in member_titles for right in prior_titles):
            return normalize_text(previous.get("event_id")), normalize_text(previous.get("first_seen"))
    return None


def _new_event_id(members: list[dict[str, Any]], first_seen: str) -> str:
    tokens: set[str] = set()
    for item in members:
        tokens.update(_content_tokens(item["title_key"]))
    topic = sorted({item["topic"] for item in members})[0]
    day = parse_datetime(first_seen).date().isoformat()
    seed = f"{topic}|{day}|{' '.join(sorted(tokens)[:10])}"
    return "evt_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _importance(articles: list[dict[str, Any]], verification: str, operational_impact: str) -> int:
    base = {
        "OFFICIAL_NOTICE": 45, "OPERATIONAL_SIGNAL": 45, "FACT": 32,
        "DECLARATION": 20, "ANALYSIS": 14, "OPINION": 8, "RUMOR": 5,
        "UNCONFIRMED": 4,
    }.get(_event_classification(articles), 4)
    base += {
        "CONFIRMED_PRIMARY": 22, "CONFIRMED_MULTI_SOURCE": 24,
        "SINGLE_SOURCE": 8, "DECLARATION_ONLY": 0, "UNCONFIRMED": 0,
        "CONFLICTING": 8,
    }[verification]
    base += {"MATERIAL": 22, "POTENTIAL": 10, "CONTEXT": 3, "NONE": 0}[operational_impact]
    base += min(8, max(0, len({item["source_id"] for item in articles}) - 1) * 3)
    return max(0, min(100, base))


def _operational_impact(articles: list[dict[str, Any]], verification: str) -> str:
    operational = any(item["classification"] in {"OFFICIAL_NOTICE", "OPERATIONAL_SIGNAL"} for item in articles)
    if operational and verification in {"CONFIRMED_PRIMARY", "CONFIRMED_MULTI_SOURCE"}:
        return "MATERIAL"
    if operational or any(item["classification"] == "DECLARATION" for item in articles):
        return "POTENTIAL"
    if any(item["classification"] in {"FACT", "ANALYSIS"} for item in articles):
        return "CONTEXT"
    return "NONE"


def aggregate_events(
    raw_articles: Iterable[dict[str, Any]],
    registry: SourceRegistry,
    previous_events: Iterable[dict[str, Any]] = (),
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    articles = deduplicate_articles(raw_articles, registry)
    clusters: list[list[dict[str, Any]]] = []
    for article in sorted(articles, key=lambda item: parse_datetime(item["published_at"])):
        target = next((members for members in clusters if _event_match(article, members)), None)
        if target is None:
            clusters.append([article])
        else:
            target.append(article)

    events: list[dict[str, Any]] = []
    previous_list = list(previous_events)
    reused_previous_ids: set[str] = set()
    for members in clusters:
        members.sort(key=lambda item: parse_datetime(item["published_at"]))
        first_seen = next((item["published_at"] for item in members if item["published_at"]), generated_at or "")
        last_seen = next((item["published_at"] for item in reversed(members) if item["published_at"]), first_seen)
        prior = _prior_event_id(members, previous_list)
        event_id = prior[0] if prior and prior[0] and prior[0] not in reused_previous_ids else _new_event_id(members, first_seen)
        if prior and event_id == prior[0]:
            reused_previous_ids.add(event_id)
        if prior and event_id == prior[0] and prior[1]:
            first_seen = prior[1]
        verification = _verification(members)
        classification = _event_classification(members)
        operational_impact = _operational_impact(members, verification)
        sources: list[dict[str, Any]] = []
        for source_id in sorted({item["source_id"] for item in members}):
            sample = next(item for item in members if item["source_id"] == source_id)
            sources.append({key: sample[key] for key in ("source_id", "source_name", "source_domain", "tier", "official", "weight")})
        events.append({
            "event_id": event_id,
            "topic": max({item["topic"] for item in members}, key=lambda topic: sum(1 for item in members if item["topic"] == topic)),
            "first_seen": first_seen,
            "last_seen": last_seen,
            "headline": max(members, key=lambda item: (item["tier"], len(item["title"]), item["published_at"]))["title"],
            "classification": classification,
            "verification_status": verification,
            "verification_reason": verification_reason(verification, sources),
            "sources": sources,
            "source_ids": [item["source_id"] for item in sources],
            "articles": members,
            "importance": _importance(members, verification, operational_impact),
            "operational_impact": operational_impact,
            "operational_eligible": verification in {"CONFIRMED_PRIMARY", "CONFIRMED_MULTI_SOURCE"} and operational_impact == "MATERIAL",
        })
    events.sort(key=lambda item: (parse_datetime(item["last_seen"]), item["importance"]), reverse=True)
    now = generated_at or iso_z(datetime.now(timezone.utc))
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now,
        "events": events,
        "verification_summary": verification_summary(events),
        "article_count": len(articles),
        "event_count": len(events),
    }


def verification_reason(status: str, sources: list[dict[str, Any]]) -> str:
    if status == "CONFIRMED_PRIMARY":
        return "Direct official or primary evidence."
    if status == "CONFIRMED_MULTI_SOURCE":
        return "Corroborated by at least two reliable independent sources."
    if status == "SINGLE_SOURCE":
        return "Supported by one usable source; independent corroboration is pending."
    if status == "DECLARATION_ONLY":
        return "The record is a declaration and is not treated as an operational fact."
    if status == "CONFLICTING":
        return "Reliable records contain incompatible operational claims."
    return "The available records do not meet the confirmation threshold."


def verification_summary(events: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts = {status: 0 for status in sorted(VERIFICATION_STATUSES)}
    for event in events:
        status = normalize_text(event.get("verification_status")).upper()
        if status in counts:
            counts[status] += 1
    counts["TOTAL"] = sum(counts.values())
    return counts


def factual_packet(
    *,
    monitor: dict[str, Any],
    operational_assessment: dict[str, Any],
    event_store: dict[str, Any],
    comparison: dict[str, Any],
    known_limits: list[str],
    watch_items: list[str],
) -> dict[str, Any]:
    events = event_store.get("events") if isinstance(event_store.get("events"), list) else []
    selected_full = [event for event in events if event.get("verification_status") != "UNCONFIRMED"][:20]
    event_keys = (
        "event_id", "topic", "first_seen", "last_seen", "headline", "classification",
        "verification_status", "verification_reason", "sources", "source_ids", "importance",
        "operational_impact", "operational_eligible",
    )
    # The full event store retains article-level provenance. The editorial
    # packet needs the verified event and source facts, not duplicate article
    # payloads that can push a real packet over the remote safety limit.
    selected = [
        {key: event.get(key) for key in event_keys if event.get(key) is not None}
        for event in selected_full
    ]
    statements = [event for event in selected if event.get("classification") == "DECLARATION"]
    source_map: dict[str, dict[str, Any]] = {}
    for event in selected:
        for source in event.get("sources") or []:
            if isinstance(source, dict) and source.get("source_id"):
                source_map[str(source["source_id"])] = source
    public_monitor_keys = (
        "checked_at", "status", "operational_status", "confidence", "verification_ok", "stale",
        "generated_at", "maritime_status", "maritime_note", "border_pressure", "border_note",
        "bilateral_tension", "bilateral_note", "security_status", "security_note",
    )
    public_operational_keys = (
        "version", "generated_at", "state", "family", "label_es", "label_en",
        "operational_label_es", "operational_label_en", "confidence", "summary_es",
        "summary_en", "dimensions", "dimension_labels_es", "dimension_labels_en",
        "traffic_snapshot", "latest_confirmed_transit_at", "carried_forward",
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "monitor": {key: monitor.get(key) for key in public_monitor_keys if monitor.get(key) is not None},
        "operational_assessment": {
            key: operational_assessment.get(key)
            for key in public_operational_keys
            if operational_assessment.get(key) is not None
        },
        "events": selected,
        "statements": statements,
        "sources": [source_map[key] for key in sorted(source_map)],
        "comparison_with_previous_edition": comparison,
        "known_limits": [normalize_text(item) for item in known_limits if normalize_text(item)],
        "watch_items": [normalize_text(item) for item in watch_items if normalize_text(item)],
        "verification_summary": event_store.get("verification_summary") or verification_summary(events),
    }


def packet_hash(packet: dict[str, Any]) -> str:
    encoded = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def write_json_if_changed(path: Path, payload: Any) -> bool:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    previous = path.read_text(encoding="utf-8") if path.exists() else None
    if previous == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def public_source_registry(registry: SourceRegistry) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "sources": [
            {
                **record.public_dict(),
                "aliases": list(record.aliases),
                "domains": list(record.domains),
            }
            for record in registry.records
        ],
    }


__all__ = [
    "CLASSIFICATIONS", "PUBLIC_SIGNAL_LABELS", "SCHEMA_VERSION", "SourceRecord",
    "SourceRegistry", "VERIFICATION_STATUSES", "aggregate_events", "canonical_url",
    "deduplicate_articles", "factual_packet", "iso_z", "normalize_article",
    "normalize_text", "normalize_title", "normalized_key", "packet_hash",
    "parse_datetime", "public_signal_label", "public_source_registry",
    "title_similarity", "verification_summary", "write_json_if_changed",
]
