#!/usr/bin/env python3
from __future__ import annotations

import argparse
import py_compile
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GENERATOR = ROOT / "generate_daily_journal.py"
DIARY_WORKFLOW = ROOT / ".github" / "workflows" / "diario-ormuz.yml"

METHOD_ES = (
    "Esta edición ha sido preparada por el Equipo editorial de Estrecho Ormuz a partir de "
    "fuentes marítimas, energéticas y periodísticas contrastadas, junto con los datos propios "
    "del observatorio. La redacción distingue hechos operativos, declaraciones, interpretación "
    "y señales de mercado. Las fuentes utilizadas se enlazan para facilitar su comprobación."
)

METHOD_EN = (
    "This edition has been prepared by the Estrecho Ormuz Editorial Team using cross-checked "
    "maritime, energy and journalistic sources together with the observatory's own data. "
    "The editorial process distinguishes operational facts, statements, interpretation and "
    "market signals. Sources are linked so readers can verify the underlying information."
)

FORBIDDEN_PUBLIC = (
    "Redacción automatizada",
    "Automated newsroom",
    "El texto se genera automáticamente",
    "The text is generated automatically",
    "Puntuación de novedad",
    "Novelty score",
    "Cómo se ha escrito esta edición",
    "How this edition was produced",
    "Crónica diaria automática",
    "Daily automated",
    "status.json",
)

def sub_once(source: str, pattern: str, replacement: str, label: str, flags: int = 0) -> str:
    updated, count = re.subn(pattern, replacement, source, count=1, flags=flags)
    if count == 0:
        if replacement in source:
            return source
        raise RuntimeError(f"No se encontró el bloque esperado: {label}")
    return updated

def patch_generator(source: str) -> str:
    source = source.replace(
        "El Diario de Ormuz · generador editorial automático V8",
        "El Diario de Ormuz · sistema editorial V8",
    )
    source = source.replace(
        "No usa una API de IA de pago. La redacción es determinista y se construye solo",
        "La edición se construye",
    )

    source = sub_once(
        source,
        r'^[ \t]*byline = "Redacción automatizada con control de consistencia" if lang == "es" else "Automated newsroom with consistency checks"$',
        '    byline = "Equipo editorial de Estrecho Ormuz" if lang == "es" else "Estrecho Ormuz Editorial Team"',
        "byline",
        re.M,
    )

    source = source.replace(
        '"Edición archivada por cambio material" if lang == "es" else "Archived because of material change"',
        '"Edición de hemeroteca" if lang == "es" else "Archive edition"',
    )
    source = source.replace(
        '"Edición viva · se actualiza una vez al día" if lang == "es" else "Live edition · updated once a day"',
        '"Edición diaria · seguimiento continuo" if lang == "es" else "Daily edition · continuous monitoring"',
    )

    source = source.replace(
        '"author": {"@type": "Organization", "name": "Redacción de Estrecho Ormuz" if lang == "es" else "Estrecho Ormuz News Desk"},',
        '"author": {"@type": "Organization", "name": "Equipo editorial de Estrecho Ormuz" if lang == "es" else "Estrecho Ormuz Editorial Team", "url": BASE_URL + ("/sobre.html" if lang == "es" else "/en-about.html")},',
    )

    reason_replacement = (
        '    reason_html = (\\n'
        '        "<li>La edición incorpora novedades suficientes para formar parte de la hemeroteca.</li>"\\n'
        '        if material_score_value >= MATERIAL_THRESHOLD and lang == "es"\\n'
        '        else "<li>La edición diaria se mantiene actualizada sin crear una entrada histórica redundante.</li>"\\n'
        '        if lang == "es"\\n'
        '        else "<li>This edition contains sufficient new information to form part of the permanent archive.</li>"\\n'
        '        if material_score_value >= MATERIAL_THRESHOLD\\n'
        '        else "<li>The daily edition remains updated without creating a redundant historical entry.</li>"\\n'
        '    )'
    ).replace("\\n", "\n")

    source = sub_once(
        source,
        r'^[ \t]*reason_html = ""\.join\(f"<li>\{safe\(item\)\}</li>" for item in material_reasons\)$',
        reason_replacement,
        "reason_html",
        re.M,
    )

    quality_replacement = (
        '    quality_note = (\\n'
        '        "Esta edición forma parte de la hemeroteca porque incorpora novedades materiales suficientes."\\n'
        '        if lang == "es" and material_score_value >= MATERIAL_THRESHOLD\\n'
        '        else "La edición diaria se actualiza sin añadir una entrada redundante a la hemeroteca."\\n'
        '        if lang == "es"\\n'
        '        else "This edition forms part of the archive because it contains sufficient material developments."\\n'
        '        if material_score_value >= MATERIAL_THRESHOLD\\n'
        '        else "The daily edition is updated without adding a redundant entry to the archive."\\n'
        '    )\\n'
        '    description ='
    ).replace("\\n", "\n")

    source = sub_once(
        source,
        r'^[ \t]*quality_note = \(.*?^[ \t]*\)\n[ \t]*description =',
        quality_replacement,
        "quality_note",
        re.M | re.S,
    )

    if "PUBLIC_METHOD_ES =" not in source:
        constants = (
            "PUBLIC_METHOD_ES = " + repr(METHOD_ES) + "\n"
            "PUBLIC_METHOD_EN = " + repr(METHOD_EN) + "\n\n"
        )
        source = source.replace("def render_page(\n", constants + "def render_page(\n", 1)

    method_replacement = (
        '<section class="journal-method-note">'
        "<h2>{'Criterios editoriales de esta edición' if lang == 'es' else 'Editorial standards for this edition'}</h2>"
        "<p>{safe(PUBLIC_METHOD_ES if lang == 'es' else PUBLIC_METHOD_EN)}</p>"
        "<p>{safe(quality_note)}</p>"
        "<details><summary>{'Criterio de hemeroteca' if lang == 'es' else 'Archive criteria'}</summary>"
        "<ul>{reason_html}</ul></details></section>"
    )

    source = sub_once(
        source,
        r'<section class="journal-method-note">.*?</details></section>',
        method_replacement,
        "journal-method-note",
        re.S,
    )

    source = source.replace(
        "{'Trazabilidad' if lang == 'es' else 'Traceability'}",
        "{'Fuentes verificables' if lang == 'es' else 'Verifiable sources'}",
    )

    source = source.replace(
        '<span>{"Novedad" if es else "Novelty"}: {safe(item.get("material_score"))}</span>',
        '<span>{"Edición archivada" if es else "Archive edition"}</span>',
    )

    source = source.replace(
        "{'Crónica diaria automática y trazable' if es else 'Daily automated, traceable briefing'}",
        "{'Crónica diaria · fuentes verificables' if es else 'Daily briefing · verifiable sources'}",
    )

    source = source.replace(
        "La web registra el cambio y conserva la edición previa para poder auditarlo.",
        "La hemeroteca conserva la edición previa para documentar la evolución.",
    )
    source = source.replace(
        "The site records the change and preserves the previous edition for auditability.",
        "The archive preserves the previous edition to document the evolution.",
    )
    source = source.replace(
        "el sistema mantiene separados el nivel de tráfico, las restricciones y el riesgo.",
        "la evaluación mantiene separados el nivel de tráfico, las restricciones y el riesgo.",
    )

    source = source.replace(
        "for item, clause in interpretable[:2]:\n                clauses.append(clause)\n                used_sources.append(item.source)",
        "for item, clause in interpretable[:2]:\n"
        "                if clause not in clauses:\n"
        "                    clauses.append(clause)\n"
        "                if item.source not in used_sources:\n"
        "                    used_sources.append(item.source)",
    )

    compile(source, str(GENERATOR), "exec")
    return source

def clean_rendered_html(body: str, lang: str) -> str:
    if lang == "es":
        replacement = (
            '<section class="journal-method-note">'
            '<h2>Criterios editoriales de esta edición</h2>'
            f'<p>{METHOD_ES}</p>'
            '<p>La hemeroteca conserva las jornadas con novedades materiales; '
            'los días de continuidad actualizan la edición diaria sin generar páginas redundantes.</p>'
            '</section>'
        )
    else:
        replacement = (
            '<section class="journal-method-note">'
            '<h2>Editorial standards for this edition</h2>'
            f'<p>{METHOD_EN}</p>'
            '<p>The archive preserves editions with material developments; '
            'continuity days update the daily edition without creating redundant pages.</p>'
            '</section>'
        )

    body = re.sub(
        r'<section class="journal-method-note">.*?</section>',
        replacement,
        body,
        flags=re.I | re.S,
    )

    replacements = (
        ("Redacción automatizada con control de consistencia", "Equipo editorial de Estrecho Ormuz"),
        ("Automated newsroom with consistency checks", "Estrecho Ormuz Editorial Team"),
        ("Edición archivada por cambio material", "Edición de hemeroteca"),
        ("Archived because of material change", "Archive edition"),
        ("Edición viva · se actualiza una vez al día", "Edición diaria · seguimiento continuo"),
        ("Live edition · updated once a day", "Daily edition · continuous monitoring"),
        ("Crónica diaria automática y trazable", "Crónica diaria · fuentes verificables"),
        ("Daily automated, traceable briefing", "Daily briefing · verifiable sources"),
        ("Trazabilidad", "Fuentes verificables"),
        ("Traceability", "Verifiable sources"),
    )
    for old, new in replacements:
        body = body.replace(old, new)

    body = re.sub(r'<span>Novedad:\s*[^<]+</span>', '<span>Edición archivada</span>', body, flags=re.I)
    body = re.sub(r'<span>Novelty:\s*[^<]+</span>', '<span>Archive edition</span>', body, flags=re.I)
    return body

def clean_public_pages() -> int:
    targets = []
    for path, lang in ((ROOT / "diario.html", "es"), (ROOT / "en-diary.html", "en")):
        if path.exists():
            targets.append((path, lang))

    for dirname, lang in (("diario", "es"), ("diary", "en")):
        directory = ROOT / dirname
        if directory.exists():
            for path in directory.rglob("*.html"):
                targets.append((path, lang))

    for path, lang in ((ROOT / "index.html", "es"), (ROOT / "en.html", "en")):
        if path.exists():
            targets.append((path, lang))

    changed = 0
    for path, lang in targets:
        old = path.read_text(encoding="utf-8")
        new = clean_rendered_html(old, lang)
        if new != old:
            path.write_text(new, encoding="utf-8")
            changed += 1
    return changed

def patch_workflow() -> None:
    if not DIARY_WORKFLOW.exists():
        return
    body = DIARY_WORKFLOW.read_text(encoding="utf-8")
    body = body.replace("Redactar edición de la mañana", "Preparar edición de la mañana")
    body = body.replace("Validar redacción automática", "Validar edición diaria")
    DIARY_WORKFLOW.write_text(body, encoding="utf-8")

def audit() -> None:
    targets = []
    for path in (ROOT / "diario.html", ROOT / "en-diary.html"):
        if path.exists():
            targets.append(path)

    for dirname in ("diario", "diary"):
        directory = ROOT / dirname
        if directory.exists():
            targets.extend(directory.rglob("*.html"))

    errors = []
    for path in targets:
        body = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_PUBLIC:
            if token in body:
                errors.append(f"{path.relative_to(ROOT)}: {token}")

    if errors:
        raise RuntimeError("Auditoría editorial fallida: " + " | ".join(errors))

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean-only", action="store_true")
    args = parser.parse_args()

    if not args.clean_only:
        if not GENERATOR.exists():
            raise RuntimeError("generate_daily_journal.py no existe")
        source = GENERATOR.read_text(encoding="utf-8")
        updated = patch_generator(source)
        GENERATOR.write_text(updated, encoding="utf-8")
        py_compile.compile(str(GENERATOR), doraise=True)
        patch_workflow()

    changed = clean_public_pages()
    audit()

    print("Professional Editorial V9.2 OK")
    print(f"Páginas públicas limpiadas: {changed}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
