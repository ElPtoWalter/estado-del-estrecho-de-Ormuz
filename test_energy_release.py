"""PR #23: exact owner decision, authorised edits and permanent ad boundaries."""
import copy,json,re,tempfile,unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
import energy_data as data
import energy_editorial as candidate
import energy_release as release
import build_public_site as public
import build_sitemap as sitemap
from publication_quality import (ENERGY_ARTICLES,ENERGY_METHODS,ENERGY_NO_ADS,
    HISTORY_NO_ADS,ENERGY_APPROVED_COMMIT,owner_energy_review_valid,owner_history_review_valid,apply_policy)


class Plain(HTMLParser):
    def __init__(self):super().__init__();self.parts=[]
    def handle_data(self,s):self.parts.append(s)
    def text(self):return re.sub(r'\s+',' ',''.join(self.parts)).strip()


class EnergyReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.files,cls.reviews=release.verify()

    def test_evidence_is_real_scoped_and_keeps_original_manifest_immutable(self):
        record=json.loads(release.RECORD.read_text(encoding='utf-8'))
        self.assertEqual(record['approved_candidate_commit'],ENERGY_APPROVED_COMMIT)
        self.assertEqual(record['sha256_lf'],candidate.manifest(self.files)['sha256_lf'])
        for key in ('merge_authorized','deployment_authorized','advertising_authorized','personal_data_publication_authorized'):
            self.assertFalse(record[key])
        original=json.loads(candidate.MANIFEST.read_text(encoding='utf-8'))
        self.assertIsNone(original['human_editorial_approval']);self.assertIsNone(original['reviewer'])
        for name in ENERGY_NO_ADS:
            review=self.reviews[name]
            for absent in ('reviewer','reviewed_at','facts_checked','rights_checked'):self.assertNotIn(absent,review)
            self.assertTrue(owner_energy_review_valid(self.files[name].decode(),review))

    def test_only_exact_candidate_and_record_can_pass(self):
        for name in ENERGY_NO_ADS:
            text=self.files[name].decode();review=self.reviews[name]
            self.assertFalse(owner_energy_review_valid(text+'changed',review))
            for key,bad in [('approved',False),('approval_reference','technical assessment'),('document','other.html'),
                            ('public_author','Unnamed reviewer'),('approved_candidate_commit','0'*40),('evidence_recorded_at','2099-01-01')]:
                altered=dict(review);altered[key]=bad
                self.assertFalse(owner_energy_review_valid(text,altered),(name,key))
            self.assertIn('noindex',apply_policy(text+'changed',name,review=review))

    def test_first_and_second_approvals_are_not_interchangeable(self):
        from history_release import verify
        older,_=verify()
        history_name=next(iter(HISTORY_NO_ADS));energy_name=next(iter(ENERGY_ARTICLES))
        self.assertFalse(owner_energy_review_valid(older[history_name].decode(),self.reviews[energy_name]))
        self.assertFalse(owner_history_review_valid(self.files[energy_name].decode(),self.reviews[history_name]))

    def test_wrong_route_missing_record_or_tampered_manifest_fails_closed(self):
        name=next(iter(ENERGY_ARTICLES));text=self.files[name].decode()
        for route in ('other.html','diario/'+name):
            rendered=apply_policy(text,route,review=self.reviews[name])
            self.assertIn('noindex',rendered);self.assertNotIn('data-original-review',rendered)
        partial=copy.deepcopy(self.reviews);partial.pop(name)
        with self.assertRaises(ValueError):release.verify(partial)
        with patch.object(data,'sha',return_value='changed'):
            with self.assertRaises(ValueError):release.verify(self.reviews)

    def test_authorised_edits_preserve_all_factual_article_text(self):
        rendered=release.render(self.files,self.reviews)
        for lang,name in candidate.ARTICLES.items():
            before=self.files[name].decode();after=rendered[name].decode()
            before=re.sub(r'<a href="/assets/research/energy-flows-20261025/energy-series\.csv" download>(?:Datos y cálculos \(CSV\)|Data and calculations \(CSV\))</a>\.','',before)
            def article(text):
                parser=Plain();parser.feed(text[text.index('<article>'):text.index('</article>')]);return parser.text()
            self.assertEqual(article(before),article(after))
            guide='puede-estar-abierto-ormuz-aunque-caiga-trafico.html' if lang=='es' else 'en-can-hormuz-be-open-while-traffic-collapses.html'
            self.assertEqual(after.count('data-context-guide'),1);self.assertIn('href="/'+guide+'"',after)
            self.assertEqual(len(re.findall(r'<a\b[^>]*href="/assets/research/energy-flows-20261025/energy-series\.csv"',after)),1)

    def test_all_non_html_resources_remain_byte_for_byte_identical(self):
        rendered=release.render(self.files,self.reviews)
        for name,raw in self.files.items():
            if not name.endswith('.html'):self.assertEqual(rendered[name],raw,name)
        self.assertEqual(sum(n.endswith('.svg') for n in rendered),8)
        self.assertEqual(sum(n.endswith('.csv') for n in rendered),1)

    def test_two_articles_indexable_two_methods_noindex_and_all_ads_disabled(self):
        rendered=release.render(self.files,self.reviews)
        for name in ENERGY_NO_ADS:
            text=rendered[name].decode();meta=sitemap.MetaParser();meta.feed(text)
            self.assertEqual('noindex' in meta.robots,name in ENERGY_METHODS)
            self.assertEqual(meta.canonical,public.DOMAIN+'/'+name)
            self.assertNotRegex(text,r'Borrador|Draft for editorial|data-draft-disclosure|awaiting editorial approval|Sin autorización de publicación|Publication not authorised|ElPtoWalter|Eduardo')
            self.assertIn('asistencia de IA' if not name.startswith('en-') else 'AI assistance',text)
            if name in ENERGY_ARTICLES:self.assertIn('data-institutional-byline',text)
            self.assertIn('publisher-ads" content="disabled',text)
            forced=apply_policy(self.files[name].decode(),name,programmatic_ads=True,review=self.reviews[name])
            self.assertIn('publisher-ads" content="disabled',forced);self.assertNotIn('adsbygoogle',forced)

    def test_missing_kind_meta_cannot_bypass_the_energy_hold(self):
        for name in ENERGY_NO_ADS:
            text=self.files[name].decode().replace('<meta name="content-kind" content="original-draft">','')
            result=apply_policy(text,name,programmatic_ads=True)
            self.assertIn('noindex',result);self.assertIn('publisher-ads" content="disabled',result)

    def test_incoming_navigation_is_bilingual_and_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in ('index.html','en.html','analisis.html','en-analysis.html','historial.html','en-history.html'):
                (root/name).write_text('<main></main>',encoding='utf-8')
            release.integrate(root);release.integrate(root)
            for path in root.glob('*.html'):
                text=path.read_text();self.assertEqual(text.count('data-energy-analysis'),1)
                self.assertIn(candidate.ARTICLES['en' if path.name.startswith('en') else 'es'],text)

    def test_future_postdeploy_smoke_requires_fourteen_exact_resources_and_sitemap(self):
        import remote_smoke_test as smoke
        expected=release.render(self.files,self.reviews)
        tree=ET.Element('urlset',xmlns=sitemap.SITEMAP_NS)
        for name in ENERGY_ARTICLES:
            node=ET.SubElement(tree,'url');ET.SubElement(node,'loc').text=public.DOMAIN+'/'+name
        seen=[]
        def fetch(name,token,timeout):
            seen.append(name)
            return (ET.tostring(tree),'text/xml') if name=='sitemap.xml' else (expected[name],'text/html')
        with patch.object(smoke,'fetch',side_effect=fetch):
            self.assertEqual(smoke.energy_attempt(1),[])
        self.assertEqual(set(seen),set(expected)|{'sitemap.xml'})
        with patch.object(smoke,'fetch',return_value=(b'wrong release','text/html')):
            self.assertTrue(smoke.energy_attempt(1))


if __name__=='__main__':unittest.main()
