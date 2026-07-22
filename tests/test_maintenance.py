from __future__ import annotations

import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import build_sitemap
import evidence_guard
from maintenance_common import atomic_write_json


HTML_ES = """<!doctype html><html lang='es'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<meta name='description' content='Estado'><link rel='canonical' href='https://estrechoormuz.com/'>
<link rel='alternate' hreflang='es' href='https://estrechoormuz.com/'>
<link rel='alternate' hreflang='en' href='https://estrechoormuz.com/en.html'>
<title>Estado</title></head><body><h1>Estado</h1></body></html>"""
HTML_EN = """<!doctype html><html lang='en'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<meta name='description' content='Status'><link rel='canonical' href='https://estrechoormuz.com/en.html'>
<link rel='alternate' hreflang='es' href='https://estrechoormuz.com/'>
<link rel='alternate' hreflang='en' href='https://estrechoormuz.com/en.html'>
<title>Status</title></head><body><h1>Status</h1></body></html>"""


class MaintenanceTests(unittest.TestCase):
    def test_sitemap_declares_xhtml_namespace_and_nested_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "index.html").write_text(HTML_ES, encoding="utf-8")
            (root / "en.html").write_text(HTML_EN, encoding="utf-8")
            nested = root / "briefs"
            nested.mkdir()
            (nested / "one.html").write_text(
                HTML_ES.replace("https://estrechoormuz.com/", "https://estrechoormuz.com/briefs/one.html"),
                encoding="utf-8",
            )
            pages = build_sitemap.discover_pages(root)
            tree = build_sitemap.build_tree(root, pages)
            self.assertFalse(build_sitemap.validate_tree(tree, root))
            data = build_sitemap.serialize(tree)
            self.assertIn(b'xmlns:xhtml="http://www.w3.org/1999/xhtml"', data)
            self.assertIn(b"briefs/one.html", data)
            ET.fromstring(data)

    def test_bad_open_transition_is_rolled_back_and_source_fixed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            aliases = Path(__file__).resolve().parents[1] / "source_aliases.json"
            previous = {
                "status": "INCIERTO",
                "operational_status": "HIGH_RISK_UNCONFIRMED",
                "confidence": "ALTA",
                "checked_at": "2026-07-20T10:00:00Z",
                "last_change_at": "2026-07-20T10:00:00Z",
                "verification_ok": True,
                "stale": False,
            }
            current = {
                **previous,
                "status": "ABIERTO",
                "operational_status": "OPEN_RESTRICTED",
                "checked_at": "2026-07-20T11:00:00Z",
                "last_change_at": "2026-07-20T11:00:00Z",
                "evidence": [{
                    "signal": "OPEN_OPERATIONAL",
                    "title": "Why can't a president keep the Strait of Hormuz open? - The National Interest",
                    "source_name": "Oman News Agency",
                    "source_url": "https://example.invalid/x",
                    "published_at": "2026-07-20T10:30:00Z",
                    "observed_at": "2026-07-20T11:00:00Z",
                    "tier": 4,
                    "official": True,
                }],
            }
            atomic_write_json(root / "previous.json", previous)
            atomic_write_json(root / "status.json", current)
            payload = json.loads((root / "status.json").read_text(encoding="utf-8"))
            notes = evidence_guard.normalize_sources(payload, aliases)
            supported, _, _ = evidence_guard.support_transition(payload, "ABIERTO")
            self.assertTrue(notes)
            self.assertFalse(supported)
            evidence_guard.safe_previous_classification(payload, previous)
            self.assertEqual(payload["status"], "INCIERTO")
            self.assertEqual(payload["evidence"][0]["source_name"], "The National Interest")
            self.assertFalse(payload["evidence"][0]["official"])

    def test_explicit_official_transit_can_support_open(self):
        payload = {
            "checked_at": "2026-07-20T11:00:00Z",
            "evidence": [{
                "signal": "OPEN_OPERATIONAL",
                "title": "UKMTO confirms commercial traffic is transiting the Strait of Hormuz - UKMTO",
                "source_name": "UKMTO",
                "source_url": "https://example.invalid/official",
                "published_at": "2026-07-20T10:30:00Z",
                "observed_at": "2026-07-20T11:00:00Z",
                "tier": 5,
                "official": True,
            }],
        }
        supported, valid, _ = evidence_guard.support_transition(payload, "ABIERTO")
        self.assertTrue(supported)
        self.assertEqual(len(valid), 1)


if __name__ == "__main__":
    unittest.main()
