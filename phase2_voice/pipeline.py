"""Temporary artifacts, immutable editorial input and validated idempotent reuse."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from .audio import inspect_audio
from .gemini import render_gemini
from .input import build_voice_input, default_pronunciation
from .schema import VoiceError, digest
from .validator import IDENTITY_KEYS, segment_map, validate_audio

SECRET_PATTERN = re.compile(r"AIza[0-9A-Za-z_-]{20,}|(?:api[_-]?key|authorization|bearer|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_-]{12,}", re.I)
ARTIFACT_NAMES = {"video-package.json", "script.json", "voice-input.json", "audio-gemini.wav", "audio-metadata.json", "validation-report.json", "preview.md", ".voice.lock"}


def audit_output(text: str) -> None:
    values = [os.getenv(name, "") for name in ("GEMINI_API_KEY", "OPENROUTER_API_KEY")]
    if SECRET_PATTERN.search(text) or any(value in text for value in values if len(value) >= 8):
        raise VoiceError("SECRET_DETECTED_IN_OUTPUT")


def write_text(path: Path, text: str) -> None:
    audit_output(text)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def write_json(path: Path, value: dict) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise VoiceError("CORRUPT_CACHED_ARTIFACT") from None


def make_metadata(value: dict, data: bytes) -> dict:
    metrics, _ = inspect_audio(data, value["target_seconds"])
    config = value["voice_config"]
    return {
        "schema_version": "1.0.0", **{key: value[key] for key in IDENTITY_KEYS},
        **{key: config[key] for key in ("provider", "model", "voice", "profile_id", "locale")},
        "input_hash": digest(value), "audio_sha256": hashlib.sha256(data).hexdigest(),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "audio_filename": "audio-gemini.wav", "audio_metrics": metrics,
        "segment_map": segment_map(value, metrics.get("duration_seconds", 0)),
        "alignment": "structural-proportional-estimate-not-ASR", "human_review_required": True,
        "human_review_status": "PENDING", "transcript_validation": "NOT_RUN",
        "billing": {"enabled_by_pipeline": False, "model_free_tier_documented": True, "account_tier_verified": False, "automatic_upgrade": False},
        "generation_trace": [{"provider": "gemini", "attempts": 1, "fallback_used": False}],
    }


def preview(value: dict, report: dict, fixture: dict) -> str:
    config = value["voice_config"]
    metrics = report.get("audio_metrics", {})
    lines = [
        "# STRAITWATCH · Piloto de voz Gemini", "",
        f"Fixture histórico: {fixture.get('historical_fixture', 'NO DECLARADO')}", "",
        f"Procedencia: {fixture.get('fixture_source', 'Paquete y guion proporcionados; revalidados localmente')}", "",
        "No presenta una instantánea histórica como estado actual.", "",
        f"Modelo: {config['model']} · Voz: {config['voice']} · Perfil: {config['profile_id']}", "",
        f"Idioma: {config['locale']} · Objetivo: {value['target_seconds']} s · Real: {metrics.get('duration_seconds', 'pendiente')} s", "",
        f"Validación técnica: {report['validation_status']} · Errores: {', '.join(report.get('validation_errors', [])) or 'ninguno'}", "",
        "Aprobación humana: PENDIENTE. Transcripción/ASR: NO ejecutada.", "",
        "Comprobar texto íntegro, cifras, nombres, pronunciación, acento peninsular y calidad de locución.", "",
        "Publicación y continuación audiovisual: DESACTIVADAS.", "",
        "No hay alineación acústica: los tiempos por segmento son estimaciones proporcionales, no marcas ASR.", "",
        "La API no demuestra el nivel de facturación de la cuenta. No se activa facturación ni se cambia de modelo.", "",
        "## Escuchar el candidato", "", "[WAV nativo](audio-gemini.wav)" if metrics else "Audio todavía no disponible.", "",
        "## Texto editorial original", "", value["full_editorial_text"], "",
        "## Texto enviado a TTS", "", value["full_text_for_tts"], "",
        "## Pronunciación pendiente de revisión", "", ", ".join(value["pending_pronunciation_review"]) or "Sin términos de la lista en este guion.", "",
        "## Identidad y trazabilidad", "", f"Job: `{value['voice_job_id']}`", "", f"Guion: `{value['script_id']}`", "",
    ]
    return "\n".join(lines)


def run_voice_job(package: dict, script: dict, output_dir: Path, *, repo_root: Path, fixture: dict | None = None, prepare_only: bool = False, provider=render_gemini, config: dict | None = None, pronunciation: dict | None = None) -> dict:
    output_dir, repo_root = output_dir.resolve(), repo_root.resolve()
    if output_dir == repo_root or output_dir.is_relative_to(repo_root):
        raise VoiceError("OUTPUT_MUST_BE_OUTSIDE_REPOSITORY")
    rules = pronunciation if pronunciation is not None else default_pronunciation(script)
    value = build_voice_input(package, script, config=config, pronunciation=rules)
    # Audit everything before writing anything; a credential cannot enter an artifact.
    for item in (package, script, value, fixture or {}):
        audit_output(json.dumps(item, ensure_ascii=False))
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(path.name not in ARTIFACT_NAMES for path in output_dir.iterdir()):
        raise VoiceError("OUTPUT_DIRECTORY_CONFLICT")
    lock = output_dir / ".voice.lock"
    try:
        handle = lock.open("x", encoding="utf-8")
    except FileExistsError:
        raise VoiceError("JOB_ALREADY_RUNNING") from None
    try:
        handle.close()
        existing = output_dir / "voice-input.json"
        if existing.exists() and read_json(existing) != value:
            raise VoiceError("OUTPUT_IDENTITY_CONFLICT")
        inputs = {"video-package.json": package, "script.json": script, "voice-input.json": value}
        for name, item in inputs.items():
            write_json(output_dir / name, item)
        audio_path, meta_path = output_dir / "audio-gemini.wav", output_dir / "audio-metadata.json"
        if audio_path.exists() or meta_path.exists():
            if not audio_path.exists() or not meta_path.exists():
                raise VoiceError("INCOMPLETE_CACHED_JOB")
            data, metadata = audio_path.read_bytes(), read_json(meta_path)
            report = validate_audio(package, script, value, data, metadata, pronunciation=rules)
            report["cache_hit"] = True
        elif prepare_only:
            report = {"voice_job_id": value["voice_job_id"], "validation_status": "READY", "validation_errors": [], "cache_hit": False, "human_review_required": True, "human_review_status": "PENDING", "publication": "DISABLED"}
        else:
            previous = output_dir / "validation-report.json"
            if previous.exists() and read_json(previous).get("validation_status") == "FAIL":
                raise VoiceError("FAILED_JOB_REQUIRES_EXPLICIT_NEW_ATTEMPT_DIRECTORY")
            try:
                data = provider(package, script, value, pronunciation=rules)
            except VoiceError as exc:
                report = {"voice_job_id": value["voice_job_id"], "validation_status": "FAIL", "validation_errors": [exc.code], "audio_metrics": {}, "cache_hit": False, "human_review_required": True, "human_review_status": "PENDING", "publication": "DISABLED"}
            except Exception:
                # Never serialize or print an exception supplied by an HTTP client.
                report = {"voice_job_id": value["voice_job_id"], "validation_status": "FAIL", "validation_errors": ["INTERNAL_PROVIDER_ERROR"], "audio_metrics": {}, "cache_hit": False, "human_review_required": True, "human_review_status": "PENDING", "publication": "DISABLED"}
            else:
                metadata = make_metadata(value, data)
                temporary = audio_path.with_suffix(".wav.tmp")
                temporary.write_bytes(data)
                temporary.replace(audio_path)
                write_json(meta_path, metadata)
                report = validate_audio(package, script, value, data, metadata, pronunciation=rules)
                report["cache_hit"] = False
            if report["validation_status"] == "FAIL" and not meta_path.exists():
                metadata = make_metadata(value, b"")
                metadata["audio_filename"] = None
                metadata["audio_sha256"] = None
                if report["validation_errors"] == ["MISSING_API_KEY"]:
                    metadata["generation_trace"][0]["attempts"] = 0
                write_json(meta_path, metadata)
        report["fixture"] = fixture or {"historical_fixture": "NOT_DECLARED"}
        write_json(output_dir / "validation-report.json", report)
        write_text(output_dir / "preview.md", preview(value, report, fixture or {}))
        return report
    finally:
        lock.unlink(missing_ok=True)
