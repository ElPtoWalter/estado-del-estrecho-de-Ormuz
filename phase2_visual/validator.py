"""Fail-closed validation for Phase 2C storyboards and SVG manifests."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from phase2_video.schema import canonical_json
from phase2_video.validator import validate_package, validate_script

from .schema import (
    ASSET_KEYS,
    MANIFEST_KEYS,
    STORYBOARD_KEYS,
    STORYBOARD_SCENE_KEYS,
    STORYBOARD_SCHEMA_VERSION,
    VISUAL_MANIFEST_SCHEMA_VERSION,
    VISUAL_RENDERER_VERSION,
    VISUAL_RULE_VERSION,
    VISUAL_VALIDATOR_VERSION,
    load_visual_rules,
    sha256_file,
    storyboard_content_hash,
    storyboard_id,
    visual_manifest_content_hash,
    visual_manifest_id,
)
from .storyboard import build_storyboard


def _report(kind: str, identity: str, errors: list[str], **extra: Any) -> dict[str, Any]:
    unique = list(dict.fromkeys(errors))
    return {
        "validator_version": VISUAL_VALIDATOR_VERSION,
        "artifact_kind": kind,
        "artifact_id": identity,
        "validation_status": "PASS" if not unique else "FAIL",
        "validation_errors": unique,
        **extra,
    }


def validate_storyboard(
    package: dict[str, Any],
    script: dict[str, Any],
    storyboard: Any,
    *,
    rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(storyboard, dict):
        return _report("storyboard", "", ["STORYBOARD_SCHEMA"])
    identity = str(storyboard.get("storyboard_id") or "")
    config = rules or load_visual_rules()
    if validate_package(package)["validation_status"] != "PASS":
        errors.append("PACKAGE_INVALID")
    if validate_script(package, script)["validation_status"] != "PASS":
        errors.append("SCRIPT_INVALID")
    if set(storyboard) != STORYBOARD_KEYS or storyboard.get("schema_version") != STORYBOARD_SCHEMA_VERSION:
        errors.append("STORYBOARD_SCHEMA")
    if storyboard.get("rule_version") != VISUAL_RULE_VERSION:
        errors.append("RULE_VERSION")
    if storyboard.get("package_id") != package.get("package_id"):
        errors.append("PACKAGE_ID_MISMATCH")
    if storyboard.get("package_content_hash") != package.get("content_hash"):
        errors.append("PACKAGE_HASH_MISMATCH")
    if storyboard.get("script_id") != script.get("script_id"):
        errors.append("SCRIPT_ID_MISMATCH")
    digest = str(storyboard.get("content_hash") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", digest) or digest != storyboard_content_hash(storyboard):
        errors.append("CONTENT_HASH_MISMATCH")
    try:
        expected_id = storyboard_id(str(package.get("site") or ""), digest)
    except ValueError:
        expected_id = ""
    if identity != expected_id:
        errors.append("STORYBOARD_ID_MISMATCH")
    frame = config["frame"]
    for key in ("aspect_ratio", "width_px", "height_px", "fps"):
        if storyboard.get(key) != frame[key]:
            errors.append("FRAME_FORMAT")
    if storyboard.get("target_seconds") != script.get("target_seconds"):
        errors.append("TARGET_DURATION")
    if storyboard.get("site") != package.get("site") or storyboard.get("language") != script.get("language"):
        errors.append("SITE_OR_LANGUAGE")
    if storyboard.get("generated_at") != package.get("generated_at"):
        errors.append("GENERATED_AT")
    if storyboard.get("human_review_required") is not True or storyboard.get("publication_allowed") is not False:
        errors.append("PUBLICATION_GUARD")
    if storyboard.get("rights_policy") != "generated_original_only":
        errors.append("RIGHTS_POLICY")

    scenes = storyboard.get("scenes") if isinstance(storyboard.get("scenes"), list) else []
    if len(scenes) != len(script.get("scenes") or []) or not scenes:
        errors.append("SCENE_COUNT")
    cursor = 0
    asset_ids: set[str] = set()
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict) or set(scene) != STORYBOARD_SCENE_KEYS:
            errors.append("SCENE_SCHEMA")
            continue
        if scene.get("scene_id") != f"visual-scene-{index + 1:02d}":
            errors.append("SCENE_ID")
        if scene.get("start_ms") != cursor:
            errors.append("TIMELINE_GAP")
        if scene.get("duration_ms") != scene.get("end_ms", 0) - scene.get("start_ms", 0):
            errors.append("SCENE_DURATION")
        if int(scene.get("duration_ms") or 0) < int(config["timeline"]["minimum_scene_ms"]):
            errors.append("SCENE_TOO_SHORT")
        cursor = int(scene.get("end_ms") or cursor)
        current_asset_id = str(scene.get("asset_id") or "")
        if not current_asset_id or current_asset_id in asset_ids:
            errors.append("ASSET_ID")
        asset_ids.add(current_asset_id)
        for key in ("eyebrow", "headline", "body", "footer"):
            if not isinstance(scene.get(key), str) or not scene.get(key).strip():
                errors.append("SCENE_TEXT")
        for key in ("fact_ids", "statement_ids", "source_ids"):
            if not isinstance(scene.get(key), list) or not all(isinstance(item, str) for item in scene.get(key, [])):
                errors.append("SCENE_TRACEABILITY")
    if cursor != int(script.get("target_seconds") or 0) * 1000:
        errors.append("TIMELINE_TOTAL")

    try:
        expected = build_storyboard(package, script, rules=config)
    except (TypeError, ValueError):
        expected = None
    if expected is None or canonical_json(storyboard) != canonical_json(expected):
        errors.append("NON_DETERMINISTIC_STORYBOARD")
    return _report(
        "storyboard",
        identity,
        errors,
        storyboard_schema_version=STORYBOARD_SCHEMA_VERSION,
        rule_version=str(storyboard.get("rule_version") or ""),
        package_id=str(storyboard.get("package_id") or ""),
        script_id=str(storyboard.get("script_id") or ""),
        content_hash=digest,
        scene_count=len(scenes),
    )


def _unsafe_svg(root: ET.Element) -> bool:
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1].casefold()
        if tag in {"script", "image", "foreignobject", "audio", "video", "iframe"}:
            return True
        for attribute, value in element.attrib.items():
            name = attribute.rsplit("}", 1)[-1].casefold()
            if name in {"href", "src"} or str(value).strip().casefold().startswith(("data:", "javascript:")):
                return True
    return False


def validate_visual_manifest(
    package: dict[str, Any],
    script: dict[str, Any],
    storyboard: dict[str, Any],
    manifest: Any,
    artifact_root: Path | str,
    *,
    rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return _report("visual-manifest", "", ["MANIFEST_SCHEMA"])
    identity = str(manifest.get("manifest_id") or "")
    config = rules or load_visual_rules()
    if validate_storyboard(package, script, storyboard, rules=config)["validation_status"] != "PASS":
        errors.append("STORYBOARD_INVALID")
    if set(manifest) != MANIFEST_KEYS or manifest.get("schema_version") != VISUAL_MANIFEST_SCHEMA_VERSION:
        errors.append("MANIFEST_SCHEMA")
    digest = str(manifest.get("content_hash") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", digest) or digest != visual_manifest_content_hash(manifest):
        errors.append("CONTENT_HASH_MISMATCH")
    try:
        expected_id = visual_manifest_id(digest)
    except ValueError:
        expected_id = ""
    if identity != expected_id:
        errors.append("MANIFEST_ID_MISMATCH")
    links = {
        "storyboard_id": storyboard.get("storyboard_id"),
        "storyboard_content_hash": storyboard.get("content_hash"),
        "package_id": package.get("package_id"),
        "script_id": script.get("script_id"),
        "generated_at": storyboard.get("generated_at"),
    }
    if any(manifest.get(key) != value for key, value in links.items()):
        errors.append("MANIFEST_TRACEABILITY")
    if manifest.get("renderer_version") != VISUAL_RENDERER_VERSION or manifest.get("engine") != "straitwatch-svg":
        errors.append("RENDERER")
    if (
        manifest.get("network_used") is not False
        or manifest.get("external_assets_used") is not False
        or manifest.get("human_review_required") is not True
        or manifest.get("publication_allowed") is not False
    ):
        errors.append("PUBLICATION_OR_NETWORK_GUARD")

    root_path = Path(artifact_root).resolve()
    assets = manifest.get("assets") if isinstance(manifest.get("assets"), list) else []
    scene_map = {scene["scene_id"]: scene for scene in storyboard.get("scenes", [])}
    if len(assets) != len(scene_map) or not assets:
        errors.append("ASSET_COUNT")
    seen: set[str] = set()
    for asset in assets:
        if not isinstance(asset, dict) or set(asset) != ASSET_KEYS:
            errors.append("ASSET_SCHEMA")
            continue
        scene = scene_map.get(str(asset.get("scene_id") or ""))
        if scene is None or asset.get("asset_id") != scene.get("asset_id"):
            errors.append("ASSET_TRACEABILITY")
            continue
        if asset["asset_id"] in seen:
            errors.append("ASSET_ID")
        seen.add(asset["asset_id"])
        if asset.get("file") != f'assets/{scene["scene_id"]}.svg' or asset.get("media_type") != "image/svg+xml":
            errors.append("ASSET_FILE")
        if asset.get("width_px") != storyboard.get("width_px") or asset.get("height_px") != storyboard.get("height_px"):
            errors.append("ASSET_DIMENSIONS")
        rights = config["rights"]
        if (
            asset.get("rights_status") != rights["status"]
            or asset.get("credit") != rights["credit"]
            or asset.get("allowed_uses") != rights["allowed_uses"]
        ):
            errors.append("ASSET_RIGHTS")
        for key in ("fact_ids", "statement_ids", "source_ids"):
            if asset.get(key) != scene.get(key):
                errors.append("ASSET_TRACEABILITY")
        relative = Path(str(asset.get("file") or ""))
        path = (root_path / relative).resolve()
        try:
            path.relative_to(root_path)
        except ValueError:
            errors.append("ASSET_PATH")
            continue
        if not path.is_file():
            errors.append("ASSET_MISSING")
            continue
        if asset.get("sha256") != sha256_file(path) or asset.get("bytes") != path.stat().st_size:
            errors.append("ASSET_HASH")
        try:
            svg_root = ET.fromstring(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ET.ParseError):
            errors.append("SVG_INVALID")
            continue
        if svg_root.tag.rsplit("}", 1)[-1].casefold() != "svg" or _unsafe_svg(svg_root):
            errors.append("SVG_UNSAFE")
        if svg_root.get("width") != str(storyboard.get("width_px")) or svg_root.get("height") != str(storyboard.get("height_px")):
            errors.append("SVG_DIMENSIONS")
    return _report(
        "visual-manifest",
        identity,
        errors,
        manifest_schema_version=VISUAL_MANIFEST_SCHEMA_VERSION,
        renderer_version=str(manifest.get("renderer_version") or ""),
        storyboard_id=str(manifest.get("storyboard_id") or ""),
        content_hash=digest,
        asset_count=len(assets),
    )
