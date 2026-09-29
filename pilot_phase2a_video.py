#!/usr/bin/env python3
"""Manual, non-publishing Phase 2A pilot for either StraitWatch site."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phase2_video.package import build_video_package, load_site_inputs
from phase2_video.schema import parse_utc
from phase2_video.script import generate_local_script, generate_script
from phase2_video.validator import validate_package, validate_script
from straitwatch_core import SourceRegistry, aggregate_events


OUTPUT_NAMES = {
    "video-package.json",
    "script-local.json",
    "script-gemini.json",
    "validation-local.json",
    "validation-gemini.json",
    "preview.md",
}
SECRET_PATTERN = re.compile(
    r"(?:AIza[0-9A-Za-z_-]{20,}|sk-or-v1-[0-9A-Za-z]{20,}|"
    r"(?:api[_-]?key|authorization|bearer|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_-]{12,})",
    re.I,
)


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return default


def _ormuz_historical_fixture(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    store = load_json(root / "events.json", {})
    eligible = [
        event for event in store.get("events", [])
        if isinstance(event, dict)
        and event.get("verification_status") in {"CONFIRMED_PRIMARY", "CONFIRMED_MULTI_SOURCE"}
        and int(event.get("importance") or 0) >= 65
    ]
    if not eligible:
        raise RuntimeError("no-real-ormuz-event-for-historical-fixture")
    event = max(eligible, key=lambda item: (int(item.get("importance") or 0), str(item.get("last_seen") or "")))
    event_time = parse_utc(event.get("last_seen"))
    history = load_json(root / "operational-intelligence-history.json", [])
    states = [
        row for row in history
        if isinstance(row, dict)
        and row.get("generated_at")
        and parse_utc(row["generated_at"]) >= event_time
    ]
    if not states:
        raise RuntimeError("no-ormuz-state-after-real-event")
    canonical = min(states, key=lambda row: parse_utc(row["generated_at"]))
    package = build_video_package(
        site="ormuz",
        event_store={"schema_version": store.get("schema_version"), "events": [event]},
        operational_context={
            "state": canonical["state"],
            "confidence": canonical["confidence"],
            "dimensions": canonical.get("dimensions") or {},
            "as_of": canonical["generated_at"],
            # The historical state archive does not preserve the complete
            # Phase 1 health envelope.  Degraded is the conservative value.
            "health": "degraded",
        },
        source_health="degraded",
        comparison=["El evento verificado se incorporó a esta instantánea histórica."],
        what_we_dont_know=[
            "La instantánea histórica no conserva el sobre completo de salud de fuentes.",
            "Una declaración no sustituye una confirmación operativa.",
        ],
        watch_next_24h=[
            "Nuevas confirmaciones operativas y avisos marítimos oficiales.",
            "Corroboración independiente de cualquier cambio material.",
        ],
        headlines={"es": event["headline"], "en": event["headline"]},
        content_kind="event",
        event_id=event["event_id"],
        generated_at=canonical["generated_at"],
        edition_date=str(canonical["generated_at"])[:10],
    )
    return package, {
        "historical_fixture": True,
        "fixture_source": "events.json + operational-intelligence-history.json",
        "fixture_event_id": event["event_id"],
    }


def _gibraltar_historical_fixture(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    ope_history = load_json(root / "ope-history.json", [])
    observatory_history = load_json(root / "observatory-history.json", [])
    snapshot = next((row for row in observatory_history if row.get("date") == "2026-08-15"), None)
    report = next((row for row in ope_history if row.get("report_date") == "2026-08-14"), None)
    if not isinstance(snapshot, dict) or not isinstance(report, dict):
        raise RuntimeError("missing-real-gibraltar-historical-fixture-data")
    metrics = snapshot.get("metrics") if isinstance(snapshot.get("metrics"), dict) else {}
    passengers = int(report["departure"]["passengers"]) + int(report["return"]["passengers"])
    vehicles = int(report["departure"]["vehicles"]) + int(report["return"]["vehicles"])
    rotations = int(report["departure"]["rotations"]) + int(report["return"]["rotations"])
    if (passengers, vehicles, rotations) != (
        int(metrics.get("ope_passengers_day") or -1),
        int(metrics.get("ope_vehicles_day") or -1),
        int(metrics.get("ope_rotations_day") or -1),
    ):
        raise RuntimeError("gibraltar-historical-fixture-crosscheck-failed")
    headline_es = (
        f"Protección Civil registró {passengers} pasajeros, {vehicles} vehículos y "
        f"{rotations} rotaciones en la OPE del 14 de agosto de 2026"
    )
    headline_en = (
        f"Spanish Civil Protection recorded {passengers} passengers, {vehicles} vehicles and "
        f"{rotations} rotations in the Strait Crossing Operation on 14 August 2026"
    )
    registry = SourceRegistry.from_path(root / "source-registry.json")
    store = aggregate_events(
        [{
            "title": headline_es,
            "description": "",
            "source": "Secretaría General de Protección Civil y Emergencias",
            "url": report["source_url"],
            "published_at": "2026-08-14T21:00:00Z",
            "observed_at": snapshot["generated_at"],
            "topic": "maritime",
            "signal": "TRAFFIC_PRESENT",
        }],
        registry,
        generated_at=snapshot["generated_at"],
    )
    event = store["events"][0]
    event["headline_es"] = headline_es
    event["headline_en"] = headline_en
    package = build_video_package(
        site="gibraltar",
        event_store=store,
        operational_context={
            "state": snapshot["state_code"],
            # The compact history did not retain confidence. Low preserves the
            # uncertainty instead of reconstructing or upgrading it.
            "confidence": "low",
            "dimensions": {
                "state_label": snapshot.get("state_label"),
                "ope_metrics": metrics,
            },
            "as_of": snapshot["generated_at"],
            "health": snapshot["health"],
        },
        source_health=snapshot["health"],
        comparison=[
            "El parte oficial de la OPE del 14 de agosto quedó incorporado al observatorio histórico."
        ],
        what_we_dont_know=[
            "La instantánea compacta no conservó un nivel explícito de confianza; el piloto usa confianza baja.",
            "El informe diario no es un contador de tráfico en tiempo real.",
        ],
        watch_next_24h=[
            "El siguiente parte oficial de Protección Civil y cualquier aviso portuario.",
            "Cambios verificados en la continuidad de las rutas marítimas.",
        ],
        headlines={"es": headline_es, "en": headline_en},
        content_kind="event",
        event_id=event["event_id"],
        generated_at=snapshot["generated_at"],
        edition_date=snapshot["date"],
    )
    return package, {
        "historical_fixture": True,
        "fixture_source": "ope-history.json + observatory-history.json",
        "fixture_event_id": event["event_id"],
    }


def select_package(root: Path, site: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Prefer a current real candidate; otherwise use a labelled real fixture."""
    inputs = load_site_inputs(root, site)
    store = inputs["event_store"]
    candidates = sorted(
        [event for event in store.get("events", []) if isinstance(event, dict)],
        key=lambda item: (int(item.get("importance") or 0), str(item.get("last_seen") or "")),
        reverse=True,
    )
    now = datetime.now(timezone.utc).replace(microsecond=0)
    for event in candidates:
        try:
            package = build_video_package(
                site=site,
                event_store=store,
                operational_context=inputs["operational_context"],
                source_health=inputs["source_health"],
                comparison=inputs["comparison"],
                what_we_dont_know=inputs["what_we_dont_know"],
                watch_next_24h=inputs["watch_next_24h"],
                headlines=inputs["headlines"],
                content_kind="event",
                event_id=event.get("event_id"),
                generated_at=now.isoformat().replace("+00:00", "Z"),
                edition_date=now.date().isoformat(),
            )
        except (TypeError, ValueError):
            continue
        if package.get("video_recommended") is True and validate_package(package)["validation_status"] == "PASS":
            return package, {
                "historical_fixture": False,
                "fixture_source": "current Phase 1 stores",
                "fixture_event_id": event.get("event_id"),
            }
    return _ormuz_historical_fixture(root) if site == "ormuz" else _gibraltar_historical_fixture(root)


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def _script_preview(label: str, script: dict[str, Any], validation: dict[str, Any]) -> str:
    lines = [
        f"## {label}", "", f"Generado por: `{script.get('generated_by')}`", "",
        f"Duración objetivo: {script.get('target_seconds')} segundos", "",
        f"Palabras estimadas: {script.get('estimated_words')}", "",
        "### Hook", "", str(script.get("hook") or ""), "",
    ]
    for scene in script.get("scenes", []):
        lines.extend([
            f"### {scene.get('scene_id')}", "",
            "**Voz**", "", str(scene.get("voiceover") or ""), "",
            "**Respaldo**", "", ", ".join([*scene.get("fact_ids", []), *scene.get("statement_ids", [])]) or "Ninguno", "",
            "**Fuentes**", "", ", ".join(scene.get("source_ids", [])) or "Ninguna", "",
            "**Visual**", "", str(scene.get("visual_intent") or ""), "",
        ])
    lines.extend([
        "### Validación", "", validation.get("validation_status", "FAIL"), "",
        "Errores: " + (", ".join(validation.get("validation_errors", [])) or "ninguno"), "",
    ])
    return "\n".join(lines)


def render_preview(
    package: dict[str, Any],
    local_script: dict[str, Any],
    remote_script: dict[str, Any],
    local_validation: dict[str, Any],
    remote_validation: dict[str, Any],
    metadata: dict[str, Any],
) -> str:
    reasons = package["video_recommendation"]["reason_codes"]
    local_voice = " ".join(scene["voiceover"] for scene in local_script["scenes"])
    remote_voice = " ".join(scene["voiceover"] for scene in remote_script["scenes"])
    changed = local_voice != remote_voice
    return "\n".join([
        "# STRAITWATCH VIDEO CANDIDATE", "",
        f"Sitio: **{package['site']}**", "",
        f"Fixture histórico: **{'SÍ' if metadata['historical_fixture'] else 'NO'}**", "",
        f"Procedencia: `{metadata['fixture_source']}`", "",
        f"Tipo: **{package['video_type']}**", "",
        f"Importancia: **{package['importance']}/100**", "",
        f"Verificación: **{', '.join(sorted({fact['verification_status'] for fact in package['verified_facts']}))}**", "",
        "Motivos:", *(f"- `{reason}`" for reason in reasons), "",
        "Publicación: **NO**", "",
        "Revisión humana obligatoria: **SÍ**", "",
        "## Comparación", "",
        f"El guion remoto cambió el texto local: **{'SÍ' if changed else 'NO'}**.", "",
        f"Proveedor final: **{remote_script.get('generated_by')}**.", "",
        f"Ambos guiones respetan los hechos: **{'SÍ' if local_validation['validation_status'] == remote_validation['validation_status'] == 'PASS' else 'NO'}**.", "",
        f"Información nueva detectada: **{'NO' if remote_validation['validation_status'] == 'PASS' else 'SÍ'}**.", "",
        "## Qué no sabemos", "",
        *[f"- {item}" for item in package.get("what_we_dont_know", [])], "",
        _script_preview("LOCAL", local_script, local_validation),
        _script_preview("GEMINI / FALLBACK", remote_script, remote_validation),
    ]) + "\n"


def _audit_secrets(rendered: dict[str, str]) -> None:
    secret_values = [
        value for value in (os.getenv("GEMINI_API_KEY"), os.getenv("OPENROUTER_API_KEY"))
        if value and len(value) >= 8
    ]
    for name, text in rendered.items():
        if SECRET_PATTERN.search(text) or any(secret in text for secret in secret_values):
            raise RuntimeError(f"secret-detected-in-pilot-output:{name}")


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

    package, metadata = select_package(root, site)
    package_validation = validate_package(package)
    if package_validation["validation_status"] != "PASS" or package.get("video_recommended") is not True:
        raise RuntimeError("pilot-package-not-valid-or-not-recommended:" + ",".join(package_validation["validation_errors"]))
    local_script = generate_local_script(package)
    local_validation = validate_script(package, local_script)
    remote_script, generation_trace = generate_script(package)
    remote_validation = validate_script(package, remote_script)
    local_validation.update(metadata)
    local_validation["fallback_used"] = False
    remote_validation.update(metadata)
    remote_validation["generation_trace"] = generation_trace
    preview = render_preview(
        package, local_script, remote_script, local_validation, remote_validation, metadata
    )
    rendered = {
        "video-package.json": _json_text(package),
        "script-local.json": _json_text(local_script),
        "script-gemini.json": _json_text(remote_script),
        "validation-local.json": _json_text(local_validation),
        "validation-gemini.json": _json_text(remote_validation),
        "preview.md": preview,
    }
    _audit_secrets(rendered)
    for name, text in rendered.items():
        (output_dir / name).write_text(text, encoding="utf-8")
    if set(path.name for path in output_dir.iterdir() if path.is_file()) != OUTPUT_NAMES:
        raise RuntimeError("unexpected-pilot-output")
    if local_validation["validation_status"] != "PASS" or remote_validation["validation_status"] != "PASS":
        raise RuntimeError("pilot-script-validation-failed")
    return {
        "site": site,
        "package_id": package["package_id"],
        "content_hash": package["content_hash"],
        "historical_fixture": metadata["historical_fixture"],
        "local": local_validation["validation_status"],
        "remote": remote_validation["validation_status"],
        "generated_by": remote_script["generated_by"],
        "output_dir": str(output_dir),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", choices=("ormuz", "gibraltar"), required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    output = args.output_dir or Path(tempfile.mkdtemp(prefix=f"straitwatch-{args.site}-phase2a-"))
    result = run_pilot(args.root, args.site, output)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
