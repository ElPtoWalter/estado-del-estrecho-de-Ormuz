"""An explicit owner decision releases only the sealed historical bundle."""
import copy
import hashlib
import json
import re
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import history_release as release
import history_public_candidate as candidate
import build_public_site as public
from publication_quality import (apply_policy, owner_history_review_valid,
    HISTORY_ARTICLES, HISTORY_REFERENCES, HISTORY_NO_ADS, HISTORY_APPROVED_COMMIT)


class HistoryReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files,cls.reviews=release.verify()

    def test_actual_owner_evidence_is_separate_from_immutable_preapproval_manifest(self):
        record=json.loads(release.RECORD.read_text(encoding='utf-8'))
        self.assertEqual(record['approved_candidate_commit'],HISTORY_APPROVED_COMMIT)
        self.assertEqual(record['sha256_lf'],candidate.manifest(self.files)['sha256_lf'])
        self.assertFalse(record['merge_authorized'])
        self.assertFalse(record['deployment_authorized'])
        self.assertFalse(record['advertising_authorized'])
        self.assertIsNone(candidate.manifest(self.files)['human_editorial_approval'])
        for name,r in self.reviews.items():
            self.assertNotIn('reviewer',r)
            self.assertNotIn('facts_checked',r)
            self.assertNotIn('rights_checked',r)
            self.assertNotIn('reviewed_at',r)
            self.assertTrue(owner_history_review_valid(self.files[name].decode(),r))

    def test_only_exact_bytes_with_owner_decision_pass(self):
        for name in HISTORY_NO_ADS:
            text=self.files[name].decode();review=self.reviews[name]
            self.assertFalse(owner_history_review_valid(text+'changed',review))
            for key,bad in [('approved',False),('approval_reference','technical review'),
                            ('approved_candidate_commit','0'*40),('public_author','Unnamed team'),
                            ('approval_date','2020-01-01'),('document','unrelated.html')]:
                changed=dict(review);changed[key]=bad
                self.assertFalse(owner_history_review_valid(text,changed),(name,key))
            result=apply_policy(text+'changed',name,review=review)
            self.assertIn('noindex',result)
            self.assertIn('data-draft-disclosure',result)

    def test_partial_decision_or_changed_candidate_cannot_enter_public_build(self):
        partial=copy.deepcopy(self.reviews);partial.pop(next(iter(HISTORY_ARTICLES)))
        with self.assertRaises(ValueError):release.verify(partial)
        with patch.object(candidate,'sha',return_value='changed'):
            with self.assertRaises(ValueError):release.verify(self.reviews)

    def test_public_articles_are_institutional_and_support_remains_noindex(self):
        rendered=release.render(self.files,self.reviews)
        for name in HISTORY_NO_ADS:
            text=rendered[name].decode()
            parser=candidate.sitemap.MetaParser();parser.feed(text)
            self.assertEqual(parser.canonical,public.DOMAIN+'/'+name)
            self.assertEqual('noindex' in parser.robots,name in HISTORY_REFERENCES)
            self.assertNotRegex(text,r'Publicación no autorizada|Publication not authorised|data-editorial-approval-pending|data-draft-disclosure|ElPtoWalter|Eduardo|mailto:')
            self.assertIn('Prepared with AI assistance' if name.startswith('en-') else 'asistencia de IA',text)
            self.assertIn('publisher-ads" content="disabled',text)
            if name in HISTORY_ARTICLES:
                self.assertIn('data-institutional-byline',text)
                self.assertIn('<meta name="author" content="Estrecho Ormuz">',text)
        for name in set(rendered)-HISTORY_NO_ADS:
            self.assertEqual(rendered[name],self.files[name])

    def test_owner_approval_cannot_enable_any_history_advertising(self):
        for name in HISTORY_NO_ADS:
            text=apply_policy(self.files[name].decode(),name,programmatic_ads=True,review=self.reviews[name])
            self.assertIn('publisher-ads" content="disabled',text)
            self.assertNotIn('adsbygoogle',text)

    def test_owner_record_cannot_be_reused_for_another_route(self):
        name=next(iter(HISTORY_ARTICLES))
        result=apply_policy(self.files[name].decode(),'unrelated.html',review=self.reviews[name])
        self.assertIn('noindex',result)
        self.assertNotIn('data-institutional-byline',result)

    def test_postdeploy_smoke_compares_all_seventeen_resources_and_sitemap(self):
        import remote_smoke_test as smoke
        expected=release.render(self.files,self.reviews)
        tree=candidate.sitemap.ET.Element('urlset',xmlns=candidate.sitemap.SITEMAP_NS)
        for name in HISTORY_ARTICLES:
            node=candidate.sitemap.ET.SubElement(tree,'url')
            candidate.sitemap.ET.SubElement(node,'loc').text=public.DOMAIN+'/'+name
        seen=[]
        def fetch(name,token,timeout):
            seen.append(name)
            return (ET.tostring(tree),'text/xml') if name=='sitemap.xml' else (expected[name],'text/html')
        with patch.object(smoke,'fetch',side_effect=fetch):
            self.assertEqual(smoke.history_attempt(1),[])
        self.assertEqual(set(seen),set(expected)|{'sitemap.xml'})
        with patch.object(smoke,'fetch',return_value=(b'wrong release','text/html')):
            self.assertTrue(smoke.history_attempt(1))

    def test_release_keeps_every_factual_word_table_and_cautious_conclusion(self):
        from test_history_public_candidate import Text
        rendered=release.render(self.files,self.reviews)
        for name in HISTORY_ARTICLES:
            def core(data):
                text=data.decode()
                text=re.sub(r'<p\b[^>]*\bdata-institutional-byline[^>]*>.*?</p>','',text,flags=re.S)
                text=re.sub(r'<p\b[^>]*\bdata-original-review[^>]*>.*?</p>','',text,flags=re.S)
                start=text.index('<div class="hero">')
                end=text.index('<p class="review-note" data-editorial-approval-pending') if 'data-editorial-approval-pending' in text else text.index('</main>')
                parser=Text();parser.feed(text[start:end]);return parser.normalized()
            self.assertEqual(core(self.files[name]),core(rendered[name]))

    def test_navigation_is_released_once_in_each_language(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in ('index.html','en.html','analisis.html','en-analysis.html','historial.html','en-history.html'):
                (root/name).write_text('<html><main></main></html>')
            candidate.integrate(root,self.reviews);candidate.integrate(root,self.reviews)
            for name in root.glob('*.html'):
                text=name.read_text();self.assertEqual(text.count('data-history-candidate'),1)
                self.assertNotIn('pendiente',text);self.assertNotIn('awaiting',text)
                self.assertIn(candidate.ARTICLES['en' if name.name.startswith('en') else 'es'],text)


if __name__=='__main__':unittest.main()
