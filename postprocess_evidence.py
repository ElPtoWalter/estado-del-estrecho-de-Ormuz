#!/usr/bin/env python3
"""Postprocesa la salida del motor de Ormuz sin tocar su lógica de decisión.

- Conserva hasta 14 días de evidencias relevantes dentro de status.json.
- Si el último ciclo no publica evidencias nuevas, muestra las últimas disponibles
  claramente etiquetadas como anteriores.
- Sustituye el estado estático del HTML por un estado de carga neutral para evitar
  que la portada enseñe fugazmente una clasificación antigua al recargar.
- Inyecta evidence-ui.js en las portadas ES/EN.

Se ejecuta justo después de update_status.py y antes del commit del workflow.
"""
from __future__ import annotations

import json
import re
import subprocess
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
STATUS_FILE = ROOT / "status.json"
HTML_FILES = ((ROOT / "index.html", "es"), (ROOT / "en.html", "en"))
ARCHIVE_DAYS = 14
ARCHIVE_LIMIT = 60
DISPLAY_LIMIT = 6

ALLOWED_EVIDENCE_FIELDS = (
    "signal",
    "title",
    "source_name",
    "source_url",
    "published_at",
    "tier",
    "official",
)


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return deepcopy(default)


def previous_status_from_git() -> dict[str, Any]:
    """Lee el status.json del commit anterior, aún accesible como HEAD."""
    try:
        result = subprocess.run(
            ["git", "show", "HEAD:status.json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
        )
        payload = json.loads(result.stdout)
        return payload if isinstance(payload, dict) else {}
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return {}


def clean_item(item: Any, observed_at: str | None = None) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    title = str(item.get("title") or "").strip()
    source_name = str(item.get("source_name") or "").strip()
    source_url = str(item.get("source_url") or "").strip()
    if not title and not source_url:
        return None
    cleaned = {field: item.get(field) for field in ALLOWED_EVIDENCE_FIELDS}
    cleaned["title"] = title
    cleaned["source_name"] = source_name
    cleaned["source_url"] = source_url
    if observed_at:
        cleaned["observed_at"] = observed_at
    elif item.get("observed_at"):
        cleaned["observed_at"] = item.get("observed_at")
    return cleaned


def evidence_key(item: dict[str, Any]) -> str:
    title = re.sub(r"\s+", " ", str(item.get("title") or "").lower()).strip()
    source = re.sub(r"\s+", " ", str(item.get("source_name") or "").lower()).strip()
    if title:
        return f"{source}|{title}"
    return str(item.get("source_url") or "").split("?", 1)[0].lower()


def newest_first(item: dict[str, Any]) -> tuple[datetime, datetime]:
    minimum = datetime.min.replace(tzinfo=timezone.utc)
    return (
        parse_dt(item.get("published_at")) or minimum,
        parse_dt(item.get("observed_at")) or minimum,
    )


def merge_archive(
    current_items: list[dict[str, Any]],
    previous_payload: dict[str, Any],
    checked_at: str,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in current_items:
        cleaned = clean_item(item, checked_at)
        if cleaned:
            candidates.append(cleaned)

    previous_archive = previous_payload.get("evidence_archive")
    if not isinstance(previous_archive, list):
        previous_archive = previous_payload.get("evidence", [])
    for item in previous_archive if isinstance(previous_archive, list) else []:
        cleaned = clean_item(item)
        if cleaned:
            candidates.append(cleaned)

    checked_dt = parse_dt(checked_at) or datetime.now(timezone.utc)
    cutoff = checked_dt - timedelta(days=ARCHIVE_DAYS)
    unique: dict[str, dict[str, Any]] = {}
    for item in candidates:
        published = parse_dt(item.get("published_at"))
        observed = parse_dt(item.get("observed_at"))
        relevant_date = published or observed
        if relevant_date and relevant_date < cutoff:
            continue
        key = evidence_key(item)
        if not key:
            continue
        existing = unique.get(key)
        if existing is None or newest_first(item) > newest_first(existing):
            unique[key] = item

    return sorted(unique.values(), key=newest_first, reverse=True)[:ARCHIVE_LIMIT]


def latest_evidence_date(items: list[dict[str, Any]]) -> str | None:
    dates = [parse_dt(item.get("published_at")) for item in items]
    dates = [value for value in dates if value is not None]
    return iso_z(max(dates)) if dates else None


def build_context(mode: str, as_of: str | None, current_count: int) -> dict[str, Any]:
    if mode == "current":
        return {
            "mode": mode,
            "as_of": as_of,
            "current_cycle_count": current_count,
            "heading_es": "Evidencias de esta comprobación",
            "heading_en": "Evidence from this check",
            "description_es": "Señales publicables encontradas en el ciclo más reciente.",
            "description_en": "Publishable signals found during the latest verification cycle.",
        }
    if mode == "carried":
        return {
            "mode": mode,
            "as_of": as_of,
            "current_cycle_count": 0,
            "heading_es": "Últimas evidencias disponibles",
            "heading_en": "Latest available evidence",
            "description_es": (
                "La comprobación más reciente no aportó nuevas evidencias publicables. "
                "Estas señales proceden de ciclos anteriores y se muestran con su fecha real."
            ),
            "description_en": (
                "The latest check produced no new publishable evidence. These signals come "
                "from earlier cycles and retain their actual publication dates."
            ),
        }
    return {
        "mode": "none",
        "as_of": None,
        "current_cycle_count": 0,
        "heading_es": "Sin evidencias publicables",
        "heading_en": "No publishable evidence",
        "description_es": "El sistema no dispone todavía de señales verificables para mostrar.",
        "description_en": "The system does not currently have verifiable signals to display.",
    }


def update_status() -> dict[str, Any]:
    current = load_json(STATUS_FILE, {})
    if not isinstance(current, dict):
        raise RuntimeError("status.json no contiene un objeto JSON válido")

    previous = previous_status_from_git()
    checked_at = str(current.get("checked_at") or iso_z(datetime.now(timezone.utc)))
    raw_current = current.get("evidence")
    current_items = [item for item in raw_current if isinstance(item, dict)] if isinstance(raw_current, list) else []
    current_items = [cleaned for item in current_items if (cleaned := clean_item(item, checked_at))]
    archive = merge_archive(current_items, previous, checked_at)

    if current_items:
        display_items = current_items[:DISPLAY_LIMIT]
        mode = "current"
    else:
        previous_display = previous.get("evidence") if isinstance(previous.get("evidence"), list) else []
        carried = [cleaned for item in previous_display if (cleaned := clean_item(item))]
        display_items = (carried or archive)[:DISPLAY_LIMIT]
        mode = "carried" if display_items else "none"

    context = build_context(mode, latest_evidence_date(display_items), len(current_items))
    current["evidence"] = display_items
    current["evidence_context"] = context
    current["evidence_archive"] = archive
    diagnostics = current.get("diagnostics") if isinstance(current.get("diagnostics"), dict) else {}
    diagnostics.update(
        {
            "current_cycle_evidence": len(current_items),
            "evidence_display_mode": mode,
            "evidence_archive_size": len(archive),
            "evidence_archive_days": ARCHIVE_DAYS,
        }
    )
    current["diagnostics"] = diagnostics
    STATUS_FILE.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return current


LOADING_STYLE = """<style id=\"ormuz-v8-evidence-style\">
.status-hero.is-loading::after{background:var(--muted);opacity:.10}
.status-hero.is-loading .status-dot,.status-hero.is-loading .status-word{color:var(--muted)}
.status-hero.is-loading .status-word{font-size:clamp(2.2rem,6vw,4.8rem);letter-spacing:-.045em}
.evidence-context-badge{display:inline-flex;align-items:center;margin-top:8px;padding:6px 10px;border:1px solid var(--line-strong);border-radius:999px;color:var(--muted);font-size:.75rem;font-weight:750}
.evidence-section.is-carried-evidence{border-top:1px solid var(--line)}
</style>"""


def replace_id_element(html: str, element_id: str, replacement: str) -> str:
    pattern = rf"<(?P<tag>[a-zA-Z0-9]+)(?=[^>]*\bid=[\"']{re.escape(element_id)}[\"'])[^>]*>.*?</(?P=tag)>"
    return re.sub(pattern, replacement, html, count=1, flags=re.IGNORECASE | re.DOTALL)


def patch_html(path: Path, lang: str) -> None:
    try:
        html = path.read_text(encoding="utf-8")
    except OSError:
        return

    if "/evidence-ui.js" not in html:
        app_pattern = r"(<script\b[^>]*src=[\"']/app\.js[\"'][^>]*></script>)"
        html = re.sub(
            app_pattern,
            r'\1\n<script defer="" src="/evidence-ui.js"></script>',
            html,
            count=1,
            flags=re.IGNORECASE,
        )

    if "ormuz-v8-evidence-style" not in html:
        html = html.replace("</head>", LOADING_STYLE + "\n</head>", 1)

    if lang == "es":
        loading_label = "Consultando estado actual"
        loading_word = "CONSULTANDO…"
        loading_summary = "Recuperando la última comprobación y sus evidencias verificadas."
        loading_evidence = "Cargando evidencias verificadas…"
        heading = "Evidencias de esta comprobación"
        intro = "Comprobando si el último ciclo aportó señales nuevas."
    else:
        loading_label = "Checking current status"
        loading_word = "CHECKING…"
        loading_summary = "Retrieving the latest verification and its supporting evidence."
        loading_evidence = "Loading verified evidence…"
        heading = "Evidence from this check"
        intro = "Checking whether the latest cycle produced new signals."

    html = re.sub(
        r"<div(?=[^>]*\bid=[\"']statusHero[\"'])[^>]*>",
        '<div class="status-hero is-loading" id="statusHero">',
        html,
        count=1,
        flags=re.IGNORECASE,
    )
    html = replace_id_element(html, "operationalLabel", f'<span id="operationalLabel">{loading_label}</span>')
    html = replace_id_element(html, "statusWord", f'<div class="status-word is-long-status" id="statusWord">{loading_word}</div>')
    html = replace_id_element(html, "statusSummary", f'<p class="status-summary" id="statusSummary">{loading_summary}</p>')
    html = replace_id_element(html, "statusAdvisory", '<p class="status-advisory" hidden="" id="statusAdvisory"></p>')
    html = replace_id_element(html, "checkedAt", '<strong id="checkedAt">—</strong>')
    html = replace_id_element(html, "confidence", '<strong id="confidence">—</strong>')
    html = replace_id_element(html, "lastValidAt", '<strong id="lastValidAt">—</strong>')

    evidence_pattern = re.compile(
        r'(<div class=["\']evidence-section["\']>.*?<div class=["\']section-heading["\']><div>)'
        r'<h2[^>]*>.*?</h2>\s*<p[^>]*>.*?</p>',
        flags=re.IGNORECASE | re.DOTALL,
    )
    html = evidence_pattern.sub(
        rf'\1<h2 id="evidenceHeading">{heading}</h2><p id="evidenceIntro">{intro}</p>',
        html,
        count=1,
    )
    html = replace_id_element(
        html,
        "evidenceList",
        f'<div class="evidence-grid" id="evidenceList"><p class="empty-state">{loading_evidence}</p></div>',
    )

    path.write_text(html, encoding="utf-8")


def main() -> None:
    update_status()
    for path, lang in HTML_FILES:
        patch_html(path, lang)
    print("V8: evidencias conservadas y estado de carga neutral aplicado.")


if __name__ == "__main__":
    main()
