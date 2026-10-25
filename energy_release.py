"""Exact PR #23 production candidate. Local build only; never merges or deploys."""
import argparse,json,re
from pathlib import Path
import xml.etree.ElementTree as ET
import energy_data as data
import energy_editorial as candidate
import build_public_site as public
import build_sitemap as sitemap
from check_public_links import check as check_links
from publication_quality import (ENERGY_ARTICLES,ENERGY_METHODS,ENERGY_NO_ADS,
    ENERGY_APPROVED_COMMIT,ENERGY_APPROVED_MANIFEST,ENERGY_APPROVAL_REFERENCE,
    owner_energy_review_valid,apply_policy)

RECORD=data.ROOT/'docs/energy-release-20261025.json'
REPORT=candidate.FOLDER/'release-build-audit.json'


def verify(reviews=None):
    files=candidate.verify()
    if data.sha(candidate.MANIFEST.read_bytes())!=ENERGY_APPROVED_MANIFEST:
        raise ValueError('Approved e40b057e manifest changed')
    record=json.loads(RECORD.read_text(encoding='utf-8'))
    if (record.get('approved_candidate_commit')!=ENERGY_APPROVED_COMMIT
            or record.get('approved_manifest_sha256_lf')!=ENERGY_APPROVED_MANIFEST
            or record.get('approval_reference')!=ENERGY_APPROVAL_REFERENCE
            or record.get('public_author')!='Estrecho Ormuz'
            or any(record.get(k) is not False for k in ('merge_authorized','deployment_authorized','advertising_authorized','personal_data_publication_authorized'))
            or record.get('sha256_lf')!={n:data.sha(b) for n,b in sorted(files.items())}):
        raise ValueError('Energy release decision differs from the approved scope or bundle')
    if reviews is None:reviews=json.loads((data.ROOT/'editorial-reviews.json').read_text(encoding='utf-8'))
    for name in ENERGY_NO_ADS:
        review=reviews.get(name) if isinstance(reviews,dict) else None
        if not owner_energy_review_valid(files[name].decode('utf-8'),review) or review.get('document')!=name:
            raise ValueError('Missing exact energy approval: '+name)
    return files,reviews


def render(files,reviews):
    result={}
    for name,raw in files.items():
        if name.endswith('.html'):
            text=apply_policy(raw.decode('utf-8'),name,programmatic_ads=False,review=reviews[name])
            result[name]=public.sanitize_html(text,name).encode('utf-8')
        else:result[name]=raw
    return result


def integrate(root):
    for lang,names in {'es':('index.html','analisis.html','historial.html'),
                       'en':('en.html','en-analysis.html','en-history.html')}.items():
        title='Cierre, paso y flujos: seis trimestres de la EIA' if lang=='es' else 'Closure, passage and flows: six EIA quarters'
        note='Análisis original de estimaciones históricas · 2025T1–2026T2' if lang=='es' else 'Original analysis of historical estimates · 2025 Q1–2026 Q2'
        block=f'<aside class="content-section prose-card" data-energy-analysis><h2><a href="/{candidate.ARTICLES[lang]}">{title}</a></h2><p>{note}</p></aside>'
        for name in names:
            path=root/name;text=path.read_text(encoding='utf-8')
            text=re.sub(r'<aside\b[^>]*\bdata-energy-analysis[^>]*>.*?</aside>','',text,flags=re.S)
            if '</main>' not in text:raise ValueError('Missing integration point: '+name)
            path.write_text(text.replace('</main>',block+'</main>',1),encoding='utf-8',newline='\n')


def publish(root,reviews):
    files,reviews=verify(reviews)
    for name,raw in render(files,reviews).items():
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    integrate(root)


def audit(root):
    files,reviews=verify();expected=render(files,reviews);errors=[]
    for name,raw in expected.items():
        path=root/name
        if not path.is_file() or data.sha(path.read_bytes())!=data.sha(raw):
            errors.append('Energy release bytes differ: '+name);continue
        if not name.endswith('.html'):continue
        text=path.read_text(encoding='utf-8');meta=sitemap.MetaParser();meta.feed(text)
        if meta.canonical!=public.DOMAIN+'/'+name:errors.append('Canonical: '+name)
        if ('noindex' in meta.robots)!=(name in ENERGY_METHODS):errors.append('Indexability: '+name)
        for pair in (candidate.ARTICLES,candidate.METHODS):
            if name in pair.values() and meta.alternates!={k:public.DOMAIN+'/'+v for k,v in {**pair,'x-default':pair['es']}.items()}:errors.append('Hreflang: '+name)
        if len(re.findall(r'<a\b[^>]*href="/assets/research/energy-flows-20261025/energy-series\.csv"',text))!=1:errors.append('CSV download count: '+name)
        if name in ENERGY_ARTICLES and ('data-context-guide' not in text or 'data-institutional-byline' not in text or '<meta name="author" content="Estrecho Ormuz">' not in text):errors.append('Guide/byline: '+name)
        if (re.search(r'Borrador|Draft for editorial|awaiting editorial approval|Sin autorización de publicación|Publication not authorised|data-draft-disclosure|Eduardo|ElPtoWalter|adsbygoogle|mailto:',text,re.I)
                or 'publisher-ads" content="disabled' not in text):errors.append('Publication/privacy/ads boundary: '+name)
    tree=ET.parse(root/'sitemap.xml')
    urls={n.find(sitemap.qname(sitemap.SITEMAP_NS,'loc')).text for n in tree.getroot()}
    for name in ENERGY_NO_ADS:
        if ((public.DOMAIN+'/'+name) in urls)!=(name in ENERGY_ARTICLES):errors.append('Sitemap: '+name)
    for lang,names in {'es':('index.html','analisis.html','historial.html'),'en':('en.html','en-analysis.html','en-history.html')}.items():
        for name in names:
            if f'href="/{candidate.ARTICLES[lang]}"' not in (root/name).read_text(encoding='utf-8'):errors.append('Navigation: '+name)
    errors.extend(check_links(root))
    if errors:raise ValueError('\n'.join(errors))
    result={'kind':'exact_energy_publication_candidate','approved_candidate_commit':ENERGY_APPROVED_COMMIT,
            'approval_reference':ENERGY_APPROVAL_REFERENCE,'merge_authorized':False,'deployment_authorized':False,
            'public_author':'Estrecho Ormuz','advertising':False,'indexable':sorted(ENERGY_ARTICLES),'accessible_noindex':sorted(ENERGY_METHODS),
            'sitemap_count':len(urls),'link_errors':errors,
            'sha256_lf':{n:data.sha(b) for n,b in sorted(expected.items())},
            'full_artifact_sha256_lf':{p.relative_to(root).as_posix():data.sha(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}}
    REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true',required=True);parser.parse_args()
    verify();print('Exact energy candidate approval, original hashes and limited release scope verified.')
