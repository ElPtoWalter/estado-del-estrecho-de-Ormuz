"""Third report: incompatible units cannot become an exposure ranking."""
import csv,io,json,re,unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
import spain_data as data
import spain_editorial as editorial
import build_public_site as public
import build_sitemap as sitemap
from publication_quality import original_review_valid,apply_policy

class SpainEditorialTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.files=editorial.verify()

 def test_selected_official_units_and_period_are_exact(self):
  rows={r['metric']:r for r in data.read_inputs()}
  self.assertEqual(len(rows),6)
  self.assertEqual(rows['eu_qatar_value_share']['unit'],'percent_of_trade_value')
  self.assertEqual(rows['qatar_excel_fraction']['unit'],'fraction')
  self.assertEqual({rows[k]['unit'] for k in ('es_total','es_lng','qatar_map')},{'GWh'})
  for old,new in [('372498','372499'),('percent_of_trade_value','percent_of_volume'),('2025','2026')]:
   with patch.object(Path,'read_text',return_value=data.INPUT.read_text(encoding='utf-8').replace(old,new)):
    with self.assertRaises(ValueError):data.read_inputs()

 def test_denominators_and_fraction_conversion_have_independent_expected_results(self):
  values=data.calculate()
  self.assertAlmostEqual(values['es_total_share'][0],Decimal('1.718935403680019758495347626'),places=24)
  self.assertAlmostEqual(values['es_lng_share'][0],Decimal('2.580980635591170732493832734'),places=24)
  self.assertEqual(values['excel_share'][0],Decimal('1.71889077090790500'))
  self.assertEqual(values['implied_qatar_volume'][0],Decimal('6462.8403'))
  self.assertEqual(values['implied_minus_map'][0],Decimal('59.8403'))
  self.assertEqual(values['eu_news_rounded'][0],Decimal('8.9'))
  self.assertEqual(values['pdf_minus_quotient'][1],'percentage_points')
  self.assertNotIn('relative_risk',values);self.assertNotIn('lost_energy',values)

 def test_csv_preserves_all_six_inputs_and_eight_explained_results(self):
  inputs=list(csv.DictReader(io.StringIO(self.files[f'{editorial.ASSETS}/source-inputs.csv'].decode())))
  rows=list(csv.DictReader(io.StringIO(self.files[f'{editorial.ASSETS}/calculations.csv'].decode())))
  self.assertEqual(len(inputs),6);self.assertEqual(len(rows),8)
  for r in inputs:self.assertTrue(r['source'].startswith('https://'));self.assertTrue(r['locator']);self.assertEqual(r['period'],'2025')
  self.assertEqual(next(r for r in rows if r['calculation']=='excel_minus_quotient')['value'],'-0.00004463')
  for r in rows:self.assertTrue(r['formula']);self.assertTrue(r['interpretation'])
  editorial.audit_payload(self.files)
  for name in ('source-inputs.csv','calculations.csv'):
   with self.assertRaises(ValueError):editorial.audit_payload({f'{editorial.ASSETS}/{name}':b'value\n=WEBSERVICE("https://example.org")\n'})

 def test_original_four_drafts_remain_unchanged_and_discrepancy_is_unresolved(self):
  record=json.loads((editorial.FOLDER/'source-verification.json').read_text(encoding='utf-8'))
  for name,digest in record['original_draft_sha256_lf'].items():self.assertEqual(data.sha((data.ROOT/'drafts/adsense-20261024'/name).read_bytes()),digest)
  self.assertIn('unresolved',record['selected_data_checks']['reconciliation'])
  self.assertIsNone(record['human_editorial_approval'])
  self.assertTrue(all(r['status']==200 for r in record['http'].values()))

 def test_exact_fifteen_resources_and_no_silent_resealing(self):
  self.assertEqual(len(self.files),15)
  self.assertEqual(sum(n.endswith('.svg') for n in self.files),8)
  self.assertEqual(sum(n.endswith('.csv') for n in self.files),2)
  original=data.sha
  with patch.object(data,'sha',side_effect=lambda b:'tampered' if b==b'<changed>' else original(b)):
   changed=dict(self.files);changed[next(iter(editorial.ARTICLES.values()))]=b'<changed>'
   with patch.object(editorial,'files',return_value=changed):
    with self.assertRaises(ValueError):editorial.verify()

 def test_four_pages_have_reciprocal_seo_but_no_publication_or_ads(self):
  manifest=json.loads(editorial.MANIFEST.read_text(encoding='utf-8'))
  self.assertFalse(manifest['publication_authorized']);self.assertIsNone(manifest['human_editorial_approval'])
  self.assertIsNone(manifest['reviewer']);self.assertFalse(manifest['advertising'])
  reviews=json.loads((data.ROOT/'editorial-reviews.json').read_text(encoding='utf-8'))
  for pair in (editorial.ARTICLES,editorial.METHODS):
   for lang,name in pair.items():
    text=self.files[name].decode();meta=sitemap.MetaParser();meta.feed(text)
    self.assertIn('noindex',meta.robots);self.assertEqual(meta.canonical,public.DOMAIN+'/'+name)
    self.assertEqual(meta.alternates,{k:public.DOMAIN+'/'+v for k,v in {**pair,'x-default':pair['es']}.items()})
    self.assertIn('data-draft-disclosure',text);self.assertIn('publisher-ads" content="disabled',text)
    self.assertNotIn(name,reviews)
    self.assertFalse(public.public_html_path((editorial.SOURCE/name).relative_to(data.ROOT)))
    self.assertNotRegex(text,r'\.json\b|\.py\b|mailto:|pub-\d+|ElPtoWalter|Eduardo|<script')
    self.assertEqual(len(re.findall(r'<a\b[^>]*href="[^"]+\.csv"',text)),2)

 def test_past_approvals_cannot_release_or_monetise_third_draft(self):
  reviews=json.loads((data.ROOT/'editorial-reviews.json').read_text(encoding='utf-8'))
  for name in (*editorial.ARTICLES.values(),*editorial.METHODS.values()):
   text=self.files[name].decode()
   for review in reviews.values():
    self.assertFalse(original_review_valid(text,review))
    rendered=apply_policy(text,name,programmatic_ads=True,review=review)
    self.assertIn('noindex',rendered);self.assertNotIn('data-original-review',rendered)
    self.assertIn('publisher-ads" content="disabled',rendered);self.assertNotIn('adsbygoogle',rendered)

 def test_all_graphs_are_safe_legible_and_never_compare_spanish_with_eu_share(self):
  audit=json.loads((editorial.FOLDER/'chart-audit.json').read_text())
  self.assertEqual(len(audit),8)
  for name,row in audit.items():
   self.assertTrue(row['text_within_figure']);self.assertFalse(row['label_title_source_overlap']);self.assertFalse(row['eu_risk_comparison'])
   self.assertEqual(row['source_input_sha256_lf'],data.sha(data.INPUT.read_bytes()))
   text=self.files[f'{editorial.ASSETS}/{name}'].decode()
   self.assertNotRegex(text,r'<script|<image|foreignObject|8[.,]9\s?%')
   self.assertIn('<title>',text);self.assertIn('<desc>',text)

 def test_only_two_exact_csv_routes_are_permitted(self):
  for name in editorial.CSV_NAMES:self.assertTrue(public.copy_asset(Path(editorial.ASSETS)/name))
  for name in ('private.csv','nested/source-inputs.csv','calculations.json','render_charts.py'):
   self.assertFalse(public.copy_asset(Path(editorial.ASSETS)/name))

 def test_both_languages_preserve_meaning_limits_sources_and_earlier_links(self):
  for lang,name in editorial.ARTICLES.items():
   text=self.files[name].decode()
   for url in (data.ENAGAS,data.ENAGAS_XLSX,data.EUROSTAT,data.EUROSTAT_XLSX):self.assertIn(url,text)
   for term in ('372.498','6.403','248.084','1,735','8,9','0,016065') if lang=='es' else ('372,498','6,403','248,084','1.735','8.9','0.016065'):self.assertIn(term,text)
   self.assertIn('historiales-monitor-ormuz.html' if lang=='es' else 'en-monitor-archives-hormuz.html',text)
   self.assertIn('ormuz-cierre-paso-flujos.html' if lang=='es' else 'en-hormuz-closure-passage-flows.html',text)
   self.assertIn('Sin conciliación causal' if lang=='es' else 'No cause established',text)
   self.assertIn('role="region" tabindex="0"',text);self.assertIn('<caption>',text)
   self.assertEqual(len(re.findall(r'<picture>',text)),2)

if __name__=='__main__':unittest.main()
