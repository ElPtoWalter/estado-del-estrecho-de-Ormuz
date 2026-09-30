"""Render original, network-free SVG frames from a sealed storyboard."""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from .schema import (
    STORYBOARD_KEYS,
    STORYBOARD_SCENE_KEYS,
    STORYBOARD_SCHEMA_VERSION,
    VISUAL_MANIFEST_SCHEMA_VERSION,
    VISUAL_RENDERER_VERSION,
    load_visual_rules,
    sha256_file,
    storyboard_content_hash,
    storyboard_id,
    visual_manifest_content_hash,
    visual_manifest_id,
)


def _lines(value: Any, width: int, maximum: int) -> list[str]:
    text = " ".join(str(value or "").split())
    if not text:
        return []
    rows = textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False)
    if len(rows) > maximum:
        rows = rows[:maximum]
        rows[-1] = rows[-1].rstrip(" .") + "…"
    return rows


def _text_block(rows: list[str], *, x: int, y: int, size: int, line_height: int, fill: str, weight: int = 400) -> str:
    spans = "".join(
        f'<tspan x="{x}" y="{y + index * line_height}">{escape(row)}</tspan>'
        for index, row in enumerate(rows)
    )
    return f'<text font-size="{size}" font-weight="{weight}" fill="{fill}">{spans}</text>'


def _map_art(site: str, theme: dict[str, str]) -> str:
    if site == "ormuz":
        land_a = "M90 1160 C240 1030 350 1040 485 1110 C600 1170 705 1160 990 1025 L990 1480 L90 1480 Z"
        land_b = "M90 830 C310 720 510 760 650 850 C770 925 875 910 990 825 L990 620 L90 620 Z"
        label = "ESTRECHO DE ORMUZ"
    else:
        land_a = "M90 1140 C275 1010 430 1040 570 1120 C720 1205 850 1170 990 1070 L990 1480 L90 1480 Z"
        land_b = "M90 790 C270 690 450 735 600 810 C760 890 865 850 990 760 L990 620 L90 620 Z"
        label = "ESTRECHO DE GIBRALTAR"
    return "".join([
        f'<path d="{land_a}" fill="{theme["panel"]}" stroke="{theme["accent"]}" stroke-width="4"/>',
        f'<path d="{land_b}" fill="{theme["panel"]}" stroke="{theme["accent"]}" stroke-width="4"/>',
        f'<path d="M170 950 C420 900 680 1010 910 920" fill="none" stroke="{theme["signal"]}" stroke-width="12" stroke-linecap="round" stroke-dasharray="22 24"/>',
        f'<circle cx="540" cy="952" r="20" fill="{theme["signal"]}"/>',
        f'<text x="540" y="1545" text-anchor="middle" font-size="34" font-weight="700" fill="{theme["muted"]}">{label}</text>',
        f'<text x="540" y="1595" text-anchor="middle" font-size="26" fill="{theme["signal"]}">ESQUEMA · NO APTO PARA NAVEGACIÓN</text>',
    ])


def _template_art(scene: dict[str, Any], site: str, theme: dict[str, str]) -> str:
    template = scene["resolved_template"]
    if template == "schematic-map":
        return _map_art(site, theme)
    if template == "timeline":
        return "".join([
            f'<line x1="170" y1="1120" x2="910" y2="1120" stroke="{theme["muted"]}" stroke-width="8"/>',
            f'<circle cx="250" cy="1120" r="28" fill="{theme["panel"]}" stroke="{theme["accent"]}" stroke-width="8"/>',
            f'<circle cx="540" cy="1120" r="34" fill="{theme["accent"]}"/>',
            f'<circle cx="830" cy="1120" r="28" fill="{theme["panel"]}" stroke="{theme["accent"]}" stroke-width="8"/>',
        ])
    if template == "metric-card":
        return "".join([
            f'<circle cx="540" cy="1190" r="190" fill="none" stroke="{theme["panel"]}" stroke-width="44"/>',
            f'<path d="M540 1000 A190 190 0 1 1 390 1305" fill="none" stroke="{theme["accent"]}" stroke-width="44" stroke-linecap="round"/>',
            f'<circle cx="540" cy="1190" r="26" fill="{theme["signal"]}"/>',
        ])
    if template == "source-card":
        return "".join([
            f'<rect x="130" y="1060" width="820" height="310" rx="36" fill="{theme["panel"]}" stroke="{theme["accent"]}" stroke-width="4"/>',
            f'<path d="M210 1160 H870 M210 1230 H760 M210 1300 H820" stroke="{theme["muted"]}" stroke-width="18" stroke-linecap="round"/>',
            f'<circle cx="850" cy="1160" r="24" fill="{theme["signal"]}"/>',
        ])
    if template == "status-card":
        return "".join([
            f'<rect x="130" y="1060" width="820" height="310" rx="44" fill="{theme["panel"]}"/>',
            f'<circle cx="260" cy="1215" r="72" fill="{theme["accent"]}" opacity="0.18"/>',
            f'<circle cx="260" cy="1215" r="34" fill="{theme["accent"]}"/>',
            f'<path d="M390 1160 H850 M390 1230 H760 M390 1300 H820" stroke="{theme["muted"]}" stroke-width="18" stroke-linecap="round"/>',
        ])
    return "".join([
        f'<rect x="130" y="1080" width="820" height="260" rx="40" fill="{theme["panel"]}"/>',
        f'<path d="M220 1165 H860 M220 1245 H790" stroke="{theme["muted"]}" stroke-width="18" stroke-linecap="round"/>',
    ])


def render_scene_svg(storyboard: dict[str, Any], scene: dict[str, Any], theme: dict[str, str]) -> str:
    headline = _lines(scene["headline"], 29, 5)
    body = _lines(scene["body"], 52, 3)
    footer = _lines(scene["footer"], 58, 2)
    progress = max(0.02, min(1.0, scene["end_ms"] / (storyboard["target_seconds"] * 1000)))
    progress_width = round(900 * progress)
    return "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{storyboard["width_px"]}" height="{storyboard["height_px"]}" viewBox="0 0 {storyboard["width_px"]} {storyboard["height_px"]}">',
        f'<rect width="1080" height="1920" fill="{theme["background"]}"/>',
        f'<rect x="0" y="0" width="1080" height="18" fill="{theme["accent"]}"/>',
        f'<text x="90" y="105" font-family="Arial, sans-serif" font-size="34" font-weight="700" fill="{theme["text"]}">STRAITWATCH</text>',
        f'<text x="990" y="105" text-anchor="end" font-family="Arial, sans-serif" font-size="28" fill="{theme["muted"]}">{escape(storyboard["site"].upper())}</text>',
        f'<text x="90" y="245" font-family="Arial, sans-serif" font-size="28" font-weight="700" letter-spacing="3" fill="{theme["accent"]}">{escape(scene["eyebrow"])}</text>',
        '<g font-family="Arial, sans-serif">',
        _text_block(headline, x=90, y=355, size=72, line_height=88, fill=theme["text"], weight=700),
        _text_block(body, x=90, y=835, size=34, line_height=48, fill=theme["muted"], weight=400),
        _template_art(scene, storyboard["site"], theme),
        _text_block(footer, x=90, y=1705, size=28, line_height=40, fill=theme["muted"], weight=400),
        f'<text x="990" y="1810" text-anchor="end" font-size="24" fill="{theme["muted"]}">{escape(scene["scene_id"])} · {scene["duration_ms"] / 1000:.1f}s</text>',
        '</g>',
        f'<rect x="90" y="1845" width="900" height="12" rx="6" fill="{theme["panel"]}"/>',
        f'<rect x="90" y="1845" width="{progress_width}" height="12" rx="6" fill="{theme["signal"]}"/>',
        '</svg>',
        '',
    ])


def render_storyboard(
    storyboard: dict[str, Any],
    output_dir: Path | str,
    *,
    rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write only original SVG assets and return a sealed manifest."""
    config = rules or load_visual_rules()
    digest = str(storyboard.get("content_hash") or "") if isinstance(storyboard, dict) else ""
    try:
        expected_id = storyboard_id(str(storyboard.get("site") or ""), digest)
    except (AttributeError, ValueError):
        expected_id = ""
    if (
        not isinstance(storyboard, dict)
        or set(storyboard) != STORYBOARD_KEYS
        or storyboard.get("schema_version") != STORYBOARD_SCHEMA_VERSION
        or digest != storyboard_content_hash(storyboard)
        or storyboard.get("storyboard_id") != expected_id
        or storyboard.get("human_review_required") is not True
        or storyboard.get("publication_allowed") is not False
        or storyboard.get("rights_policy") != "generated_original_only"
        or not isinstance(storyboard.get("scenes"), list)
        or not storyboard.get("scenes")
        or any(not isinstance(scene, dict) or set(scene) != STORYBOARD_SCENE_KEYS for scene in storyboard["scenes"])
    ):
        raise ValueError("invalid-storyboard-for-render")
    target = Path(output_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    if target.name != "assets":
        raise ValueError("visual-output-directory-must-be-assets")
    if any(target.iterdir()):
        raise ValueError("visual-output-directory-must-be-empty")
    theme = config["themes"][storyboard["site"]]
    rights = config["rights"]
    assets: list[dict[str, Any]] = []
    for scene in storyboard["scenes"]:
        filename = f'{scene["scene_id"]}.svg'
        path = target / filename
        path.write_text(render_scene_svg(storyboard, scene, theme), encoding="utf-8", newline="\n")
        assets.append({
            "asset_id": scene["asset_id"],
            "scene_id": scene["scene_id"],
            "file": f"assets/{filename}",
            "media_type": "image/svg+xml",
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
            "width_px": storyboard["width_px"],
            "height_px": storyboard["height_px"],
            "rights_status": rights["status"],
            "credit": rights["credit"],
            "allowed_uses": list(rights["allowed_uses"]),
            "fact_ids": list(scene["fact_ids"]),
            "statement_ids": list(scene["statement_ids"]),
            "source_ids": list(scene["source_ids"]),
        })
    manifest: dict[str, Any] = {
        "schema_version": VISUAL_MANIFEST_SCHEMA_VERSION,
        "manifest_id": "",
        "content_hash": "",
        "renderer_version": VISUAL_RENDERER_VERSION,
        "storyboard_id": storyboard["storyboard_id"],
        "storyboard_content_hash": storyboard["content_hash"],
        "package_id": storyboard["package_id"],
        "script_id": storyboard["script_id"],
        "generated_at": storyboard["generated_at"],
        "engine": "straitwatch-svg",
        "network_used": False,
        "external_assets_used": False,
        "human_review_required": True,
        "publication_allowed": False,
        "assets": assets,
    }
    digest = visual_manifest_content_hash(manifest)
    manifest["content_hash"] = digest
    manifest["manifest_id"] = visual_manifest_id(digest)
    return manifest
