from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from operational_intelligence_v7 import Signal, assess, iso_z

NOW = datetime(2026, 8, 7, 11, 20, tzinfo=timezone.utc)


def sig(kind, source, hours=12, tier=5, ratio=None, title=None):
    return Signal(
        kind=kind,
        title=title or kind,
        source=source,
        url="https://example.com",
        published_at=iso_z(NOW - timedelta(hours=hours)),
        tier=tier,
        weight={5: 5, 4: 4, 3: 3, 2: 2, 1: 1}[tier],
        provider="fixture",
        traffic_ratio=ratio,
    )


class IntelligenceV7Tests(unittest.TestCase):
    def test_current_like_case_is_open_severely_restricted(self):
        signals = [
            sig("TRANSIT_CONFIRMED", "JMIC / UKMTO", 18, 5),
            sig("TRANSIT_CONFIRMED", "Reuters", 24, 4),
            sig("TRAFFIC_SEVERELY_REDUCED", "JMIC / UKMTO", 18, 5, 0.11),
            sig("ACCESS_RESTRICTED", "Reuters", 8, 4),
            sig("RISK_SEVERE", "JMIC / UKMTO", 18, 5),
        ]
        result = assess(signals, NOW, {})
        self.assertEqual(result["state"], "OPEN_SEVERELY_RESTRICTED")
        self.assertEqual(result["family"], "OPEN")
        self.assertEqual(result["confidence"], "ALTA")

    def test_political_closure_claim_does_not_override_transit(self):
        signals = [
            sig("TRANSIT_CONFIRMED", "JMIC / UKMTO", 6, 5),
            sig("TRANSIT_CONFIRMED", "Reuters", 7, 4),
            sig("FORMAL_CLOSURE_CLAIM", "Reuters", 4, 4),
            sig("RISK_SEVERE", "JMIC / UKMTO", 5, 5),
        ]
        result = assess(signals, NOW, {})
        self.assertTrue(result["state"].startswith("OPEN_"))

    def test_effective_closure_requires_multiple_sources_and_no_recent_transit(self):
        signals = [
            sig("CLOSURE_EFFECTIVE", "JMIC / UKMTO", 5, 5),
            sig("CLOSURE_EFFECTIVE", "Reuters", 6, 4),
            sig("FORMAL_CLOSURE_CLAIM", "Reuters", 4, 4),
        ]
        result = assess(signals, NOW, {})
        self.assertIn(result["state"], {"EFFECTIVELY_CLOSED", "CLOSED_CONFIRMED"})

    def test_single_weak_closure_report_is_not_enough(self):
        result = assess(
            [sig("CLOSURE_EFFECTIVE", "Unknown outlet", 3, 1)],
            NOW,
            {},
        )
        self.assertEqual(result["state"], "UNVERIFIED")

    def test_stale_transit_does_not_force_open(self):
        signals = [
            Signal(
                kind="TRANSIT_CONFIRMED",
                title="Old transit",
                source="JMIC / UKMTO",
                url="https://example.com",
                published_at=iso_z(NOW - timedelta(hours=150)),
                tier=5,
                weight=5,
                provider="fixture",
            )
        ]
        result = assess(signals, NOW, {})
        self.assertEqual(result["state"], "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
