"""Plain-language contract regressions, without API calls or publication."""
import copy
import unittest
from unittest.mock import Mock

from phase2_video.editorial import CLEAR_SCRIPT_VERSION, GLOSSARY, target_seconds
from phase2_video.rules import load_rules
from phase2_video.schema import package_content_hash, package_id
from phase2_video.script import generate_local_script, generate_script
from phase2_video.validator import validate_script
from phase2_voice.fixtures import load_pilot_fixture
from phase2_voice.input import build_voice_input, validate_voice_input
from phase2_voice.schema import load_pronunciation
from phase2_voice.gemini import request_payload
from phase2_visual.storyboard import build_storyboard
from phase2_visual.validator import validate_storyboard
from test_video_support import event, package, reseal_script


def fixture(text="Dos fuentes confirman una reducción del tráfico comercial"):
    return package(event_row=event(headline=text))


class PlainEditorialTests(unittest.TestCase):
    def setUp(self):
        self.package = fixture()
        self.script = generate_local_script(self.package)

    def errors(self, candidate, package_value=None):
        return validate_script(package_value or self.package, reseal_script(candidate))["validation_errors"]

    def test_new_contract_and_deterministic_short_duration(self):
        self.assertEqual(self.script["schema_version"], CLEAR_SCRIPT_VERSION)
        self.assertEqual(validate_script(self.package, self.script)["validation_status"], "PASS")
        self.assertEqual(self.script, generate_local_script(self.package))
        self.assertEqual(self.script["target_seconds"], target_seconds(self.script["estimated_words"], load_rules(), self.script["video_type"]))
        self.assertLess(self.script["target_seconds"], 60)

    def test_input_is_immutable(self):
        original = copy.deepcopy(self.package)
        generate_local_script(self.package)
        self.assertEqual(self.package, original)

    def test_no_technical_padding_or_clerical_yesterday_change(self):
        speech = " ".join(row["voiceover"] for row in self.script["scenes"])
        for token in ("canónico", "Fase Uno", "reglas deterministas", "snapshot", "edición anterior"):
            self.assertNotIn(token, speech)
        self.assertFalse(any(row["evidence_kind"] == "change" for row in self.script["scenes"]))

    def test_news_uses_own_sources_not_state_or_context_as_evidence(self):
        news = self.script["scenes"][0]
        self.assertEqual(news["source_ids"], self.package["verified_facts"][0]["source_ids"])
        state = next(row for row in self.script["scenes"] if row["evidence_kind"] == "state")
        self.assertEqual(state["fact_ids"], [])
        self.assertEqual(state["source_ids"], [])
        self.assertEqual(state["package_fields"], ["operational_context.state", "operational_context.confidence"])

    def test_ope_gets_separate_sourced_definition(self):
        value = fixture("Protección Civil registró 57024 pasajeros y 14140 vehículos en la OPE.")
        script = generate_local_script(value)
        self.assertEqual(validate_script(value, script)["validation_status"], "PASS")
        background = next(row for row in script["scenes"] if row["evidence_kind"] == "background")
        self.assertEqual(background["fact_ids"], [])
        self.assertEqual(background["source_ids"], [])
        self.assertEqual(script["editorial_context"]["background"], [GLOSSARY["ope"]])

    def test_huties_definition_and_pronunciation_review_follow_voice(self):
        value = fixture("Irán y Estados Unidos intercambian amenazas tras ataques hutíes que agravan el conflicto regional.")
        script = generate_local_script(value)
        self.assertEqual(validate_script(value, script)["validation_status"], "PASS")
        voice = build_voice_input(value, script)
        self.assertEqual(voice["schema_version"], "1.1.0")
        self.assertIn("utíes", voice["pending_pronunciation_review"])
        self.assertEqual(voice["editorial_context"], script["editorial_context"])
        self.assertEqual(voice["full_editorial_text"].replace("hutíes", "utíes"), voice["full_text_for_tts"])
        self.assertIn("hutíes", voice["full_editorial_text"])
        self.assertEqual(len(voice["pronunciation_changes"]), 2)
        self.assertTrue(voice["human_review_required"])
        validate_voice_input(value, script, voice)

    def test_huties_h_mute_does_not_change_editorial_or_provider_style(self):
        value = fixture("Se registró una reducción del tráfico tras ataques hutíes.")
        script = generate_local_script(value)
        original = copy.deepcopy(script)
        voice = build_voice_input(value, script)
        self.assertEqual(script, original)
        payload = request_payload(voice)
        self.assertIn("utíes", payload["input"][0]["content"][0]["text"])
        self.assertNotIn("hutíes", payload["input"][0]["content"][0]["text"])
        self.assertEqual(voice["voice_config"]["profile_id"], "straitwatch_es_v2")
        self.assertEqual(voice["voice_config"]["voice"], "es-es-advisor-2")
        self.assertFalse(voice["editorial_context"]["publication_allowed"])

    def test_legacy_voice_identity_uses_unchanged_pronunciation_dictionary(self):
        value, script, _ = load_pilot_fixture("ormuz")
        original = build_voice_input(value, script, pronunciation=load_pronunciation())
        self.assertEqual(build_voice_input(value, script), original)
        self.assertEqual(original["pronunciation_version"], "STRAITWATCH_PRONUNCIATION_V1")
        self.assertEqual(original["pronunciation_changes"], [])

    def test_explicit_pronunciation_dictionary_takes_precedence(self):
        value = fixture("Se registró una reducción del tráfico tras ataques hutíes.")
        script = generate_local_script(value)
        voice = build_voice_input(value, script, pronunciation=load_pronunciation())
        self.assertEqual(voice["full_editorial_text"], voice["full_text_for_tts"])
        self.assertEqual(voice["pronunciation_changes"], [])

    def test_context_definition_cannot_be_altered_or_extended(self):
        value = fixture("Se registró una reducción del tráfico tras ataques hutíes.")
        script = generate_local_script(value)
        script["editorial_context"]["background"][0]["definition"] += " El ataque cerró el estrecho."
        self.assertIn("EDITORIAL_CONTEXT_ALTERED", self.errors(script, value))

    def test_background_cannot_be_used_as_news_evidence(self):
        value = fixture("Se registró una reducción del tráfico tras ataques hutíes.")
        script = generate_local_script(value)
        script["scenes"][0]["voiceover"] += " El ataque ocurrió en Yemen."
        self.assertIn("NEW_ENTITY", self.errors(script, value))

    def test_background_voice_cannot_add_event_claim(self):
        value = fixture("Se registró una reducción del tráfico tras ataques hutíes.")
        script = generate_local_script(value)
        background = next(row for row in script["scenes"] if row["evidence_kind"] == "background")
        background["voiceover"] += " El ataque ocurrió en Yemen."
        self.assertIn("BACKGROUND_TRACE", self.errors(script, value))

    def test_definition_cannot_be_removed(self):
        value = fixture("Se registró una reducción del tráfico tras ataques hutíes.")
        script = generate_local_script(value)
        script["scenes"] = [row for row in script["scenes"] if row["evidence_kind"] != "background"]
        for index, row in enumerate(script["scenes"], 1):
            row["scene_id"] = f"scene-{index:02d}"
        self.assertIn("MISSING_BACKGROUND_DEFINITION", self.errors(script, value))

    def test_number_units_cannot_change(self):
        value = fixture("Protección Civil registró 173 vehículos en la OPE.")
        script = generate_local_script(value)
        script["scenes"][0]["voiceover"] = "Protección Civil registró 173 buques en la OPE."
        self.assertIn("QUANTITY_UNIT_ALTERED", self.errors(script, value))

    def test_confidence_cannot_be_upgraded_with_nonadjacent_words(self):
        self.script["scenes"][0]["voiceover"] += " La confianza de esta evaluación es alta."
        self.assertIn("CONFIDENCE_ALTERED", self.errors(self.script))

    def test_state_and_uncertainty_are_not_model_editable(self):
        state = next(row for row in self.script["scenes"] if row["evidence_kind"] == "state")
        state["voiceover"] = "El estrecho está cerrado."
        errors = self.errors(self.script)
        self.assertIn("CANONICAL_CONTEXT_ALTERED", errors)
        self.assertIn("OPERATIONAL_STATE_ALTERED", errors)

    def test_uncertainty_cannot_be_omitted(self):
        self.script["scenes"] = [row for row in self.script["scenes"] if row["evidence_kind"] != "uncertainty"]
        self.assertIn("UNCERTAINTY_REMOVED", self.errors(self.script))

    def test_unknown_acronym_fails_before_any_remote_call(self):
        value = fixture("UKMTO informa de una reducción del tráfico comercial.")
        transport = Mock()
        with self.assertRaisesRegex(ValueError, "UNEXPLAINED_ACRONYM"):
            generate_script(value, gemini_key="test-only", openrouter_key="", transport=transport)
        transport.assert_not_called()

    def test_unknown_state_is_not_spoken_as_internal_label(self):
        value = copy.deepcopy(self.package)
        value["operational_context"]["state"] = "NEW_UNKNOWN_LABEL"
        value["content_hash"] = package_content_hash(value)
        value["package_id"] = package_id(value["site"], value["edition_date"], value["content_hash"])
        with self.assertRaisesRegex(ValueError, "unmapped-operational-state"):
            generate_local_script(value)

    def test_long_facts_fail_closed_not_truncated_or_padded(self):
        value = fixture(" ".join(["información"] * 50) + ".")
        with self.assertRaisesRegex(ValueError, "LONG_SENTENCE"):
            generate_script(value, gemini_key="", openrouter_key="")

    def test_not_recommended_means_no_script_or_provider_call(self):
        value = package(event_row=event(verification_status="SINGLE_SOURCE"))
        transport = Mock()
        with self.assertRaisesRegex(ValueError, "video-not-recommended"):
            generate_script(value, gemini_key="test-only", openrouter_key="", transport=transport)
        transport.assert_not_called()

    def test_unexplained_secondary_rotation_metric_is_omitted_not_converted(self):
        value, _, _ = load_pilot_fixture("gibraltar")
        script = generate_local_script(value)
        self.assertEqual(validate_script(value, script)["validation_status"], "PASS")
        news = next(row for row in script["scenes"] if row["evidence_kind"] == "news")
        self.assertNotIn("173", news["voiceover"])
        self.assertNotIn("rotaciones", news["voiceover"])
        self.assertIn("57024 pasajeros y 14140 vehículos", news["voiceover"])
        self.assertIn("173 rotaciones", value["verified_facts"][0]["text_es"])

    def test_unknown_rotation_unit_blocks_instead_of_becoming_ship_count(self):
        value = fixture("Protección Civil registró 173 rotaciones en la OPE.")
        with self.assertRaisesRegex(ValueError, "UNEXPLAINED_TECHNICAL_TERM"):
            generate_script(value, gemini_key="", openrouter_key="")

    def test_legacy_real_fixtures_still_pass_without_new_fields(self):
        for site in ("ormuz", "gibraltar"):
            value, script, _ = load_pilot_fixture(site)
            original = copy.deepcopy((value, script))
            self.assertEqual(validate_script(value, script)["validation_status"], "PASS")
            voice = build_voice_input(value, script)
            self.assertEqual(voice["schema_version"], "1.0.0")
            self.assertNotIn("editorial_context", voice)
            self.assertNotIn("scene_evidence", voice)
            self.assertEqual((value, script), original)

    def test_storyboard_labels_context_and_unknowns_honestly(self):
        value = fixture("Protección Civil registró 173 vehículos en la OPE.")
        script = generate_local_script(value)
        storyboard = build_storyboard(value, script)
        self.assertEqual(validate_storyboard(value, script, storyboard)["validation_status"], "PASS")
        self.assertTrue(any(row["eyebrow"] == "PARA ENTENDERLO" for row in storyboard["scenes"]))
        self.assertTrue(any(row["eyebrow"] == "QUÉ NO SABEMOS" for row in storyboard["scenes"]))
        self.assertFalse(any("Fase 1" in row["footer"] for row in storyboard["scenes"]))
        self.assertFalse(storyboard["publication_allowed"])


if __name__ == "__main__":
    unittest.main()


