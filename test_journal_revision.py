"""Editorial regressions: distinct prose, dated context and permanent distribution."""
import copy
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import generate_daily_journal as journal
from check_public_links import check
from free_editorial_ai import editorial_quality_report, _normalize_supplied_names, _validate_candidate, _entity_supported
from journal_evidence import primary_context, classify_headline
from test_free_editorial_ai import valid_draft

ROOT = Path(__file__).parent


class JournalRevisionTests(unittest.TestCase):
    def test_a_spill_story_is_not_mistaken_for_an_oil_price_report(self):
        self.assertEqual(classify_headline('Oil spill hits beaches as tanker attacks multiply'), 'maritime')
        self.assertEqual(classify_headline('Oil prices rise after tanker attacks'), 'energy')
    def test_repeat_detector_compares_fields_not_just_the_template(self):
        draft = valid_draft()
        draft['situation'][0] = draft['deck']
        quality = editorial_quality_report(draft, {})
        self.assertIn('repeated_sentence_across_fields', quality['flags'])
        self.assertFalse(quality['style_checks_passed'])

    def test_typography_only_normalizes_places_already_in_the_packet(self):
        facts = {'selected_sources': [{'title': 'Iran and the Strait of Hormuz in the Middle East'}]}
        value = {'headline': 'ormuz y oriente medio: seguimiento de irán', 'meaning': ['Atlantis remains absent.']}
        result = _normalize_supplied_names(value, facts, 'es')
        self.assertEqual(result['headline'], 'Ormuz y Oriente Medio: seguimiento de Irán')
        self.assertEqual(result['meaning'], value['meaning'])
        self.assertEqual(_normalize_supplied_names('oriente medio', {}, 'es'), 'oriente medio')
        self.assertTrue(_entity_supported('estados unidos', 'Iran warns US about shipping'))
        self.assertFalse(_entity_supported('estados unidos', 'Shipping report from Reuters'))
        self.assertEqual(_normalize_supplied_names('U.S. CENTCOM', {'title': 'US alert'}, 'en'), 'U.S. CENTCOM')

    def test_primary_context_is_dated_and_bound_to_the_reviewed_text(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = json.loads((ROOT / 'editorial-context.json').read_text(encoding='utf-8'))
            path = root / 'editorial-context.json'
            path.write_text(json.dumps(original), encoding='utf-8')
            self.assertEqual(len(primary_context(root, date(2026, 10, 23))), 1)
            self.assertEqual(primary_context(root, date(2026, 10, 22)), [])
            original['items'][0]['fact_es'] += ' An unreviewed extra claim.'
            path.write_text(json.dumps(original), encoding='utf-8')
            self.assertEqual(primary_context(root, date(2026, 10, 23)), [])

    def test_historical_primary_source_needs_its_period_in_the_same_block(self):
        draft = valid_draft()
        draft['meaning'][0] += ' La EIA aporta una referencia histórica para interpretar la relevancia del corredor.'
        facts = {'selected_sources': [{'source': 'Reuters'}],
                 'primary_context': [{'source': 'EIA', 'reference_period': '2024'}]}
        diagnostics = {}
        self.assertIsNone(_validate_candidate({'es': draft}, facts=facts, fallbacks={'es': valid_draft()},
            sources_by_section={'es': {'Tráfico': ['Reuters']}}, diagnostics=diagnostics)[0])
        self.assertEqual(diagnostics['reason'], 'required-dated-primary-context')

    def test_generic_market_prose_cannot_replace_a_spill_headline(self):
        draft = valid_draft()
        draft['sections'][0]['paragraph'] = 'Euronews ha informado de que los precios del petróleo y el suministro global continúan condicionados por las incidencias en las rutas energéticas.'
        facts = {'editorial_brief': {'mode': 'continuity'}, 'selected_sources': [
            {'source': 'Euronews', 'title': 'Oil spill hits beaches', 'grounding': {'anchors': ['vertido', 'derrame', 'oil spill']}}]}
        diagnostics = {}
        self.assertIsNone(_validate_candidate({'es': draft}, facts=facts, fallbacks={'es': valid_draft()},
            sources_by_section={'es': {'Tráfico': ['Euronews']}}, diagnostics=diagnostics)[0])
        self.assertEqual(diagnostics['reason'], 'section-headline-grounding')

    def test_rephrased_assessment_in_lead_is_an_editorial_flag(self):
        draft = valid_draft()
        draft['deck'] = 'La navegación mantiene tránsitos confirmados y restricciones de seguridad.'
        draft['situation'][0] = 'Los tránsitos comerciales sufren restricciones de seguridad durante la jornada.'
        self.assertIn('assessment_repeated_in_lead', editorial_quality_report(draft, {})['flags'])

    def test_a_number_elsewhere_in_packet_does_not_authorize_another_publishers_claim(self):
        draft = valid_draft()
        draft['sections'][0]['paragraph'] += ' Reuters calcula 77 unidades.'
        facts = {'editorial_brief': {'mode': 'continuity'},
                 'selected_sources': [{'source': 'Reuters', 'title': 'Shipping traffic'},
                                      {'source': 'Bloomberg', 'title': '77 units in another story'}]}
        diagnostics = {}
        self.assertIsNone(_validate_candidate({'es': draft}, facts=facts, fallbacks={'es': valid_draft()},
            sources_by_section={'es': {'Tráfico': ['Reuters']}}, diagnostics=diagnostics)[0])
        self.assertEqual(diagnostics['reason'], 'section-number-provenance')

    def test_live_diary_links_are_rejected_even_if_feed_xml_is_called_directly(self):
        item = {'date': '2026-10-22', 'url_es': journal.BASE_URL + '/diario.html',
                'url_en': journal.BASE_URL + '/en-diary.html'}
        for lang in ('es', 'en'):
            self.assertNotIn('<entry>', journal.feed_xml([item], '2026-10-23T00:00:00Z', lang))

    def test_public_artifact_checks_historical_links_noindex_and_ad_exclusion(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'index.html').write_text('<html><body>Home</body></html>', encoding='utf-8')
            item = {'date': '2026-10-22', 'url_es': journal.BASE_URL + '/diario/2026-10-22.html'}
            (root / 'diario-feed.xml').write_text(journal.feed_xml([item], '2026-10-23T00:00:00Z'), encoding='utf-8')
            self.assertTrue(any('missing historical' in error for error in check(root)))
            (root / 'diario').mkdir()
            page = root / 'diario/2026-10-22.html'
            page.write_text('<html><head><meta name="robots" content="noindex,follow"></head><body>Archive</body></html>', encoding='utf-8')
            self.assertEqual(check(root), [])
            page.write_text('<html><body>adsbygoogle</body></html>', encoding='utf-8')
            errors = check(root)
            self.assertTrue(any('noindex' in error for error in errors))
            self.assertTrue(any('advertising' in error for error in errors))


if __name__ == '__main__':
    unittest.main()
