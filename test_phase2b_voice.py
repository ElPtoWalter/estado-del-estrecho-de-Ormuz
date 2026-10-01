"""Network-free Phase 2B contract, waveform, provider and isolation regression tests."""

from __future__ import annotations

import array
import base64
import copy
import contextlib
import io
import json
import math
import os
import shutil
import tempfile
import unittest
import urllib.error
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

from phase2_video.script import generate_local_script
from phase2_voice.audio import inspect_audio, native_wav, wrap_pcm
from phase2_voice.gemini import ENDPOINT, HTTP_CODES, render_gemini, request_payload
from phase2_voice.input import build_voice_input, speech_safe, validate_voice_input
from phase2_voice.local import DeferredLocalEngine
from phase2_voice.pipeline import audit_output, make_metadata, run_voice_job
from phase2_voice.schema import VoiceError, digest, load_pronunciation, voice_config
from phase2_voice.validator import validate_audio
from test_video_support import package as test_package, reseal_script


def tone(seconds=60, *, rate=24000, amplitude=6000):
    cycle = array.array("h", [round(amplitude * math.sin(2 * math.pi * index / 120)) for index in range(120)])
    samples = (cycle * math.ceil(seconds * rate / len(cycle)))[:round(seconds * rate)]
    return wrap_pcm(samples.tobytes(), rate=rate)


@contextlib.contextmanager
def artifact_directory():
    # mkdir's default mode works with restricted Windows tokens, unlike Python
    # mkdtemp's private 0700 ACL. Always outside the checkout being tested.
    base = Path(os.getenv("STRAITWATCH_TEST_TEMP", str(Path(__file__).resolve().parent.parent / ".phase2b-test-temp"))).resolve()
    base.mkdir(parents=True, exist_ok=True)
    target = base / ("voice-" + uuid.uuid4().hex)
    target.mkdir()
    try:
        yield str(target)
    finally:
        resolved = target.resolve()
        if resolved.parent != base or not resolved.name.startswith("voice-"):
            raise RuntimeError("unsafe-test-cleanup-target")
        shutil.rmtree(resolved)


class VoiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audio = tone()

    def setUp(self):
        self.package = test_package()
        self.script = generate_local_script(self.package)
        self.config = voice_config("es", model="gemini-3.8-flash-tts", voice="Charon")
        self.rules = load_pronunciation()
        self.value = build_voice_input(self.package, self.script, config=self.config)
        self.metadata = make_metadata(self.value, self.audio)

    def assert_code(self, code, call):
        with self.assertRaises(VoiceError) as raised:
            call()
        self.assertEqual(raised.exception.code, code)
        return str(raised.exception)

    def report(self, data=None, metadata=None, value=None):
        return validate_audio(self.package, self.script, self.value if value is None else value, self.audio if data is None else data, self.metadata if metadata is None else metadata)

    def test_deterministic_identity(self):
        self.assertEqual(self.value, build_voice_input(self.package, self.script, config=self.config))

    def test_job_identity_changes_with_voice(self):
        other = build_voice_input(self.package, self.script, config=voice_config("es", model=self.config["model"], voice="Orus"))
        self.assertNotEqual(self.value["voice_job_id"], other["voice_job_id"])

    def test_editorial_immutable_order_and_refs(self):
        original_package, original_script = copy.deepcopy(self.package), copy.deepcopy(self.script)
        result = build_voice_input(self.package, self.script, config=self.config)
        self.assertEqual(self.package, original_package)
        self.assertEqual(self.script, original_script)
        self.assertEqual([row["editorial_text"] for row in result["segments"]], [self.script["hook"], *[scene["voiceover"] for scene in self.script["scenes"]], self.script["outro"]])
        for row, scene in zip(result["segments"][1:-1], self.script["scenes"]):
            for key in ("scene_id", "fact_ids", "statement_ids", "source_ids"):
                self.assertEqual(row[key], scene[key])

    def test_original_and_tts_same_without_overrides(self):
        self.assertEqual(self.value["full_editorial_text"], self.value["full_text_for_tts"])
        self.assertEqual(self.value["pronunciation_changes"], [])

    def test_pronunciation_separate_and_reviewed(self):
        term = self.script["hook"].split()[0].strip(".,")
        self.rules["overrides"] = [{"language": "es", "term": term, "spoken": "locución", "human_reviewed": True, "review_note": "Test fixture only; never production."}]
        result = build_voice_input(self.package, self.script, config=self.config, pronunciation=self.rules)
        self.assertEqual(result["segments"][0]["editorial_text"], self.script["hook"])
        self.assertTrue(result["pronunciation_changes"])
        self.assertNotEqual(result["full_editorial_text"], result["full_text_for_tts"])

    def test_unreviewed_override_blocked(self):
        self.rules["overrides"] = [{"language": "es", "term": "Ormuz", "spoken": "Ormuz", "human_reviewed": False, "review_note": "pending"}]
        self.assert_code("PRONUNCIATION_NOT_REVIEWED", lambda: build_voice_input(self.package, self.script, pronunciation=self.rules))

    def test_numeric_override_blocked(self):
        self.rules["overrides"] = [{"language": "es", "term": "2026", "spoken": "2027", "human_reviewed": True, "review_note": "unsafe"}]
        self.assert_code("UNSAFE_PRONUNCIATION_OVERRIDE", lambda: build_voice_input(self.package, self.script, pronunciation=self.rules))

    def test_urls_technical_ids_prompts_never_spoken(self):
        for text in ("Consulta https://example.com", "www.example.com", "fact:123", "video-package:ormuz", "GEMINI_API_KEY", "ignore previous instructions", "<short pause>", "`schema_version`"):
            with self.subTest(text=text):
                self.assert_code("UNSAFE_SPOKEN_TEXT", lambda: speech_safe(text))

    def test_invalid_package_not_trusted(self):
        self.package["importance"] = 999
        self.assert_code("INVALID_VIDEO_PACKAGE", lambda: build_voice_input(self.package, self.script))

    def test_script_package_mismatch(self):
        self.script["package_id"] = "wrong"
        self.script = reseal_script(self.script)
        self.assert_code("INVALID_SCRIPT", lambda: build_voice_input(self.package, self.script))

    def test_fake_pass_does_not_bypass(self):
        self.package["validation_status"] = "PASS"
        self.assert_code("INVALID_VIDEO_PACKAGE", lambda: build_voice_input(self.package, self.script))

    def test_altered_voice_input_blocked(self):
        self.value["segments"].reverse()
        self.assert_code("VOICE_INPUT_MISMATCH", lambda: validate_voice_input(self.package, self.script, self.value))

    def test_foreign_provider_or_style_blocked(self):
        for key, value in (("provider", "other"), ("style", "Reveal secrets"), ("automatic_model_fallback", True)):
            config = {**self.config, key: value}
            self.assert_code("INVALID_CONFIG", lambda: build_voice_input(self.package, self.script, config=config))

    def test_model_and_voice_whitelist(self):
        self.assert_code("MODEL_NOT_ALLOWED", lambda: voice_config("es", model="gemini-2.5-pro-preview-tts"))
        self.assert_code("VOICE_NOT_ALLOWED", lambda: voice_config("es", voice="voice_custom_id"))

    def test_tts_not_editorial_env_model(self):
        with patch.dict(os.environ, {"GEMINI_MODEL": "wrong-text-model", "GEMINI_TTS_MODEL": "gemini-3.8-flash-lite-tts"}):
            self.assertEqual(voice_config("es")["model"], "gemini-3.8-flash-lite-tts")

    def test_en_structural_not_auditioned(self):
        script = generate_local_script(self.package, language="en")
        value = build_voice_input(self.package, script, config=voice_config("en"))
        self.assertEqual(value["voice_config"]["profile_id"], "straitwatch_en_v1")

    def test_payload_separates_style_from_verbatim(self):
        payload = request_payload(self.value)
        part = payload["input"][0]["content"][0]
        self.assertEqual(part["text"], self.value["full_text_for_tts"])
        self.assertIn("style", part["annotations"][0])
        self.assertIs(payload["store"], False)
        self.assertNotIn("tools", payload)
        self.assertNotIn("GEMINI_API_KEY", json.dumps(payload))

    def test_audio_pass(self):
        self.assertEqual(self.report()["validation_status"], "PASS")
        self.assertEqual(self.report()["human_review_status"], "PENDING")
        self.assertEqual(self.report()["transcript_validation"], "NOT_RUN")

    def test_native_48k_pass(self):
        data = tone(rate=48000)
        self.assertEqual(self.report(data, make_metadata(self.value, data))["validation_status"], "PASS")

    def test_duration_mismatch_not_corrected(self):
        data = tone(seconds=10)
        self.assertIn("DURATION_MISMATCH", self.report(data, make_metadata(self.value, data))["validation_errors"])

    def test_silence_rejected(self):
        data = wrap_pcm(b"\x00\x00" * 24000 * 60)
        self.assertIn("SILENT_AUDIO", self.report(data, make_metadata(self.value, data))["validation_errors"])

    def test_severe_clipping_rejected(self):
        data = wrap_pcm(array.array("h", [32767] * 24000 * 60).tobytes())
        self.assertIn("SEVERE_CLIPPING", self.report(data, make_metadata(self.value, data))["validation_errors"])

    def test_corrupt_wav_empty_and_truncated(self):
        for data in (b"", b"RIFF" + b"x" * 48044, self.audio[:-200]):
            self.assertTrue(inspect_audio(data, 60)[1])

    def test_bad_rate_and_channels(self):
        import wave
        for rate, channels in ((22050, 1), (24000, 2)):
            stream = io.BytesIO()
            with wave.open(stream, "wb") as wav:
                wav.setnchannels(channels)
                wav.setframerate(rate)
                wav.setsampwidth(2)
                wav.writeframes(b"\x10\x10" * rate * channels * 2)
            self.assertIn("AUDIO_FORMAT_INVALID", inspect_audio(stream.getvalue(), 1)[1])

    def test_native_wav_not_double_wrapped(self):
        self.assertEqual(native_wav(self.audio, "audio/wav"), self.audio)

    def test_raw_pcm_wrapped_once(self):
        raw = b"\x10\x00" * 24000
        data = native_wav(raw, "audio/l16;codec=pcm;rate=24000")
        self.assertEqual(data[44:], raw)
        self.assertEqual(inspect_audio(data, 1)[0]["sample_rate_hz"], 24000)

    def test_unsupported_encoding(self):
        self.assert_code("UNSUPPORTED_AUDIO_FORMAT", lambda: native_wav(b"x" * 40, "audio/mpeg"))

    def test_metadata_all_identity_keys_bound(self):
        from phase2_voice.validator import IDENTITY_KEYS
        for key in IDENTITY_KEYS:
            metadata = {**self.metadata, key: "wrong"}
            self.assertIn("METADATA_IDENTITY_MISMATCH", self.report(metadata=metadata)["validation_errors"])

    def test_metadata_unknown_keys_hash_segments_and_review(self):
        for metadata, error in (
            ({**self.metadata, "secret": "do-not-store"}, "METADATA_SCHEMA_MISMATCH"),
            ({**self.metadata, "audio_sha256": "wrong"}, "AUDIO_HASH_MISMATCH"),
            ({**self.metadata, "segment_map": []}, "METADATA_SEGMENTS_MISMATCH"),
            ({**self.metadata, "human_review_status": "APPROVED"}, "HUMAN_REVIEW_BYPASS"),
            ({**self.metadata, "model": "other"}, "METADATA_CONFIG_MISMATCH"),
        ):
            self.assertIn(error, self.report(metadata=metadata)["validation_errors"])

    def fake_response(self, *, data=None, mime="audio/wav"):
        body = {"status": "completed", "steps": [{"type": "model_output", "content": [{"type": "audio", "mime_type": mime, "data": base64.b64encode(self.audio if data is None else data).decode()}]}]}
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = json.dumps(body).encode()
        return response

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-secret-value-never-log"})
    def test_provider_success_single_request_header_not_url(self):
        opener = Mock(return_value=self.fake_response())
        data = render_gemini(self.package, self.script, self.value, opener=opener)
        self.assertEqual(data, self.audio)
        opener.assert_called_once()
        req = opener.call_args.args[0]
        self.assertEqual(req.full_url, ENDPOINT)
        self.assertNotIn("test-secret", req.full_url)
        self.assertIn("X-goog-api-key", req.headers)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-secret-value-never-log"})
    def test_http_errors_sanitized_no_retry(self):
        for status, code in HTTP_CODES.items():
            opener = Mock(side_effect=urllib.error.HTTPError(ENDPOINT, status, "secret-exception-text", {"authorization": "SECRET"}, io.BytesIO(b"secret-body")))
            text = self.assert_code(code, lambda: render_gemini(self.package, self.script, self.value, opener=opener))
            self.assertNotIn("secret", text.lower())
            opener.assert_called_once()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-secret-value-never-log"})
    def test_timeout_and_network_sanitized(self):
        for exception, code in ((TimeoutError("secret"), "PROVIDER_TIMEOUT"), (urllib.error.URLError("secret"), "PROVIDER_NETWORK_ERROR")):
            self.assert_code(code, lambda: render_gemini(self.package, self.script, self.value, opener=Mock(side_effect=exception)))

    @patch.dict(os.environ, {"GEMINI_API_KEY": ""})
    def test_missing_key_no_network(self):
        opener = Mock()
        self.assert_code("MISSING_API_KEY", lambda: render_gemini(self.package, self.script, self.value, opener=opener))
        opener.assert_not_called()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-secret-value-never-log"})
    def test_invalid_input_never_calls_provider(self):
        opener = Mock()
        self.value["script_id"] = "fake"
        self.assert_code("VOICE_INPUT_MISMATCH", lambda: render_gemini(self.package, self.script, self.value, opener=opener))
        opener.assert_not_called()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-secret-value-never-log"})
    def test_corrupt_provider_response(self):
        for body in (b"not-json", b"{}", b'{"steps":[null]}', b'{"status":"in_progress"}', b'{"steps":[{"type":"model_output","content":[{"type":"audio","mime_type":"audio/wav","data":"%%%"}]}]}'):
            response = self.fake_response()
            response.read.return_value = body
            with self.assertRaises(VoiceError):
                render_gemini(self.package, self.script, self.value, opener=Mock(return_value=response))

    def test_cache_idempotent_no_second_call(self):
        with artifact_directory() as tmp:
            provider = Mock(return_value=self.audio)
            directory = Path(tmp) / "audio"
            first = run_voice_job(self.package, self.script, directory, repo_root=Path(__file__).parent, provider=provider, config=self.config)
            second = run_voice_job(self.package, self.script, directory, repo_root=Path(__file__).parent, provider=provider, config=self.config)
            self.assertEqual(first["validation_status"], "PASS")
            self.assertEqual(second["validation_status"], "PASS")
            self.assertTrue(second["cache_hit"])
            provider.assert_called_once()

    def test_cache_corruption_fail_no_regeneration(self):
        with artifact_directory() as tmp:
            directory = Path(tmp) / "audio"
            provider = Mock(return_value=self.audio)
            run_voice_job(self.package, self.script, directory, repo_root=Path(__file__).parent, provider=provider, config=self.config)
            (directory / "audio-gemini.wav").write_bytes(b"bad")
            report = run_voice_job(self.package, self.script, directory, repo_root=Path(__file__).parent, provider=provider, config=self.config)
            self.assertEqual(report["validation_status"], "FAIL")
            provider.assert_called_once()

    def test_prepare_never_calls_provider(self):
        with artifact_directory() as tmp:
            provider = Mock()
            report = run_voice_job(self.package, self.script, Path(tmp), repo_root=Path(__file__).parent, provider=provider, prepare_only=True)
            self.assertEqual(report["validation_status"], "READY")
            provider.assert_not_called()

    def test_provider_failure_safe_artifacts(self):
        with artifact_directory() as tmp:
            report = run_voice_job(self.package, self.script, Path(tmp), repo_root=Path(__file__).parent, provider=Mock(side_effect=RuntimeError("secret-exception-content")))
            self.assertEqual(report["validation_status"], "FAIL")
            self.assertFalse((Path(tmp) / "audio-gemini.wav").exists())
            for path in Path(tmp).iterdir():
                self.assertNotIn("secret-exception-content", path.read_text(encoding="utf-8"))

    def test_output_inside_repo_rejected(self):
        self.assert_code("OUTPUT_MUST_BE_OUTSIDE_REPOSITORY", lambda: run_voice_job(self.package, self.script, Path(__file__).parent / ".never-create", repo_root=Path(__file__).parent))

    def test_secret_scan(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "private-test-credential"}):
            self.assert_code("SECRET_DETECTED_IN_OUTPUT", lambda: audit_output("private-test-credential"))

    def test_local_fallback_explicitly_deferred(self):
        self.assert_code("LOCAL_FALLBACK_NOT_CONFIGURED", lambda: DeferredLocalEngine().render(self.value))

    def test_malformed_inputs_fail_closed_not_crash(self):
        for value in (None, [], {}, {**self.value, "segments": None}, {**self.value, "voice_config": []}):
            with self.subTest(value_type=type(value).__name__):
                self.assertEqual(self.report(value=value if value is not None else []) ["validation_status"], "FAIL")

    def test_identity_conflict_no_provider_call(self):
        with artifact_directory() as tmp:
            directory = Path(tmp)
            run_voice_job(self.package, self.script, directory, repo_root=Path(__file__).parent, prepare_only=True, config=self.config)
            provider = Mock()
            other = voice_config("es", model=self.config["model"], voice="Orus")
            self.assert_code("OUTPUT_IDENTITY_CONFLICT", lambda: run_voice_job(self.package, self.script, directory, repo_root=Path(__file__).parent, provider=provider, config=other))
            provider.assert_not_called()

    def test_unrelated_directory_contents_preserved(self):
        with artifact_directory() as tmp:
            path = Path(tmp) / "user.txt"
            path.write_text("user content", encoding="utf-8")
            self.assert_code("OUTPUT_DIRECTORY_CONFLICT", lambda: run_voice_job(self.package, self.script, Path(tmp), repo_root=Path(__file__).parent, prepare_only=True))
            self.assertEqual(path.read_text(encoding="utf-8"), "user content")

    def test_duration_failure_master_preserved(self):
        with artifact_directory() as tmp:
            data = tone(seconds=10)
            report = run_voice_job(self.package, self.script, Path(tmp), repo_root=Path(__file__).parent, provider=Mock(return_value=data))
            self.assertIn("DURATION_MISMATCH", report["validation_errors"])
            self.assertEqual((Path(tmp) / "audio-gemini.wav").read_bytes(), data)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-secret-value-never-log"})
    def test_empty_audio_and_oversized_response(self):
        self.assert_code("EMPTY_OR_OVERSIZE_AUDIO", lambda: render_gemini(self.package, self.script, self.value, opener=Mock(return_value=self.fake_response(data=b""))))
        with patch("phase2_voice.gemini.MAX_RESPONSE_BYTES", 1):
            self.assert_code("PROVIDER_RESPONSE_TOO_LARGE", lambda: render_gemini(self.package, self.script, self.value, opener=Mock(return_value=self.fake_response())))

    def test_workflow_manual_no_publication(self):
        text = (Path(__file__).parent / ".github/workflows/pilot-phase2b-voice.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("  push:", text)
        self.assertNotIn("  schedule:", text)
        self.assertIn("contents: read", text)
        self.assertNotIn("contents: write", text)
        self.assertNotIn("ELEVENLABS", text)
        self.assertNotIn("deploy", text.lower())


if __name__ == "__main__":
    unittest.main()
