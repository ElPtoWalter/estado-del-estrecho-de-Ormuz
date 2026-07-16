#!/usr/bin/env python3
"""Instalación idempotente de las mejoras V11 sobre el repositorio existente."""
from __future__ import annotations
from pathlib import Path

ROOT=Path(__file__).resolve().parent
NEW_URLS=[
 ("parte-diario.html","daily","0.95"),("en-daily-brief.html","daily","0.95"),
 ("paises-dependen-mas-estrecho-ormuz.html","monthly","0.90"),
 ("en-countries-most-dependent-on-strait-of-hormuz.html","monthly","0.90"),
 ("por-que-qatar-no-puede-desviar-gnl-ormuz.html","monthly","0.90"),
 ("en-why-qatar-cannot-reroute-lng-around-hormuz.html","monthly","0.90"),
 ("como-afecta-ormuz-espana-europa.html","monthly","0.90"),
 ("en-how-hormuz-affects-spain-europe.html","monthly","0.90"),
 ("media-kit.html","monthly","0.55"),("en-media-kit.html","monthly","0.55")
]
ARTICLES_ES=["que-significa-cierre-estrecho-ormuz.html","como-afectaria-cierre-ormuz-petroleo-gas-economia.html","como-comprobar-trafico-maritimo-operativo-ormuz.html","rutas-alternativas-cierre-estrecho-ormuz-capacidad.html"]
ARTICLES_EN=["en-what-does-closing-strait-of-hormuz-mean.html","en-how-hormuz-closure-affects-oil-gas-economy.html","en-how-to-verify-operational-maritime-traffic-hormuz.html","en-alternative-routes-strait-of-hormuz-closure-capacity.html"]

def stable_write(path:Path,text:str)->None:
    previous=path.read_text(encoding="utf-8") if path.exists() else None
    if previous!=text:path.write_text(text,encoding="utf-8")

def ensure_assets_and_nav(path:Path)->None:
    text=path.read_text(encoding="utf-8")
    is_en='lang="en"' in text or "lang='en'" in text
    if "/v11.css" not in text and "</head>" in text:
        text=text.replace("</head>",'<link href="/v11.css" rel="stylesheet"/>\n</head>',1)
    anchor='<a href="/en-history.html">History</a>' if is_en else '<a href="/historial.html">Historial</a>'
    label="Daily brief" if is_en else "Parte diario"
    addition=anchor+('<a href="/en-daily-brief.html">Daily brief</a>' if is_en else '<a href="/parte-diario.html">Parte diario</a>')
    if anchor in text and label not in text:text=text.replace(anchor,addition,1)
    stable_write(path,text)

def patch_home(path:Path,is_en:bool)->None:
    text=path.read_text(encoding="utf-8")
    if "V11_DAILY_BRIEF_TEASER" in text:return
    block='''<!-- V11_DAILY_BRIEF_TEASER -->
<section class="content-section v11-panel">
  <span class="section-kicker">Daily operational briefing</span>
  <h2>A concise daily brief, generated from the verified status</h2>
  <p>Status, material changes, selected evidence and the next signals to watch, without turning every headline into an alert.</p>
  <div class="hero-actions"><a class="button primary" href="/en-daily-brief.html">Open daily brief</a><a class="button" href="/panel-x.html">Editorial X panel</a></div>
</section>
''' if is_en else '''<!-- V11_DAILY_BRIEF_TEASER -->
<section class="content-section v11-panel">
  <span class="section-kicker">Informe operativo diario</span>
  <h2>Un parte conciso generado desde el estado verificado</h2>
  <p>Situación, cambios materiales, evidencias seleccionadas y próximas señales a vigilar, sin convertir cada titular en una alerta.</p>
  <div class="hero-actions"><a class="button primary" href="/parte-diario.html">Abrir parte diario</a><a class="button" href="/panel-x.html">Panel editorial de X</a></div>
</section>
'''
    for token in ('<section aria-labelledby="faq-title"','<section class="content-section sponsor-band">','</main>'):
        if token in text:
            stable_write(path,text.replace(token,block+token,1));return

def patch_article(path:Path,is_en:bool)->None:
    text=path.read_text(encoding="utf-8")
    if "V11_EDITORIAL_TRANSPARENCY" in text or "</main>" not in text:return
    box='''<!-- V11_EDITORIAL_TRANSPARENCY -->
<section class="editorial-transparency">
  <span class="section-kicker">Editorial record</span><h2>Traceability and corrections</h2>
  <dl><dt>Author</dt><dd>Estrecho Ormuz Editorial Team</dd><dt>Review</dt><dd>Reviewed when operational evidence or source data materially changes.</dd><dt>Method</dt><dd>Facts, inferences and scenarios are separated. Primary sources are prioritised.</dd><dt>Corrections</dt><dd><a href="/en-contact.html">Send a documented correction</a>.</dd></dl>
  <div class="related-v11"><a href="/en-countries-most-dependent-on-strait-of-hormuz.html">Countries most exposed to Hormuz</a><a href="/en-why-qatar-cannot-reroute-lng-around-hormuz.html">Why Qatari LNG cannot bypass Hormuz</a><a href="/en-how-hormuz-affects-spain-europe.html">Impact on Spain and Europe</a></div>
</section>
''' if is_en else '''<!-- V11_EDITORIAL_TRANSPARENCY -->
<section class="editorial-transparency">
  <span class="section-kicker">Ficha editorial</span><h2>Trazabilidad y correcciones</h2>
  <dl><dt>Autoría</dt><dd>Equipo editorial de Estrecho Ormuz</dd><dt>Revisión</dt><dd>Se revisa cuando cambian materialmente las evidencias operativas o los datos fuente.</dd><dt>Método</dt><dd>Se separan hechos, inferencias y escenarios. Se priorizan fuentes primarias.</dd><dt>Correcciones</dt><dd><a href="/contacto.html">Enviar una corrección documentada</a>.</dd></dl>
  <div class="related-v11"><a href="/paises-dependen-mas-estrecho-ormuz.html">Países más expuestos a Ormuz</a><a href="/por-que-qatar-no-puede-desviar-gnl-ormuz.html">Por qué el GNL catarí no puede evitar Ormuz</a><a href="/como-afecta-ormuz-espana-europa.html">Impacto en España y Europa</a></div>
</section>
'''
    stable_write(path,text.replace("</main>",box+"</main>",1))

def update_sitemap()->None:
    path=ROOT/"sitemap.xml"
    if not path.exists():return
    text=path.read_text(encoding="utf-8");blocks=[]
    for rel,freq,priority in NEW_URLS:
        absolute=f"https://estrechoormuz.com/{rel}"
        if absolute in text:continue
        blocks.append(f"  <url>\n    <loc>{absolute}</loc>\n    <lastmod>2026-07-17</lastmod>\n    <changefreq>{freq}</changefreq>\n    <priority>{priority}</priority>\n  </url>\n")
    if blocks and "</urlset>" in text:stable_write(path,text.replace("</urlset>","".join(blocks)+"</urlset>",1))

def update_text_files()->None:
    robots=ROOT/"robots.txt"
    if robots.exists():
        text=robots.read_text(encoding="utf-8")
        if "Disallow: /panel-x.html" not in text:stable_write(robots,text.rstrip()+"\nDisallow: /panel-x.html\n")
    llms=ROOT/"llms.txt"
    if llms.exists():
        text=llms.read_text(encoding="utf-8")
        if "## V11 · partes y nuevos análisis" not in text:
            stable_write(llms,text.rstrip()+'''\n\n## V11 · partes y nuevos análisis
- Parte diario: https://estrechoormuz.com/parte-diario.html
- Daily brief: https://estrechoormuz.com/en-daily-brief.html
- Países más dependientes: https://estrechoormuz.com/paises-dependen-mas-estrecho-ormuz.html
- GNL de Catar y Ormuz: https://estrechoormuz.com/por-que-qatar-no-puede-desviar-gnl-ormuz.html
- España y Europa: https://estrechoormuz.com/como-afecta-ormuz-espana-europa.html
''')

def main()->int:
    for path in ROOT.glob("*.html"):ensure_assets_and_nav(path)
    for name in ("index.html","en.html"):
        path=ROOT/name
        if path.exists():patch_home(path,name=="en.html")
    for name in ARTICLES_ES:
        path=ROOT/name
        if path.exists():patch_article(path,False)
    for name in ARTICLES_EN:
        path=ROOT/name
        if path.exists():patch_article(path,True)
    update_sitemap();update_text_files()
    print("V11 instalada de forma idempotente.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
