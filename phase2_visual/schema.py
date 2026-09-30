"""Versioned schemas and canonical identifiers for Phase 2C."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from phase2_video.schema import canonical_json


STORYBOARD_SCHEMA_VERSION = "1.0.0"
VISUAL_MANIFEST_SCHEMA_VERSION = "1.0.0"
VISUAL_RENDERER_VERSION = "1.0.0"
VISUAL_VALIDATOR_VERSION = "1.0.0"
VISUAL_RULE_VERSION = "VISUAL_RULESET_V1"

STORYBOARD_KEYS = {
    "schema_version", "storyboard_id", "content_hash", "rule_version",
    "package_id", "package_content_hash", "script_id", "site", "language",
    "aspect_ratio", "width_px", "height_px", "fps", "target_seconds",
    "generated_at", "human_review_required", "publication_allowed",
    "rights_policy", "scenes",
}
STORYBOARD_SCENE_KEYS = {
    "scene_id", "source_scene_id", "start_ms", "end_ms", "duration_ms",
    "requested_intent", "resolved_template", "eyebrow", "headline", "body",
    "footer", "fact_ids", "statement_ids", "source_ids", "asset_id",
}
MANIFEST_KEYS = {
    "schema_version", "manifest_id", "content_hash", "renderer_version",
    "storyboard_id", "storyboard_content_hash", "package_id", "script_id",
    "generated_at", "engine", "network_used", "external_assets_used",
    "human_review_required", "publication_allowed", "assets",
}
ASSET_KEYS = {
    "asset_id", "scene_id", "file", "media_type", "sha256", "bytes",
    "width_px", "height_px", "rights_status", "credit", "allowed_uses",
    "fact_ids", "statement_ids", "source_ids",
}


def _hash_without(payload: dict[str, Any], *keys: str) -> str:
    basis = copy.deepcopy(payload)
    for key in keys:
        basis.pop(key, None)
    return hashlib.sha256(canonical_json(basis).encode("utf-8")).hexdigest()


def storyboard_content_hash(storyboard: dict[str, Any]) -> str:
    return _hash_without(storyboard, "storyboard_id", "content_hash")


def storyboard_id(site: str, content_hash: str) -> str:
    if site not in {"ormuz", "gibraltar"}:
        raise ValueError("invalid-visual-site")
    if not re.fullmatch(r"[0-9a-f]{64}", content_hash or ""):
        raise ValueError("invalid-storyboard-hash")
    return f"visual-storyboard:{site}:{content_hash}"


def visual_manifest_content_hash(manifest: dict[str, Any]) -> str:
    return _hash_without(manifest, "manifest_id", "content_hash")


def visual_manifest_id(content_hash: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", content_hash or ""):
        raise ValueError("invalid-visual-manifest-hash")
    return f"visual-manifest:{content_hash}"


def asset_id(package_id: str, script_id: str, scene_id: str, template: str) -> str:
    value = "|".join((package_id, script_id, scene_id, template))
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]
    return f"visual-asset:{digest}"


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_visual_rules(path: Path | None = None) -> dict[str, Any]:
    target = path or Path(__file__).resolve().parent.parent / "visual-rules.json"
    rules = json.loads(target.read_text(encoding="utf-8"))
    if rules.get("rule_id") != VISUAL_RULE_VERSION:
        raise ValueError("unsupported-visual-rule-version")
    frame = rules.get("frame") or {}
    if frame != {
        "aspect_ratio": "9:16",
        "width_px": 1080,
        "height_px": 1920,
        "fps": 30,
    }:
        raise ValueError("invalid-visual-frame-rules")
    if int((rules.get("timeline") or {}).get("minimum_scene_ms") or 0) < 1000:
        raise ValueError("invalid-visual-timeline-rules")
    if (rules.get("rights") or {}).get("policy") != "generated_original_only":
        raise ValueError("invalid-visual-rights-policy")
    expected_resolution = {
        "presenter": "status-card",
        "map": "schematic-map",
        "chart": "metric-card-or-text-card",
        "timeline": "timeline",
        "source-card": "source-card",
        "status-card": "status-card",
        "text-card": "text-card",
    }
    if rules.get("intent_resolution") != expected_resolution:
        raise ValueError("invalid-visual-intent-rules")
    color_keys = {"background", "panel", "accent", "signal", "text", "muted"}
    themes = rules.get("themes")
    if not isinstance(themes, dict) or set(themes) != {"ormuz", "gibraltar"}:
        raise ValueError("invalid-visual-themes")
    for theme in themes.values():
        if (
            not isinstance(theme, dict)
            or set(theme) != color_keys
            or not all(re.fullmatch(r"#[0-9A-Fa-f]{6}", str(value or "")) for value in theme.values())
        ):
            raise ValueError("invalid-visual-theme")
    return rules
