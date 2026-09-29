"""Build the closed Phase 2A package from Phase 1 artefacts."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from .rules import decide_video, load_rules
from .schema import (
    PACKAGE_SCHEMA_VERSION,
    VERIFIED_STATUSES,
    normalize_confidence,
    normalize_health,
    package_content_hash,
    package_id,
    parse_utc,
    phase2_verification,
    utc_iso,
    validate_edition_date,
)


_ATTRIBUTION_RE = re.compile(
    r"^(?P<speaker>[^:,.!?]{2,100}?)\s+(?:says?|said|warns?|warned|declares?|declared|"
    r"announces?|announced|claims?|claimed|afirma|afirm[oó]|dice|dijo|advierte|advirti[oó]|"
    r"declara|declar[oó]|anuncia|anunci[oó])\b",
    re.I,
)
_NO_CHANGE_MARKERS = (
    "sin cambio material", "no material change", "sin cambios materiales",
    "no hay cambios", "no change",
)
_UNTRUSTED_INSTRUCTION_RE = re.compile(
    r"\b(?:ignore (?:all |the |any )?(?:previous |prior )?instructions|"
    r"ignora (?:todas? )?(?:las )?instrucciones|system prompt|developer message|"
    r"reveal (?:the )?(?:secret|key|prompt)|disclose (?:secrets?|credentials?))\b",
    re.I,
)


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return default


def _as_text_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    return [text] if text else []


def _source_health_from_components(health: dict[str, Any]) -> str:
    rows = health.get("source_health")
    if isinstance(rows, dict):
        return normalize_health(rows.get("state") or health.get("overall"))
    if isinstance(rows, list):
        states = {str(row.get("state") or "").upper() for row in rows if isinstance(row, dict)}
        if states & {"STALE", "ERROR", "FAILED"}:
            return "stale"
        if states & {"DEGRADED", "WARNING"}:
            return "degraded"
    return normalize_health(health.get("overall") or "DEGRADED")


def load_site_inputs(root: Path | str, site: str) -> dict[str, Any]:
    """Load only the approved Phase 1 integration points for one site."""
    root = Path(root)
    events = _load_json(root / "events.json", {})
    health = _load_json(root / "health.json", {})
    if site == "ormuz":
        canonical = _load_json(root / "operational-intelligence.json", {})
        brief = _load_json(root / "daily-brief.json", {})
        context = {
            "state": canonical.get("state"),
            "confidence": normalize_confidence(canonical.get("confidence")),
            "dimensions": canonical.get("dimensions") if isinstance(canonical.get("dimensions"), dict) else {},
            "as_of": canonical.get("generated_at"),
            "health": normalize_health(health.get("overall") or "DEGRADED"),
        }
        comparison = _as_text_list(brief.get("change_es")) + _as_text_list(brief.get("change_en"))
        unknowns = _as_text_list(brief.get("risks_es")) + _as_text_list(brief.get("risks_en"))
        watch = _as_text_list(brief.get("watchlist_es")) + _as_text_list(brief.get("watchlist_en"))
        headlines = {
            "es": str(brief.get("summary_es") or "").strip(),
            "en": str(brief.get("summary_en") or "").strip(),
        }
    elif site == "gibraltar":
        observatory = _load_json(root / "observatory.json", {})
        state = observatory.get("state") if isinstance(observatory.get("state"), dict) else {}
        context = {
            "state": state.get("code"),
            "confidence": normalize_confidence(state.get("confidence")),
            "dimensions": state.get("layers") if isinstance(state.get("layers"), dict) else {},
            "as_of": observatory.get("generated_at"),
            "health": normalize_health(health.get("overall") or (observatory.get("health") or {}).get("overall") or "DEGRADED"),
        }
        since = observatory.get("since_yesterday") if isinstance(observatory.get("since_yesterday"), dict) else {}
        comparison = _as_text_list(since.get("summary_es"))
        unknowns = _as_text_list(state.get("confidence_explanation_es"))
        methodology = observatory.get("methodology") if isinstance(observatory.get("methodology"), dict) else {}
        unknowns += _as_text_list(methodology.get("operational_note"))
        watch = [
            "Avisos oficiales de navegación, puertos y salvamento marítimo.",
            "Cambios verificados en la frontera y en la relación bilateral.",
            "Nuevas incidencias de seguridad con corroboración independiente.",
        ]
        headlines = {
            "es": str(state.get("summary_es") or state.get("label_es") or "").strip(),
            "en": "",
        }
    else:
        raise ValueError("invalid-site")

    if not context.get("state") or not context.get("as_of"):
        raise ValueError("missing-canonical-operational-context")
    parse_utc(context["as_of"])
    return {
        "event_store": events,
        "operational_context": context,
        "source_health": _source_health_from_components(health),
        "comparison": comparison,
        "what_we_dont_know": unknowns,
        "watch_next_24h": watch,
        "headlines": headlines,
    }


def _fact_id(event: dict[str, Any]) -> str:
    seed = "|".join(str(event.get(key) or "") for key in ("event_id", "headline", "last_seen"))
    return "fact-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _statement_id(event: dict[str, Any], text: str) -> str:
    seed = f"{event.get('event_id', '')}|{text}"
    return "statement-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _verified_fact_source_ids(event: dict[str, Any]) -> list[str]:
    factual_classes = {"FACT", "OFFICIAL_NOTICE", "OPERATIONAL_SIGNAL"}
    article_sources = {
        str(article.get("source_id") or "")
        for article in event.get("articles") or []
        if isinstance(article, dict)
        and str(article.get("classification") or "").upper() in factual_classes
        and str(article.get("source_id") or "") not in {"", "unknown"}
    }
    event_sources = {
        str(item) for item in event.get("source_ids") or []
        if str(item) not in {"", "unknown"}
    }
    return sorted(article_sources or event_sources)


def _extract_speaker(event: dict[str, Any]) -> str:
    explicit = str(event.get("speaker") or "").strip()
    if explicit:
        return explicit
    for article in event.get("articles") or []:
        if not isinstance(article, dict):
            continue
        explicit = str(article.get("speaker") or "").strip()
        if explicit:
            return explicit
        match = _ATTRIBUTION_RE.search(str(article.get("title") or "").strip())
        if match:
            return match.group("speaker").strip(" -:")
    match = _ATTRIBUTION_RE.search(str(event.get("headline") or "").strip())
    return match.group("speaker").strip(" -:") if match else ""


def _source_tier(source: dict[str, Any]) -> str:
    if bool(source.get("official")):
        return "official"
    tier = int(source.get("tier") or 1)
    if tier >= 5:
        return "primary"
    if tier >= 3:
        return "trusted_media"
    return "secondary"


def _best_article(events: Iterable[dict[str, Any]], source_id: str) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for event in events:
        for article in event.get("articles") or []:
            if isinstance(article, dict) and str(article.get("source_id")) == source_id and article.get("url"):
                matches.append(article)
    if not matches:
        return {}
    return max(matches, key=lambda item: str(item.get("published_at") or ""))


def _build_sources(events: list[dict[str, Any]], source_ids: set[str]) -> list[dict[str, Any]]:
    source_records: dict[str, dict[str, Any]] = {}
    for event in events:
        for source in event.get("sources") or []:
            if isinstance(source, dict) and str(source.get("source_id") or "") in source_ids:
                source_records[str(source["source_id"])] = source
    output: list[dict[str, Any]] = []
    for source_id in sorted(source_ids):
        source = source_records.get(source_id, {})
        article = _best_article(events, source_id)
        published = article.get("published_at") or article.get("observed_at")
        if published:
            published = utc_iso(parse_utc(published))
        output.append({
            "source_id": source_id,
            "canonical_name": str(source.get("source_name") or source.get("canonical_name") or article.get("source_name") or "").strip(),
            "url": str(article.get("url") or "").strip(),
            "published_at": published or "",
            "tier": _source_tier(source or article),
            "official": bool(source.get("official") or article.get("official")),
            "rights_status": "link_and_factual_reference_only",
        })
    return output


def _is_recent(event: dict[str, Any], generated_at: datetime, maximum_age_hours: int) -> bool:
    try:
        observed = parse_utc(event.get("last_seen") or event.get("first_seen"))
    except (TypeError, ValueError):
        return False
    age = generated_at - observed
    return timedelta(0) <= age <= timedelta(hours=maximum_age_hours)


def _has_material_comparison(items: list[str]) -> bool:
    if not items:
        return False
    text = " ".join(items).casefold()
    return not any(marker in text for marker in _NO_CHANGE_MARKERS)


def build_video_package(
    *,
    site: str,
    event_store: dict[str, Any],
    operational_context: dict[str, Any],
    source_health: str,
    comparison: Iterable[str] = (),
    what_we_dont_know: Iterable[str] = (),
    watch_next_24h: Iterable[str] = (),
    headlines: dict[str, str] | None = None,
    content_kind: str = "event",
    event_id: str | None = None,
    generated_at: str | None = None,
    edition_date: str | None = None,
    duplicate_package: bool = False,
    material_change_override: bool | None = None,
    new_event_override: bool | None = None,
    rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a closed package without calling any model or external service."""
    config = rules or load_rules()
    now = parse_utc(generated_at) if generated_at else datetime.now(timezone.utc).replace(microsecond=0)
    generated = utc_iso(now)
    edition = validate_edition_date(edition_date or now.date().isoformat())
    if content_kind not in {"event", "daily_summary"}:
        raise ValueError("invalid-content-kind")

    all_events = [event for event in event_store.get("events", []) if isinstance(event, dict)]
    if content_kind == "event":
        selected = [event for event in all_events if str(event.get("event_id")) == str(event_id)]
        if not selected:
            raise ValueError("event-not-found")
    else:
        selected = [
            event for event in all_events
            if str(event.get("last_seen") or "")[:10] == edition
            or str(event.get("first_seen") or "")[:10] == edition
        ]

    phase1_statuses = [str(event.get("verification_status") or "").upper() for event in selected]
    facts: list[dict[str, Any]] = []
    statements: list[dict[str, Any]] = []
    for event in selected:
        status = str(event.get("verification_status") or "").upper()
        mapped = phase2_verification(status)
        source_ids = sorted({str(item) for item in event.get("source_ids") or [] if str(item)})
        headline = str(event.get("headline") or "").strip()
        fact_source_ids = _verified_fact_source_ids(event)
        if mapped in VERIFIED_STATUSES and headline and fact_source_ids:
            observed_at = utc_iso(parse_utc(event.get("last_seen") or event.get("first_seen")))
            facts.append({
                "fact_id": _fact_id(event),
                "text_es": str(event.get("headline_es") or headline).strip(),
                "text_en": str(event.get("headline_en") or headline).strip(),
                "event_id": str(event.get("event_id") or ""),
                "verification_status": mapped,
                "source_ids": fact_source_ids,
                "observed_at": observed_at,
            })
        if status == "DECLARATION_ONLY" or str(event.get("classification") or "").upper() == "DECLARATION":
            speaker = _extract_speaker(event)
            if speaker and headline and source_ids:
                statements.append({
                    "statement_id": _statement_id(event, headline),
                    "text_es": str(event.get("headline_es") or headline).strip(),
                    "text_en": str(event.get("headline_en") or headline).strip(),
                    "speaker": speaker,
                    "source_ids": source_ids,
                    "attributed": True,
                    "not_verified_as_fact": True,
                })

    needed_sources = {
        source_id
        for row in [*facts, *statements]
        for source_id in row.get("source_ids", [])
    }
    sources = _build_sources(selected, needed_sources)
    source_index = {item["source_id"]: item for item in sources}
    traceability_complete = bool(facts) and all(
        source_id in source_index
        and bool(source_index[source_id].get("url"))
        and bool(source_index[source_id].get("published_at"))
        for fact in facts
        for source_id in fact["source_ids"]
    )

    context = {
        "state": str(operational_context.get("state") or "").strip(),
        "confidence": normalize_confidence(operational_context.get("confidence")),
        "dimensions": operational_context.get("dimensions") if isinstance(operational_context.get("dimensions"), dict) else {},
        "as_of": utc_iso(parse_utc(operational_context.get("as_of"))),
        "health": normalize_health(operational_context.get("health")),
    }
    source_health = normalize_health(source_health)
    changes = _as_text_list(list(comparison))
    unknowns = _as_text_list(list(what_we_dont_know))
    watch = _as_text_list(list(watch_next_24h))
    importance = max([int(event.get("importance") or 0) for event in selected] or [0])
    recent_flags = [_is_recent(event, now, int(config["freshness"]["maximum_event_age_hours"])) for event in selected]
    new_event = new_event_override if new_event_override is not None else bool(recent_flags and any(recent_flags))
    material_change = (
        material_change_override
        if material_change_override is not None
        else bool(new_event and (_has_material_comparison(changes) or any(
            str(event.get("operational_impact") or "").upper() in {"MATERIAL", "POTENTIAL", "CONTEXT"}
            for event in selected
        )))
    )
    tolerance = timedelta(seconds=int(config["freshness"]["future_tolerance_seconds"]))
    future_values: list[datetime] = [parse_utc(context["as_of"])]
    for event in selected:
        for key in ("first_seen", "last_seen"):
            if event.get(key):
                future_values.append(parse_utc(event[key]))
    for source in sources:
        if source.get("published_at"):
            future_values.append(parse_utc(source["published_at"]))
    has_future = any(value > now + tolerance for value in future_values)

    chosen_headline = str(selected[0].get("headline") or "").strip() if selected else ""
    supplied_headlines = headlines or {}
    headline_payload = {
        "es": str(supplied_headlines.get("es") or chosen_headline).strip(),
        "en": str(supplied_headlines.get("en") or chosen_headline).strip(),
    }
    phase2_statuses = [fact["verification_status"] for fact in facts]
    contains_untrusted_instruction = any(
        _UNTRUSTED_INSTRUCTION_RE.search(str(value or ""))
        for value in [
            *[fact.get("text_es") for fact in facts],
            *[fact.get("text_en") for fact in facts],
            *[statement.get("text_es") for statement in statements],
            *[statement.get("text_en") for statement in statements],
        ]
    )
    operational_impact = max(
        (str(event.get("operational_impact") or "NONE").upper() for event in selected),
        key=lambda value: {"NONE": 0, "CONTEXT": 1, "POTENTIAL": 2, "MATERIAL": 3}.get(value, -1),
        default="NONE",
    )
    decision = decide_video(
        importance=importance,
        content_kind=content_kind,
        phase1_verification_statuses=phase1_statuses,
        phase2_verification_statuses=phase2_statuses,
        verified_fact_count=len(facts),
        statement_count=len(statements),
        verified_event_count=len({fact["event_id"] for fact in facts}),
        source_ids=needed_sources,
        operational_health=context["health"],
        source_health=source_health,
        material_change=material_change,
        new_event=new_event,
        operational_impact=operational_impact,
        traceability_complete=traceability_complete,
        factual_package_valid=bool(
            context["state"] and headline_payload["es"] and headline_payload["en"]
            and not contains_untrusted_instruction
        ),
        state_consistent=bool(context["state"] and context["as_of"]),
        has_future_data=has_future,
        content_hash_valid=True,
        duplicate_package=duplicate_package,
        rules=config,
    )

    package: dict[str, Any] = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "package_id": "",
        "site": site,
        "language_set": ["es", "en"],
        "generated_at": generated,
        "edition_date": edition,
        "content_kind": content_kind,
        "event_id": str(selected[0].get("event_id")) if content_kind == "event" and selected else None,
        "importance": importance,
        **decision.as_package_fields(),
        "headlines": headline_payload,
        "verified_facts": facts,
        "statements": statements,
        "sources": sources,
        "operational_context": context,
        "what_changed": changes,
        "what_we_know": [fact["text_es"] for fact in facts],
        "what_we_dont_know": unknowns,
        "watch_next_24h": watch,
        "visual_assets": [],
        "content_hash": "",
    }
    digest = package_content_hash(package)
    package["content_hash"] = digest
    package["package_id"] = package_id(site, edition, digest)
    return package
