#!/usr/bin/env python3
"""Manual, isolated and non-publishing StraitWatch Phase 2B voice pilot."""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from pathlib import Path
from typing import Any, Callable

from phase2_video.script import generate_local_script
from phase2_video.validator import validate_package, validate_script
from phase2_voice.package import build_voice_package
from phase2_voice.render import render_voice_package
from phase2_voice.validator import validate_audio, validate_voice_package
from pilot_phase2a_video import select_package


OUTPUT_NAMES = {
    "video-package.json",
    "script.json",
    "voice-package.json",
    "audio-local.wav",
    "audio-manifest.json",
    "validation-voice-package.json",
    "validation-audio.json",
    "preview.md",
}
SECRET_PATTERN = re.compile(
    r"(?:AIza[0-9A-Za-z_-]{20,}|sk-or-v1-[0-9A-Za-z]{20,}|"
    r"(?:api[_-]?key|authorization|bearer|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_-]{12,})",
    re.I,
)


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_preview(
    voice_package: dict[str, Any],
    manifest: dict[str, Any],
    package_validation: dict[str, Any],
    audio_validation: dict[str, Any],
    metadata: dict[str, Any],
) -> str:
    narration = voice_package["narration"]
    profile = voice_package["voice_profile"]
    segments = narration["segments"]
    lines = [
        "# STRAITWATCH · CANDIDATO DE VOZ", "",
        f"Sitio: **{voice_package['site']}**", "",
        f"Fixture histórico: **{'SÍ' if metadata['historical_fixture'] else 'NO'}**", "",
        f"Procedencia: `{metadata['fixture_source']}`", "",
        f"Paquete de vídeo: `{voice_package['video_package_id']}`", "",
        f"Guion: `{voice_package['script_id']}`", "",
        f"Motor local: **{profile['engine']}**", "",
        f"Voz: **{profile['voice']}**", "",
        f"Duración: **{manifest['duration_seconds']:.2f} s**", "",
        f"Audio: **{manifest['sample_rate_hz']} Hz · {manifest['channels']} canal · {manifest['sample_width_bits']} bit**", "",
        f"Validación del paquete: **{package_validation['validation_status']}**", "",
        f"Validación técnica del audio: **{audio_validation['validation_status']}**", "",
        "Red utilizada para sintetizar: **NO**", "",
        "Clonación de voz: **NO**", "",
        "Publicación: **NO**", "",
        "Revisión humana obligatoria: **SÍ**", "",
        "Escucha semántica y de pronunciación: **PENDIENTE**", "",
        "## Texto sintetizado", "",
    ]
    for segment in segments:
        refs = [*segment["fact_ids"], *segment["statement_ids"]]
        lines.extend([
            f"### {segment['segment_id']}", "",
            segment["text"], "",
            "Trazabilidad: " + (", ".join(refs) or "texto de plantilla sin afirmación nueva"), "",
        ])
    lines.extend([
        "## Límite de esta validación", "",
        "El hash acredita qué texto se entregó al sintetizador y la validación técnica acredita el WAV resultante. "
        "La pronunciación, el ritmo y la correspondencia audible completa deben revisarse escuchando el archivo antes de cualquier uso.", "",
    ])
    return "\n".join(lines)


def _audit_text_outputs(rendered: dict[str, str]) -> None:
    for name, text in rendered.items():
        if SECRET_PATTERN.search(text):
            raise RuntimeError(f"secret-detected-in-pilot-output:{name}")


def run_pilot(
    root: Path,
    site: str,
    output_dir: Path,
    *,
    renderer: Callable[..., dict[str, Any]] = render_voice_package,
) -> dict[str, Any]:
    root = root.resolve()
    output_dir = output_dir.resolve()
    try:
        output_dir.relative_to(root)
    except ValueError:
        pass
    else:
        raise ValueError("pilot-output-must-be-outside-repository")
    output_dir.mkdir(parents=True, exist_ok=True)

    video_package, metadata = select_package(root, site)
    script = generate_local_script(video_package)
    if validate_package(video_package)["validation_status"] != "PASS":
        raise RuntimeError("pilot-video-package-invalid")
    if validate_script(video_package, script)["validation_status"] != "PASS":
        raise RuntimeError("pilot-video-script-invalid")
    voice_package = build_voice_package(video_package, script)
    package_validation = validate_voice_package(video_package, script, voice_package)
    if package_validation["validation_status"] != "PASS":
        raise RuntimeError("pilot-voice-package-invalid:" + ",".join(package_validation["validation_errors"]))

    audio_path = output_dir / "audio-local.wav"
    manifest = renderer(voice_package, audio_path)
    audio_validation = validate_audio(voice_package, manifest, audio_path)
    preview = render_preview(voice_package, manifest, package_validation, audio_validation, metadata)
    rendered = {
        "video-package.json": _json_text(video_package),
        "script.json": _json_text(script),
        "voice-package.json": _json_text(voice_package),
        "audio-manifest.json": _json_text(manifest),
        "validation-voice-package.json": _json_text(package_validation),
        "validation-audio.json": _json_text(audio_validation),
        "preview.md": preview,
    }
    _audit_text_outputs(rendered)
    for name, text in rendered.items():
        (output_dir / name).write_text(text, encoding="utf-8")
    actual = {path.name for path in output_dir.iterdir() if path.is_file()}
    if actual != OUTPUT_NAMES:
        raise RuntimeError("unexpected-pilot-output:" + ",".join(sorted(actual)))
    if audio_validation["validation_status"] != "PASS":
        raise RuntimeError("pilot-audio-validation-failed:" + ",".join(audio_validation["validation_errors"]))
    return {
        "site": site,
        "voice_package_id": voice_package["voice_package_id"],
        "content_hash": voice_package["content_hash"],
        "historical_fixture": metadata["historical_fixture"],
        "voice_package_validation": package_validation["validation_status"],
        "audio_validation": audio_validation["validation_status"],
        "semantic_listening_required": True,
        "publication_allowed": False,
        "output_dir": str(output_dir),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", choices=("ormuz", "gibraltar"), required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    output = args.output_dir or Path(tempfile.mkdtemp(prefix=f"straitwatch-{args.site}-phase2b-"))
    result = run_pilot(args.root, args.site, output)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
