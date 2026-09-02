#!/usr/bin/env python3
"""El Diario de Ormuz · sistema editorial V9.

Objetivo
--------
Crear una crónica diaria legible y trazable a partir de datos ya publicados por
el monitor y de un barrido prudente de noticias recientes. La edición en vivo
se actualiza todos los días; solo se crea una URL histórica indexable cuando
hay novedad material suficiente.

con hechos estructurados y titulares enlazados. Los titulares interrogativos,
de opinión o puramente especulativos nunca se convierten en hechos.
"""
from __future__ import annotations

from journal_evidence import classify_headline, identity, reading, section_note

import argparse
import email.utils
import hashlib
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")
BASE_URL = "https://estrechoormuz.com"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "Chrome/126 Safari/537.36 Estrecho-Ormuz-Diario/8"
)
MAX_NEWS = 40
MAX_ARCHIVE = 180
MATERIAL_THRESHOLD = 4
EDITORIAL_VERSION = 10

TRUSTED_SOURCES = {
    "reuters": 5,
    "associated press": 5,
    "ap news": 5,
    "bbc": 4,
    "bbc news": 4,
    "financial times": 4,
    "bloomberg": 4,
    "the guardian": 3,
    "al jazeera": 3,
    "cnbc": 3,
    "euronews": 3,
    "lloyd's list": 5,
    "lloyds list": 5,
    "tradewinds": 4,
    "tradewinds news": 4,
    "marinelink": 3,
    "seatrade maritime": 3,
    "seatrade maritime news": 3,
    "s&p global": 4,
    "sp global": 4,
    "argus media": 4,
    "ukmto": 5,
    "jmic": 5,
    "imo": 5,
    "u.s. marad": 5,
    "marad": 5,
    "u.s. centcom": 5,
    "centcom": 5,
    "oman news agency": 4,
}

TOPIC_PATTERNS = {
    "maritime": re.compile(
        r"\b(ship|ships|shipping|vessel|vessels|tanker|tankers|traffic|transit|transits|"
        r"strait|ais|route|routes|carrier|carriers|cargo|port|ports)\b",
        re.I,
    ),
    "security": re.compile(
        r"\b(attack|attacks|strike|strikes|struck|missile|projectile|drone|uav|mine|mines|"
        r"explosion|navy|naval|escort|warning|threat|security|centcom|ukmto|jmic)\b",
        re.I,
    ),
    "diplomacy": re.compile(
        r"\b(talk|talks|deal|agreement|negotiation|negotiations|ceasefire|diplomatic|diplomacy|"
        r"iran|tehran|oman|washington|trump|sanction|sanctions)\b",
        re.I,
    ),
    "energy": re.compile(
        r"\b(oil|crude|brent|wti|lng|gas|energy|barrel|barrels|refinery|refining|export|exports|"
        r"qatar|saudi|uae|emirates)\b",
        re.I,
    ),
    "insurance": re.compile(
        r"\b(insurance|insurer|insurers|premium|premiums|war risk|p&i|underwriter|underwriters|"
        r"freight|charter|chartering)\b",
        re.I,
    ),
}

TOPIC_LABELS = {
    "es": {
        "maritime": "Tráfico marítimo",
        "security": "Seguridad",
        "diplomacy": "Diplomacia",
        "energy": "Energía y mercados",
        "insurance": "Seguros y costes de navegación",
        "other": "Otras novedades",
    },
    "en": {
        "maritime": "Maritime traffic",
        "security": "Security",
        "diplomacy": "Diplomacy",
        "energy": "Energy and markets",
        "insurance": "Insurance and shipping costs",
        "other": "Other developments",
    },
}

EDITION_IDENTITIES = {
    "maritime": {"slug": "navigation", "es": "Cuaderno de navegación", "en": "Navigation log"},
    "security": {"slug": "security", "es": "Cuaderno de seguridad", "en": "Security log"},
    "diplomacy": {"slug": "diplomacy", "es": "Cuaderno diplomático", "en": "Diplomatic log"},
    "energy": {"slug": "energy", "es": "Cuaderno de energía", "en": "Energy log"},
    "insurance": {"slug": "insurance", "es": "Cuaderno de costes marítimos", "en": "Shipping-cost log"},
    "other": {"slug": "continuity", "es": "Cuaderno de continuidad", "en": "Continuity log"},
}

QUESTION_OR_ANALYSIS = re.compile(
    r"(?:\?|\bwhy\b|\bhow\b|\bwhat\b|\bwhether\b|\bopinion\b|\banalysis\b|"
    r"\bexplainer\b|\bclaims?\b|\binsists?\b|\bargues?\b)",
    re.I,
)

@dataclass
class NewsItem:
    title: str
    source: str
    url: str
    published_at: str
    tier: int
    topic: str
    query: str
    analytical: bool = False


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_date(value: Any) -> datetime:
    text = str(value or "").strip()
    if not text:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        pass
    try:
        dt = email.utils.parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def stable_write(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = path.read_text(encoding="utf-8") if path.exists() else None
    if previous == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def dump_json(path: Path, value: Any) -> bool:
    return stable_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def safe(value: Any) -> str:
    return html.escape(norm(value), quote=True)


def stable_pick(options: tuple[str, ...], seed: str) -> str:
    if not options:
        return ""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return options[int.from_bytes(digest[:2], "big") % len(options)]


def dominant_topic(items: list[NewsItem]) -> str:
    scores: Counter[str] = Counter()
    for item in items:
        if item.topic != "other":
            scores[item.topic] += max(1, item.tier)
    return scores.most_common(1)[0][0] if scores else "other"


def build_editorial_context(
    root: Path,
    news: list[NewsItem],
    new_items: list[NewsItem],
    local_dt: datetime,
) -> dict[str, Any]:
    """Crea un pulso basado en el archivo propio; nunca lo presenta como tráfico real."""
    topic = dominant_topic(new_items)
    identity = EDITION_IDENTITIES.get(topic, EDITION_IDENTITIES["other"])
    previous_counts: list[int] = []
    data_dir = root / "journal-data"
    if data_dir.exists():
        for path in sorted(data_dir.glob("*.json"), reverse=True):
            if path.stem == local_dt.date().isoformat():
                continue
            record = load_json(path, {})
            value = record.get("new_articles") if isinstance(record, dict) else None
            if isinstance(value, int):
                previous_counts.append(value)
            if len(previous_counts) >= 7:
                break
    average = sum(previous_counts) / len(previous_counts) if previous_counts else 0.0
    current = len(new_items)
    if not previous_counts:
        pulse_es, pulse_en = "Primera referencia comparable", "First comparable baseline"
    elif current >= average + 2:
        pulse_es, pulse_en = "Agenda más intensa que la media reciente", "A busier news agenda than the recent average"
    elif current <= max(0, average - 2):
        pulse_es, pulse_en = "Agenda más contenida que la media reciente", "A quieter news agenda than the recent average"
    else:
        pulse_es, pulse_en = "Agenda en línea con la media reciente", "News agenda in line with the recent average"

    sources = {item.source.lower() for item in new_items if item.source}
    analytical = sum(1 for item in new_items if item.analytical)
    candidates = sorted(new_items or news, key=lambda item: (item.tier, parse_date(item.published_at)), reverse=True)
    signal = candidates[0] if candidates else None
    if not new_items:
        limit_es = "No hay una noticia nueva de calidad suficiente para alterar la lectura. La edición se apoya en el último diagnóstico operativo válido."
        limit_en = "There is no new high-quality report sufficient to alter the assessment. This edition relies on the latest valid operational diagnosis."
    elif len(sources) < 2:
        limit_es = "Las novedades no cuentan todavía con contraste entre dos fuentes independientes; se mantienen como señales y no como cambio confirmado."
        limit_en = "The new items are not yet supported by two independent sources; they remain signals rather than a confirmed change."
    elif analytical:
        limit_es = f"{analytical} titular(es) analítico(s) se conservan como contexto, pero no se utilizan para afirmar hechos operativos."
        limit_en = f"{analytical} analytical headline(s) are retained as context but are not used to assert operational facts."
    else:
        limit_es = "Los titulares no permiten medir por sí solos el volumen real de tráfico ni confirmar una normalización sostenida."
        limit_en = "Headlines alone cannot measure actual traffic volume or confirm sustained normalisation."

    return {
        "version": EDITORIAL_VERSION,
        "topic": topic,
        "slug": identity["slug"],
        "label_es": identity["es"],
        "label_en": identity["en"],
        "current_count": current,
        "recent_average": average,
        "pulse_es": pulse_es,
        "pulse_en": pulse_en,
        "source_count": len(sources),
        "analytical_count": analytical,
        "signal": signal,
        "limit_es": limit_es,
        "limit_en": limit_en,
    }


def source_tier(name: str) -> int:
    key = norm(name).lower().strip(" .")
    if key in TRUSTED_SOURCES:
        return TRUSTED_SOURCES[key]
    for token, tier in TRUSTED_SOURCES.items():
        if len(token) >= 5 and token in key:
            return tier
    return 0


def topic_for(title: str) -> str:
    return classify_headline(title)

def article_key(item: NewsItem | dict[str, Any]) -> str:
    if isinstance(item, NewsItem):
        url = item.url
        title = item.title
        source = item.source
    else:
        url = str(item.get("url") or item.get("source_url") or "")
        title = str(item.get("title") or "")
        source = str(item.get("source") or item.get("source_name") or "")
    return identity(url, title, source)


def request_bytes(url: str, timeout: int = 25) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml,application/xml,text/xml;q=0.9,*/*;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def google_news_url(query: str) -> str:
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
    )


def fetch_news(now: datetime) -> tuple[list[NewsItem], list[str]]:
    queries = (
        '"Strait of Hormuz" (traffic OR transit OR shipping OR vessels OR tankers) when:2d',
        '"Strait of Hormuz" (attack OR security OR UKMTO OR JMIC OR mine OR navy) when:2d',
        '"Strait of Hormuz" (Iran OR Oman OR talks OR deal OR negotiations) when:2d',
        '"Strait of Hormuz" (oil OR LNG OR insurance OR freight OR war risk) when:2d',
    )
    results: list[NewsItem] = []
    errors: list[str] = []
    cutoff = now - timedelta(hours=42)

    for query in queries:
        try:
            raw = request_bytes(google_news_url(query))
            root = ET.fromstring(raw)
        except Exception as exc:
            errors.append(f"Google News RSS: {type(exc).__name__}: {exc}")
            continue

        for node in root.findall("./channel/item"):
            title = norm(node.findtext("title"))
            link = norm(node.findtext("link"))
            pub = parse_date(node.findtext("pubDate"))
            source_node = node.find("source")
            source = norm(source_node.text if source_node is not None else "")
            tier = source_tier(source)
            if tier <= 0 or not title or pub < cutoff:
                continue
            if "hormuz" not in title.lower() and "hormuz" not in query.lower():
                continue
            results.append(
                NewsItem(
                    title=title,
                    source=source,
                    url=link,
                    published_at=iso_z(pub),
                    tier=tier,
                    topic=topic_for(title),
                    query=query,
                    analytical=bool(QUESTION_OR_ANALYSIS.search(title)),
                )
            )

    return dedupe_news(results)[:MAX_NEWS], errors


def dedupe_news(items: list[NewsItem]) -> list[NewsItem]:
    output: list[NewsItem] = []
    seen: set[str] = set()
    for item in sorted(items, key=lambda x: (parse_date(x.published_at), x.tier), reverse=True):
        key = article_key(item)
        fuzzy = re.sub(r"\W+", " ", item.title.lower()).strip()
        fuzzy = " ".join(fuzzy.split()[:12])
        if key in seen or fuzzy in seen:
            continue
        seen.add(key)
        seen.add(fuzzy)
        output.append(item)
    return output


def evidence_as_news(status: dict[str, Any], now: datetime) -> list[NewsItem]:
    output: list[NewsItem] = []
    cutoff = now - timedelta(hours=48)
    for raw in status.get("evidence") or []:
        if not isinstance(raw, dict):
            continue
        title = norm(raw.get("title"))
        source = norm(raw.get("source_name"))
        pub = parse_date(raw.get("published_at") or raw.get("observed_at"))
        tier = source_tier(source)
        url = norm(raw.get("source_url"))
        if not title or tier <= 0 or pub < cutoff or pub > now or not re.match(r"^https?://[^/\s]+", url):
            continue
        output.append(
            NewsItem(
                title=title,
                source=source,
                url=url,
                published_at=iso_z(pub),
                tier=tier,
                topic=topic_for(title),
                query="legacy evidence",
                analytical=bool(QUESTION_OR_ANALYSIS.search(title)),
            )
        )
    return output


def get_operational(status: dict[str, Any], root: Path) -> dict[str, Any]:
    candidate = status.get("operational_intelligence")
    if isinstance(candidate, dict) and candidate.get("state"):
        return candidate
    direct = load_json(root / "operational-intelligence.json", {})
    if isinstance(direct, dict) and direct.get("state"):
        return direct
    return {}


def display_state(status: dict[str, Any], operational: dict[str, Any], lang: str) -> tuple[str, str, str]:
    if operational:
        label = operational.get("label_es" if lang == "es" else "label_en") or operational.get("state")
        summary = operational.get("summary_es" if lang == "es" else "summary_en") or ""
        confidence = operational.get("confidence") or status.get("confidence") or "BAJA"
        return norm(label), norm(summary), norm(confidence)

    state = status.get("status") or "INCIERTO"
    op = status.get("operational_label_es" if lang == "es" else "operational_label_en")
    if lang == "en":
        state = {"ABIERTO": "OPEN", "CERRADO": "CLOSED", "INCIERTO": "UNCERTAIN"}.get(state, state)
    return norm(op or state), norm(status.get("summary_es" if lang == "es" else "summary_en")), norm(status.get("confidence") or "BAJA")


def dimensions(operational: dict[str, Any], lang: str) -> dict[str, str]:
    key = "dimension_labels_es" if lang == "es" else "dimension_labels_en"
    labels = operational.get(key) if isinstance(operational.get(key), dict) else {}
    if labels:
        return {str(k): norm(v) for k, v in labels.items()}
    return {}


def state_fingerprint(status: dict[str, Any], operational: dict[str, Any]) -> dict[str, Any]:
    return {
        "legacy_status": status.get("status"),
        "legacy_operational": status.get("operational_status"),
        "legacy_confidence": status.get("confidence"),
        "v7_state": operational.get("state") if operational else None,
        "v7_confidence": operational.get("confidence") if operational else None,
        "dimensions": operational.get("dimensions") if operational else None,
    }


def material_score(current: dict[str, Any], previous: dict[str, Any], new_items: list[NewsItem]) -> tuple[int, list[str]]:
    # Headline volume is not an editorial event. Preserve state changes, not daily synonyms.
    if not previous:
        return 6, ["Primera referencia del seguimiento; no implica revisión humana"]
    reasons = []
    score = 0
    if current.get("v7_state") != previous.get("v7_state") or current.get("legacy_status") != previous.get("legacy_status"):
        score = 5
        reasons.append("Cambio de clasificación del monitor; no equivale a un cambio físico confirmado")
    changed = [key for key in set(current.get("dimensions") or {}) | set(previous.get("dimensions") or {})
               if (current.get("dimensions") or {}).get(key) != (previous.get("dimensions") or {}).get(key)]
    if changed:
        score += 4
        reasons.append("Cambian dimensiones: " + ", ".join(sorted(changed)))
    if not reasons:
        reasons.append("Sin cambio de clasificación: más titulares no justifican otra URL histórica")
    return score, reasons

def confidence_label(value: str, lang: str) -> str:
    mapping = {
        "es": {"ALTA": "alta", "MEDIA": "media", "BAJA": "baja"},
        "en": {"ALTA": "high", "MEDIA": "medium", "BAJA": "low"},
    }
    return mapping[lang].get(value, value.lower() if value else "baja")


def date_label(dt: datetime, lang: str) -> str:
    months_es = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ]
    if lang == "es":
        return f"{dt.day} de {months_es[dt.month - 1]} de {dt.year}"
    return dt.strftime("%B %-d, %Y") if os.name != "nt" else dt.strftime("%B %d, %Y").replace(" 0", " ")


def headline_for(status: dict[str, Any], operational: dict[str, Any], new_items: list[NewsItem], lang: str) -> str:
    if operational.get("carried_forward"):
        return "Ormuz: titulares nuevos, tránsito sin nueva confirmación" if lang == "es" else "Hormuz: new headlines, no fresh transit confirmation"
    topic = dominant_topic(new_items)
    focus = TOPIC_LABELS[lang].get(topic, TOPIC_LABELS[lang]["other"]).lower()
    return f"Ormuz: {focus}, evidencia y límites" if lang == "es" else f"Hormuz: {focus}, evidence and limits"

def interpret_item(item: NewsItem, lang: str) -> str | None:
    # Explain evidentiary limits, never manufacture a summary from keywords.
    return None if item.analytical else reading(item.topic, lang)

def selected_narrative_items(items: list[NewsItem]) -> list[NewsItem]:
    selected: list[NewsItem] = []
    seen_topics: set[str] = set()
    for item in sorted(items, key=lambda x: (x.tier, parse_date(x.published_at)), reverse=True):
        if item.analytical:
            continue
        if item.topic not in seen_topics:
            selected.append(item)
            seen_topics.add(item.topic)
        if len(selected) >= 5:
            break
    if len(selected) < 4:
        for item in items:
            if item in selected or item.analytical:
                continue
            selected.append(item)
            if len(selected) >= 5:
                break
    return selected


def build_lead(status: dict[str, Any], operational: dict[str, Any], local_dt: datetime, lang: str) -> str:
    _, summary, confidence = display_state(status, operational, lang)
    checked = status.get("checked_at") or "—"
    carried = operational.get("carried_forward")
    if lang == "es":
        return (f"Última consulta del monitor: {checked}. {summary} "
                + ("Las dimensiones mostradas se arrastran del diagnóstico anterior: no son una nueva comprobación de tránsito. " if carried else "")
                + "Este parte clasifica titulares y separa su alcance de la evidencia operativa; no sustituye la lectura de las fuentes originales.")
    return (f"Latest monitor check: {checked}. {summary} "
            + ("Displayed dimensions are carried forward from the previous assessment, not a fresh transit observation. " if carried else "")
            + "This digest classifies headlines and distinguishes their scope from operational evidence; it does not replace the original sources.")

def change_paragraph(
    current_fp: dict[str, Any], previous_fp: dict[str, Any], lang: str
) -> str:
    if not previous_fp:
        return (
            "Esta es la primera línea base de El Diario de Ormuz. A partir de hoy, cada edición comparará el diagnóstico con la jornada anterior para distinguir continuidad de cambio real."
            if lang == "es"
            else "This is the first baseline for Hormuz Daily. From today, each edition will compare the assessment with the previous day to separate continuity from genuine change."
        )
    changed = []
    cur_dims = current_fp.get("dimensions") or {}
    prev_dims = previous_fp.get("dimensions") or {}
    for key in ("passage", "traffic", "access", "risk", "legal"):
        if cur_dims.get(key) != prev_dims.get(key):
            changed.append(key)
    state_changed = current_fp.get("v7_state") != previous_fp.get("v7_state") or current_fp.get("legacy_status") != previous_fp.get("legacy_status")
    if lang == "es":
        if state_changed:
            return "La principal diferencia frente a la edición anterior está en la propia clasificación operativa: el balance de evidencias ha desplazado el diagnóstico. La hemeroteca conserva la edición previa para documentar la evolución."
        if changed:
            labels = {"passage":"paso físico", "traffic":"tráfico", "access":"acceso", "risk":"riesgo", "legal":"marco político/legal"}
            return "El estado general no cambia, pero sí lo hacen algunas dimensiones: " + ", ".join(labels[x] for x in changed) + ". Esto evita tratar como idénticas dos jornadas que comparten etiqueta pero no condiciones operativas."
        return "Frente a la edición anterior no aparece un cambio material en la clasificación. La continuidad, sin embargo, no equivale a normalidad: la evaluación mantiene separados el nivel de tráfico, las restricciones y el riesgo."
    else:
        if state_changed:
            return "The main difference from the previous edition is the operational classification itself: the balance of evidence has shifted the assessment. The archive preserves the previous edition to document the evolution."
        if changed:
            labels = {"passage":"physical passage", "traffic":"traffic", "access":"access", "risk":"risk", "legal":"political/legal framework"}
            return "The headline state is unchanged, but some dimensions have moved: " + ", ".join(labels[x] for x in changed) + ". This prevents two days with the same label from being treated as operationally identical."
        return "There is no material change in the classification from the previous edition. Continuity does not mean normality: traffic intensity, restrictions and risk remain separate variables."


def section_paragraph(topic: str, items: list[NewsItem], lang: str) -> str:
    return section_note(topic, items, lang)

def watchlist(status: dict[str, Any], operational: dict[str, Any], lang: str) -> list[str]:
    dims_raw = operational.get("dimensions") if operational else {}
    dims_raw = dims_raw if isinstance(dims_raw, dict) else {}
    items: list[str] = []
    if lang == "es":
        if dims_raw.get("traffic") in {"REDUCED", "SEVERELY_REDUCED", "NEAR_HALT"}:
            items.append("Si el número de cruces comerciales se recupera durante varias jornadas o, por el contrario, vuelve a caer hacia una pausa casi total.")
        if dims_raw.get("risk") in {"SEVERE", "EXTREME"}:
            items.append("Nuevos avisos de JMIC/UKMTO, ataques confirmados, interferencias o cambios en escoltas y presencia naval.")
        if dims_raw.get("access") in {"RESTRICTED", "SELECTIVE"}:
            items.append("Cambios en rutas impuestas, inspecciones, autorizaciones, sanciones, seguros o condiciones selectivas de paso.")
        items.append("La reacción de navieras, aseguradoras y grandes cargadores: el retorno sostenido de operadores privados sería una señal de normalización más fuerte que una declaración política.")
    else:
        if dims_raw.get("traffic") in {"REDUCED", "SEVERELY_REDUCED", "NEAR_HALT"}:
            items.append("Whether commercial crossings recover for several consecutive days or fall again towards a near-total pause.")
        if dims_raw.get("risk") in {"SEVERE", "EXTREME"}:
            items.append("New JMIC/UKMTO advisories, confirmed attacks, interference or changes in escorts and naval presence.")
        if dims_raw.get("access") in {"RESTRICTED", "SELECTIVE"}:
            items.append("Changes in imposed routes, inspections, permissions, sanctions, insurance or selective passage conditions.")
        items.append("The behaviour of shipowners, insurers and major cargo interests: a sustained return of private operators would be stronger evidence of normalisation than a political statement.")
    return items[:4]


def make_sources(items: list[NewsItem], lang: str) -> str:
    rows = []
    for item in items[:10]:
        when = parse_date(item.published_at).astimezone(MADRID).strftime("%d/%m · %H:%M")
        tag = TOPIC_LABELS[lang].get(item.topic, TOPIC_LABELS[lang]["other"])
        note = " · análisis/titular no usado como hecho" if lang == "es" and item.analytical else " · analysis/headline not used as fact" if lang == "en" and item.analytical else ""
        rows.append(
            f'<li><div><span>{safe(tag)}</span><time>{safe(when)}</time></div>'
            f'<a href="{safe(item.url)}" target="_blank" rel="noopener noreferrer">{safe(item.title)}</a>'
            f'<small>{safe(item.source)}{safe(note)}</small></li>'
        )
    if rows:
        return "".join(rows)
    return (
        '<li><p>No se han incorporado titulares externos nuevos; la edición se apoya en los datos estructurados del monitor.</p></li>'
        if lang == "es"
        else '<li><p>No new external headlines were incorporated; this edition relies on the monitor’s structured data.</p></li>'
    )


def editorial_dashboard(profile: dict[str, Any], lang: str) -> str:
    es = lang == "es"
    signal = profile.get("signal")
    if isinstance(signal, NewsItem):
        signal_html = (
            f'<a href="{safe(signal.url)}" target="_blank" rel="noopener noreferrer">'
            f'<strong>{safe(signal.title)}</strong><span>{safe(signal.source)} · {"abrir fuente" if es else "open source"} ↗</span></a>'
        )
    else:
        signal_html = (
            '<strong>Sin una señal nueva dominante</strong><span>La continuidad también forma parte del registro.</span>'
            if es else
            '<strong>No dominant new signal</strong><span>Continuity is also part of the record.</span>'
        )
    average = profile.get("recent_average") or 0
    average_text = f"{average:.1f}" if average else "—"
    topic = TOPIC_LABELS[lang].get(str(profile.get("topic")), TOPIC_LABELS[lang]["other"])
    return f'''<section class="journal-desk" aria-label="{'Mesa de edición' if es else 'Editorial desk'}">
<article class="journal-desk-signal"><span>{'LA SEÑAL DEL DÍA' if es else 'SIGNAL OF THE DAY'}</span>{signal_html}</article>
<article><span>{'PULSO DEL ARCHIVO' if es else 'ARCHIVE PULSE'}</span><strong>{profile.get('current_count', 0)} {'novedades' if es else 'new items'}</strong><small>{'Media de 7 ediciones' if es else 'Seven-edition average'}: {average_text}<br>{safe(profile.get('pulse_es' if es else 'pulse_en'))}</small></article>
<article><span>{'FOCO DE EDICIÓN' if es else 'EDITION FOCUS'}</span><strong>{safe(topic)}</strong><small>{profile.get('source_count', 0)} {'fuentes independientes' if es else 'independent sources'}</small></article>
</section>'''


def structured_data(
    title: str,
    description: str,
    canonical: str,
    date_iso: str,
    lang: str,
    archive: bool,
) -> str:
    payload = {
        "@context": "https://schema.org",
        "@type": "NewsArticle" if archive else "Article",
        "headline": title,
        "description": description,
        "datePublished": date_iso,
        "dateModified": date_iso,
        "inLanguage": lang,
        "mainEntityOfPage": canonical,
        "author": {"@type": "Organization", "name": "Equipo editorial de Estrecho Ormuz" if lang == "es" else "Estrecho Ormuz Editorial Team", "url": BASE_URL + ("/sobre.html" if lang == "es" else "/en-about.html")},
        "publisher": {"@type": "Organization", "name": "Estrecho Ormuz", "url": BASE_URL},
        "isAccessibleForFree": True,
    }
    return json.dumps(payload, ensure_ascii=False)


def nav(lang: str, archive: bool = False) -> str:
    if lang == "es":
        return (
            '<nav class="journal-nav"><a href="/">Estado</a><a href="/diario.html">Diario de hoy</a>'
            '<a href="/diario/">Archivo</a><a href="/analisis.html">Análisis</a><a href="/metodologia.html">Metodología</a>'
            '<a class="journal-lang" href="/en-diary.html">EN</a></nav>'
        )
    return (
        '<nav class="journal-nav"><a href="/en.html">Status</a><a href="/en-diary.html">Today’s diary</a>'
        '<a href="/diary/">Archive</a><a href="/en-analysis.html">Analysis</a><a href="/en-methodology.html">Methodology</a>'
        '<a class="journal-lang" href="/diario.html">ES</a></nav>'
    )


def render_page(
    *,
    status: dict[str, Any],
    operational: dict[str, Any],
    news: list[NewsItem],
    new_items: list[NewsItem],
    previous_fp: dict[str, Any],
    current_fp: dict[str, Any],
    local_dt: datetime,
    lang: str,
    canonical: str,
    archive: bool,
    material_score_value: int,
    material_reasons: list[str],
    editorial: dict[str, Any],
) -> str:
    title = headline_for(status, operational, news, lang)
    state_label, summary, confidence = display_state(status, operational, lang)
    lead = build_lead(status, operational, local_dt, lang)
    change = change_paragraph(current_fp, previous_fp, lang)
    watch = watchlist(status, operational, lang)
    sources_html = make_sources(news, lang)
    topic_counts = Counter(item.topic for item in news if item.topic in TOPIC_PATTERNS)
    topics = [topic for topic, _ in topic_counts.most_common()]
    if not topics:
        topics = ["maritime"]
    date_text = date_label(local_dt, lang)
    byline = "Estrecho Ormuz · selección automática" if lang == "es" else "Estrecho Ormuz · automated selection"
    minutes = max(3, min(7, 2 + len(topics)))
    read_time = f"Lectura: {minutes} min" if lang == "es" else f"Reading time: {minutes} min"
    kicker = "EL DIARIO DE ORMUZ" if lang == "es" else "HORMUZ DAILY"
    edition = editorial.get("label_es" if lang == "es" else "label_en") or ("Edición de la mañana" if lang == "es" else "Morning edition")
    archive_note = (
        "Edición de hemeroteca" if lang == "es" else "Archive edition"
    ) if archive else (
        "Edición diaria · seguimiento continuo" if lang == "es" else "Daily edition · continuous monitoring"
    )

    dim_labels = dimensions(operational, lang)
    metric_names = {
        "es": {"passage": "Paso físico", "traffic": "Tráfico", "access": "Acceso", "risk": "Riesgo"},
        "en": {"passage": "Physical passage", "traffic": "Traffic", "access": "Access", "risk": "Risk"},
    }
    metrics = ""
    for key in ("passage", "traffic", "access", "risk"):
        value = dim_labels.get(key)
        if value:
            metrics += f'<div class="journal-metric"><span>{safe(metric_names[lang][key])}</span><strong>{safe(value)}</strong></div>'
    if not metrics:
        metrics = f'<div class="journal-metric"><span>{"Estado" if lang == "es" else "Status"}</span><strong>{safe(state_label)}</strong></div>'

    sections = ""
    for topic in topics:
        paragraph = section_paragraph(topic, news, lang)
        relevant = [x for x in news if x.topic == topic]
        link_cards = ""
        for item in relevant[:2]:
            link_cards += (
                f'<a class="journal-news-link" href="{safe(item.url)}" target="_blank" rel="noopener noreferrer">'
                f'<span>{safe(item.source)}</span><strong>{safe(item.title)}</strong></a>'
            )
        sections += (
            f'<section class="journal-section"><h2>{safe(TOPIC_LABELS[lang][topic])}</h2>'
            f'<p>{safe(paragraph)}</p>{link_cards}</section>'
        )

    watch_html = "".join(f"<li>{safe(item)}</li>" for item in watch)
    reason_html = (
        "<li>La edición incorpora novedades suficientes para formar parte de la hemeroteca.</li>"
        if material_score_value >= MATERIAL_THRESHOLD and lang == "es"
        else "<li>La edición diaria se mantiene actualizada sin crear una entrada histórica redundante.</li>"
        if lang == "es"
        else "<li>This edition contains sufficient new information to form part of the permanent archive.</li>"
        if material_score_value >= MATERIAL_THRESHOLD
        else "<li>The daily edition remains updated without creating a redundant historical entry.</li>"
    )
    quality_note = (
        "Esta edición forma parte de la hemeroteca porque incorpora novedades materiales suficientes."
        if lang == "es" and material_score_value >= MATERIAL_THRESHOLD
        else "La edición diaria se actualiza sin añadir una entrada redundante a la hemeroteca."
        if lang == "es"
        else "This edition forms part of the archive because it contains sufficient material developments."
        if material_score_value >= MATERIAL_THRESHOLD
        else "The daily edition is updated without adding a redundant entry to the archive."
    )
    description = summary or lead[:220]
    schema = structured_data(title, description, canonical, iso_z(local_dt.astimezone(timezone.utc)), lang, archive)
    alternate = (
        canonical.replace("/diario/", "/diary/").replace("/diario.html", "/en-diary.html")
        if lang == "es"
        else canonical.replace("/diary/", "/diario/").replace("/en-diary.html", "/diario.html")
    )
    desk = editorial_dashboard(editorial, lang)
    limit = editorial.get("limit_es" if lang == "es" else "limit_en") or ""
    triad = f'''<section class="journal-triad" aria-label="{'Capas de lectura' if lang == 'es' else 'Reading layers'}">
<article><span>{'BASE OBSERVABLE' if lang == 'es' else 'OBSERVABLE BASE'}</span><strong>{safe(state_label)}</strong><p>{'Diagnóstico del observatorio con confianza' if lang == 'es' else 'Observatory assessment with'} {safe(confidence_label(confidence, lang))}{'' if lang == 'es' else ' confidence'}.</p></article>
<article><span>{'CAMBIO' if lang == 'es' else 'CHANGE'}</span><strong>{'Desde la referencia anterior' if lang == 'es' else 'Since the previous reference'}</strong><p>{safe(change)}</p></article>
<article><span>{'LÍMITE' if lang == 'es' else 'LIMIT'}</span><strong>{'Lo que aún no sabemos' if lang == 'es' else 'What remains unknown'}</strong><p>{safe(limit)}</p></article>
</section>'''

    return f'''<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{safe(title)} | {safe(kicker.title())}</title>
<meta name="description" content="{safe(description[:250])}"/>
<meta name="robots" content="noindex,follow"/>
<meta name="editorial-status" content="automated-digest"/>
<meta name="theme-color" content="#07111f"/>
<link rel="canonical" href="{safe(canonical)}"/>
<link rel="alternate" hreflang="{lang}" href="{safe(canonical)}"/>
<link rel="alternate" hreflang="{'en' if lang == 'es' else 'es'}" href="{safe(alternate)}"/>
<link rel="alternate" hreflang="x-default" href="{safe(canonical if lang == 'es' else alternate)}"/>
<link rel="stylesheet" href="/styles.css"/>
<link rel="stylesheet" href="/v11.css"/>
<link rel="stylesheet" href="/diario-v8.css?v=20260831-9"/>
<meta property="og:type" content="article"/>
<meta property="og:site_name" content="Estrecho Ormuz"/>
<meta property="og:title" content="{safe(title)}"/>
<meta property="og:description" content="{safe(description[:250])}"/>
<meta property="og:url" content="{safe(canonical)}"/>
<meta property="og:image" content="https://estrechoormuz.com/social-card.png"/>
<meta name="twitter:card" content="summary_large_image"/>
<script type="application/ld+json">{schema}</script>
</head>
<body class="journal-page journal-theme-{safe(editorial.get('slug') or 'continuity')}" data-lang="{lang}">
<a class="skip-link" href="#contenido">{'Saltar al contenido' if lang == 'es' else 'Skip to content'}</a>
<header class="journal-header"><div class="journal-header-inner"><a class="journal-brand" href="{'/' if lang == 'es' else '/en.html'}"><strong>ESTRECHO ORMUZ</strong><small>{'Inteligencia marítima y energética' if lang == 'es' else 'Maritime & energy intelligence'}</small></a>{nav(lang)}</div></header>
<main id="contenido" class="journal-main">
<article class="journal-article">
<header class="journal-hero">
<div class="journal-edition"><span>{kicker}</span><b>{edition}</b><time datetime="{local_dt.date().isoformat()}">{safe(date_text)}</time></div>
<h1>{safe(title)}</h1>
<p class="journal-deck">{safe(description)}</p>
<div class="journal-byline"><span>{safe(byline)}</span><span>{read_time}</span><span>{safe(archive_note)}</span></div>
</header>
<section class="journal-status-card">
<div><span>{'Diagnóstico al cierre de edición' if lang == 'es' else 'Assessment at publication time'}</span><strong>{safe(state_label)}</strong><small>{'Confianza' if lang == 'es' else 'Confidence'}: {safe(confidence_label(confidence, lang))}</small></div>
<div class="journal-metrics">{metrics}</div>
</section>
{desk}
<p class="journal-lead">{safe(lead)}</p>
{triad}
<p><a href="{'/datos-propios-monitor-ormuz.html' if lang == 'es' else '/en-monitor-original-data-report.html'}">{'Análisis propio: qué mide realmente el historial del monitor' if lang == 'es' else 'Original analysis: what the monitor archive actually measures'}</a></p>
{sections}
<section class="journal-section journal-watch"><h2>{'Qué vigilar en las próximas 24 horas' if lang == 'es' else 'What to watch over the next 24 hours'}</h2><ul>{watch_html}</ul></section>
<section class="journal-section journal-sources"><div class="journal-section-title"><div><span>{'Fuentes verificables' if lang == 'es' else 'Verifiable sources'}</span><h2>{'Referencias seleccionadas' if lang == 'es' else 'Selected references'}</h2></div></div><ul>{sources_html}</ul></section>
<section class="journal-method-note"><h2>{'Criterios editoriales de esta edición' if lang == 'es' else 'Editorial standards for this edition'}</h2><p>{safe('Este parte se compone mediante reglas locales y selección automática de titulares. No se ha leído ni verificado automáticamente el texto íntegro de cada noticia, ni se atribuye una revisión humana a cada edición. La fecha de un feed puede corresponder a una actualización, no al momento del hecho. Las marcas de medios diferentes tampoco garantizan investigación independiente. Para el análisis propio y reproducible, consulta el informe de datos del monitor.' if lang == 'es' else "This digest uses local rules and automated headline selection. Full article texts are not automatically read or verified, and no per-edition human review is claimed. Feed dates may reflect updates rather than event dates. Different publisher names do not guarantee independent reporting.")}</p><p>{safe(quality_note)}</p><details><summary>{'Criterio de hemeroteca' if lang == 'es' else 'Archive criteria'}</summary><ul>{reason_html}</ul></details></section>
</article>
</main>
<footer class="journal-footer"><p>© 2026 Estrecho Ormuz · {'Proyecto independiente · No constituye asesoramiento marítimo, financiero ni de seguridad.' if lang == 'es' else 'Independent project · Not maritime, financial or security advice.'}</p></footer>
</body></html>'''


def archive_page(items: list[dict[str, Any]], lang: str) -> str:
    es = lang == "es"
    cards = []
    for item in items:
        url = item.get("url_es" if es else "url_en")
        title = item.get("title_es" if es else "title_en")
        summary = item.get("summary_es" if es else "summary_en")
        identity = item.get("editorial", {}) if isinstance(item.get("editorial"), dict) else {}
        label = identity.get("label_es" if es else "label_en") or ("Cuaderno de Ormuz" if es else "Hormuz log")
        cards.append(
            f'<article class="journal-archive-card"><time>{safe(item.get("date"))}</time><small>{safe(label)}</small><h2><a href="{safe(url)}">{safe(title)}</a></h2><p>{safe(summary)}</p><span>{"Edición archivada" if es else "Archive edition"}</span></article>'
        )
    canonical = f"{BASE_URL}/{'diario/' if es else 'diary/'}"
    alt = f"{BASE_URL}/{'diary/' if es else 'diario/'}"
    return f'''<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/><title>{'Archivo de El Diario de Ormuz' if es else 'Hormuz Daily Archive'}</title><meta name="description" content="{'Archivo de ediciones materiales de El Diario de Ormuz.' if es else 'Archive of material Hormuz Daily editions.'}"/><meta name="robots" content="index,follow,max-image-preview:large"/><link rel="canonical" href="{canonical}"/><link rel="alternate" hreflang="{lang}" href="{canonical}"/><link rel="alternate" hreflang="{'en' if es else 'es'}" href="{alt}"/><link rel="stylesheet" href="/styles.css"/><link rel="stylesheet" href="/v11.css"/><link rel="stylesheet" href="/diario-v8.css?v=20260831-9"/></head><body class="journal-page"> <header class="journal-header"><div class="journal-header-inner"><a class="journal-brand" href="{'/' if es else '/en.html'}"><strong>ESTRECHO ORMUZ</strong><small>{'El Diario de Ormuz' if es else 'Hormuz Daily'}</small></a>{nav(lang)}</div></header><main class="journal-main"><section class="journal-archive-hero"><span class="section-kicker">{'HEMEROTECA · CUADERNOS DE ORMUZ' if es else 'ARCHIVE · HORMUZ LOGS'}</span><h1>{'El Diario de Ormuz' if es else 'Hormuz Daily'}</h1><p>{'Los partes conservan las referencias y el diagnóstico de cada edición. Las nuevas entradas exigen un cambio de clasificación y referencias nuevas de al menos dos medios; no se presentan como reportajes verificados ni como páginas indexables.' if es else 'Digests preserve each edition’s references and assessment. New archive entries require a changed classification and new references from at least two publishers; they are not presented as verified reporting or indexable articles.'}</p></section><section class="journal-archive-grid">{''.join(cards) if cards else '<p>Aún no hay ediciones archivadas.</p>' if es else '<p>No archived editions yet.</p>'}</section></main></body></html>'''


def feed_xml(items: list[dict[str, Any]], generated_at: str) -> str:
    entries = []
    for item in items[:30]:
        entries.append(
            f'''  <entry>\n    <title>{html.escape(item.get('title_es','El Diario de Ormuz'))}</title>\n    <id>{html.escape(item.get('url_es',''))}</id>\n    <link href="{html.escape(item.get('url_es',''))}"/>\n    <updated>{html.escape(item.get('generated_at',generated_at))}</updated>\n    <summary>{html.escape(item.get('summary_es',''))}</summary>\n  </entry>'''
        )
    return f'''<?xml version="1.0" encoding="utf-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom">\n  <title>El Diario de Ormuz</title>\n  <id>{BASE_URL}/diario-feed.xml</id>\n  <link href="{BASE_URL}/diario-feed.xml" rel="self"/>\n  <link href="{BASE_URL}/diario.html"/>\n  <updated>{generated_at}</updated>\n{chr(10).join(entries)}\n</feed>\n'''


def patch_home_teaser(path: Path, lang: str, edition: dict[str, Any]) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    es = lang == "es"
    title = edition.get("title_es" if es else "title_en") or ("El Diario de Ormuz" if es else "Hormuz Daily")
    summary = edition.get("summary_es" if es else "summary_en") or ""
    block = f'''<!-- JOURNAL_V8_HOME_START -->
<section class="content-section journal-home-v8" aria-labelledby="journal-home-title">
  <div><span class="section-kicker">{'EL DIARIO DE ORMUZ' if es else 'HORMUZ DAILY'}</span><h2 id="journal-home-title">{safe(title)}</h2><p>{safe(summary)}</p><div class="journal-home-meta"><span>{safe(edition.get('date'))}</span><span>{'Crónica diaria · fuentes verificables' if es else 'Daily briefing · verifiable sources'}</span></div></div>
  <aside><strong>{'Edición de hoy' if es else 'Today’s edition'}</strong><p>{'Noticias, tráfico, seguridad, diplomacia, energía y qué vigilar durante las próximas 24 horas.' if es else 'News, traffic, security, diplomacy, energy and what to watch over the next 24 hours.'}</p><a class="button primary" href="{'/diario.html' if es else '/en-diary.html'}">{'Leer la crónica completa' if es else 'Read the full edition'}</a><a class="text-link" href="{'/diario/' if es else '/diary/'}">{'Ver hemeroteca →' if es else 'Open archive →'}</a></aside>
</section>
<!-- JOURNAL_V8_HOME_END -->'''
    marker = re.compile(r'<!-- JOURNAL_V8_HOME_START -->.*?<!-- JOURNAL_V8_HOME_END -->', re.I | re.S)
    if marker.search(text):
        text = marker.sub(block, text, count=1)
    else:
        anchor = re.search(r'<!-- HOME_V11_BRIEF_START -->', text)
        if anchor:
            text = text[:anchor.start()] + block + "\n" + text[anchor.start():]
        else:
            faq = re.search(r'<section\b(?=[^>]*aria-labelledby=["\']faq-title["\'])', text, re.I)
            if faq:
                text = text[:faq.start()] + block + "\n" + text[faq.start():]
            else:
                text = text.replace("</main>", block + "\n</main>", 1)
    stable_write(path, text)


def scheduled_allowed(root: Path, local_now: datetime) -> bool:
    state = load_json(root / "journal-state.json", {})
    last_date = state.get("last_date") if isinstance(state, dict) else None
    if last_date == local_now.date().isoformat():
        return False
    # GitHub puede retrasar un cron varias horas. Si la edición de hoy falta, cualquier
    # ejecución posterior a las 07:00 debe poder recuperarla en vez de declarar éxito vacío.
    return local_now.hour >= 7


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(os.getenv("ORMUZ_ROOT", Path(__file__).resolve().parent)))
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--scheduled", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    now = utc_now()
    local_now = now.astimezone(MADRID)
    if args.scheduled and not args.force and not scheduled_allowed(root, local_now):
        print(f"Diario V{EDITORIAL_VERSION}: ejecución omitida por horario/idempotencia ({local_now.isoformat()}).")
        return 0

    status = load_json(root / "status.json", {})
    if not isinstance(status, dict) or not status.get("status"):
        raise SystemExit("status.json no contiene un estado válido.")
    operational = get_operational(status, root)
    previous_state = load_json(root / "journal-state.json", {})
    if not isinstance(previous_state, dict):
        previous_state = {}
    previous_fp = previous_state.get("fingerprint") if isinstance(previous_state.get("fingerprint"), dict) else {}
    seen = set(previous_state.get("seen_keys") or [])
    latest = load_json(root / "journal-latest.json", {})
    seen.update(article_key(item) for item in latest.get("news", []) if isinstance(item, dict))

    news = evidence_as_news(status, now)
    if args.offline:
        # Preserve the last RSS selection when rebuilding without network access.
        for item in latest.get("news", []):
            if isinstance(item, dict) and now - timedelta(hours=48) <= parse_date(item.get("published_at")) <= now:
                try:
                    cached = NewsItem(**{key: item[key] for key in NewsItem.__dataclass_fields__ if key in item})
                    cached.topic = topic_for(cached.title)
                    news.append(cached)
                except TypeError:
                    continue
    fetch_errors: list[str] = []
    if not args.offline:
        fetched, fetch_errors = fetch_news(now)
        news.extend(fetched)
    news = dedupe_news(news)
    new_items = [item for item in news if article_key(item) not in seen]
    if not previous_state:
        new_items = news[:12]

    current_fp = state_fingerprint(status, operational)
    score, reasons = material_score(current_fp, previous_fp, new_items)
    independent = {item.source.lower() for item in new_items if not item.analytical}
    material = score >= MATERIAL_THRESHOLD and len(independent) >= 2

    date_iso = local_now.date().isoformat()
    generated_at = iso_z(now)
    editorial = build_editorial_context(root, news, new_items, local_now)
    title_es = headline_for(status, operational, news, "es")
    title_en = headline_for(status, operational, news, "en")
    _, summary_es, _ = display_state(status, operational, "es")
    _, summary_en, _ = display_state(status, operational, "en")

    live_es = render_page(
        status=status, operational=operational, news=news, new_items=new_items,
        previous_fp=previous_fp, current_fp=current_fp, local_dt=local_now,
        lang="es", canonical=f"{BASE_URL}/diario.html", archive=False,
        material_score_value=score if material else 0, material_reasons=reasons,
        editorial=editorial,
    )
    live_en = render_page(
        status=status, operational=operational, news=news, new_items=new_items,
        previous_fp=previous_fp, current_fp=current_fp, local_dt=local_now,
        lang="en", canonical=f"{BASE_URL}/en-diary.html", archive=False,
        material_score_value=score if material else 0, material_reasons=reasons,
        editorial=editorial,
    )
    stable_write(root / "diario.html", live_es)
    stable_write(root / "en-diary.html", live_en)

    archive = load_json(root / "journal-archive.json", [])
    if not isinstance(archive, list):
        archive = []

    edition = {
        "schema_version": 1,
        "date": date_iso,
        "generated_at": generated_at,
        "title_es": title_es,
        "title_en": title_en,
        "summary_es": summary_es,
        "summary_en": summary_en,
        "material_score": score,
        "material_reasons": reasons,
        "material_archive": material,
        "new_articles": len(new_items),
        "source_brands": len(independent),
        "topics": dict(Counter(item.topic for item in new_items)),
        "fingerprint": current_fp,
        "news": [asdict(item) for item in news[:15]],
        "fetch_errors": fetch_errors,
        "editorial": {k: v for k, v in editorial.items() if k != "signal"},
        "url_es": f"{BASE_URL}/diario.html",
        "url_en": f"{BASE_URL}/en-diary.html",
    }

    # Store a compact daily data record every day, even when no historical HTML is created.
    dump_json(root / "journal-data" / f"{date_iso}.json", edition)
    dump_json(root / "journal-latest.json", edition)

    if material or (root / "diario" / f"{date_iso}.html").exists():
        archive_es_url = f"{BASE_URL}/diario/{date_iso}.html"
        archive_en_url = f"{BASE_URL}/diary/{date_iso}.html"
        archive_es = render_page(
            status=status, operational=operational, news=news, new_items=new_items,
            previous_fp=previous_fp, current_fp=current_fp, local_dt=local_now,
            lang="es", canonical=archive_es_url, archive=True,
            material_score_value=score, material_reasons=reasons,
            editorial=editorial,
        )
        archive_en = render_page(
            status=status, operational=operational, news=news, new_items=new_items,
            previous_fp=previous_fp, current_fp=current_fp, local_dt=local_now,
            lang="en", canonical=archive_en_url, archive=True,
            material_score_value=score, material_reasons=reasons,
            editorial=editorial,
        )
        stable_write(root / "diario" / f"{date_iso}.html", archive_es)
        stable_write(root / "diary" / f"{date_iso}.html", archive_en)
        archive = [x for x in archive if isinstance(x, dict) and x.get("date") != date_iso]
        archived_edition = dict(edition)
        archived_edition["url_es"] = archive_es_url
        archived_edition["url_en"] = archive_en_url
        archive.insert(0, archived_edition)
        archive = archive[:MAX_ARCHIVE]
        dump_json(root / "journal-archive.json", archive)

    stable_write(root / "diario" / "index.html", archive_page(archive, "es"))
    stable_write(root / "diary" / "index.html", archive_page(archive, "en"))
    stable_write(root / "diario-feed.xml", feed_xml(archive, generated_at))

    patch_home_teaser(root / "index.html", "es", edition)
    patch_home_teaser(root / "en.html", "en", edition)

    social = {
        "generated_at": generated_at,
        "publish_recommended": material,
        "es": f"EL DIARIO DE ORMUZ — {date_iso}\n\n{title_es}\n\n{summary_es}\n\n{BASE_URL}/diario.html?utm_source=social&utm_medium=organic&utm_campaign=diario",
        "en": f"HORMUZ DAILY — {date_iso}\n\n{title_en}\n\n{summary_en}\n\n{BASE_URL}/en-diary.html?utm_source=social&utm_medium=organic&utm_campaign=daily",
    }
    dump_json(root / "journal-social-draft.json", social)

    seen_today = [article_key(item) for item in news]
    state_out = {
        "version": EDITORIAL_VERSION,
        "last_date": date_iso,
        "last_generated_at": generated_at,
        "fingerprint": current_fp,
        "seen_keys": list(dict.fromkeys(seen_today + list(seen)))[:500],
        "last_material_archive_date": date_iso if material else previous_state.get("last_material_archive_date"),
        "last_material_score": score,
    }
    dump_json(root / "journal-state.json", state_out)
    dump_json(root / "journal-health.json", {
        "version": EDITORIAL_VERSION,
        "generated_at": generated_at,
        "ok": True,
        "date": date_iso,
        "material_score": score,
        "material_archive": material,
        "news_considered": len(news),
        "new_articles": len(new_items),
        "source_brands": len(independent),
        "fetch_errors": fetch_errors,
        "operational_intelligence_used": bool(operational),
    })

    print(
        f"El Diario de Ormuz V{EDITORIAL_VERSION} listo: {date_iso} · score={score} · "
        f"archivo={'sí' if material else 'no'} · noticias={len(news)} · nuevas={len(new_items)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
