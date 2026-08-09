from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import generate_daily_journal as journal


class DailyJournalV8Tests(unittest.TestCase):
    def test_question_headline_is_not_interpreted_as_fact(self):
        item = journal.NewsItem(
            title="Is the Strait of Hormuz open today?",
            source="Reuters",
            url="https://example.com/a",
            published_at="2026-08-10T05:00:00Z",
            tier=5,
            topic="maritime",
            query="x",
            analytical=True,
        )
        self.assertIsNone(journal.interpret_item(item, "es"))
        self.assertIsNone(journal.interpret_item(item, "en"))

    def test_material_score_archives_first_edition(self):
        score, reasons = journal.material_score({"legacy_status": "INCIERTO"}, {}, [])
        self.assertGreaterEqual(score, journal.MATERIAL_THRESHOLD)
        self.assertTrue(reasons)

    def test_material_score_detects_dimension_change(self):
        current = {
            "legacy_status": "INCIERTO",
            "v7_state": "OPEN_RESTRICTED",
            "dimensions": {"traffic": "REDUCED", "risk": "SEVERE"},
        }
        previous = {
            "legacy_status": "INCIERTO",
            "v7_state": "OPEN_RESTRICTED",
            "dimensions": {"traffic": "SEVERELY_REDUCED", "risk": "SEVERE"},
        }
        item = journal.NewsItem(
            title="Strait of Hormuz shipping traffic continues",
            source="Reuters",
            url="https://example.com/b",
            published_at="2026-08-10T05:00:00Z",
            tier=5,
            topic="maritime",
            query="x",
        )
        score, reasons = journal.material_score(current, previous, [item])
        self.assertGreaterEqual(score, 2)
        self.assertTrue(any("dimensiones" in reason.lower() for reason in reasons))

    def test_offline_generator_creates_live_and_archive_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = {
                "status": "INCIERTO",
                "operational_status": "HIGH_RISK_UNCONFIRMED",
                "confidence": "MEDIA",
                "summary_es": "Riesgo elevado.",
                "summary_en": "Elevated risk.",
                "evidence": [
                    {
                        "title": "Strait of Hormuz shipping traffic continues at reduced levels",
                        "source_name": "Reuters",
                        "source_url": "https://example.com/reuters",
                        "published_at": journal.iso_z(journal.utc_now()),
                    },
                    {
                        "title": "JMIC issues new Strait of Hormuz security advisory",
                        "source_name": "JMIC",
                        "source_url": "https://example.com/jmic",
                        "published_at": journal.iso_z(journal.utc_now()),
                    },
                ],
                "operational_intelligence": {
                    "state": "OPEN_SEVERELY_RESTRICTED",
                    "label_es": "ABIERTO · TRÁNSITO MUY RESTRINGIDO",
                    "label_en": "OPEN · SEVERELY RESTRICTED TRANSIT",
                    "summary_es": "Hay paso físico, pero el tráfico está muy reducido.",
                    "summary_en": "Physical passage exists, but traffic is severely reduced.",
                    "confidence": "ALTA",
                    "dimensions": {
                        "passage": "PASSAGE_CONFIRMED",
                        "traffic": "SEVERELY_REDUCED",
                        "access": "RESTRICTED",
                        "risk": "SEVERE",
                    },
                    "dimension_labels_es": {
                        "passage": "Confirmado",
                        "traffic": "Muy reducido",
                        "access": "Restringido",
                        "risk": "Severo",
                    },
                    "dimension_labels_en": {
                        "passage": "Confirmed",
                        "traffic": "Severely reduced",
                        "access": "Restricted",
                        "risk": "Severe",
                    },
                },
            }
            (root / "status.json").write_text(json.dumps(status), encoding="utf-8")
            (root / "index.html").write_text('<html><head></head><body><main><!-- HOME_V11_BRIEF_START --><section></section><!-- HOME_V11_BRIEF_END --></main></body></html>', encoding="utf-8")
            (root / "en.html").write_text('<html lang="en"><head></head><body><main><!-- HOME_V11_BRIEF_START --><section></section><!-- HOME_V11_BRIEF_END --></main></body></html>', encoding="utf-8")

            old_argv = list(__import__("sys").argv)
            try:
                __import__("sys").argv = ["generate_daily_journal.py", "--root", str(root), "--offline", "--force"]
                result = journal.main()
            finally:
                __import__("sys").argv = old_argv
            self.assertEqual(result, 0)
            self.assertTrue((root / "diario.html").exists())
            self.assertTrue((root / "en-diary.html").exists())
            self.assertTrue((root / "diario" / "index.html").exists())
            latest = json.loads((root / "journal-latest.json").read_text(encoding="utf-8"))
            self.assertTrue(latest["material_archive"])
            self.assertIn("JOURNAL_V8_HOME_START", (root / "index.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
