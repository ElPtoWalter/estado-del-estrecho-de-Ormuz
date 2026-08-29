#!/usr/bin/env python3
"""Prerender editorial fallbacks for Estrecho Ormuz."""
from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def clean(value: Any, fallback: str = "—") -> str:
    text = str(value or "").strip()
    return text or fallback


def esc(value: Any, fallback: str = "—") -> str:
    return html.escape(clean(value, fallback), quote=True)


def format_date(value: Any, lang: str) -> str:
    text = clean(value, "")
    if not text:
        return "Sin confirmación válida" if lang == "es" else "No valid confirmation"
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return (
            dt.strftime("%d/%m/%Y %H:%M UTC")
            if lang == "es"
            else dt.strftime("%Y-%m-%d %H:%M UTC")
        )
    except ValueError:
        return text


def replace_content(document: str, element_id: str, content: str) -> str:
    opening = re.compile(
        rf'<(?P<tag>[a-zA-Z0-9]+)\b[^>]*\bid=["\']{re.escape(element_id)}["\'][^>]*>',
        re.I | re.S,
    )
    match = opening.search(document)
    if not match:
        return document

    tag = match.group("tag")
    token_re = re.compile(
        rf'<{re.escape(tag)}\b[^>]*>|</{re.escape(tag)}\s*>',
        re.I | re.S,
    )
    depth = 1
    for token in token_re.finditer(document, match.end()):
        raw = token.group(0)
        if raw.lower().startswith(f'</{tag.lower()}'):
            depth -= 1
            if depth == 0:
                return document[:match.end()] + content + document[token.start():]
        elif not raw.rstrip().endswith('/>'):
            depth += 1
    raise RuntimeError(f'No se encontró el cierre de <{tag}> para #{element_id}')


def remove_trailing_corruption(document: str, element_id: str) -> str:
    """Drop legacy fragments left after a formerly broken nested replacement."""
    opening = re.compile(
        rf'<(?P<tag>[a-zA-Z0-9]+)\b[^>]*\bid=["\']{re.escape(element_id)}["\'][^>]*>',
        re.I | re.S,
    )
    match = opening.search(document)
    if not match:
        return document
    tag = match.group("tag")
    token_re = re.compile(rf'<{re.escape(tag)}\b[^>]*>|</{re.escape(tag)}\s*>', re.I | re.S)
    depth = 1
    element_end = None
    for token in token_re.finditer(document, match.end()):
        if token.group(0).lower().startswith(f'</{tag.lower()}'):
            depth -= 1
            if depth == 0:
                element_end = token.end()
                break
        elif not token.group(0).rstrip().endswith('/>'):
            depth += 1
    if element_end is None:
        return document
    section_end = re.search(r'</section\s*>', document[element_end:], re.I)
    if not section_end:
        return document
    absolute_section_end = element_end + section_end.start()
    trailing = document[element_end:absolute_section_end]
    if '<article' not in trailing.lower():
        return document
    return document[:element_end] + document[absolute_section_end:]


def remove_loading_class(document: str, element_id: str) -> str:
    pattern = re.compile(
        rf'(<[^>]*\bid=["\']{re.escape(element_id)}["\'][^>]*\bclass=["\'])'
        rf'([^"\']*)(["\'][^>]*>)',
        re.I,
    )

    def repl(match: re.Match[str]) -> str:
        classes = " ".join(
            item
            for item in match.group(2).split()
            if item not in {"is-loading", "loading"}
        )
        return match.group(1) + classes + match.group(3)

    return pattern.sub(repl, document, count=1)


def hide_element(document: str, element_id: str) -> str:
    pattern = re.compile(
        rf'(<[^>]*\bid=["\']{re.escape(element_id)}["\'])([^>]*>)',
        re.I,
    )

    def repl(match: re.Match[str]) -> str:
        tail = match.group(2)
        if re.search(r'\bhidden(?:\s|=|>)', tail, re.I):
            return match.group(0)
        return match.group(1) + " hidden" + tail

    return pattern.sub(repl, document, count=1)


def signal_label(signal: Any, lang: str) -> str:
    key = clean(signal, "").upper()
    labels = {
        "RISK_RESTRICTION": ("Riesgo o restricción", "Risk or restriction"),
        "OPEN_OPERATIONAL": ("Tránsito operativo", "Operational transit"),
        "CLOSED_OPERATIONAL": ("Cierre operativo", "Operational closure"),
        "CLOSURE_DECLARED": ("Cierre declarado", "Closure declared"),
    }
    return labels.get(key, ("Evidencia", "Evidence"))[0 if lang == "es" else 1]


def render_evidence(items: list[dict[str, Any]], lang: str, limit: int = 4) -> str:
    cards: list[str] = []
    for item in items[:limit]:
        title = esc(
            item.get("title"),
            "Evidencia sin título" if lang == "es" else "Untitled evidence",
        )
        source = esc(item.get("source_name"), "Fuente" if lang == "es" else "Source")
        url = esc(item.get("source_url"), "#")
        date = esc(format_date(item.get("published_at"), lang))
        label = esc(signal_label(item.get("signal"), lang))
        cards.append(
            '<article class="evidence-card">'
            f'<div class="evidence-meta"><span>{label}</span><time>{date}</time></div>'
            f'<h3><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></h3>'
            f"<p>{source}</p>"
            "</article>"
        )
    if cards:
        return "".join(cards)
    return (
        '<p class="empty-state">No hay evidencias recientes publicables.</p>'
        if lang == "es"
        else '<p class="empty-state">No recent publishable evidence.</p>'
    )


def render_history(items: list[dict[str, Any]], lang: str, limit: int = 4) -> str:
    rows: list[str] = []
    for item in items[:limit]:
        label = item.get(
            "operational_label_es" if lang == "es" else "operational_label_en"
        )
        summary = item.get("summary_es" if lang == "es" else "summary_en")
        rows.append(
            '<article class="timeline-item">'
            f'<time>{esc(format_date(item.get("at"), lang))}</time>'
            f'<h3>{esc(label, clean(item.get("status")))}</h3>'
            f'<p>{esc(summary, "")}</p>'
            "</article>"
        )
    if rows:
        return "".join(rows)
    return (
        '<p class="empty-state">Todavía no hay cambios significativos archivados.</p>'
        if lang == "es"
        else '<p class="empty-state">No material changes have been archived yet.</p>'
    )


def prerender_home(root: Path, filename: str, lang: str) -> None:
    path = root / filename
    if not path.exists():
        return

    status = load_json(root / "status.json", {})
    history = load_json(root / "history.json", [])
    document = path.read_text(encoding="utf-8")

    operational = status.get(
        "operational_label_es" if lang == "es" else "operational_label_en"
    )
    status_word = status.get("status")
    if lang == "en" and status_word == "INCIERTO":
        status_word = "UNCERTAIN"
    summary = status.get("summary_es" if lang == "es" else "summary_en")
    confidence = clean(status.get("confidence"))
    if lang == "en":
        confidence = {
            "ALTA": "HIGH",
            "MEDIA": "MEDIUM",
            "BAJA": "LOW",
        }.get(confidence, confidence)

    document = remove_loading_class(document, "statusHero")
    document = replace_content(
        document,
        "operationalLabel",
        esc(operational, "Estado verificado" if lang == "es" else "Verified status"),
    )
    document = replace_content(
        document,
        "statusWord",
        esc(status_word, "INCIERTO" if lang == "es" else "UNCERTAIN"),
    )
    document = replace_content(
        document,
        "statusSummary",
        esc(summary, "Sin resumen disponible." if lang == "es" else "No summary available."),
    )
    document = replace_content(
        document,
        "checkedAt",
        esc(format_date(status.get("checked_at"), lang)),
    )
    document = replace_content(document, "confidence", esc(confidence))
    confirmation = status.get("last_valid_confirmation") or {}
    document = replace_content(
        document,
        "lastValidAt",
        esc(format_date(confirmation.get("at"), lang)),
    )
    document = replace_content(
        document,
        "evidenceList",
        render_evidence(status.get("evidence") or [], lang),
    )
    document = replace_content(
        document,
        "recentHistory",
        render_history(history if isinstance(history, list) else [], lang),
    )
    path.write_text(document, encoding="utf-8")


def list_items(values: Any) -> str:
    if not isinstance(values, list):
        return ""
    return "".join(f"<li>{esc(value)}</li>" for value in values)


def render_archive(root: Path, lang: str) -> str:
    archive = load_json(root / "daily-brief-archive.json", [])
    if not isinstance(archive, list):
        return ""
    cards: list[str] = []
    for item in archive[:4]:
        if not isinstance(item, dict):
            continue
        title = item.get(
            "operational_label_es" if lang == "es" else "operational_label_en"
        )
        summary = item.get("summary_es" if lang == "es" else "summary_en")
        cards.append(
            '<article class="archive-card">'
            f'<time>{esc(item.get("date") or item.get("generated_at"))}</time>'
            f'<h3>{esc(title, clean(item.get("status")))}</h3>'
            f'<p>{esc(summary, "")}</p>'
            "</article>"
        )
    return "".join(cards)


def prerender_daily(root: Path, filename: str, lang: str) -> None:
    path = root / filename
    if not path.exists():
        return

    brief = load_json(root / "daily-brief.json", {})
    status = load_json(root / "status.json", {})
    document = path.read_text(encoding="utf-8")
    document = remove_trailing_corruption(document, "briefEvidence")

    suffix = "es" if lang == "es" else "en"
    status_label = brief.get(f"status_label_{suffix}") or status.get("status")
    operational = brief.get(f"operational_label_{suffix}") or status.get(
        f"operational_label_{suffix}"
    )
    summary = brief.get(f"summary_{suffix}") or status.get(f"summary_{suffix}")
    change = brief.get(f"change_{suffix}")
    confidence = (
        (brief.get("confidence_label") or {}).get(suffix)
        or brief.get("confidence")
        or status.get("confidence")
    )

    document = hide_element(document, "briefLoading")
    document = replace_content(
        document,
        "briefDate",
        esc(brief.get("date") or brief.get("generated_at")),
    )
    document = replace_content(document, "briefStatusPill", esc(status_label))
    document = replace_content(document, "briefOperational", esc(operational))
    document = replace_content(document, "briefSummary", esc(summary))
    document = replace_content(document, "briefConfidence", esc(confidence))
    document = replace_content(
        document,
        "briefGenerated",
        esc(format_date(brief.get("generated_at"), lang)),
    )
    document = replace_content(
        document,
        "briefChange",
        esc(
            change,
            "Sin cambio material confirmado."
            if lang == "es"
            else "No material change confirmed.",
        ),
    )
    document = replace_content(
        document,
        "briefRisks",
        list_items(brief.get(f"risks_{suffix}")),
    )
    document = replace_content(
        document,
        "briefEvidence",
        render_evidence(brief.get("evidence") or [], lang, limit=5),
    )
    document = replace_content(
        document,
        "briefWatch",
        list_items(brief.get(f"watchlist_{suffix}")),
    )
    document = replace_content(document, "briefArchive", render_archive(root, lang))
    path.write_text(document, encoding="utf-8")


def prerender_widget(root: Path) -> None:
    status = load_json(root / "status.json", {})
    for filename, lang in (("widget.html", "es"), ("en-widget.html", "en")):
        path = root / filename
        if not path.exists():
            continue
        document = path.read_text(encoding="utf-8")
        label = status.get(
            "operational_label_es" if lang == "es" else "operational_label_en"
        )
        summary = status.get("summary_es" if lang == "es" else "summary_en")
        document = re.sub(
            r'(<[^>]*data-state[^>]*>).*?(</[^>]+>)',
            lambda match: match.group(1)
            + esc(label, clean(status.get("status")))
            + match.group(2),
            document,
            count=1,
            flags=re.I | re.S,
        )
        document = re.sub(
            r'(<[^>]*data-summary[^>]*>).*?(</[^>]+>)',
            lambda match: match.group(1) + esc(summary, "") + match.group(2),
            document,
            count=1,
            flags=re.I | re.S,
        )
        path.write_text(document, encoding="utf-8")


def prerender_all(root: Path | str | None = None) -> None:
    root_path = Path(root) if root else Path(__file__).resolve().parent
    prerender_home(root_path, "index.html", "es")
    prerender_home(root_path, "en.html", "en")
    prerender_daily(root_path, "parte-diario.html", "es")
    prerender_daily(root_path, "en-daily-brief.html", "en")
    prerender_widget(root_path)


if __name__ == "__main__":
    prerender_all()
