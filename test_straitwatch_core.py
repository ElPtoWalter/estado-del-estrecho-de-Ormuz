from __future__ import annotations

import unittest
from pathlib import Path

from straitwatch_core import SourceRegistry, aggregate_events, deduplicate_articles


ROOT = Path(__file__).resolve().parent
REGISTRY = SourceRegistry.from_path(ROOT / "source-registry.json")


def article(
    title: str,
    source: str,
    url: str,
    *,
    published_at: str = "2026-09-28T08:00:00Z",
    signal: str = "",
    topic: str = "maritime",
) -> dict:
    return {
        "title": title,
        "source_name": source,
        "source_url": url,
        "published_at": published_at,
        "signal": signal,
        "topic": topic,
    }


class SourceRegistryTests(unittest.TestCase):
    def test_aliases_resolve_to_one_identity(self) -> None:
        ids = {
            REGISTRY.resolve(name).source_id
            for name in ("Reuters", "Reuters.com", "reuters.com")
        }
        self.assertEqual(ids, {"reuters"})
        self.assertEqual(REGISTRY.resolve("AlJazeera.com").source_id, "aljazeera")
        self.assertEqual(REGISTRY.resolve("TradeWinds News").source_id, "tradewinds")

    def test_domain_resolution_precedes_ambiguous_names(self) -> None:
        source = REGISTRY.resolve("News desk", "https://www.reuters.com/world/example")
        self.assertEqual(source.source_id, "reuters")
        self.assertEqual(source.tier, 4)


class DeduplicationTests(unittest.TestCase):
    def test_same_url_and_publisher_variant_is_one_article(self) -> None:
        rows = [
            article("Traffic continues through Hormuz - Reuters", "Reuters", "https://news.example/item?utm_source=a"),
            article("Traffic continues through Hormuz - reuters.com", "Reuters.com", "https://news.example/item?utm_source=b"),
        ]
        result = deduplicate_articles(rows, REGISTRY)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source_id"], "reuters")

    def test_near_identical_titles_from_same_source_are_one_article(self) -> None:
        rows = [
            article("Three vessels transit the Strait of Hormuz", "Reuters", "https://example.com/a"),
            article("Three vessels transited Strait of Hormuz", "reuters.com", "https://example.com/b"),
        ]
        self.assertEqual(len(deduplicate_articles(rows, REGISTRY)), 1)


class EventTests(unittest.TestCase):
    def test_same_event_keeps_multiple_independent_sources(self) -> None:
        rows = [
            article("Three vessels transit the Strait of Hormuz", "Reuters", "https://reuters.com/a", signal="TRANSIT_CONFIRMED"),
            article("Three ships cross Hormuz despite restrictions", "BBC", "https://bbc.com/b", signal="TRANSIT_CONFIRMED"),
        ]
        store = aggregate_events(rows, REGISTRY, generated_at="2026-09-28T09:00:00Z")
        self.assertEqual(store["event_count"], 1)
        event = store["events"][0]
        self.assertEqual(set(event["source_ids"]), {"reuters", "bbc"})
        self.assertEqual(event["verification_status"], "CONFIRMED_MULTI_SOURCE")
        self.assertTrue(event["operational_eligible"])

    def test_official_direct_signal_is_primary_confirmation(self) -> None:
        rows = [article(
            "UKMTO confirms vessels are transiting Hormuz",
            "UKMTO",
            "https://ukmto.org/notice/1",
            signal="TRANSIT_CONFIRMED",
        )]
        event = aggregate_events(rows, REGISTRY)["events"][0]
        self.assertEqual(event["verification_status"], "CONFIRMED_PRIMARY")
        self.assertTrue(event["operational_eligible"])

    def test_single_reliable_source_remains_single_source(self) -> None:
        rows = [article(
            "Three vessels transit the Strait of Hormuz",
            "Reuters",
            "https://reuters.com/a",
            signal="TRANSIT_CONFIRMED",
        )]
        event = aggregate_events(rows, REGISTRY)["events"][0]
        self.assertEqual(event["verification_status"], "SINGLE_SOURCE")
        self.assertFalse(event["operational_eligible"])

    def test_declaration_is_not_an_operational_fact(self) -> None:
        rows = [article(
            "Iran says it has closed the Strait of Hormuz",
            "Reuters",
            "https://reuters.com/declaration",
            signal="FORMAL_CLOSURE_CLAIM",
        )]
        event = aggregate_events(rows, REGISTRY)["events"][0]
        self.assertEqual(event["classification"], "DECLARATION")
        self.assertEqual(event["verification_status"], "DECLARATION_ONLY")
        self.assertFalse(event["operational_eligible"])

    def test_conflicting_operational_claims_are_flagged(self) -> None:
        rows = [
            article("Traffic halted through Hormuz", "Reuters", "https://reuters.com/closed", signal="CLOSURE_EFFECTIVE"),
            article("Traffic continues through Hormuz", "BBC", "https://bbc.com/open", signal="TRANSIT_CONFIRMED"),
        ]
        event = aggregate_events(rows, REGISTRY)["events"][0]
        self.assertEqual(event["verification_status"], "CONFLICTING")
        self.assertFalse(event["operational_eligible"])

    def test_event_id_is_reused_when_an_independent_source_arrives(self) -> None:
        first = aggregate_events([
            article("Three vessels transit the Strait of Hormuz", "Reuters", "https://reuters.com/a", signal="TRANSIT_CONFIRMED"),
        ], REGISTRY, generated_at="2026-09-28T09:00:00Z")
        updated = aggregate_events([
            article("Three vessels transit the Strait of Hormuz", "Reuters", "https://reuters.com/a", signal="TRANSIT_CONFIRMED"),
            article("Three ships cross Hormuz despite restrictions", "BBC", "https://bbc.com/b", signal="TRANSIT_CONFIRMED"),
        ], REGISTRY, first["events"], generated_at="2026-09-28T10:00:00Z")
        self.assertEqual(first["events"][0]["event_id"], updated["events"][0]["event_id"])

    def test_tier_one_hint_cannot_be_operationally_eligible(self) -> None:
        rows = [article(
            "Traffic halted through Hormuz",
            "Unknown blog",
            "https://unknown.invalid/claim",
            signal="CLOSURE_EFFECTIVE",
        )]
        event = aggregate_events(rows, REGISTRY)["events"][0]
        self.assertEqual(event["verification_status"], "UNCONFIRMED")
        self.assertFalse(event["operational_eligible"])


if __name__ == "__main__":
    unittest.main()
