#!/usr/bin/env python3
"""Operational Intelligence V7 for Estrecho Ormuz.

Companion assessment layer: it does not replace the conservative legacy engine.
It separately evaluates physical passage, traffic intensity, access restrictions
and maritime risk.
"""
from __future__ import annotations

import argparse
import email.utils
import html
import json
import math
import re
import statistics
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

VERSION = 7
USER_AGENT = "Mozilla/5.0 Estrecho-Ormuz-Operational-Intelligence/7"
BASELINE_VESSELS_PER_DAY = 138.0

SOURCE_TIERS = {
    "ukmto": 5, "jmic": 5, "imo": 5, "u.s. marad": 5, "marad": 5,
    "u.s. centcom": 5, "centcom": 5, "reuters": 4, "associated press": 4,
    "ap news": 4, "lloyd's list": 4, "lloyds list": 4, "kpler": 4,
    "s&p global": 4, "bbc": 3, "financial times": 3, "bloomberg": 3,
    "the guardian": 3, "marinelink": 2, "seatrade maritime": 2,
    "al jazeera": 2,
}

STATE_META = {
    "OPEN_NORMAL": {
        "family": "OPEN", "label_es": "ABIERTO", "label_en": "OPEN",
        "operational_es": "Tránsito operativo normal",
        "operational_en": "Normal operational transit",
    },
    "OPEN_RESTRICTED": {
        "family": "OPEN", "label_es": "ABIERTO CON RESTRICCIONES",
        "label_en": "OPEN WITH RESTRICTIONS",
        "operational_es": "Paso físico confirmado con restricciones",
        "operational_en": "Physical passage confirmed with restrictions",
    },
    "OPEN_SEVERELY_RESTRICTED": {
        "family": "OPEN", "label_es": "ABIERTO · TRÁNSITO MUY RESTRINGIDO",
        "label_en": "OPEN · SEVERELY RESTRICTED TRANSIT",
        "operational_es": "Hay paso físico, pero el flujo está severamente degradado",
        "operational_en": "Physical passage exists, but flows are severely degraded",
    },
    "EFFECTIVELY_CLOSED": {
        "family": "CLOSED", "label_es": "EFECTIVAMENTE CERRADO",
        "label_en": "EFFECTIVELY CLOSED",
        "operational_es": "El tráfico comercial ordinario está prácticamente detenido",
        "operational_en": "Routine commercial traffic is effectively halted",
    },
    "CLOSED_CONFIRMED": {
        "family": "CLOSED", "label_es": "CERRADO", "label_en": "CLOSED",
        "operational_es": "Cierre operativo confirmado",
        "operational_en": "Operational closure confirmed",
    },
    "UNVERIFIED": {
        "family": "UNKNOWN", "label_es": "SIN DATOS OPERATIVOS RECIENTES",
        "label_en": "NO RECENT OPERATIONAL DATA",
        "operational_es": "No hay datos recientes suficientes para determinar el paso físico",
        "operational_en": "Recent evidence is insufficient to determine physical passage",
    },
}

KIND_LABELS = {
    "TRANSIT_CONFIRMED": ("Tránsito confirmado", "Confirmed transit"),
    "TRAFFIC_PRESENT": ("Tráfico observado", "Traffic observed"),
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

@dataclass
class Signal:
    kind: str
    title: str
    source: str
    url: str
    published_at: str
    tier: int
    weight: float
    provider: str
    details: str = ""
    traffic_ratio: float | None = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    text = str(value or "").strip()
    if not text:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass
    try:
        parsed = email.utils.parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, value: Any) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    previous = path.read_text(encoding="utf-8") if path.exists() else None
    if previous != text:
        path.write_text(text, encoding="utf-8")


def normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def source_tier(name: str) -> int:
    key = normalize(name).lower()
    for token, tier in SOURCE_TIERS.items():
        if token in key:
            return tier
    return 1


def source_weight(tier: int) -> float:
    return {5: 5.0, 4: 4.0, 3: 3.0, 2: 2.0, 1: 1.0}.get(tier, 1.0)


def age_multiplier(published_at: str, now: datetime) -> float:
    hours = max(0.0, (now - parse_dt(published_at)).total_seconds() / 3600)
    if hours <= 24: return 1.0
    if hours <= 48: return 0.9
    if hours <= 72: return 0.78
    if hours <= 96: return 0.62
    if hours <= 120: return 0.42
    return 0.0


def headline_is_question_or_analysis(text: str) -> bool:
    low = normalize(text).lower()
    return (
        "?" in low
        or bool(re.match(r"^(why|how|what|whether|can|could|would|will|is|are|does|do)\b", low))
        or bool(re.search(r"\b(opinion|analysis|explainer|keeps? insisting|claims?|argues?)\b", low))
    )


def add_signal(out: list[Signal], kind: str, title: str, source: str, url: str,
               published_at: str, provider: str, *, details: str = "",
               traffic_ratio: float | None = None, tier: int | None = None,
               weight_multiplier: float = 1.0) -> None:
    t = tier if tier is not None else source_tier(source)
    out.append(Signal(kind, normalize(title), normalize(source) or "Unknown source",
                      normalize(url), published_at, t, source_weight(t) * weight_multiplier,
                      provider, normalize(details), traffic_ratio))


def classify_text_record(title: str, source: str, url: str, published_at: str,
                         provider: str, *, description: str = "",
                         context_hormuz: bool = False) -> list[Signal]:
    out: list[Signal] = []
    combined = normalize(f"{title}. {description}")
    low = combined.lower()
    if not low:
        return out
    hormuz = context_hormuz or "hormuz" in low
    analytical = headline_is_question_or_analysis(title)

    direct_patterns = (
        r"\b(?:ships?|vessels?|tankers?|carriers?)\b.{0,90}\b(?:transit|transiting|passed|passing|crossed|crossing|moving)\b",
        r"\b(?:traffic|transits?)\b.{0,90}\b(?:continues?|continued|remains?|remained|moving|flows?)\b",
        r"\b(?:traffic|vessel traffic|shipping traffic)\s+through\s+(?:the\s+)?(?:strait of\s+)?hormuz\b",
        r"\bships?\s+keep\s+moving\s+through\s+hormuz\b",
        r"\btransits?\s+through\s+hormuz\b",
    )
    if hormuz and not analytical and any(re.search(p, low) for p in direct_patterns):
        add_signal(out, "TRANSIT_CONFIRMED", title, source, url, published_at, provider)
    if hormuz and not analytical and re.search(
        r"\b(?:traffic|shipping|vessels?|ships?|tankers?|transits?)\b.{0,70}\b(?:little changed|steady|stable|continues?|ongoing|present)\b", low):
        add_signal(out, "TRAFFIC_PRESENT", title, source, url, published_at, provider, weight_multiplier=0.85)
    if hormuz and re.search(r"\b(?:reduced levels?|reduced|slow|slowed|dwindl(?:e|es|ed)|plung(?:e|es|ed)|fall(?:en|ing)?|declin(?:e|ed|ing)|suppression)\b", low):
        add_signal(out, "TRAFFIC_REDUCED", title, source, url, published_at, provider)
    if hormuz and re.search(r"\b(?:single[- ]digit|trickle|freefall|collapsed?|collapse|near[- ]total pause|virtually disappeared|80%|90%|severely reduced)\b", low):
        add_signal(out, "TRAFFIC_SEVERELY_REDUCED", title, source, url, published_at, provider, weight_multiplier=1.15)
    if hormuz and re.search(r"\b(?:normal traffic|traffic returned to normal|normal transit levels?|freely open)\b", low):
        add_signal(out, "TRAFFIC_NORMAL", title, source, url, published_at, provider)
    if hormuz and re.search(r"\b(?:no commercial traffic|traffic (?:is |was |has been )?(?:halted|stopped)|shipping (?:is |was |has been )?(?:halted|stopped)|near[- ]total temporary pause|effectively closed|impassable)\b", low):
        add_signal(out, "CLOSURE_EFFECTIVE", title, source, url, published_at, provider, weight_multiplier=1.2)
    if hormuz and re.search(r"\b(?:declares?|declared|says|vows|threatens?)\b.{0,80}\b(?:closed|closure|block(?:ed|ing)?)\b", low):
        add_signal(out, "FORMAL_CLOSURE_CLAIM", title, source, url, published_at, provider, weight_multiplier=0.7)
    if hormuz and re.search(r"\b(?:fee|fees|toll|tolls|iranian[- ]controlled route|controlled route|clearance|inspection|visit-and-search|blockade|selective|bar .*vessels|ban .*vessels|restricted|restrictions?)\b", low):
        add_signal(out, "ACCESS_RESTRICTED", title, source, url, published_at, provider)
    if hormuz and re.search(r"\b(?:neutral transit is permitted|neutral transit permitted|safe passage|passage remains possible)\b", low):
        add_signal(out, "NEUTRAL_TRANSIT_PERMITTED", title, source, url, published_at, provider)
    if hormuz and re.search(r"\b(?:severe|extreme|critical|projectile|attack|attacks|struck|warning shots|mine risk|mines?|hostile action|harassment|uav)\b", low):
        add_signal(out, "RISK_SEVERE", title, source, url, published_at, provider)
    elif hormuz and re.search(r"\b(?:elevated risk|high risk|war risk|caution|threat)\b", low):
        add_signal(out, "RISK_ELEVATED", title, source, url, published_at, provider)
    return out


def seed_signals(root: Path, now: datetime) -> list[Signal]:
    data = load_json(root / "operational-intelligence-seed.json", {})
    if parse_dt(data.get("expires_at")) <= now:
        return []
    output: list[Signal] = []
    for item in data.get("signals", []):
        if not isinstance(item, dict): continue
        add_signal(output, str(item.get("kind") or ""), str(item.get("title") or ""),
                   str(item.get("source") or ""), str(item.get("url") or ""),
                   str(item.get("published_at") or ""), "seed-primary",
                   details=str(item.get("details") or ""),
                   traffic_ratio=item.get("traffic_ratio"),
                   tier=int(item.get("tier") or source_tier(str(item.get("source") or ""))),
                   weight_multiplier=float(item.get("weight_multiplier") or 1.0))
    return output


def signals_from_existing_status(root: Path) -> list[Signal]:
    data = load_json(root / "status.json", {})
    output: list[Signal] = []
    evidence = data.get("evidence") or []
    if not isinstance(evidence, list): return output
    for item in evidence:
        if not isinstance(item, dict): continue
        output.extend(classify_text_record(
            str(item.get("title") or ""), str(item.get("source_name") or ""),
            str(item.get("source_url") or ""),
            str(item.get("published_at") or item.get("observed_at") or ""),
            "legacy-engine", context_hormuz=True))
    return output


def request_bytes(url: str, timeout: int = 18) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
        "Accept": "application/rss+xml,application/xml,text/html;q=0.9,*/*;q=0.7",
        "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def google_news_url(query: str) -> str:
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"})


def fetch_google_news(now: datetime) -> tuple[list[Signal], list[str]]:
    queries = (
        '"Strait of Hormuz" (traffic OR transits OR vessels OR shipping) when:4d',
        '"Strait of Hormuz" (open OR reopened OR closed OR closure) when:4d',
        '"Strait of Hormuz" (attack OR restrictions OR insurance OR route) when:4d',
        '"Hormuz" (Kpler OR UKMTO OR JMIC OR Lloyds OR Reuters) when:4d',
    )
    signals: list[Signal] = []; errors: list[str] = []
    for query in queries:
        try:
            tree = ET.fromstring(request_bytes(google_news_url(query)))
        except Exception as exc:
            errors.append(f"Google News: {type(exc).__name__}: {exc}"); continue
        for item in tree.findall("./channel/item"):
            title = normalize(item.findtext("title")); link = normalize(item.findtext("link"))
            published = normalize(item.findtext("pubDate")); source_node = item.find("source")
            source = normalize(source_node.text if source_node is not None else "")
            parsed = parse_dt(published)
            published_iso = iso_z(parsed) if parsed.year > 1970 else published
            signals.extend(classify_text_record(title, source, link, published_iso,
                                                "Google News RSS", context_hormuz=True))
    return signals, errors


def fetch_lloyds_hot_topic(now: datetime) -> tuple[list[Signal], list[str]]:
    url = "https://www.lloydslist.com/hot-topics/strait-of-hormuz-crisis"
    try:
        raw = request_bytes(url).decode("utf-8", errors="ignore")
    except Exception as exc:
        return [], [f"Lloyd's List: {type(exc).__name__}: {exc}"]
    text = normalize(html.unescape(re.sub(r"<[^>]+>", " ", raw)))
    out: list[Signal] = []
    if re.search(r"\b(?:extreme|severe|attack|attacks|war risk)\b", text, re.I):
        add_signal(out, "RISK_SEVERE", "Lloyd's List Hormuz crisis monitor reports severe/extreme shipping risk",
                   "Lloyd's List", url, iso_z(now), "Lloyd's List hot topic", weight_multiplier=0.75)
    if re.search(r"\b(?:fees?|tolls?|controlled route|restrictions?)\b", text, re.I):
        add_signal(out, "ACCESS_RESTRICTED", "Lloyd's List Hormuz crisis monitor reports routing/access constraints",
                   "Lloyd's List", url, iso_z(now), "Lloyd's List hot topic", weight_multiplier=0.65)
    return out, []


def dedupe(signals: list[Signal]) -> list[Signal]:
    seen = set(); result = []
    for item in sorted(signals, key=lambda x: parse_dt(x.published_at), reverse=True):
        key = (item.kind, normalize(item.source).lower(), re.sub(r"\W+", " ", item.title.lower()).strip())
        if key in seen: continue
        seen.add(key); result.append(item)
    return result


def weighted(item: Signal, now: datetime) -> float:
    return item.weight * age_multiplier(item.published_at, now)


def independent_sources(signals: list[Signal], kinds: set[str], now: datetime) -> set[str]:
    return {normalize(i.source).lower() for i in signals if i.kind in kinds and age_multiplier(i.published_at, now) > 0}


def dimension_labels(value: str, lang: str) -> str:
    mapping = {
        "PASSAGE_CONFIRMED": ("Confirmado", "Confirmed"),
        "PASSAGE_NOT_CONFIRMED": ("No confirmado", "Not confirmed"),
        "NORMAL": ("Normal", "Normal"), "REDUCED": ("Reducido", "Reduced"),
        "SEVERELY_REDUCED": ("Muy reducido", "Severely reduced"),
        "NEAR_HALT": ("Casi detenido", "Near halt"),
        "UNRESTRICTED": ("Sin restricciones relevantes", "No material restrictions"),
        "RESTRICTED": ("Restringido", "Restricted"),
        "SELECTIVE": ("Selectivo / condicionado", "Selective / conditional"),
        "LOW": ("Bajo", "Low"), "ELEVATED": ("Elevado", "Elevated"),
        "SEVERE": ("Severo", "Severe"), "EXTREME": ("Extremo", "Extreme"),
        "OPEN_LEGAL": ("Sin cierre formal reconocido", "No recognised formal closure"),
        "DISPUTED": ("Régimen disputado", "Disputed regime"),
        "CLOSURE_CLAIMED": ("Cierre declarado por una parte", "Closure claimed by one party"),
    }
    pair = mapping.get(value, (value, value)); return pair[0 if lang == "es" else 1]


def assess(signals: list[Signal], now: datetime, legacy: dict[str, Any] | None = None) -> dict[str, Any]:
    legacy = legacy or {}; fresh = [i for i in dedupe(signals) if age_multiplier(i.published_at, now) > 0]
    open_kinds = {"TRANSIT_CONFIRMED", "TRAFFIC_PRESENT", "NEUTRAL_TRANSIT_PERMITTED"}
    closed_kinds = {"CLOSURE_EFFECTIVE"}
    reduced_kinds = {"TRAFFIC_REDUCED", "TRAFFIC_SEVERELY_REDUCED"}
    open_score = sum(weighted(i, now) * (1.30 if i.kind == "TRANSIT_CONFIRMED" else 1.0 if i.kind == "NEUTRAL_TRANSIT_PERMITTED" else 0.75) for i in fresh if i.kind in open_kinds)
    closed_score = sum(weighted(i, now) * 1.25 for i in fresh if i.kind in closed_kinds)
    reduced_score = sum(weighted(i, now) for i in fresh if i.kind in reduced_kinds)
    severe_traffic_score = sum(weighted(i, now) for i in fresh if i.kind == "TRAFFIC_SEVERELY_REDUCED")
    restriction_score = sum(weighted(i, now) for i in fresh if i.kind == "ACCESS_RESTRICTED")
    risk_score = sum(weighted(i, now) for i in fresh if i.kind in {"RISK_SEVERE", "RISK_ELEVATED"})
    formal_claim_score = sum(weighted(i, now) for i in fresh if i.kind == "FORMAL_CLOSURE_CLAIM")
    ratios = [float(i.traffic_ratio) for i in fresh if i.traffic_ratio is not None and math.isfinite(float(i.traffic_ratio)) and 0 <= float(i.traffic_ratio) <= 1.5]
    ratio = statistics.median(ratios) if ratios else None
    open_sources = independent_sources(fresh, open_kinds, now); closed_sources = independent_sources(fresh, closed_kinds, now)
    latest_transit = max((parse_dt(i.published_at) for i in fresh if i.kind == "TRANSIT_CONFIRMED"), default=datetime.min.replace(tzinfo=timezone.utc))
    passage_confirmed = latest_transit > now - timedelta(hours=96) and (any(i.tier >= 5 and i.kind in open_kinds for i in fresh) or len(open_sources) >= 2 or open_score >= 7.0)
    closure_confirmed = closed_score >= 8.0 and len(closed_sources) >= 2 and latest_transit < now - timedelta(hours=48)
    passage = "PASSAGE_CONFIRMED" if passage_confirmed else "PASSAGE_NOT_CONFIRMED"
    if ratio is not None:
        traffic = "NORMAL" if ratio >= .70 else "REDUCED" if ratio >= .35 else "SEVERELY_REDUCED" if ratio >= .05 else "NEAR_HALT"
    elif severe_traffic_score >= 3: traffic = "SEVERELY_REDUCED"
    elif reduced_score >= 3: traffic = "REDUCED"
    elif closed_score >= 6: traffic = "NEAR_HALT"
    else: traffic = "REDUCED" if passage_confirmed else "SEVERELY_REDUCED"
    access = "SELECTIVE" if restriction_score >= 5 else "RESTRICTED" if restriction_score >= 2 or risk_score >= 5 else "UNRESTRICTED"
    risk = "EXTREME" if risk_score >= 8 else "SEVERE" if risk_score >= 3.5 else "ELEVATED" if risk_score > 0 else "LOW"
    legal = "CLOSURE_CLAIMED" if formal_claim_score >= 3 else "DISPUTED" if restriction_score >= 3 else "OPEN_LEGAL"
    if closure_confirmed: state = "CLOSED_CONFIRMED" if formal_claim_score >= 3 else "EFFECTIVELY_CLOSED"
    elif passage_confirmed:
        if traffic in {"SEVERELY_REDUCED", "NEAR_HALT"} or risk in {"SEVERE", "EXTREME"} or access == "SELECTIVE": state = "OPEN_SEVERELY_RESTRICTED"
        elif traffic == "REDUCED" or access == "RESTRICTED" or risk == "ELEVATED": state = "OPEN_RESTRICTED"
        else: state = "OPEN_NORMAL"
    else: state = "UNVERIFIED"
    meta = STATE_META[state]
    primary_sources = {normalize(i.source).lower() for i in fresh if i.tier >= 4 and weighted(i, now) > 0}
    confidence = "ALTA" if state != "UNVERIFIED" and len(primary_sources) >= 2 and any(i.tier >= 5 for i in fresh) else "MEDIA" if state != "UNVERIFIED" and (primary_sources or len(open_sources | closed_sources) >= 2) else "BAJA"
    summaries = {
        "OPEN_SEVERELY_RESTRICTED": (
            "Hay tránsitos comerciales confirmados a través del estrecho, pero el flujo está muy por debajo de la normalidad y las condiciones de seguridad y acceso siguen siendo severas. No está físicamente cerrado: está operativo de forma muy limitada.",
            "Commercial transits through the strait are confirmed, but flows remain far below normal and security/access conditions are severe. It is not physically closed; it is operating on a highly constrained basis."),
        "OPEN_RESTRICTED": ("El paso físico está confirmado y existe tráfico comercial, aunque persisten restricciones o riesgos que impiden hablar de normalidad.", "Physical passage and commercial traffic are confirmed, although restrictions or risks prevent a return to normal conditions."),
        "OPEN_NORMAL": ("El paso físico y el tráfico comercial se mantienen operativos sin restricciones materiales relevantes.", "Physical passage and commercial traffic remain operational without material restrictions."),
        "EFFECTIVELY_CLOSED": ("La evidencia disponible apunta a una interrupción efectiva del tráfico comercial ordinario.", "Available evidence indicates an effective interruption of routine commercial traffic."),
        "CLOSED_CONFIRMED": ("La evidencia disponible confirma una interrupción operativa del tráfico comercial ordinario.", "Available evidence confirms an operational interruption of routine commercial traffic."),
        "UNVERIFIED": ("No hay una confirmación operativa reciente suficiente para afirmar paso físico o interrupción efectiva. El sistema evita inferir el estado solo a partir de titulares.", "There is insufficient recent operational evidence to confirm physical passage or effective interruption. The system does not infer status from headlines alone."),
    }
    summary_es, summary_en = summaries[state]
    ranked = sorted(fresh, key=lambda i: (weighted(i, now), i.tier, parse_dt(i.published_at)), reverse=True)
    top = []; seen_titles = set()
    for item in ranked:
        tk = re.sub(r"\W+", " ", item.title.lower()).strip()
        if tk in seen_titles: continue
        seen_titles.add(tk)
        row = asdict(item); row["effective_weight"] = round(weighted(item, now), 3)
        row["kind_label_es"], row["kind_label_en"] = KIND_LABELS.get(item.kind, (item.kind, item.kind))
        top.append(row)
        if len(top) >= 8: break
    dims = {"passage": passage, "traffic": traffic, "access": access, "risk": risk, "legal": legal}
    return {
        "version": VERSION, "generated_at": iso_z(now), "state": state,
        "family": meta["family"], "label_es": meta["label_es"], "label_en": meta["label_en"],
        "operational_label_es": meta["operational_es"], "operational_label_en": meta["operational_en"],
        "confidence": confidence, "summary_es": summary_es, "summary_en": summary_en,
        "dimensions": dims,
        "dimension_labels_es": {k: dimension_labels(v, "es") for k, v in dims.items()},
        "dimension_labels_en": {k: dimension_labels(v, "en") for k, v in dims.items()},
        "traffic_ratio_estimate": round(ratio, 4) if ratio is not None else None,
        "scores": {"passage": round(open_score,3), "closure": round(closed_score,3), "traffic_reduction": round(reduced_score,3), "access_restriction": round(restriction_score,3), "risk": round(risk_score,3)},
        "source_counts": {"passage": len(open_sources), "closure": len(closed_sources), "primary_sources": len(primary_sources)},
        "latest_confirmed_transit_at": iso_z(latest_transit) if latest_transit.year > 1970 else None,
        "legacy_engine": {"status": legacy.get("status"), "operational_status": legacy.get("operational_status"), "confidence": legacy.get("confidence")},
        "evidence": top,
    }


def merge_previous_if_needed(assessment: dict[str, Any], previous: dict[str, Any], now: datetime) -> dict[str, Any]:
    if assessment.get("state") != "UNVERIFIED" or not isinstance(previous, dict): return assessment
    generated = parse_dt(previous.get("generated_at"))
    if previous.get("state") in {"OPEN_NORMAL", "OPEN_RESTRICTED", "OPEN_SEVERELY_RESTRICTED"} and generated > now - timedelta(hours=12):
        carried = dict(previous); carried["generated_at"] = iso_z(now); carried["confidence"] = "BAJA"; carried["carried_forward"] = True
        carried["summary_es"] = "No ha llegado una nueva prueba operativa suficiente en este ciclo. Se conserva durante un máximo de 12 horas el último diagnóstico operativo confirmado."
        carried["summary_en"] = "No new sufficient operational proof arrived in this cycle. The latest confirmed operational assessment is carried for up to 12 hours."
        return carried
    return assessment


def replace_element_content(document: str, element_id: str, content: str) -> str:
    pattern = re.compile(rf'(<(?P<tag>[a-zA-Z0-9]+)\b[^>]*\bid=["\']{re.escape(element_id)}["\'][^>]*>).*?(</(?P=tag)>)', re.I|re.S)
    return pattern.sub(lambda m: m.group(1)+content+m.group(3), document, count=1)


def confidence_text(value: str, lang: str) -> str:
    return {"es":{"ALTA":"Alta","MEDIA":"Media","BAJA":"Baja"},"en":{"ALTA":"High","MEDIA":"Medium","BAJA":"Low"}}[lang].get(value, value)


def render_block(a: dict[str, Any], lang: str) -> str:
    es = lang == "es"; labels = a["dimension_labels_es" if es else "dimension_labels_en"]
    rows = []
    for item in (a.get("evidence") or [])[:4]:
        rows.append(f'<li><span>{html.escape(str(item.get("kind_label_es" if es else "kind_label_en") or ""))}</span><a href="{html.escape(str(item.get("url") or "#"), quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(str(item.get("title") or ""))}</a><small>{html.escape(str(item.get("source") or ""))}</small></li>')
    evidence_html = "".join(rows) or ("<li><strong>No hay evidencia operativa reciente suficiente.</strong></li>" if es else "<li><strong>There is not enough recent operational evidence.</strong></li>")
    names = {"passage":"Paso físico","traffic":"Tráfico","access":"Acceso","risk":"Riesgo"} if es else {"passage":"Physical passage","traffic":"Traffic","access":"Access","risk":"Risk"}
    metrics = "".join(f'<div class="opintel-metric"><span>{names[k]}</span><strong data-opintel-{k}>{html.escape(str(labels[k]))}</strong></div>' for k in ("passage","traffic","access","risk"))
    return f'''<!-- OPERATIONAL_INTELLIGENCE_V7_START -->
<section class="content-section opintel-v7" id="diagnostico-operativo-v7" data-opintel-state="{html.escape(str(a.get("state") or ""))}">
  <div class="opintel-head"><div><span class="section-kicker">{"Inteligencia operativa V7" if es else "Operational Intelligence V7"}</span><h2>{"Diagnóstico operativo multidimensional" if es else "Multidimensional operational assessment"}</h2><p>{"No tratamos Ormuz como un interruptor binario: separamos paso físico, intensidad, acceso y riesgo." if es else "Hormuz is not treated as a binary switch: physical passage, traffic intensity, access and risk are assessed separately."}</p></div>
  <div class="opintel-verdict"><span>{"Conclusión" if es else "Assessment"}</span><strong data-opintel-label>{html.escape(str(a.get("label_es" if es else "label_en") or ""))}</strong><small data-opintel-confidence>{"Confianza" if es else "Confidence"}: {html.escape(confidence_text(str(a.get("confidence") or "BAJA"), lang))}</small></div></div>
  <div class="opintel-grid">{metrics}</div>
  <p class="opintel-summary" data-opintel-summary>{html.escape(str(a.get("summary_es" if es else "summary_en") or ""))}</p>
  <div class="opintel-evidence"><div class="opintel-evidence-head"><strong>{"Por qué este diagnóstico" if es else "Why this assessment"}</strong><a href="{'/metodo-inteligencia-operativa.html' if es else '/en-operational-intelligence-method.html'}">{"Cómo se calcula →" if es else "How it is calculated →"}</a></div><ul>{evidence_html}</ul></div>
</section>
<!-- OPERATIONAL_INTELLIGENCE_V7_END -->'''


def update_home(root: Path, filename: str, lang: str, a: dict[str, Any]) -> None:
    path = root / filename
    if not path.exists(): return
    doc = path.read_text(encoding="utf-8"); block = render_block(a, lang)
    marker = re.compile(r'<!-- OPERATIONAL_INTELLIGENCE_V7_START -->.*?<!-- OPERATIONAL_INTELLIGENCE_V7_END -->', re.I|re.S)
    if marker.search(doc): doc = marker.sub(block, doc, count=1)
    else:
        anchor = re.search(r'<section\b[^>]*aria-labelledby=["\']verification-title["\'][^>]*>', doc, re.I)
        doc = doc[:anchor.start()] + block + "\n" + doc[anchor.start():] if anchor else doc.replace("</main>", block+"\n</main>",1)
    doc = replace_element_content(doc, "statusWord", html.escape(str(a.get("label_es" if lang=="es" else "label_en") or "")))
    doc = replace_element_content(doc, "operationalLabel", html.escape(str(a.get("operational_label_es" if lang=="es" else "operational_label_en") or "")))
    doc = replace_element_content(doc, "statusSummary", html.escape(str(a.get("summary_es" if lang=="es" else "summary_en") or "")))
    doc = replace_element_content(doc, "confidence", html.escape(confidence_text(str(a.get("confidence") or "BAJA"), lang)))
    if a.get("latest_confirmed_transit_at"): doc = replace_element_content(doc, "lastValidAt", html.escape(str(a["latest_confirmed_transit_at"])))
    path.write_text(doc, encoding="utf-8")


def update_status_files(root: Path, a: dict[str, Any]) -> None:
    for filename in ("status.json","daily-brief.json"):
        path = root / filename
        if not path.exists(): continue
        data = load_json(path, {})
        if isinstance(data, dict): data["operational_intelligence"] = a; write_json(path, data)


def update_history(root: Path, a: dict[str, Any]) -> None:
    path = root / "operational-intelligence-history.json"; hist = load_json(path, [])
    if not isinstance(hist, list): hist=[]
    key=(a.get("state"),a.get("dimensions",{}).get("traffic"),a.get("dimensions",{}).get("access"),a.get("dimensions",{}).get("risk"))
    prev=None
    if hist:
        p=hist[0]; prev=(p.get("state"),p.get("dimensions",{}).get("traffic"),p.get("dimensions",{}).get("access"),p.get("dimensions",{}).get("risk"))
    if key!=prev: hist.insert(0,a); write_json(path,hist[:365])


def run(root: Path | str | None = None, *, offline: bool=False) -> dict[str, Any]:
    root_path = Path(root) if root else Path(__file__).resolve().parent; now=utc_now()
    legacy=load_json(root_path/"status.json",{}); previous=load_json(root_path/"operational-intelligence.json",{})
    signals=[]; signals.extend(seed_signals(root_path,now)); signals.extend(signals_from_existing_status(root_path)); errors=[]
    if not offline:
        fetched,e=fetch_google_news(now); signals.extend(fetched); errors.extend(e)
        fetched,e=fetch_lloyds_hot_topic(now); signals.extend(fetched); errors.extend(e)
    a=assess(signals,now,legacy if isinstance(legacy,dict) else {}); a=merge_previous_if_needed(a,previous if isinstance(previous,dict) else {},now)
    a["diagnostics"]={"signals_considered":len(dedupe(signals)),"provider_errors":errors,"offline":offline,"baseline_vessels_per_day":BASELINE_VESSELS_PER_DAY,
        "model_note_es":"La clasificación pública prioriza pruebas de tránsito real. Una declaración política de cierre no invalida un tránsito comercial confirmado.",
        "model_note_en":"The public assessment prioritises evidence of actual transit. A political closure declaration does not override confirmed commercial passage."}
    write_json(root_path/"operational-intelligence.json",a); update_status_files(root_path,a); update_history(root_path,a); update_home(root_path,"index.html","es",a); update_home(root_path,"en.html","en",a)
    return a


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parent); parser.add_argument("--offline",action="store_true"); args=parser.parse_args()
    result=run(args.root,offline=args.offline); print(f"Operational Intelligence V7: {result.get('state')} / {result.get('confidence')}"); return 0

if __name__ == "__main__": raise SystemExit(main())
