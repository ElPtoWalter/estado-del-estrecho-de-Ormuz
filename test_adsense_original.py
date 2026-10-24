"""Regressions for publisher verification and the boundaries of original research."""
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import adsense_checks as ads
import original_research as research
from publication_quality import apply_policy
import build_public_site as build

ROOT = Path(__file__).parent
PUBLISHER = 'pub-1713078636060241'
LINE = f'google.com, {PUBLISHER}, DIRECT, f08c47fec0942fa0\n'.encode()


class AdsTxtChecks(unittest.TestCase):
    def test_public_html_or_a_wrong_account_cannot_pass_as_ads_txt(self):
        for raw in (b'<html>Not found</html>', LINE.replace(PUBLISHER.encode(), b'pub-0000000000000000'),
                    b'\xef\xbb\xbf'+LINE, LINE+LINE, b'google.com, ca-pub-1713078636060241, DIRECT, f08c47fec0942fa0'):
            self.assertTrue(ads.validate_ads_txt(raw, PUBLISHER))
        self.assertEqual(ads.validate_ads_txt(b'# Authorized seller\n'+LINE+b'\n', PUBLISHER), [])

    def test_a_missing_artifact_file_or_inconsistent_meta_is_an_error(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'index.html').write_text(f'<meta name="google-adsense-account" content="ca-{PUBLISHER}">')
            self.assertTrue(ads.check_artifact(root))
            (root/'ads.txt').write_bytes(LINE)
            self.assertEqual(ads.check_artifact(root), [])
            (root/'en.html').write_text('<meta content="ca-pub-0000000000000000" name="google-adsense-account">')
            self.assertTrue(ads.check_artifact(root))

    def test_duplicate_publisher_meta_cannot_define_an_account(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'index.html').write_text(('<meta name="google-adsense-account" content="ca-'+PUBLISHER+'">')*2)
            with self.assertRaises(ValueError):ads.publisher_id(root)


class ResearchChecks(unittest.TestCase):
    def test_equal_windows_keep_boundaries_and_models_separate_even_if_unsorted(self):
        rows=[{'model':'v7','at':date,'state':'OPEN_SEVERELY_RESTRICTED','confidence':'MEDIA','traffic_ratio_available':False}
              for date in ('2026-10-21T23:59:59Z','2026-09-10T00:00:00Z','2026-09-30T23:59:59Z','2026-10-01T00:00:00Z','2026-09-09T23:59:59Z')]
        rows.append(dict(rows[0],model='legacy',state='INCIERTO'))
        first,second=research.compare_windows(rows)
        self.assertEqual([first['records'],second['records']],[2,2])
        self.assertEqual(first['end_exclusive'],second['start_inclusive'])
        self.assertEqual(second['records_with_traffic_ratio'],0)
        self.assertEqual(second['states'],{'OPEN_SEVERELY_RESTRICTED':2})

    def test_duplicate_or_unzoned_timestamps_require_resolution(self):
        for date in ('2026-10-21T12:00:00','2026-10-21T12:00:00Z'):
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp)
                row={'at':date,'status':'INCIERTO'}
                (root/'history.json').write_text(json.dumps([row,row]))
                (root/'operational-intelligence-history.json').write_text('[]')
                with self.assertRaises(ValueError):research.monitor_rows(root)

    def test_zero_is_a_measurement_and_missing_data_is_not_a_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'history.json').write_text('[]')
            row={'generated_at':'2026-10-21T12:00:00Z','state':'TEST','traffic_ratio_estimate':0,'traffic_snapshot':None}
            (root/'operational-intelligence-history.json').write_text(json.dumps([row]))
            result=research.monitor_rows(root)[0]
            self.assertTrue(result['traffic_ratio_available'])
            self.assertFalse(result['traffic_snapshot_available'])

    def test_frozen_comparison_and_energy_units_match_the_draft_claims(self):
        root=ROOT/'drafts/adsense-20261024'
        summary=json.loads((root/'monitor-summary.json').read_text(encoding='utf-8'))
        self.assertEqual([w['records'] for w in summary['comparison']],[11,10])
        self.assertEqual([w['days_with_retained_record'] for w in summary['comparison']],[8,7])
        with (root/'energy-context.csv').open(encoding='utf-8',newline='') as stream:rows=list(csv.DictReader(stream))
        self.assertAlmostEqual((float(rows[-1]['oil_million_barrels_per_day'])/float(rows[3]['oil_million_barrels_per_day'])-1)*100,-77.3148148148)
        self.assertAlmostEqual((float(rows[-1]['lng_billion_cubic_feet_per_day'])/float(rows[3]['lng_billion_cubic_feet_per_day'])-1)*100,-92.38095238095)
        with (root/'spain-eu-context.csv').open(encoding='utf-8',newline='') as stream:bases=list(csv.DictReader(stream))
        self.assertNotEqual(bases[0]['denominator'],bases[1]['denominator'])

    def test_frozen_originals_stay_private_and_cannot_receive_house_ads(self):
        from own_projects import add_promotions
        from validate_site import public_html_files
        folder=ROOT/'drafts/adsense-20261024'
        pages=list(folder.glob('*.html'))
        self.assertEqual(len(pages),6)  # Three stories with two language versions.
        public_sources=set(public_html_files(ROOT))
        for page in pages:
            text=page.read_text(encoding='utf-8')
            self.assertFalse(build.public_html_path(page.relative_to(ROOT)))
            self.assertNotIn(page,public_sources)
            self.assertIn('content="noindex,follow"',text)
            self.assertIn('data-draft-disclosure',text)
            self.assertEqual(add_promotions(text,page.relative_to(ROOT).as_posix(),'ormuz'),text)
            self.assertNotIn('adsbygoogle',text)

    def test_automatic_original_report_and_held_guide_require_review(self):
        page='<html lang="es"><head><meta name="content-kind" content="original-draft"></head><body><main><p>Datos propios</p></main></body></html>'
        result=apply_policy(page,'datos-propios-monitor-ormuz.html',programmatic_ads=True)
        self.assertIn('noindex',result);self.assertIn('data-draft-disclosure',result)
        result=apply_policy(page.replace('content-kind','other'),'importancia.html',programmatic_ads=True)
        self.assertIn('data-editorial-hold',result);self.assertIn('noindex',result)
        self.assertEqual(apply_policy(result,'importancia.html').count('data-editorial-hold'),1)

    def test_old_generator_stamp_is_not_a_human_review(self):
        page='<html><head></head><body><main>Revisión documental realizada el 4 de agosto de 2026. Se actualiza si cambian los datos fuente.</main></body></html>'
        result=apply_policy(page,'guide.html')
        self.assertNotIn('Revisión documental realizada',result)
        self.assertIn('no consta una revisión humana',result)


if __name__=='__main__':unittest.main()
