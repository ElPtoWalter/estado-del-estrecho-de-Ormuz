"""Synthetic metric fixtures only; no private query or account export in Git."""
import copy
from datetime import date,timedelta
from pathlib import Path
import re,tempfile,unittest
import seo_surface as seo
import search_console_report as report
import build_public_site as public
import history_release,energy_release,spain_release


class SearchConsoleReportTests(unittest.TestCase):
    def daily(self):
        start=date(2026,8,29)
        return [{'date':(start+timedelta(days=i)).isoformat(),'clicks':1 if i<28 else 2,'impressions':100 if i<28 else 50,'position':10 if i<28 else 5} for i in range(56)]
    def test_equal_adjacent_windows_and_weighted_ctr(self):
        r=report.compare(self.daily(),'2026-10-23')
        self.assertEqual((r['previous']['start'],r['previous']['end']),('2026-08-29','2026-09-25'))
        self.assertEqual((r['current']['start'],r['current']['end']),('2026-09-26','2026-10-23'))
        self.assertTrue(r['comparison_valid']);self.assertEqual(r['change']['clicks']['percent'],100)
        self.assertEqual(r['change']['ctr_percentage_points'],3)
        m=report.metrics([{'clicks':1,'impressions':2,'position':2},{'clicks':1,'impressions':98,'position':10}])
        self.assertEqual(m['ctr_percent'],2);self.assertAlmostEqual(m['position_reconstructed_approx'],9.84)
    def test_missing_days_never_become_zero_or_growth(self):
        r=report.compare(self.daily()[1:],'2026-10-23')
        self.assertFalse(r['comparison_valid']);self.assertEqual(r['previous']['missing_days'],['2026-08-29']);self.assertEqual(r['change'],{})
    def test_duplicate_wrong_dimensions_and_search_type_rejected(self):
        rows=self.daily()
        for bad in (rows+[rows[0]],[{**r,'device':'MOBILE'} for r in rows],[{**r,'search_type':'image'} for r in rows]):
            with self.assertRaises(ValueError):report.compare(bad,'2026-10-23')
    def test_zero_baseline_and_invalid_metrics(self):
        rows=self.daily()
        for r in rows[:28]:r['clicks']=0
        self.assertIsNone(report.compare(rows,'2026-10-23')['change']['clicks']['percent'])
        for v in (-1,float('nan'),float('inf'),None):
            with self.assertRaises(ValueError):report.metrics([{'clicks':v,'impressions':10,'position':1}])
    def test_private_paths_and_provenance_fail_closed(self):
        with self.assertRaises(ValueError):report.private_path(report.ROOT/'private-export.json')
        with tempfile.TemporaryDirectory() as t:self.assertEqual(report.private_path(Path(t)/'data.json'),(Path(t)/'data.json').resolve())
        with self.assertRaises(ValueError):report.make_report(self.daily(),[],[],'2026-10-23',28,{'site':report.SITE})
    def test_query_coverage_is_not_a_replacement_for_page_totals(self):
        page='https://estrechoormuz.com/en.html'
        r=report.page_audit([{'page':page,'clicks':2,'impressions':100,'position':8}],[{'page':page,'clicks':1,'impressions':10,'position':5}])[0]
        self.assertEqual(r['impressions'],100);self.assertEqual(r['query_impression_fraction'],.1);self.assertFalse(r['query_table_is_complete'])
    def test_page_comparisons_preserve_missing_and_zero_ctr(self):
        a={'page':'https://estrechoormuz.com/en.html','clicks':0,'impressions':100,'position':8}
        b={**a,'clicks':2,'impressions':200,'position':7}
        r=report.compare_pages([a],[b,{**b,'page':'https://estrechoormuz.com/new.html'}])
        self.assertEqual(r[0]['change']['ctr_percentage_points'],1)
        self.assertIsNone(r[1]['previous']);self.assertIsNone(r[1]['change'])


class SEOPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reviews=public.load_json('editorial-reviews.json',{})
    def baseline(self,name):
        # Source snapshots are generated exactly as the existing public builder.
        text=public.sanitize_html((public.ROOT/name).read_text(encoding='utf-8'),name)
        lang=seo.PAGES[name][0]
        asides=''.join(f'<aside class="content-section prose-card"><h2><a href="/{path}">{title}</a></h2></aside>' for path,title,*_ in seo.RESEARCH[lang])
        return text.replace('</main>',asides+'</main>')
    def test_four_surfaces_preserve_canonical_assessment_and_consolidate_links(self):
        for name,(lang,kind) in seo.PAGES.items():
            before=self.baseline(name);after=seo.transform(before,name)
            if kind=='home':
                block=lambda t:re.search(r'<!-- STATUS_SNAPSHOT_START -->.*?<!-- STATUS_SNAPSHOT_END -->',t,re.S)[0]
                self.assertEqual(block(before),block(after))
                self.assertIn('data-seo-jump',after);self.assertIn('data-seo-scope',after)
                self.assertNotIn('data-seo-jump',re.search(r'<div class="hero-actions">.*?</div>',after,re.S)[0])
            self.assertEqual(after.count('data-seo-research'),1)
            for path,*_ in seo.RESEARCH[lang]:self.assertEqual(after.count(f'href="/{path}"'),1)
            self.assertEqual(after,seo.transform(after,name))
    def test_research_follows_status_or_hero_not_the_footer(self):
        for name,(lang,kind) in seo.PAGES.items():
            t=seo.transform(self.baseline(name),name);nodes=seo.Regions(t).nodes
            section=next((a,b) for a,b,tag,d in nodes if 'data-seo-research' in d)
            anchor=next((a,b) for a,b,tag,d in nodes if tag=='section' and (d.get('id')==('estado-actual' if lang=='es' else 'current-status') if kind=='home' else 'v11-hero' in d.get('class','').split()))
            self.assertEqual(section[0],anchor[1])
    def test_home_metadata_does_not_promise_ais_measurements(self):
        for name in ('index.html','en.html'):
            t=seo.transform(self.baseline(name),name);head=t.split('</head>')[0]
            self.assertNotIn('with verifiable evidence, AIS traffic',head);self.assertNotIn('tráfico AIS, historial',head)
            self.assertIn('data-seo-scope',t)
    def test_only_four_landing_pages_are_mutated(self):
        for release in (history_release,energy_release,spain_release):
            files,reviews=release.verify()
            for name,raw in release.render(files,reviews).items():
                if name.endswith('.html'):self.assertEqual(seo.transform(raw.decode('utf-8'),name).encode('utf-8'),raw)
    def test_missing_sealed_navigation_blocks_instead_of_inventing_a_publication(self):
        t=public.sanitize_html((public.ROOT/'index.html').read_text(encoding='utf-8'),'index.html')
        with self.assertRaises(ValueError):seo.transform(t,'index.html')


if __name__=='__main__':unittest.main()
