"""Regressions found on the deployed bilingual archive and monitor links."""
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urlsplit

from build_public_site import repair_public_navigation, professional_language, render_history
from check_public_links import References, check


class PostDeployNavigationTests(unittest.TestCase):
    def test_brief_feed_excludes_snapshots_without_historical_html(self):
        import xml.etree.ElementTree as ET
        from generate_daily_brief import build_feed
        item = {'date': '2026-10-22', 'generated_at': '2026-10-22T18:00:00Z', 'summary_es': 'Parte de esa fecha.'}
        atom = {'a': 'http://www.w3.org/2005/Atom'}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(ET.fromstring(build_feed([item], item['generated_at'], root=root)).findall('a:entry', atom), [])
            (root / 'briefs').mkdir()
            (root / 'briefs/2026-10-22.html').write_text('<html><head><meta name="robots" content="noindex,follow"></head><body>Parte de esa fecha.</body></html>')
            feed = build_feed([item], item['generated_at'], root=root)
            entry = ET.fromstring(feed).find('a:entry', atom)
            self.assertEqual(entry.find('a:link', atom).get('href'), 'https://estrechoormuz.com/briefs/2026-10-22.html')
            self.assertEqual(entry.findtext('a:id', namespaces=atom), 'https://estrechoormuz.com/parte-diario.html#2026-10-22')
            (root / 'index.html').write_text('<html><body>Home</body></html>')
            (root / 'daily-brief-feed.xml').write_text(feed, encoding='utf-8')
            self.assertEqual(check(root), [])

    def test_monitor_feed_retains_both_supplied_and_legacy_history_anchors(self):
        from update_status import build_feed
        records = [{'id': 'event-original', 'at': '2026-10-23T18:38:46Z', 'status': 'INCIERTO',
                    'summary_es': 'Registro original.', 'summary_en': 'Original record.'},
                   {'at': '2026-10-22T18:00:00Z', 'status': 'ABIERTO', 'summary_es': 'Registro previo.'}]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'index.html').write_text('<html><body>Home</body></html>')
            (root / 'feed.xml').write_text(build_feed(records, 'https://estrechoormuz.com/'), encoding='utf-8')
            history = root / 'historial.html'
            history.write_text('<html><body>History without anchors</body></html>')
            self.assertEqual(len(check(root)), 2)
            history.write_text('<html><body>' + render_history(records, 'es', 50) + '</body></html>', encoding='utf-8')
            self.assertEqual(check(root), [])
            self.assertIn('Registro original.', history.read_text(encoding='utf-8'))
            parser = References(); parser.feed(render_history(records, 'en', 50))
            self.assertIn('event-original', parser.ids)

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

    def test_checker_rejects_unconfirmed_corrections_alias_without_flagging_other_mail(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            p = root / 'index.html'
            original = ('<html><body><a href="mailto:CORRECCIONES@estrechoormuz.com?subject=Correction">Old</a>'
                        '<a href="mailto:contacto@estrechoormuz.com?subject=Correction">Contact</a>'
                        '<a href="mailto:correcciones@example.org">External</a></body></html>')
            p.write_text(original, encoding='utf-8')
            self.assertEqual(len(check(root)), 1)
            self.assertIn('unverified corrections mailbox', check(root)[0])
            p.write_text(original.replace('CORRECCIONES@estrechoormuz.com','contacto@estrechoormuz.com'), encoding='utf-8')
            self.assertEqual(check(root), [])

    def test_contextual_guide_links_resolve_in_their_own_language(self):
        root = Path(__file__).resolve().parent
        pairs = {
            'en-can-hormuz-be-open-while-traffic-collapses.html': {'en-who-controls-strait-of-hormuz-transit-passage.html','en-how-hormuz-closure-affects-oil-gas-economy.html'},
            'puede-estar-abierto-ormuz-aunque-caiga-trafico.html': {'quien-controla-estrecho-ormuz-derecho-paso.html','como-afectaria-cierre-ormuz-petroleo-gas-economia.html'},
            'en-how-hormuz-closure-affects-oil-gas-economy.html': {'en-alternative-routes-strait-of-hormuz-closure-capacity.html','en-marine-insurance-war-risk-premiums-hormuz.html'},
            'como-afectaria-cierre-ormuz-petroleo-gas-economia.html': {'rutas-alternativas-cierre-estrecho-ormuz-capacidad.html','seguros-maritimos-primas-guerra-ormuz.html'},
        }
        for origin, expected in pairs.items():
            p = References();p.feed((root/origin).read_text(encoding='utf-8'))
            targets = {urlsplit(a['href']).path.lstrip('/') for a in p.anchors}
            self.assertTrue(expected <= targets, origin)
            for name in expected:
                other=References();other.feed((root/name).read_text(encoding='utf-8'))
                self.assertEqual(other.lang,p.lang)


if __name__ == '__main__':
    unittest.main()
