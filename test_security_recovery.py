from pathlib import Path
import re
import tempfile,contextlib,io
import unittest
import build_public_site as public
from editorial_evidence_audit import evidence_record
from editorial_evidence_audit import confidence_errors
from straitwatch_core import SourceRegistry
from straitwatch_core import aggregate_events

class SecurityRecoveryTests(unittest.TestCase):
    def test_hidden_public_contact_is_allowed_but_accidental_dotfiles_block_the_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ("index.html","en.html"):
                (root/name).write_text('<html><head></head><body>Public</body></html>',encoding="utf-8")
            (root/"robots.txt").write_text("User-agent: *\nAllow: /\n",encoding="utf-8")
            (root/"sitemap.xml").write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>',encoding="utf-8")
            (root/"ads.txt").write_bytes((Path(__file__).parent/"ads.txt").read_bytes())
            (root/".well-known").mkdir()
            (root/".well-known/security.txt").write_text("Contact: mailto:contacto@estrechoormuz.com\n",encoding="utf-8")
            public.audit_public_build(root)
            (root/".env").write_text("TEST_SENTINEL=not-a-credential\n",encoding="utf-8")
            captured=io.StringIO()
            with contextlib.redirect_stderr(captured),self.assertRaises(SystemExit):
                public.audit_public_build(root)
            self.assertIn("unapproved hidden path: .env",captured.getvalue())
    def test_article_update_retains_previous_text_without_inventing_a_correction(self):
        registry=SourceRegistry.from_path(Path(__file__).parent/"source-registry.json")
        old={"title":"Tanker crosses Hormuz","source_name":"Reuters","source_url":"https://reuters.com/a",
             "published_at":"2026-11-19T01:00:00Z","signal":"TRANSIT_CONFIRMED"}
        first=aggregate_events([old],registry,generated_at="2026-11-19T02:00:00Z")
        changed={**old,"title":"Tanker crosses Hormuz under restrictions","event_at":"2026-11-18T23:00:00Z"}
        second=aggregate_events([changed],registry,first["events"],generated_at="2026-11-19T03:00:00Z")
        revision=second["events"][0]["article_revisions"][0]
        self.assertEqual(revision["before"]["title"],old["title"])
        self.assertEqual(revision["kind"],"CONTENT_UPDATE")
        self.assertFalse(revision["human_review_recorded"])
        third=aggregate_events([changed],registry,second["events"],generated_at="2026-11-19T04:00:00Z")
        self.assertEqual(third["events"][0]["article_revisions"],second["events"][0]["article_revisions"])
    def test_actions_are_pinned_to_full_commits(self):
        for path in (Path(__file__).parent/".github/workflows").glob("*.yml"):
            for action in re.findall(r"uses:\s+([^\s#]+)",path.read_text(encoding="utf-8")):
                if not action.startswith(("./","docker:")):
                    self.assertRegex(action,r"@[0-9a-f]{40}$",str(path))
    def test_unjustified_high_confidence_blocks_publication_without_reclassification(self):
        a={"state":"OPEN_RESTRICTED","family":"OPEN","confidence":"ALTA","source_counts":{"passage":1,"primary_sources":0}}
        self.assertTrue(confidence_errors(a))
        self.assertEqual(a["confidence"],"ALTA")  # Report, never silently rewrite the assessment.
        a["source_counts"]["passage"]=2
        self.assertFalse(confidence_errors(a))
        self.assertTrue(confidence_errors({"family":"UNKNOWN","confidence":"ALTA"}))
    def test_public_assets_are_explicit_not_arbitrary_xml_or_javascript(self):
        for name in ("private.xml","new-admin.js","assets/admin.js","assets/notes.css","internal-config.json"):
            self.assertFalse(public.copy_asset(Path(name)), name)
        for name in ("radar-map.js","embed.js","styles.css","daily-brief-feed-en.xml",
                     "assets/research/energy-flows-20261025/energy-editorial.css"):
            self.assertTrue(public.copy_asset(Path(name)), name)

    def test_public_assets_do_not_include_code_or_sensitive_extensions(self):
        for name in public.PUBLIC_ROOT_ASSETS:
            self.assertNotIn(Path(name).suffix, public.PRIVATE_EXTENSIONS)

    def test_regional_headline_is_not_assumed_to_be_hormuz_evidence(self):
        registry=SourceRegistry.from_path(Path(__file__).parent/"source-registry.json")
        a=evidence_record({"title":"Forces launch an attack on rebels in Yemen","source":"Reuters",
                           "url":"https://www.reuters.com/world/story","published_at":"2026-11-19T01:00:00Z"},registry)
        self.assertEqual(a["relevance"],"UNESTABLISHED")
        self.assertIn("EVENT_TIME_UNKNOWN",a["flags"])
        self.assertIsNone(a["event_at"])
        self.assertFalse(a["volume_measurement_documented"])

    def test_primary_source_does_not_supply_an_invented_event_time(self):
        registry=SourceRegistry.from_path(Path(__file__).parent/"source-registry.json")
        a=evidence_record({"title":"UKMTO Hormuz vessel notice","source":"UKMTO","url":"https://www.ukmto.org/notice",
                           "published_at":"2026-11-19T01:00:00Z","event_at":"2026-11-18T21:00:00Z"},registry)
        self.assertEqual(a["source_type"],"PRIMARY")
        self.assertEqual(a["relevance"],"DIRECT")
        self.assertEqual(a["event_at"],"2026-11-18T21:00:00Z")
        self.assertFalse(a["event_time_inferred"])

if __name__=="__main__":
    unittest.main()
