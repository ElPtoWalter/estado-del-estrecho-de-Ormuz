from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

import pilot_gemini_phase1 as pilot


ROOT = Path(__file__).resolve().parent


class Phase1PilotTests(unittest.TestCase):
    def test_real_data_pilot_requires_an_explicit_gemini_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "GEMINI_API_KEY"):
                pilot.run_pilot(ROOT)

    def test_local_and_gemini_must_use_the_same_packet(self) -> None:
        draft = {
            "es": {"headline": "Estado", "deck": "Resumen", "situation": [], "sections": [], "meaning": [], "watch": []},
            "en": {"headline": "Status", "deck": "Summary", "situation": [], "sections": [], "meaning": [], "watch": []},
        }
        trace = {
            "validator_version": 2,
            "factual_packet_hash": "a" * 64,
            "event_ids": ["evt_test"],
            "source_ids": ["reuters"],
            "verification_summary": {"CONFIRMED_MULTI_SOURCE": 1},
            "fallback_used": True,
            "attempts": [],
        }
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-only"}, clear=True):
            with patch.object(
                pilot.journal,
                "editorial_drafts",
                side_effect=[
                    (draft, "rules", "no-key", trace),
                    (draft, "gemini", "ok", {**trace, "fallback_used": False}),
                ],
            ):
                report = pilot.run_pilot(ROOT)
        self.assertTrue(report["passed"])
        self.assertFalse(report["published"])
        self.assertTrue(report["checks"]["same_factual_packet"])

    def test_failure_diagnostics_are_actionable_and_do_not_include_drafts(self) -> None:
        report = {
            "checks": {"same_factual_packet": True, "gemini_selected": False},
            "gemini": {
                "engine": "rules",
                "assistant_status": "gemini-validation-es",
                "attempts": [{"provider": "gemini", "model": "gemini-2.5-flash-lite", "raw": "secret"}],
                "drafts": {"es": {"headline": "private response"}},
            },
        }
        diagnostics = pilot.safe_failure_diagnostics(report)
        self.assertEqual(diagnostics["failed_checks"], ["gemini_selected"])
        self.assertEqual(diagnostics["gemini_status"], "gemini-validation-es")
        self.assertNotIn("raw", diagnostics["attempts"][0])
        self.assertNotIn("drafts", diagnostics)


if __name__ == "__main__":
    unittest.main()
