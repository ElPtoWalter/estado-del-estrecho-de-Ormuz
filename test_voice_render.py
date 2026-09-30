from __future__ import annotations

import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from phase2_voice.render import render_voice_package
from test_voice_support import fake_elevenlabs_requester, voice_fixture


ROOT = Path(__file__).resolve().parent
UNIT_TEST_API_KEY = "x" * 24


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
    def test_renderer_sends_exact_text_and_keeps_credential_out_of_manifest(self):
        _, _, voice = voice_fixture()
        captured = {}

        def requester(url, body, headers, timeout):
            captured.update(url=url, body=body, headers=headers, timeout=timeout)
            return fake_elevenlabs_requester(url, body, headers, timeout)

        directory = test_output("phase2b-render-test")
        try:
            output = directory / "voice.wav"
            manifest = render_voice_package(
                voice,
                output,
                api_key=UNIT_TEST_API_KEY,
                requester=requester,
                rendered_at=datetime(2026, 9, 30, 10, tzinfo=timezone.utc),
            )
            request = json.loads(captured["body"].decode("utf-8"))
            self.assertEqual(request["text"], voice["narration"]["text"])
            self.assertEqual(request["model_id"], "eleven_multilingual_v2")
            self.assertIn(voice["voice_profile"]["voice"], captured["url"])
            self.assertIn("output_format=pcm_24000", captured["url"])
            self.assertEqual(captured["headers"]["xi-api-key"], UNIT_TEST_API_KEY)
            self.assertTrue(manifest["network_used"])
            self.assertFalse(manifest["cloning_used"])
            self.assertEqual(manifest["engine_version"], "v1")
            self.assertEqual(manifest["model_id"], "eleven_multilingual_v2")
            self.assertEqual(manifest["audio_file"], "voice.wav")
            self.assertNotIn(UNIT_TEST_API_KEY, json.dumps(manifest))
        finally:
            remove_output(directory)

    def test_missing_credential_fails_without_calling_provider(self):
        _, _, voice = voice_fixture()
        directory = test_output("phase2b-render-missing-test")
        try:
            output = directory / "voice.wav"
            with self.assertRaisesRegex(RuntimeError, "credential-missing"):
                render_voice_package(voice, output, api_key="")
            self.assertFalse(output.exists())
        finally:
            remove_output(directory)

    def test_non_wav_output_is_rejected(self):
        _, _, voice = voice_fixture()
        with self.assertRaisesRegex(ValueError, "must-be-wav"):
            render_voice_package(voice, "voice.mp3", api_key=UNIT_TEST_API_KEY)

    def test_tampered_text_is_blocked_before_engine_lookup(self):
        _, _, voice = voice_fixture()
        changed = copy.deepcopy(voice)
        changed["narration"]["text"] += " Texto no autorizado."
        with self.assertRaisesRegex(ValueError, "invalid-voice-package-integrity"):
            render_voice_package(changed, "voice.wav", api_key=UNIT_TEST_API_KEY)

    def test_provider_error_fails_without_writing_audio(self):
        _, _, voice = voice_fixture()
        directory = test_output("phase2b-render-provider-error-test")
        try:
            output = directory / "voice.wav"
            with self.assertRaisesRegex(RuntimeError, "http-error:elevenlabs:429"):
                render_voice_package(
                    voice,
                    output,
                    api_key=UNIT_TEST_API_KEY,
                    requester=lambda url, body, headers, timeout: (429, {}, b'{"detail":"quota"}'),
                )
            self.assertFalse(output.exists())
        finally:
            remove_output(directory)

    def test_provider_error_exposes_only_safe_machine_code(self):
        _, _, voice = voice_fixture()
        directory = test_output("phase2b-render-provider-code-test")
        try:
            output = directory / "voice.wav"
            response = {
                "detail": {
                    "status": "invalid_voice_id",
                    "message": "unsafe provider detail must remain private",
                }
            }
            with self.assertRaisesRegex(
                RuntimeError,
                r"http-error:elevenlabs:400:invalid_voice_id$",
            ) as caught:
                render_voice_package(
                    voice,
                    output,
                    api_key=UNIT_TEST_API_KEY,
                    requester=lambda url, body, headers, timeout: (
                        400,
                        {},
                        json.dumps(response).encode("utf-8"),
                    ),
                )
            self.assertNotIn("unsafe provider detail", str(caught.exception))
            self.assertFalse(output.exists())
        finally:
            remove_output(directory)


if __name__ == "__main__":
    unittest.main()
