"""Presentation-only SEO for the two homepages and analysis indexes.

No assessment, approved article, source data or monetization decision is edited.
Applied after the three sealed publications, so automated source updates survive.
"""
from __future__ import annotations
import argparse
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit
import build_sitemap as sitemap

DOMAIN='https://estrechoormuz.com'
PAGES={'index.html':('es','home'),'en.html':('en','home'),
       'analisis.html':('es','analysis'),'en-analysis.html':('en','analysis')}
RESEARCH={
 'es':[
  ('historiales-monitor-ormuz.html','Historiales del monitor','Registros del sistema y observaciones de tráfico son cosas distintas.','Archivos congelados · fuentes y CSV'),
  ('ormuz-cierre-paso-flujos.html','Cierre, paso y flujos de energía','Seis trimestres de la EIA para distinguir travesías, volúmenes y restricciones.','2025T1–2026T2 · fuentes y CSV'),
  ('espana-europa-ormuz-dos-porcentajes.html','España y Europa: qué mide cada cuota','Gas físico, valor de importación y una discrepancia documental sin resolver.','Estadísticas de 2025 · Enagás y Eurostat')],
 'en':[
  ('en-monitor-archives-hormuz.html','Monitor archives and their limits','System records and observations of vessel traffic measure different things.','Frozen archives · sources and CSV'),
  ('en-hormuz-closure-passage-flows.html','Closure, passage and energy flows','Six EIA quarters distinguish vessel passage, energy volumes and restrictions.','2025 Q1–2026 Q2 · sources and CSV'),
  ('en-spain-europe-hormuz-two-percentages.html','Spain and Europe: what each share measures','Physical gas, import value and an unresolved documentary discrepancy.','2025 statistics · Enagás and Eurostat')]}
COPY={
 ('es','home'):('Estrecho de Ormuz hoy: estado y fuentes | Estrecho Ormuz',
  'Consulta la última evaluación del paso por Ormuz, su fecha, confianza y fuentes. El monitor no ofrece un recuento completo de buques ni mediciones AIS propias.',
  'Estrecho de Ormuz hoy: estado y evidencias'),
 ('en','home'):('Strait of Hormuz status today | Estrecho Ormuz',
  'Read the latest Hormuz passage assessment, its timestamp, confidence and sources. The monitor does not count every ship or provide its own AIS measurements.',
  'Strait of Hormuz today: status and evidence'),
 ('es','analysis'):('Análisis de Ormuz: datos, métodos y contexto | Estrecho Ormuz',
  'Tres investigaciones originales sobre los historiales de Ormuz, los flujos de energía y el gas de España y Europa, con fuentes, CSV, gráficos y límites.',
  'Análisis de Ormuz: datos, métodos y contexto'),
 ('en','analysis'):('Hormuz analysis: data, methods and context | Estrecho Ormuz',
  'Three original investigations into Hormuz monitor archives, energy flows and gas in Spain and Europe, with sources, CSV data, charts and explicit limits.',
  'Hormuz analysis: data, methods and context')}
STYLE='''
.seo-research{scroll-margin-top:100px}.seo-research-head{display:flex;gap:20px;align-items:start;justify-content:space-between}.seo-research-head h2{margin-top:6px}.seo-research-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-top:22px}.seo-research-card{min-width:0;padding:22px;border:1px solid var(--line);border-radius:18px;background:rgba(255,255,255,.025)}.seo-research-card h3{margin:8px 0 12px;font-size:1.3rem;line-height:1.35}.seo-research-card a{display:block;padding:8px 0;color:var(--text);text-decoration:underline;text-underline-offset:4px}.seo-research-card a:focus-visible{outline:3px solid #67cde3;outline-offset:5px}.seo-research-card p{line-height:1.65}.seo-research-card small{display:block;line-height:1.6;color:var(--muted)}.seo-research-intro{max-width:74ch}.seo-scope-note{max-width:78ch;font-size:.95rem;line-height:1.65;color:var(--muted)}@media(max-width:700px){.seo-research-grid{grid-template-columns:1fr}.seo-research-head{display:block}.seo-research-card{padding:18px}.seo-research{scroll-margin-top:84px}}
.seo-research-jump{display:inline-block;min-height:44px;padding:10px 0;margin-top:4px;font-weight:700;text-decoration:underline;text-underline-offset:4px}.seo-research-jump:focus-visible{outline:3px solid #67cde3;outline-offset:5px}
'''.strip()


class Regions(HTMLParser):
    """Offsets of balanced sections/asides; nested divs do not truncate them."""
    def __init__(self,text):
        super().__init__();self.text=text;self.lines=[0];self.stack=[];self.nodes=[]
        for m in re.finditer('\n',text):self.lines.append(m.end())
        self.feed(text)
    def source_offset(self):
        line,col=self.getpos();return self.lines[line-1]+col
    def handle_starttag(self,tag,attrs):
        if tag in ('section','aside'):self.stack.append((tag,dict(attrs),self.source_offset()))
    def handle_endtag(self,tag):
        if tag not in ('section','aside'):return
        if not self.stack or self.stack[-1][0]!=tag:raise ValueError('Unbalanced presentation region')
        start,attrs,pos=self.stack.pop();self.nodes.append((pos,self.source_offset()+len(tag)+3,tag,attrs))


def attributes(tag):
    class Attrs(HTMLParser):
        def handle_starttag(self,t,attrs):self.attrs=dict(attrs)
    p=Attrs();p.feed(tag);return getattr(p,'attrs',{})


def research_section(lang):
    es=lang=='es';anchor='investigaciones-originales' if es else 'original-research'
    heading='Tres investigaciones originales' if es else 'Three original investigations'
    intro=('Fuentes identificadas, períodos visibles y datos reproducibles. Cada investigación explica qué puede concluir y qué queda fuera de sus datos.' if es else
           'Identified sources, explicit periods and reproducible data. Each investigation explains what its evidence supports and what falls outside it.')
    cards=''.join(f'<article class="seo-research-card"><small>{i:02d} · {html.escape(note)}</small><h3><a href="/{path}">{html.escape(title)}</a></h3><p>{html.escape(desc)}</p></article>' for i,(path,title,desc,note) in enumerate(RESEARCH[lang],1))
    return f'<section class="content-section seo-research" data-seo-research id="{anchor}" aria-labelledby="{anchor}-title"><div class="seo-research-head"><div><p class="section-kicker">{"Datos y contexto" if es else "Data and context"}</p><h2 id="{anchor}-title">{heading}</h2></div></div><p class="seo-research-intro">{intro}</p><div class="seo-research-grid">{cards}</div></section>'


def transform(document,name):
    if name not in PAGES:return document
    lang,kind=PAGES[name];title,description,h1=COPY[lang,kind]
    # Reapplying is safe; the original incoming links are consolidated, not lost.
    had_section='data-seo-research' in document
    cuts=[];found=set()
    for start,end,tag,attrs in Regions(document).nodes:
        text=document[start:end]
        if 'data-seo-research' in attrs:cuts.append((start,end))
        elif tag=='aside':
            paths={p for p,*_ in RESEARCH[lang] if f'href="/{p}"' in text}
            if paths:found.update(paths);cuts.append((start,end))
    if not had_section and len(found)!=3:raise ValueError('Expected three approved incoming research links: '+name)
    for start,end in sorted(cuts,reverse=True):document=document[:start]+document[end:]
    document=re.sub(r'<style\b[^>]*data-seo-surface[^>]*>.*?</style>','',document,flags=re.S)
    document=re.sub(r'<a\b[^>]*data-seo-jump[^>]*>.*?</a>','',document,flags=re.S)
    document=re.sub(r'<p\b[^>]*data-seo-scope[^>]*>.*?</p>','',document,flags=re.S)
    document=re.sub(r'<title>.*?</title>',lambda m:'<title>'+html.escape(title)+'</title>',document,count=1,flags=re.S)
    descriptions={'description','og:description','twitter:description'}
    titles={'og:title','twitter:title'}
    def meta(m):
        d=attributes(m[0]);key=d.get('name',d.get('property',''))
        if key not in descriptions|titles:return m[0]
        content=title if key in titles else description
        attr='property' if 'property' in d else 'name'
        return f'<meta {attr}="{key}" content="{html.escape(content,quote=True)}">'
    document=re.sub(r'<meta\b[^>]*>',meta,document,flags=re.I)
    def jsonld(m):
        value=json.loads(m[2])
        def walk(v):
            if isinstance(v,list):return [walk(x) for x in v]
            if not isinstance(v,dict):return v
            v={k:walk(x) for k,x in v.items()}
            if v.get('@type')=='WebPage':v.update(name=title,description=description)
            return v
        return m[1]+json.dumps(walk(value),ensure_ascii=False,separators=(',',':'))+m[3]
    document=re.sub(r'(<script\b[^>]*type="application/ld\+json"[^>]*>)(.*?)(</script>)',jsonld,document,flags=re.S)
    document=re.sub(r'<h1\b[^>]*>.*?</h1>',lambda m:'<h1>'+html.escape(h1)+'</h1>',document,count=1,flags=re.S)
    es_page='index.html' if kind=='home' else 'analisis.html'
    en_page='en.html' if kind=='home' else 'en-analysis.html'
    urls={'es':DOMAIN+('/' if kind=='home' else '/'+es_page),'en':DOMAIN+'/'+en_page}
    def link(m):
        d=attributes(m[0]);rel=d.get('rel','').split()
        return '' if 'canonical' in rel or ('alternate' in rel and 'hreflang' in d) else m[0]
    document=re.sub(r'<link\b[^>]*>',link,document,flags=re.I)
    head=f'<link rel="canonical" href="{urls[lang]}">'+''.join(f'<link rel="alternate" hreflang="{k}" href="{v}">' for k,v in {**urls,'x-default':urls['es']}.items())+f'<style data-seo-surface>{STYLE}</style>'
    document=document.replace('</head>',head+'</head>',1)
    other=urls['en' if lang=='es' else 'es'].removeprefix(DOMAIN)
    document=re.sub(r'(<a\b[^>]*class="[^"]*\blanguage-link\b[^"]*"[^>]*href=")[^"]*(")',lambda m:m[1]+other+m[2],document)
    document=re.sub(r'(<a\b[^>]*href=")[^"]*("[^>]*class="[^"]*\blanguage-link\b[^"]*")',lambda m:m[1]+other+m[2],document)
    if kind=='home':
        jump='Investigaciones originales' if lang=='es' else 'Original investigations'
        anchor='investigaciones-originales' if lang=='es' else 'original-research'
        # The professional stylesheet deliberately hides .hero-actions. Keep the
        # research jump outside that existing container so it is keyboard-visible.
        document=re.sub(r'<div class="hero-actions">.*?</div>',lambda m:m[0]+f'<a class="seo-research-jump" data-seo-jump href="#{anchor}">{jump}</a>',document,count=1,flags=re.S)
        scope=('El indicador sintetiza fuentes fechadas y puede mantener incertidumbre. Los mapas AIS externos se cargan a petición; su cobertura puede ser incompleta y no son mediciones propias del observatorio.' if lang=='es' else
               'The indicator summarises dated sources and may retain uncertainty. External AIS maps load on request; their coverage may be incomplete and they are not the observatory’s own measurements.')
        document=re.sub(r'(<a\b[^>]*data-seo-jump[^>]*>.*?</a>)',lambda m:m[1]+f'<p class="seo-scope-note" data-seo-scope>{scope}</p>',document,count=1,flags=re.S)
    else:
        document=document.replace('16 análisis publicados','Guías e investigaciones').replace('16 published analyses','Guides and investigations')
    regions=Regions(document).nodes
    matches=[(a,b) for a,b,t,d in regions if t=='section' and (d.get('id')==('estado-actual' if lang=='es' else 'current-status') if kind=='home' else 'v11-hero' in d.get('class','').split())]
    if len(matches)!=1:raise ValueError('Missing exact research insertion point: '+name)
    end=matches[0][1];return document[:end]+research_section(lang)+document[end:]


def publish(root):
    for name in PAGES:
        path=root/name;path.write_text(transform(path.read_text(encoding='utf-8'),name),encoding='utf-8',newline='\n')


def audit(root):
    errors=[];pages={};warnings=[]
    for path in root.rglob('*.html'):
        p=sitemap.MetaParser();p.feed(path.read_text(encoding='utf-8'));pages[path.relative_to(root).as_posix()]=p
    locations=[n.find(sitemap.qname(sitemap.SITEMAP_NS,'loc')).text for n in ET.parse(root/'sitemap.xml').getroot()]
    for url in locations:
        name=urlsplit(url).path.lstrip('/') or 'index.html'
        if name.endswith('/'):name+='index.html'
        p=pages.get(name)
        if p is None or 'noindex' in p.robots or p.canonical!=url:errors.append('Invalid sitemap eligibility: '+url)
    for name,p in pages.items():
        if not p.canonical:continue
        for lang,url in p.alternates.items():
            if lang=='x-default':continue
            target=urlsplit(url).path.lstrip('/') or 'index.html'
            if target.endswith('/'):target+='index.html'
            q=pages.get(target)
            if not q or q.canonical!=url or q.lang!=lang or q.alternates.get(p.lang)!=p.canonical:
                (errors if name in PAGES else warnings).append('Alternate language mismatch: '+name+' -> '+url)
    for name,(lang,kind) in PAGES.items():
        text=(root/name).read_text(encoding='utf-8');p=pages[name]
        if text.count('data-seo-research')!=1:errors.append('Research section count: '+name)
        for article,*_ in RESEARCH[lang]:
            if text.count(f'href="/{article}"')!=1:errors.append('Research visibility/duplication: '+name+' '+article)
        if 'noindex' in p.robots:errors.append('Landing page blocked: '+name)
        expected=DOMAIN+('/' if name=='index.html' else '/'+name)
        if p.canonical!=expected:errors.append('Canonical mismatch: '+name)
        es=DOMAIN+('/' if kind=='home' else '/analisis.html')
        en=DOMAIN+('/en.html' if kind=='home' else '/en-analysis.html')
        if p.alternates!={'es':es,'en':en,'x-default':es}:errors.append('Hreflang cluster mismatch: '+name)
        if COPY[lang,kind][0] not in text or 'pagead/js/adsbygoogle.js' in text:errors.append('Metadata/ads boundary: '+name)
    if errors:raise ValueError('\n'.join(errors))
    return {'sitemap_urls':len(locations),'indexing_confirmed':False,'errors':errors,'existing_hreflang_warnings':warnings,'scope':list(PAGES),'private_search_console_exports_in_artifact':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path('_site'));args=parser.parse_args()
    print(json.dumps(audit(args.root),ensure_ascii=False,indent=2))
