from __future__ import annotations

import copy
import unittest
from pathlib import Path

from phase2_voice.validator import validate_audio, validate_voice_package
from test_voice_support import audio_manifest, voice_fixture, write_wav


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


class VoiceValidatorTests(unittest.TestCase):
    def test_valid_package_passes(self):
        video, script, voice = voice_fixture()
        report = validate_voice_package(video, script, voice)
        self.assertEqual(report["validation_status"], "PASS", report)

    def test_reordered_or_changed_narration_is_rejected(self):
        video, script, voice = voice_fixture()
        changed = copy.deepcopy(voice)
        changed["narration"]["segments"].reverse()
        report = validate_voice_package(video, script, changed)
        self.assertIn("NARRATION_TRACE_CHANGED", report["validation_errors"])

    def test_publication_cloning_and_required_network_cannot_be_changed(self):
        video, script, voice = voice_fixture()
        changed = copy.deepcopy(voice)
        changed["publication_allowed"] = True
        changed["voice_profile"]["cloning"] = True
        changed["voice_profile"]["network_required"] = False
        report = validate_voice_package(video, script, changed)
        self.assertIn("PUBLICATION_ENABLED", report["validation_errors"])
        self.assertIn("VOICE_CLONING_ENABLED", report["validation_errors"])
        self.assertIn("VOICE_NETWORK_DISABLED", report["validation_errors"])

    def test_real_wav_and_manifest_pass(self):
        _, _, voice = voice_fixture()
        directory = test_output("phase2b-validator-green-test")
        try:
            path = directory / "audio-elevenlabs.wav"
            write_wav(path)
            manifest = audio_manifest(voice, path)
            report = validate_audio(voice, manifest, path)
            self.assertEqual(report["validation_status"], "PASS", report)
            self.assertTrue(report["semantic_listening_required"])
        finally:
            remove_output(directory)

    def test_tampering_and_silence_are_rejected(self):
        _, _, voice = voice_fixture()
        directory = test_output("phase2b-validator-red-test")
        try:
            path = directory / "audio-elevenlabs.wav"
            write_wav(path, silent=True)
            manifest = audio_manifest(voice, path)
            manifest["audio_sha256"] = "0" * 64
            report = validate_audio(voice, manifest, path)
            self.assertIn("AUDIO_HASH", report["validation_errors"])
            self.assertIn("AUDIO_SILENT", report["validation_errors"])
        finally:
            remove_output(directory)

    def test_audio_validation_rechecks_voice_package_integrity(self):
        _, _, voice = voice_fixture()
        changed = copy.deepcopy(voice)
        changed["narration"]["text"] += " Alteración."
        directory = test_output("phase2b-validator-integrity-test")
        try:
            path = directory / "audio-elevenlabs.wav"
            write_wav(path)
            report = validate_audio(changed, audio_manifest(changed, path), path)
            self.assertIn("VOICE_PACKAGE_INTEGRITY", report["validation_errors"])
        finally:
            remove_output(directory)


if __name__ == "__main__":
    unittest.main()
