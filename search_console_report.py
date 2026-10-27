"""Offline Search Console comparisons. Detailed inputs and outputs stay private.

Accepts local JSON rows (or Windsor's {status: done, data: [...]}) outside this
checkout. Never sends data, authenticates, submits URLs or writes into Pages.
"""
from __future__ import annotations
import argparse
from datetime import date,timedelta
from decimal import Decimal
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SITE='sc-domain:estrechoormuz.com'


def private_path(path):
    path=Path(path).resolve()
    if path.is_relative_to(ROOT):raise ValueError('Detailed Search Console inputs/outputs must be outside the public checkout')
    return path


def read_rows(path):
    path=private_path(path);value=json.loads(path.read_text(encoding='utf-8-sig'))
    if isinstance(value,dict):
        if value.get('status')!='done':raise ValueError('Search Console export is incomplete')
        value=value.get('data')
    if not isinstance(value,list) or not all(isinstance(r,dict) for r in value):raise ValueError('Expected a list of Search Console rows')
    return value


def number(value,name):
    try:n=Decimal(str(value))
    except Exception as exc:raise ValueError('Invalid '+name) from exc
    if not n.is_finite() or n<0:raise ValueError('Invalid '+name)
    return n


def metrics(rows):
    clicks=Decimal(0);impressions=Decimal(0);weighted=Decimal(0)
    for r in rows:
        c=number(r.get('clicks'),'clicks');i=number(r.get('impressions'),'impressions')
        if c!=int(c) or i!=int(i):raise ValueError('Clicks and impressions must be integral counts')
        p=number(r.get('position'),'position')
        clicks+=c;impressions+=i;weighted+=p*i
    return {'clicks':int(clicks),'impressions':int(impressions),
            'ctr_percent':float(clicks/impressions*100) if impressions else None,
            'position_reconstructed_approx':float(weighted/impressions) if impressions else None}


def windows(end,days=28):
    if days<1:raise ValueError('Window length must be positive')
    end=date.fromisoformat(str(end));start=end-timedelta(days=days-1)
    return ((start-timedelta(days=days),start-timedelta(days=1)),(start,end))


def compare(daily,end,days=28):
    seen={}
    for row in daily:
        if set(row)-{'date','clicks','impressions','position','search_type'}:raise ValueError('Daily rows must not contain page/query/device dimensions')
        d=date.fromisoformat(row['date'])
        if d in seen:raise ValueError('Duplicate daily totals would double count impressions')
        if row.get('search_type','web')!='web':raise ValueError('Use the same web search type in both periods')
        seen[d]=row
    result=[]
    for start,stop in windows(end,days):
        expected=[start+timedelta(days=i) for i in range(days)]
        missing=[d.isoformat() for d in expected if d not in seen]
        rows=[seen[d] for d in expected if d in seen]
        result.append({'start':start.isoformat(),'end':stop.isoformat(),'days':days,
                       'returned_days':len(rows),'missing_days':missing,'complete':not missing,**metrics(rows)})
    previous,current=result
    complete=all(r['complete'] for r in result)
    change={}
    if complete:
        for key in ('clicks','impressions'):
            a,b=previous[key],current[key]
            change[key]={'absolute':b-a,'percent':100*(b-a)/a if a else None}
        change['ctr_percentage_points']=(current['ctr_percent']-previous['ctr_percent']) if current['ctr_percent'] is not None and previous['ctr_percent'] is not None else None
        a,b=previous['position_reconstructed_approx'],current['position_reconstructed_approx']
        change['position_difference_approx']=b-a if a is not None and b is not None else None
    return {'previous':previous,'current':current,'comparison_valid':complete,'change':change}


def page_audit(pages,queries):
    rows=[];seen=set()
    for r in pages:
        page=r['page']
        if not page.startswith('https://estrechoormuz.com/'):raise ValueError('Foreign Search Console property')
        if page in seen:raise ValueError('Expected one aggregate row per page')
        seen.add(page);m=metrics([r]);query_rows=[q for q in queries if q.get('page')==page]
        visible=metrics(query_rows) if query_rows else None
        rows.append({'page':page,**m,'visible_query_rows':len(query_rows),
          'visible_query_impressions':visible['impressions'] if visible else None,
          'query_impression_fraction':visible['impressions']/m['impressions'] if visible and m['impressions'] else None,
          'query_table_is_complete':False})
    return rows


def compare_pages(previous,current):
    before={r['page']:r for r in page_audit(previous,[])}
    after={r['page']:r for r in page_audit(current,[])}
    result=[]
    for page in sorted(before.keys()|after.keys()):
        a,b=before.get(page),after.get(page)
        change=None
        if a is not None and b is not None:
            change={'clicks_absolute':b['clicks']-a['clicks'],'impressions_absolute':b['impressions']-a['impressions'],
                    'ctr_percentage_points':b['ctr_percent']-a['ctr_percent'] if a['ctr_percent'] is not None and b['ctr_percent'] is not None else None,
                    'position_difference_approx':b['position_reconstructed_approx']-a['position_reconstructed_approx'] if a['position_reconstructed_approx'] is not None and b['position_reconstructed_approx'] is not None else None}
        result.append({'page':page,'previous':a,'current':b,'change':change,'missing_period_is_not_zero':True})
    return result


def make_report(daily,pages,queries,end,days,provenance):
    if (provenance.get('site')!=SITE or provenance.get('search_type')!='web'
            or provenance.get('include_fresh_data') is not False
            or provenance.get('date_timezone')!='America/Los_Angeles'):
        raise ValueError('Require explicit property, web, finalized data and Search Console date timezone')
    periods=compare(daily,end,days)
    if provenance.get('date_to')!=str(end):raise ValueError('Manifest end differs from requested comparison')
    return {'kind':'private_search_console_comparison','provenance':provenance,'periods':periods,
      'daily_totals_for_export_range':metrics(daily),'page_audit':page_audit(pages,queries),
      'limits':[
       'Daily totals, page aggregates and query tables use different aggregation/privacy rules; do not add them together.',
       'CTR is total clicks / total impressions, never the mean of row CTRs.',
       'Position is reconstructed with impression weights from rounded row positions; it is approximate, not an adjusted causal estimate.',
       'A missing day is unknown, not zero. Incomplete windows have no growth comparison.',
       'Queries may be anonymized or truncated. Visible query rows do not explain every impression.',
       'These dates precede publication of all three original investigations. No growth is attributed to them.',
       'Sitemap eligibility and search impressions do not establish the current number of indexed pages. URL Inspection/Page Indexing access is separate.',
       'Search CTR measures search-result clicks, not subscriptions, reading completion or advertising revenue.']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('daily','pages','provenance','output'):p.add_argument('--'+arg,type=Path,required=True)
    p.add_argument('--queries',type=Path);p.add_argument('--end',required=True);p.add_argument('--days',type=int,default=28)
    p.add_argument('--previous-pages',type=Path);p.add_argument('--current-pages',type=Path)
    a=p.parse_args();out=private_path(a.output)
    if out.exists():raise ValueError('Choose a new private output file; existing reports are not overwritten')
    provenance=json.loads(private_path(a.provenance).read_text(encoding='utf-8-sig'))
    report=make_report(read_rows(a.daily),read_rows(a.pages),read_rows(a.queries) if a.queries else [],a.end,a.days,provenance)
    if bool(a.previous_pages)!=bool(a.current_pages):raise ValueError('Provide both page period exports')
    if a.previous_pages:
        expected=[[start.isoformat(),end.isoformat()] for start,end in windows(a.end,a.days)]
        if provenance.get('page_comparison_windows')!=expected:raise ValueError('Page export periods must match the two daily comparison windows')
        report['pages_equal_windows']=compare_pages(read_rows(a.previous_pages),read_rows(a.current_pages))
    report['input_sha256']={key:hashlib.sha256(private_path(path).read_bytes()).hexdigest() for key,path in vars(a).items() if key in ('daily','pages','queries','provenance','previous_pages','current_pages') and path}
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    print('Private Search Console report written; no upload or public export performed.')


if __name__=='__main__':main()
