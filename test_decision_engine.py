from __future__ import annotations

import unittest
from datetime import timedelta

import update_status as engine


class DecisionEngineTests(unittest.TestCase):
    def article(
        self,
        *,
        title: str,
        description: str = "",
        source_name: str = "Reuters",
        source_id: str = "reuters",
        tier: int = 4,
        weight: float = 4.0,
        official: bool = False,
        hours_ago: int = 1,
    ) -> dict:
        now = engine.utc_now()
        return {
            "title": title,
            "description": description,
            "url": f"https://example.com/{source_id}/{hours_ago}",
            "source_name": source_name,
            "source_id": source_id,
            "tier": tier,
            "base_weight": weight,
            "official": official,
            "published_at": engine.iso_z(now - timedelta(hours=hours_ago)),
            "provider": "test",
        }

    def analyze(self, articles: list[dict], previous: dict | None = None) -> dict:
        now = engine.utc_now()
        evidence = engine.evidence_from_articles(articles, now, now - timedelta(hours=100))
        return engine.analyze_evidence(evidence, previous or {}, now, 18)

    def test_declaration_does_not_equal_operational_closure(self) -> None:
        result = self.analyze([
            self.article(title="Iran declares closure of the Strait of Hormuz")
        ])
        self.assertEqual(result["status"], "INCIERTO")
        self.assertEqual(result["operational_status"], "CLOSURE_DECLARED_UNCONFIRMED")

    def test_official_open_route_with_risk_is_open_restricted(self) -> None:
        result = self.analyze([
            self.article(
                title="UKMTO says southern route through the Strait of Hormuz remains open",
                description="Vessels continue to transit despite mines and congestion.",
                source_name="UKMTO",
                source_id="ukmto",
                tier=5,
                weight=5.0,
                official=True,
            )
        ])
        self.assertEqual(result["status"], "ABIERTO")
        self.assertEqual(result["operational_status"], "OPEN_RESTRICTED")
        self.assertEqual(result["confidence"], "ALTA")

    def test_two_independent_operational_closure_reports_confirm_closed(self) -> None:
        result = self.analyze([
            self.article(
                title="Shipping halted through the Strait of Hormuz",
                description="No commercial vessels are transiting the Strait of Hormuz.",
                source_id="reuters",
                source_name="Reuters",
                tier=4,
                weight=4.0,
            ),
            self.article(
                title="Maritime traffic stopped in the Strait of Hormuz",
                description="The passage through the Strait of Hormuz is blocked.",
                source_id="ap",
                source_name="Associated Press",
                tier=4,
                weight=4.0,
                hours_ago=2,
            ),
        ])
        self.assertEqual(result["status"], "CERRADO")
        self.assertEqual(result["operational_status"], "CLOSED_CONFIRMED")

    def test_close_declaration_plus_open_route_is_not_closed(self) -> None:
        result = self.analyze([
            self.article(title="Iran closes the Strait of Hormuz", source_id="bbc", source_name="BBC", tier=3, weight=3.2),
            self.article(
                title="UKMTO says the Strait of Hormuz remains open",
                description="A safe southern route remains open but risk is elevated.",
                source_name="UKMTO",
                source_id="ukmto",
                tier=5,
                weight=5.0,
                official=True,
            ),
        ])
        self.assertEqual(result["status"], "ABIERTO")
        self.assertEqual(result["operational_status"], "OPEN_RESTRICTED")

    def test_conflicting_operational_signals_are_uncertain(self) -> None:
        result = self.analyze([
            self.article(
                title="UKMTO confirms no safe transit through the Strait of Hormuz",
                source_name="UKMTO",
                source_id="ukmto",
                tier=5,
                weight=5.0,
                official=True,
            ),
            self.article(
                title="IMO says the Strait of Hormuz remains open",
                source_name="IMO",
                source_id="imo",
                tier=5,
                weight=5.0,
                official=True,
            ),
        ])
        self.assertEqual(result["status"], "INCIERTO")
        self.assertEqual(result["operational_status"], "CONTRADICTORY")

    def test_hypothetical_closure_is_ignored(self) -> None:
        signals = engine.classify_text("Oil prices rise on fear Iran could close the Strait of Hormuz")
        self.assertNotIn("CLOSURE_DECLARED", signals)
        self.assertNotIn("CLOSED_OPERATIONAL", signals)

    def test_official_southern_route_available_is_open_restricted(self) -> None:
        result = self.analyze([
            self.article(
                title="Strait of Hormuz Southern Route Remains Available",
                description="The regional maritime threat level remains SEVERE.",
                source_name="UKMTO",
                source_id="ukmto",
                tier=5,
                weight=5.0,
                official=True,
            )
        ])
        self.assertEqual(result["status"], "ABIERTO")
        self.assertEqual(result["operational_status"], "OPEN_RESTRICTED")
        self.assertEqual(result["confidence"], "ALTA")

    def test_document_date_is_extracted_from_official_title(self) -> None:
        parsed = engine.date_from_result_text("JMIC Advisory Note: 014-26 | July 12, 2026")
        self.assertEqual(parsed.year, 2026)
        self.assertEqual(parsed.month, 7)
        self.assertEqual(parsed.day, 12)

    def test_manual_override_object_is_applied(self) -> None:
        now = engine.utc_now()
        payload = engine.manual_override_payload(
            {
                "manual_override": {
                    "status": "ABIERTO",
                    "operational_status": "OPEN_RESTRICTED",
                    "confidence": "ALTA",
                    "reason_es": "Revisión manual confirmada.",
                    "reason_en": "Manual review confirmed.",
                    "expires_at": engine.iso_z(now + timedelta(hours=2)),
                }
            },
            {},
            now,
        )
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["status"], "ABIERTO")
        self.assertEqual(payload["operational_status"], "OPEN_RESTRICTED")
        self.assertEqual(payload["confidence"], "ALTA")


if __name__ == "__main__":
    unittest.main()
