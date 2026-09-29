"""Shared deterministic fixtures for Phase 2A tests."""

from __future__ import annotations

import copy
import re

from phase2_video.package import build_video_package
from phase2_video.schema import script_id


def source(source_id: str, name: str, tier: int = 4, official: bool = False) -> dict:
    return {
        "source_id": source_id,
        "source_name": name,
        "source_domain": f"{source_id}.example",
        "tier": tier,
        "official": official,
        "weight": float(tier),
    }


def article(source_row: dict, title: str, published_at: str) -> dict:
    return {
        "article_id": f"art-{source_row['source_id']}",
        "title": title,
        "title_key": title.casefold(),
        "url": f"https://{source_row['source_domain']}/reports/{source_row['source_id']}",
        "published_at": published_at,
        "observed_at": published_at,
        **source_row,
        "source_name": source_row["source_name"],
        "topic": "maritime",
        "classification": "FACT",
        "signal": "TRAFFIC_REDUCED",
        "description": "",
    }


def event(
    *,
    event_id: str = "evt-real-001",
    importance: int = 70,
    verification_status: str = "CONFIRMED_MULTI_SOURCE",
    headline: str = "Independent reports confirm reduced commercial traffic through the strait",
    last_seen: str = "2020-01-01T10:00:00Z",
    operational_impact: str = "CONTEXT",
    sources: list[dict] | None = None,
    classification: str = "FACT",
) -> dict:
    rows = sources or [source("reuters", "Reuters"), source("ap", "Associated Press")]
    articles = [article(row, headline, last_seen) for row in rows]
    for row in articles:
        row["classification"] = classification
    return {
        "event_id": event_id,
        "topic": "maritime",
        "first_seen": last_seen,
        "last_seen": last_seen,
        "headline": headline,
        "classification": classification,
        "verification_status": verification_status,
        "verification_reason": "Fixture mirrors a real verified event shape.",
        "sources": rows,
        "source_ids": [row["source_id"] for row in rows],
        "articles": articles,
        "importance": importance,
        "operational_impact": operational_impact,
        "operational_eligible": operational_impact == "MATERIAL",
    }


def operational_context(site: str = "ormuz") -> dict:
    return {
        "state": "OPEN_RESTRICTED" if site == "ormuz" else "reinforced_watch",
        "confidence": "medium" if site == "ormuz" else "low",
        "dimensions": {"traffic": "REDUCED"} if site == "ormuz" else {"maritime": {"value": "OPERATIONAL"}},
        "as_of": "2020-01-01T10:30:00Z",
        "health": "healthy",
    }


def package(
    *,
    site: str = "ormuz",
    event_row: dict | None = None,
    events: list[dict] | None = None,
    content_kind: str = "event",
) -> dict:
    chosen = event_row or event()
    rows = events or [chosen]
    return build_video_package(
        site=site,
        event_store={"schema_version": 1, "events": rows},
        operational_context=operational_context(site),
        source_health="healthy",
        comparison=["The verified evidence changed from the previous edition."],
        what_we_dont_know=["The duration of the restriction is not yet known."],
        watch_next_24h=["Official navigation notices and independently confirmed transits."],
        headlines={
            "es": "Dos fuentes confirman una reducción del tráfico comercial",
            "en": "Two sources confirm reduced commercial traffic",
        },
        content_kind=content_kind,
        event_id=chosen["event_id"] if content_kind == "event" else None,
        generated_at="2020-01-01T11:00:00Z",
        edition_date="2020-01-01",
    )


def reseal_script(script: dict, *, generated_by: str | None = None) -> dict:
    result = copy.deepcopy(script)
    if generated_by:
        result["generated_by"] = generated_by
    spoken = " ".join([
        str(result.get("hook") or ""),
        *(str(scene.get("voiceover") or "") for scene in result.get("scenes", [])),
        str(result.get("outro") or ""),
    ])
    result["estimated_words"] = len(re.findall(r"\b[\wáéíóúüñ'-]+\b", spoken, re.I))
    result["script_id"] = script_id(result)
    return result
