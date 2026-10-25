"""Six-quarter arithmetic, evidence boundaries and private editorial selection."""
import copy,csv,io,json,re,tempfile,unittest
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET
import energy_data as data
import energy_editorial as editorial
import build_public_site as public
import build_sitemap as sitemap
from publication_quality import apply_policy,original_review_valid
from own_projects import add_promotions


class EnergyEditorialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.files=editorial.verify()

    def test_all_twelve_official_values_and_order_are_preserved(self):
        rows=data.read_rows();self.assertEqual(len(rows),6)
        self.assertEqual([(r['period'],r['oil_million_barrels_per_day'],r['lng_billion_cubic_feet_per_day']) for r in rows],list(data.EXPECTED))
        receipt=json.loads((data.FOLDER/'source-verification.json').read_text())
        self.assertTrue(all(c['http_status']==200 for c in receipt['checks']))
        eia=receipt['checks'][0];self.assertEqual(eia['release'],'2026-08-12')
        self.assertEqual(eia['selected_rows']['oil'],[r[1] for r in data.EXPECTED])
        self.assertEqual(eia['selected_rows']['lng'],[r[2] for r in data.EXPECTED])

    def test_headlines_quarter_changes_and_sensitivity_use_separate_units(self):
        rows,c=data.calculate()
        expected={'2025_path':('3.34928230','-10.25641026'),
                  '2026q1_vs_2025q4':('-31.01851852','-29.52380952'),
                  '2026q2_vs_2026q1':('-67.11409396','-89.18918919'),
                  'headline_2026q2_vs_2025q4':('-77.31481481','-92.38095238'),
                  'sensitivity_2026q2_vs_2025q1':('-76.55502392','-93.16239316')}
        for label,values in expected.items():self.assertEqual((c[label]['oil_pct'],c[label]['lng_pct']),values)
        self.assertEqual(rows[3]['oil_index_2025q4_100'],'100.00000000')
        self.assertEqual(rows[3]['lng_index_2025q4_100'],'100.00000000')
        self.assertEqual(rows[5]['oil_index_2025q4_100'],'22.68518519')
        self.assertEqual(rows[5]['lng_index_2025q4_100'],'7.61904762')
        self.assertEqual(rows[0]['oil_change_previous_quarter_pct'],'')
        for baseline in (0,-1):
            with self.assertRaises(ValueError):data.pct(10,baseline)

    def test_csv_is_reproducible_typed_numbers_not_formula_cells(self):
        raw=self.files[f'{editorial.ASSETS}/energy-series.csv'];self.assertEqual(raw.decode(),data.csv_text())
        records=list(csv.DictReader(io.StringIO(raw.decode())))
        self.assertEqual(tuple(records[0]),data.FIELDS)
        for row in records:
            for field in data.FIELDS[1:7]:
                if row[field]:Decimal(row[field])
                self.assertNotRegex(row[field],r'^[=+@]')
        self.assertNotEqual(records[4]['oil_change_previous_quarter_pct'],records[4]['lng_change_previous_quarter_pct'])

    def test_four_html_have_reciprocal_metadata_and_no_ad_inventory(self):
        approvals=json.loads((data.ROOT/'editorial-reviews.json').read_text())
        for pair in (editorial.ARTICLES,editorial.METHODS):
            expected={key:public.DOMAIN+'/'+slug for key,slug in {**pair,'x-default':pair['es']}.items()}
            for name in pair.values():
                text=self.files[name].decode();p=sitemap.MetaParser();p.feed(text)
                self.assertEqual(p.canonical,public.DOMAIN+'/'+name);self.assertEqual(p.alternates,expected)
                self.assertIn('noindex',p.robots);self.assertIn('publisher-ads" content="disabled',text)
                self.assertIsNone(approvals.get(name));self.assertFalse(public.public_html_path((editorial.SOURCE/name).relative_to(data.ROOT)))
                for old_review in approvals.values():self.assertFalse(original_review_valid(text,old_review))
                rendered=apply_policy(text,name,programmatic_ads=True,review=next(iter(approvals.values())))
                self.assertIn('noindex',rendered);self.assertNotIn('data-original-review',rendered)
                self.assertEqual(add_promotions(text,'drafts/energy-flows-20261025/'+name,'ormuz'),text)

    def test_public_references_have_no_internal_code_configuration_or_personal_data(self):
        for name,raw in self.files.items():
            if name.endswith('.html'):
                text=raw.decode();self.assertNotRegex(text,r'\.json\b|\.py\b|github\.com|mailto:|ElPtoWalter|Eduardo|<script|<iframe|<form')
                self.assertEqual(text.count('<h1>'),1);self.assertIn('class="skip"',text)
                self.assertNotRegex(text,r'\{\{\w+\}\}')
                for table in re.findall(r'<table>.*?</table>',text,re.S):self.assertIn('<caption>',table)

    def test_eight_safe_graphs_cover_both_units_languages_and_viewports(self):
        graphs={n:b for n,b in self.files.items() if n.endswith('.svg')};self.assertEqual(len(graphs),8)
        audit=json.loads((data.FOLDER/'chart-audit.json').read_text())
        for name,raw in graphs.items():
            root=ET.fromstring(raw);self.assertEqual(root.get('role'),'img')
            text=raw.decode();self.assertNotRegex(text,r'<script|<foreignObject|<image')
            record=audit[Path(name).name];self.assertEqual(record['quarters'],6);self.assertEqual(record['series'],2)
            self.assertFalse(record['value_label_overlap']);self.assertTrue(record['value_labels_within_figure'])
            self.assertFalse(record['title_units_source_overlap'])
            self.assertEqual(record['source_input_sha256_lf'],data.sha(data.INPUT.read_bytes()))
            if 'absolute' in name:self.assertIn('21,6' if '-es' in name else '21.6',text)

    def test_csv_public_exception_is_one_exact_destination(self):
        route=f'{editorial.ASSETS}/energy-series.csv'
        self.assertTrue(public.copy_asset(Path(route)))
        for route in ('energy-series.csv',f'{editorial.ASSETS}/private.csv',f'{editorial.ASSETS}/sources.json',f'{editorial.ASSETS}/render_charts.py'):
            self.assertFalse(public.copy_asset(Path(route)),route)

    def test_tampered_asset_or_approval_state_fails_integrity(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'manifest.json';record=editorial.manifest(self.files);record['human_editorial_approval']='invented';path.write_text(json.dumps(record))
            with patch.object(editorial,'MANIFEST',path):
                with self.assertRaises(ValueError):editorial.verify()
        for name,bad in [(f'{editorial.ASSETS}/energy-series.csv',b'x\n=HYPERLINK("bad")'),('private.json',b'{}')]:
            with self.assertRaises(ValueError):editorial.audit_payload({name:bad})

    def test_noindex_draft_cannot_enter_a_sitemap(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name,raw in self.files.items():
                if name.endswith('.html'):(root/name).write_bytes(raw)
            self.assertEqual(sitemap.discover_pages(root),[])
        record=json.loads(editorial.MANIFEST.read_text())
        self.assertFalse(record['publication_authorized']);self.assertFalse(record['index']);self.assertFalse(record['advertising'])
        self.assertIsNone(record['human_editorial_approval']);self.assertIsNone(record['reviewer']);self.assertIsNone(record['reviewed_at'])


if __name__=='__main__':unittest.main()
