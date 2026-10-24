"""Prepare a sealed, safe public candidate; never used by the Pages deploy workflow.

--write prepares static candidate sources. --check verifies exact regeneration.
--build checks and overlays the candidate onto a COPY of the normal public build.
All resulting pages remain noindex. No review approval or release switch is created.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import html
import importlib.util
import io
import json
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET

import build_public_site as public
import build_sitemap as sitemap
from check_public_links import check as check_links
from publication_quality import apply_policy

ROOT = Path(__file__).resolve().parent
DRAFT = ROOT / 'drafts/historiales-20261024'
SOURCE = DRAFT / 'public-candidate'
PREVIEW = DRAFT / 'preview'
MANIFEST = DRAFT / 'public-candidate-manifest.json'
ASSETS = 'assets/research/monitor-history-20261024'
ARTICLES = {'es': 'historiales-monitor-ormuz.html', 'en': 'en-monitor-archives-hormuz.html'}
METHODS = {'es': 'metodo-historiales-monitor-20261024.html', 'en': 'en-monitor-archive-method-20261024.html'}
ARCHIVE = 'archivo-monitor-20261024.html'
CSV_MAP = {'monitor-observations.csv': 'records.csv', 'model-summary.csv': 'models.csv',
           'v7-confidence.csv': 'confidence.csv', 'comparison-windows.csv': 'windows.csv',
           'plot-records.csv': 'plot.csv'}
spec = importlib.util.spec_from_file_location('frozen_history_candidate', DRAFT / 'reproduce.py')
research = importlib.util.module_from_spec(spec)
spec.loader.exec_module(research)


def sha(data):
    return hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest()


def nav(lang, alternate):
    es = lang == 'es'
    links = [('index.html' if es else 'en.html', 'Inicio' if es else 'Home'),
             ('monitor-ormuz.html' if es else 'en-hormuz-monitor.html', 'Monitor'),
             ('analisis.html' if es else 'en-analysis.html', 'Análisis' if es else 'Analysis'),
             ('historial.html' if es else 'en-history.html', 'Historial' if es else 'History'),
             (METHODS[lang], 'Método de este análisis' if es else 'This analysis: method')]
    # Monitor's public route is the homepage status section, not an invented slug.
    links[1] = ('index.html#estado-actual' if es else 'en.html#current-status', 'Monitor')
    body = ''.join(f'<a href="/{url}">{label}</a>' for url, label in links)
    return (f'<header class="masthead"><a class="brand" href="/{links[0][0]}">ESTRECHO ORMUZ'
            f'<small>{"Observatorio marítimo y energético" if es else "Maritime and energy observatory"}</small></a>'
            f'<a class="language language-link" href="/{alternate}" lang="{"en" if es else "es"}" '
            f'hreflang="{"en" if es else "es"}">{"Read in English ↗" if es else "Leer en español ↗"}</a></header>'
            f'<nav class="observatory-nav" aria-label="{"Navegación del observatorio" if es else "Observatory navigation"}">{body}</nav>')


def disclosure(lang):
    return ('Candidato para autorización · Preparación con asistencia de IA · Publicación no autorizada · Anuncios desactivados'
            if lang == 'es' else 'Candidate awaiting authorisation · Prepared with AI assistance · Publication not authorised · Advertising disabled')


def footer(lang):
    links = [('politica-editorial.html', 'Política editorial'), ('contacto.html', 'Contacto'),
             ('aviso-legal.html', 'Aviso legal'), ('privacidad.html', 'Privacidad')] if lang == 'es' else [
             ('en-editorial-policy.html', 'Editorial policy'), ('en-contact.html', 'Contact'),
             ('en-legal.html', 'Legal notice'), ('en-privacy.html', 'Privacy')]
    return '<footer><p>ESTRECHO ORMUZ · ' + disclosure(lang) + '</p><nav aria-label="' + (
        'Información institucional' if lang == 'es' else 'Institutional information') + '">' + ' · '.join(
        f'<a href="/{url}">{label}</a>' for url, label in links) + '</nav></footer>'


def head(lang, slug, title, pair=None):
    description = ('Método y archivo del análisis histórico: fuentes congeladas, decisiones de dos modelos y cálculos reproducibles.' if lang == 'es' else
                   'Method and archive for the historical analysis: frozen sources, decisions from two models and reproducible calculations.')
    alternates = ''.join(f'<link rel="alternate" hreflang="{key}" href="{public.DOMAIN}/{value}">'
                         for key, value in ({**pair, 'x-default': pair['es']}.items() if pair else []))
    return (f'<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(title)} | Estrecho Ormuz</title>'
            f'<meta name="description" content="{description}">'
            '<meta name="robots" content="noindex,follow"><meta name="content-kind" content="original-draft">'
            '<meta name="publisher-ads" content="disabled"><meta name="referrer" content="strict-origin-when-cross-origin">'
            f'<link rel="canonical" href="{public.DOMAIN}/{slug}">{alternates}'
            f'<link rel="stylesheet" href="/{ASSETS}/history-editorial.css"></head><body>'
            f'<a class="skip" href="#content">{"Saltar al contenido" if lang == "es" else "Skip to content"}</a>')


def sources_table(lang):
    sources = json.loads((DRAFT/'sources.json').read_text(encoding='utf-8'))['sources']
    rows = ''.join(f'<tr><th scope="row">{label}</th><td><code>{s["commit"]}</code></td><td><code>{s["sha256_lf"]}</code></td></tr>'
                   for label, s in zip(('Motor anterior / Earlier engine', 'V7', 'CSV original / Original CSV'), sources))
    return ('<div class="table-wrap" role="region" tabindex="0" aria-label="Identificadores de fuentes / Source identifiers">'
            '<table><caption>SHA-256: UTF-8, CRLF → LF; sin reformatear / no reformatting.</caption>'
            '<thead><tr><th scope="col">Fuente / Source</th><th scope="col">Commit</th><th scope="col">SHA-256 LF</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')


def method(lang):
    es = lang == 'es'
    title = 'Cómo leer y reproducir este historial' if es else 'How to read and reproduce this archive'
    intro = ('Esta metodología acompaña al análisis histórico, no al estado en directo. Los 103 registros son decisiones guardadas por dos modelos; no son posiciones de buques ni una serie periódica de tráfico.' if es else
             'This method accompanies the historical analysis, not the live status. The 103 records are stored decisions from two models, not vessel positions or a periodic traffic series.')
    steps = [
        'Descargar records.csv. Sus seis columnas son modelo, fecha y hora, estado, confianza y dos indicadores booleanos de disponibilidad de mediciones; no contienen las mediciones.',
        'Interpretar fechas con zona horaria y convertir a UTC. Separar legacy y v7; comprobar que modelo/fecha no se repite. No añadir filas ni rellenar días ausentes.',
        'Contar filas por modelo, estado y confianza. Resultados: legacy 54 (51 INCIERTO, 3 ABIERTO); V7 49 (47 MEDIA, 2 ALTA), con la misma etiqueta operativa V7 en las 49 filas.',
        'Filtrar v7 para cada ventana: inicio incluido y final excluido. Contar filas y fechas UTC distintas. No contar varias filas del mismo día como varios días.',
        'Primera ventana [2026-09-10T00:00:00Z, 2026-10-01T00:00:00Z): 11 filas, 8 días, 11 MEDIA. Segunda [2026-10-01T00:00:00Z, 2026-10-22T00:00:00Z): 10 filas, 7 días, 10 MEDIA. Cada ventana dura 21 días.',
        'Ordenar por modelo y fecha. Para cada modelo/día, asignar posiciones 1, 2, 3… a las filas consecutivas. plot.csv conserva la hora exacta, el día y la posición; la altura solo separa símbolos.',
        'Dibujar paneles separados por modelo: eje X = día UTC, eje Y = posición de apilado; símbolo por fila, sin líneas ni interpolación. Distinguir estado en legacy y confianza en V7. El gráfico de barras representa los recuentos 47 y 2.',
        'Contrastar las tablas con models.csv, confidence.csv y windows.csv. Los dos ALTA son del 07/08 a las 12:21:33 UTC y del 02/09 a las 11:41:03 UTC, fuera de las dos ventanas. No se calculan barcos, caídas del tráfico, horas de cierre ni precisión.'
    ] if es else [
        'Download records.csv. Its six columns hold model, timestamp, classification, confidence and two boolean indicators of measurement availability; they do not contain measurements.',
        'Parse timezone-aware dates and convert to UTC. Separate legacy and v7; verify model/timestamp uniqueness. Do not add rows or fill missing days.',
        'Count rows by model, classification and confidence. Results: legacy 54 (51 INCIERTO, 3 ABIERTO); V7 49 (47 MEDIA, 2 ALTA), with the same V7 operational label in all 49 rows.',
        'Filter v7 for each window: inclusive start and exclusive end. Count rows and distinct UTC dates. Several rows on one day count as one date.',
        'First window [2026-09-10T00:00:00Z, 2026-10-01T00:00:00Z): 11 rows, 8 days, 11 MEDIA. Second [2026-10-01T00:00:00Z, 2026-10-22T00:00:00Z): 10 rows, 7 days, 10 MEDIA. Each window spans 21 days.',
        'Sort by model and timestamp. Within each model/day assign consecutive rows positions 1, 2, 3… . plot.csv preserves exact time, day and position; height only separates symbols.',
        'Draw separate model panels: X = UTC day, Y = stack position; one symbol per row, no lines or interpolation. Encode classification for legacy and confidence for V7. The bar chart represents the counts 47 and 2.',
        'Check tables against models.csv, confidence.csv and windows.csv. The two ALTA records are 7 August at 12:21:33 UTC and 2 September at 11:41:03 UTC, outside both windows. Do not calculate vessel counts, traffic declines, closure hours or accuracy.'
    ]
    provenance = ('Los dos archivos técnicos originales quedaron congelados en el commit indicado; sus huellas identifican las entradas utilizadas. La instantánea pública es una proyección de campos seleccionados, no una copia completa de los archivos técnicos. Se conserva exactamente el CSV original. El motor anterior abarca 12/07–18/10/2026 y V7 07/08–21/10/2026. Consulta de integridad registrada el 24/10/2026: tres fuentes HTTP 200 y huellas coincidentes. Esta comprobación no verifica el tráfico marítimo ni actualiza el pasado.' if es else
                  'The two original technical archives were frozen at the commit shown; their hashes identify the inputs used. The public snapshot projects selected fields and is not a complete copy of technical archives. The original CSV is preserved exactly. The earlier engine spans 12 July–18 October 2026 and V7 7 August–21 October 2026. Integrity check recorded on 24 October 2026: three HTTP 200 sources with matching hashes. This does not verify maritime traffic or update past observations.')
    overlap = ('Los SVG propios conservan 54 y 49 centros únicos. La separación mínima medida es 8,55849 unidades SVG, mayor que el diámetro conservador de 8. Formas y color distinguen categorías; el gráfico de confianza dispone de composición móvil. La cronología mantiene ancho mínimo y desplazamiento para no comprimir puntos y fechas.' if es else
               'The original SVGs retain 54 and 49 unique centres. Minimum measured separation is 8.55849 SVG units, greater than the conservative diameter of 8. Shapes and colour distinguish categories; confidence has a mobile layout. The timeline retains minimum width and scrolling to avoid compressing points and dates.')
    limits = ('Los días sin fila no prueban ausencia de barcos ni fallos de servicio. No hay ratio numérico de tráfico ni instantánea de recuento marítimo en los campos V7 examinados. MEDIA y ALTA son etiquetas del modelo, no probabilidades calibradas. Los cambios de método y la retención impiden tratar los dos archivos como una única serie marítima.' if es else
              'Days without a row prove neither an absence of ships nor service outages. The examined V7 fields contain no numeric traffic ratio or maritime-count snapshot. MEDIA and ALTA are model labels, not calibrated probabilities. Method changes and retention prevent treating both archives as one maritime series.')
    downloads = ''.join(f'<li><a href="/{ASSETS}/{name}" download>{name}</a></li>' for name in CSV_MAP.values())
    graphs = ''.join(f'<li><a href="/{ASSETS}/history-{kind}-{lang}.svg" download>SVG: {kind}</a></li>' for kind in ('timeline', 'confidence', 'confidence-mobile'))
    return (head(lang, METHODS[lang], title, METHODS) + nav(lang, METHODS['en' if es else 'es']) +
            f'<main id="content"><p class="draft-bar" data-draft-disclosure>{disclosure(lang)}</p><h1>{title}</h1>'
            f'<div class="prose"><p>{intro}</p><p><a href="/{ARTICLES[lang]}">{"Volver al análisis" if es else "Back to the analysis"}</a></p>'
            f'<h2 id="recuento">{"Reproducción paso a paso" if es else "Step-by-step reproduction"}</h2><ol>' + ''.join(f'<li>{s}</li>' for s in steps) + '</ol></div>'
            f'<h2 id="fuentes">{"Fuentes e integridad" if es else "Sources and integrity"}</h2><div class="prose"><p>{provenance}</p></div>' + sources_table(lang) +
            f'<p><a href="/{ARCHIVE}#legacy">{"Instantánea congelada: motor anterior" if es else "Frozen snapshot: earlier engine"}</a> · '
            f'<a href="/{ARCHIVE}#v7">V7</a></p><div class="prose"><h2>{"Datos y gráficos propios" if es else "Original data and charts"}</h2><p>{overlap}</p>'
            f'<ul>{downloads}{graphs}</ul><h2>{"Límites y reutilización" if es else "Limitations and reuse"}</h2><p>{limits}</p>'
            '<p>' + ('Metadatos de decisiones y gráficos elaborados por el proyecto, pendientes de autorización de publicación por el titular. Las fuentes, la versión y la atribución se documentan aquí. El archivo excluye posiciones AIS y textos de medios.' if es else
                      'Decision metadata and charts prepared by the project, awaiting publication authorisation from the owner. Sources, version and attribution are documented here. The archive excludes AIS positions and media article bodies.') +
            '</p></div></main>' + footer(lang) + '</body></html>\n')


def archive():
    rows = research.read_rows()
    archive_nav = nav('es', METHODS['en']).replace('class="language language-link"', 'class="language"')
    archive_nav = archive_nav.replace('Read in English ↗', 'Method in English ↗')
    tables = ''
    for model, title in (('legacy', 'Motor anterior / Earlier engine'), ('v7', 'V7')):
        body = ''.join('<tr>' + ''.join(f'<td>{html.escape(row[k])}</td>' for k in research.FIELDS) + '</tr>' for row in rows if row['model'] == model)
        headers = ''.join(f'<th scope="col">{key}</th>' for key in research.FIELDS)
        tables += (f'<h2 id="{model}">{title}</h2><div class="table-wrap" role="region" tabindex="0" aria-label="{title}">'
                   f'<table><caption>UTC · {54 if model == "legacy" else 49} registros / records · 2026</caption><thead><tr>{headers}</tr></thead><tbody>{body}</tbody></table></div>')
    return (head('es', ARCHIVE, 'Archivo congelado / Frozen archive · 24 octubre 2026') + archive_nav +
            f'<main id="content"><p class="draft-bar" data-draft-disclosure>{disclosure("es")}</p><h1>Archivo congelado / Frozen archive</h1>'
            '<p>103 registros originales de dos modelos, analizados por separado. Períodos: legacy 12/07–18/10/2026; V7 07/08–21/10/2026, UTC. No son observaciones de buques.</p>'
            '<p lang="en">103 original records from two models, analysed separately. Periods: legacy 12 July–18 October 2026; V7 7 August–21 October 2026, UTC. These are not vessel observations.</p>'
            f'<p><a href="/{METHODS["es"]}">Método y fuentes ES</a> · <a href="/{METHODS["en"]}" lang="en">Method and sources EN</a></p>'
            f'<p id="csv"><a href="/{ASSETS}/records.csv" download>CSV original congelado / Original frozen CSV</a></p>'
            '<p>Los dos indicadores True/False solo indican disponibilidad del campo de medición; no miden tráfico. <span lang="en">The two True/False indicators describe measurement-field availability; they do not measure traffic.</span></p>'
            f'<p>SHA-256 LF: <code>{research.EXPECTED_INPUT_SHA256_LF}</code>.</p>' + tables +
            '</main>' + footer('es') + '</body></html>\n')


def article(lang):
    es = lang == 'es'
    text = (DRAFT/ARTICLES[lang]).read_text(encoding='utf-8')
    text = re.sub(r'<header class="masthead">.*?</header>', lambda m: nav(lang, ARTICLES['en' if es else 'es']), text, count=1, flags=re.S)
    text = re.sub(r'(<p class="draft-bar" data-draft-disclosure>).*?</p>', lambda m: m[1] + disclosure(lang) + '</p>', text, count=1, flags=re.S)
    text = text.replace('href="history-editorial.css"', f'href="/{ASSETS}/history-editorial.css"')
    text = re.sub(r'(src|srcset)="(history-[^"]+\.svg)"', lambda m: f'{m[1]}="/{ASSETS}/{m[2]}"', text)
    for before, after in CSV_MAP.items():
        text = text.replace(f'href="{before}"', f'href="/{ASSETS}/{after}"')
    text = text.replace('href="analysis-summary.json"', f'href="/{METHODS[lang]}#recuento"')
    marker = '<div class="prose"><h2>' + ('Fuentes congeladas y reproducción' if es else 'Frozen sources and reproduction') + '</h2>'
    start = text.index(marker)
    end = text.index('</article>', start)
    section = (f'<div class="prose"><h2>{"Fuentes congeladas y reproducción" if es else "Frozen sources and reproduction"}</h2><p>' +
               ('La instantánea pública conserva las 103 filas originales y las fuentes identificadas por versión y huella. Los dos modelos se leen por separado. La metodología explica la selección de campos y permite reproducir tablas y gráficos con las descargas públicas.' if es else
                'The public snapshot preserves all 103 original rows and identifies sources by version and hash. The two models remain separate. The method explains field selection and lets readers reproduce tables and charts using public downloads.') +
               f'</p><ol class="source-list"><li><a href="/{ARCHIVE}#legacy">{"Motor anterior: 54 registros congelados" if es else "Earlier engine: 54 frozen records"}</a></li>'
               f'<li><a href="/{ARCHIVE}#v7">V7: 49 {"registros congelados" if es else "frozen records"}</a></li>'
               f'<li><a href="/{METHODS[lang]}#fuentes">{"Fuentes, versiones y huellas de integridad" if es else "Sources, versions and integrity hashes"}</a></li></ol>'
               f'<p><a href="/{METHODS[lang]}">{"Método completo y reproducción" if es else "Full method and reproduction"}</a> · '
               f'<a href="/{ASSETS}/records.csv" download>{"Descargar el CSV original" if es else "Download the original CSV"}</a></p></div>'
               '<aside class="limits" data-related-guides><h2>' + ('Para ampliar el contexto' if es else 'Further context') + '</h2><ul>' +
               ''.join(f'<li><a href="/{url}">{label}</a></li>' for url, label in ([
                   ('que-significa-cierre-estrecho-ormuz.html', 'Qué significa un cierre de Ormuz'),
                   ('como-comprobar-trafico-maritimo-operativo-ormuz.html', 'Cómo comprobar el tránsito marítimo'),
                   ('metodologia.html', 'Metodología general del observatorio')] if es else [
                   ('en-what-does-closing-strait-of-hormuz-mean.html', 'What a Hormuz closure means'),
                   ('en-how-to-verify-operational-maritime-traffic-hormuz.html', 'How to verify maritime passage'),
                   ('en-methodology.html', 'The observatory’s general methodology')])) + '</ul></aside>'
               '<p class="review-note">' + ('El contenido anterior fue revisado favorablemente por el propietario. Esta adaptación pública y sus recursos siguen pendientes de autorización final. No se registra una aprobación editorial ni se autoriza la publicación con esta entrega.' if es else
                'The owner reviewed the preceding content favourably. This public adaptation and its resources still await final authorisation. This delivery does not record an editorial approval or authorise publication.') + '</p>\n')
    text = text[:start] + section + text[end:]
    return re.sub(r'<footer>.*?</footer>', lambda m: footer(lang), text, count=1, flags=re.S)


def candidate_files():
    research.read_rows()  # pinned input hash, schema and uniqueness
    for name, text in research.outputs().items():
        if (DRAFT/name).read_text(encoding='utf-8') != text:
            raise ValueError(f'Derived input changed: {name}')
    result = {ARTICLES[lang]: article(lang).encode('utf-8') for lang in ARTICLES}
    result.update({METHODS[lang]: method(lang).encode('utf-8') for lang in METHODS})
    result[ARCHIVE] = archive().encode('utf-8')
    for source, dest in CSV_MAP.items():
        result[f'{ASSETS}/{dest}'] = (DRAFT/source).read_bytes().replace(b'\r\n', b'\n')
    for path in DRAFT.glob('history-*.svg'):
        result[f'{ASSETS}/{path.name}'] = path.read_bytes().replace(b'\r\n', b'\n')
    css = (DRAFT/'history-editorial.css').read_text(encoding='utf-8') + '\n' + (
        '.brand{color:var(--text);text-decoration:none}.observatory-nav{max-width:1160px;margin:auto;padding:14px 28px;display:flex;flex-wrap:wrap;gap:10px 24px;border-bottom:1px solid var(--line);font-size:14px}'
        '.observatory-nav a{padding:5px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}li{margin-bottom:.6em}'
        '@media(max-width:760px){.observatory-nav{padding:12px 20px;gap:6px 18px}.brand{letter-spacing:.1em}}\n')
    result[f'{ASSETS}/history-editorial.css'] = css.encode('utf-8')
    return result


def manifest(files):
    return {'kind': 'exact_public_candidate_not_authorized', 'publication_authorized': False,
            'human_editorial_approval': None, 'reviewer': None, 'approved_at': None,
            'owner_feedback': 'Favourable review of preceding articles and charts; final public candidate not authorized',
            'review_reference': 'https://github.com/ElPtoWalter/estado-del-estrecho-de-Ormuz/pull/22#pullrequestreview-5638634753',
            'index': False, 'advertising': False, 'pages_workflow_input': '_site (candidate excluded)',
            'sha256_lf': {name: sha(data) for name, data in sorted(files.items())}}


def verify():
    expected = candidate_files()
    audit_payload(expected)
    actual = {p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob('*') if p.is_file()}
    if actual != set(expected):
        raise ValueError(f'Candidate file list differs: {actual ^ set(expected)}')
    for name, data in expected.items():
        if sha((SOURCE/name).read_bytes()) != sha(data):
            raise ValueError(f'Candidate differs from reproducible sources: {name}')
    if json.loads(MANIFEST.read_text(encoding='utf-8')) != manifest(expected):
        raise ValueError('Candidate manifest differs; no silent resealing')
    return expected


def audit_payload(files):
    """Inspect actual intended public bytes, including SVG and CSV, before rendering."""
    for name, data in files.items():
        path = Path(name)
        if '..' in path.parts or path.is_absolute() or path.suffix not in {'.html', '.csv', '.css', '.svg'}:
            raise ValueError(f'Unsafe candidate destination: {name}')
        text = data.decode('utf-8')
        if path.suffix == '.csv':
            if name not in public.HISTORY_PUBLIC_CSV:
                raise ValueError(f'CSV route not approved for candidate: {name}')
            for row in csv.reader(io.StringIO(text)):
                if any(cell.lstrip().startswith(('=', '+', '-', '@')) for cell in row):
                    raise ValueError(f'CSV formula-like cell: {name}')
        elif path.suffix == '.svg':
            svg = ET.fromstring(text)
            for element in svg.iter():
                if element.tag.rsplit('}', 1)[-1].lower() in {'script', 'foreignobject', 'image'}:
                    raise ValueError(f'Active or remote SVG element: {name}')
                if any(key.lower().startswith('on') or
                       (key.rsplit('}', 1)[-1] == 'href' and not value.startswith('#'))
                       for key, value in element.attrib.items()):
                    raise ValueError(f'Active or external SVG attribute: {name}')
        elif path.suffix == '.html':
            if re.search(r'\.json\b|\.py\b|github\.com|raw\.githubusercontent|<script|<iframe|<form|mailto:|pub-\d+', text, re.I):
                raise ValueError(f'Internal reference or unexpected active element: {name}')
            if 'noindex,follow' not in text or 'publisher-ads" content="disabled' not in text:
                raise ValueError(f'Missing draft/ads boundary: {name}')


def integrate(root):
    for lang, pages in {'es': ('index.html', 'analisis.html', 'historial.html'),
                        'en': ('en.html', 'en-analysis.html', 'en-history.html')}.items():
        title = 'El historial de Ormuz cuenta decisiones, no barcos' if lang == 'es' else 'The Hormuz archive records decisions, not ships'
        note = 'Candidato editorial pendiente de autorización' if lang == 'es' else 'Editorial candidate awaiting authorisation'
        block = f'<aside class="content-section prose-card" data-history-candidate><h2><a href="/{ARTICLES[lang]}">{title}</a></h2><p>{note} · 54 + 49 {"registros, modelos separados" if lang == "es" else "records, separate models"}.</p></aside>'
        for name in pages:
            path = root/name
            text = path.read_text(encoding='utf-8')
            if '</main>' not in text:
                raise ValueError(f'Missing navigation insertion point: {name}')
            path.write_text(text.replace('</main>', block+'</main>', 1), encoding='utf-8', newline='\n')


def build_preview(base=None, out=None):
    files = verify()
    base = Path(base or public.OUT).resolve()
    requested = Path(out or PREVIEW)
    out = requested.resolve()
    expected = DRAFT.resolve() / 'preview'  # do not resolve through a preview junction/symlink
    if (not DRAFT.resolve().is_relative_to(ROOT.resolve()) or out != expected
            or requested.is_symlink() or base == out or not (base/'index.html').is_file()):
        raise ValueError('Preview is restricted to the named draft preview directory')
    public.audit_public_build(base)
    baseline = {p.relative_to(base).as_posix(): sha(p.read_bytes()) for p in base.rglob('*') if p.is_file()}
    if any(name in baseline for name in files):
        raise ValueError('Candidate must remain absent from the Pages artifact')
    if out.exists():
        shutil.rmtree(out)  # resolved exact draft target checked above
    shutil.copytree(base, out)
    for name in files:
        source = SOURCE/name
        target = out/name
        if source.suffix == '.html':
            raw = source.read_text(encoding='utf-8')
            text = public.sanitize_html(apply_policy(raw, name, programmatic_ads=False), name)
            target.write_text(text, encoding='utf-8', newline='\n')
        elif public.copy_asset(Path(name)):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes().replace(b'\r\n', b'\n'))
        else:
            raise ValueError(f'Asset not explicitly permitted: {name}')
    integrate(out)
    public.write_sitemap(out)
    public.audit_public_build(out)
    errors = check_links(out)
    if errors:
        raise ValueError('\n'.join(errors))
    # Future sitemap only: metadata simulation in memory, never a released HTML or approval.
    pages = sitemap.discover_pages(out)
    for name in list(ARTICLES.values()) + list(METHODS.values()) + [ARCHIVE]:
        page = sitemap.parse_page(out, out/name)
        page.robots = ''
        pages.append(page)
    tree = sitemap.build_tree(out, pages)
    errors = sitemap.validate_tree(tree, out)
    if errors:
        raise ValueError('\n'.join(errors))
    for node in tree.getroot():
        date = node.find(sitemap.qname(sitemap.SITEMAP_NS, 'lastmod'))
        if date is not None:
            node.remove(date)
    tree.write(DRAFT/'sitemap-after-authorization.xml', encoding='utf-8', xml_declaration=True)
    if baseline != {p.relative_to(base).as_posix(): sha(p.read_bytes()) for p in base.rglob('*') if p.is_file()}:
        raise ValueError('Pages artifact changed during candidate preparation')
    result = {'kind': 'local_public_candidate_audit', 'publication_authorized': False,
              'candidate_pages': list(ARTICLES.values()) + list(METHODS.values()) + [ARCHIVE],
              'safe_csv_routes': sorted(public.HISTORY_PUBLIC_CSV), 'link_errors': errors,
              'privacy_and_ads_audit': 'passed', 'default_pages_artifact_unchanged': True,
              'sitemap_current_count': len(ET.parse(out/'sitemap.xml').getroot()),
              'sitemap_projected_count': len(tree.getroot()),
              'sha256_lf': {name: sha((out/name).read_bytes()) for name in files},
              'navigation_sha256_lf': {name: sha((out/name).read_bytes()) for name in
                  ('index.html', 'en.html', 'analisis.html', 'en-analysis.html', 'historial.html', 'en-history.html')},
              'full_artifact_sha256_lf': {p.relative_to(out).as_posix(): sha(p.read_bytes())
                                        for p in sorted(out.rglob('*')) if p.is_file()}}
    (DRAFT/'candidate-build-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Exact local candidate built, privacy/ads/links passed; publication remains unauthorized.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write', action='store_true')
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--build', action='store_true')
    args = parser.parse_args()
    if args.write:
        files = candidate_files()
        audit_payload(files)
        for name, data in files.items():
            path = SOURCE/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        MANIFEST.write_text(json.dumps(manifest(files), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    elif args.check:
        verify()
        print('Candidate sources, exact file list and manifest verified; no approval recorded.')
    else:
        build_preview()


if __name__ == '__main__':
    main()
