from pathlib import Path
import unittest
from home_layout import transform
import build_public_site as public
import history_release,energy_release,spain_release,seo_surface

class HomeLayoutTests(unittest.TestCase):
    def test_logo_links_have_an_accessible_name_without_replacing_existing_labels(self):
        doc='<html lang="en"><body><a class="brand brand-v4" href="/en.html"><svg aria-hidden="true"></svg></a><a class="brand" aria-label="Existing" href="/">x</a></body></html>'
        result=public.sanitize_html(doc,"en.html")
        self.assertIn('aria-label="Estrecho Ormuz — Home"',result)
        self.assertIn('aria-label="Existing"',result)
    def baseline(self,name):
        doc=public.sanitize_html((public.ROOT/name).read_text(encoding="utf-8"),name)
        lang=seo_surface.PAGES[name][0]
        asides=''.join(f'<aside class="content-section prose-card"><h2><a href="/{path}">{title}</a></h2></aside>'
                       for path,title,*_ in seo_surface.RESEARCH[lang])
        doc=doc.replace('</main>',asides+'</main>')
        return seo_surface.transform(doc,name)

    def test_reading_order_preserves_all_data_and_links(self):
        import re
        for name in ("index.html","en.html"):
            before=self.baseline(name); after=transform(before,name)
            self.assertEqual(sorted(re.findall(r'href="([^"]+)"',before)),sorted(re.findall(r'href="([^"]+)"',after)))
            self.assertEqual(after.count('class="observatory-dimensions"'),1)
            self.assertEqual(after.count('data-home-assessment'),1)
            self.assertEqual(after.count('data-home-recent'),1)
            self.assertLess(after.index('id="confidence"'),after.index('class="observatory-dimensions"'))
            self.assertLess(after.index('data-home-recent'),after.index('id="evidenceList"'))
            self.assertLess(after.index('JOURNAL_V8_HOME_START'),after.index('data-seo-research'))
            self.assertEqual(after,transform(after,name))

    def test_approved_articles_are_not_transformed(self):
        for name in ("historiales-monitor-ormuz.html","en-hormuz-closure-passage-flows.html",
                     "espana-europa-ormuz-dos-porcentajes.html"):
            self.assertEqual(transform("approved bytes",name),"approved bytes")
            doc='<html lang="es"><body><a class="brand" aria-label="Estrecho Ormuz — Inicio" href="/"><span class="brand-copy">Estrecho Ormuz</span></a></body></html>'
            rendered=public.sanitize_html(doc,name)
            self.assertNotIn("brand-readable-",rendered)
            self.assertIn('aria-label="Estrecho Ormuz — Inicio"',rendered)

if __name__=="__main__":
    unittest.main()
