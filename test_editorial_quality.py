import csv
import json
import tempfile
import unittest
from pathlib import Path
import generate_daily_journal as journal
import monitor_report
from publication_quality import apply_policy


class EditorialQualityTests(unittest.TestCase):
    def item(self, title, source="Reuters", url="https://example.org/news"):
        return journal.NewsItem(title, source, url, journal.iso_z(journal.utc_now()), 5, journal.topic_for(title), "")

    def test_attack_is_not_diplomacy(self):
        self.assertEqual(journal.topic_for("US launches new strikes on Iran as Tehran hits back in widening conflict"), "security")
        self.assertEqual(journal.topic_for("Iran Tehran Washington"), "other")
        self.assertEqual(journal.topic_for("Iran and Washington resume talks"), "diplomacy")

    def test_oil_price_subject_is_not_a_transit_measure(self):
        self.assertEqual(journal.topic_for("Oil Extends Gain as Strikes Raise Supply Concerns"), "energy")
        self.assertNotIn("nuevas señales de tránsito", journal.interpret_item(self.item("Oil traffic falls"), "es"))

    def test_same_url_with_updated_title_is_not_new(self):
        a = self.item("Original headline", url="https://example.org/a?utm_source=x")
        b = self.item("Updated headline", url="https://example.org/a?utm_source=y")
        self.assertEqual(journal.article_key(a), journal.article_key(b))
        self.assertEqual(len(journal.dedupe_news([a, b])), 1)

    def test_volume_alone_does_not_create_archive(self):
        fp = {"legacy_status": "INCIERTO", "v7_state": "UNKNOWN", "dimensions": {}}
        items = [self.item("Oil prices rise", "Reuters"), self.item("Iran resumes talks", "BBC"), self.item("Shipping traffic update", "AP")]
        self.assertLess(journal.material_score(fp, fp, items)[0], journal.MATERIAL_THRESHOLD)

    def test_section_names_only_the_sources_of_its_two_links(self):
        items = [self.item("Missile attack", source, f"https://example.org/{source}") for source in ("Bloomberg", "BBC", "Al Jazeera")]
        text = journal.section_paragraph("security", items, "es")
        self.assertIn("Bloomberg, BBC", text)
        self.assertNotIn("Al Jazeera", text)
        self.assertNotIn("conversaciones", text)

    def test_digest_is_unmonetized_and_noindex_without_removing_content(self):
        page = '<html><head><meta name="robots" content="index,follow"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"></script></head><body><main><h1>Archivo</h1></main></body></html>'
        result = apply_policy(page, "diario/2026-08-31.html")
        self.assertIn("noindex,follow", result)
        self.assertNotIn("adsbygoogle", result)
        self.assertIn("<h1>Archivo</h1>", result)
        self.assertIn("data-editorial-disclosure", result)

    def test_report_csv_and_table_use_same_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [{"at": f"2026-09-0{i}T00:00:00Z", "status": state, "confidence": "BAJA"} for i, state in enumerate(("INCIERTO", "INCIERTO", "ABIERTO"), 1)]
            (root / "history.json").write_text(json.dumps(rows))
            (root / "status.json").write_text('{"checked_at":"2026-09-03T01:00:00Z"}')
            monitor_report.build_reports(root)
            with (root / "monitor-records.csv").open() as stream:
                exported = list(csv.DictReader(stream))
            self.assertEqual(len(exported), 3)
            self.assertEqual(set(exported[0]), set(monitor_report.FIELDS))
            page = (root / "datos-propios-monitor-ormuz.html").read_text()
            self.assertIn("66.7%", page)
            self.assertIn("1 cambios", page)
            self.assertIn("1 pares", page)
            self.assertIn("monitor-records.csv", page)
