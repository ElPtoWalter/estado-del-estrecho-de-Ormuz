#!/usr/bin/env python3
"""Manual, local-only Phase 2C storyboard and graphics pilot."""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from pathlib import Path
from typing import Any

from phase2_video.script import generate_local_script
from phase2_video.validator import validate_package, validate_script
from phase2_visual.render import render_storyboard
from phase2_visual.storyboard import build_storyboard
from phase2_visual.validator import validate_storyboard, validate_visual_manifest
from pilot_phase2a_video import select_package


OUTPUT_NAMES = {
    "video-package.json",
    "script.json",
    "storyboard.json",
    "visual-manifest.json",
    "validation.json",
    "storyboard.md",
    "assets",
}
SECRET_PATTERN = re.compile(
    r"(?:AIza[0-9A-Za-z_-]{20,}|sk-[0-9A-Za-z_-]{20,}|"
    r"(?:api[_-]?key|authorization|bearer|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_-]{12,})",
    re.I,
)


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_preview(
    package: dict[str, Any],
    script: dict[str, Any],
    storyboard: dict[str, Any],
    manifest: dict[str, Any],
    validation: dict[str, Any],
    metadata: dict[str, Any],
) -> str:
    assets = {asset["scene_id"]: asset for asset in manifest["assets"]}
    lines = [
        "# STRAITWATCH · STORYBOARD FASE 2C", "",
        f"Sitio: **{package['site']}**", "",
        f"Fixture histórico: **{'SÍ' if metadata['historical_fixture'] else 'NO'}**", "",
        f"Procedencia: `{metadata['fixture_source']}`", "",
        f"Tipo: **{package['video_type']}**", "",
        f"Formato: **{storyboard['aspect_ratio']} · {storyboard['width_px']}×{storyboard['height_px']} · {storyboard['fps']} fps**", "",
        f"Duración planificada: **{storyboard['target_seconds']} segundos**", "",
        "Recursos externos: **NO**", "",
        "Red utilizada: **NO**", "",
        "Publicación: **NO**", "",
        "Revisión humana obligatoria: **SÍ**", "",
        "## Escenas", "",
    ]
    for scene in storyboard["scenes"]:
        asset = assets[scene["scene_id"]]
        lines.extend([
            f"### {scene['scene_id']} · {scene['start_ms'] / 1000:.1f}s–{scene['end_ms'] / 1000:.1f}s", "",
            f"![{scene['headline']}]({asset['file']})", "",
            f"- Intención solicitada: `{scene['requested_intent']}`", 
            f"- Plantilla resuelta: `{scene['resolved_template']}`",
            f"- Respaldo factual: `{', '.join(scene['fact_ids']) or 'ninguno'}`",
            f"- Declaraciones: `{', '.join(scene['statement_ids']) or 'ninguna'}`",
            f"- Fuentes: `{', '.join(scene['source_ids']) or 'ninguna'}`",
            f"- Derechos: `{asset['rights_status']}` · `{', '.join(asset['allowed_uses'])}`", "",
        ])
    lines.extend([
        "## Validación", "",
        f"Paquete factual: **{validation['package']['validation_status']}**", "",
        f"Guion: **{validation['script']['validation_status']}**", "",
        f"Storyboard: **{validation['storyboard']['validation_status']}**", "",
        f"Activos: **{validation['manifest']['validation_status']}**", "",
        "## Límites", "",
        "Los mapas son localizadores editoriales esquemáticos y no sirven para navegación.", "",
        "No se ha generado voz, avatar, metraje real ni vídeo final.", "",
        "Cualquier uso posterior exige escucha, QA audiovisual, revisión de derechos y aprobación humana.", "",
    ])
    return "\n".join(lines)


def _audit_outputs(output_dir: Path) -> None:
    for path in output_dir.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if SECRET_PATTERN.search(text):
            raise RuntimeError(f"secret-detected-in-visual-output:{path.name}")


def run_pilot(root: Path, site: str, output_dir: Path) -> dict[str, Any]:
    root = root.resolve()
    output_dir = output_dir.resolve()
    try:
        output_dir.relative_to(root)
    except ValueError:
        pass
    else:
        raise ValueError("pilot-output-must-be-outside-repository")
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise ValueError("pilot-output-directory-must-be-empty")

    package, metadata = select_package(root, site)
    package_validation = validate_package(package)
    if package_validation["validation_status"] != "PASS" or package.get("video_recommended") is not True:
        raise RuntimeError("pilot-package-not-valid-or-not-recommended")
    script = generate_local_script(package)
    script_validation = validate_script(package, script)
    if script_validation["validation_status"] != "PASS":
        raise RuntimeError("pilot-script-not-valid")
    storyboard = build_storyboard(package, script)
    storyboard_validation = validate_storyboard(package, script, storyboard)
    if storyboard_validation["validation_status"] != "PASS":
        raise RuntimeError("pilot-storyboard-not-valid")
    manifest = render_storyboard(storyboard, output_dir / "assets")
    manifest_validation = validate_visual_manifest(
        package, script, storyboard, manifest, output_dir
    )
    if manifest_validation["validation_status"] != "PASS":
        raise RuntimeError("pilot-visual-manifest-not-valid")
    validation = {
        "package": package_validation,
        "script": script_validation,
        "storyboard": storyboard_validation,
        "manifest": manifest_validation,
        **metadata,
        "publication_allowed": False,
        "human_review_required": True,
    }
    rendered = {
        "video-package.json": _json_text(package),
        "script.json": _json_text(script),
        "storyboard.json": _json_text(storyboard),
        "visual-manifest.json": _json_text(manifest),
        "validation.json": _json_text(validation),
        "storyboard.md": render_preview(package, script, storyboard, manifest, validation, metadata),
    }
    for name, text in rendered.items():
        (output_dir / name).write_text(text, encoding="utf-8", newline="\n")
    _audit_outputs(output_dir)
    if {path.name for path in output_dir.iterdir()} != OUTPUT_NAMES:
        raise RuntimeError("unexpected-pilot-output")
    return {
        "site": site,
        "package_id": package["package_id"],
        "script_id": script["script_id"],
        "storyboard_id": storyboard["storyboard_id"],
        "manifest_id": manifest["manifest_id"],
        "historical_fixture": metadata["historical_fixture"],
        "scene_count": len(storyboard["scenes"]),
        "validation_status": "PASS",
        "publication_allowed": False,
        "output_dir": str(output_dir),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", choices=("ormuz", "gibraltar"), required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    output = args.output_dir or Path(tempfile.mkdtemp(prefix=f"straitwatch-{args.site}-phase2c-"))
    print(json.dumps(run_pilot(args.root, args.site, output), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
