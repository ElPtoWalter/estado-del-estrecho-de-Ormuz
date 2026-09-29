"""Deterministic audiovisual selection rules."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .schema import RULE_VERSION, VERIFIED_STATUSES


DEFAULT_RULES_PATH = Path(__file__).resolve().parents[1] / "video-rules.json"


@dataclass(frozen=True)
class VideoDecision:
    video_recommended: bool
    video_type: str | None
    rule_id: str
    reason_codes: tuple[str, ...]
    decided_by: str = "deterministic_rules"
    human_review_required: bool = True

    def as_package_fields(self) -> dict[str, Any]:
        data = asdict(self)
        video_type = data.pop("video_type")
        recommended = data.pop("video_recommended")
        data["reason_codes"] = list(data["reason_codes"])
        return {
            "video_recommended": recommended,
            "video_type": video_type,
            "video_recommendation": data,
        }


def load_rules(path: Path | str = DEFAULT_RULES_PATH) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("rule_id") != RULE_VERSION:
        raise ValueError("unsupported-video-rules")
    thresholds = payload.get("thresholds") or {}
    values = [
        thresholds.get("daily_summary_min"),
        thresholds.get("explainer_min"),
        thresholds.get("breaking_min"),
        thresholds.get("exceptional_information_min"),
    ]
    if not all(isinstance(item, int) for item in values) or values != sorted(values):
        raise ValueError("invalid-video-thresholds")
    return payload


def _ordered_unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def decide_video(
    *,
    importance: int,
    content_kind: str,
    phase1_verification_statuses: Iterable[str],
    phase2_verification_statuses: Iterable[str],
    verified_fact_count: int,
    statement_count: int,
    verified_event_count: int,
    source_ids: Iterable[str],
    operational_health: str,
    source_health: str,
    material_change: bool,
    new_event: bool,
    operational_impact: str,
    traceability_complete: bool,
    factual_package_valid: bool,
    state_consistent: bool,
    has_future_data: bool,
    content_hash_valid: bool,
    duplicate_package: bool = False,
    rules: dict[str, Any] | None = None,
) -> VideoDecision:
    """Return a reproducible decision.  A generative model is never consulted."""
    config = rules or load_rules()
    if not isinstance(importance, int) or isinstance(importance, bool):
        importance = -1
    importance = max(-1, min(100, importance))
    phase1 = {str(item).strip().upper() for item in phase1_verification_statuses}
    phase2 = {str(item).strip().upper() for item in phase2_verification_statuses}
    sources = {str(item).strip() for item in source_ids if str(item).strip()}
    blockers: list[str] = []

    if "CONFLICTING" in phase1:
        blockers.append("UNRESOLVED_CONFLICT")
    if not phase2 and phase1 == {"DECLARATION_ONLY"}:
        blockers.append("ONLY_DECLARATIONS")
    if not phase2 and "SINGLE_SOURCE" in phase1:
        blockers.append("SINGLE_SOURCE")
    if not phase2 and "UNCONFIRMED" in phase1:
        blockers.append("UNCONFIRMED_EVENT")
    if verified_fact_count <= 0:
        blockers.append("ONLY_DECLARATIONS" if statement_count > 0 else "INVALID_FACTUAL_PACKAGE")
    if not phase2 or not phase2.issubset(VERIFIED_STATUSES):
        blockers.append("INVALID_FACTUAL_PACKAGE")
    if not sources or not traceability_complete or not factual_package_valid or not state_consistent:
        blockers.append("INVALID_FACTUAL_PACKAGE")
    if has_future_data or not content_hash_valid:
        blockers.append("INVALID_FACTUAL_PACKAGE")
    if source_health == "stale":
        blockers.append("STALE_SOURCES")
    if operational_health == "stale":
        blockers.append("STALE_OPERATIONAL_CONTEXT")
    if not material_change or not new_event:
        blockers.append("NO_MATERIAL_CHANGE")
    if duplicate_package:
        blockers.append("DUPLICATE_PACKAGE")

    thresholds = config["thresholds"]
    daily_min = thresholds["daily_summary_min"]
    explainer_min = thresholds["explainer_min"]
    breaking_min = thresholds["breaking_min"]
    if importance < daily_min:
        blockers.append("BELOW_VIDEO_THRESHOLD")
    elif importance < explainer_min and content_kind != "daily_summary":
        blockers.append("BELOW_VIDEO_THRESHOLD")
    if content_kind == "daily_summary" and verified_event_count < config["daily_summary"]["minimum_verified_events"]:
        blockers.append("NO_MATERIAL_CHANGE")

    if blockers:
        return VideoDecision(False, None, config["rule_id"], _ordered_unique(blockers))

    reasons: list[str] = []
    if "VERIFIED_PRIMARY" in phase2:
        reasons.append("PRIMARY_VERIFICATION")
    if "VERIFIED_MULTISOURCE" in phase2:
        reasons.append("MULTISOURCE_VERIFICATION")
    if verified_event_count > 1:
        reasons.append("MULTIPLE_VERIFIED_EVENTS")
    if operational_impact.upper() == "MATERIAL":
        reasons.append("MATERIAL_OPERATIONAL_CHANGE")
    if importance >= explainer_min:
        reasons.append("HIGH_IMPORTANCE")

    exceptional = importance >= thresholds["exceptional_information_min"]
    breaking_ready = (
        content_kind == "event"
        and importance >= breaking_min
        and (operational_impact.upper() == "MATERIAL" or exceptional)
    )
    if breaking_ready:
        video_type = "breaking"
        reasons.append("BREAKING_CANDIDATE")
    elif content_kind == "daily_summary":
        video_type = "daily_summary"
        reasons.append("DAILY_MATERIAL_UPDATE")
    else:
        video_type = "explainer"

    return VideoDecision(True, video_type, config["rule_id"], _ordered_unique(reasons))
