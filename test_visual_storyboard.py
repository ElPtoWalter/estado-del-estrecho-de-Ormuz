from __future__ import annotations

import copy
import unittest

from phase2_video.schema import script_id
from phase2_video.script import generate_local_script
from phase2_visual.schema import storyboard_content_hash, storyboard_id
from phase2_visual.storyboard import build_storyboard
from test_video_support import package


class VisualStoryboardTests(unittest.TestCase):
    def setUp(self):
        self.package = package()
        self.script = generate_local_script(self.package)

    def test_storyboard_is_deterministic_sealed_and_fills_the_timeline(self):
        first = build_storyboard(self.package, self.script)
        second = build_storyboard(self.package, self.script)
        self.assertEqual(first, second)
        self.assertEqual(first["content_hash"], storyboard_content_hash(first))
        self.assertEqual(first["storyboard_id"], storyboard_id("ormuz", first["content_hash"]))
        self.assertEqual(first["scenes"][0]["start_ms"], 0)
        self.assertEqual(first["scenes"][-1]["end_ms"], self.script["target_seconds"] * 1000)
        self.assertTrue(first["human_review_required"])
        self.assertFalse(first["publication_allowed"])

    def test_every_visual_scene_preserves_script_traceability(self):
        storyboard = build_storyboard(self.package, self.script)
        for source, visual in zip(self.script["scenes"], storyboard["scenes"]):
            self.assertEqual(visual["source_scene_id"], source["scene_id"])
            self.assertEqual(visual["fact_ids"], source["fact_ids"])
            self.assertEqual(visual["statement_ids"], source["statement_ids"])
            self.assertEqual(visual["source_ids"], source["source_ids"])

    def test_presenter_intent_never_creates_an_avatar(self):
        changed = copy.deepcopy(self.script)
        changed["scenes"][0]["visual_intent"] = "presenter"
        changed["script_id"] = script_id(changed)
        storyboard = build_storyboard(self.package, changed)
        self.assertEqual(storyboard["scenes"][0]["resolved_template"], "status-card")
        self.assertNotIn("avatar", str(storyboard).casefold())

    def test_tampered_script_is_rejected_before_storyboarding(self):
        changed = copy.deepcopy(self.script)
        changed["scenes"][0]["fact_ids"] = ["fact-does-not-exist"]
        with self.assertRaisesRegex(ValueError, "invalid-video-script"):
            build_storyboard(self.package, changed)

    def test_script_change_produces_new_storyboard_identity(self):
        changed = copy.deepcopy(self.script)
        changed["scenes"][0]["visual_intent"] = "presenter"
        changed["script_id"] = script_id(changed)
        self.assertNotEqual(
            build_storyboard(self.package, self.script)["storyboard_id"],
            build_storyboard(self.package, changed)["storyboard_id"],
        )


if __name__ == "__main__":
    unittest.main()
