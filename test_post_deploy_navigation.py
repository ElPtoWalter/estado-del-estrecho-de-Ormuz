"""Regressions found on the deployed bilingual archive and monitor links."""
from pathlib import Path
import tempfile
import unittest

from build_public_site import repair_public_navigation, professional_language
from check_public_links import References, check


class PostDeployNavigationTests(unittest.TestCase):
    def test_archived_translation_keeps_the_date_and_body(self):
        page = ('<html lang="es"><head><link rel="alternate" hreflang="en" '
                'href="https://estrechoormuz.com/diary/2026-10-22.html"></head>'
                '<body><a data-href="unchanged" class="language-link" href="/en-diary.html"><span>EN</span></a>'
                '<a href="https://example.org/english">English</a>'
                '<h1>Edición del 22 de octubre</h1><p>Diagnóstico original fechado.</p></body></html>')
        result = repair_public_navigation(page, 'diario/2026-10-22.html')
        parser = References(); parser.feed(result)
        self.assertEqual(parser.anchors[0]['href'], '/diary/2026-10-22.html')
        self.assertEqual(parser.anchors[1]['href'], 'https://example.org/english')
        self.assertIn('data-href="unchanged"', result)
        self.assertIn('<h1>Edición del 22 de octubre</h1><p>Diagnóstico original fechado.</p>', result)

    def test_english_archive_returns_to_the_matching_spanish_day(self):
        page = ("<html lang='en'><head><link rel='alternate' hreflang='es' "
                "href='https://estrechoormuz.com/diario/2026-10-22.html'></head>"
                "<body><a href='/diario.html' class='language-link' lang='es'>ES</a></body></html>")
        parser = References(); parser.feed(repair_public_navigation(page, 'diary/2026-10-22.html'))
        self.assertEqual(parser.anchors[0]['href'], '/diario/2026-10-22.html')

    def test_english_monitor_fragment_is_repaired_without_touching_other_sites(self):
        page = ('<html lang="en"><body><a href="/en.html#estado-actual">Monitor</a>'
                '<a href="https://example.org/en.html#estado-actual">External</a>'
                '<a href="/index.html#estado-actual">Spanish monitor</a>'
                '<a href="https://www.ukmto.org/indian-ocean/products">JMIC products</a>'
                '<a href="https://www.ukmto.org/-/media/ukmto/products/update-040-to-jmic-advisory-note-03-may.pdf">May bulletin</a></body></html>')
        parser = References(); parser.feed(repair_public_navigation(page, 'en-analysis.html'))
        self.assertEqual([a['href'] for a in parser.anchors], ['/en.html#current-status',
            'https://example.org/en.html#estado-actual', '/index.html#estado-actual',
            'https://www.ukmto.org/partner-products/jmic-products',
            'https://www.ukmto.org/-/media/ukmto/products/update-040-jmic-advisory-note-03-may.pdf'])

    def test_checker_rejects_wrong_language_destination_even_when_it_exists(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'index.html').write_text('<html lang="es"><body id="estado-actual">Home</body></html>')
            (root / 'en.html').write_text('<html lang="en"><body id="current-status">Home</body></html>')
            page = root / 'article.html'
            page.write_text('<html lang="es"><head><link rel="alternate" hreflang="en" href="https://estrechoormuz.com/en-article.html"></head>'
                '<body><a class="language-link" href="/en.html">EN</a><a href="/en.html#estado-actual">Monitor</a></body></html>')
            (root / 'en-article.html').write_text('<html lang="en"><body>Article</body></html>')
            errors = check(root)
            self.assertEqual(len(errors), 2)
            self.assertTrue(any('language switch' in error for error in errors))
            self.assertTrue(any('fragment' in error for error in errors))
            page.write_text(repair_public_navigation(page.read_text(), 'article.html'))
            self.assertEqual(check(root), [])

    def test_root_alias_and_named_fragment_are_valid(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'index.html').write_text('<html lang="es"><body><a name="legacy">Home</a><a href="#legacy">Here</a></body></html>')
            (root / 'en.html').write_text('<html lang="en"><head><link rel="alternate" hreflang="es" href="https://estrechoormuz.com/"></head>'
                '<body><a class="language-link" href="/index.html">ES</a></body></html>')
            self.assertEqual(check(root), [])

    def test_public_copy_does_not_offer_an_unpublished_api(self):
        result = professional_language('History, API, RSS and methodology are accessible.', 'en')
        self.assertEqual(result, 'History, sources, RSS and methodology are accessible.')


if __name__ == '__main__':
    unittest.main()
