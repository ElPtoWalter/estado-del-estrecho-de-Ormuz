#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import py_compile
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GEN = ROOT / "generate_daily_journal.py"
V11 = ROOT / "install_v11.py"

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

BRIEF_ES = (
    "<!-- HOME_V11_BRIEF_START -->\n"
    '<section aria-labelledby="daily-brief-title" class="content-section home-brief-v11">'
    '<div><span class="section-kicker">Parte operativo diario</span>'
    '<h2 id="daily-brief-title">La situación esencial, bajo seguimiento continuo</h2>'
    '<p>Una síntesis del estado verificado, los cambios materiales, las evidencias destacadas y las señales que conviene vigilar.</p>'
    '<ul class="home-brief-points"><li>Estado operativo y nivel de confianza.</li>'
    '<li>Cambios frente al parte anterior.</li><li>Evidencias seleccionadas y próximas señales.</li></ul></div>'
    '<aside class="home-brief-action-v11"><strong>Seguimiento editorial continuo</strong>'
    '<p>La edición reúne el diagnóstico vigente, las evidencias seleccionadas y el contexto necesario para interpretar cada cambio.</p>'
    '<a class="button primary" href="/parte-diario.html">Abrir parte diario</a></aside></section>\n'
    "<!-- HOME_V11_BRIEF_END -->"
)
BRIEF_EN = (
    "<!-- HOME_V11_BRIEF_START -->\n"
    '<section aria-labelledby="daily-brief-title" class="content-section home-brief-v11">'
    '<div><span class="section-kicker">Daily operational brief</span>'
    '<h2 id="daily-brief-title">The essential situation, under continuous monitoring</h2>'
    '<p>A concise view of verified status, material changes, highlighted evidence and the signals worth watching.</p>'
    '<ul class="home-brief-points"><li>Operational status and confidence level.</li>'
    '<li>Changes from the previous brief.</li><li>Selected evidence and next signals.</li></ul></div>'
    '<aside class="home-brief-action-v11"><strong>Continuous editorial monitoring</strong>'
    '<p>The edition brings together the current assessment, selected evidence and the context needed to interpret each change.</p>'
    '<a class="button primary" href="/en-daily-brief.html">Open daily brief</a></aside></section>\n'
    "<!-- HOME_V11_BRIEF_END -->"
)

FOLLOW_ES = (
    '<aside class="data-access-card"><span class="section-kicker">Seguimiento público</span>'
    '<h2>Fuentes, metodología y suscripción</h2>'
    '<p>Consulta la metodología, revisa las fuentes empleadas o sigue las publicaciones mediante RSS.</p>'
    '<div class="data-actions"><a class="button" href="/metodologia.html">Metodología</a>'
    '<a class="button" href="/fuentes.html">Fuentes</a>'
    '<a class="button primary" href="/feed.xml">RSS</a></div></aside>'
)
FOLLOW_EN = (
    '<aside class="data-access-card"><span class="section-kicker">Public monitoring</span>'
    '<h2>Sources, methodology and subscription</h2>'
    '<p>Review the methodology, inspect the source framework or follow publications via RSS.</p>'
    '<div class="data-actions"><a class="button" href="/en-methodology.html">Methodology</a>'
    '<a class="button" href="/en-sources.html">Sources</a>'
    '<a class="button primary" href="/feed.xml">RSS</a></div></aside>'
)

FORBIDDEN = (
    "status.json", "history.json", "config.json", "operational-intelligence.json",
    "journal-state.json", "journal-health.json", "Redacción automatizada",
    "Automated newsroom", "El texto se genera automáticamente",
    "The text is generated automatically", "Puntuación de novedad", "Novelty score",
    "Crónica diaria automática", "Daily automated", "API pública", "Public API",
    "social-studio.html",
)

def save(path: Path, text: str) -> None:
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")

def patch_generator(text: str) -> str:
    pairs = (
        ('byline = "Redacción automatizada con control de consistencia" if lang == "es" else "Automated newsroom with consistency checks"',
         'byline = "Equipo editorial de Estrecho Ormuz" if lang == "es" else "Estrecho Ormuz Editorial Team"'),
        ('"Edición archivada por cambio material" if lang == "es" else "Archived because of material change"',
         '"Edición de hemeroteca" if lang == "es" else "Archive edition"'),
        ('"Edición viva · se actualiza una vez al día" if lang == "es" else "Live edition · updated once a day"',
         '"Edición diaria · seguimiento continuo" if lang == "es" else "Daily edition · continuous monitoring"'),
        ("{'Crónica diaria automática y trazable' if es else 'Daily automated, traceable briefing'}",
         "{'Crónica diaria · fuentes verificables' if es else 'Daily briefing · verifiable sources'}"),
        ("{'Trazabilidad' if lang == 'es' else 'Traceability'}",
         "{'Fuentes verificables' if lang == 'es' else 'Verifiable sources'}"),
        ('<span>{"Novedad" if es else "Novelty"}: {safe(item.get("material_score"))}</span>',
         '<span>{"Edición archivada" if es else "Archive edition"}</span>'),
        ("La web registra el cambio y conserva la edición previa para poder auditarlo.",
         "La hemeroteca conserva la edición previa para documentar la evolución."),
        ("The site records the change and preserves the previous edition for auditability.",
         "The archive preserves the previous edition to document the evolution."),
        ("el sistema mantiene separados el nivel de tráfico, las restricciones y el riesgo.",
         "la evaluación mantiene separados el nivel de tráfico, las restricciones y el riesgo."),
        ("El Diario de Ormuz · generador editorial automático V8",
         "El Diario de Ormuz · sistema editorial V8"),
    )
    for old, new in pairs:
        text = text.replace(old, new)

    reason = (
        '    reason_html = (\n'
        '        "<li>La edición incorpora novedades suficientes para formar parte de la hemeroteca.</li>"\n'
        '        if material_score_value >= MATERIAL_THRESHOLD and lang == "es"\n'
        '        else "<li>La edición diaria se mantiene actualizada sin crear una entrada histórica redundante.</li>"\n'
        '        if lang == "es"\n'
        '        else "<li>This edition contains sufficient new information to form part of the permanent archive.</li>"\n'
        '        if material_score_value >= MATERIAL_THRESHOLD\n'
        '        else "<li>The daily edition remains updated without creating a redundant historical entry.</li>"\n'
        '    )'
    )
    text = re.sub(
        r'^[ \t]*reason_html = ""\.join\(f"<li>\{safe\(item\)\}</li>" for item in material_reasons\)$',
        reason, text, count=1, flags=re.M
    )

    quality = (
        '    quality_note = (\n'
        '        "Esta edición forma parte de la hemeroteca porque incorpora novedades materiales suficientes."\n'
        '        if lang == "es" and material_score_value >= MATERIAL_THRESHOLD\n'
        '        else "La edición diaria se actualiza sin añadir una entrada redundante a la hemeroteca."\n'
        '        if lang == "es"\n'
        '        else "This edition forms part of the archive because it contains sufficient material developments."\n'
        '        if material_score_value >= MATERIAL_THRESHOLD\n'
        '        else "The daily edition is updated without adding a redundant entry to the archive."\n'
        '    )\n    description ='
    )
    text = re.sub(
        r'^[ \t]*quality_note = \(.*?^[ \t]*\)\n[ \t]*description =',
        quality, text, count=1, flags=re.M | re.S
    )

    block = (
        '<section class="journal-method-note">'
        "<h2>{'Criterios editoriales de esta edición' if lang == 'es' else 'Editorial standards for this edition'}</h2>"
        "<p>{safe(" + repr(METHOD_ES) + " if lang == 'es' else " + repr(METHOD_EN) + ")}</p>"
        "<p>{safe(quality_note)}</p>"
        "<details><summary>{'Criterio de hemeroteca' if lang == 'es' else 'Archive criteria'}</summary>"
        "<ul>{reason_html}</ul></details></section>"
    )
    text, n = re.subn(
        r'<section class="journal-method-note">.*?</details></section>',
        block, text, count=1, flags=re.S
    )
    if n == 0 and "Criterios editoriales de esta edición" not in text:
        raise RuntimeError("No se encontró journal-method-note")

    compile(text, str(GEN), "exec")
    return text

def patch_v11(text: str) -> str:
    text, n1 = re.subn(
        r"BRIEF_ES = r'''<!-- HOME_V11_BRIEF_START -->.*?<!-- HOME_V11_BRIEF_END -->'''",
        "BRIEF_ES = r'''" + BRIEF_ES + "'''", text, count=1, flags=re.S
    )
    text, n2 = re.subn(
        r"BRIEF_EN = r'''<!-- HOME_V11_BRIEF_START -->.*?<!-- HOME_V11_BRIEF_END -->'''",
        "BRIEF_EN = r'''" + BRIEF_EN + "'''", text, count=1, flags=re.S
    )
    if n1 == 0 and "Seguimiento editorial continuo" not in text:
        raise RuntimeError("No se encontró BRIEF_ES")
    if n2 == 0 and "Continuous editorial monitoring" not in text:
        raise RuntimeError("No se encontró BRIEF_EN")
    compile(text, str(V11), "exec")
    return text

def clean_jsonld(text: str) -> str:
    def repl(m):
        try:
            data = json.loads(m.group(2))
        except Exception:
            return m.group(0).replace(
                "https://estrechoormuz.com/status.json",
                "https://estrechoormuz.com/metodologia.html",
            )
        if isinstance(data, dict):
            main = data.get("mainEntity")
            if isinstance(main, dict) and str(main.get("url") or "").endswith(".json"):
                data.pop("mainEntity", None)
        return m.group(1) + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + m.group(3)

    return re.sub(
        r'(<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>)(.*?)(</script>)',
        repl, text, flags=re.I | re.S
    )

def clean_home(text: str, lang: str) -> str:
    es = lang == "es"
    text = re.sub(
        r'<!-- ORMUZ_GROWTH_V4_HOME_START -->.*?<!-- ORMUZ_GROWTH_V4_HOME_END -->',
        "", text, count=1, flags=re.I | re.S
    )
    text = re.sub(
        r'<aside class="data-access-card">.*?</aside>',
        FOLLOW_ES if es else FOLLOW_EN, text, count=1, flags=re.I | re.S
    )
    text = re.sub(
        r'<!-- HOME_V11_BRIEF_START -->.*?<!-- HOME_V11_BRIEF_END -->',
        BRIEF_ES if es else BRIEF_EN, text, count=1, flags=re.I | re.S
    )
    for old, new in (
        ("Actualización automática", "Seguimiento continuo"),
        ("Automatic update", "Continuous monitoring"),
        ("actualizada automáticamente", "bajo seguimiento continuo"),
        ("updated automatically", "under continuous monitoring"),
        ("indicador automático", "indicador operativo"),
        ("automatic indicator", "operational indicator"),
        ("Trazabilidad pública", "Fuentes y metodología"),
        ("Public traceability", "Sources and methodology"),
        ("Historial, API, RSS y metodología accesibles.", "Historial, fuentes, RSS y metodología accesibles."),
        ("History, API, RSS and methodology available.", "History, sources, RSS and methodology available."),
        ("diagnósticos del motor", "indicadores internos de verificación"),
        ("engine diagnostics", "internal verification indicators"),
        ("Transparencia técnica", "Verificación editorial"),
        ("Technical transparency", "Editorial verification"),
        ("Registro auditable", "Evolución documentada"),
        ("Auditable record", "Documented evolution"),
    ):
        text = text.replace(old, new)

    text = re.sub(
        r'<script\b(?![^>]*type=["\']application/ld\+json["\'])[^>]*>'
        r'(?:(?!</script>).)*(?:status|history|config|operational-intelligence)\.json'
        r'(?:(?!</script>).)*</script>',
        "", text, flags=re.I | re.S
    )
    text = re.sub(
        r'<a\b[^>]*href=["\'][^"\']*social-studio\.html[^"\']*["\'][^>]*>.*?</a>',
        "", text, flags=re.I | re.S
    )
    text = re.sub(
        r'\b(?:status|history|config|operational-intelligence|journal-state|journal-health)\.json\b',
        "datos internos del observatorio" if es else "internal observatory data",
        text, flags=re.I
    )
    return clean_jsonld(text)

def clean_diary(text: str, lang: str) -> str:
    es = lang == "es"
    block = (
        '<section class="journal-method-note"><h2>Criterios editoriales de esta edición</h2>'
        f'<p>{METHOD_ES}</p><p>La hemeroteca conserva las jornadas con novedades materiales; '
        'los días de continuidad actualizan la edición diaria sin generar páginas redundantes.</p></section>'
        if es else
        '<section class="journal-method-note"><h2>Editorial standards for this edition</h2>'
        f'<p>{METHOD_EN}</p><p>The archive preserves editions with material developments; '
        'continuity days update the daily edition without creating redundant pages.</p></section>'
    )
    text = re.sub(
        r'<section class="journal-method-note">.*?</section>',
        block, text, flags=re.I | re.S
    )
    for old, new in (
        ("Redacción automatizada con control de consistencia", "Equipo editorial de Estrecho Ormuz"),
        ("Automated newsroom with consistency checks", "Estrecho Ormuz Editorial Team"),
        ("Crónica diaria automática y trazable", "Crónica diaria · fuentes verificables"),
        ("Daily automated, traceable briefing", "Daily briefing · verifiable sources"),
        ("Trazabilidad", "Fuentes verificables"),
        ("Traceability", "Verifiable sources"),
    ):
        text = text.replace(old, new)
    text = re.sub(r'<span>Novedad:\s*[^<]+</span>', '<span>Edición archivada</span>', text, flags=re.I)
    text = re.sub(r'<span>Novelty:\s*[^<]+</span>', '<span>Archive edition</span>', text, flags=re.I)
    text = re.sub(
        r'\b(?:status|history|config|operational-intelligence)\.json\b',
        "datos internos del observatorio" if es else "internal observatory data",
        text, flags=re.I
    )
    return text

def clean_pages():
    for name, lang in (("index.html","es"),("en.html","en")):
        p = ROOT / name
        if p.exists():
            save(p, clean_home(p.read_text(encoding="utf-8"), lang))
    for name, lang in (("diario.html","es"),("en-diary.html","en")):
        p = ROOT / name
        if p.exists():
            save(p, clean_diary(p.read_text(encoding="utf-8"), lang))
    for dirname, lang in (("diario","es"),("diary","en")):
        d = ROOT / dirname
        if d.exists():
            for p in d.rglob("*.html"):
                save(p, clean_diary(p.read_text(encoding="utf-8"), lang))

def audit():
    targets = []
    for name in ("index.html","en.html","diario.html","en-diary.html"):
        p = ROOT / name
        if p.exists():
            targets.append(p)
    for dirname in ("diario","diary"):
        d = ROOT / dirname
        if d.exists():
            targets += list(d.rglob("*.html"))
    errors = []
    for p in targets:
        body = p.read_text(encoding="utf-8", errors="ignore")
        for token in FORBIDDEN:
            if token in body:
                errors.append(f"{p.relative_to(ROOT)}: {token}")
    if errors:
        raise RuntimeError("Auditoría V9.3 fallida: " + " | ".join(errors))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean-only", action="store_true")
    args = ap.parse_args()

    if not args.clean_only:
        if GEN.exists():
            save(GEN, patch_generator(GEN.read_text(encoding="utf-8")))
            py_compile.compile(str(GEN), doraise=True)
        if V11.exists():
            save(V11, patch_v11(V11.read_text(encoding="utf-8")))
            py_compile.compile(str(V11), doraise=True)

    clean_pages()
    audit()
    print("Professional Surface V9.3 OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
