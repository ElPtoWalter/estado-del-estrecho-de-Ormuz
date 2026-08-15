#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
MADRID = ZoneInfo("Europe/Madrid")

GEN = ROOT / "generate_daily_journal.py"
INDEX_ES = ROOT / "index.html"
INDEX_EN = ROOT / "en.html"
INSTALL_V11 = ROOT / "install_v11.py"
PUBLIC_BUILDER = ROOT / "build_public_site.py"

BRIEF_ES = r'''<!-- HOME_V11_BRIEF_START -->
<section aria-labelledby="daily-brief-title" class="content-section home-brief-v11">
  <div>
    <span class="section-kicker">Parte operativo diario</span>
    <h2 id="daily-brief-title">La situación esencial, bajo seguimiento continuo</h2>
    <p>Una síntesis del estado verificado, los cambios materiales, las evidencias destacadas y las señales que conviene vigilar, sin convertir cada titular en una alerta.</p>
    <ul class="home-brief-points">
      <li>Estado operativo y nivel de confianza.</li>
      <li>Cambios frente al parte anterior.</li>
      <li>Evidencias seleccionadas y próximas señales.</li>
    </ul>
  </div>
  <aside class="home-brief-action-v11">
    <strong>Seguimiento editorial continuo</strong>
    <p>La edición reúne el diagnóstico vigente, las evidencias seleccionadas y el contexto necesario para interpretar cada cambio.</p>
    <a class="button primary" href="/parte-diario.html">Abrir parte diario</a>
  </aside>
</section>
<!-- HOME_V11_BRIEF_END -->'''

BRIEF_EN = r'''<!-- HOME_V11_BRIEF_START -->
<section aria-labelledby="daily-brief-title" class="content-section home-brief-v11">
  <div>
    <span class="section-kicker">Daily operational brief</span>
    <h2 id="daily-brief-title">The essential situation, under continuous monitoring</h2>
    <p>A concise view of verified status, material changes, highlighted evidence and the signals worth watching, without turning every headline into an alert.</p>
    <ul class="home-brief-points">
      <li>Operational status and confidence level.</li>
      <li>Changes from the previous brief.</li>
      <li>Selected evidence and next signals.</li>
    </ul>
  </div>
  <aside class="home-brief-action-v11">
    <strong>Continuous editorial monitoring</strong>
    <p>The edition brings together the current assessment, selected evidence and the context needed to interpret each change.</p>
    <a class="button primary" href="/en-daily-brief.html">Open daily brief</a>
  </aside>
</section>
<!-- HOME_V11_BRIEF_END -->'''

DATA_CARD_ES = '''<aside class="data-access-card"><span class="section-kicker">Seguimiento público</span><h2>Fuentes, metodología y suscripción</h2><p>Consulta la metodología, revisa las fuentes empleadas o sigue las publicaciones mediante RSS.</p><div class="data-actions"><a class="button" href="/metodologia.html">Metodología</a><a class="button" href="/fuentes.html">Fuentes</a><a class="button primary" href="/feed.xml">RSS</a></div></aside>'''

DATA_CARD_EN = '''<aside class="data-access-card"><span class="section-kicker">Public monitoring</span><h2>Sources, methodology and subscription</h2><p>Review the methodology, inspect the source framework or follow publications via RSS.</p><div class="data-actions"><a class="button" href="/en-methodology.html">Methodology</a><a class="button" href="/en-sources.html">Sources</a><a class="button primary" href="/feed.xml">RSS</a></div></aside>'''

FAQ_REPLACEMENTS = {
    "es": (
        (
            "El motor ejecuta comprobaciones automáticas periódicas. La hora exacta del último ciclo aparece en el panel principal.",
            "El observatorio mantiene un seguimiento continuo. La hora de la última comprobación aparece en el panel principal.",
        ),
        (
            "La API y el RSS son públicos para consulta razonable. Cita a Estrecho Ormuz y enlaza la metodología cuando reutilices la clasificación.",
            "Sí. Puedes citar las conclusiones públicas de Estrecho Ormuz, indicando la fuente y enlazando la metodología. El RSS está disponible para seguir nuevas publicaciones.",
        ),
    ),
    "en": (
        (
            "The engine runs periodic automated checks. The exact time of the latest cycle appears in the main panel.",
            "The observatory is continuously monitored. The time of the latest verification appears in the main panel.",
        ),
        (
            "The API and RSS are public for reasonable use. Credit Estrecho Ormuz and link to the methodology when reusing the classification.",
            "Yes. You may cite Estrecho Ormuz's public conclusions with attribution and a link to the methodology. RSS is available for following new publications.",
        ),
    ),
}

FOOTER_REPLACEMENTS = {
    "es": (
        ("Seguimiento automatizado y prudente del estado operativo del estrecho.", "Seguimiento editorial continuo y prudente del estado operativo del estrecho."),
        ("Código y metodología auditables", "Metodología pública · Fuentes verificables"),
        ("Sistema operativo", "Seguimiento activo"),
    ),
    "en": (
        ("Automated, cautious monitoring of the Strait’s operational status.", "Continuous, cautious editorial monitoring of the Strait’s operational status."),
        ("Auditable code and methodology", "Public methodology · Verifiable sources"),
        ("System operational", "Monitoring active"),
    ),
}

BANNED_PUBLIC = (
    "El motor ejecuta comprobaciones automáticas periódicas",
    "The engine runs periodic automated checks",
    "La API y el RSS son públicos",
    "The API and RSS are public",
    "Crónica diaria automática",
    "Daily automated",
)

def read(path: Path) -> str:
    if not path.exists():
        raise RuntimeError(f"Falta el archivo requerido: {path.name}")
    return path.read_text(encoding="utf-8")

def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")

def patch_generator(text: str) -> str:
    text = re.sub(
        r"No usa una API de IA de pago\. La redacción es determinista y se construye solo\n",
        "",
        text,
        count=1,
    )
    text = text.replace(
        '"author": {"@type": "Organization", "name": "Redacción de Estrecho Ormuz" if lang == "es" else "Estrecho Ormuz News Desk"},',
        '"author": {"@type": "Organization", "name": "Equipo editorial de Estrecho Ormuz" if lang == "es" else "Estrecho Ormuz Editorial Team", "url": BASE_URL + ("/sobre.html" if lang == "es" else "/en-about.html")},',
    )

    old_loop = re.compile(
        r'''(?P<indent>[ \t]+)for item, clause in interpretable\[:2\]:\n'''
        r'''(?P=indent)[ \t]+clauses\.append\(clause\)\n'''
        r'''(?P=indent)[ \t]+used_sources\.append\(item\.source\)''',
        re.M,
    )
    replacement = (
        r'''\g<indent>for item, clause in interpretable:
'''
        r'''\g<indent>    if clause in clauses:
'''
        r'''\g<indent>        continue
'''
        r'''\g<indent>    clauses.append(clause)
'''
        r'''\g<indent>    if item.source not in used_sources:
'''
        r'''\g<indent>        used_sources.append(item.source)
'''
        r'''\g<indent>    if len(clauses) >= 2:
'''
        r'''\g<indent>        break'''
    )
    text, count = old_loop.subn(replacement, text)
    if count not in {0, 2}:
        raise RuntimeError(f"Se esperaban 2 bucles de narrativa; encontrados/parcheados: {count}")
    if count == 0 and text.count("if clause in clauses:") < 2:
        raise RuntimeError("No se encontró la lógica de narrativa del Diario")

    compile(text, str(GEN), "exec")
    return text

def patch_home(text: str, lang: str) -> str:
    for old, new in FAQ_REPLACEMENTS[lang]:
        text = text.replace(old, new)
    for old, new in FOOTER_REPLACEMENTS[lang]:
        text = text.replace(old, new)

    text = re.sub(
        r'<a\b[^>]*href=["\']/?status\.json["\'][^>]*>.*?</a>',
        "",
        text,
        flags=re.I | re.S,
    )

    text, _ = re.subn(
        r'<aside class="data-access-card">.*?</aside>',
        DATA_CARD_ES if lang == "es" else DATA_CARD_EN,
        text,
        count=1,
        flags=re.I | re.S,
    )

    text = re.sub(
        r'<!-- HOME_V11_BRIEF_START -->.*?<!-- HOME_V11_BRIEF_END -->',
        BRIEF_ES if lang == "es" else BRIEF_EN,
        text,
        count=1,
        flags=re.I | re.S,
    )
    return text

def patch_install_v11(text: str) -> str:
    text, c_es = re.subn(
        r"BRIEF_ES = r'''<!-- HOME_V11_BRIEF_START -->.*?<!-- HOME_V11_BRIEF_END -->'''",
        "BRIEF_ES = r'''" + BRIEF_ES + "'''",
        text,
        count=1,
        flags=re.S,
    )
    text, c_en = re.subn(
        r"BRIEF_EN = r'''<!-- HOME_V11_BRIEF_START -->.*?<!-- HOME_V11_BRIEF_END -->'''",
        "BRIEF_EN = r'''" + BRIEF_EN + "'''",
        text,
        count=1,
        flags=re.S,
    )
    if c_es == 0 and "Seguimiento editorial continuo" not in text:
        raise RuntimeError("No se pudo actualizar BRIEF_ES de install_v11.py")
    if c_en == 0 and "Continuous editorial monitoring" not in text:
        raise RuntimeError("No se pudo actualizar BRIEF_EN de install_v11.py")

    compile(text, str(INSTALL_V11), "exec")
    return text

def patch_public_builder(text: str) -> str:
    additions = (
        '    ("El motor ejecuta comprobaciones automáticas periódicas. La hora exacta del último ciclo aparece en el panel principal.", '
        '"El observatorio mantiene un seguimiento continuo. La hora de la última comprobación aparece en el panel principal."),\n'
        '    ("The engine runs periodic automated checks. The exact time of the latest cycle appears in the main panel.", '
        '"The observatory is continuously monitored. The time of the latest verification appears in the main panel."),\n'
        '    ("La API y el RSS son públicos para consulta razonable. Cita a Estrecho Ormuz y enlaza la metodología cuando reutilices la clasificación.", '
        '"Sí. Puedes citar las conclusiones públicas de Estrecho Ormuz, indicando la fuente y enlazando la metodología. El RSS está disponible para seguir nuevas publicaciones."),\n'
        '    ("The API and RSS are public for reasonable use. Credit Estrecho Ormuz and link to the methodology when reusing the classification.", '
        '"Yes. You may cite Estrecho Ormuz\\\'s public conclusions with attribution and a link to the methodology. RSS is available for following new publications."),\n'
    )
    if "El observatorio mantiene un seguimiento continuo. La hora de la última comprobación" not in text:
        anchor = '    ("Developer data", "Editorial documentation"),\n'
        if anchor not in text:
            raise RuntimeError("No se encontró PRO_LANGUAGE en build_public_site.py")
        text = text.replace(anchor, anchor + additions, 1)
    compile(text, str(PUBLIC_BUILDER), "exec")
    return text

def audit_source() -> None:
    errors: list[str] = []
    for path in (INDEX_ES, INDEX_EN):
        body = read(path)
        for token in BANNED_PUBLIC:
            if token.lower() in body.lower():
                errors.append(f"{path.name}: {token}")
        if "status.json" in body.lower():
            errors.append(f"{path.name}: todavía contiene status.json")

    gen = read(GEN)
    if "for item, clause in interpretable[:2]:" in gen:
        errors.append("generate_daily_journal.py: deduplicación antigua")
    if gen.count("if clause in clauses:") < 2:
        errors.append("generate_daily_journal.py: faltan los dos filtros de cláusulas duplicadas")

    v11 = read(INSTALL_V11)
    for token in (
        "La situación esencial, actualizada automáticamente",
        "The essential situation, updated automatically",
        "La página se regenera desde <code>status.json</code>",
        "The page is regenerated from <code>status.json</code>",
    ):
        if token in v11:
            errors.append(f"install_v11.py: {token}")

    if errors:
        raise RuntimeError(" | ".join(errors))

def audit_diary_after_generation() -> None:
    for filename, lang in (("diario.html", "es"), ("en-diary.html", "en")):
        path = ROOT / filename
        body = read(path)

        if lang == "es":
            dup = re.search(
                r"En conjunto,\s*(?P<x>[^.;<]+);\s*además,\s*(?P=x)(?:[.<])",
                body,
                re.I,
            )
        else:
            dup = re.search(
                r"Taken together,\s*(?P<x>[^.;<]+);\s*in addition,\s*(?P=x)(?:[.<])",
                body,
                re.I,
            )
        if dup:
            raise RuntimeError(f"{filename}: frase interpretativa duplicada")

        today = datetime.now(MADRID).date().isoformat()
        if f'datetime="{today}"' not in body:
            raise RuntimeError(f"{filename}: la edición no corresponde a {today}")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-diary", action="store_true")
    args = parser.parse_args()

    if args.audit_diary:
        audit_diary_after_generation()
        print("Diario: fecha actual y narrativa sin duplicados.")
        return 0

    write(GEN, patch_generator(read(GEN)))
    write(INDEX_ES, patch_home(read(INDEX_ES), "es"))
    write(INDEX_EN, patch_home(read(INDEX_EN), "en"))
    write(INSTALL_V11, patch_install_v11(read(INSTALL_V11)))
    write(PUBLIC_BUILDER, patch_public_builder(read(PUBLIC_BUILDER)))

    audit_source()
    print("AdSense readiness patch aplicado.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
