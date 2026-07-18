#!/usr/bin/env python3
"""Rescate de update_status.py para Estrecho Ormuz.

Este archivo restaura automáticamente la última versión completa y funcional
del motor desde el commit 4af49e1eac8e670b83521b46e481a8d2f1b071d5.

Funcionamiento:
- Durante la primera importación de los tests, recupera el motor bueno.
- Valida que sea la versión completa y compatible.
- Sustituye este archivo por el motor restaurado.
- Carga las funciones restauradas en el proceso actual para que los tests sigan.
- En el siguiente paso del workflow, update_status.py ya es el motor original.
"""
from __future__ import annotations

import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "update_status.py"

GOOD_COMMIT = "4af49e1eac8e670b83521b46e481a8d2f1b071d5"
RAW_URL = (
    "https://raw.githubusercontent.com/"
    "ElPtoWalter/estado-del-estrecho-de-Ormuz/"
    f"{GOOD_COMMIT}/update_status.py"
)

USER_AGENT = "Mozilla/5.0 Estrecho-Ormuz-Recovery/1.0"


class RecoveryError(RuntimeError):
    """No se pudo recuperar o validar el motor completo."""


def _download_from_github() -> str:
    request = urllib.request.Request(
        RAW_URL,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/plain,*/*;q=0.8",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        raw = response.read()
    return raw.decode("utf-8-sig")


def _run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _recover_from_git_history() -> str:
    reference = f"{GOOD_COMMIT}:update_status.py"

    result = _run_git("show", reference)
    if result.returncode == 0 and result.stdout:
        return result.stdout

    fetches = (
        ("fetch", "--no-tags", "--depth=1", "origin", GOOD_COMMIT),
        ("fetch", "--no-tags", "--deepen=100", "origin", "main"),
    )
    errors: list[str] = []

    for command in fetches:
        fetched = _run_git(*command)
        if fetched.returncode != 0:
            errors.append(fetched.stderr.strip() or fetched.stdout.strip())

        result = _run_git("show", reference)
        if result.returncode == 0 and result.stdout:
            return result.stdout

    raise RecoveryError(
        "No se pudo recuperar el commit bueno desde Git. "
        + " | ".join(error for error in errors if error)
    )


def _validate(source: str) -> None:
    required_markers = (
        "ENGINE_VERSION = 3",
        "HISTORY_FILE",
        "FEED_FILE",
        "SITEMAP_FILE",
        "def utc_now(",
        "def iso_z(",
        "def classify_text(",
        "def evidence_from_articles(",
        "def analyze_evidence(",
        "def manual_override_payload(",
        "def run_update(",
    )

    missing = [marker for marker in required_markers if marker not in source]
    if missing:
        raise RecoveryError(
            "El archivo recuperado no es el motor completo. Faltan: "
            + ", ".join(missing)
        )

    if len(source.encode("utf-8")) < 60_000:
        raise RecoveryError(
            "El archivo recuperado es demasiado pequeño para ser el motor completo."
        )

    compile(source, str(TARGET), "exec")


def _write_atomically(source: str) -> None:
    temporary = TARGET.with_name("update_status.py.restoring")
    temporary.write_text(source, encoding="utf-8")
    temporary.replace(TARGET)


def _restore() -> str:
    errors: list[str] = []

    try:
        source = _download_from_github()
        _validate(source)
        print("Motor completo recuperado desde el commit seguro de GitHub.")
        return source
    except Exception as exc:
        errors.append(f"Descarga directa: {type(exc).__name__}: {exc}")

    try:
        source = _recover_from_git_history()
        _validate(source)
        print("Motor completo recuperado desde el historial Git local.")
        return source
    except Exception as exc:
        errors.append(f"Historial Git: {type(exc).__name__}: {exc}")

    raise RecoveryError(" | ".join(errors))


try:
    _restored_source = _restore()
    _write_atomically(_restored_source)

    print(
        "update_status.py restaurado correctamente. "
        "Se mantienen el motor de decisión, historial, RSS y portadas."
    )

    exec(compile(_restored_source, str(TARGET), "exec"), globals(), globals())

except Exception as exc:
    print(f"::error::Rescate fallido: {exc}", file=sys.stderr)
    raise
