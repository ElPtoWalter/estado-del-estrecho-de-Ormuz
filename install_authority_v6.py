#!/usr/bin/env python3
from __future__ import annotations
import argparse,ast,json,re,shutil,subprocess,sys,zipfile
from datetime import date
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parent
PAYLOAD_ZIP=ROOT/"authority_v6_payload.zip"
MARKER="ORMUZ_AUTHORITY_V6"

class InstallError(RuntimeError):pass

def stable(path:Path,text:str):
    old=path.read_text(encoding="utf-8") if path.exists() else None
    if old!=text:path.write_text(text,encoding="utf-8")

def ensure_css(text:str)->str:
    if 'href="/authority-v6.css"' in text or "href='/authority-v6.css'" in text:return text
    return re.sub(r'</head>','<link rel="stylesheet" href="/authority-v6.css"/>\n</head>',text,count=1,flags=re.I)

def is_en(text:str)->bool:return bool(re.search(r'<html\b[^>]*lang=["\']en',text,re.I))

def extract_payload():
    if not PAYLOAD_ZIP.exists():raise InstallError("authority_v6_payload.zip is missing")
    with zipfile.ZipFile(PAYLOAD_ZIP) as z:
        bad=[n for n in z.namelist() if n.startswith('/') or '..' in Path(n).parts]
        if bad:raise InstallError(f"Unsafe payload paths: {bad}")
        z.extractall(ROOT)

def insert_between(text:str,start:str,end:str,block:str)->str:
    pattern=re.compile(re.escape(start)+r'.*?'+re.escape(end),re.S)
    if pattern.search(text):return pattern.sub(block,text,count=1)
    return text

def patch_home(path:Path):
    if not path.exists():return
    text=path.read_text(encoding="utf-8");text=ensure_css(text);en=is_en(text)
    block=(ROOT/("home_en.html" if en else "home_es.html")).read_text(encoding="utf-8")
    if "<!-- ORMUZ_AUTHORITY_V6_HOME_START -->" in text:
        text=insert_between(text,"<!-- ORMUZ_AUTHORITY_V6_HOME_START -->","<!-- ORMUZ_AUTHORITY_V6_HOME_END -->",block)
    else:
        anchor='<!-- HOME_V11_ANALYSIS_END -->'
        if anchor in text:text=text.replace(anchor,anchor+'\n'+block,1)
        else:text=text.replace('</main>',block+'\n</main>',1)
    stable(path,text)

def patch_analysis(path:Path):
    if not path.exists():return
    text=path.read_text(encoding="utf-8");text=ensure_css(text);en=is_en(text)
    block=(ROOT/("cards_en.html" if en else "cards_es.html")).read_text(encoding="utf-8")
    if "<!-- ORMUZ_AUTHORITY_V6_CARDS_START -->" in text:
        text=insert_between(text,"<!-- ORMUZ_AUTHORITY_V6_CARDS_START -->","<!-- ORMUZ_AUTHORITY_V6_CARDS_END -->",block)
    elif "<!-- ORMUZ_GROWTH_V4_CARDS_END -->" in text:
        text=text.replace("<!-- ORMUZ_GROWTH_V4_CARDS_END -->","<!-- ORMUZ_GROWTH_V4_CARDS_END -->"+block,1)
    else:
        m=re.search(r'(<div class=["\']analysis-grid-v11["\'][^>]*>)(.*?)(</div>)',text,re.I|re.S)
        if not m:raise InstallError(f"Could not locate analysis grid in {path.name}")
        text=text[:m.start(3)]+block+text[m.start(3):]
    text=re.sub(r'<strong>\s*10\s+(análisis publicados|analyses published)\s*</strong>',lambda m:'<strong>'+('16 análisis publicados' if not en else '16 analyses published')+'</strong>',text,count=1,flags=re.I)
    stable(path,text)

def patch_about(path:Path):
    if not path.exists():return
    text=path.read_text(encoding="utf-8");text=ensure_css(text);en=is_en(text)
    marker='<!-- ORMUZ_AUTHORITY_V6_ABOUT -->'
    if marker in text:return
    block=(marker+'<section class="content-section a6-note"><h2>'+('Más transparencia editorial' if not en else 'More editorial transparency')+'</h2><p>'+('Consulta quién publica, cómo se usa la automatización y cómo se documentan las correcciones.' if not en else 'See who publishes, how automation is used and how corrections are documented.')+'</p><p><a class="button primary" href="/'+('equipo-editorial.html' if not en else 'en-editorial-team.html')+'">'+('Equipo editorial' if not en else 'Editorial team')+'</a> <a class="button" href="/'+('correcciones.html' if not en else 'en-corrections.html')+'">'+('Correcciones' if not en else 'Corrections')+'</a></p></section>')
    text=text.replace('</main>',block+'</main>',1);stable(path,text)

def patch_installer():
    path=ROOT/'install_v11.py'
    if not path.exists():return
    source=path.read_text(encoding='utf-8')
    if 'from build_authority_report import build_reports' in source:return
    anchor='    for path in ROOT.glob("*.html"):\n'
    if anchor not in source:raise InstallError('Could not find install_v11 main loop')
    hook='''    try:\n        from build_authority_report import build_reports\n        build_reports(ROOT)\n    except Exception as exc:\n        print(f"AVISO: informe Authority V6 no generado: {exc}")\n\n'''
    source=source.replace(anchor,hook+anchor,1)
    compile(source,str(path),'exec');stable(path,source)

def update_sitemap(urls:list[str]):
    path=ROOT/'sitemap.xml'
    if not path.exists():return
    text=path.read_text(encoding='utf-8');blocks=[];today=date.today().isoformat()
    for rel in urls:
        url='https://estrechoormuz.com/'+rel
        if url in text:continue
        blocks.append(f'  <url>\n    <loc>{url}</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>{"0.8" if "research" in rel or "investigacion" in rel else "0.7"}</priority>\n  </url>\n')
    if blocks:
        if '</urlset>' not in text:raise InstallError('Invalid sitemap: missing </urlset>')
        text=text.replace('</urlset>',''.join(blocks)+'</urlset>',1);stable(path,text)

def remove_helpers():
    for name in ('home_es.html','home_en.html','cards_es.html','cards_en.html'):
        p=ROOT/name
        if p.exists():p.unlink()

def visible_words(text:str)->int:
    text=re.sub(r'<script\b.*?</script>',' ',text,flags=re.I|re.S);text=re.sub(r'<style\b.*?</style>',' ',text,flags=re.I|re.S);text=re.sub(r'<[^>]+>',' ',text)
    return len(re.findall(r'\b[\wÀ-ÿ\'-]+\b',text))

def validate(manifest:dict[str,Any]):
    errors=[];report={'version':6,'pages':{},'errors':errors}
    for rel in manifest['pages']:
        p=ROOT/rel
        if not p.exists():errors.append(f'missing {rel}');continue
        text=p.read_text(encoding='utf-8');words=visible_words(text);report['pages'][rel]={'words':words,'article_schema':'AnalysisNewsArticle' in text,'canonical':bool(re.search(r'<link[^>]+rel=["\']canonical',text,re.I))}
        if rel in manifest['articles_es']+manifest['articles_en'] and words<650:errors.append(f'{rel}: only {words} visible words')
        if '</html>' not in text.lower():errors.append(f'{rel}: incomplete HTML')
    for rel in ('index.html','en.html','analisis.html','en-analysis.html'):
        p=ROOT/rel
        if p.exists() and 'authority-v6.css' not in p.read_text(encoding='utf-8'):errors.append(f'{rel}: missing authority CSS')
    report['ready']=not errors;stable(ROOT/'authority-v6-readiness.json',json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if errors:raise InstallError(' | '.join(errors))

def main():
    extract_payload();manifest=json.loads((ROOT/'authority-v6-manifest.json').read_text(encoding='utf-8'))
    # Generate original-data reports before page validation.
    from build_authority_report import build_reports
    build_reports(ROOT)
    for name in ('index.html','en.html'):patch_home(ROOT/name)
    for name in ('analisis.html','en-analysis.html'):patch_analysis(ROOT/name)
    for name in ('sobre.html','en-about.html'):patch_about(ROOT/name)
    for p in ROOT.glob('*.html'):
        if p.name in manifest['pages']:stable(p,ensure_css(p.read_text(encoding='utf-8')))
    patch_installer();update_sitemap(manifest['pages']);remove_helpers();validate(manifest)
    print('ORMUZ AUTHORITY V6 INSTALLED AND VALIDATED')
    return 0

if __name__=='__main__':raise SystemExit(main())
