"""Frozen EIA table-4 inputs and decimal calculations; no monitor data or API keys."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime,timezone
from decimal import Decimal,ROUND_HALF_UP
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parent
FOLDER=ROOT/'drafts/energy-flows-20261025'
INPUT=ROOT/'drafts/adsense-20261024/energy-context.csv'
EIA='https://www.eia.gov/outlooks/steo/report/energysecurity/article.php'
RIGHTS='https://www.eia.gov/about/copyrights_reuse.php'
IMO='https://www.imo.org/en/mediacentre/hottopics/pages/middle-east-strait-of-hormuz.aspx'
EXPECTED=(('2025Q1','20.9','11.7'),('2025Q2','21.0','11.0'),('2025Q3','21.3','10.9'),
          ('2025Q4','21.6','10.5'),('2026Q1','14.9','7.4'),('2026Q2','4.9','0.8'))
FIELDS=('period','oil_million_barrels_per_day','lng_billion_cubic_feet_per_day','oil_index_2025q4_100','lng_index_2025q4_100','oil_change_previous_quarter_pct','lng_change_previous_quarter_pct','source','source_release')


def sha(data):
    return hashlib.sha256(data.replace(b'\r\n',b'\n')).hexdigest()


def read_rows():
    with INPUT.open(encoding='utf-8',newline='') as f: rows=list(csv.DictReader(f))
    selected=tuple((r['period'],r['oil_million_barrels_per_day'],r['lng_billion_cubic_feet_per_day']) for r in rows)
    if selected!=EXPECTED or any(r['source']!=EIA or r['source_release']!='2026-08-12' for r in rows):
        raise ValueError('Frozen six-quarter EIA input changed; investigate and obtain a new review')
    return rows


def pct(value,base):
    value,base=Decimal(str(value)),Decimal(str(base))
    if base<=0:raise ValueError('A percentage requires a strictly positive baseline')
    return (value/base-1)*100


def number(value,places=8):
    return str(Decimal(value).quantize(Decimal(1).scaleb(-places),rounding=ROUND_HALF_UP))


def calculate(rows=None):
    rows=read_rows() if rows is None else rows
    out=[]
    for i,row in enumerate(rows):
        oil=Decimal(row['oil_million_barrels_per_day']);lng=Decimal(row['lng_billion_cubic_feet_per_day'])
        result={**row,'oil_index_2025q4_100':number(oil/Decimal('21.6')*100),
                'lng_index_2025q4_100':number(lng/Decimal('10.5')*100),
                'oil_change_previous_quarter_pct':'','lng_change_previous_quarter_pct':''}
        if i:
            for field,raw in [('oil_change_previous_quarter_pct','oil_million_barrels_per_day'),('lng_change_previous_quarter_pct','lng_billion_cubic_feet_per_day')]:
                result[field]=number(pct(row[raw],rows[i-1][raw]))
        out.append(result)
    comparisons={}
    for label,a,b in [('2025_path',0,3),('2026q1_vs_2025q4',3,4),('2026q2_vs_2026q1',4,5),
                      ('headline_2026q2_vs_2025q4',3,5),('sensitivity_2026q2_vs_2025q1',0,5)]:
        comparisons[label]={'start':rows[a]['period'],'end':rows[b]['period'],
                           'oil_pct':number(pct(rows[b]['oil_million_barrels_per_day'],rows[a]['oil_million_barrels_per_day'])),
                           'lng_pct':number(pct(rows[b]['lng_billion_cubic_feet_per_day'],rows[a]['lng_billion_cubic_feet_per_day']))}
    return out,comparisons


def csv_text():
    rows,_=calculate();f=io.StringIO(newline='')
    writer=csv.DictWriter(f,fieldnames=FIELDS,lineterminator='\n');writer.writeheader();writer.writerows(rows)
    return f.getvalue()


class Tables(HTMLParser):
    def __init__(self):
        super().__init__();self.tables=[];self.table=None;self.row=None;self.cell=None;self.text=[]
    def handle_starttag(self,tag,attrs):
        if tag=='table':self.table=[]
        elif tag=='tr' and self.table is not None:self.row=[]
        elif tag in ('td','th') and self.row is not None:self.cell=[]
    def handle_data(self,data):
        self.text.append(data)
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()));self.cell=None
        elif tag=='tr' and self.row is not None:
            self.table.append(self.row);self.row=None
        elif tag=='table' and self.table is not None:
            self.tables.append(self.table);self.table=None


def extract_official(raw):
    parser=Tables();parser.feed(raw.decode('utf-8'))
    values={}
    for table in parser.tables:
        for row in table:
            if not row:continue
            if row[0] in ('Total oil flows through the Strait of Hormuz','LNG flows through the Strait of Hormuz (billion cubic feet per day)'):
                if len(row)!=7:raise ValueError('Official quarter schema changed')
                values['oil' if row[0].startswith('Total') else 'lng']=row[1:]
    if values!={'oil':[r[1] for r in EXPECTED],'lng':[r[2] for r in EXPECTED]}:
        raise ValueError('Official EIA selected rows differ from frozen data')
    normalized=' '.join(' '.join(parser.text).split())
    if 'Release Date: August 12, 2026' not in normalized:raise ValueError('Supplement release date changed')
    return values


def verify_online():
    records=[]
    for name,url in [('eia_table4',EIA),('eia_reuse',RIGHTS),('imo_context',IMO)]:
        with urlopen(Request(url,headers={'User-Agent':'EstrechoOrmuz-editorial-source-check/1.0'}),timeout=30) as response:
            raw=response.read();status=response.status
        if status!=200:raise ValueError(f'{name}: HTTP {status}')
        record={'source':name,'url':url,'http_status':status,'page_sha256_lf':sha(raw)}
        if name=='eia_table4':record['selected_rows']=extract_official(raw);record['release']='2026-08-12'
        records.append(record)
    result={'checked_at':datetime.now(timezone.utc).isoformat(),'checks':records,
            'scope':'HTTP delivery, exact two EIA table-4 rows and supplement date; source policy read separately. No verification of individual voyages, current traffic or independent legal clearance.',
            'personal_data_copied':False}
    (FOLDER/'source-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-online',action='store_true')
    args=parser.parse_args()
    if args.verify_online:
        result=verify_online();print('Three primary URLs HTTP 200; 12 table-4 values and supplement release match.')
    else:
        _,comparisons=calculate();print(json.dumps(comparisons,ensure_ascii=False,indent=2))
