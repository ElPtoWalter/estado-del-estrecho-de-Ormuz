"""Public adaptation, privacy boundaries and truthful release state of PR #22."""
import csv
import hashlib
from contextlib import redirect_stderr
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit, urljoin
import xml.etree.ElementTree as ET

import build_public_site as public
import build_sitemap as sitemap
from check_public_links import References
import history_public_candidate as candidate
from publication_quality import apply_policy, original_review_valid, HISTORY_ARTICLES, HISTORY_REFERENCES


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)
    def normalized(self):
        return re.sub(r'\s+', ' ', ''.join(self.parts)).strip()


class PublicHistoryCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = candidate.verify()

    def test_article_facts_tables_and_cautious_conclusions_are_unchanged(self):
        for lang, filename in candidate.ARTICLES.items():
            original = (candidate.DRAFT/filename).read_text(encoding='utf-8')
            prepared = self.files[filename].decode('utf-8')
            marker = '<div class="prose"><h2>' + ('Fuentes congeladas y reproducción' if lang == 'es' else 'Frozen sources and reproduction')
            # Compare every reader-visible word from the title through all evidence/limits.
            def core(text):
                parser = Text()
                parser.feed(text[text.index('<div class="hero">'):text.index(marker)])
                return parser.normalized()
            self.assertEqual(core(original), core(prepared))

    def test_five_data_downloads_and_six_graphs_preserve_the_frozen_evidence(self):
        for source, dest in candidate.CSV_MAP.items():
            data = self.files[f'{candidate.ASSETS}/{dest}']
            self.assertEqual(candidate.sha(data), candidate.sha((candidate.DRAFT/source).read_bytes()))
        rows = list(csv.DictReader(io.StringIO(self.files[f'{candidate.ASSETS}/records.csv'].decode())))
        self.assertEqual(tuple(rows[0]), candidate.research.FIELDS)
        self.assertEqual(len(rows), 103)
        self.assertEqual(sum(r['model'] == 'v7' and r['confidence'] == 'MEDIA' for r in rows), 47)
        self.assertEqual(sum(r['model'] == 'v7' and r['confidence'] == 'ALTA' for r in rows), 2)
        graphs = [name for name in self.files if name.endswith('.svg')]
        self.assertEqual(len(graphs), 6)
        for name in graphs:
            self.assertEqual(candidate.sha(self.files[name]), candidate.sha((candidate.DRAFT/Path(name).name).read_bytes()))

    def test_csv_exception_is_exact_and_audit_still_blocks_unknown_exports(self):
        for name in public.HISTORY_PUBLIC_CSV:
            self.assertTrue(public.copy_asset(Path(name)))
            self.assertTrue(public.copy_asset(public.ROOT/name))
        for name in ('records.csv', 'assets/research/records.csv', 'private/records.csv',
                     candidate.ASSETS+'/secrets.csv', 'assets/other/records.csv',
                     candidate.ASSETS+'/sources.json', candidate.ASSETS+'/reproduce.py'):
            self.assertFalse(public.copy_asset(Path(name)), name)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'unexpected.csv').write_text('password,value\nsecret,private\n')
            captured = io.StringIO()
            with redirect_stderr(captured), self.assertRaises(SystemExit):
                public.audit_public_build(root)
            self.assertIn('unapproved public CSV: unexpected.csv', captured.getvalue())

    def test_payload_rejects_technical_resources_active_svg_and_csv_formulas(self):
        for name, payload in [
            ('x.json', b'{}'),
            (candidate.ASSETS+'/records.csv', b'value\n=HYPERLINK("bad")\n'),
            (candidate.ASSETS+'/x.svg', b'<svg><script>bad()</script></svg>'),
            (candidate.ASSETS+'/x.svg', b'<svg><use href="https://example.org/data"/></svg>'),
            ('x.html', b'<a href="source.json">Internal</a>')]:
            with self.assertRaises(ValueError, msg=name):
                candidate.audit_payload({name: payload})

    def test_metadata_routes_remain_reciprocal_noindex_and_ads_disabled_after_render(self):
        for pair in (candidate.ARTICLES, candidate.METHODS):
            for lang, name in pair.items():
                source = self.files[name].decode()
                rendered = public.sanitize_html(apply_policy(source, name, programmatic_ads=False), name)
                parser = sitemap.MetaParser(); parser.feed(rendered)
                self.assertEqual(parser.canonical, public.DOMAIN+'/'+name)
                self.assertEqual(parser.alternates, {k: public.DOMAIN+'/'+v for k,v in {**pair, 'x-default':pair['es']}.items()})
                self.assertIn('noindex', parser.robots)
                self.assertNotIn('data-original-review', rendered)
                self.assertNotIn('adsbygoogle', rendered)
                self.assertIn('data-draft-disclosure', rendered)

    def test_all_references_use_safe_public_destinations_and_transparent_provenance(self):
        for name, data in self.files.items():
            if not name.endswith('.html'):
                continue
            text = data.decode()
            parser = References(); parser.feed(text)
            self.assertNotRegex(text, r'\.json\b|\.py\b|github\.com|mailto:')
            if name == candidate.ARCHIVE:
                self.assertIn('Method in English ↗', text)
                self.assertNotIn('Read in English ↗', text)
            for ref in parser.refs:
                url = urlsplit(ref)
                if url.netloc and url.netloc != 'estrechoormuz.com':
                    self.fail(f'Unexpected external destination: {ref}')
                path = url.path.lstrip('/')
                if path in self.files:
                    if path.endswith('.html') and url.fragment:
                        target = References(); target.feed(self.files[path].decode())
                        self.assertIn(url.fragment, target.ids)
                elif path:
                    self.assertTrue((public.ROOT/path).is_file(), ref)
            if name in candidate.METHODS.values():
                for source in json.loads((candidate.DRAFT/'sources.json').read_text())['sources']:
                    self.assertIn(source['commit'], text)
                    self.assertIn(source['sha256_lf'], text)
            for href, identity in re.findall(r'<a href="([^"]+)" data-source-url="([^"]+)"', text):
                self.assertEqual(urljoin(public.DOMAIN+'/', href), identity)

    def test_no_review_or_publication_authorization_is_invented(self):
        manifest = json.loads(candidate.MANIFEST.read_text())
        self.assertFalse(manifest['publication_authorized'])
        self.assertFalse(manifest['index'])
        self.assertFalse(manifest['advertising'])
        self.assertIsNone(manifest['human_editorial_approval'])
        self.assertIsNone(manifest['reviewer'])
        self.assertIsNone(manifest['approved_at'])
        self.assertNotIn('owner_feedback', manifest)
        proposal = manifest['publication_proposal']
        self.assertEqual(proposal['indexable_after_real_editorial_approval'], sorted(HISTORY_ARTICLES))
        self.assertEqual(proposal['accessible_noindex_follow_even_after_approval'], sorted(HISTORY_REFERENCES))
        self.assertFalse(proposal['advertising_on_all_five_pages'])
        self.assertEqual(json.loads((public.ROOT/'editorial-reviews.json').read_text()), {})
        for name in self.files:
            if name.endswith('.html'):
                self.assertFalse(public.public_html_path((candidate.SOURCE/name).relative_to(public.ROOT)))
        deploy = (public.ROOT/'.github/workflows/deploy-public.yml').read_text()
        self.assertIn('path: _site', deploy)
        self.assertNotIn('history_public_candidate', deploy)

    def test_tampered_candidate_cannot_be_built_without_explicit_regeneration(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, data in self.files.items():
                path = root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
            (root/candidate.ARTICLES['es']).write_text('changed')
            with patch.object(candidate, 'SOURCE', root):
                with self.assertRaisesRegex(ValueError, 'differs'):
                    candidate.verify()
        with self.assertRaisesRegex(ValueError, 'restricted'):
            candidate.build_preview(out=public.OUT)

    def test_navigation_integration_is_bilingual_and_confined_to_candidate_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ('index.html','en.html','analisis.html','en-analysis.html','historial.html','en-history.html'):
                (root/name).write_text('<main><p>Existing content</p></main>')
            technical = {name:{'technical_assessment':'favourable', 'state':'COMMENTED'} for name in candidate.ARTICLES.values()}
            candidate.integrate(root, reviews=technical)
            for name in ('index.html','analisis.html','historial.html'):
                text = (root/name).read_text(encoding='utf-8')
                self.assertIn('Existing content', text)
                self.assertIn(candidate.ARTICLES['es'], text)
                self.assertIn('pendiente de autorización', text)
            for name in ('en.html','en-analysis.html','en-history.html'):
                self.assertIn(candidate.ARTICLES['en'], (root/name).read_text(encoding='utf-8'))

    def test_sitemap_excludes_pending_pages_and_future_metadata_is_valid(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pages = []
            for name, data in self.files.items():
                if name.endswith('.html'):
                    path = root/name; path.write_bytes(data)
                    pages.append(sitemap.parse_page(root, path))
            self.assertEqual(sitemap.discover_pages(root), [])
            # Model future eligibility in memory; no reviewed page or approval is written.
            for page in pages:
                if page.relative.as_posix() in HISTORY_ARTICLES:
                    page.robots = ''
            tree = sitemap.build_tree(root, [p for p in pages if 'noindex' not in p.robots])
            self.assertEqual(len(tree.getroot()), 2)
            self.assertEqual(sitemap.validate_tree(tree, root), [])
            self.assertEqual({node.find(sitemap.qname(sitemap.SITEMAP_NS, 'loc')).text for node in tree.getroot()},
                             {public.DOMAIN+'/'+name for name in HISTORY_ARTICLES})
            for pair in (candidate.ARTICLES, candidate.METHODS):
                expected = {lang: public.DOMAIN+'/'+slug for lang, slug in {**pair, 'x-default':pair['es']}.items()}
                for node in tree.getroot():
                    if node.find(sitemap.qname(sitemap.SITEMAP_NS, 'loc')).text in expected.values():
                        self.assertEqual({n.get('hreflang'):n.get('href') for n in
                                          node.findall(sitemap.qname(sitemap.XHTML_NS, 'link'))}, expected)

    def test_both_languages_attribute_only_the_documented_preparatory_review(self):
        for lang, name in candidate.ARTICLES.items():
            text = self.files[name].decode()
            self.assertNotIn('revisado favorablemente por el propietario', text)
            self.assertNotIn('The owner reviewed', text)
            self.assertIn('revisión técnica preparatoria' if lang == 'es' else 'preliminary technical review', text)
            self.assertIn('pendiente de aprobación editorial por el titular' if lang == 'es' else 'awaits editorial approval by the publisher', text)

    def test_assisted_technical_assessment_cannot_lift_the_hold_or_ad_boundary(self):
        assessment = {'state':'COMMENTED', 'technical_assessment':'favourable',
                      'review_reference':'https://example.invalid/test-fixture'}
        for name in HISTORY_ARTICLES | HISTORY_REFERENCES:
            text = self.files[name].decode()
            result = apply_policy(text, name, programmatic_ads=True, review=assessment)
            self.assertIn('noindex', result)
            self.assertIn('data-draft-disclosure', result)
            self.assertIn('data-history-publication-status', result)
            self.assertNotIn('data-original-review', result)
            self.assertIn('publisher-ads" content="disabled', result)

    def test_exact_review_gate_has_two_indexable_articles_and_three_noindex_resources(self):
        # Synthetic unit-test objects only. No record/file or approved HTML is persisted.
        registry_before = (public.ROOT/'editorial-reviews.json').read_bytes()
        for name in HISTORY_ARTICLES | HISTORY_REFERENCES:
            text = self.files[name].decode()
            sources = re.findall(r'data-source-url="([^"]+)"', text)
            review = {'kind':'original_analysis', 'facts_checked':True, 'rights_checked':True, 'approved':True,
                      'reviewer':'SYNTHETIC UNIT TEST — not a real approval', 'reviewed_at':'2020-01-01T00:00:00Z',
                      'original_contribution':'Synthetic gate test only; these fields are never saved to a review registry or included in an exported publication artifact.',
                      'sources':list(dict.fromkeys(sources))[:2], 'sha256':hashlib.sha256(text.encode()).hexdigest()}
            self.assertTrue(original_review_valid(text, review), name)
            result = apply_policy(text, name, programmatic_ads=True, review=review)
            metadata = sitemap.MetaParser(); metadata.feed(result)
            self.assertEqual('noindex' in metadata.robots, name in HISTORY_REFERENCES)
            self.assertNotIn('data-draft-disclosure', result)
            self.assertNotIn('data-history-publication-status', result)
            self.assertNotIn('data-editorial-approval-pending', result)
            self.assertNotIn('Publicación no autorizada', result)
            self.assertNotIn('Publication not authorised', result)
            self.assertNotIn('adsbygoogle', result)
            self.assertIn('publisher-ads" content="disabled', result)
            # A changed document cannot inherit that exact approval.
            rejected = apply_policy(text+'\nchanged', name, review=review)
            self.assertIn('noindex', rejected)
            self.assertIn('data-draft-disclosure', rejected)
        self.assertEqual((public.ROOT/'editorial-reviews.json').read_bytes(), registry_before)

    def test_a_missing_kind_meta_cannot_bypass_hold_or_enable_ads(self):
        page = '<html lang="en"><head><meta name="robots" content="index,follow"><meta name="publisher-ads" content="enabled"></head><body><main>Test fixture</main></body></html>'
        for name in HISTORY_ARTICLES | HISTORY_REFERENCES:
            result = apply_policy(page, name, programmatic_ads=True)
            self.assertIn('noindex', result)
            self.assertNotIn('publisher-ads" content="enabled', result)
            self.assertIn('publisher-ads" content="disabled', result)


if __name__ == '__main__':
    unittest.main()
