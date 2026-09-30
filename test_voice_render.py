from __future__ import annotations

import copy
import unittest
from datetime import datetime, timezone
from pathlib import Path

from phase2_voice.render import render_voice_package
from test_voice_support import fake_render_runner, voice_fixture


ROOT = Path(__file__).resolve().parent


def test_output(name: str) -> Path:
    directory = ROOT / ("." + name)
    directory.mkdir(exist_ok=True)
    return directory


def remove_output(directory: Path) -> None:
    for path in directory.iterdir():
        if path.is_file():
            path.unlink()
    directory.rmdir()


class VoiceRenderTests(unittest.TestCase):
    def test_renderer_uses_exact_text_safe_arguments_and_no_network(self):
        _, _, voice = voice_fixture()
        captured = {}

        def runner(command, **kwargs):
            captured["command"] = command
            captured["kwargs"] = kwargs
            return fake_render_runner(command, **kwargs)

        directory = test_output("phase2b-render-test")
        try:
            output = directory / "voice.wav"
            manifest = render_voice_package(
                voice,
                output,
                which=lambda name: "/usr/bin/espeak-ng",
                runner=runner,
                rendered_at=datetime(2026, 9, 30, 10, tzinfo=timezone.utc),
            )
            self.assertEqual(captured["kwargs"]["input"], voice["narration"]["text"])
            self.assertIs(captured["kwargs"]["shell"], False)
            self.assertIn("--stdin", captured["command"])
            self.assertEqual(captured["command"][captured["command"].index("-w") + 1], str(output.resolve()))
            self.assertFalse(manifest["network_used"])
            self.assertFalse(manifest["cloning_used"])
            self.assertEqual(manifest["engine_version"], "eSpeak NG text-to-speech: 1.52.0")
            self.assertNotIn("engine-data", manifest["engine_version"])
            self.assertEqual(manifest["audio_file"], "voice.wav")
        finally:
            remove_output(directory)

    def test_missing_engine_fails_without_fake_audio(self):
        _, _, voice = voice_fixture()
        directory = test_output("phase2b-render-missing-test")
        try:
            output = directory / "voice.wav"
            with self.assertRaisesRegex(RuntimeError, "voice-engine-unavailable"):
                render_voice_package(voice, output, which=lambda name: None)
            self.assertFalse(output.exists())
        finally:
            remove_output(directory)

    def test_non_wav_output_is_rejected(self):
        _, _, voice = voice_fixture()
        with self.assertRaisesRegex(ValueError, "must-be-wav"):
            render_voice_package(voice, "voice.mp3", which=lambda name: "/usr/bin/espeak-ng")

    def test_tampered_text_is_blocked_before_engine_lookup(self):
        _, _, voice = voice_fixture()
        changed = copy.deepcopy(voice)
        changed["narration"]["text"] += " Texto no autorizado."
        with self.assertRaisesRegex(ValueError, "invalid-voice-package-integrity"):
            render_voice_package(changed, "voice.wav", which=lambda name: None)


if __name__ == "__main__":
    unittest.main()
