"""Regression checks for publication boundaries and dated bilingual distribution."""
import hashlib
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import build_public_site as build
import generate_daily_journal as journal
from publication_quality import ads_authorized, apply_policy, original_review_valid
from free_editorial_ai import editorial_quality_report
from own_projects import eligible


class ObservatoryContracts(unittest.TestCase):
    def test_sources_beyond_first_ten_remain_auditable(self):
        items = [journal.NewsItem(title=f'Headline {i}', url=f'https://example.org/{i}',
                    source='Reuters', published_at='2026-10-23T07:00:00Z',
                    tier=4, topic='energy', query='test') for i in range(12)]
        for lang in ('es', 'en'):
            self.assertIn('https://example.org/11', journal.make_sources(items, lang))

    def test_cached_publisher_mismatch_cannot_enter_the_factual_news_selection(self):
        item = journal.NewsItem('Iran says ships damaged - Epping Forest Guardian', 'The Guardian',
                                'https://news.google.com/rss/articles/example', '2026-10-22T08:00:00Z', 3, 'maritime', '')
        self.assertEqual(journal.dedupe_news([item]), [])
        self.assertEqual(journal.source_tier('Not Reuters Journal'), 0)

    def test_hypotheses_and_commentary_remain_analytical(self):
        self.assertTrue(journal.analytical_headline('Iran could drop mines into the Strait of Hormuz'))
        self.assertTrue(journal.analytical_headline("COMMENTARY: Don't mistake an oil rebound for normality"))
        self.assertFalse(journal.analytical_headline('Iran says seven vessels were damaged'))
    def test_private_previews_cannot_become_public_articles(self):
        for name in ('work/preview.html', 'tests/report.html', '.private/index.html', '_audit/example.html', 'preview.html', 'private-notes.html', 'draft-analysis.html'):
            self.assertFalse(build.public_html_path(Path(name)), name)
        self.assertTrue(build.public_html_path(Path('diario/2026-10-22.html')))
        self.assertFalse(build.copy_asset(Path('monetization.json')))

    def test_public_indexnow_key_is_not_treated_as_a_secret(self):
        self.assertTrue(build.copy_asset(Path('8ee87f80641eba7927c66d271c9380a5.txt')))
        self.assertFalse(build.copy_asset(Path('private-notes.txt')))

    def test_disclosure_survives_public_wording(self):
        text = 'Generado por IA. Seguimiento automatizado. Automated monitoring.'
        self.assertEqual(build.professional_language(text, 'es'), text)

    def test_ads_require_all_explicit_account_attestations(self):
        settings = {'adsense': {key: True for key in ('enabled', 'account_ready', 'cmp_verified', 'publisher_identity_complete')}}
        self.assertTrue(ads_authorized(settings))
        for key in settings['adsense']:
            candidate = json.loads(json.dumps(settings))
            candidate['adsense'][key] = False
            self.assertFalse(ads_authorized(candidate))
        self.assertFalse(ads_authorized({}))

    def test_daily_digest_cannot_be_monetized_by_global_switch(self):
        page = '<html><head><script src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"></script></head><body><main>Text</main></body></html>'
        self.assertNotIn('adsbygoogle', apply_policy(page, 'diario/2026-10-22.html', programmatic_ads=True))
        self.assertIn('noindex,follow', apply_policy(page, 'diario/2026-10-22.html', programmatic_ads=True))
        self.assertNotIn('adsbygoogle', apply_policy(page, 'analysis.html'))
        self.assertIn('adsbygoogle', apply_policy(page, 'analysis.html', programmatic_ads=True))

    def test_programmatic_switch_keeps_labelled_house_promotion_eligible(self):
        page = '<html lang="es"><head></head><body><main>Home</main></body></html>'
        self.assertTrue(eligible(apply_policy(page, 'index.html'), 'index.html', 'ormuz'))

    def test_quality_check_detects_a_safe_but_unedited_template(self):
        draft = {'headline': 'Ormuz: evidencia y límites', 'deck': 'Same deck', 'situation': ['Same paragraph']}
        quality = editorial_quality_report(draft, draft)
        self.assertEqual(quality['template_similarity'], 1)
        self.assertIn('near_identical_to_local_template', quality['flags'])
        self.assertIn('generic_headline', quality['flags'])

    def test_bilingual_metadata_includes_self_reference(self):
        doc = '<html lang="es"><head><link rel="canonical" href="https://estrechoormuz.com/a.html"><link rel="alternate" hreflang="en" href="https://estrechoormuz.com/b.html"></head><body></body></html>'
        result = build.sanitize_html(doc, 'a.html')
        self.assertIn('hreflang="es" href="https://estrechoormuz.com/a.html"', result)

    def original(self):
        page = '<html><head><meta name="content-kind" content="original-draft"><meta name="robots" content="noindex,follow"></head><body><main><a href="https://example.org/a">Source A</a><a href="https://example.net/b">Source B</a></main></body></html>'
        review = {'kind': 'original_analysis', 'facts_checked': True, 'rights_checked': True,
                  'approved': True, 'reviewer': 'Test reviewer', 'reviewed_at': '2020-01-01T12:00:00Z',
                  'original_contribution': 'Reproducible analysis and original calculations with documented limitations, dated evidence and source attribution.',
                  'sha256': hashlib.sha256(page.encode()).hexdigest(),
                  'sources': ['https://example.org/a', 'https://example.net/b']}
        return page, review

    def test_exact_review_can_release_original_but_not_automatic_digest(self):
        page, review = self.original()
        self.assertTrue(original_review_valid(page, review))
        self.assertIn('data-original-review', apply_policy(page, 'original.html', review=review))
        self.assertNotIn('noindex', apply_policy(page, 'original.html', review=review))
        self.assertIn('noindex', apply_policy(page, 'diario/2026-10-22.html', review=review))

    def test_review_is_invalid_after_edit_or_without_proof(self):
        page, review = self.original()
        self.assertFalse(original_review_valid(page + ' changed', review))
        for key, value in [('approved', False), ('reviewed_at', '2999-01-01T00:00:00Z'), ('sources', [{}]), ('original_contribution', '')]:
            candidate = dict(review, **{key: value})
            self.assertFalse(original_review_valid(page, candidate))
        self.assertIn('noindex', apply_policy(page, 'original.html'))

    def test_non_material_daily_snapshot_appears_once_in_both_feeds(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'journal-data').mkdir()
            item = {'date': '2026-10-22', 'generated_at': '2026-10-22T06:00:00Z',
                    'title_es': 'Ormuz: paso restringido', 'title_en': 'Hormuz: restricted passage',
                    'summary_es': 'Instantánea española.', 'summary_en': 'English snapshot.',
                    'url_es': 'https://estrechoormuz.com/diario.html', 'url_en': 'https://estrechoormuz.com/en-diary.html'}
            (root / 'journal-data' / '2026-10-22.json').write_text(json.dumps(item), encoding='utf-8')
            items = journal.feed_editions(root, item, [])
            self.assertEqual(len(items), 1)
            for lang in ('es', 'en'):
                feed = ET.fromstring(journal.feed_xml(items, item['generated_at'], lang))
                entries = feed.findall('{http://www.w3.org/2005/Atom}entry')
                self.assertEqual(len(entries), 1)
                self.assertTrue(entries[0].find('{http://www.w3.org/2005/Atom}id').text.endswith('/' + lang))
                self.assertEqual(entries[0].find('{http://www.w3.org/2005/Atom}summary').text, item['summary_' + lang])

    def test_same_day_schedule_does_not_duplicate_editions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'journal-state.json').write_text('{"last_date":"2026-10-22"}', encoding='utf-8')
            self.assertFalse(journal.scheduled_allowed(root, datetime(2026, 10, 22, 18, tzinfo=journal.MADRID)))

    def test_stale_teaser_never_promises_todays_edition(self):
        result = journal.home_teaser_html('es', {'date': '2020-01-01'})
        self.assertIn('Última edición disponible', result)
        self.assertNotIn('Edición de hoy', result)

    def test_surface_uses_canonical_dimensions_without_inventing_measurements(self):
        page = '<p class="status-advisory"></p><div class="evidence-section"></div>'
        assessment = {'dimension_labels_es': {'passage': 'Confirmado', 'traffic': 'Reducido', 'risk': 'Extremo'}, 'generated_at': '2026-10-22T06:00:00Z'}
        with patch.object(build, 'load_json', return_value={}):
            result = build.render_home_surface(page, assessment, 'es')
        self.assertIn('<dd>Reducido</dd>', result)
        self.assertIn('No es un recuento AIS en tiempo real', result)

    def test_production_jobs_are_guarded_from_development_refs(self):
        root = Path(__file__).parent / '.github' / 'workflows'
        for name in ('update-status.yml', 'diario-ormuz.yml', 'deploy-public.yml'):
            self.assertIn("github.ref == 'refs/heads/main'", (root / name).read_text(encoding='utf-8'))
        self.assertIn("github.event.workflow_run.head_branch == 'main'", (root / 'deploy-public.yml').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
