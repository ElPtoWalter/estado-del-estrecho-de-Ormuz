from __future__ import annotations

import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

import pilot_phase2c_visual as pilot
from phase2_voice.fixtures import load_pilot_fixture


ROOT = Path(__file__).resolve().parent


class Phase2CVisualPilotTests(unittest.TestCase):
    def test_real_historical_fixture_builds_green_local_visuals(self):
        output = ROOT.parent / "phase2c-pilot-test-output-ormuz"
        output.mkdir(exist_ok=True)
        try:
            # Real historic input must not disappear when live events rotate.
            with patch.object(pilot, "select_package", return_value=(load_pilot_fixture("ormuz")[0], load_pilot_fixture("ormuz")[2])):
                result = pilot.run_pilot(ROOT, "ormuz", output)
            self.assertTrue(result["historical_fixture"])
            self.assertEqual(result["validation_status"], "PASS")
            self.assertFalse(result["publication_allowed"])
            self.assertEqual({path.name for path in output.iterdir()}, pilot.OUTPUT_NAMES)
            self.assertEqual(len(list((output / "assets").glob("*.svg"))), result["scene_count"])
            preview = (output / "storyboard.md").read_text(encoding="utf-8")
            self.assertIn("Recursos externos: **NO**", preview)
            self.assertIn("Red utilizada: **NO**", preview)
            self.assertIn("Publicación: **NO**", preview)
        finally:
            shutil.rmtree(output, ignore_errors=True)

    def test_outputs_inside_repository_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside-repository"):
            pilot.run_pilot(ROOT, "ormuz", ROOT / "phase2c-output")

    def test_workflow_is_manual_read_only_and_has_no_credentials(self):
        text = (ROOT / ".github" / "workflows" / "pilot-phase2c-visual.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("contents: read", text)
        self.assertNotIn("pull_request:", text)
        self.assertNotIn("push:", text)
        self.assertNotIn("secrets.", text)
        for forbidden in (
            "git commit", "git push", "deploy", "youtube", "tiktok", "instagram",
            "elevenlabs", "pixverse", "kling", "heygen", "synthesia", "ffmpeg",
        ):
            self.assertNotIn(forbidden, text.casefold())

    def test_workflow_uploads_only_the_approved_output_directory(self):
        text = (ROOT / ".github" / "workflows" / "pilot-phase2c-visual.yml").read_text(encoding="utf-8")
        self.assertIn("${{ runner.temp }}/phase2c-visual", text)
        self.assertIn("if-no-files-found: error", text)


if __name__ == "__main__":
    unittest.main()
