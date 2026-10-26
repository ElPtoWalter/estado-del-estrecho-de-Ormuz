"""PR #24: exact editorial approval, presentation-only edits and no advertising."""
import copy,json,re,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET
import spain_data as data
import spain_editorial as candidate
import spain_release as release
import build_public_site as public
import build_sitemap as sitemap
from publication_quality import (SPAIN_ARTICLES,SPAIN_METHODS,SPAIN_NO_ADS,SPAIN_APPROVED_COMMIT,
    HISTORY_NO_ADS,ENERGY_NO_ADS,owner_spain_review_valid,owner_history_review_valid,owner_energy_review_valid,apply_policy)


class SpainReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.files,cls.reviews=release.verify()

    def test_real_decision_is_separate_from_immutable_draft_and_registration_time(self):
        record=json.loads(release.RECORD.read_text(encoding='utf-8'))
        self.assertEqual(record['approved_candidate_commit'],SPAIN_APPROVED_COMMIT)
        self.assertEqual(record['sha256_lf'],candidate.manifest(self.files)['sha256_lf'])
        self.assertEqual(record['approval_date'],'2026-10-25')
        self.assertEqual(record['evidence_recorded_at'],'2026-10-26T08:38:42Z')
        self.assertEqual(record['authorised_factual_article_edits'],[])
        for key in ('merge_authorized','deployment_authorized','advertising_authorized','personal_data_publication_authorized'):self.assertFalse(record[key])
        original=json.loads(candidate.MANIFEST.read_text(encoding='utf-8'))
        self.assertIsNone(original['human_editorial_approval']);self.assertIsNone(original['reviewer'])
        for name in SPAIN_NO_ADS:
            for absent in ('reviewer','reviewed_at','facts_checked','rights_checked'):self.assertNotIn(absent,self.reviews[name])
            self.assertTrue(owner_spain_review_valid(self.files[name].decode(),self.reviews[name]))

    def test_wrong_commit_hash_date_or_technical_review_cannot_release(self):
        for name in SPAIN_NO_ADS:
            text=self.files[name].decode();review=self.reviews[name]
            self.assertFalse(owner_spain_review_valid(text+'changed',review))
            for key,bad in [('approved',False),('approval_reference','https://github.com/ElPtoWalter/estado-del-estrecho-de-Ormuz/pull/24#pullrequestreview-5644345114'),('approved_candidate_commit','0'*40),('document','other.html'),('public_author','Unnamed reviewer'),('approval_date','2026-10-26'),('evidence_recorded_at','2099-01-01')]:
                altered=dict(review);altered[key]=bad
                self.assertFalse(owner_spain_review_valid(text,altered),(name,key))
            self.assertIn('noindex',apply_policy(text+'changed',name,review=review))

    def test_route_missing_record_and_altered_manifest_fail_closed(self):
        name=next(iter(SPAIN_ARTICLES));text=self.files[name].decode()
        for route in ('other.html','diario/'+name):
            result=apply_policy(text,route,review=self.reviews[name])
            self.assertIn('noindex',result);self.assertNotIn('data-original-review',result)
        partial=copy.deepcopy(self.reviews);partial.pop(name)
        with self.assertRaises(ValueError):release.verify(partial)
        with patch.object(data,'sha',return_value='changed'):
            with self.assertRaises(ValueError):release.verify(self.reviews)
        record=json.loads(release.RECORD.read_text(encoding='utf-8'));record['evidence_recorded_at']='2026-10-25T08:38:42Z'
        fake=unittest.mock.Mock();fake.read_text.return_value=json.dumps(record)
        with patch.object(release,'RECORD',fake):
            with self.assertRaises(ValueError):release.verify(self.reviews)

    def test_old_and_new_editorial_decisions_are_not_interchangeable(self):
        import history_release,energy_release
        older,_=history_release.verify();energy,_=energy_release.verify()
        history_name=next(iter(HISTORY_NO_ADS));energy_name=next(iter(ENERGY_NO_ADS));name=next(iter(SPAIN_ARTICLES))
        for old in (history_name,energy_name):self.assertFalse(owner_spain_review_valid(self.files[name].decode(),self.reviews[old]))
        self.assertFalse(owner_spain_review_valid(older[history_name].decode(),self.reviews[name]))
        self.assertFalse(owner_spain_review_valid(energy[energy_name].decode(),self.reviews[name]))
        self.assertFalse(owner_history_review_valid(self.files[name].decode(),self.reviews[name]))
        self.assertFalse(owner_energy_review_valid(self.files[name].decode(),self.reviews[name]))

    def test_approved_article_body_and_every_download_remain_identical(self):
        rendered=release.render(self.files,self.reviews)
        for name in SPAIN_ARTICLES:
            def core(raw):return raw.decode().split('<article>',1)[1].split('</article>',1)[0]
            self.assertEqual(core(self.files[name]),core(rendered[name]))
        for name,raw in self.files.items():
            if not name.endswith('.html'):self.assertEqual(rendered[name],raw,name)
        self.assertEqual(sum(n.endswith('.svg') for n in rendered),8)
        self.assertEqual(sum(n.endswith('.csv') for n in rendered),2)

    def test_method_keeps_unresolved_discrepancy_arithmetic_and_legal_limits(self):
        rendered=release.render(self.files,self.reviews)
        for name in SPAIN_METHODS:
            before=self.files[name].decode();after=rendered[name].decode()
            # Every method section before the rights presentation remains exact.
            heading='Alcance y versiones' if not name.startswith('en-') else 'Scope and releases'
            end='Derechos y atribución' if not name.startswith('en-') else 'Rights and attribution'
            self.assertEqual(before.split('<h2>'+heading,1)[1].split('<h2>'+end,1)[0],after.split('<h2>'+heading,1)[1].split('<h2>'+end,1)[0])
            self.assertIn('Discrepancia documental no resuelta' if not name.startswith('en-') else 'Unresolved documentary discrepancy',after)
            self.assertIn('no acredita una autorización específica de Enagás ni una revisión jurídica independiente' if not name.startswith('en-') else 'neither specific permission from Enagás nor independent legal clearance',after)
            self.assertNotIn('revisión pendiente',after);self.assertNotIn('review pending',after)

    def test_two_indexable_articles_two_noindex_methods_and_permanent_no_ads(self):
        for name,raw in release.render(self.files,self.reviews).items():
            if not name.endswith('.html'):continue
            text=raw.decode();meta=sitemap.MetaParser();meta.feed(text)
            self.assertEqual('noindex' in meta.robots,name in SPAIN_METHODS)
            self.assertEqual(meta.canonical,public.DOMAIN+'/'+name)
            self.assertIn('publisher-ads" content="disabled',text)
            self.assertIn('26/10/2026' if not name.startswith('en-') else '26 October 2026',text)
            self.assertNotRegex(text,r'Borrador|Draft for editorial|data-draft-disclosure|Publication not authorised|Publicación no autorizada|ElPtoWalter|Eduardo|mailto:')
            self.assertEqual(len(re.findall(r'<a\b[^>]*href="[^"]+\.csv"',text)),2)
            if name in SPAIN_ARTICLES:
                self.assertIn('data-institutional-byline',text);self.assertIn('<meta name="author" content="Estrecho Ormuz">',text)
            forced=apply_policy(self.files[name].decode(),name,programmatic_ads=True,review=self.reviews[name])
            self.assertIn('publisher-ads" content="disabled',forced);self.assertNotIn('adsbygoogle',forced)

    def test_missing_kind_cannot_bypass_hold_or_monetisation_boundary(self):
        for name in SPAIN_NO_ADS:
            text=self.files[name].decode().replace('<meta name="content-kind" content="original-draft">','')
            result=apply_policy(text,name,programmatic_ads=True)
            self.assertIn('noindex',result);self.assertIn('publisher-ads" content="disabled',result)

    def test_bilingual_navigation_is_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in ('index.html','en.html','analisis.html','en-analysis.html','historial.html','en-history.html'):(root/name).write_text('<main></main>',encoding='utf-8')
            release.integrate(root);release.integrate(root)
            for path in root.glob('*.html'):
                text=path.read_text(encoding='utf-8');self.assertEqual(text.count('data-spain-analysis'),1)
                self.assertIn(candidate.ARTICLES['en' if path.name.startswith('en') else 'es'],text)

    def test_future_postdeploy_checks_fifteen_resources_and_sitemap(self):
        import remote_smoke_test as smoke
        expected=release.render(self.files,self.reviews);tree=ET.Element('urlset',xmlns=sitemap.SITEMAP_NS)
        for name in SPAIN_ARTICLES:
            node=ET.SubElement(tree,'url');ET.SubElement(node,'loc').text=public.DOMAIN+'/'+name
        seen=[]
        def fetch(name,token,timeout):
            seen.append(name);return (ET.tostring(tree),'text/xml') if name=='sitemap.xml' else (expected[name],'text/html')
        with patch.object(smoke,'fetch',side_effect=fetch):self.assertEqual(smoke.spain_attempt(1),[])
        self.assertEqual(set(seen),set(expected)|{'sitemap.xml'})
        with patch.object(smoke,'fetch',return_value=(b'wrong release','text/html')):self.assertTrue(smoke.spain_attempt(1))

if __name__=='__main__':unittest.main()
