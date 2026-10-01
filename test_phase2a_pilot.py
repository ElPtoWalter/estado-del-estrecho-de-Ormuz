from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

import pilot_phase2a_video as pilot
from phase2_voice.fixtures import load_pilot_fixture


ROOT = Path(__file__).resolve().parent


class Phase2APilotTests(unittest.TestCase):
    def test_real_historical_fixture_builds_a_green_isolated_pilot(self):
        output = ROOT.parent / "phase2a-pilot-test-output-ormuz"
        output.mkdir(exist_ok=True)
        try:
            with patch.dict(
                os.environ, {"GEMINI_API_KEY": "", "OPENROUTER_API_KEY": ""}, clear=False
            ), patch.object(pilot, "select_package", return_value=(load_pilot_fixture("ormuz")[0], load_pilot_fixture("ormuz")[2])):
                result = pilot.run_pilot(ROOT, "ormuz", output)
            self.assertTrue(result["historical_fixture"])
            self.assertEqual(result["local"], "PASS")
            self.assertEqual(result["remote"], "PASS")
            self.assertEqual({path.name for path in output.iterdir()}, pilot.OUTPUT_NAMES)
            preview = (output / "preview.md").read_text(encoding="utf-8")
            self.assertIn("Fixture histórico: **SÍ**", preview)
            self.assertIn("Publicación: **NO**", preview)
            self.assertIn("Revisión humana obligatoria: **SÍ**", preview)
        finally:
            for name in pilot.OUTPUT_NAMES:
                path = output / name
                if path.exists():
                    path.unlink()
            output.rmdir()

    def test_outputs_inside_repository_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside-repository"):
            pilot.run_pilot(ROOT, "ormuz", ROOT / "phase2a-output")

    def test_workflow_is_manual_read_only_and_non_publishing(self):
        text = (ROOT / ".github" / "workflows" / "pilot-phase2a-video.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("contents: read", text)
        self.assertNotIn("pull_request:", text)
        self.assertNotIn("push:", text)
        for forbidden in (
            "git commit", "git push", "deploy", "youtube", "tiktok", "instagram",
            "elevenlabs", "pixverse", "kling", "ffmpeg",
        ):
            self.assertNotIn(forbidden, text.casefold())

    def test_workflow_uploads_only_the_six_approved_files(self):
        text = (ROOT / ".github" / "workflows" / "pilot-phase2a-video.yml").read_text(encoding="utf-8")
        for name in pilot.OUTPUT_NAMES:
            self.assertIn(name, text)
        self.assertNotIn("path: ${{ runner.temp }}/phase2a-video\n", text)


if __name__ == "__main__":
    unittest.main()
