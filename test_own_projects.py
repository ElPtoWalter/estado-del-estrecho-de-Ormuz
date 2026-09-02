import unittest
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import own_projects as promo


class PromotionTests(unittest.TestCase):
    def page(self, words=400, lang="es", meta=""):
        return f'<html lang="{lang}"><head>{meta}</head><body><main><article><h1>Guía</h1><p>{"dato " * words}</p></article></main><footer>Pie</footer></body></html>'

    def test_two_correct_destinations_for_each_site(self):
        for site, other in (("ormuz", "estrechogibraltar.com"), ("gibraltar", "estrechoormuz.com")):
            result = promo.add_promotions(self.page(), "index.html", site)
            block = result.split("data-own-projects", 1)[1]
            self.assertEqual(block.count('class="own-projects__card '), 2)
            self.assertIn('href="https://despedidaverse.com/"', block)
            self.assertIn(f'href="https://{other}/"', block)
            self.assertNotIn(f'https://estrecho{site}.com/', block)
            self.assertIn("Publicidad propia · Otros proyectos", block)

    def test_english_pages_link_to_english_strait(self):
        result = promo.add_promotions(self.page(lang="en-GB"), "en.html", "gibraltar")
        self.assertIn("House promotion · Other projects", result)
        self.assertIn('href="https://estrechoormuz.com/en.html"', result)
        self.assertIn("Spanish-language site", result)
        self.assertIn('href="https://despedidaverse.com/"', result)

    def test_inserted_after_first_information_before_main_end(self):
        result = promo.add_promotions(self.page(), "index.html", "ormuz")
        self.assertLess(result.index("</p>"), result.index("data-own-projects"))
        self.assertLess(result.index("data-own-projects"), result.index("</article>"))
        self.assertLess(result.index("data-own-projects"), result.index("</main>"))
        self.assertLess(result.index("</main>"), result.index("<footer>"))

    def test_idempotent(self):
        once = promo.add_promotions(self.page(), "index.html", "ormuz")
        twice = promo.add_promotions(once, "index.html", "ormuz")
        self.assertEqual(once, twice)
        self.assertEqual(twice.count('id="otros-proyectos"'), 1)
        self.assertEqual(twice.count("/own-projects.css"), 1)

    def test_small_articles_are_not_promotional_inventory(self):
        name = "que-significa-cierre-estrecho-ormuz.html"
        self.assertFalse(promo.eligible(self.page(349), name, "ormuz"))
        self.assertTrue(promo.eligible(self.page(350), name, "ormuz"))

    def test_navigation_and_scripts_do_not_inflate_word_count(self):
        page = self.page(50).replace("</main>", "<nav><p>" + "menú " * 500 + "</p></nav><script>" + "texto " * 500 + "</script></main>")
        self.assertFalse(promo.eligible(page, "importancia.html", "ormuz"))

    def test_excludes_diaries_archives_legal_and_panels(self):
        for name in ("diario.html", "en-diary.html", "diario/actual.html", "diario/2026-09-02.html", "diario-2026-08-15.html",
                     "briefs/example.html", "newsletter/latest.html", "privacidad.html", "contacto.html", "datos.html", "trafico.html", "analisis.html"):
            for site in ("ormuz", "gibraltar"):
                self.assertEqual(promo.add_promotions(self.page(1000), name, site), self.page(1000))

    def test_respects_noindex_ad_exclusions_and_redirects(self):
        for meta in ('<meta name="robots" content="noindex,follow">',
                     '<meta content="noindex" name="googlebot">',
                     '<meta name="publisher-ads" content="disabled">',
                     '<meta http-equiv="refresh" content="0;url=/">'):
            self.assertFalse(promo.eligible(self.page(meta=meta), "index.html", "ormuz"))

    def test_no_tracking_scripts_or_external_assets(self):
        block = promo.render_promotions("gibraltar", "es")
        for unwanted in ("<script", "<iframe", "utm_", "onclick", "adsbygoogle", "target="):
            self.assertNotIn(unwanted, block)
        self.assertEqual(block.count('rel="sponsored"'), 2)

    def test_missing_main_or_head_does_not_modify_document(self):
        for page in ("<html><head></head><body>Texto</body></html>", "<main><p>Texto</p></main>"):
            self.assertEqual(promo.add_promotions(page, "index.html", "ormuz"), page)

    def test_css_has_mobile_and_keyboard_rules_without_animation(self):
        css = (Path(__file__).parent / "own-projects.css").read_text()
        self.assertIn("@media (max-width: 48rem)", css)
        self.assertIn("grid-template-columns: minmax(0, 1fr)", css)
        self.assertIn(":focus-visible", css)
        for forbidden in ("animation:", "@import", "url("):
            self.assertNotIn(forbidden, css)

    def test_each_card_identified_as_house_promotion(self):
        for lang in ("es", "en"):
            result = promo.render_promotions("ormuz", lang)
            self.assertEqual(result.count('class="own-projects__disclosure"'), 2)
            self.assertIn("Ejemplo real" if lang == "es" else "Real example", result)

    def test_portal_images_are_local_real_assets_with_reserved_dimensions(self):
        class Images(HTMLParser):
            def __init__(self):
                super().__init__()
                self.images = []
            def handle_starttag(self, tag, attrs):
                if tag == "img":
                    self.images.append(dict(attrs))
        parser = Images()
        parser.feed(promo.render_promotions("ormuz", "es"))
        self.assertEqual(len(parser.images), 2)
        for attrs in parser.images:
            self.assertTrue(attrs["src"].startswith("/own-projects-dv-"))
            self.assertGreater(int(attrs["width"]), 0)
            self.assertGreater(int(attrs["height"]), 0)
            self.assertIn("alt", attrs)
            asset = Path(__file__).parent / attrs["src"].lstrip("/")
            self.assertTrue(asset.is_file())
            self.assertLess(asset.stat().st_size, 200_000)
            self.assertEqual(asset.read_bytes()[:4], b"RIFF")

    def test_fixed_rules_are_only_in_wide_tall_mouse_media_query(self):
        css = (Path(__file__).parent / "own-projects.css").read_text()
        guard = "@media screen and (min-width: 110rem) and (min-height: 50rem) and (hover: hover) and (pointer: fine)"
        before, after = css.split(guard)
        self.assertNotIn("position: fixed", before)
        self.assertIn("position: fixed", after)
        self.assertIn("@media print", after)
        self.assertIn("overflow-y: auto", after)
        self.assertIn("min(38rem, calc(100svh - 11rem))", after)
        self.assertIn(".own-projects__cta { flex: 0 0 auto", after)

    def test_side_geometry_preserves_editorial_width(self):
        # Mirrors CSS: 80rem centre, max 18rem rail, 1rem edge and content gap.
        for rem in (16, 20, 32):
            for width in (110 * rem, 120 * rem, 160 * rem, 240 * rem):
                card = min(18 * rem, (width - 80 * rem) / 2 - 2 * rem)
                left = max(rem, width / 2 - 59 * rem)
                content_left = (width - 80 * rem) / 2
                self.assertGreaterEqual(card, 13 * rem)
                self.assertGreaterEqual(left, rem)
                self.assertGreaterEqual(content_left - (left + card), rem)

    def test_portals_have_balanced_markup_and_only_two_click_targets(self):
        class Structure(HTMLParser):
            def __init__(self):
                super().__init__()
                self.stack = []
                self.errors = []
                self.links = 0
            def handle_starttag(self, tag, attrs):
                if tag == "a":
                    self.links += 1
                    if "a" in self.stack:
                        self.errors.append("nested link")
                if tag != "img":
                    self.stack.append(tag)
            def handle_endtag(self, tag):
                if not self.stack or self.stack.pop() != tag:
                    self.errors.append(tag)
        for site in ("ormuz", "gibraltar"):
            parser = Structure()
            parser.feed(promo.render_promotions(site, "es"))
            self.assertEqual(parser.links, 2)
            self.assertEqual(parser.stack, [])
            self.assertEqual(parser.errors, [])

    def test_css_version_invalidates_previous_cached_cards(self):
        result = promo.add_promotions(self.page(), "index.html", "ormuz")
        self.assertIn("own-projects.css?v=20260902-3", result)
        self.assertIn('defer src="/own-projects.js?v=20260902-3"', result)

    def test_home_comes_after_status_not_before_initial_information(self):
        for site, path, attrs in (("ormuz", "index.html", 'id="estado-actual"'),
                                  ("ormuz", "en.html", 'id="current-status"'),
                                  ("gibraltar", "index.html", 'class="gwc-status"'),
                                  ("gibraltar", "en.html", 'class="gwc-status"')):
            content = ('<section><h1>Portada</h1><p>' + 'intro ' * 30 + '</p></section>'
                       f'<section {attrs}><header><h2>Estado</h2></header><p>' + 'situación ' * 30 +
                       '</p><section><p>Detalle anidado</p></section></section>'
                       '<section id="siguiente"><p>Más información</p></section>')
            page = f'<html><head></head><body><main>{content}</main></body></html>'
            result = promo.add_promotions(page, path, site)
            self.assertIn('</section></section><span id="projects-mobile-position"', result)
            self.assertLess(result.index("data-own-projects"), result.index('id="siguiente"'))
            self.assertEqual(result.count('id="otros-proyectos"'), 1)

    def test_article_keeps_complete_intro_before_promotions(self):
        content = ('<article><header><h1>Guía del estrecho</h1><p>' + 'intro ' * 30 +
                   '</p></header><section id="analisis"><p>' + 'dato ' * 400 + '</p></section></article>')
        page = f'<html><head></head><body><main>{content}</main></body></html>'
        result = promo.add_promotions(page, "importancia.html", "ormuz")
        self.assertIn('</header><span id="projects-mobile-position"', result)
        self.assertLess(result.index("data-own-projects"), result.index('id="analisis"'))
        self.assertLess(result.index('</article>'), result.index('id="projects-desktop-position"'))

    def test_empty_or_non_editorial_sections_are_not_insertion_targets(self):
        content = ('<nav><section><p>' + 'menú ' * 50 + '</p></section></nav><section></section>'
                   '<header><h1>Título</h1></header><script>const x = "</section>";</script>'
                   '<section id="primero"><p>' + 'texto ' * 40 + '</p></section><section id="resto"></section>')
        page = f'<html><head></head><body><main>{content}</main></body></html>'
        result = promo.add_promotions(page, "index.html", "ormuz")
        self.assertLess(result.index('id="primero"'), result.index('id="projects-mobile-position"'))
        self.assertLess(result.index("data-own-projects"), result.index('id="resto"'))

    def test_unicode_multiline_offsets_and_fallback_are_safe(self):
        page = '<html>\n<head></head><body><main><section><p>' + 'tráfico ' * 20 + '</p></section>\n<p>Final</p></main></body></html>'
        result = promo.add_promotions(page, "index.html", "gibraltar")
        self.assertIn('</section><span id="projects-mobile-position"', result)
        self.assertIn('<p>Final</p><span id="projects-desktop-position"', result)
        minimal = '<html><head></head><body><main><h1>Sin resumen</h1></main></body></html>'
        result = promo.add_promotions(minimal, "index.html", "ormuz")
        self.assertLess(result.index('</h1>'), result.index('data-own-projects'))
        self.assertLess(result.index('projects-desktop-position'), result.index('</main>'))

    def test_mobile_is_compact_and_not_fixed_or_sticky(self):
        css = (Path(__file__).parent / "own-projects.css").read_text()
        mobile = css.split('@media (max-width: 48rem)', 1)[1].split('/* 1280px', 1)[0]
        for unwanted in ('position: fixed', 'position: sticky', 'animation:', 'overflow-y: auto'):
            self.assertNotIn(unwanted, mobile)
        self.assertIn('grid-template-columns: minmax(0, 1fr) 28%', mobile)
        self.assertIn('height: 5.5rem', mobile)

    @unittest.skipUnless(shutil.which('node'), 'Node is required for the responsive placement test')
    def test_responsive_relocation_script(self):
        root = Path(__file__).parent
        result = subprocess.run(['node', '--test', str(root / 'test_own_projects.cjs')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
