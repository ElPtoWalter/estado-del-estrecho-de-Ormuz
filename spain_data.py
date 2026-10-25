"""Six selected official facts and Decimal calculations; no traffic estimates."""
from __future__ import annotations
import argparse,csv,hashlib,io,json
from decimal import Decimal,localcontext,ROUND_HALF_UP
from pathlib import Path

ROOT=Path(__file__).resolve().parent
FOLDER=ROOT/'drafts/spain-europe-20261025'
INPUT=FOLDER/'source-inputs.csv'
ENAGAS='https://www.enagas.es/content/dam/enagas/es/ficheros/sala-de-comunicacion/publicaciones/informe-sistema-gasista/informe-sistema-gasista-espa%C3%B1ol-2025.pdf'
ENAGAS_XLSX='https://www.enagas.es/content/dam/enagas/es/ficheros/informe-sistema-gasista-2025/2-Operacion-fisica_Informe_Sistema_Gasista_2025.xlsx'
EUROSTAT='https://ec.europa.eu/eurostat/web/products-eurostat-news/w/ddn-20260325-3'
EUROSTAT_XLSX='https://ec.europa.eu/eurostat/documents/d/products-eurostat-news/imports-energy-products-2025'
EXPECTED={
 'es_total':('372498','GWh',ENAGAS),
 'es_lng':('248084','GWh',ENAGAS),
 'qatar_map':('6403','GWh',ENAGAS),
 'qatar_pdf_share':('1.735','percent',ENAGAS),
 'qatar_excel_fraction':('0.01718890770907905','fraction',ENAGAS_XLSX),
 'eu_qatar_value_share':('8.855309243451158','percent_of_trade_value',EUROSTAT_XLSX)}

def sha(raw):return hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()

def read_inputs():
 rows=list(csv.DictReader(io.StringIO(INPUT.read_text(encoding='utf-8'))))
 if len(rows)!=6 or {r['metric'] for r in rows}!=set(EXPECTED):raise ValueError('Unexpected source selection or duplicate metric')
 for r in rows:
  value,unit,url=EXPECTED[r['metric']]
  if (r['value'],r['unit'],r['source'],r['period'])!=(value,unit,url,'2025'):raise ValueError('Frozen fact, unit, source or period changed: '+r['metric'])
 return rows

def calculate():
 facts={r['metric']:Decimal(r['value']) for r in read_inputs()}
 with localcontext() as context:
  context.prec=50
  total=facts['qatar_map']/facts['es_total']*100
  lng=facts['qatar_map']/facts['es_lng']*100
  excel=facts['qatar_excel_fraction']*100
  implied=facts['es_total']*facts['qatar_pdf_share']/100
  return {
   'es_total_share':(total,'percent','qatar_map / es_total * 100','Own quotient; not a correction to the PDF chart'),
   'es_lng_share':(lng,'percent','qatar_map / es_lng * 100','Own LNG-only denominator; not comparable to EU trade value'),
   'excel_share':(excel,'percent','qatar_excel_fraction * 100','Official workbook fraction converted to percent'),
   'pdf_minus_quotient':(facts['qatar_pdf_share']-total,'percentage_points','qatar_pdf_share - es_total_share','Documentary difference; cause unresolved'),
   'excel_minus_quotient':(excel-total,'percentage_points','excel_share - es_total_share','Small residual; no unverified cause assigned'),
   'implied_qatar_volume':(implied,'GWh','es_total * qatar_pdf_share / 100','Hypothetical equality check; not observed volume'),
   'implied_minus_map':(implied-facts['qatar_map'],'GWh','implied_qatar_volume - qatar_map','Arithmetic residual; not lost or missing energy'),
   'eu_news_rounded':(facts['eu_qatar_value_share'].quantize(Decimal('.1'),rounding=ROUND_HALF_UP),'percent_of_trade_value','round(eu_qatar_value_share; 1 decimal)','Value of extra-EU LNG imports; not volume or consumption')}

def calculations_csv():
 stream=io.StringIO();writer=csv.writer(stream,lineterminator='\n')
 writer.writerow(['calculation','value','unit','period','formula','interpretation','source_inputs'])
 for key,(value,unit,formula,note) in calculate().items():
  writer.writerow([key,format(value.quantize(Decimal('.00000001'),rounding=ROUND_HALF_UP),'f'),unit,'2025',formula,note,'source-inputs.csv'])
 return stream.getvalue()

def verify_downloads(directory):
 """Optional read-only audit of downloaded originals; packages not needed by CI."""
 from pypdf import PdfReader
 import openpyxl
 directory=Path(directory)
 pdf=PdfReader(directory/'enagas-2025.pdf')
 for page,terms in [(22,('372.498','248.084','124.414')),(23,('Qatar','6.403')),(24,('Qatar','1,735'))]:
  text=pdf.pages[page].extract_text()
  if not all(term in text for term in terms):raise ValueError('Enagás PDF source changed')
 w=openpyxl.load_workbook(directory/'enagas-operation-2025.xlsx',read_only=True,data_only=False)
 if w['Pág. 25']['E4'].value!=2025 or w['Pág. 25']['B12'].value!='Qatar' or str(w['Pág. 25']['E12'].value)!=EXPECTED['qatar_excel_fraction'][0]:raise ValueError('Enagás Excel cell changed')
 import zipfile,xml.etree.ElementTree as ET
 with zipfile.ZipFile(directory/'enagas-operation-2025.xlsx') as z:
  chart=ET.fromstring(z.read('xl/charts/chart2.xml'));ns={'c':'http://schemas.openxmlformats.org/drawingml/2006/chart'}
  series=[s for s in chart.findall('.//c:ser',ns) if any(f.text=="'Pág. 25'!$E$5:$E$28" for f in s.findall('.//c:f',ns))]
  if len(series)!=1:raise ValueError('Enagás chart binding changed')
  point=series[0].find('.//c:numCache/c:pt[@idx="7"]/c:v',ns)
  if point is None or abs(Decimal(point.text)-Decimal(EXPECTED['qatar_excel_fraction'][0]))>Decimal('0.00000000000000001'):raise ValueError('Enagás chart cache changed')
 e=openpyxl.load_workbook(directory/'eurostat-energy-2025.xlsx',read_only=True,data_only=False)
 sheet=e['VISUAL 2']
 if ('2025' not in sheet['A1'].value or 'value' not in sheet['A2'].value or sheet['D9'].value.strip()!='Qatar' or str(sheet['E9'].value)!=EXPECTED['eu_qatar_value_share'][0]):raise ValueError('Eurostat annex definition or value changed')
 if 'Net mass' not in e['Natural gas (liq) partners']['C16'].value:raise ValueError('Eurostat mass metadata changed')
 return {'selected_facts_match':True,'pdf_pages_inspected':[23,24,25,80],'enagas_workbook':'Pág. 25!B12:E12; E4=2025; E12 is a literal fraction','eurostat_workbook':'VISUAL 2!A1:A2, D4:E9; E9 is a literal percentage','mass_data_also_available':'Natural gas (liq) partners!A15:C19; mass is not GWh','reconciliation':'unresolved PDF chart versus map/total and linked Excel; no cause inferred'}

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify-downloads');args=parser.parse_args()
 print(json.dumps(verify_downloads(args.verify_downloads) if args.verify_downloads else {k:str(v[0]) for k,v in calculate().items()},ensure_ascii=False,indent=2))
