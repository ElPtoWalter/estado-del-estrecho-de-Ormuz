from __future__ import annotations

import copy
import io
import json
import socket
import unittest
import urllib.error

from phase2_video.script import generate_local_script, generate_script
from phase2_video.validator import validate_script
from test_video_support import package, reseal_script


class VideoScriptTests(unittest.TestCase):
    def setUp(self):
        self.package = package()

    def gemini_envelope(self, script):
        return {"candidates": [{"content": {"parts": [{"text": json.dumps(script)}]}}]}

    def openrouter_envelope(self, script):
        return {"choices": [{"message": {"content": json.dumps(script)}}]}

    def test_local_script_has_scenes_duration_and_traceability(self):
        script = generate_local_script(self.package)
        report = validate_script(self.package, script)
        self.assertEqual(report["validation_status"], "PASS", report)
        self.assertGreaterEqual(len(script["scenes"]), 3)
        self.assertTrue(all(scene["fact_ids"] for scene in script["scenes"]))
        self.assertTrue(all(scene["source_ids"] for scene in script["scenes"]))
        self.assertEqual(script["generated_by"], "rules")

    def test_local_script_supports_both_languages(self):
        for language in ("es", "en"):
            script = generate_local_script(self.package, language=language)
            self.assertEqual(script["language"], language)
            self.assertEqual(validate_script(self.package, script)["validation_status"], "PASS")

    def test_valid_gemini_script_is_selected_and_locally_sealed(self):
        candidate = generate_local_script(self.package)
        candidate["headline"] = self.package["headlines"]["es"]
        candidate["generated_by"] = "gemini"

        def transport(request, timeout):
            self.assertIn("generativelanguage.googleapis.com", request.full_url)
            self.assertNotIn("test-secret", request.full_url)
            self.assertEqual(request.headers.get("X-goog-api-key"), "test-secret")
            return self.gemini_envelope(candidate)

        script, trace = generate_script(
            self.package,
            gemini_key="test-secret",
            openrouter_key="",
            transport=transport,
        )
        self.assertEqual(script["generated_by"], "gemini")
        self.assertFalse(trace["fallback_used"])
        self.assertEqual(validate_script(self.package, script)["validation_status"], "PASS")
        self.assertNotIn("test-secret", json.dumps(trace))

    def test_gemini_429_uses_rules(self):
        def transport(request, timeout):
            raise urllib.error.HTTPError(request.full_url, 429, "quota", {}, io.BytesIO())

        script, trace = generate_script(self.package, gemini_key="secret", openrouter_key="", transport=transport)
        self.assertEqual(script["generated_by"], "rules")
        self.assertTrue(trace["fallback_used"])
        self.assertEqual(trace["attempts"][0]["status"], "http-429")

    def test_gemini_timeout_uses_rules(self):
        def transport(request, timeout):
            raise socket.timeout("timed out")

        script, trace = generate_script(self.package, gemini_key="secret", openrouter_key="", transport=transport)
        self.assertEqual(script["generated_by"], "rules")
        self.assertEqual(trace["attempts"][0]["status"], "timeout")

    def test_invalid_json_uses_rules(self):
        def transport(request, timeout):
            return {"candidates": [{"content": {"parts": [{"text": "```json\n{}\n```"}]}}]}

        script, trace = generate_script(self.package, gemini_key="secret", openrouter_key="", transport=transport)
        self.assertEqual(script["generated_by"], "rules")
        self.assertEqual(trace["attempts"][0]["status"], "invalid-json")

    def test_openrouter_free_is_second_fallback(self):
        candidate = reseal_script(generate_local_script(self.package), generated_by="openrouter-free")

        def transport(request, timeout):
            if "generativelanguage" in request.full_url:
                raise urllib.error.HTTPError(request.full_url, 429, "quota", {}, io.BytesIO())
            self.assertEqual(request.full_url, "https://openrouter.ai/api/v1/chat/completions")
            self.assertEqual(request.headers.get("Authorization"), "Bearer openrouter-secret")
            return self.openrouter_envelope(candidate)

        script, trace = generate_script(
            self.package,
            gemini_key="gemini-secret",
            openrouter_key="openrouter-secret",
            openrouter_model="some-provider/free-model:free",
            transport=transport,
        )
        self.assertEqual(script["generated_by"], "openrouter-free")
        self.assertFalse(trace["fallback_used"])
        self.assertEqual([item["status"] for item in trace["attempts"]], ["http-429", "ok"])

    def test_invalid_remote_fact_id_is_rejected_before_rules_fallback(self):
        candidate = copy.deepcopy(generate_local_script(self.package))
        candidate["scenes"][0]["fact_ids"] = ["fact-invented"]
        candidate = reseal_script(candidate, generated_by="gemini")

        def transport(request, timeout):
            return self.gemini_envelope(candidate)

        script, trace = generate_script(self.package, gemini_key="secret", openrouter_key="", transport=transport)
        self.assertEqual(script["generated_by"], "rules")
        self.assertIn("UNKNOWN_FACT_ID", trace["attempts"][0]["validation_errors"])

    def test_remote_cannot_replace_package_identity(self):
        candidate = copy.deepcopy(generate_local_script(self.package))
        candidate["package_id"] = "wrong"

        def transport(request, timeout):
            return self.gemini_envelope(candidate)

        script, trace = generate_script(self.package, gemini_key="secret", openrouter_key="", transport=transport)
        self.assertEqual(script["generated_by"], "rules")
        self.assertEqual(trace["attempts"][0]["status"], "valueerror")


if __name__ == "__main__":
    unittest.main()
