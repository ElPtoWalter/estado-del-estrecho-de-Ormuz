from __future__ import annotations

import copy
import unittest

from phase2_video.script import generate_local_script
from phase2_voice.package import build_voice_package
from phase2_voice.schema import voice_content_hash
from test_video_support import package
from test_voice_support import voice_fixture


class VoicePackageTests(unittest.TestCase):
    def test_package_is_deterministic_and_closed(self):
        video, script, left = voice_fixture()
        right = build_voice_package(video, script)
        self.assertEqual(left, right)
        self.assertEqual(left["content_hash"], voice_content_hash(left))
        self.assertTrue(left["voice_package_id"].endswith(left["content_hash"]))
        self.assertTrue(left["human_review_required"])
        self.assertFalse(left["publication_allowed"])
        self.assertFalse(left["voice_profile"]["cloning"])
        self.assertFalse(left["voice_profile"]["network_required"])

    def test_exact_script_order_and_traceability_are_preserved(self):
        _, script, voice = voice_fixture()
        expected_ids = ["hook", *[scene["scene_id"] for scene in script["scenes"]], "outro"]
        self.assertEqual([item["segment_id"] for item in voice["narration"]["segments"]], expected_ids)
        self.assertEqual(
            voice["narration"]["text"],
            "\n".join([script["hook"], *[scene["voiceover"] for scene in script["scenes"]], script["outro"]]),
        )
        for source, copied in zip(script["scenes"], voice["narration"]["segments"][1:-1]):
            self.assertEqual(copied["fact_ids"], source["fact_ids"])
            self.assertEqual(copied["statement_ids"], source["statement_ids"])
            self.assertEqual(copied["source_ids"], source["source_ids"])

    def test_language_profiles_are_explicit_and_change_identity(self):
        video = package()
        es = build_voice_package(video, generate_local_script(video, language="es"))
        en = build_voice_package(video, generate_local_script(video, language="en"))
        self.assertEqual(es["voice_profile"]["voice"], "es")
        self.assertEqual(en["voice_profile"]["voice"], "en-gb")
        self.assertNotEqual(es["content_hash"], en["content_hash"])

    def test_invalid_script_is_blocked_before_voice(self):
        video = package()
        script = generate_local_script(video)
        script["package_id"] = "wrong"
        with self.assertRaisesRegex(ValueError, "invalid-video-script"):
            build_voice_package(video, script)


if __name__ == "__main__":
    unittest.main()
