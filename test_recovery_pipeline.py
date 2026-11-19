from __future__ import annotations
import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET

import canonical_publication as cp
import canonical_notifications as cn
import generate_daily_brief as brief
import operational_intelligence_v7 as v7
import refresh_publication as refresh
import watch_publication as watch
from commit_generated import allowed

NOW = datetime(2026, 11, 19, 11, tzinfo=timezone.utc)


def assessment(state="OPEN_RESTRICTED", confidence="MEDIA", hour=11):
    family = "UNKNOWN" if state == "UNVERIFIED" else "CLOSED" if "CLOSED" in state else "OPEN"
    a = {"version": 7, "state": state, "family": family, "confidence": confidence,
         "generated_at": f"2026-11-19T{hour:02d}:00:00Z", "label_es": state, "label_en": state,
         "dimensions": {"passage": "CONFIRMED", "traffic": "REDUCED", "access": "RESTRICTED", "risk": "HIGH"},
         "summary_es": "Evaluación fechada", "summary_en": "Dated assessment", "evidence": []}
    return a


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.a = assessment()
        self.save("operational-intelligence.json", self.a)
        self.save("status.json", {"status": "CERRADO", "operational_intelligence": self.a, "verification_ok": True})
        self.save("daily-brief.json", {"assessment_id": cp.assessment_id(self.a), "source_checked_at": self.a["generated_at"]})
        self.save("journal-latest.json", {"generated_at": "2026-11-19T08:00:00Z"})

    def save(self, name, obj):
        (self.root / name).write_text(json.dumps(obj), encoding="utf-8")

    def test_legacy_disagreement_does_not_change_public_canonical(self):
        self.assertEqual(cp.canonical(self.root)["state"], "OPEN_RESTRICTED")
        self.assertFalse(cp.validate(self.root, require_fresh=True, now=NOW))

    def test_mismatched_embedded_v7_fails_closed(self):
        self.save("status.json", {"operational_intelligence": assessment("CLOSED_CONFIRMED")})
        with self.assertRaises(ValueError):
            cp.canonical(self.root)

    def test_brief_mismatch_and_stale_timestamp_are_detected(self):
        self.save("daily-brief.json", {"assessment_id": "bad", "source_checked_at": "2026-11-19T01:00:00Z"})
        self.assertEqual(len(cp.validate(self.root, now=NOW)), 2)
        self.assertTrue(cp.validate(self.root, require_fresh=True, now=NOW + timedelta(hours=4)))

    def test_minimal_public_contract_has_no_internal_evidence_or_addresses(self):
        text = cp.health_xml(self.root, "abc")
        self.assertNotIn("status.json", text)
        self.assertNotIn("legacy", text)
        self.assertNotIn("source_url", text)
        self.assertFalse(watch.check(text, now=NOW))
        self.assertTrue(watch.check(text, now=NOW+timedelta(hours=4)))

    def test_watchdog_does_not_treat_document_generation_as_verification(self):
        self.a["verified_at"] = "2026-11-19T06:00:00Z"
        self.save("operational-intelligence.json", self.a)
        self.save("status.json", {"operational_intelligence": self.a})
        text = cp.health_xml(self.root, "abc")
        self.assertTrue(any("verified_at" in e for e in watch.check(text, now=NOW)))

    def test_carry_forward_cannot_renew_its_twelve_hour_window(self):
        first = assessment(hour=1)
        carried = v7.merge_previous_if_needed(assessment("UNVERIFIED"), first, NOW)
        self.assertTrue(carried["carried_forward"])
        self.assertEqual(carried["verified_at"], "2026-11-19T01:00:00Z")
        expired = v7.merge_previous_if_needed(assessment("UNVERIFIED"), carried, NOW+timedelta(hours=3))
        self.assertEqual(expired["state"], "UNVERIFIED")

    def test_confidence_changes_are_preserved_without_modifying_history(self):
        old = assessment(confidence="BAJA", hour=10)
        self.save("operational-intelligence-history.json", [old])
        v7.update_history(self.root, self.a)
        rows = cp.read(self.root/"operational-intelligence-history.json")
        self.assertEqual(rows, [self.a, old])

    def test_feed_uses_canonical_timeline_and_stable_anchors(self):
        self.save("operational-intelligence-history.json", [self.a])
        text = refresh.feed(self.root)
        self.assertIn("OPEN_RESTRICTED", text)
        self.assertNotIn("CERRADO", text)
        self.assertIn("historial.html#v7-", text)
        ET.fromstring(text)

    def test_brief_uses_v7_and_its_timestamp(self):
        source = cp.read(self.root/"status.json")
        with patch.object(brief, "age_hours", return_value=4):
            result = brief.apply_operational_intelligence(source)
        self.assertEqual(result["status"], "ABIERTO")
        self.assertEqual(result["checked_at"], self.a["generated_at"])
        self.assertTrue(result["stale"])

    def test_frozen_brief_is_bilingual_safe_and_not_indexable(self):
        record = {"date": "2026-11-19", "generated_at": self.a["generated_at"], "source_checked_at": self.a["generated_at"],
                  "operational_label_es": "<closed>", "operational_label_en": "<closed>", "evidence": [
                      {"source_url": "javascript:alert(1)", "title": "unsafe"}]}
        for lang in ("es", "en"):
            doc = brief.render_frozen(record, lang)
            self.assertIn('content="noindex,follow"', doc)
            self.assertIn("&lt;closed&gt;", doc)
            self.assertNotIn("javascript:", doc)
            self.assertIn("briefs-en/2026-11-19.html", doc)

    def test_material_change_scenarios_and_deduplication(self):
        for state in ("OPEN_NORMAL", "CLOSED_CONFIRMED", "OPEN_SEVERELY_RESTRICTED", "UNVERIFIED"):
            with self.subTest(state=state):
                event = cn.enqueue(self.root, self.a, assessment(state, hour=12))
                self.assertIsNotNone(event)
                cn.enqueue(self.root, self.a, assessment(state, hour=12))
        before_count = len(cp.read(self.root/"notification-outbox.json"))
        self.assertEqual(before_count, 4)
        changed = copy.deepcopy(self.a)
        changed["confidence"] = "ALTA"
        self.assertEqual(cn.enqueue(self.root, self.a, changed)["kind"], "confidence")
        changed = copy.deepcopy(self.a)
        changed["dimensions"]["risk"] = "EXTREME"
        self.assertEqual(cn.enqueue(self.root, self.a, changed)["kind"], "dimensions")
        changed = copy.deepcopy(self.a)
        changed["generated_at"] = "2026-11-19T12:00:00Z"
        changed["evidence"] = [{"title": "new article"}]
        self.assertIsNone(cn.enqueue(self.root, self.a, changed))

    def test_no_delivery_before_exact_publication_proof(self):
        cn.enqueue(self.root, assessment(hour=10), assessment("CLOSED_CONFIRMED"))
        calls = []
        with self.assertRaises(ValueError):
            cn.deliver(self.root, "expected", enabled=True, fetcher=lambda url: cp.health_xml(self.root,"different"),
                       sender=lambda *args: calls.append(args))
        self.assertFalse(calls)
        self.assertFalse(cn.deliver(self.root, "x")["enabled"])

    def test_retry_receipts_partial_failure_and_per_channel_deduplication(self):
        before = assessment("CLOSED_CONFIRMED", hour=10)
        event = cn.enqueue(self.root, before, self.a)
        attempts = {"telegram": 0, "ntfy": 0}
        def sender(channel, settings, text):
            attempts[channel] += 1
            if channel == "ntfy" and attempts[channel] <= 3:
                raise OSError("secret URL should never enter ledger")
        with patch.object(cn, "configured_channels", return_value={"telegram": ("x",""), "ntfy":("y","")}):
            args = dict(enabled=True, fetcher=lambda url: cp.health_xml(self.root,"abc"), sender=sender, sleep=lambda _:None)
            self.assertTrue(cn.deliver(self.root,"abc",**args)["errors"])
            self.assertFalse(cn.deliver(self.root,"abc",**args)["errors"])
            self.assertEqual(attempts, {"telegram": 1, "ntfy": 4})
            self.assertFalse(cn.deliver(self.root,"abc",**args)["errors"])
            self.assertEqual(attempts, {"telegram": 1, "ntfy": 4})
        self.assertNotIn("secret URL", (self.root/"notification-delivery.json").read_text())

    def test_superseded_event_is_not_announced(self):
        cn.enqueue(self.root, self.a, assessment("CLOSED_CONFIRMED", hour=10))
        calls = []
        with patch.object(cn, "configured_channels", return_value={"telegram":("x","")}):
            report = cn.deliver(self.root,"abc",enabled=True,fetcher=lambda _:cp.health_xml(self.root,"abc"),
                                sender=lambda *args:calls.append(args))
        self.assertFalse(calls)
        self.assertFalse(report["errors"])

    def test_staging_contract_rejects_code_and_private_accidental_outputs(self):
        for name in ("status.json","daily-brief.json","daily-brief-archive.json","briefs/2026-11-19.html",
                     "briefs-en/2026-11-19.html","daily-brief-feed-en.xml"):
            self.assertTrue(allowed(name,"monitor"),name)
            if name!="status.json":
                self.assertTrue(allowed(name,"journal"),name)
        for name in (".env","config.json","update_status.py","drafts/a.html","briefs/private.json","../secret"):
            self.assertFalse(allowed(name,"monitor"),name)


if __name__ == "__main__":
    unittest.main()
