"""Build a deterministic storyboard from a validated package and script."""

from __future__ import annotations

import re
from typing import Any

from phase2_video.validator import validate_package, validate_script

from .schema import (
    STORYBOARD_SCHEMA_VERSION,
    VISUAL_RULE_VERSION,
    asset_id,
    load_visual_rules,
    storyboard_content_hash,
    storyboard_id,
)


_WORD_RE = re.compile(r"\b[\wáéíóúüñ'-]+\b", re.I)

_STATE_LABELS = {
    "OPEN_SEVERELY_RESTRICTED": "Tránsito muy restringido",
    "OPEN_RESTRICTED": "Tránsito restringido",
    "OPEN": "Abierto",
    "NORMAL": "Normalidad operativa",
    "CLOSED": "Cerrado",
    "UNCERTAIN": "Situación incierta",
    "REINFORCED_WATCH": "Vigilancia reforzada",
}
_CONFIDENCE_LABELS = {"high": "alta", "medium": "media", "low": "baja"}


def _words(value: Any) -> int:
    return len(_WORD_RE.findall(str(value or "")))


def _durations(script: dict[str, Any], minimum_ms: int) -> list[int]:
    scenes = script.get("scenes") or []
    total_ms = int(script["target_seconds"]) * 1000
    if not scenes or total_ms < minimum_ms * len(scenes):
        raise ValueError("visual-timeline-cannot-fit-scenes")
    weights = [max(1, _words(scene.get("voiceover"))) for scene in scenes]
    weights[0] += _words(script.get("hook"))
    weights[-1] += _words(script.get("outro"))
    remaining = total_ms - minimum_ms * len(scenes)
    total_weight = sum(weights)
    exact = [remaining * weight / total_weight for weight in weights]
    extra = [int(value) for value in exact]
    remainder = remaining - sum(extra)
    ranking = sorted(range(len(scenes)), key=lambda index: (-(exact[index] - extra[index]), index))
    for index in ranking[:remainder]:
        extra[index] += 1
    return [minimum_ms + value for value in extra]


def resolve_template(scene: dict[str, Any]) -> str:
    requested = str(scene.get("visual_intent") or "")
    if requested == "presenter":
        return "status-card"
    if requested == "map":
        return "schematic-map"
    if requested == "chart":
        return "metric-card" if re.search(r"\d", str(scene.get("on_screen_text") or "")) else "text-card"
    if requested in {"timeline", "source-card", "status-card", "text-card"}:
        return requested
    raise ValueError("unsupported-visual-intent")


def _source_names(package: dict[str, Any], source_ids: list[str]) -> str:
    names = {
        str(row.get("source_id")): str(row.get("canonical_name") or "")
        for row in package.get("sources", [])
        if isinstance(row, dict)
    }
    selected = [names[source_id] for source_id in source_ids if names.get(source_id)]
    return " · ".join(selected[:3])


def _copy_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _editorial_text(
    package: dict[str, Any], script: dict[str, Any], scene: dict[str, Any], template: str, index: int
) -> tuple[str, str, str, str]:
    context = package["operational_context"]
    on_screen = str(scene.get("on_screen_text") or "").strip()
    headline = on_screen or str(script.get("headline") or "").strip()
    source_names = _source_names(package, _copy_list(scene.get("source_ids")))
    if template == "source-card":
        return "HECHO VERIFICADO", headline, source_names or "Fuente trazada en el paquete", "Consulta la fuente original"
    if template == "status-card":
        state = str(context.get("state") or "").strip()
        state_label = _STATE_LABELS.get(state.upper(), state.replace("_", " ").strip().title())
        confidence = _CONFIDENCE_LABELS.get(str(context.get("confidence") or "").casefold(), "no indicada")
        return "ESTADO OPERATIVO", state_label, f"Confianza {confidence}", "Evaluación heredada de Fase 1"
    if template == "timeline":
        return "QUÉ HA CAMBIADO", headline, "Comparación con la edición anterior", "Cambio trazado y validado"
    if template == "schematic-map":
        return "DÓNDE MIRAMOS", headline, "Localizador editorial esquemático", "No apto para navegación"
    if template == "metric-card":
        return "DATO VERIFICADO", headline, source_names or "Dato trazado en el paquete", "Sin extrapolaciones"
    eyebrow = "INCERTIDUMBRE ABIERTA" if index == len(script.get("scenes") or []) - 1 else "CLAVE VERIFICADA"
    return eyebrow, headline, "Solo información contenida en el guion validado", "Revisión humana obligatoria"


def build_storyboard(
    package: dict[str, Any],
    script: dict[str, Any],
    *,
    rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a sealed storyboard without fetching or accepting external media."""
    config = rules or load_visual_rules()
    package_report = validate_package(package)
    script_report = validate_script(package, script)
    if package_report["validation_status"] != "PASS":
        raise ValueError("invalid-video-package:" + ",".join(package_report["validation_errors"]))
    if script_report["validation_status"] != "PASS":
        raise ValueError("invalid-video-script:" + ",".join(script_report["validation_errors"]))
    frame = config["frame"]
    durations = _durations(script, int(config["timeline"]["minimum_scene_ms"]))
    cursor = 0
    scenes: list[dict[str, Any]] = []
    for index, (source_scene, duration_ms) in enumerate(zip(script["scenes"], durations)):
        template = resolve_template(source_scene)
        eyebrow, headline, body, footer = _editorial_text(
            package, script, source_scene, template, index
        )
        end_ms = cursor + duration_ms
        scene_id = f"visual-scene-{index + 1:02d}"
        scenes.append({
            "scene_id": scene_id,
            "source_scene_id": source_scene["scene_id"],
            "start_ms": cursor,
            "end_ms": end_ms,
            "duration_ms": duration_ms,
            "requested_intent": source_scene["visual_intent"],
            "resolved_template": template,
            "eyebrow": eyebrow,
            "headline": headline,
            "body": body,
            "footer": footer,
            "fact_ids": _copy_list(source_scene.get("fact_ids")),
            "statement_ids": _copy_list(source_scene.get("statement_ids")),
            "source_ids": _copy_list(source_scene.get("source_ids")),
            "asset_id": asset_id(package["package_id"], script["script_id"], scene_id, template),
        })
        cursor = end_ms

    storyboard: dict[str, Any] = {
        "schema_version": STORYBOARD_SCHEMA_VERSION,
        "storyboard_id": "",
        "content_hash": "",
        "rule_version": VISUAL_RULE_VERSION,
        "package_id": package["package_id"],
        "package_content_hash": package["content_hash"],
        "script_id": script["script_id"],
        "site": package["site"],
        "language": script["language"],
        "aspect_ratio": frame["aspect_ratio"],
        "width_px": frame["width_px"],
        "height_px": frame["height_px"],
        "fps": frame["fps"],
        "target_seconds": script["target_seconds"],
        "generated_at": package["generated_at"],
        "human_review_required": True,
        "publication_allowed": False,
        "rights_policy": config["rights"]["policy"],
        "scenes": scenes,
    }
    digest = storyboard_content_hash(storyboard)
    storyboard["content_hash"] = digest
    storyboard["storyboard_id"] = storyboard_id(package["site"], digest)
    return storyboard
