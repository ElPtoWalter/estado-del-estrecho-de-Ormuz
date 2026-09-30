from __future__ import annotations

import unittest
from pathlib import Path

import pilot_phase2b_voice as pilot
from phase2_voice.render import render_voice_package
from test_voice_support import TEST_VOICE_ID, fake_elevenlabs_requester


ROOT = Path(__file__).resolve().parent


def fake_renderer(voice_package, output_path):
    return render_voice_package(
        voice_package,
        output_path,
        api_key="x" * 24,
        requester=fake_elevenlabs_requester,
    )


class Phase2BVoicePilotTests(unittest.TestCase):
    def test_real_fixture_builds_a_green_isolated_pilot(self):
        output = ROOT.parent / "phase2b-pilot-test-output-ormuz"
        output.mkdir(exist_ok=True)
        try:
            result = pilot.run_pilot(
                ROOT, "ormuz", output, renderer=fake_renderer, voice_id=TEST_VOICE_ID,
            )
            self.assertTrue(result["historical_fixture"])
            self.assertEqual(result["voice_package_validation"], "PASS")
            self.assertEqual(result["audio_validation"], "PASS")
            self.assertEqual({path.name for path in output.iterdir()}, pilot.OUTPUT_NAMES)
            preview = (output / "preview.md").read_text(encoding="utf-8")
            self.assertIn("Publicación: **NO**", preview)
            self.assertIn("Revisión humana obligatoria: **SÍ**", preview)
            self.assertIn("Escucha semántica y de pronunciación: **PENDIENTE**", preview)
        finally:
            for name in pilot.OUTPUT_NAMES:
                path = output / name
                if path.exists():
                    path.unlink()
            output.rmdir()

    def test_outputs_inside_repository_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside-repository"):
            pilot.run_pilot(
                ROOT,
                "ormuz",
                ROOT / "phase2b-output",
                renderer=fake_renderer,
                voice_id=TEST_VOICE_ID,
            )

    def test_workflow_is_manual_read_only_paid_guarded_and_non_publishing(self):
        text = (ROOT / ".github" / "workflows" / "pilot-phase2b-voice.yml").read_text(encoding="utf-8")
        lowered = text.casefold()
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("contents: read", text)
        self.assertIn("secrets.elevenlabs_api_key", lowered)
        self.assertIn("vars.elevenlabs_voice_id_es", lowered)
        self.assertIn("confirm_paid_synthesis", lowered)
        self.assertNotIn("pull_request:", text)
        self.assertNotIn("push:", text)
        for forbidden in (
            "git commit", "git push", "youtube", "tiktok", "instagram",
            "voice cloning", "gemini_api_key", "openrouter_api_key",
        ):
            self.assertNotIn(forbidden, lowered)

    def test_workflow_uploads_only_the_eight_approved_files(self):
        text = (ROOT / ".github" / "workflows" / "pilot-phase2b-voice.yml").read_text(encoding="utf-8")
        for name in pilot.OUTPUT_NAMES:
            self.assertIn(name, text)
        self.assertNotIn("path: ${{ runner.temp }}/phase2b-voice\n", text)


if __name__ == "__main__":
    unittest.main()
