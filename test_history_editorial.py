"""Data, layout and publication boundaries for the independent history article."""
from collections import Counter
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

import build_public_site as build
from build_sitemap import MetaParser
from check_public_links import References
from own_projects import add_promotions
from publication_quality import apply_policy

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT/'drafts/historiales-20261024'
spec = importlib.util.spec_from_file_location('history_reproduce', FOLDER/'reproduce.py')
research = importlib.util.module_from_spec(spec)
spec.loader.exec_module(research)


class HistoryEditorialTests(unittest.TestCase):
    def test_frozen_csv_matches_its_pinned_hash_and_the_original_dataset(self):
        sources = json.loads((FOLDER/'sources.json').read_text(encoding='utf-8'))['sources']
        self.assertEqual(research.digest(FOLDER/'monitor-observations.csv'), sources[2]['sha256_lf'])
        self.assertEqual(Counter(r['model'] for r in research.read_rows()), {'legacy': 54, 'v7': 49})
        summary = json.loads((FOLDER/'source-summary.json').read_text(encoding='utf-8'))
        self.assertEqual({s['path']: s['sha256_lf'] for s in sources[:2]}, summary['inputs_sha256'])
        self.assertEqual((FOLDER/'monitor-observations.csv').read_bytes(),
                         (ROOT/'drafts/adsense-20261024/monitor-observations.csv').read_bytes())

    def test_confidence_counts_and_high_dates_do_not_contaminate_the_equal_windows(self):
        result = research.analyse(research.read_rows())
        self.assertEqual(result['models'][1]['confidence'], {'ALTA': 2, 'MEDIA': 47})
        self.assertEqual(result['v7_high_confidence_dates_utc'], ['2026-08-07T12:21:33Z', '2026-09-02T11:41:03Z'])
        self.assertEqual([w['records'] for w in result['windows']], [11, 10])
        self.assertEqual([w['days_with_record'] for w in result['windows']], [8, 7])
        self.assertEqual([w['confidence'] for w in result['windows']], [{'MEDIA': 11}, {'MEDIA': 10}])
        self.assertEqual(result['v7_rows_with_numeric_traffic_ratio'], 0)
        self.assertEqual(result['v7_rows_with_traffic_snapshot'], 0)

    def test_half_open_utc_boundaries_do_not_count_the_same_row_twice(self):
        base = {'model': 'v7', 'state': 'OPEN_SEVERELY_RESTRICTED', 'confidence': 'MEDIA',
                'traffic_ratio_available': 'False', 'traffic_snapshot_available': 'False'}
        rows = [dict(base, at=date) for date in ('2026-09-09T23:59:59Z', '2026-09-10T00:00:00Z',
                '2026-09-30T23:59:59Z', '2026-10-01T02:00:00+02:00', '2026-10-21T23:59:59Z', '2026-10-22T00:00:00Z')]
        rows.append(dict(base, model='legacy', at='2026-09-10T00:00:00Z'))
        result = research.analyse(rows)
        self.assertEqual([w['records'] for w in result['windows']], [2, 2])
        self.assertEqual(research.utc('2026-10-01T02:00:00+02:00'), research.utc('2026-10-01T00:00:00Z'))
        with self.assertRaises(ValueError):
            research.utc('2026-10-01T00:00:00')

    def test_regeneration_rejects_a_changed_frozen_input(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = (FOLDER/'monitor-observations.csv').read_bytes()
            (root/'monitor-observations.csv').write_bytes(original.replace(b'ALTA', b'MEDIA', 1))
            with self.assertRaisesRegex(ValueError, 'Frozen input changed'):
                research.outputs(root)
        for name, text in research.outputs().items():
            self.assertEqual((FOLDER/name).read_text(encoding='utf-8'), text)

    def test_all_rendered_svg_points_are_present_and_separated(self):
        ns = {'s': 'http://www.w3.org/2000/svg'}
        for lang in ('es', 'en'):
            svg = FOLDER/f'history-timeline-{lang}.svg'
            self.assertIn('sans-serif', svg.read_text(encoding='utf-8'))
            self.assertTrue((FOLDER/f'history-confidence-mobile-{lang}.svg').is_file())
            tree = ET.parse(svg)
            counts = []
            for ax in tree.findall('.//s:g', ns):
                if not ax.get('id', '').startswith('axes_'):
                    continue
                points = [(float(u.get('x')), float(u.get('y')))
                          for collection in ax.findall('./s:g', ns) if collection.get('id', '').startswith('PathCollection_')
                          for u in collection.findall('.//s:use', ns)]
                counts.append(len(points))
                self.assertEqual(len(points), len(set(points)))
                self.assertGreater(min(math.dist(a, b) for i, a in enumerate(points) for b in points[i+1:]), 8.0)
            self.assertEqual(counts, [54, 49])

    def test_metadata_prepares_reciprocal_routes_without_indexing_or_claiming_publication(self):
        plan = json.loads((FOLDER/'publication-plan.json').read_text(encoding='utf-8'))
        for lang, filename in (('es', 'historiales-monitor-ormuz.html'), ('en', 'en-monitor-archives-hormuz.html')):
            text = (FOLDER/filename).read_text(encoding='utf-8')
            parser = MetaParser(); parser.feed(text)
            self.assertEqual(parser.lang, lang)
            self.assertEqual(parser.canonical, plan['routes'][lang])
            self.assertEqual(parser.alternates, plan['routes'])
            self.assertIn('noindex', parser.robots)
            self.assertIn('data-draft-disclosure', text)
            self.assertIn('name="publisher-ads" content="disabled"', text)
            self.assertNotIn('datePublished', text)
            self.assertNotIn('<script', text)

    def test_resources_and_immutable_source_links_are_consistent(self):
        sources = json.loads((FOLDER/'sources.json').read_text(encoding='utf-8'))['sources']
        allowed = {s['url'] for s in sources}
        for page in FOLDER.glob('*.html'):
            parser = References(); parser.feed(page.read_text(encoding='utf-8'))
            self.assertEqual(sum('history-' in ref and ref.endswith('.svg') for ref in parser.refs), 2)
            for ref in parser.refs:
                url = urlsplit(ref)
                if url.scheme or url.netloc:
                    if '/blob/' in ref:
                        self.assertIn(ref, allowed)
                    continue
                self.assertTrue((page.parent/url.path).is_file() if url.path else url.fragment in parser.ids, ref)

    def test_new_draft_cannot_enter_public_selection_or_ad_inventory(self):
        for page in FOLDER.glob('*.html'):
            text = page.read_text(encoding='utf-8')
            relative = page.relative_to(ROOT)
            self.assertFalse(build.public_html_path(relative))
            self.assertEqual(add_promotions(text, relative.as_posix(), 'ormuz'), text)
            accidental_public_copy = apply_policy(text, page.name, programmatic_ads=True)
            self.assertIn('noindex', accidental_public_copy)
            self.assertNotIn('adsbygoogle', accidental_public_copy)
        plan = json.loads((FOLDER/'publication-plan.json').read_text(encoding='utf-8'))
        self.assertIs(plan['publish'], False)
        self.assertIs(plan['index'], False)
        self.assertIs(plan['advertising'], False)
        self.assertIsNone(plan['human_editorial_approval'])

    def test_manifest_does_not_turn_owner_data_checks_into_editorial_approval(self):
        manifest = json.loads((FOLDER/'review-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['owner_verification_scope'], 'counts_and_windows_only')
        self.assertFalse(manifest['new_editorial_version_approved'])
        self.assertIsNone(manifest['reviewer'])
        self.assertIsNone(manifest['reviewed_at'])
        for name, digest in manifest['sha256_lf'].items():
            self.assertEqual(research.digest(FOLDER/name), digest, name)


if __name__ == '__main__':
    unittest.main()
