from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import evidence_guard
import update_status


class FinalEditorialGuardTests(unittest.TestCase):
    def test_ona_does_not_match_inside_national(self) -> None:
        self.assertIsNone(update_status.source_profile("National Desk"))
        profile = update_status.source_profile("Oman News Agency")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.source_id, "oman_news")

    def test_national_security_journal_is_non_official(self) -> None:
        profile = update_status.source_profile("National Security Journal")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.source_id, "national_security_journal")
        self.assertFalse(profile.official)
        self.assertEqual(profile.tier, 2)

    def test_analytical_open_headline_is_not_operational_proof(self) -> None:
        title = "CENTCOM Keeps Insisting the Strait of Hormuz Is Open — but Shipping Traffic Has Collapsed"
        signals = update_status.classify_text(title)
        self.assertNotIn("OPEN_OPERATIONAL", signals)
        self.assertIn("RISK_RESTRICTION", signals)

    def test_question_is_not_operational_proof(self) -> None:
        signals = update_status.classify_text("Why Can't Donald Trump Keep the Strait of Hormuz Open?")
        self.assertNotIn("OPEN_OPERATIONAL", signals)

    def test_factual_description_can_confirm_transit(self) -> None:
        signals = update_status.classify_text(
            "Is the Strait of Hormuz open?",
            "UKMTO reports commercial shipping continues through the Strait of Hormuz.",
        )
        self.assertIn("OPEN_OPERATIONAL", signals)

    def test_risk_item_never_becomes_last_valid_confirmation(self) -> None:
        now = update_status.utc_now()
        risk = {
            "signal": "RISK_RESTRICTION", "title": "U.S. forces complete another night of strikes",
            "description": "", "source_name": "U.S. CENTCOM", "source_id": "centcom",
            "source_url": "https://centcom.mil/example", "published_at": update_status.iso_z(now),
            "tier": 5, "official": True, "score": 5.0,
        }
        payload = update_status.finalize_payload(
            previous={}, now=now, status="ABIERTO", operational="OPEN_RESTRICTED",
            confidence="BAJA", summary_es="x", summary_en="x", evidence=[risk],
            verification_ok=True, diagnostics={},
        )
        self.assertIsNone(payload["last_valid_confirmation"])

    def test_invalid_previous_confirmation_is_not_carried(self) -> None:
        now = update_status.utc_now()
        previous = {
            "engine_version": update_status.ENGINE_VERSION, "status": "ABIERTO",
            "last_valid_confirmation": {
                "status": "ABIERTO", "at": update_status.iso_z(now - timedelta(hours=1)),
                "source_name": "U.S. CENTCOM", "source_url": "https://centcom.mil/example",
                "title": "U.S. forces complete another night of strikes",
            },
        }
        self.assertFalse(update_status.previous_is_carryable(previous, now, 18))

    def test_guard_downgrades_unchanged_unsupported_open_state(self) -> None:
        now = update_status.iso_z(update_status.utc_now())
        payload = {
            "engine_version": 3, "status": "ABIERTO", "operational_status": "OPEN_RESTRICTED",
            "confidence": "ALTA", "checked_at": now, "last_change_at": now,
            "verification_ok": True,
            "evidence": [{
                "signal": "RISK_RESTRICTION", "title": "Shipping traffic has collapsed amid attacks",
                "source_name": "Reuters", "source_url": "https://reuters.com/example",
                "published_at": now, "tier": 4, "official": False,
            }],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            status, previous, review, aliases = [root / name for name in ("status.json", "previous.json", "review.json", "aliases.json")]
            status.write_text(json.dumps(payload), encoding="utf-8")
            previous.write_text(json.dumps(payload), encoding="utf-8")
            aliases.write_text(json.dumps({"version": 2, "official_publishers": {}, "publishers": {}}), encoding="utf-8")
            argv = ["evidence_guard.py", "--status", str(status), "--previous", str(previous), "--review", str(review), "--aliases", str(aliases), "--no-restore-generated"]
            with patch.object(sys, "argv", argv), patch.dict(os.environ, {}, clear=False):
                result = evidence_guard.main()
            self.assertEqual(result, 0)
            updated = json.loads(status.read_text(encoding="utf-8"))
            self.assertEqual(updated["status"], "INCIERTO")
            self.assertEqual(updated["operational_status"], "HIGH_RISK_UNCONFIRMED")
            self.assertIsNone(updated["last_valid_confirmation"])
            self.assertTrue(review.exists())


if __name__ == "__main__":
    unittest.main()
