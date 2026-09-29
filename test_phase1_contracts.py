from __future__ import annotations

import json
import unittest
from pathlib import Path

from generate_daily_journal import edition_mode_for, material_score


ROOT = Path(__file__).resolve().parent


class Phase1ContractTests(unittest.TestCase):
    def load(self, name: str):
        return json.loads((ROOT / name).read_text(encoding="utf-8"))

    def test_diary_modes_are_deterministic(self) -> None:
        self.assertEqual(edition_mode_for(0, False), "brief")
        self.assertEqual(edition_mode_for(6, True), "article")
        self.assertEqual(edition_mode_for(8, True), "highlight")

    def test_first_event_baseline_does_not_create_a_false_material_change(self) -> None:
        previous = {"v7_state": "OPEN", "dimensions": {"traffic": "REDUCED"}}
        current = {
            **previous,
            "events": [{
                "event_id": "evt_baseline",
                "verification_status": "CONFIRMED_MULTI_SOURCE",
                "importance": 90,
            }],
            "event_ids": ["evt_baseline"],
        }
        score, reasons = material_score(current, previous, [])
        self.assertEqual(score, 0)
        self.assertIn("Sin cambio de clasificación", reasons[0])

    def test_canonical_assessment_is_v7_and_legacy_is_diagnostic(self) -> None:
        status = self.load("status.json")
        self.assertEqual(status["canonical_assessment"]["engine"], "operational-intelligence-v7")
        self.assertEqual(status["legacy_engine_role"], "internal_diagnostic")
        self.assertEqual(status["canonical_assessment"]["state"], status["operational_intelligence"]["state"])

    def test_health_separates_sources_pipeline_publication_and_operation(self) -> None:
        health = self.load("health.json")
        self.assertIn(health["overall"], {"HEALTHY", "DEGRADED", "STALE", "ERROR"})
        self.assertIn("source_health", health)
        self.assertIn("pipeline_health", health)
        self.assertIn("publication_health", health)
        self.assertIn("operational_assessment", health)
        self.assertEqual(health["legacy_monitor"]["role"], "internal_diagnostic")

    def test_diary_trace_can_reconstruct_the_edition(self) -> None:
        edition = self.load("journal-latest.json")
        required = {
            "editor_engine", "assistant_status", "validator_version",
            "factual_packet_hash", "event_ids", "source_ids", "timestamp",
            "fallback_used", "verification_summary",
        }
        self.assertFalse(required - set(edition))
        self.assertEqual(len(edition["factual_packet_hash"]), 64)
        self.assertIn(edition["edition_mode"], {"brief", "article", "highlight"})

    def test_event_store_is_versioned_and_deduplicated(self) -> None:
        store = self.load("events.json")
        self.assertEqual(store["schema_version"], 1)
        event_ids = [event["event_id"] for event in store["events"]]
        self.assertEqual(len(event_ids), len(set(event_ids)))
        for event in store["events"]:
            self.assertIn("verification_status", event)
            self.assertIn("classification", event)
            self.assertEqual(len(event["source_ids"]), len(set(event["source_ids"])))


if __name__ == "__main__":
    unittest.main()
