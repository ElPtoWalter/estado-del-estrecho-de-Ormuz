"""Third original: sealed draft and separate local preview; never publishes."""
from __future__ import annotations
import argparse,csv,io,json,re,shutil
from pathlib import Path
import spain_data as data
import build_public_site as public
import history_public_candidate as history
from publication_quality import apply_policy
from check_public_links import check as check_links

FOLDER=data.FOLDER;SOURCE=FOLDER/'candidate';MANIFEST=FOLDER/'review-manifest.json'
ASSETS='assets/research/spain-europe-20261025'
ARTICLES={'es':'espana-europa-ormuz-dos-porcentajes.html','en':'en-spain-europe-hormuz-two-percentages.html'}
METHODS={'es':'metodo-espana-europa-20261025.html','en':'en-spain-europe-method-20261025.html'}
CSV_NAMES=('source-inputs.csv','calculations.csv')

def table(headers,rows,caption,label):
 return f'<div class="table-wrap" role="region" tabindex="0" aria-label="{label}"><table><caption>{caption}</caption><thead><tr>'+''.join(f'<th scope="col">{h}</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr><th scope="row">'+r[0]+'</th>'+''.join('<td>'+c+'</td>' for c in r[1:])+'</tr>' for r in rows)+'</tbody></table></div>'

def matrix(lang):
 es=lang=='es'
 rows=[('Enagás · 2025','GWh; aprovisionamientos físicos españoles de gas por gasoducto y GNL','Procedencia atribuida del suministro','Consumo, coste, ruta de cada barco o gas perdido'),
       ('Eurostat · 2025','% del valor de importaciones extracomunitarias de GNL de la UE','Peso de Catar en ese gasto de importación','Cuota en GWh, consumo europeo o toda la energía'),
       ('Cálculos del observatorio','Cocientes de cantidades publicadas; unidades separadas','Efecto del denominador y discrepancia documental','Una cuota oficial corregida o un ranking de vulnerabilidad')]
 if not es:rows=[('Enagás · 2025','GWh; Spanish physical pipeline-gas and LNG supplies','Attributed supply origin','Consumption, costs, each vessel route or lost gas'),('Eurostat · 2025','% of the value of EU extra-EU LNG imports','Qatar’s share of that import spending','GWh share, European consumption or all energy'),('Observatory calculations','Quotients of published quantities; separate units','Denominator effects and a documentary discrepancy','An official corrected share or vulnerability ranking')]
 return table(['Fuente y período','Unidad y denominador','Qué describe','Qué no mide'] if es else ['Source and period','Unit and denominator','What it describes','What it does not measure'],rows,'Mismo año, distintas magnitudes. Elaboración propia a partir de las definiciones oficiales.' if es else 'Same year, different quantities. Own table based on official definitions.','Definiciones y límites de las fuentes' if es else 'Source definitions and limits')

def chart(lang,kind):
 es=lang=='es';base=f'/{ASSETS}/spain-{kind}-{lang}'
 title=('Un numerador, dos denominadores físicos' if es else 'One numerator, two physical denominators') if kind=='denominators' else ('La discrepancia, sin una causa confirmada' if es else 'The discrepancy, without a confirmed cause')
 alt=('Catar: 6.403 GWh. Entre todos los aprovisionamientos españoles, 372.498 GWh: 1,718935 %. Entre el GNL, 248.084 GWh: 2,580981 %. Cocientes propios de 2025.' if es else 'Qatar: 6,403 GWh. All Spanish supplies, 372,498 GWh: 1.718935%. LNG supplies, 248,084 GWh: 2.580981%. Own 2025 quotients.') if kind=='denominators' else ('Tres filas separadas: gráfico PDF 1,735 %; cociente mapa/total 1,718935 %; Excel oficial 1,718891 %. Escala ampliada 1,710–1,740 %. Sin conciliación causal.' if es else 'Three separate rows: PDF chart 1.735%; map/total quotient 1.718935%; official workbook 1.718891%. Expanded scale 1.710–1.740%. No cause established.')
 note=('Elaboración propia. Enagás 2025, pp. 23–24. Las barras parten de cero; no comparan España con la UE. Los cocientes no sustituyen la cuota publicada del PDF.' if es else 'Own chart. Enagás 2025, pp. 23–24. Bars start at zero; they do not compare Spain with the EU. Quotients do not replace the PDF’s published share.') if kind=='denominators' else ('Elaboración propia. Enagás 2025, PDF pp. 23–25 y Excel «Pág. 25», E12. El eje está ampliado; los puntos no son intervalos de incertidumbre. Las lecturas próximas ocupan filas distintas sin alterar su valor horizontal.' if es else 'Own chart. Enagás 2025, PDF pp. 23–25 and workbook “Pág. 25”, E12. The axis is expanded; dots are not uncertainty intervals. Nearby readings use separate rows without changing their horizontal values.')
 return f'<figure><h3>{title}</h3><picture><source media="(max-width: 640px)" srcset="{base}-mobile.svg"><img src="{base}.svg" width="864" height="396" alt="{alt}" loading="lazy"></picture><figcaption>{note}</figcaption></figure>'

def channels(lang):
 es=lang=='es'
 rows=[('1 · Suministro','Origen, energía y período de las entradas.','Lo que las estadísticas de aprovisionamiento permiten describir.'),('2 · Ruta','Puerto, carga, travesía y destino documentados.','La conexión que falta para medir el tránsito efectivo.'),('3 · Mercado','Alternativas, contratos, inventarios y precios.','La información adicional para estimar consecuencias económicas.')]
 if not es:rows=[('1 · Supply','Origin, energy and period of incoming supplies.','What procurement statistics can describe.'),('2 · Route','Documented port, cargo, passage and destination.','The missing link for measuring actual transit.'),('3 · Market','Alternatives, contracts, stocks and prices.','Additional information needed to estimate economic consequences.')]
 return '<aside class="channels" aria-label="'+('Tres planos de exposición' if es else 'Three aspects of exposure')+'">'+''.join(f'<section><h3>{a}</h3><p>{b}</p><p class="source-note">{c}</p></section>' for a,b,c in rows)+'</aside>'

def downloads(lang):
 es=lang=='es'
 return '<div class="download-row">'+f'<a href="/{ASSETS}/source-inputs.csv" download>'+('Datos seleccionados CSV' if es else 'Selected inputs CSV')+'</a>'+f'<a href="/{ASSETS}/calculations.csv" download>'+('Cálculos CSV' if es else 'Calculations CSV')+'</a>'+f'<a href="/{METHODS[lang]}">'+('Método, fuentes y derechos' if es else 'Method, sources and rights')+'</a></div>'

def frame(lang,name,title,body,pair):
 es=lang=='es';other='en' if es else 'es'
 nav=[('index.html' if es else 'en.html','Inicio' if es else 'Home'),('analisis.html' if es else 'en-analysis.html','Análisis' if es else 'Analysis'),('historiales-monitor-ormuz.html' if es else 'en-monitor-archives-hormuz.html','Historiales' if es else 'Archives'),('ormuz-cierre-paso-flujos.html' if es else 'en-hormuz-closure-passage-flows.html','Cierre, paso y flujos' if es else 'Closure, passage and flows'),(METHODS[lang],'Método y fuentes' if es else 'Method and sources')]
 alts=''.join(f'<link rel="alternate" hreflang="{key}" href="{public.DOMAIN}/{slug}">' for key,slug in {**pair,'x-default':pair['es']}.items())
 disclosure=('Borrador para revisión editorial · Preparación con asistencia de IA · Publicación no autorizada · Publicidad desactivada' if es else 'Draft for editorial review · Prepared with AI assistance · Publication not authorised · Advertising disabled')
 description=('Gas español y GNL europeo en 2025: denominadores físicos y monetarios, discrepancia de Enagás y límites de una comparación de exposición a Ormuz.' if es else 'Spanish gas and EU LNG in 2025: physical and monetary denominators, the Enagás discrepancy and limits to comparing Hormuz exposure.')
 return f'''<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} | Estrecho Ormuz</title><meta name="description" content="{description}"><meta name="robots" content="noindex,follow"><meta name="content-kind" content="original-draft"><meta name="publisher-ads" content="disabled"><meta name="referrer" content="strict-origin-when-cross-origin"><link rel="canonical" href="{public.DOMAIN}/{name}">{alts}<link rel="stylesheet" href="/{ASSETS}/spain-editorial.css"></head><body>
<a class="skip" href="#article">{'Saltar al artículo' if es else 'Skip to article'}</a><header class="masthead"><a class="brand" href="/{nav[0][0]}">ESTRECHO ORMUZ<small>{'Observatorio marítimo y energético' if es else 'Maritime and energy observatory'}</small></a><a class="language" lang="{other}" hreflang="{other}" href="/{pair[other]}">{'Read in English ↗' if es else 'Leer en español ↗'}</a></header><nav class="observatory-nav" aria-label="{'Navegación' if es else 'Navigation'}">{''.join(f'<a href="/{url}">{label}</a>' for url,label in nav)}</nav>
<main id="article"><p class="draft-bar" data-draft-disclosure>{disclosure}</p>{body}</main><footer><p>ESTRECHO ORMUZ · {disclosure}</p><nav aria-label="{'Información institucional' if es else 'Institutional information'}"><a href="/{'politica-editorial.html' if es else 'en-editorial-policy.html'}">{'Política editorial' if es else 'Editorial policy'}</a> · <a href="/{'correcciones.html' if es else 'en-corrections.html'}">{'Correcciones' if es else 'Corrections'}</a> · <a href="/{'contacto.html' if es else 'en-contact.html'}">{'Contacto' if es else 'Contact'}</a></nav></footer></body></html>'''

def method(lang):
 es=lang=='es'
 sections=[('Alcance y versiones','Estudio histórico de gas en 2025, no balance completo de petróleo o energía ni evaluación del estado actual de Ormuz. Se consultan el PDF Enagás 2025 y el Excel de Operación física enlazado en su p. 80; Eurostat, noticia del 25/03/2026 y anexo original. El expediente registra URL, fecha de consulta 25/10/2026 y huellas de cada documento. Las páginas 23, 24 y 25 son la numeración impresa del PDF.'),
 ('Lectura del Excel de Enagás','Hoja «Pág. 25»: E4 identifica 2025, B12 identifica Qatar y E12 contiene 0,01718890770907905 como fracción literal, no como porcentaje ya multiplicado por cien. El caché del gráfico del propio Excel apunta al mismo valor. No se recalcula una fórmula inexistente ni se interpreta la columna C, de otro año, como 2025.'),
 ('Dictamen de conciliación','Discrepancia documental no resuelta. PDF p. 25: 1,735 %. Cociente de cifras PDF pp. 23–24: 1,718935403680… %. Excel E12 × 100: 1,718890770907905 %. Las dos últimas lecturas coinciden a tres decimales, pero no prueban la causa de la primera. No se ha obtenido una conciliación específica de SL-ATR ni una explicación del emisor. No se ha contactado con Enagás ni se afirma haberlo hecho.'),
 ('Fórmulas reproducibles','Cuota del total = 6403 / 372498 × 100. Cuota del GNL = 6403 / 248084 × 100. Excel en porcentaje = 0.01718890770907905 × 100. Diferencia en puntos porcentuales = 1.735 − cuota del total. Volumen implícito hipotético = 372498 × 1.735 / 100; diferencia = resultado − 6403. El volumen implícito no es un dato observado. La aritmética usa Decimal, sin redondeo intermedio; el CSV ofrece ocho decimales por reproducibilidad, sin aumentar la precisión de la fuente.'),
 ('Cómo comprobar Eurostat','VISUAL 2: A1 fija importaciones extracomunitarias y 2025; A2 dice cuota del comercio por valor; D4 identifica GNL, D9 a Qatar y E9 contiene 8.855309243451158 %. Su redondeo a un decimal es 8,9 %. La noticia identifica el producto CN 27111100. El anexo también contiene cuotas por masa neta en «Natural gas (liq) partners», bloque de 2025, A15:C19. Esa masa no es energía en GWh; no la sustituimos silenciosamente por la cuota de valor.'),
 ('Repetición sin archivos técnicos','Descarga los datos seleccionados y los cálculos. Comprueba las seis filas de entrada, sus unidades y período. Repite las operaciones anteriores y compara las ocho filas calculadas. Los CSV usan punto decimal y separador coma, con fuentes y localizadores visibles. Las operaciones se expresan como texto, no como celdas ejecutables. No se publican el PDF completo, Excel originales, JSON, código o configuraciones.'),
 ('Qué muestran los gráficos','Las dos barras de denominadores comienzan en cero y usan el mismo numerador español; no incluyen el porcentaje europeo. La figura de discrepancia usa puntos, tres filas y una escala ampliada identificada de 1,710 a 1,740 %. El valor cercano del Excel no se desplaza horizontalmente para distinguirlo del cociente. No hay intervalos de confianza inventados. Cada figura tiene alternativa textual y versión móvil.'),
 ('Derechos y atribución','El aviso legal de Enagás, apartado 7, protege sus contenidos y no concede una licencia abierta general de explotación. Este borrador selecciona hechos numéricos limitados, los atribuye y aporta cálculos, gráficos y texto propios. No reproduce sus gráficos, mapa, tablas gráficas, fotos, logos o páginas. La disponibilidad del Excel no se presenta como permiso de redistribución. El titular debe valorar la base de reutilización de estas cifras antes de autorizar su publicación; no se acredita una autorización específica ni una revisión jurídica independiente.'),
 ('Condiciones Eurostat y contexto AIE','Eurostat permite reutilizar sus datos estadísticos con atribución, sujeto a avisos particulares y excepciones de terceros. Las adaptaciones y cálculos son del observatorio; Eurostat no es responsable de ellos ni de las conclusiones o explicaciones en español e inglés. No se reproduce la fotografía de la noticia. La AIE se enlaza como contexto geográfico y económico de su ficha fechada en febrero de 2026; no se copian sus gráficos, bases de terceros o series.'),
 ('Estado editorial','Firma institucional prevista: Estrecho Ormuz. Preparación con asistencia de IA. No existe aprobación editorial humana de esta edición ni se hereda la de otros análisis. Los cuatro HTML siguen noindex,follow, fuera de Pages, sitemap y RSS. Publicidad apagada; sin cambios de clasificación del monitor.')]
 if not es:sections=[('Scope and releases','Historical gas analysis for 2025, not a complete oil or energy balance or an assessment of current Hormuz conditions. Sources are the Enagás 2025 PDF and the physical-operation workbook linked on p. 80, plus the Eurostat news release of 25 March 2026 and original annex. The record identifies URLs, access date 25 October 2026 and document hashes. PDF locators use printed pages 23–25.'),('Reading the Enagás workbook','Sheet “Pág. 25”: E4 identifies 2025, B12 identifies Qatar, and E12 contains 0.01718890770907905 as a literal fraction, not a percentage already multiplied by 100. The workbook chart cache references the same value. We do not recalculate a nonexistent formula or use column C, from another year, as 2025.'),('Reconciliation verdict','Unresolved documentary discrepancy. PDF p. 25: 1.735%. Quotient from PDF pp. 23–24: 1.718935403680…%. Workbook E12 × 100: 1.718890770907905%. The latter two agree to three decimal places but do not establish the cause of the first. No specific SL-ATR reconciliation or issuer explanation was obtained. Enagás was not contacted; no such contact is claimed.'),('Reproducible formulas','Total share = 6403 / 372498 × 100. LNG share = 6403 / 248084 × 100. Workbook percentage = 0.01718890770907905 × 100. Percentage-point gap = 1.735 − total share. Hypothetical implied volume = 372498 × 1.735 / 100; residual = result − 6403. Implied volume is not observed supply. Decimal arithmetic avoids intermediate rounding. Eight CSV decimals aid reproduction without increasing source precision.'),('Checking Eurostat','VISUAL 2: A1 specifies extra-EU imports and 2025; A2 identifies trade value shares; D4 identifies LNG, D9 Qatar and E9 the 8.855309243451158% share. One-decimal rounding gives 8.9%. The news release identifies CN 27111100. The annex also contains net-mass shares in “Natural gas (liq) partners”, 2025 block A15:C19. Mass is not energy in GWh and is not silently substituted for the value share.'),('Reproduction without technical files','Download the selected inputs and calculations. Check six input rows, units and period, then repeat the operations and compare the eight derived rows. CSV uses decimal points and comma separators, with sources and locators. Formulas are descriptive text, not executable spreadsheet cells. Complete PDFs, original workbooks, JSON, code and configuration are not published.'),('Visual rules','The denominator bars start at zero and use the same Spanish numerator; the EU percentage is absent. The discrepancy figure uses dots on three rows and a labelled expanded 1.710–1.740% scale. The nearby workbook value is not moved horizontally to separate it from the quotient. No confidence intervals are invented. Each figure has a text alternative and mobile version.'),('Rights and attribution','Section 7 of the Enagás legal notice protects its content and does not grant a general open exploitation licence. This draft cites limited numerical facts with attribution and adds original calculations, graphics and text. Its map, charts, graphic tables, photos, logos and pages are not reproduced. Workbook availability is not treated as redistribution permission. The publisher must consider the basis for reusing these figures before authorising publication; no specific permission or independent legal clearance is claimed.'),('Eurostat conditions and IEA context','Eurostat permits reuse of its statistical data with attribution, subject to individual notices and third-party exceptions. Adaptations and calculations are the observatory’s own; Eurostat is not responsible for them or for the conclusions and explanations in Spanish and English. The news photograph is not reproduced. The IEA factsheet dated February 2026 is linked as geographical and economic context; its charts, third-party databases and series are not copied.'),('Editorial status','Proposed institutional byline: Estrecho Ormuz. Prepared with AI assistance. This edition has no human editorial approval and inherits none from earlier analyses. All four HTML pages remain noindex,follow and excluded from Pages, sitemap and RSS. Advertising is disabled; monitor classifications are unchanged.')]
 rights_rows=[('Enagás · PDF / Excel','GWh y cuota física; España, 2025' if es else 'GWh and physical share; Spain, 2025','Sin licencia abierta general acreditada; hechos limitados y obra propia, revisión pendiente.' if es else 'No general open licence established; limited facts and own work, review pending.'),('Eurostat · VISUAL 2','Cuota monetaria; GNL extracomunitario, UE, 2025' if es else 'Monetary share; EU extra-EU LNG, 2025','Reutilización estadística con atribución y cambios identificados; excepciones de terceros.' if es else 'Statistical reuse with attribution and adaptations identified; third-party exceptions.'),('AIE / IEA · February 2026','Contexto de ruta y mercado' if es else 'Route and market context','Referencia enlazada; sin copiar gráficos ni bases.' if es else 'Linked reference; no charts or databases copied.')]
 sources=[(data.ENAGAS,'Enagás · Informe del Sistema Gasista Español 2025 · pp. 2, 23–25, 80'),(data.ENAGAS_XLSX,'Enagás · Excel Operación física 2025 · Pág. 25!E12'),('https://www.enagas.es/es/aviso-legal/','Enagás · Aviso legal · apartado 7'),(data.EUROSTAT,'Eurostat · EU imports of energy products decreased again in 2025 · 25 March 2026'),(data.EUROSTAT_XLSX,'Eurostat · original annex · VISUAL 2!A1:A2, D4:E9'),('https://ec.europa.eu/eurostat/help/copyright-notice','Eurostat · Copyright notice and free re-use of data'),('https://www.iea.org/about/strait-of-hormuz','IEA · Strait of Hormuz · factsheet dated February 2026')]
 title='Método, fuentes y derechos: España y Europa ante Ormuz' if es else 'Method, sources and rights: Spain, Europe and Hormuz'
 body=f'<h1>{title}</h1><div class="prose">'+''.join(f'<h2>{h}</h2><p>{p}</p>' for h,p in sections)+'</div>'+table(['Fuente','Unidad y ámbito','Derechos y uso previsto'] if es else ['Source','Unit and scope','Rights and intended use'],rights_rows,'Matriz de fuentes y derechos · consulta 25/10/2026' if es else 'Sources and rights matrix · accessed 25 October 2026','Fuentes y derechos' if es else 'Sources and rights')+'<h2 id="sources">'+('Fuentes originales' if es else 'Original sources')+'</h2><ol class="source-list">'+''.join(f'<li><a href="{url}">{label}</a></li>' for url,label in sources)+'</ol>'+downloads(lang)+f'<p><a href="/{ARTICLES[lang]}">'+('Volver al artículo' if es else 'Return to article')+'</a></p>'
 return frame(lang,METHODS[lang],title,body,METHODS)

def files():
 data.read_inputs();result={}
 for lang,name in ARTICLES.items():
  body=(FOLDER/f'text-{lang}.html').read_text(encoding='utf-8')
  for key,value in {'DENOMINATORS':chart(lang,'denominators'),'DISCREPANCY':chart(lang,'discrepancy'),'MATRIX':matrix(lang),'CHANNELS':channels(lang),'DOWNLOADS':downloads(lang)}.items():body=body.replace('{{'+key+'}}',value)
  if '{{' in body:raise ValueError('Unexpanded placeholder')
  title='España y Europa ante Ormuz: qué miden dos porcentajes' if lang=='es' else 'Spain, Europe and Hormuz: what two gas shares measure'
  result[name]=frame(lang,name,title,body,ARTICLES).encode();result[METHODS[lang]]=method(lang).encode()
 result[f'{ASSETS}/source-inputs.csv']=data.INPUT.read_bytes().replace(b'\r\n',b'\n')
 result[f'{ASSETS}/calculations.csv']=data.calculations_csv().encode()
 for kind in ('denominators','discrepancy'):
  for lang in ('es','en'):
   for suffix in ('','-mobile'):
    name=f'spain-{kind}-{lang}{suffix}.svg';result[f'{ASSETS}/{name}']=(FOLDER/name).read_bytes()
 # Reuse the established design without modifying the approved prior bundle.
 css=(data.ROOT/'drafts/energy-flows-20261025/candidate/assets/research/energy-flows-20261025/energy-editorial.css').read_text(encoding='utf-8')+'\n.channels{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin:35px 0}.channels section{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:22px}.channels p{font-size:16px}.channels h3{color:var(--blue)}.table-wrap table{min-width:820px}picture img{max-width:100%}@media(max-width:760px){.channels{grid-template-columns:1fr}.channels section{padding:20px}.channels p{margin-bottom:12px}}\n'
 css+='picture img{aspect-ratio:24/11}@media(max-width:640px){picture img{aspect-ratio:4/5}}\n'
 result[f'{ASSETS}/spain-editorial.css']=css.encode();audit_payload(result);return result

def audit_payload(payload):
 for name,raw in payload.items():
  if name.endswith('.csv'):
   if name not in {f'{ASSETS}/{n}' for n in CSV_NAMES}:raise ValueError('Unexpected CSV route')
   for row in csv.reader(io.StringIO(raw.decode())):
    if any(cell.lstrip().startswith(('=','+','-','@')) and not re.fullmatch(r'[+-]?\d+(?:\.\d+)?',cell) for cell in row):raise ValueError('CSV formula injection')
  else:history.audit_payload({name:raw})

def manifest(payload):
 return {'kind':'third_original_editorial_draft','prepared_on':'2026-10-25','base_main':'63aba657f3cb269d0a686eec4b43dd5621c65fa9','publication_authorized':False,'human_editorial_approval':None,'reviewer':None,'reviewed_at':None,'advertising':False,'index':False,'proposed_institutional_byline':'Estrecho Ormuz','reconciliation':'Unresolved documentary discrepancy; no cause assigned','source_input_sha256_lf':data.sha(data.INPUT.read_bytes()),'sha256_lf':{n:data.sha(b) for n,b in sorted(payload.items())},'generator_sha256_lf':{n:data.sha((data.ROOT/n).read_bytes()) for n in ('spain_data.py','spain_editorial.py')},'editorial_input_sha256_lf':{n:data.sha((FOLDER/n).read_bytes()) for n in ('text-es.html','text-en.html','render_charts.py','chart-audit.json','source-verification.json','sources-and-rights.json')}}

def verify():
 payload=files()
 if {p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob('*') if p.is_file()}!=set(payload):raise ValueError('Draft selection changed')
 for name,raw in payload.items():
  if data.sha((SOURCE/name).read_bytes())!=data.sha(raw):raise ValueError('Draft bytes changed: '+name)
 if json.loads(MANIFEST.read_text(encoding='utf-8'))!=manifest(payload):raise ValueError('Draft manifest differs; no silent resealing')
 return payload

def preview():
 payload=verify();base=public.OUT;requested=FOLDER/'preview';out=requested.resolve()
 if requested.is_symlink() or out!=FOLDER.resolve()/'preview' or not out.is_relative_to(data.ROOT.resolve()):raise ValueError('Unsafe preview target')
 public.audit_public_build(base)
 before={p.relative_to(base).as_posix():data.sha(p.read_bytes()) for p in base.rglob('*') if p.is_file()}
 if set(payload)&set(before):raise ValueError('Unapproved third analysis in Pages')
 if out.exists():shutil.rmtree(out)
 shutil.copytree(base,out)
 for name,raw in payload.items():
  path=out/name;path.parent.mkdir(parents=True,exist_ok=True)
  if name.endswith('.html'):raw=public.sanitize_html(apply_policy(raw.decode(),name,programmatic_ads=False),name).encode()
  elif not public.copy_asset(Path(name)):raise ValueError('Preview asset not explicitly selected: '+name)
  path.write_bytes(raw)
 for lang,names in {'es':('index.html','analisis.html'),'en':('en.html','en-analysis.html')}.items():
  label='Tercer análisis: borrador pendiente de revisión' if lang=='es' else 'Third analysis: draft awaiting review'
  block=f'<aside data-spain-draft><h2><a href="/{ARTICLES[lang]}">{label}</a></h2></aside>'
  for name in names:
   path=out/name;path.write_text(path.read_text(encoding='utf-8').replace('</main>',block+'</main>',1),encoding='utf-8',newline='\n')
 public.write_sitemap(out);public.audit_public_build(out);errors=check_links(out)
 if errors:raise ValueError('\n'.join(errors))
 if before!={p.relative_to(base).as_posix():data.sha(p.read_bytes()) for p in base.rglob('*') if p.is_file()}:raise ValueError('Normal Pages artifact changed')
 report={'kind':'local_only_third_original_preview','publication_authorized':False,'human_review':None,'default_pages_artifact_unchanged':True,'advertising':False,'link_errors':errors,'sha256_lf':{n:data.sha((out/n).read_bytes()) for n in payload},'full_artifact_sha256_lf':{p.relative_to(out).as_posix():data.sha(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()}}
 (FOLDER/'preview-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Local third draft built; normal Pages unchanged; four HTML noindex; ads/privacy/links passed.')

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);g=parser.add_mutually_exclusive_group(required=True);g.add_argument('--write',action='store_true');g.add_argument('--check',action='store_true');g.add_argument('--build-preview',action='store_true');args=parser.parse_args()
 if args.write:
  payload=files()
  for name,raw in payload.items():
   path=SOURCE/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
  MANIFEST.write_text(json.dumps(manifest(payload),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 elif args.check:verify();print('Third draft: selected facts, formulas, resources and unapproved manifest verified.')
 else:preview()
