from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from operational_intelligence_v7 import Signal, assess, classify_text_record, iso_z, traffic_measurement

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

    def test_extracts_count_and_reference_average_from_report(self):
        count, average, ratio = traffic_measurement(
            "Three commodity vessels transited the Strait of Hormuz, below the 10-day moving average of about 15"
        )
        self.assertEqual((count, average), (3, 15))
        self.assertAlmostEqual(ratio, 0.2)

    def test_quantified_report_adds_public_traffic_snapshot(self):
        signals = classify_text_record(
            "Three commodity vessels transited the Strait of Hormuz",
            "Reuters",
            "https://example.com/reuters",
            iso_z(NOW - timedelta(hours=2)),
            "fixture",
            description="The recent moving average was about 15 vessels.",
        )
        signals.append(sig("TRANSIT_CONFIRMED", "JMIC / UKMTO", 3, 5))
        result = assess(signals, NOW, {})
        self.assertEqual(result["traffic_snapshot"]["vessels"], 3)
        self.assertEqual(result["traffic_snapshot"]["comparison_average"], 15)
        self.assertEqual(result["dimensions"]["traffic"], "SEVERELY_REDUCED")


if __name__ == "__main__":
    unittest.main()
