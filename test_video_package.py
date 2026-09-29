from __future__ import annotations

import copy
import unittest
from datetime import datetime, timezone

from phase2_video.package import build_video_package
from phase2_video.schema import (
    PACKAGE_SCHEMA_VERSION,
    package_content_hash,
    phase2_verification,
)
from phase2_video.validator import validate_package
from test_video_support import event, operational_context, package, source


class VideoPackageTests(unittest.TestCase):
    def test_phase1_mapping_is_explicit_and_conservative(self):
        self.assertEqual(phase2_verification("CONFIRMED_PRIMARY"), "VERIFIED_PRIMARY")
        self.assertEqual(phase2_verification("CONFIRMED_MULTI_SOURCE"), "VERIFIED_MULTISOURCE")
        for status in ("DECLARATION_ONLY", "SINGLE_SOURCE", "UNCONFIRMED", "CONFLICTING"):
            self.assertIsNone(phase2_verification(status))
        with self.assertRaises(ValueError):
            phase2_verification("MADE_UP")

    def test_hash_and_package_id_are_deterministic(self):
        left = package()
        right = package()
        self.assertEqual(left, right)
        self.assertEqual(left["schema_version"], PACKAGE_SCHEMA_VERSION)
        self.assertEqual(left["content_hash"], package_content_hash(left))
        self.assertEqual(left["package_id"], f"video-package:ormuz:2020-01-01:{left['content_hash']}")

    def test_hash_basis_excludes_both_derived_fields_only(self):
        original = package()
        changed_id = copy.deepcopy(original)
        changed_id["package_id"] = "derived-field-does-not-enter-hash"
        changed_hash = copy.deepcopy(original)
        changed_hash["content_hash"] = "0" * 64
        changed_fact = copy.deepcopy(original)
        changed_fact["verified_facts"][0]["text_es"] += " Corrección."
        self.assertEqual(package_content_hash(original), package_content_hash(changed_id))
        self.assertEqual(package_content_hash(original), package_content_hash(changed_hash))
        self.assertNotEqual(package_content_hash(original), package_content_hash(changed_fact))

    def test_new_data_changes_hash(self):
        changed = event(headline="Independent reports confirm a new verified traffic restriction")
        self.assertNotEqual(package()["content_hash"], package(event_row=changed)["content_hash"])

    def test_internal_ids_sources_and_utc_dates_validate(self):
        payload = package()
        report = validate_package(payload, now=datetime(2020, 1, 2, tzinfo=timezone.utc))
        self.assertEqual(report["validation_status"], "PASS", report)
        source_ids = {item["source_id"] for item in payload["sources"]}
        for fact in payload["verified_facts"]:
            self.assertTrue(set(fact["source_ids"]).issubset(source_ids))
            self.assertTrue(fact["observed_at"].endswith("Z"))
        self.assertNotIn("articles", payload)
        self.assertNotIn("description", str(payload))

    def test_future_date_is_rejected(self):
        payload = package()
        payload["generated_at"] = "2099-01-01T00:00:00Z"
        payload["content_hash"] = package_content_hash(payload)
        payload["package_id"] = f"video-package:ormuz:2020-01-01:{payload['content_hash']}"
        report = validate_package(payload, now=datetime(2020, 1, 2, tzinfo=timezone.utc))
        self.assertIn("FUTURE_DATE", report["validation_errors"])

    def test_declarations_are_separate_and_never_verified_facts(self):
        row = event(
            importance=90,
            verification_status="DECLARATION_ONLY",
            classification="DECLARATION",
            headline="The minister says transit will resume soon",
            sources=[source("reuters", "Reuters")],
        )
        payload = package(event_row=row)
        self.assertEqual(payload["verified_facts"], [])
        self.assertEqual(len(payload["statements"]), 1)
        self.assertTrue(payload["statements"][0]["not_verified_as_fact"])
        self.assertFalse(payload["video_recommended"])

    def test_single_source_and_unconfirmed_never_become_facts(self):
        for status in ("SINGLE_SOURCE", "UNCONFIRMED"):
            row = event(verification_status=status, sources=[source("reuters", "Reuters")])
            payload = package(event_row=row)
            self.assertEqual(payload["verified_facts"], [])
            self.assertFalse(payload["video_recommended"])

    def test_same_builder_supports_ormuz_and_gibraltar_adapters(self):
        ormuz = package(site="ormuz")
        gibraltar = package(site="gibraltar")
        self.assertEqual(ormuz["operational_context"]["state"], "OPEN_RESTRICTED")
        self.assertEqual(gibraltar["operational_context"]["state"], "reinforced_watch")
        self.assertEqual(gibraltar["operational_context"]["confidence"], "low")
        self.assertEqual(
            [key for key in ormuz if key != "site"],
            [key for key in gibraltar if key != "site"],
        )

    def test_primary_official_source_maps_to_verified_primary(self):
        official = source("ukmto", "UKMTO", tier=5, official=True)
        row = event(
            verification_status="CONFIRMED_PRIMARY",
            sources=[official],
            operational_impact="MATERIAL",
            importance=90,
        )
        payload = build_video_package(
            site="ormuz",
            event_store={"events": [row]},
            operational_context=operational_context(),
            source_health="healthy",
            comparison=["Material verified change."],
            what_we_dont_know=["Duration remains unknown."],
            watch_next_24h=["Official notices."],
            headlines={"es": "Cambio operativo confirmado", "en": "Confirmed operational change"},
            event_id=row["event_id"],
            generated_at="2020-01-01T11:00:00Z",
            edition_date="2020-01-01",
        )
        self.assertEqual(payload["verified_facts"][0]["verification_status"], "VERIFIED_PRIMARY")
        self.assertEqual(payload["sources"][0]["tier"], "official")
        self.assertEqual(payload["video_type"], "breaking")


if __name__ == "__main__":
    unittest.main()
