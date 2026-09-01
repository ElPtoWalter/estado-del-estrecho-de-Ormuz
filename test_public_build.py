import unittest
from pathlib import Path
from unittest.mock import patch

import build_public_site as build
import remote_smoke_test as smoke


class PublicBuildTests(unittest.TestCase):
    def setUp(self):
        self.evidence = {"title": "Paso <verificado>", "source_name": "Reuters", "source_url": "https://example.org/story", "published_at": "2026-09-01T06:00:00Z", "signal": "OPEN_OPERATIONAL"}
        self.status = {"status": "ABIERTO", "checked_at": "2026-09-01T07:00:00Z", "verification_ok": True,
                       "evidence": [self.evidence], "evidence_archive": [self.evidence],
                       "diagnostics": {"providers_ok": ["RSS", "Official"], "signals_considered": 4,
                                       "independent_sources": {"open": 2}, "evidence_archive_days": 14}}
        self.payloads = {"status.json": self.status, "history.json": [{"status": "ABIERTO", "at": "2026-09-01T07:00:00Z"}],
                         "daily-brief.json": {"date": "2026-09-01", "confidence_label": {"es": "Media", "en": "Medium"}},
                         "daily-brief-archive.json": [{"date": "2026-08-31", "operational_label_es": "Paso confirmado", "summary_es": "Resumen anterior"}]}
        self.loader = patch.object(build, "load_json", side_effect=lambda name, default: self.payloads.get(name, default))
        self.loader.start()
        self.addCleanup(self.loader.stop)

    def test_archive_is_rendered_deduplicated_and_filterable(self):
        doc = (Path(build.ROOT) / "evidencias.html").read_text()
        result = build.sanitize_html(doc, "evidencias.html")
        self.assertEqual(result.count("data-archive-item"), 1)
        self.assertIn('value="Reuters"', result)
        self.assertNotIn("archive-loading", result)
        self.assertNotIn("Cargando archivo", result)
        self.assertIn("Paso &lt;verificado&gt;", result)
        self.assertIn('id="archiveMetricCount">1<', result)

    def test_history_and_brief_have_no_unresolved_controls(self):
        history = build.sanitize_html('<html lang="es"><body><b id="historyCount">—</b></body></html>', "historial.html")
        self.assertIn('id="historyCount">1<', history)
        brief = build.sanitize_html('<html lang="es"><body><div id="briefLoading">Cargando</div><b id="briefConfidence">—</b><div id="briefArchive"></div></body></html>', "parte-diario.html")
        self.assertIn('hidden="hidden"', brief)
        self.assertIn('id="briefConfidence">Media<', brief)
        self.assertIn("Resumen anterior", brief)

    def test_verification_metrics_are_rendered(self):
        doc = '<html lang="es"><body><b id="verificationProviders">—</b><b id="verificationSignals">—</b><span id="systemStatus">—</span></body></html>'
        result = build.sanitize_html(doc, "index.html")
        self.assertIn('id="verificationProviders">2<', result)
        self.assertIn('id="verificationSignals">4<', result)
        self.assertIn("Seguimiento activo", result)

    def test_nested_english_articles_keep_english_signature(self):
        doc = '<html lang="en"><head><script type="application/ld+json">{"@type":"Article"}</script></head><body><main></main></body></html>'
        result = build.sanitize_html(doc, "2026-09-01.html")
        self.assertIn("Published by", result)
        self.assertNotIn("Equipo editorial", result)

    def test_remote_check_uses_only_public_resources(self):
        paths = []
        def fetch(path, token, timeout):
            paths.append(path)
            if path == "sitemap.xml":
                return b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>', "text/xml"
            return b'<html><body><p data-archive-empty></p><script src="/public-ui.min.js"></script></body></html>', "text/html"
        with patch.object(smoke, "fetch", side_effect=fetch):
            self.assertEqual(smoke.one_attempt(1), [])
        self.assertFalse(any(path.endswith(".json") for path in paths))


if __name__ == "__main__":
    unittest.main()
