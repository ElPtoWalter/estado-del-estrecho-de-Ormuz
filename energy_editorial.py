"""Second original: reproducible draft sources and a local-only noindex preview.

No approval records, live monitor changes, merge or deployment operations.
"""
from __future__ import annotations
import argparse,csv,io,json,re,shutil
from decimal import Decimal
from pathlib import Path
import energy_data as data
import build_public_site as public
import history_public_candidate as history
from publication_quality import apply_policy
from check_public_links import check as check_links

FOLDER=data.FOLDER
SOURCE=FOLDER/'candidate'
MANIFEST=FOLDER/'review-manifest.json'
ASSETS='assets/research/energy-flows-20261025'
ARTICLES={'es':'ormuz-cierre-paso-flujos.html','en':'en-hormuz-closure-passage-flows.html'}
METHODS={'es':'metodo-flujos-energia-20261025.html','en':'en-energy-flow-method-20261025.html'}


def num(value,lang):
    text=data.number(Decimal(value),1)
    return text.replace('.',',') if lang=='es' else text


def frame(lang,name,title,body,pair):
    es=lang=='es'
    nav=[('index.html' if es else 'en.html','Inicio' if es else 'Home'),
         ('analisis.html' if es else 'en-analysis.html','Análisis' if es else 'Analysis'),
         ('historiales-monitor-ormuz.html' if es else 'en-monitor-archives-hormuz.html','Primer análisis' if es else 'First analysis'),
         (METHODS[lang],'Método y fuentes' if es else 'Method and sources')]
    alternate=pair['en' if es else 'es']
    alts=''.join(f'<link rel="alternate" hreflang="{key}" href="{public.DOMAIN}/{slug}">' for key,slug in {**pair,'x-default':pair['es']}.items())
    description=('Análisis de seis trimestres de petróleo y GNL de la EIA y una matriz para distinguir anuncios, travesías y continuidad comercial. Estimaciones históricas, no tráfico actual.' if es else
        'Six quarters of EIA oil and LNG estimates and an evidence matrix separating announcements, voyages and commercial continuity. Historical estimates, not current traffic.')
    disclosure=('Borrador para revisión editorial · Preparación con asistencia de IA · Sin autorización de publicación · Publicidad desactivada' if es else
        'Draft for editorial review · Prepared with AI assistance · Publication not authorised · Advertising disabled')
    document=f'''<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | Estrecho Ormuz</title><meta name="description" content="{description}"><meta name="robots" content="noindex,follow"><meta name="content-kind" content="original-draft"><meta name="publisher-ads" content="disabled"><meta name="referrer" content="strict-origin-when-cross-origin">
<link rel="canonical" href="{public.DOMAIN}/{name}">{alts}<link rel="stylesheet" href="/{ASSETS}/energy-editorial.css"></head><body>
<a class="skip" href="#article">{'Saltar al artículo' if es else 'Skip to article'}</a>
<header class="masthead"><a class="brand" href="/{nav[0][0]}">ESTRECHO ORMUZ<small>{'Observatorio marítimo y energético' if es else 'Maritime and energy observatory'}</small></a><a class="language" lang="{'en' if es else 'es'}" hreflang="{'en' if es else 'es'}" href="/{alternate}">{'Read in English ↗' if es else 'Leer en español ↗'}</a></header>
<nav class="observatory-nav" aria-label="{'Navegación' if es else 'Navigation'}">{''.join(f'<a href="/{url}">{label}</a>' for url,label in nav)}</nav>
<main id="article"><p class="draft-bar" data-draft-disclosure>{disclosure}</p>{body}</main>
<footer><p>ESTRECHO ORMUZ · {disclosure}</p><nav aria-label="{'Información institucional' if es else 'Institutional information'}"><a href="/{'politica-editorial.html' if es else 'en-editorial-policy.html'}">{'Política editorial' if es else 'Editorial policy'}</a> · <a href="/{'correcciones.html' if es else 'en-corrections.html'}">{'Correcciones' if es else 'Corrections'}</a> · <a href="/{'contacto.html' if es else 'en-contact.html'}">{'Contacto' if es else 'Contact'}</a></nav></footer></body></html>'''
    return re.sub(r'<a href="('+re.escape(public.DOMAIN)+r'/[^"]+)"',lambda m:'<a href="'+m[1][len(public.DOMAIN):]+'" data-source-url="'+m[1]+'"',document)


def matrix(lang):
    es=lang=='es'
    rows=[
        ('Cierre declarado','Declaración original, emisor, fecha y alcance','Un anuncio atribuible con ese contenido','Que se haya ejecutado o que produzca un efecto jurídico concreto'),
        ('Paso confirmado','Travesía completa, identidad contrastada, ruta e intervalo; fuentes de cobertura conocida','Que ese paso se produjo dentro del ámbito documentado','Regularidad, acceso para todos o volumen total transportado'),
        ('Bloqueo físico total','Definición del área e intervalo y evidencia operativa con cobertura suficiente','Una imposibilidad material dentro de ese ámbito, si la prueba la sostiene','Que el silencio AIS o la ausencia de noticias demuestren ausencia de barcos'),
        ('Funcionamiento comercial','Series comparables de volumen, acceso, frecuencia, demoras y riesgo','El grado de continuidad del servicio definido','Que un único paso o una media de volumen prueben normalidad')
    ] if es else [
        ('Declared closure','Original statement, issuer, date and scope','An attributable announcement with that content','Implementation or a particular legal effect'),
        ('Confirmed passage','Complete voyage, checked identity, route and interval; sources with known coverage','That the passage occurred within its documented scope','Regularity, access for everyone or total volume transported'),
        ('Total physical blockage','Defined area and interval; operational evidence with adequate coverage','Physical impassability within that scope, if supported by the evidence','That AIS silence or missing reports establish an absence of ships'),
        ('Commercial operation','Comparable volume, access, frequency, delay and risk series','Continuity of the defined service','That one passage or a volume average proves normality')]
    heads=['Afirmación','Prueba que habría que reunir','Qué puede sostener','Qué no demuestra'] if es else ['Claim','Evidence to gather','What it can support','What it cannot establish']
    return '<section><h2>'+('Una matriz para no cambiar de pregunta' if es else 'An evidence matrix that keeps the question clear')+'</h2><div class="table-wrap matrix" role="region" tabindex="0" aria-label="'+('Matriz de evidencias' if es else 'Evidence matrix')+'"><table><caption>'+('Elaboración propia: criterios propuestos, no hechos marítimos nuevos. Desliza para leer las cuatro columnas.' if es else 'Own framework: proposed criteria, not new maritime findings. Scroll to read all four columns.')+'</caption><thead><tr>'+''.join(f'<th scope="col">{h}</th>' for h in heads)+'</tr></thead><tbody>'+''.join('<tr><th scope="row">'+r[0]+'</th>'+''.join(f'<td>{x}</td>' for x in r[1:])+'</tr>' for r in rows)+'</tbody></table></div></section>'


def chart(lang,kind):
    es=lang=='es'
    alt=('Seis trimestres separados por unidad: petróleo 20,9; 21,0; 21,3; 21,6; 14,9; 4,9 millones de barriles diarios. GNL 11,7; 11,0; 10,9; 10,5; 7,4; 0,8 miles de millones de pies cúbicos diarios.' if es else
         'Six quarters in separate units: oil 20.9, 21.0, 21.3, 21.6, 14.9, 4.9 million barrels per day. LNG 11.7, 11.0, 10.9, 10.5, 7.4, 0.8 billion cubic feet per day.') if kind=='absolute' else (
         'Índices propios de seis trimestres: 2025T4 igual a 100 para ambas series; en 2026T2 petróleo 22,7 y GNL 7,6. Los puntos son trimestrales, no observaciones diarias.' if es else
         'Own six-quarter indices: 2025 Q4 equals 100 for both series; in 2026 Q2 oil reaches 22.7 and LNG 7.6. Points represent quarters, not daily observations.')
    title=('Volúmenes absolutos, con ejes separados' if es else 'Absolute volumes on separate axes') if kind=='absolute' else ('Índices con base 2025T4 = 100' if es else 'Indices with 2025 Q4 = 100')
    note=('Cada barra usa su unidad original y parte de cero.' if es else 'Each bar uses its original unit and starts at zero.') if kind=='absolute' else ('La base es una referencia de cálculo, no una capacidad normal. Las líneas solo conectan medias trimestrales. Círculos huecos y rombos distinguen las series cuando coinciden o se aproximan; ambos índices valen 100 en 2025T4. No se desplazan los puntos para separarlos.' if es else 'The baseline is a calculation reference, not normal capacity. Lines only connect quarterly means. Hollow circles and diamonds distinguish coincident or nearby points; both indices equal 100 in 2025 Q4. Points are not shifted to separate them.')
    return f'<figure><h3>{title}</h3><picture><source media="(max-width: 600px)" srcset="/{ASSETS}/energy-{kind}-{lang}-mobile.svg"><img src="/{ASSETS}/energy-{kind}-{lang}.svg" alt="{alt}" decoding="async"></picture><figcaption>{note} '+('Fuente: EIA, Global Energy Security Data, tabla 4, 12/08/2026; 2025T1–2026T2. Análisis EIA basado en Vortexa; gráficos y, en su caso, índices propios. ' if es else
        'Source: EIA, Global Energy Security Data, table 4, 12 August 2026; 2025 Q1–2026 Q2. EIA analysis based on Vortexa; own charts and, where applicable, indices. ')+f'<a href="/{ASSETS}/energy-series.csv" download>'+('Datos y cálculos (CSV)' if es else 'Data and calculations (CSV)')+'</a>.</figcaption></figure>'


def table(lang):
    rows,_=data.calculate();es=lang=='es'
    heads=['Trimestre','Petróleo (millones b/d)','GNL (miles de millones pies³/d)','Índice petróleo','Índice GNL'] if es else ['Quarter','Oil (million b/d)','LNG (billion ft³/d)','Oil index','LNG index']
    body=''
    for r in rows:
        label=r['period'].replace('Q','T') if es else r['period'].replace('Q',' Q')
        body+=f'<tr><th scope="row">{label}</th>'+''.join(f'<td class="numeric">{num(r[k],lang)}</td>' for k in data.FIELDS[1:5])+'</tr>'
    return '<div class="table-wrap" role="region" tabindex="0" aria-label="'+('Serie energética completa' if es else 'Complete energy series')+'"><table><caption>'+('EIA, tabla 4, edición 12/08/2026. Medias diarias trimestrales estimadas; índices propios con 2025T4 = 100.' if es else 'EIA table 4, release 12 August 2026. Estimated quarterly daily averages; own indices, 2025 Q4 = 100.')+'</caption><thead><tr>'+''.join(f'<th scope="col">{h}</th>' for h in heads)+'</tr></thead><tbody>'+body+'</tbody></table></div>'


def limits(lang):
    items=['Seis medias trimestrales no describen cada día, el número de buques o una hora concreta de cierre.',
           'No hay observaciones AIS propias, identificación de travesías, datos diarios, márgenes de incertidumbre publicados en estas filas ni estimación causal.',
           'Las cifras originales tienen un decimal. Los decimales adicionales del CSV sirven para reproducir las divisiones; no aumentan la precisión de la fuente.',
           'La edición del suplemento es del 12/08/2026, aunque la cabecera general del STEO muestre una edición posterior. Nuevas revisiones requieren otra versión del análisis.'] if lang=='es' else [
           'Six quarterly means do not describe every day, vessel numbers or a particular hour of closure.',
           'There are no original AIS observations, identified voyages, daily data, uncertainty ranges published in these rows or causal estimates here.',
           'Source values have one decimal. Extra CSV decimal places reproduce divisions; they do not increase source precision.',
           'The supplement release is 12 August 2026, even if the general STEO header displays a later edition. Revisions require a new analysis version.']
    return '<aside class="limits"><h2>'+('Límites que cambian la lectura' if lang=='es' else 'Limits that affect the interpretation')+'</h2><ul>'+''.join(f'<li>{s}</li>' for s in items)+'</ul></aside>'


def downloads(lang):
    es=lang=='es'
    return '<div class="download-row">'+f'<a href="/{ASSETS}/energy-series.csv" download>'+('Descargar serie y cálculos CSV' if es else 'Download series and calculations CSV')+f'</a><a href="/{METHODS[lang]}">'+('Metodología, fuentes y derechos' if es else 'Method, sources and rights')+'</a></div>'


def method(lang):
    es=lang=='es'
    paragraphs=[
        ('Qué se ha contrastado','Las dos filas seleccionadas de la tabla 4 coinciden, en los seis trimestres, con el CSV previo. La consulta HTTP y las doce cifras se registran el 25/10/2026. La fecha de edición pertenece al suplemento Global Energy Security Data: 12/08/2026. No confundimos la cabecera de otro número del STEO con una nueva fecha para esta tabla.'),
        ('Qué representa la fuente','Petróleo total: millones de barriles diarios. GNL: miles de millones de pies cúbicos diarios. Son estimaciones de medias diarias por trimestre publicadas por la EIA a partir de Vortexa con análisis adicional de la EIA. La metodología fecha los cargamentos por entrada en el paso e incorpora estimaciones de ruta cuando la señal AIS es incompleta. Aquí no asignamos horas ni zona horaria a una tabla que no ofrece observaciones diarias.'),
        ('Qué calculamos','Para cada producto: índice = valor del trimestre ÷ valor de 2025T4 × 100. Variación entre A y B = (valor B ÷ valor A − 1) × 100. Variación trimestral: B es el trimestre y A el inmediatamente anterior. El primer cambio trimestral queda vacío porque falta el período previo en esta selección. No se rellena con cero.'),
        ('Cálculos principales','Petróleo: (4,9 ÷ 21,6 − 1) × 100 = −77,31481481 %. GNL: (0,8 ÷ 10,5 − 1) × 100 = −92,38095238 %. En el artículo redondeamos a un decimal. La sensibilidad sustituye 2025T4 por 2025T1 como base: −76,55502392 % y −93,16239316 %.'),
        ('Cómo reproducirlo sin código privado','Descarga el CSV, comprueba las seis filas en orden y las dos unidades, y repite las fórmulas anteriores sin redondear los valores intermedios. Contrasta índices y cambios con sus columnas; los resultados se exportan con ocho decimales por conveniencia aritmética. El artículo muestra un decimal. La fila de petróleo total se toma tal como la publica la EIA; no se reconstruye sumando componentes redondeados.'),
        ('Reglas visuales','Las barras absolutas parten de cero y mantienen ejes separados por producto. Los índices comparten una escala adimensional y una base explícita, sin doble eje ni suma de unidades. Cada marca representa un trimestre; las líneas no son datos diarios ni interpolaciones de tráfico. Hay variantes móviles, tabla accesible y alternativas textuales. No dibujamos intervalos de confianza que la tabla no aporta.'),
        ('Aportación propia y límites','Son propios la matriz de evidencias, el cálculo de índices y variaciones, la sensibilidad de la base, las visualizaciones y la interpretación sobre continuidad comercial. La matriz propone qué evidencia pedir; no afirma haberla reunido para ningún buque. No estimamos primas de seguros, pérdidas de consumo, causalidad, días de bloqueo o precios futuros.'),
        ('Derechos contrastados y pendientes','La política general de la EIA permite reutilizar sus productos con atribución y fecha, y exige distinguir traducciones y aportaciones propias. También exceptúa materiales protegidos de terceros. Esta tabla está atribuida a análisis de la EIA basado en Vortexa: usamos solo doce valores agregados ya publicados, no datos privados ni posiciones AIS. No afirmamos que la licencia de Vortexa sea abierta ni que exista una autorización jurídica independiente. La revisión final de atribución y derechos del titular sigue pendiente. Cualquier incorporación de materiales de terceros requiere comprobar sus permisos. No reproducimos logos, fotografías, gráficos ajenos o textos completos de la EIA/OMI.'),
        ('Estado editorial','Firma institucional prevista: Estrecho Ormuz. Texto y explicación españoles e ingleses preparados por el observatorio con asistencia de IA; la EIA no es responsable de esa traducción ni de nuestras conclusiones. Los cuatro HTML permanecen noindex y fuera de la construcción de Pages, sitemap y RSS. No se registra aprobación humana ni se hereda la del primer análisis.')
    ] if es else [
        ('What was checked','Both selected table-4 rows match the existing CSV across all six quarters. HTTP delivery and the twelve figures were checked on 25 October 2026. The Global Energy Security Data supplement release is 12 August 2026. A later general STEO header is not treated as a new release date for this table.'),
        ('What the source represents','Total oil is in million barrels per day; LNG is in billion cubic feet per day. These are estimated quarterly daily averages published by the EIA from Vortexa with additional EIA analysis. Its methodology dates cargo by chokepoint entry and estimates routes when AIS is incomplete. We assign no hours or timezone to a table without daily observations.'),
        ('What we calculate','For each product: index = quarterly value ÷ 2025 Q4 value × 100. Change from A to B = (B ÷ A − 1) × 100. For quarter-to-quarter change, A is the immediately preceding quarter. The first change is blank because the preceding period is absent from this selection; it is not replaced by zero.'),
        ('Principal calculations','Oil: (4.9 ÷ 21.6 − 1) × 100 = −77.31481481%. LNG: (0.8 ÷ 10.5 − 1) × 100 = −92.38095238%. Article values round to one decimal. Sensitivity replaces 2025 Q4 with 2025 Q1 as baseline: −76.55502392% and −93.16239316%.'),
        ('Reproduction without private code','Download the CSV, check the six ordered rows and both units, then repeat the formulas without rounding intermediate inputs. Compare indices and changes with their columns, exported to eight decimal places for arithmetic convenience. The article displays one decimal. The published total-oil row is used directly rather than reconstructed from rounded component rows.'),
        ('Visual rules','Absolute bars start at zero on separate product axes. Indices share a dimensionless scale and an explicit baseline, without a second axis or adding units. Each mark represents a quarter; connecting lines are not daily traffic observations or interpolations. Mobile variants, an accessible table and text alternatives are provided. No uncertainty bands are drawn when the table supplies none.'),
        ('Original contribution and limits','The evidence matrix, calculated indices and changes, baseline sensitivity, visualisations and commercial-continuity interpretation are original. The matrix proposes evidence to seek; it does not claim that evidence was collected for any ship. We estimate no insurance premiums, consumption losses, causality, days blocked or future prices.'),
        ('Rights checked and outstanding','The EIA general policy permits reuse of its products with attribution and date and requires translations and original contributions to be distinguished. It also excepts protected third-party materials. This table is credited to EIA analysis based on Vortexa: we use twelve already-published aggregate figures, not private tracking or AIS positions. We claim neither an open Vortexa licence nor independent legal clearance. Final publisher review of attribution and rights remains pending. Any additional third-party material needs its own permission check. No logos, photographs, third-party graphics or complete EIA/IMO texts are reproduced.'),
        ('Editorial status','Proposed institutional byline: Estrecho Ormuz. Spanish and English text and explanations were prepared by the observatory with AI assistance; the EIA is not responsible for this translation or our conclusions. All four HTML files remain noindex and excluded from the Pages build, sitemap and RSS. No human approval is recorded or inherited from the first analysis.')]
    sources=[(data.EIA,'EIA · Global Energy Security Data · Table 4 · 12 August 2026'),(data.RIGHTS,'EIA · Copyrights and Reuse'),(data.IMO,'IMO · Middle East / Strait of Hormuz · general-awareness transit indicator')]
    title='Método, fuentes y derechos del análisis energético' if es else 'Energy analysis: method, sources and rights'
    body=f'<h1>{title}</h1><div class="prose">'+''.join(f'<h2>{heading}</h2><p>{text}</p>' for heading,text in paragraphs)+'<h2 id="sources">'+('Fuentes originales' if es else 'Original sources')+'</h2><ol class="source-list">'+''.join(f'<li><a href="{url}">{label}</a></li>' for url,label in sources)+'</ol>'+downloads(lang)+f'<p><a href="/{ARTICLES[lang]}">'+('Volver al artículo' if es else 'Return to the article')+'</a></p></div>'
    return frame(lang,METHODS[lang],title,body,METHODS)


def files():
    data.read_rows();result={}
    for lang,name in ARTICLES.items():
        text=(FOLDER/f'text-{lang}.html').read_text(encoding='utf-8')
        for key,value in {'MATRIX':matrix(lang),'ABSOLUTE':chart(lang,'absolute'),'INDEX':chart(lang,'index'),'TABLE':table(lang),'LIMITS':limits(lang),'DOWNLOADS':downloads(lang)}.items():
            text=text.replace('{{'+key+'}}',value)
        if '{{' in text:raise ValueError('Unexpanded editorial placeholder')
        title='Ormuz: cierre declarado, paso y flujo energético' if lang=='es' else 'Hormuz: declared closure, passage and energy flows'
        result[name]=frame(lang,name,title,text,ARTICLES).encode()
        result[METHODS[lang]]=method(lang).encode()
    result[f'{ASSETS}/energy-series.csv']=data.csv_text().encode()
    graphs={f'energy-{kind}-{lang}{suffix}.svg' for kind in ('absolute','index') for lang in ('es','en') for suffix in ('','-mobile')}
    if {p.name for p in FOLDER.glob('energy-*.svg')}!=graphs:raise ValueError('Exactly eight chart variants are required')
    for name in sorted(graphs):result[f'{ASSETS}/{name}']=(FOLDER/name).read_bytes().replace(b'\r\n',b'\n')
    css=(data.ROOT/'drafts/historiales-20261024/history-editorial.css').read_text(encoding='utf-8')+'\n'+(
        '.brand{color:var(--text);text-decoration:none}.observatory-nav{max-width:1160px;margin:auto;padding:14px 28px;display:flex;flex-wrap:wrap;gap:10px 24px;border-bottom:1px solid var(--line);font-size:14px}.observatory-nav a{padding:5px 0}picture img{display:block;width:100%;height:auto;border:1px solid var(--line);border-radius:10px}.interpretation-label{color:var(--amber);font-size:14px}.matrix table{min-width:950px}.keyfacts strong{font-size:32px}.keyfacts span{font-size:13px}.prose strong{font-weight:650}figure h3{margin:0 0 18px} @media(max-width:760px){.observatory-nav{padding:12px 20px;gap:6px 18px}.keyfacts{grid-template-columns:1fr}.keyfacts div{border-right:0;border-bottom:1px solid var(--line);padding:14px 0}.keyfacts div:first-child{padding-left:0}.keyfacts strong{font-size:29px}.brand{letter-spacing:.08em}.language{font-size:12px;padding:7px}.matrix table{font-size:15px}}\n')
    result[f'{ASSETS}/energy-editorial.css']=css.encode()
    audit_payload(result);return result


def audit_payload(payload):
    for name,raw in payload.items():
        if name.endswith('.csv'):
            if name!=f'{ASSETS}/energy-series.csv' or raw.decode()!=data.csv_text():raise ValueError('Unknown or altered CSV')
        else:history.audit_payload({name:raw})


def manifest(payload):
    return {'kind':'second_original_editorial_draft','prepared_on':'2026-10-25','publication_authorized':False,
            'human_editorial_approval':None,'reviewer':None,'reviewed_at':None,'advertising':False,
            'proposed_institutional_byline':'Estrecho Ormuz','index':False,'source_release':'2026-08-12',
            'source_input_sha256_lf':data.sha(data.INPUT.read_bytes()),
            'generator_sha256_lf':{name:data.sha((data.ROOT/name).read_bytes()) for name in ('energy_data.py','energy_editorial.py')},
            'sha256_lf':{name:data.sha(raw) for name,raw in sorted(payload.items())},
            'editorial_input_sha256_lf':{name:data.sha((FOLDER/name).read_bytes()) for name in
                ('text-es.html','text-en.html','render_charts.py','chart-audit.json','source-verification.json','sources-and-rights.json')}}


def verify():
    payload=files()
    actual={p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob('*') if p.is_file()}
    if actual!=set(payload):raise ValueError('Draft resource selection changed')
    for name,raw in payload.items():
        if data.sha((SOURCE/name).read_bytes())!=data.sha(raw):raise ValueError('Draft bytes changed: '+name)
    if json.loads(MANIFEST.read_text(encoding='utf-8'))!=manifest(payload):raise ValueError('Draft manifest mismatch; no automatic resealing')
    return payload


def preview():
    payload=verify();base=public.OUT;requested=FOLDER/'preview';out=requested.resolve()
    if requested.is_symlink() or out!=FOLDER.resolve()/'preview' or not out.is_relative_to(data.ROOT.resolve()):raise ValueError('Unsafe preview target')
    public.audit_public_build(base)
    before={p.relative_to(base).as_posix():data.sha(p.read_bytes()) for p in base.rglob('*') if p.is_file()}
    if set(payload)&set(before):raise ValueError('Unapproved second article appeared in Pages')
    if out.exists():shutil.rmtree(out)
    shutil.copytree(base,out)
    for name,raw in payload.items():
        path=out/name;path.parent.mkdir(parents=True,exist_ok=True)
        if name.endswith('.html'):
            text=public.sanitize_html(apply_policy(raw.decode(),name,programmatic_ads=False),name)
            path.write_text(text,encoding='utf-8',newline='\n')
        elif public.copy_asset(Path(name)):path.write_bytes(raw)
        else:raise ValueError('Preview asset is not explicitly permitted: '+name)
    for lang,names in {'es':('index.html','analisis.html'),'en':('en.html','en-analysis.html')}.items():
        label='Segundo análisis: borrador pendiente de revisión' if lang=='es' else 'Second analysis: draft awaiting review'
        block=f'<aside data-energy-draft><h2><a href="/{ARTICLES[lang]}">{label}</a></h2></aside>'
        for name in names:
            path=out/name;path.write_text(path.read_text(encoding='utf-8').replace('</main>',block+'</main>',1),encoding='utf-8',newline='\n')
    public.write_sitemap(out);public.audit_public_build(out)
    errors=check_links(out)
    if errors:raise ValueError('\n'.join(errors))
    if before!={p.relative_to(base).as_posix():data.sha(p.read_bytes()) for p in base.rglob('*') if p.is_file()}:raise ValueError('Pages artifact modified')
    report={'kind':'local_only_second_original_preview','publication_authorized':False,'human_review':None,
            'link_errors':errors,'default_pages_artifact_unchanged':True,'advertising':False,
            'sha256_lf':{name:data.sha((out/name).read_bytes()) for name in payload},
            'full_artifact_sha256_lf':{p.relative_to(out).as_posix():data.sha(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()}}
    (FOLDER/'preview-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Local draft preview built; links/privacy passed. Normal Pages artifact unchanged; four HTML noindex.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--write',action='store_true');group.add_argument('--check',action='store_true');group.add_argument('--build-preview',action='store_true');args=parser.parse_args()
    if args.write:
        payload=files()
        for name,raw in payload.items():
            path=SOURCE/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        MANIFEST.write_text(json.dumps(manifest(payload),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        _,comparisons=data.calculate();(FOLDER/'calculations.json').write_text(json.dumps(comparisons,indent=2)+'\n',encoding='utf-8')
    elif args.check:verify();print('Second original: exact sources, calculations, assets and unapproved draft manifest verified.')
    else:preview()
