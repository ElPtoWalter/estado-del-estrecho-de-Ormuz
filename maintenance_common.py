#!/usr/bin/env python3
"""Funciones compartidas por las herramientas de mantenimiento de Ormuz.

Solo usa la biblioteca estándar. Las escrituras son atómicas y los cambios de
metadatos de fuentes son conservadores: un sufijo editorial conocido puede
corregir una atribución RSS, pero nunca se inventa un medio.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent
BASE_URL = "https://estrechoormuz.com/"
HOST = "estrechoormuz.com"
VALID_STATUS = {"ABIERTO", "CERRADO", "INCIERTO"}
VALID_CONFIDENCE = {"ALTA", "MEDIA", "BAJA"}
VALID_OPERATIONAL = {
    "OPEN_NORMAL",
    "OPEN_RESTRICTED",
    "CLOSED_CONFIRMED",
    "CLOSURE_DECLARED_UNCONFIRMED",
    "HIGH_RISK_UNCONFIRMED",
    "CONTRADICTORY",
    "NO_RECENT_CONFIRMATION",
    "MANUAL_OVERRIDE",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode if path.exists() else None
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def atomic_write_json(path: Path, payload: Any, *, compact: bool = False) -> None:
    if compact:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    else:
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    atomic_write_text(path, text)


def normalized_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalized_key(value: Any) -> str:
    text = normalized_space(value).casefold()
    text = re.sub(r"[.]+$", "", text)
    return text


@dataclass(frozen=True)
class Publisher:
    name: str
    tier: int
    official: bool


def load_publishers(path: Path | None = None) -> dict[str, Publisher]:
    path = path or ROOT / "source_aliases.json"
    payload = load_json(path, {}) or {}
    result: dict[str, Publisher] = {}
    for section, official in (("official_publishers", True), ("publishers", False)):
        entries = payload.get(section, {})
        if not isinstance(entries, dict):
            continue
        for alias, data in entries.items():
            if not isinstance(data, dict) or not data.get("name"):
                continue
            result[normalized_key(alias)] = Publisher(
                name=normalized_space(data["name"]),
                tier=max(1, min(5, int(data.get("tier", 1)))),
                official=official,
            )
    return result


TITLE_SUFFIX_RE = re.compile(r"\s+(?:-|–|—|\|)\s+([^|–—]{2,80})\s*$")


def publisher_from_title(title: str, aliases: dict[str, Publisher]) -> Publisher | None:
    match = TITLE_SUFFIX_RE.search(normalized_space(title))
    if not match:
        return None
    suffix = normalized_key(match.group(1))
    direct = aliases.get(suffix)
    if direct:
        return direct
    # Algunos agregadores añaden el dominio como sufijo.
    suffix = suffix.removeprefix("www.")
    return aliases.get(suffix)


def normalize_evidence_source(item: dict[str, Any], aliases: dict[str, Publisher]) -> tuple[bool, str | None]:
    """Corrige una atribución solo cuando hay evidencia editorial inequívoca.

    Devuelve (cambió, motivo). Si el título termina en un medio conocido y no
    coincide con source_name, prevalece el medio del título. La marca official
    solo puede ser verdadera para una fuente de la lista oficial.
    """
    title = normalized_space(item.get("title"))
    current_key = normalized_key(item.get("source_name"))
    current = aliases.get(current_key)
    suffix = publisher_from_title(title, aliases)
    chosen = suffix or current
    if chosen is None:
        if item.get("official") is True:
            item["official"] = False
            return True, "Se retiró official=true porque la fuente no pertenece a la lista oficial."
        return False, None

    before = (
        normalized_space(item.get("source_name")),
        item.get("tier"),
        bool(item.get("official")),
    )
    item["source_name"] = chosen.name
    try:
        current_tier = int(item.get("tier", chosen.tier))
    except (TypeError, ValueError):
        current_tier = chosen.tier
    # Nunca se eleva el tier por una corrección; sí se reduce si estaba inflado.
    item["tier"] = max(1, min(current_tier, chosen.tier))
    item["official"] = chosen.official
    after = (item["source_name"], item["tier"], item["official"])
    if before == after:
        return False, None
    if suffix and normalized_key(before[0]) != normalized_key(suffix.name):
        return True, f"El sufijo editorial identifica a {suffix.name}, no a {before[0] or 'la fuente declarada'}."
    return True, "Se normalizaron nombre, tier u oficialidad de la fuente."


def iter_evidence(payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    seen_ids: set[int] = set()
    for key in ("evidence", "evidence_archive"):
        items = payload.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict) and id(item) not in seen_ids:
                seen_ids.add(id(item))
                yield item
    confirmation = payload.get("last_valid_confirmation")
    if isinstance(confirmation, dict) and id(confirmation) not in seen_ids:
        yield confirmation


def evidence_key(item: dict[str, Any]) -> str:
    title = normalized_key(item.get("title"))
    source = normalized_key(item.get("source_name"))
    url = normalized_space(item.get("source_url")).split("?", 1)[0].casefold()
    return f"{source}|{title}" if title else url
