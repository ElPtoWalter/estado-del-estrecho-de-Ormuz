"""Exact PR #24 public candidate. Local build only; never merges or deploys."""
import argparse,json,re
import xml.etree.ElementTree as ET
import spain_data as data
import spain_editorial as candidate
import build_public_site as public
import build_sitemap as sitemap
from check_public_links import check as check_links
from publication_quality import (SPAIN_ARTICLES,SPAIN_METHODS,SPAIN_NO_ADS,
    SPAIN_APPROVED_COMMIT,SPAIN_APPROVED_MANIFEST,SPAIN_APPROVAL_REFERENCE,
    owner_spain_review_valid,apply_policy)

RECORD=data.ROOT/'docs/spain-release-20261026.json'
REPORT=candidate.FOLDER/'release-build-audit.json'


def verify(reviews=None):
    files=candidate.verify()
    if data.sha(candidate.MANIFEST.read_bytes())!=SPAIN_APPROVED_MANIFEST:
        raise ValueError('Approved 21123ca1 manifest changed')
    record=json.loads(RECORD.read_text(encoding='utf-8'))
    if (record.get('approved_candidate_commit')!=SPAIN_APPROVED_COMMIT
            or record.get('kind')!='publisher_approved_spain_release_preparation'
            or record.get('approved_manifest_sha256_lf')!=SPAIN_APPROVED_MANIFEST
            or record.get('approval_reference')!=SPAIN_APPROVAL_REFERENCE
            or record.get('approval_date')!='2026-10-25'
            or record.get('evidence_recorded_at')!='2026-10-26T08:38:42Z'
            or record.get('authorised_factual_article_edits')!=[]
            or record.get('public_author')!='Estrecho Ormuz'
            or any(record.get(k) is not False for k in ('merge_authorized','deployment_authorized','advertising_authorized','personal_data_publication_authorized'))
            or record.get('sha256_lf')!={n:data.sha(b) for n,b in sorted(files.items())}):
        raise ValueError('Spain release decision differs from approved scope or bundle')
    if reviews is None:reviews=json.loads((data.ROOT/'editorial-reviews.json').read_text(encoding='utf-8'))
    for name in SPAIN_NO_ADS:
        review=reviews.get(name) if isinstance(reviews,dict) else None
        if not owner_spain_review_valid(files[name].decode('utf-8'),review) or review.get('document')!=name:
            raise ValueError('Missing exact Spain approval: '+name)
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
        title='España y Europa ante Ormuz: qué mide cada cuota' if lang=='es' else 'Spain, Europe and Hormuz: what each share measures'
        note='Análisis original de estadísticas de gas de 2025 · Enagás y Eurostat' if lang=='es' else 'Original analysis of 2025 gas statistics · Enagás and Eurostat'
        block=f'<aside class="content-section prose-card" data-spain-analysis><h2><a href="/{candidate.ARTICLES[lang]}">{title}</a></h2><p>{note}</p></aside>'
        for name in names:
            path=root/name;text=path.read_text(encoding='utf-8')
            text=re.sub(r'<aside\b[^>]*\bdata-spain-analysis[^>]*>.*?</aside>','',text,flags=re.S)
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
            errors.append('Spain release bytes differ: '+name);continue
        if not name.endswith('.html'):continue
        text=path.read_text(encoding='utf-8');meta=sitemap.MetaParser();meta.feed(text)
        if meta.canonical!=public.DOMAIN+'/'+name:errors.append('Canonical: '+name)
        if ('noindex' in meta.robots)!=(name in SPAIN_METHODS):errors.append('Indexability: '+name)
        for pair in (candidate.ARTICLES,candidate.METHODS):
            if name in pair.values() and meta.alternates!={k:public.DOMAIN+'/'+v for k,v in {**pair,'x-default':pair['es']}.items()}:errors.append('Hreflang: '+name)
        for csv_name in candidate.CSV_NAMES:
            if len(re.findall(r'<a\b[^>]*href="/'+re.escape(candidate.ASSETS+'/'+csv_name)+'"',text))!=1:errors.append('CSV download count: '+name)
        if name in SPAIN_ARTICLES:
            if 'data-institutional-byline' not in text or '<meta name="author" content="Estrecho Ormuz">' not in text:errors.append('Byline: '+name)
            # The presentation transition makes no edits inside the factual article.
            original=files[name].decode().split('<article>',1)[1].split('</article>',1)[0]
            rendered=text.split('<article>',1)[1].split('</article>',1)[0]
            if original!=rendered:errors.append('Approved article body changed: '+name)
        if (re.search(r'Borrador|Draft for editorial|Publication not authorised|Publicación no autorizada|data-draft-disclosure|Eduardo|ElPtoWalter|adsbygoogle|mailto:',text,re.I)
                or 'publisher-ads" content="disabled' not in text):errors.append('Publication/privacy/ads boundary: '+name)
        if name in SPAIN_METHODS:
            required=('Discrepancia documental no resuelta','no acredita una autorización específica de Enagás ni una revisión jurídica independiente') if not name.startswith('en-') else ('Unresolved documentary discrepancy','neither specific permission from Enagás nor independent legal clearance')
            if not all(phrase in text for phrase in required):errors.append('Unresolved discrepancy/legal limits missing: '+name)
    tree=ET.parse(root/'sitemap.xml')
    urls={n.find(sitemap.qname(sitemap.SITEMAP_NS,'loc')).text for n in tree.getroot()}
    for name in SPAIN_NO_ADS:
        if ((public.DOMAIN+'/'+name) in urls)!=(name in SPAIN_ARTICLES):errors.append('Sitemap: '+name)
    for lang,names in {'es':('index.html','analisis.html','historial.html'),'en':('en.html','en-analysis.html','en-history.html')}.items():
        for name in names:
            if f'href="/{candidate.ARTICLES[lang]}"' not in (root/name).read_text(encoding='utf-8'):errors.append('Navigation: '+name)
    errors.extend(check_links(root))
    if errors:raise ValueError('\n'.join(errors))
    result={'kind':'exact_spain_publication_candidate','approved_candidate_commit':SPAIN_APPROVED_COMMIT,
            'approval_reference':SPAIN_APPROVAL_REFERENCE,'merge_authorized':False,'deployment_authorized':False,
            'public_author':'Estrecho Ormuz','advertising':False,'indexable':sorted(SPAIN_ARTICLES),'accessible_noindex':sorted(SPAIN_METHODS),
            'sitemap_count':len(urls),'link_errors':errors,
            'sha256_lf':{n:data.sha(b) for n,b in sorted(expected.items())},
            'full_artifact_sha256_lf':{p.relative_to(root).as_posix():data.sha(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}}
    REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true',required=True);parser.parse_args()
    verify();print('Exact Spain candidate approval, original hashes and limited release scope verified.')
