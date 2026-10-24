"""Render the exact owner-approved history bundle for a future Pages deployment.

This builds local bytes only. It cannot merge, deploy, or authorize advertising.
The original c01c7d96 candidate and its manifest remain unchanged for audit.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import history_public_candidate as candidate
import build_public_site as public
from check_public_links import check as check_links
from publication_quality import (HISTORY_ARTICLES, HISTORY_REFERENCES, HISTORY_NO_ADS,
    HISTORY_APPROVED_COMMIT, HISTORY_APPROVED_MANIFEST, HISTORY_APPROVAL_REFERENCE,
    owner_history_review_valid, apply_policy)

RECORD = candidate.ROOT / 'docs/history-release-20261024.json'
REPORT = candidate.DRAFT / 'release-build-audit.json'


def verify(reviews=None):
    files = candidate.verify()
    if candidate.sha(candidate.MANIFEST.read_bytes()) != HISTORY_APPROVED_MANIFEST:
        raise ValueError('The approved c01c7d96 candidate manifest changed')
    record = json.loads(RECORD.read_text(encoding='utf-8'))
    if (record.get('approved_candidate_commit') != HISTORY_APPROVED_COMMIT
            or record.get('approval_reference') != HISTORY_APPROVAL_REFERENCE
            or record.get('approved_manifest_sha256_lf') != HISTORY_APPROVED_MANIFEST
            or record.get('public_author') != 'Estrecho Ormuz'
            or record.get('merge_authorized') is not False
            or record.get('deployment_authorized') is not False
            or record.get('advertising_authorized') is not False
            or record.get('sha256_lf') != {name:candidate.sha(data) for name,data in sorted(files.items())}):
        raise ValueError('Release record differs from the explicitly approved bundle/scope')
    if reviews is None:
        reviews = json.loads((candidate.ROOT/'editorial-reviews.json').read_text(encoding='utf-8'))
    for name in HISTORY_NO_ADS:
        review = reviews.get(name) if isinstance(reviews, dict) else None
        if (not owner_history_review_valid(files[name].decode('utf-8'), review)
                or review.get('document') != name):
            raise ValueError(f'Missing exact owner editorial decision: {name}')
    return files, reviews


def render(files, reviews):
    result = {}
    for name,data in files.items():
        if name.endswith('.html'):
            text = apply_policy(data.decode('utf-8'), name, programmatic_ads=False, review=reviews[name])
            result[name] = public.sanitize_html(text, name).encode('utf-8')
        else:
            result[name] = data
    return result


def publish(root, reviews):
    """Fail closed on a changed article, support page, CSV, graph or approval."""
    files, reviews = verify(reviews)
    rendered = render(files, reviews)
    for name,data in rendered.items():
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    candidate.integrate(root, reviews)


def audit(root):
    files, reviews = verify()
    expected = render(files, reviews)
    errors = []
    for name,data in expected.items():
        path = root/name
        if not path.is_file() or candidate.sha(path.read_bytes()) != candidate.sha(data):
            errors.append('Changed release bytes: '+name)
            continue
        if not name.endswith('.html'):
            continue
        text = path.read_text(encoding='utf-8')
        meta = candidate.sitemap.MetaParser(); meta.feed(text)
        if meta.canonical != public.DOMAIN+'/'+name:
            errors.append('Canonical mismatch: '+name)
        for pair in (candidate.ARTICLES,candidate.METHODS):
            if name in pair.values():
                alternates={lang:public.DOMAIN+'/'+slug for lang,slug in {**pair,'x-default':pair['es']}.items()}
                if meta.alternates != alternates:
                    errors.append('Reciprocal hreflang mismatch: '+name)
        if ('noindex' in meta.robots) != (name in HISTORY_REFERENCES):
            errors.append('Incorrect indexability: '+name)
        if name in HISTORY_ARTICLES and ('data-institutional-byline' not in text or
                '<meta name="author" content="Estrecho Ormuz">' not in text):
            errors.append('Missing institutional byline: '+name)
        if (re.search(r'candidato|candidate awaiting|not authori[sz]ed|no autorizada|pendiente de aprobación|awaits editorial approval|adsbygoogle|mailto:|ElPtoWalter|Eduardo', text, re.I)
                or 'publisher-ads" content="disabled' not in text):
            errors.append('Pending notice, personal data or advertising: '+name)
    locations = {node.find(candidate.sitemap.qname(candidate.sitemap.SITEMAP_NS,'loc')).text
                 for node in ET.parse(root/'sitemap.xml').getroot()}
    for name in HISTORY_NO_ADS:
        if ((public.DOMAIN+'/'+name) in locations) != (name in HISTORY_ARTICLES):
            errors.append('Sitemap selection: '+name)
    for lang,names in {'es':('index.html','analisis.html','historial.html'),
                       'en':('en.html','en-analysis.html','en-history.html')}.items():
        for name in names:
            if f'href="/{candidate.ARTICLES[lang]}"' not in (root/name).read_text(encoding='utf-8'):
                errors.append('Missing incoming navigation: '+name)
    errors.extend(check_links(root))
    if errors:
        raise ValueError('\n'.join(errors))
    report = {'kind':'owner_approved_history_release_artifact',
              'approved_candidate_commit':HISTORY_APPROVED_COMMIT,
              'approval_reference':HISTORY_APPROVAL_REFERENCE,
              'merge_authorized':False, 'deployment_authorized':False,
              'public_author':'Estrecho Ormuz', 'advertising':False,
              'indexable':sorted(HISTORY_ARTICLES), 'accessible_noindex':sorted(HISTORY_REFERENCES),
              'sitemap_count':len(locations), 'link_errors':errors,
              'sha256_lf':{name:candidate.sha(data) for name,data in sorted(expected.items())},
              'navigation_sha256_lf':{name:candidate.sha((root/name).read_bytes()) for name in
                   ('index.html','en.html','analisis.html','en-analysis.html','historial.html','en-history.html')},
              'full_artifact_sha256_lf':{p.relative_to(root).as_posix():candidate.sha(p.read_bytes())
                                       for p in sorted(root.rglob('*')) if p.is_file()}}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',required=True)
    parser.parse_args()
    verify()
    print('Owner approval, original candidate hashes and limited release scope verified.')
