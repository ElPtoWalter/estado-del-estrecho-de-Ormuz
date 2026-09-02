import unittest
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

    def test_inserted_after_article_before_main_end(self):
        result = promo.add_promotions(self.page(), "index.html", "ormuz")
        self.assertLess(result.index("</article>"), result.index("data-own-projects"))
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
        self.assertIn("@media (max-width: 42rem)", css)
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
        self.assertIn("own-projects.css?v=20260902-2", promo.add_promotions(self.page(), "index.html", "ormuz"))


if __name__ == "__main__":
    unittest.main()
