"""Read-only comparison of source, built, deployed and account evidence.

No crawl/indexing request, editorial-policy mutation or advertising activation.
Network observations are supplied as local public-HTTP evidence, not inferred.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,re
from collections import Counter,defaultdict
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo
import build_sitemap as sitemap
import seo_surface

BASE='https://estrechoormuz.com/'
ARTICLES=tuple(path for rows in seo_surface.RESEARCH.values() for path,*_ in rows)
DIARY=re.compile(r'^(?:diario|diary)/\d{4}-\d{2}-\d{2}\.html$')
ACCOUNT_FIELDS=('page_indexing_state','url_inspection_verdict','google_selected_canonical','last_crawl_time','account_checked_at','private_evidence_reference')


def sha(raw):return hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()
def urls(raw):
    tree=ET.fromstring(raw)
    return [n.find(sitemap.qname(sitemap.SITEMAP_NS,'loc')).text for n in tree]
def relative(url):
    path=urlsplit(url).path.lstrip('/')
    return (path+'index.html') if not path or path.endswith('/') else path


class TextFacts(HTMLParser):
    def __init__(self,text):
        super().__init__(convert_charrefs=True);self.meta=sitemap.MetaParser();self.meta.feed(text)
        self.depth=0;self.ignore=0;self.main=[];self.times=[];self.json_dates=[];self.hrefs=[];self.json_buffer=None
        self.paragraphs=[];self.paragraph=None
        self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='main':self.depth+=1
        if tag in ('script','style'):
            self.ignore+=1
            if tag=='script' and a.get('type')=='application/ld+json':self.json_buffer=''
        if tag=='time' and self.depth and a.get('datetime'):self.times.append(a['datetime'])
        if tag=='a' and self.depth and a.get('href'):self.hrefs.append(a['href'])
        if tag=='p' and self.depth:self.paragraph=[]
    def handle_endtag(self,tag):
        if tag=='main':self.depth=max(0,self.depth-1)
        if tag=='p' and self.paragraph is not None:
            self.paragraphs.append(re.sub(r'\s+',' ',' '.join(self.paragraph)).strip());self.paragraph=None
        if tag in ('script','style'):
            if tag=='script' and self.json_buffer is not None:
                try:self.extract_dates(json.loads(self.json_buffer))
                except (ValueError,TypeError):pass
                self.json_buffer=None
            self.ignore=max(0,self.ignore-1)
    def extract_dates(self,value):
        if isinstance(value,dict):
            for key,v in value.items():
                if key in ('datePublished','dateModified') and isinstance(v,str):self.json_dates.append(v)
                else:self.extract_dates(v)
        elif isinstance(value,list):
            for v in value:self.extract_dates(v)
    def handle_data(self,data):
        if self.json_buffer is not None:self.json_buffer+=data
        if self.depth and not self.ignore:self.main.append(data)
        if self.paragraph is not None and not self.ignore:self.paragraph.append(data)
    @property
    def text(self):return re.sub(r'\s+',' ',' '.join(self.main)).strip()


def local_date(value):
    if len(value)==10:return value
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None:return None  # Never silently assign a timezone.
    return dt.astimezone(ZoneInfo('Europe/Madrid')).date().isoformat()


def diary_facts(name,text):
    f=TextFacts(text);edition=Path(name).stem;issues=[]
    primary=f.times[0] if f.times else None
    if not primary:issues.append('fecha_visible_no_localizada')
    elif primary[:10]!=edition:issues.append('fecha_visible_distinta_de_ruta')
    for value in f.json_dates:
        try:day=local_date(value)
        except ValueError:day=None
        if day is None:issues.append('fecha_schema_sin_zona_o_invalida')
        elif day!=edition:issues.append('fecha_schema_local_distinta_de_edicion')
    later=[]
    for href in f.hrefs:
        if urlsplit(href).netloc in ('','estrechoormuz.com'):continue
        match=re.search(r'/((?:20\d\d)[/-]\d\d[/-]\d\d)(?:[/-]|$)',urlsplit(href).path)
        if match and match[1].replace('/','-')>edition:later.append(href)
    if later:issues.append('enlace_con_fecha_posterior_requiere_contexto')
    # This is a triage signal only. Masking dates/numbers cannot prove duplication.
    masked=re.sub(r'\b\d+(?:[/:.,-]\d+)*\b','[NUMBER]',f.text.casefold())
    repeated=[{'sha256':sha(p.encode()),'occurrences':n,'words':len(p.split())} for p,n in Counter(f.paragraphs).items() if p and n>1]
    return {'edition_date':edition,'visible_date':primary,'schema_dates':f.json_dates,
            'word_count':len(re.findall(r'\w+',f.text)),'main_text_sha256':sha(f.text.encode()),
            'date_number_masked_sha256':sha(masked.encode()),'temporal_review_flags':sorted(set(issues)),
            'later_dated_external_links':later,'repeated_paragraphs':repeated,'canonical':f.meta.canonical,'robots':f.meta.robots.strip()}


def layer(raw,kind,reference):
    values=urls(raw)
    return {'kind':kind,'reference':reference,'url_count':len(values),'sha256_lf':sha(raw),
            'duplicate_loc_count':len(values)-len(set(values)),'urls':values}


def audit(root,public_root,http=None):
    source=layer((root/'sitemap.xml').read_bytes(),'repository_source','sitemap.xml')
    built=layer((public_root/'sitemap.xml').read_bytes(),'generated_public_artifact','_site/sitemap.xml')
    observed=(http or {}).get('responses',{})
    live=observed.get(BASE+'sitemap.xml',{})
    deployed=layer(live['body'].encode(),'http_deployed',BASE+'sitemap.xml') if live.get('status')==200 and live.get('body') else None
    if deployed:deployed.update(http_status=live['status'],checked_at=(http or {}).get('checked_at'),headers=live.get('headers',{}))
    sets={k:set(v['urls']) if v else set() for k,v in [('source',source),('built',built),('deployed',deployed)]}
    robot=RobotFileParser();robot.parse(observed.get(BASE+'robots.txt',{}).get('body','').splitlines())
    built_robot=RobotFileParser();built_robot.parse((public_root/'robots.txt').read_text(encoding='utf-8').splitlines())
    research=[];errors=[]
    for name in ARTICLES:
        url=BASE+name;f=TextFacts((public_root/name).read_text(encoding='utf-8'))
        live_page=observed.get(url,{});p=TextFacts(live_page.get('body','')) if live_page.get('status')==200 else None
        if f.meta.canonical!=url or 'noindex' in f.meta.robots or url not in sets['built']:errors.append('Built research policy: '+name)
        if not built_robot.can_fetch('*',url):errors.append('Built robots blocks research: '+name)
        for lang,target in f.meta.alternates.items():
            if lang=='x-default':continue
            other=TextFacts((public_root/relative(target)).read_text(encoding='utf-8')).meta
            if other.canonical!=target or other.alternates.get(f.meta.lang)!=url:errors.append('Research hreflang: '+name)
        row={'url':url,'source_sitemap_contains':url in sets['source'],'built_sitemap_contains':url in sets['built'],
             'deployed_sitemap_contains':url in sets['deployed'] if deployed else None,
             'built_canonical':f.meta.canonical,'built_robots':f.meta.robots.strip(),'built_robots_txt_allowed':built_robot.can_fetch('*',url),
             'built_hreflang':f.meta.alternates,'public_http_status':live_page.get('status'),
             'public_canonical':p.meta.canonical if p else None,'public_robots':p.meta.robots.strip() if p else None,
             'public_hreflang':p.meta.alternates if p else None,
             'public_robots_txt_allowed':robot.can_fetch('*',url) if observed.get(BASE+'robots.txt',{}).get('status')==200 else None,
             'public_x_robots_tag':live_page.get('headers',{}).get('x-robots-tag'),'google_indexing_confirmed':False}
        research.append(row)
        if http is not None:
            if row['public_http_status']!=200 or row['public_canonical']!=url:errors.append('Public research delivery/canonical: '+name)
            if 'noindex' in (row['public_robots'] or '') or 'noindex' in (row['public_x_robots_tag'] or '').lower():errors.append('Public research noindex: '+name)
            if row['public_robots_txt_allowed'] is not True or row['public_hreflang']!=row['built_hreflang']:errors.append('Public robots/hreflang: '+name)
    names=sorted({relative(u) for u in sets['source'] if DIARY.match(relative(u))})
    diaries=[]
    for name in names:
        url=BASE+name;f=diary_facts(name,(root/name).read_text(encoding='utf-8'))
        built_text=(public_root/name).read_text(encoding='utf-8');g=TextFacts(built_text)
        page=observed.get(url,{});p=TextFacts(page.get('body','')) if page.get('status')==200 else None
        diaries.append({'url':url,**f,'source_sitemap_contains':True,'built_sitemap_contains':url in sets['built'],
                        'deployed_sitemap_contains':url in sets['deployed'] if deployed else None,
                        'built_robots':g.meta.robots.strip(),'public_http_status':page.get('status'),
                        'public_robots':p.meta.robots.strip() if p else None,
                        'policy_difference':('noindex' in f['robots'])!=('noindex' in g.meta.robots),
                        'editorial_decision_changed':False,'human_value_review':'pendiente_decision_titular'})
    exact=defaultdict(list);masked=defaultdict(list)
    for row in diaries:exact[row['main_text_sha256']].append(row['url']);masked[row['date_number_masked_sha256']].append(row['url'])
    common=defaultdict(set)
    for name in names:
        for paragraph in TextFacts((root/name).read_text(encoding='utf-8')).paragraphs:
            if len(paragraph.split())>=12:common[paragraph].add(BASE+name)
    shared=[{'paragraph_sha256':sha(p.encode()),'word_count':len(p.split()),'urls':sorted(v)} for p,v in common.items() if len(v)>1]
    baseline_claims=[]
    for name in names:
        t=TextFacts((root/name).read_text(encoding='utf-8')).text.casefold()
        if 'primera línea base' in t or 'first baseline' in t:baseline_claims.append(BASE+name)
    if len(baseline_claims)>2:
        for row in diaries:
            if row['url'] in baseline_claims:row['temporal_review_flags'].append('afirmacion_primera_linea_base_repetida_entre_ediciones')
    seo_http={}
    for name,(lang,kind) in seo_surface.PAGES.items():
        url=BASE if name=='index.html' else BASE+name;page=observed.get(url,{})
        seo_http[name]={'http_status':page.get('status'),'research_marker_present':'data-seo-research' in page.get('body',''),'expected_title_present':seo_surface.COPY[lang,kind][0] in page.get('body','')}
    ads=observed.get(BASE+'ads.txt',{});ads_line=(root/'ads.txt').read_text(encoding='utf-8').strip()
    return {'kind':'separate_indexation_evidence_layers','source_sitemap':source,'generated_sitemap':built,'deployed_sitemap':deployed,
      'source_only_urls':sorted(sets['source']-sets['built']),'built_only_urls':sorted(sets['built']-sets['source']),
      'built_vs_deployed_url_sets_equal':sets['built']==sets['deployed'] if deployed else None,
      'search_console_indexed_count':None,'search_console_page_indexing':'pending_external_account',
      'url_inspection':'pending_external_account','research':research,'diary_in_source_sitemap':diaries,
      'exact_main_text_duplicate_groups':[v for v in exact.values() if len(v)>1],
      'date_number_masked_similarity_groups':[v for v in masked.values() if len(v)>1],
      'cross_edition_shared_paragraphs':shared,'pr25_deployed_http_checks':seo_http,
      'baseline_claim_reused_urls':baseline_claims,
      'public_ads_txt':{'http_status':ads.get('status'),'checked_at':(http or {}).get('checked_at'),'publisher_id':ads_line.split(',')[1].strip(),
                       'sha256':ads.get('sha256'),'matches_source_and_built_file':ads.get('body','').strip()==ads_line==(public_root/'ads.txt').read_text(encoding='utf-8').strip(),'account_authorized':'not_verified'},
      'pr25_deployment_verified_by_http':all(x['http_status']==200 and x['research_marker_present'] and x['expected_title_present'] for x in seo_http.values()),
      'similarity_is_only_a_triage_heuristic':True,'editorial_decisions_changed':False,'errors':errors}


def write_report(report,output):
    output.mkdir(parents=True,exist_ok=True)
    (output/'sitemap-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    cols=['url','edition_date','word_count','visible_date','robots','built_robots','public_robots','source_sitemap_contains','built_sitemap_contains','deployed_sitemap_contains','policy_difference','temporal_review_flags','main_text_sha256','date_number_masked_sha256','editorial_decision_changed','human_value_review']
    with (output/'diary-audit.csv').open('w',encoding='utf-8',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=cols,extrasaction='ignore');w.writeheader()
        for row in report['diary_in_source_sitemap']:w.writerow({**row,'temporal_review_flags':'; '.join(row['temporal_review_flags'])})
    template=output/'url-inspection-template.csv'
    if not template.exists():
        cols=['url','built_sitemap_contains','deployed_sitemap_contains','public_http_status','built_canonical','built_robots','account_status',*ACCOUNT_FIELDS]
        with template.open('x',encoding='utf-8',newline='') as stream:
            w=csv.DictWriter(stream,fieldnames=cols,extrasaction='ignore');w.writeheader()
            for row in report['research']:w.writerow({**row,'account_status':'pendiente_cuenta_externa',**{k:'' for k in ACCOUNT_FIELDS}})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).parent);p.add_argument('--public-root',type=Path,required=True);p.add_argument('--http',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=audit(a.root,a.public_root,json.loads(a.http.read_text(encoding='utf-8')) if a.http else None);write_report(result,a.output)
    print(json.dumps({'source':result['source_sitemap']['url_count'],'built':result['generated_sitemap']['url_count'],'deployed':result['deployed_sitemap']['url_count'] if result['deployed_sitemap'] else None,'diaries':len(result['diary_in_source_sitemap']),'indexed_count':None,'errors':result['errors']},indent=2))
    if result['errors']:raise SystemExit(1)
