"""Internal preparation evidence, never an AdSense or legal approval."""
from __future__ import annotations
import argparse,copy,json
from pathlib import Path
from datetime import date
import build_sitemap as sitemap
from indexation_audit import page_indexing_snapshot

ROOT=Path(__file__).resolve().parent
STATE_KEYS={'schema_version','as_of','owner_type','public_contact_email','incoming_mail','outgoing_domain_identity','other_mail_aliases','legal_identity_complete','legal_compliance_confirmed','adsense_account_verified','cmp_verified','ready_for_resubmission','permissions'}


def state(root=ROOT):
    p=root/'publisher-preparation.json'
    if not p.exists():return None
    value=json.loads(p.read_text(encoding='utf-8'))
    if set(value)!=STATE_KEYS:raise ValueError('Unexpected preparation field; no personal or forwarding details permitted')
    incoming=value['incoming_mail'];outgoing=value['outgoing_domain_identity']
    if (value['schema_version']!=1 or value['other_mail_aliases']!='not_verified_by_this_statement'
        or value['owner_type']!='natural_person' or value['public_contact_email']!='contacto@estrechoormuz.com'
        or set(incoming)!={'status','statement_date','source','independently_tested'}
        or incoming!={'status':'confirmed_by_owner_statement','statement_date':'2026-10-28','source':'owner_instruction_in_this_chat_PR26_professional_email','independently_tested':False}
        or outgoing!={'status':'not_verified','test_sent_by_agent':False}
        or date.fromisoformat(value['as_of'])>date.today()
        or any(value[k] is not False for k in ('legal_identity_complete','legal_compliance_confirmed','adsense_account_verified','cmp_verified','ready_for_resubmission'))
        or set(value['permissions'])!={'merge','deployment','advertising_activation','adsense_review_request','indexing_request','personal_data_publication','send_email','dns_changes'}
        or any(v is not False for v in value['permissions'].values())):
        raise ValueError('Preparation must retain distinct receipt, reply and authorization boundaries')
    return value


def enrich(report,root=ROOT,public_root=None):
    result=copy.deepcopy(report);result['ready_for_resubmission']=False;result['account_approval']='not_verified'
    declarations=state(root)
    if declarations is None:return result
    if 'historical_snapshot_20261024' not in result and result.get('checked_at')=='2026-10-24':
        result['historical_snapshot_20261024']={k:copy.deepcopy(result[k]) for k in ('checked_at','warnings','external_checks_pending','inventory_note','owner_report','owner_confirmation','indexing_review') if k in result}
    result['checked_at']=declarations['as_of'];result['preparation_evidence']=declarations
    owner=result.setdefault('owner_confirmation',{});owner.pop('contact_receipt_and_reply',None)
    owner.update(owner_type='natural_person',public_contact_receipt=declarations['incoming_mail'],outgoing_domain_identity=declarations['outgoing_domain_identity'],legal_identity_details='not_provided_or_authorized',direct_adsense_account_access=False)
    result['owner_report_is_historical']=True
    result['warnings']=['AdSense account, legal identification, domain sending identity and consent remain unverified.',
      'Receipt of the public mailbox is confirmed by owner statement, not an independent agent email test.',
      'Existing editorial approvals and published investigations are not general external legal or rights clearance.',
      'Sitemap source, generated artifact, HTTP delivery, historical connector metadata and the dated owner Page Indexing snapshot are distinct evidence layers.']
    result['external_checks_pending']=['Current AdSense account policy tasks, crawl/ads.txt state and approval; no account result inferred from publisher ID',
      'Real legal identification and admissible address assessed privately, then expressly authorised through a safe publication process',
      'Ability to answer using the domain identity and effective contact procedure; other aliases not covered by the statement',
      'Individual Page Indexing and URL Inspection findings for the six research articles; the owner aggregate snapshot does not identify them',
      'Appropriate CMP, actual processing/retention/providers and consent behaviour before any advertising',
      'Separate owner authorization for merge, deployment and any future AdSense review; all advertising permissions remain off']
    owner_snapshot=page_indexing_snapshot(root)
    result['indexing_review']={'document':'docs/PREFLIGHT_ADSENSE_2026-10-28.md','performance_data_access':True,'historical_sitemaps_metadata_access':True,
      'page_indexing_access':'owner_snapshot_not_independent_api' if owner_snapshot else 'pending_external_account',
      'page_indexing_snapshot':owner_snapshot,'url_inspection_access':'pending_external_account',
      'six_research_individual_status':'pending_url_inspection','live_indexed_count':None,'editorial_indexing_decisions_changed':False}
    snapshot=root/'docs/preflight-20261028/sitemap-audit.json'
    if snapshot.exists():
        audit=json.loads(snapshot.read_text(encoding='utf-8'))
        result['publication_evidence']={'reference':'docs/preflight-20261028/sitemap-audit.json',
          'six_original_articles_http_200':len(audit['research'])==6 and all(r['public_http_status']==200 for r in audit['research']),
          'six_original_articles_built_indexable':all('noindex' not in r['built_robots'] and r['built_sitemap_contains'] for r in audit['research']),
          'pr25_deployed_verified_by_http':audit['pr25_deployment_verified_by_http'],
          'new_human_review_recorded':False,'external_legal_clearance_asserted':False}
        result['sitemap_evidence']={k:({'url_count':audit[k]['url_count'],'reference':audit[k]['reference'],'sha256_lf':audit[k]['sha256_lf']} if audit[k] else None) for k in ('source_sitemap','generated_sitemap','deployed_sitemap')}
        result['search_console_historical_submitted_urls']=60
        result['search_console_historical_submitted_is_current_indexed_count']=False
        result['public_ads_txt']=audit['public_ads_txt']
    public_root=public_root or root/'_site'
    if (public_root/'sitemap.xml').exists():
        import xml.etree.ElementTree as ET
        locations=[n.find(sitemap.qname(sitemap.SITEMAP_NS,'loc')).text for n in ET.parse(public_root/'sitemap.xml').getroot()]
        result['candidate_pages']=[('index.html' if u=='https://estrechoormuz.com/' else u.removeprefix('https://estrechoormuz.com/')) for u in locations]
        result['inventory_note']=f'{len(locations)} technically eligible URLs in the generated public sitemap; not a count of indexed or AdSense-approved pages.'
        result['monetized_pages']=[]
        from adsense_checks import check_artifact
        html_pages=sorted(p.relative_to(public_root).as_posix() for p in public_root.rglob('*.html'))
        noindex=[]
        for name in html_pages:
            meta=sitemap.MetaParser();meta.feed((public_root/name).read_text(encoding='utf-8'))
            if 'noindex' in meta.robots:noindex.append(name)
        errors=check_artifact(public_root)
        result['public_surface_snapshot']={'html_pages':len(html_pages),'noindex_pages':len(noindex),'eligible_sitemap_urls':len(locations),'artifact_privacy_or_ads_errors':errors,'google_indexing_inferred_from_artifact':False}
        result['noindex_pages']=noindex
        result['ad_free_pages']=html_pages if not errors else []
        result['errors']=list(dict.fromkeys(result.get('errors',[])+errors))
        result['local_checks_passed']=not result['errors']
    return result


def check(root=ROOT):
    declarations=state(root)
    if declarations is None:raise ValueError('Missing preparation declarations')
    report=json.loads((root/'adsense-readiness-report.json').read_text(encoding='utf-8'))
    config=json.loads((root/'monetization.json').read_text(encoding='utf-8'))['adsense']
    if report.get('ready_for_resubmission') is not False or any(config[k] is not False for k in ('enabled','account_ready','cmp_verified','publisher_identity_complete')):
        raise ValueError('Advertising/readiness permission changed')
    if report.get('preparation_evidence')!=declarations:raise ValueError('Readiness report does not reflect the actual limited owner statement')
    if report.get('indexing_review',{}).get('page_indexing_snapshot')!=page_indexing_snapshot(root):
        raise ValueError('Readiness report does not reflect the dated aggregate evidence')
    return declarations


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--refresh-report',action='store_true');p.add_argument('--check',action='store_true');a=p.parse_args()
    if a.refresh_report:
        path=ROOT/'adsense-readiness-report.json';value=enrich(json.loads(path.read_text(encoding='utf-8')))
        path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    check();print('Receipt statement distinguished from sending; readiness and every advertising gate remain false.')
