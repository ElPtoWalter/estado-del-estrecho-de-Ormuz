"""The approved single-case localization cannot mutate sources or bypass 2A."""

import copy
import json
import unittest
from pathlib import Path

from prepare_phase2a_ormuz_es import ROOT, TITLE_ES, prepare_revision, revise_editorial_input
from phase2_video.schema import package_content_hash, package_id, script_id
from phase2_video.validator import validate_package, validate_script
from phase2_voice.fixtures import load_pilot_fixture
from phase2_voice.input import build_voice_input, validate_upstream
from phase2_voice.schema import VoiceError, voice_config
from test_phase2b_voice import artifact_directory


class EditorialRevisionTests(unittest.TestCase):
    def setUp(self):
        self.package, self.script, self.fixture = load_pilot_fixture("ormuz")

    def test_new_ids_revalidated_without_mutating_original(self):
        originals = copy.deepcopy((self.package, self.script))
        package, script, audit = revise_editorial_input(self.package, self.script)
        self.assertEqual(originals, (self.package, self.script))
        self.assertNotEqual(package["package_id"], self.package["package_id"])
        self.assertNotEqual(script["script_id"], self.script["script_id"])
        self.assertEqual(validate_package(package)["validation_status"], "PASS")
        self.assertEqual(validate_script(package, script)["validation_status"], "PASS")
        self.assertEqual(audit["layer"], "phase2a")
        self.assertEqual(audit["human_review_status"], "PENDING")

    def test_only_authorized_editorial_fields_change(self):
        package, script, _ = revise_editorial_input(self.package, self.script)
        for key in self.package.keys() - {"headlines", "verified_facts", "what_we_know", "content_hash", "package_id"}:
            self.assertEqual(package[key], self.package[key], key)
        self.assertEqual(package["headlines"]["en"], self.package["headlines"]["en"])
        for key in self.package["verified_facts"][0].keys() - {"text_es"}:
            self.assertEqual(package["verified_facts"][0][key], self.package["verified_facts"][0][key], key)
        self.assertEqual(package["headlines"]["es"], TITLE_ES)
        for key in self.script.keys() - {"headline", "scenes", "package_id", "package_content_hash", "estimated_words", "script_id"}:
            self.assertEqual(script[key], self.script[key], key)
        self.assertEqual(script["scenes"][1:], self.script["scenes"][1:])
        for key in self.script["scenes"][0].keys() - {"voiceover", "on_screen_text"}:
            self.assertEqual(script["scenes"][0][key], self.script["scenes"][0][key], key)

    def test_tts_reads_corrected_script_verbatim_same_voice_new_job(self):
        package, script, _ = revise_editorial_input(self.package, self.script)
        config = voice_config("es", voice="es-es-advisor-2")
        value = build_voice_input(package, script, config=config)
        old = build_voice_input(self.package, self.script, config=config)
        self.assertEqual(value["full_text_for_tts"], value["full_editorial_text"])
        self.assertIn(TITLE_ES, value["full_text_for_tts"])
        for token in ("Iran and US", "Houthi", "reuters.com"):
            self.assertNotIn(token, value["full_text_for_tts"])
            self.assertNotIn(token, script["headline"])
            self.assertNotIn(token, script["scenes"][0]["on_screen_text"])
        self.assertEqual(value["voice_config"], old["voice_config"])
        self.assertNotEqual(value["voice_job_id"], old["voice_job_id"])

    def test_other_package_rejected_even_when_structurally_valid(self):
        package = copy.deepcopy(self.package)
        package["headlines"]["es"] = "Otro titular"
        package["content_hash"] = package_content_hash(package)
        package["package_id"] = package_id("ormuz", package["edition_date"], package["content_hash"])
        script = copy.deepcopy(self.script)
        script["package_id"] = package["package_id"]
        script["package_content_hash"] = package["content_hash"]
        script["headline"] = package["headlines"]["es"]
        script["script_id"] = script_id(script)
        self.assertEqual(validate_package(package)["validation_status"], "PASS")
        self.assertEqual(validate_script(package, script)["validation_status"], "PASS")
        with self.assertRaisesRegex(ValueError, "UNAUTHORIZED_EDITORIAL_SOURCE"):
            revise_editorial_input(package, script)

    def test_corrupt_source_rejected(self):
        self.package["operational_context"]["confidence"] = "high"
        with self.assertRaisesRegex(ValueError, "INVALID_EDITORIAL_SOURCE"):
            revise_editorial_input(self.package, self.script)

    def test_old_package_cannot_validate_new_script_or_vice_versa(self):
        package, script, _ = revise_editorial_input(self.package, self.script)
        for candidate_package, candidate_script in ((self.package, script), (package, self.script)):
            with self.assertRaises(VoiceError):
                validate_upstream(candidate_package, candidate_script)

    def test_gibraltar_original_untouched_and_not_localized(self):
        package, script, _ = load_pilot_fixture("gibraltar")
        originals = copy.deepcopy((package, script))
        with self.assertRaisesRegex(ValueError, "UNAUTHORIZED_EDITORIAL_SOURCE"):
            revise_editorial_input(package, script)
        self.assertEqual(originals, (package, script))

    def test_preparation_outside_repo_preserves_provenance_and_refuses_overwrite(self):
        with artifact_directory() as tmp:
            output = Path(tmp) / "editorial"
            report = prepare_revision(output)
            self.assertEqual(report["publication"], "DISABLED")
            self.assertTrue(report["fixture"]["historical_fixture"])
            self.assertEqual(report["fixture"]["source_commit"], self.fixture["source_commit"])
            self.assertEqual({path.name for path in output.iterdir()}, {"video-package.json", "script.json", "validation-report.json"})
            snapshots = {path.name: path.read_bytes() for path in output.iterdir()}
            with self.assertRaisesRegex(ValueError, "EDITORIAL_OUTPUT_ALREADY_EXISTS"):
                prepare_revision(output)
            self.assertEqual(snapshots, {path.name: path.read_bytes() for path in output.iterdir()})
            self.assertEqual(json.loads((output / "script.json").read_text(encoding="utf-8"))["headline"], TITLE_ES)
        with self.assertRaisesRegex(ValueError, "OUTPUT_MUST_BE_OUTSIDE_REPOSITORY"):
            prepare_revision(ROOT / ".never-create-editorial")

    def test_manual_workflow_prepares_editorial_before_voice(self):
        text = (ROOT / ".github/workflows/pilot-phase2b-voice.yml").read_text(encoding="utf-8")
        self.assertLess(text.index("python prepare_phase2a_ormuz_es.py"), text.index("python pilot_phase2b_voice.py"))
        self.assertIn("--package", text)
        self.assertIn("--fixture-metadata", text)
        self.assertNotIn("  push:", text)
        self.assertNotIn("  schedule:", text)


if __name__ == "__main__":
    unittest.main()
