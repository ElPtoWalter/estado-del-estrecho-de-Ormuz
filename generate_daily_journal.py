#!/usr/bin/env python3
"""El Diario de Ormuz · generador editorial automático V8.

Objetivo
--------
Crear una crónica diaria legible y trazable a partir de datos ya publicados por
el monitor y de un barrido prudente de noticias recientes. La edición en vivo
se actualiza todos los días; solo se crea una URL histórica indexable cuando
hay novedad material suficiente.

No usa una API de IA de pago. La redacción es determinista y se construye solo
con hechos estructurados y titulares enlazados. Los titulares interrogativos,
de opinión o puramente especulativos nunca se convierten en hechos.
"""
from __future__ import annotations

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


def source_tier(name: str) -> int:
    key = norm(name).lower().strip(" .")
    if key in TRUSTED_SOURCES:
        return TRUSTED_SOURCES[key]
    for token, tier in TRUSTED_SOURCES.items():
        if len(token) >= 5 and token in key:
            return tier
    return 0


def topic_for(title: str) -> str:
    scores = {
        key: len(pattern.findall(title))
        for key, pattern in TOPIC_PATTERNS.items()
    }
    best, score = max(scores.items(), key=lambda item: item[1])
    return best if score else "other"


def article_key(item: NewsItem | dict[str, Any]) -> str:
    if isinstance(item, NewsItem):
        url = item.url
        title = item.title
        source = item.source
    else:
        url = str(item.get("url") or item.get("source_url") or "")
        title = str(item.get("title") or "")
        source = str(item.get("source") or item.get("source_name") or "")
    raw = f"{url}|{source}|{re.sub(r'\W+', ' ', title.lower()).strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


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
        if not title or tier <= 0 or pub < cutoff:
            continue
        output.append(
            NewsItem(
                title=title,
                source=source,
                url=norm(raw.get("source_url")),
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


def material_score(
    current: dict[str, Any],
    previous: dict[str, Any],
    new_items: list[NewsItem],
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    if not previous:
        return 6, ["Primera edición del archivo editorial"]

    if current.get("v7_state") and current.get("v7_state") != previous.get("v7_state"):
        score += 5
        reasons.append("Cambio del diagnóstico operativo V7")
    elif current.get("legacy_status") != previous.get("legacy_status"):
        score += 5
        reasons.append("Cambio de estado del motor principal")

    cur_dims = current.get("dimensions") or {}
    prev_dims = previous.get("dimensions") or {}
    changed_dims = [key for key in set(cur_dims) | set(prev_dims) if cur_dims.get(key) != prev_dims.get(key)]
    if changed_dims:
        score += min(3, len(changed_dims))
        reasons.append("Cambian dimensiones: " + ", ".join(sorted(changed_dims)))

    independent = {item.source.lower() for item in new_items}
    topics = {item.topic for item in new_items if item.topic != "other"}
    high_tier = [item for item in new_items if item.tier >= 4]
    if len(new_items) >= 3:
        score += 2
        reasons.append(f"{len(new_items)} noticias nuevas de fuentes seleccionadas")
    elif new_items:
        score += 1
        reasons.append(f"{len(new_items)} noticia(s) nueva(s)")
    if len(independent) >= 2:
        score += 1
        reasons.append("Dos o más fuentes independientes")
    if len(topics) >= 2:
        score += 1
        reasons.append("Novedades en varias áreas")
    if high_tier:
        score += 1
        reasons.append("Hay una fuente de primer nivel")
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
    state = norm(operational.get("state")) if operational else ""
    if lang == "es":
        if state == "OPEN_SEVERELY_RESTRICTED":
            return "Ormuz mantiene el paso comercial, pero la normalidad sigue lejos"
        if state == "OPEN_RESTRICTED":
            return "Ormuz sigue abierto con restricciones mientras el mercado mide el riesgo"
        if state == "OPEN_NORMAL":
            return "Ormuz conserva un tránsito operativo próximo a la normalidad"
        if state in {"CLOSED_CONFIRMED", "EFFECTIVELY_CLOSED"}:
            return "El tráfico ordinario en Ormuz queda severamente interrumpido"
        legacy = status.get("status")
        if legacy == "ABIERTO":
            return "Ormuz abre la jornada con tránsito operativo y vigilancia reforzada"
        if legacy == "CERRADO":
            return "Ormuz afronta una jornada marcada por la interrupción del tráfico"
        return "Ormuz abre la jornada bajo vigilancia y sin una normalización confirmada"
    else:
        if state == "OPEN_SEVERELY_RESTRICTED":
            return "Hormuz remains physically open, but normal traffic is still far away"
        if state == "OPEN_RESTRICTED":
            return "Hormuz stays open with restrictions as shipping weighs the risk"
        if state == "OPEN_NORMAL":
            return "Hormuz maintains operational traffic close to normal conditions"
        if state in {"CLOSED_CONFIRMED", "EFFECTIVELY_CLOSED"}:
            return "Routine traffic through Hormuz faces severe interruption"
        legacy = status.get("status")
        if legacy == "ABIERTO":
            return "Hormuz starts the day with operational transit and heightened monitoring"
        if legacy == "CERRADO":
            return "Hormuz enters the day under a major disruption of routine traffic"
        return "Hormuz starts the day under watch, with normalisation still unconfirmed"


def interpret_item(item: NewsItem, lang: str) -> str | None:
    if item.analytical:
        return None
    low = item.title.lower()
    if lang == "es":
        if item.topic == "maritime":
            if re.search(r"dwindl|plung|drop|fall|declin|slow|reduced|single-digit|trickle", low):
                return "los datos publicados apuntan a un tráfico todavía muy por debajo de la normalidad"
            if re.search(r"transit|passing|cross|traffic.*contin|ships? .*moving", low):
                return "se han comunicado nuevas señales de tránsito comercial a través del estrecho"
            return "el foco marítimo continúa puesto en la continuidad y el volumen real de los cruces"
        if item.topic == "security":
            if re.search(r"attack|struck|explosion|missile|projectile|drone|mine", low):
                return "la seguridad marítima sigue condicionada por incidentes o amenazas de carácter militar"
            return "los avisos de seguridad mantienen elevada la vigilancia sobre la ruta"
        if item.topic == "diplomacy":
            return "las conversaciones y propuestas políticas siguen influyendo en las expectativas sobre el régimen de paso"
        if item.topic == "energy":
            return "el mercado energético continúa pendiente de la continuidad física de las exportaciones y del coste de sustitución"
        if item.topic == "insurance":
            return "los costes de seguro y transporte siguen siendo una pieza central de la operatividad comercial"
        return None
    else:
        if item.topic == "maritime":
            if re.search(r"dwindl|plung|drop|fall|declin|slow|reduced|single-digit|trickle", low):
                return "published data point to traffic remaining far below normal levels"
            if re.search(r"transit|passing|cross|traffic.*contin|ships? .*moving", low):
                return "new evidence of commercial transit through the strait has been reported"
            return "the maritime focus remains on the continuity and actual volume of crossings"
        if item.topic == "security":
            if re.search(r"attack|struck|explosion|missile|projectile|drone|mine", low):
                return "maritime security remains constrained by military incidents or threats"
            return "security notices continue to justify heightened monitoring of the route"
        if item.topic == "diplomacy":
            return "talks and political proposals continue to shape expectations about the passage regime"
        if item.topic == "energy":
            return "energy markets remain focused on physical export continuity and replacement costs"
        if item.topic == "insurance":
            return "insurance and freight costs remain central to commercial operability"
        return None


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


def build_lead(
    status: dict[str, Any], operational: dict[str, Any], dt: datetime, lang: str
) -> str:
    state, summary, confidence = display_state(status, operational, lang)
    dims = dimensions(operational, lang)
    if lang == "es":
        detail = ""
        if dims:
            parts = []
            if dims.get("passage"):
                parts.append(f"paso físico {dims['passage'].lower()}")
            if dims.get("traffic"):
                parts.append(f"tráfico {dims['traffic'].lower()}")
            if dims.get("risk"):
                parts.append(f"riesgo {dims['risk'].lower()}")
            detail = "; " + ", ".join(parts) if parts else ""
        return (
            f"El estrecho de Ormuz llega a la jornada del {date_label(dt, 'es')} con un diagnóstico de "
            f"«{state}» y confianza {confidence_label(confidence, 'es')}{detail}. {summary} "
            "La edición de hoy separa lo que está ocurriendo en el agua de las declaraciones políticas y de la reacción de los mercados."
        )
    detail = ""
    if dims:
        parts = []
        if dims.get("passage"):
            parts.append(f"physical passage {dims['passage'].lower()}")
        if dims.get("traffic"):
            parts.append(f"traffic {dims['traffic'].lower()}")
        if dims.get("risk"):
            parts.append(f"risk {dims['risk'].lower()}")
        detail = "; " + ", ".join(parts) if parts else ""
    return (
        f"The Strait of Hormuz enters {date_label(dt, 'en')} with an assessment of “{state}” and "
        f"{confidence_label(confidence, 'en')} confidence{detail}. {summary} "
        "Today's edition separates what is happening on the water from political statements and market reaction."
    )


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
            return "La principal diferencia frente a la edición anterior está en la propia clasificación operativa: el balance de evidencias ha desplazado el diagnóstico. La web registra el cambio y conserva la edición previa para poder auditarlo."
        if changed:
            labels = {"passage":"paso físico", "traffic":"tráfico", "access":"acceso", "risk":"riesgo", "legal":"marco político/legal"}
            return "El estado general no cambia, pero sí lo hacen algunas dimensiones: " + ", ".join(labels[x] for x in changed) + ". Esto evita tratar como idénticas dos jornadas que comparten etiqueta pero no condiciones operativas."
        return "Frente a la edición anterior no aparece un cambio material en la clasificación. La continuidad, sin embargo, no equivale a normalidad: el sistema mantiene separados el nivel de tráfico, las restricciones y el riesgo."
    else:
        if state_changed:
            return "The main difference from the previous edition is the operational classification itself: the balance of evidence has shifted the assessment. The site records the change and preserves the previous edition for auditability."
        if changed:
            labels = {"passage":"physical passage", "traffic":"traffic", "access":"access", "risk":"risk", "legal":"political/legal framework"}
            return "The headline state is unchanged, but some dimensions have moved: " + ", ".join(labels[x] for x in changed) + ". This prevents two days with the same label from being treated as operationally identical."
        return "There is no material change in the classification from the previous edition. Continuity does not mean normality: traffic intensity, restrictions and risk remain separate variables."


def section_paragraph(topic: str, items: list[NewsItem], lang: str) -> str:
    relevant = [x for x in items if x.topic == topic]
    interpretable = [(x, interpret_item(x, lang)) for x in relevant]
    interpretable = [(x, clause) for x, clause in interpretable if clause]
    if lang == "es":
        if not relevant:
            fallbacks = {
                "maritime": "No se ha detectado una nueva señal marítima de suficiente calidad para modificar la lectura de la jornada. El monitor mantiene como referencia el último diagnóstico operativo válido.",
                "security": "No hay una novedad de seguridad suficientemente sólida para elevar o rebajar por sí sola la evaluación. Los avisos oficiales siguen teniendo prioridad sobre titulares aislados.",
                "diplomacy": "La diplomacia no aporta hoy una señal suficientemente clara para modificar la conclusión física sobre el paso. Las declaraciones se mantienen separadas de la evidencia de tránsito.",
                "energy": "Sin una novedad energética material, la lectura continúa centrada en la disponibilidad física del corredor y en la prima de riesgo asociada.",
                "insurance": "No aparece una variación verificable de seguros o fletes que merezca una conclusión independiente en esta edición.",
            }
            return fallbacks[topic]
        sources = []
        for item in relevant:
            if item.source not in sources:
                sources.append(item.source)
        if interpretable:
            clauses = []
            used_sources = []
            for item, clause in interpretable[:2]:
                clauses.append(clause)
                used_sources.append(item.source)
            source_text = " y ".join(dict.fromkeys(used_sources))
            return f"Las novedades seleccionadas en este frente proceden de {source_text}. En conjunto, {clauses[0]}" + (f"; además, {clauses[1]}" if len(clauses) > 1 else "") + ". La conclusión se limita a lo que permiten sostener las fuentes enlazadas y no convierte titulares de opinión en hechos."
        return f"Hay {len(relevant)} actualización(es) reciente(s) en esta área, procedentes de {', '.join(sources[:3])}. Se conservan como contexto porque sus titulares son analíticos, interrogativos o no permiten extraer por sí solos una afirmación operativa segura."
    else:
        if not relevant:
            fallbacks = {
                "maritime": "No new maritime signal of sufficient quality has been detected to alter today's reading. The monitor keeps the latest valid operational assessment as its reference.",
                "security": "There is no sufficiently strong security development to raise or lower the assessment on its own. Official notices continue to outrank isolated headlines.",
                "diplomacy": "Diplomacy does not provide a sufficiently clear signal today to change the physical assessment of passage. Political statements remain separate from transit evidence.",
                "energy": "Without a material energy development, the focus remains on the physical availability of the corridor and the associated risk premium.",
                "insurance": "No verifiable change in insurance or freight conditions justifies a separate conclusion in this edition.",
            }
            return fallbacks[topic]
        sources = []
        for item in relevant:
            if item.source not in sources:
                sources.append(item.source)
        if interpretable:
            clauses = []
            used_sources = []
            for item, clause in interpretable[:2]:
                clauses.append(clause)
                used_sources.append(item.source)
            source_text = " and ".join(dict.fromkeys(used_sources))
            return f"Selected developments in this area come from {source_text}. Taken together, {clauses[0]}" + (f"; in addition, {clauses[1]}" if len(clauses) > 1 else "") + ". The conclusion is limited to what the linked sources support and does not turn opinion headlines into facts."
        return f"There are {len(relevant)} recent update(s) in this area from {', '.join(sources[:3])}. They are retained as context because their headlines are analytical, interrogative or insufficient on their own for a safe operational claim."


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
        "author": {"@type": "Organization", "name": "Redacción de Estrecho Ormuz" if lang == "es" else "Estrecho Ormuz News Desk"},
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
) -> str:
    title = headline_for(status, operational, new_items, lang)
    state_label, summary, confidence = display_state(status, operational, lang)
    lead = build_lead(status, operational, local_dt, lang)
    change = change_paragraph(current_fp, previous_fp, lang)
    watch = watchlist(status, operational, lang)
    sources_html = make_sources(news, lang)
    topics = ["maritime", "security", "diplomacy", "energy", "insurance"]
    date_text = date_label(local_dt, lang)
    byline = "Redacción automatizada con control de consistencia" if lang == "es" else "Automated newsroom with consistency checks"
    read_time = "Lectura: 6–8 min" if lang == "es" else "Reading time: 6–8 min"
    kicker = "EL DIARIO DE ORMUZ" if lang == "es" else "HORMUZ DAILY"
    edition = "Edición de la mañana" if lang == "es" else "Morning edition"
    archive_note = (
        "Edición archivada por cambio material" if lang == "es" else "Archived because of material change"
    ) if archive else (
        "Edición viva · se actualiza una vez al día" if lang == "es" else "Live edition · updated once a day"
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
        paragraph = section_paragraph(topic, new_items, lang)
        relevant = [x for x in new_items if x.topic == topic]
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
    reason_html = "".join(f"<li>{safe(item)}</li>" for item in material_reasons)
    quality_note = (
        "Esta edición alcanza el umbral para archivo permanente."
        if lang == "es" and material_score_value >= MATERIAL_THRESHOLD
        else "Esta edición no crea una nueva URL histórica: se actualiza la portada del diario para evitar contenido repetitivo."
        if lang == "es"
        else "This edition reaches the threshold for permanent archiving."
        if material_score_value >= MATERIAL_THRESHOLD
        else "This edition does not create a new historical URL: the live diary is updated instead, avoiding repetitive content."
    )
    description = summary or lead[:220]
    schema = structured_data(title, description, canonical, iso_z(local_dt.astimezone(timezone.utc)), lang, archive)
    alternate = (
        canonical.replace("/diario/", "/diary/").replace("/diario.html", "/en-diary.html")
        if lang == "es"
        else canonical.replace("/diary/", "/diario/").replace("/en-diary.html", "/diario.html")
    )

    return f'''<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{safe(title)} | {safe(kicker.title())}</title>
<meta name="description" content="{safe(description[:250])}"/>
<meta name="robots" content="index,follow,max-image-preview:large"/>
<meta name="theme-color" content="#07111f"/>
<link rel="canonical" href="{safe(canonical)}"/>
<link rel="alternate" hreflang="{lang}" href="{safe(canonical)}"/>
<link rel="alternate" hreflang="{'en' if lang == 'es' else 'es'}" href="{safe(alternate)}"/>
<link rel="alternate" hreflang="x-default" href="{safe(canonical if lang == 'es' else alternate)}"/>
<link rel="stylesheet" href="/styles.css"/>
<link rel="stylesheet" href="/v11.css"/>
<link rel="stylesheet" href="/diario-v8.css"/>
<meta property="og:type" content="article"/>
<meta property="og:site_name" content="Estrecho Ormuz"/>
<meta property="og:title" content="{safe(title)}"/>
<meta property="og:description" content="{safe(description[:250])}"/>
<meta property="og:url" content="{safe(canonical)}"/>
<meta property="og:image" content="https://estrechoormuz.com/social-card.png"/>
<meta name="twitter:card" content="summary_large_image"/>
<script type="application/ld+json">{schema}</script>
</head>
<body class="journal-page" data-lang="{lang}">
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
<p class="journal-lead">{safe(lead)}</p>
<section class="journal-section journal-change"><h2>{'Qué ha cambiado desde ayer' if lang == 'es' else 'What changed since yesterday'}</h2><p>{safe(change)}</p></section>
{sections}
<section class="journal-section journal-watch"><h2>{'Qué vigilar en las próximas 24 horas' if lang == 'es' else 'What to watch over the next 24 hours'}</h2><ul>{watch_html}</ul></section>
<section class="journal-section journal-sources"><div class="journal-section-title"><div><span>{'Trazabilidad' if lang == 'es' else 'Traceability'}</span><h2>{'Fuentes y noticias consultadas' if lang == 'es' else 'Sources and news reviewed'}</h2></div></div><ul>{sources_html}</ul></section>
<section class="journal-method-note"><h2>{'Cómo se ha escrito esta edición' if lang == 'es' else 'How this edition was produced'}</h2><p>{'El texto se genera automáticamente a partir de status.json, Operational Intelligence cuando está disponible y noticias recientes de fuentes seleccionadas. Las reglas separan hechos operativos de opinión, preguntas y declaraciones políticas. No se inventan citas ni se atribuyen hechos que no puedan sostenerse con los datos enlazados.' if lang == 'es' else 'The text is generated automatically from status.json, Operational Intelligence when available, and recent news from selected sources. Rules separate operational facts from opinion, questions and political statements. Quotes are not invented and claims are not attributed beyond what the linked data can support.'}</p><p>{safe(quality_note)}</p><details><summary>{'Por qué se archivó o no esta edición' if lang == 'es' else 'Why this edition was or was not archived'}</summary><p>{'Puntuación de novedad' if lang == 'es' else 'Novelty score'}: <strong>{material_score_value}</strong> / {MATERIAL_THRESHOLD}.</p><ul>{reason_html or '<li>Continuidad sin novedad material suficiente.</li>'}</ul></details></section>
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
        cards.append(
            f'<article class="journal-archive-card"><time>{safe(item.get("date"))}</time><h2><a href="{safe(url)}">{safe(title)}</a></h2><p>{safe(summary)}</p><span>{"Novedad" if es else "Novelty"}: {safe(item.get("material_score"))}</span></article>'
        )
    canonical = f"{BASE_URL}/{'diario/' if es else 'diary/'}"
    alt = f"{BASE_URL}/{'diary/' if es else 'diario/'}"
    return f'''<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/><title>{'Archivo de El Diario de Ormuz' if es else 'Hormuz Daily Archive'}</title><meta name="description" content="{'Archivo de ediciones materiales de El Diario de Ormuz.' if es else 'Archive of material Hormuz Daily editions.'}"/><meta name="robots" content="index,follow,max-image-preview:large"/><link rel="canonical" href="{canonical}"/><link rel="alternate" hreflang="{lang}" href="{canonical}"/><link rel="alternate" hreflang="{'en' if es else 'es'}" href="{alt}"/><link rel="stylesheet" href="/styles.css"/><link rel="stylesheet" href="/v11.css"/><link rel="stylesheet" href="/diario-v8.css"/></head><body class="journal-page"> <header class="journal-header"><div class="journal-header-inner"><a class="journal-brand" href="{'/' if es else '/en.html'}"><strong>ESTRECHO ORMUZ</strong><small>{'El Diario de Ormuz' if es else 'Hormuz Daily'}</small></a>{nav(lang)}</div></header><main class="journal-main"><section class="journal-archive-hero"><span class="section-kicker">{'HEMEROTECA' if es else 'ARCHIVE'}</span><h1>{'El Diario de Ormuz' if es else 'Hormuz Daily'}</h1><p>{'Solo se conservan como páginas indexables las jornadas con cambios o novedades suficientes. Los días de continuidad actualizan la edición viva sin fabricar páginas repetitivas.' if es else 'Only days with sufficient change or new information are kept as indexable pages. Continuity days update the live edition without manufacturing repetitive pages.'}</p></section><section class="journal-archive-grid">{''.join(cards) if cards else '<p>Aún no hay ediciones archivadas.</p>' if es else '<p>No archived editions yet.</p>'}</section></main></body></html>'''


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
  <div><span class="section-kicker">{'EL DIARIO DE ORMUZ' if es else 'HORMUZ DAILY'}</span><h2 id="journal-home-title">{safe(title)}</h2><p>{safe(summary)}</p><div class="journal-home-meta"><span>{safe(edition.get('date'))}</span><span>{'Crónica diaria automática y trazable' if es else 'Daily automated, traceable briefing'}</span></div></div>
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
    # Two UTC cron slots cover CET/CEST. 08:xx is a fallback if the 07:xx run was delayed/missed.
    return local_now.hour in {7, 8}


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
        print(f"Diario V8: ejecución omitida por horario/idempotencia ({local_now.isoformat()}).")
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

    news = evidence_as_news(status, now)
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
    independent = {item.source.lower() for item in new_items}
    material = score >= MATERIAL_THRESHOLD and (len(independent) >= 2 or score >= 6)

    date_iso = local_now.date().isoformat()
    generated_at = iso_z(now)
    title_es = headline_for(status, operational, new_items, "es")
    title_en = headline_for(status, operational, new_items, "en")
    _, summary_es, _ = display_state(status, operational, "es")
    _, summary_en, _ = display_state(status, operational, "en")

    live_es = render_page(
        status=status, operational=operational, news=news, new_items=new_items,
        previous_fp=previous_fp, current_fp=current_fp, local_dt=local_now,
        lang="es", canonical=f"{BASE_URL}/diario.html", archive=False,
        material_score_value=score, material_reasons=reasons,
    )
    live_en = render_page(
        status=status, operational=operational, news=news, new_items=new_items,
        previous_fp=previous_fp, current_fp=current_fp, local_dt=local_now,
        lang="en", canonical=f"{BASE_URL}/en-diary.html", archive=False,
        material_score_value=score, material_reasons=reasons,
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
        "independent_sources": len(independent),
        "topics": dict(Counter(item.topic for item in new_items)),
        "fingerprint": current_fp,
        "news": [asdict(item) for item in news[:15]],
        "fetch_errors": fetch_errors,
        "url_es": f"{BASE_URL}/diario.html",
        "url_en": f"{BASE_URL}/en-diary.html",
    }

    # Store a compact daily data record every day, even when no historical HTML is created.
    dump_json(root / "journal-data" / f"{date_iso}.json", edition)
    dump_json(root / "journal-latest.json", edition)

    if material:
        archive_es_url = f"{BASE_URL}/diario/{date_iso}.html"
        archive_en_url = f"{BASE_URL}/diary/{date_iso}.html"
        archive_es = render_page(
            status=status, operational=operational, news=news, new_items=new_items,
            previous_fp=previous_fp, current_fp=current_fp, local_dt=local_now,
            lang="es", canonical=archive_es_url, archive=True,
            material_score_value=score, material_reasons=reasons,
        )
        archive_en = render_page(
            status=status, operational=operational, news=news, new_items=new_items,
            previous_fp=previous_fp, current_fp=current_fp, local_dt=local_now,
            lang="en", canonical=archive_en_url, archive=True,
            material_score_value=score, material_reasons=reasons,
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
        "version": 8,
        "last_date": date_iso,
        "last_generated_at": generated_at,
        "fingerprint": current_fp,
        "seen_keys": list(dict.fromkeys(seen_today + list(seen)))[:500],
        "last_material_archive_date": date_iso if material else previous_state.get("last_material_archive_date"),
        "last_material_score": score,
    }
    dump_json(root / "journal-state.json", state_out)
    dump_json(root / "journal-health.json", {
        "version": 8,
        "generated_at": generated_at,
        "ok": True,
        "date": date_iso,
        "material_score": score,
        "material_archive": material,
        "news_considered": len(news),
        "new_articles": len(new_items),
        "independent_sources": len(independent),
        "fetch_errors": fetch_errors,
        "operational_intelligence_used": bool(operational),
    })

    print(
        f"El Diario de Ormuz V8 listo: {date_iso} · score={score} · "
        f"archivo={'sí' if material else 'no'} · noticias={len(news)} · nuevas={len(new_items)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
