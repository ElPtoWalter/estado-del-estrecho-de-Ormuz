#!/usr/bin/env python3
from __future__ import annotations

import py_compile
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GENERATOR = ROOT / "generate_daily_journal.py"
WORKFLOW = ROOT / ".github" / "workflows" / "diario-ormuz.yml"

OLD_METHOD_ES = (
    "El texto se genera automáticamente a partir de status.json, Operational Intelligence "
    "cuando está disponible y noticias recientes de fuentes seleccionadas. Las reglas separan "
    "hechos operativos de opinión, preguntas y declaraciones políticas.\n"
    "No se inventan citas ni se atribuyen hechos que no puedan sostenerse con los datos enlazados."
)
NEW_METHOD_ES = (
    "Esta edición ha sido elaborada por el Equipo editorial de Estrecho Ormuz a partir de "
    "fuentes marítimas, energéticas y periodísticas contrastadas, junto con los datos propios "
    "del observatorio. La redacción distingue hechos operativos, declaraciones, interpretación "
    "y señales de mercado. Las fuentes utilizadas se enlazan para facilitar su comprobación."
)

OLD_METHOD_EN = (
    "The text is generated automatically from status.json, Operational Intelligence when "
    "available, and recent news from selected sources. Rules separate operational facts from "
    "opinion, questions and political statements.\n"
    "Quotes are not invented and claims are not attributed beyond what the linked data can support."
)
NEW_METHOD_EN = (
    "This edition has been prepared by the Estrecho Ormuz Editorial Team using cross-checked "
    "maritime, energy and journalistic sources together with the observatory's own data. "
    "The editorial process distinguishes operational facts, statements, interpretation and "
    "market signals. Sources are linked so readers can verify the underlying information."
)

PUBLIC_REPLACEMENTS = (
    ("Redacción automatizada con control de consistencia", "Equipo editorial de Estrecho Ormuz"),
    ("Automated newsroom with consistency checks", "Estrecho Ormuz Editorial Team"),
    ("Edición viva · se actualiza una vez al día", "Edición diaria · seguimiento continuo"),
    ("Live edition · updated once a day", "Daily edition · continuous monitoring"),
    ("Edición archivada por cambio material", "Edición de hemeroteca"),
    ("Archived because of material change", "Archive edition"),
    ("Cómo se ha escrito esta edición", "Criterios editoriales de esta edición"),
    ("How this edition was produced", "Editorial standards for this edition"),
    (OLD_METHOD_ES, NEW_METHOD_ES),
    (OLD_METHOD_EN, NEW_METHOD_EN),
    ("Trazabilidad", "Fuentes"),
    ("Traceability", "Sources"),
    ("Crónica diaria automática y trazable", "Crónica diaria · fuentes verificables"),
    ("Daily automated, traceable briefing", "Daily briefing · verifiable sources"),
    ("Puntuación de novedad", "Criterio editorial de archivo"),
    ("Novelty score", "Editorial archive criterion"),
    ("Por qué se archivó o no esta edición", "Criterio de hemeroteca"),
    ("Why this edition was or was not archived", "Archive criteria"),
)

def replace_all(text: str) -> str:
    for old, new in PUBLIC_REPLACEMENTS:
        text = text.replace(old, new)
    return text

def patch_generator(source: str) -> str:
    source = replace_all(source)

    source = source.replace(
        '"""El Diario de Ormuz · generador editorial automático V8.',
        '"""El Diario de Ormuz · sistema editorial V8.',
    )
    source = source.replace(
        "No usa una API de IA de pago. La redacción es determinista y se construye solo\n"
        "con hechos estructurados y titulares enlazados. Los titulares interrogativos,\n"
        "de opinión o puramente especulativos nunca se convierten en hechos.\n",
        "La edición se construye con hechos estructurados y titulares enlazados. Los titulares\n"
        "interrogativos, de opinión o puramente especulativos nunca se convierten en hechos.\n",
    )

    source = source.replace(
        'reason_html = "".join(f"<li>{safe(item)}</li>" for item in material_reasons)',
        """reason_html = (
        "<li>La edición incorpora novedades suficientes para formar parte de la hemeroteca.</li>"
        if material_score_value >= MATERIAL_THRESHOLD and lang == "es"
        else "<li>La edición diaria se mantiene actualizada sin crear una entrada histórica redundante.</li>"
        if lang == "es"
        else "<li>This edition contains sufficient new information to form part of the permanent archive.</li>"
        if material_score_value >= MATERIAL_THRESHOLD
        else "<li>The daily edition remains updated without creating a redundant historical entry.</li>"
    )""",
    )

    old_quality = """quality_note = (
        "Esta edición alcanza el umbral para archivo permanente."
        if lang == "es" and material_score_value >= MATERIAL_THRESHOLD
        else "Esta edición no crea una nueva URL histórica: se actualiza la portada del diario para evitar contenido repetitivo."
        if lang == "es"
        else "This edition reaches the threshold for permanent archiving."
        if material_score_value >= MATERIAL_THRESHOLD
        else "This edition does not create a new historical URL: the live diary is updated instead, avoiding repetitive content."
    )"""
    new_quality = """quality_note = (
        "Esta edición forma parte de la hemeroteca porque incorpora novedades materiales suficientes."
        if lang == "es" and material_score_value >= MATERIAL_THRESHOLD
        else "La edición diaria se actualiza sin añadir una entrada redundante a la hemeroteca."
        if lang == "es"
        else "This edition forms part of the archive because it contains sufficient material developments."
        if material_score_value >= MATERIAL_THRESHOLD
        else "The daily edition is updated without adding a redundant entry to the archive."
    )"""
    source = source.replace(old_quality, new_quality)

    old_details = """<details><summary>{'Criterio de hemeroteca' if lang == 'es' else 'Archive criteria'}</summary><p>{'Criterio editorial de archivo' if lang == 'es' else 'Editorial archive criterion'}: <strong>{material_score_value}</strong> / {MATERIAL_THRESHOLD}.</p><ul>{reason_html or '<li>Continuidad sin novedad material suficiente.</li>'}</ul></details>"""
    new_details = """<details><summary>{'Criterio de hemeroteca' if lang == 'es' else 'Archive criteria'}</summary><ul>{reason_html}</ul></details>"""
    source = source.replace(old_details, new_details)

    source = source.replace(
        '<span>{"Novedad" if es else "Novelty"}: {safe(item.get("material_score"))}</span>',
        '<span>{"Edición archivada" if es else "Archive edition"}</span>',
    )

    old_clause = """clauses.append(clause)
                if item.source not in used_sources:
                    used_sources.append(item.source)"""
    new_clause = """if clause not in clauses:
                    clauses.append(clause)
                if item.source not in used_sources:
                    used_sources.append(item.source)"""
    source = source.replace(old_clause, new_clause)

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

    compile(source, str(GENERATOR), "exec")
    return source

def clean_html(text: str) -> str:
    text = replace_all(text)

    text = re.sub(
        r"El texto se genera automáticamente a partir de status\.json, Operational Intelligence "
        r"cuando está disponible y noticias recientes de fuentes seleccionadas\. Las reglas separan "
        r"hechos operativos de opinión, preguntas y declaraciones políticas\.\s*"
        r"No se inventan citas ni se atribuyen hechos que no puedan sostenerse con los datos enlazados\.",
        NEW_METHOD_ES,
        text,
        flags=re.I,
    )
    text = re.sub(
        r"The text is generated automatically from status\.json, Operational Intelligence when "
        r"available, and recent news from selected sources\. Rules separate operational facts from "
        r"opinion, questions and political statements\.\s*"
        r"Quotes are not invented and claims are not attributed beyond what the linked data can support\.",
        NEW_METHOD_EN,
        text,
        flags=re.I,
    )

    text = re.sub(
        r"<p>(?:Criterio editorial de archivo|Editorial archive criterion):\s*"
        r"<strong>\d+</strong>\s*/\s*\d+\.</p>",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"<span>Novedad:\s*[^<]+</span>",
        "<span>Edición archivada</span>",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"<span>Novelty:\s*[^<]+</span>",
        "<span>Archive edition</span>",
        text,
        flags=re.I,
    )

    text = re.sub(r"\bstatus\.json\b", "datos propios del observatorio", text, flags=re.I)
    text = re.sub(r"\bOperational Intelligence\b", "metodología operativa", text, flags=re.I)
    return text

def patch_existing_pages() -> int:
    changed = 0
    targets = []
    for rel in ("diario.html", "en-diary.html"):
        path = ROOT / rel
        if path.exists():
            targets.append(path)

    for dirname in ("diario", "diary"):
        directory = ROOT / dirname
        if directory.exists():
            targets.extend(directory.rglob("*.html"))

    for path in targets:
        old = path.read_text(encoding="utf-8")
        new = clean_html(old)
        if old != new:
            path.write_text(new, encoding="utf-8")
            changed += 1
    return changed

def patch_homepages() -> int:
    changed = 0
    for name in ("index.html", "en.html"):
        path = ROOT / name
        if not path.exists():
            continue
        old = path.read_text(encoding="utf-8")
        new = replace_all(old)
        if old != new:
            path.write_text(new, encoding="utf-8")
            changed += 1
    return changed

def patch_workflow() -> None:
    if not WORKFLOW.exists():
        return
    text = WORKFLOW.read_text(encoding="utf-8")
    text = text.replace("Validar redacción automática", "Validar edición diaria")
    text = text.replace("Redactar edición de la mañana", "Preparar edición de la mañana")
    WORKFLOW.write_text(text, encoding="utf-8")

def audit_public_pages() -> None:
    forbidden = (
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
    errors = []
    for path in (ROOT / "diario.html", ROOT / "en-diary.html"):
        if not path.exists():
            continue
        body = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in body:
                errors.append(f"{path.name}: {token}")
    if errors:
        raise SystemExit("Editorial audit failed: " + " | ".join(errors))

def main() -> int:
    if not GENERATOR.exists():
        raise SystemExit("generate_daily_journal.py not found")

    original = GENERATOR.read_text(encoding="utf-8")
    updated = patch_generator(original)
    GENERATOR.write_text(updated, encoding="utf-8")
    py_compile.compile(str(GENERATOR), doraise=True)

    patch_workflow()
    changed_pages = patch_existing_pages()
    changed_pages += patch_homepages()
    audit_public_pages()

    print("Professional Editorial V9.1 applied successfully.")
    print(f"Existing public pages updated: {changed_pages}")
    print("Future Diario editions will use the institutional editorial presentation.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
