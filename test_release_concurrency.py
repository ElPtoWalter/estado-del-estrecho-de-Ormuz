"""Release races use fake transports and local Git only; no real messages."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import canonical_notifications as cn
import canonical_publication as cp
import generate_daily_journal as journal
import watch_publication as watch
from notification_repository import revision_guard
from test_recovery_pipeline import NOW, assessment


class ReleaseRaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.a = assessment()
        for name, data in {
            "status.json": {"operational_intelligence": self.a},
            "operational-intelligence.json": self.a,
            "daily-brief.json": {"assessment_id": cp.assessment_id(self.a), "source_checked_at": self.a["generated_at"]},
            "journal-latest.json": {"date": "2026-11-19", "generated_at": "2026-11-19T08:00:00Z"},
        }.items():
            (self.root/name).write_text(json.dumps(data), encoding="utf-8")
        cn.enqueue(self.root, assessment("CLOSED_CONFIRMED", hour=10), self.a)

    def fetch(self, url):
        if url.endswith("publication-health.xml"):
            return cp.health_xml(self.root, "built")
        return '<meta name="ormuz-assessment" content="' + cp.assessment_id(self.a) + '">'

    def test_release_changes_during_html_reads_fail_closed(self):
        manifests = 0
        def fetch(url):
            nonlocal manifests
            if url.endswith("publication-health.xml"):
                manifests += 1
                return cp.health_xml(self.root, "built" if manifests == 1 else "next")
            return self.fetch(url)
        with self.assertRaises(ValueError):
            cn.verify_release(fetch, self.a, "built")

    def test_new_deployment_after_provider_error_blocks_retry(self):
        changed = False
        calls = []
        def sender(*args):
            nonlocal changed
            calls.append(args)
            changed = True
            raise OSError("private provider URL")
        def fetch(url):
            if changed and url.endswith("publication-health.xml"):
                return cp.health_xml(self.root, "next")
            return self.fetch(url)
        with patch.object(cn, "configured_channels", return_value={"telegram": ("fake", "")}):
            with self.assertRaises(ValueError):
                cn.deliver(self.root, "built", enabled=True, fetcher=fetch, sender=sender, sleep=lambda _: None)
        self.assertEqual(len(calls), 1)
        self.assertNotIn("private provider", (self.root/"notification-delivery.json").read_text())

    def test_main_advance_between_channels_preserves_first_receipt_and_stops_second(self):
        changed = False
        calls = []
        def guard():
            if changed:
                raise ValueError("Main advanced")
        def sender(channel, *args):
            nonlocal changed
            calls.append(channel)
            changed = True
        with patch.object(cn, "configured_channels", return_value={"telegram": ("fake", ""), "ntfy": ("fake", "")}):
            with self.assertRaises(ValueError):
                cn.deliver(self.root, "built", enabled=True, fetcher=self.fetch, sender=sender, revision_check=guard)
        self.assertEqual(calls, ["telegram"])
        ledger = json.loads((self.root/"notification-delivery.json").read_text())
        row = next(iter(ledger.values()))
        self.assertTrue(row["channels"]["telegram"]["delivered"])
        self.assertFalse(row["channels"].get("ntfy", {}).get("delivered"))

    def test_main_advance_after_provider_failure_blocks_even_same_release_retry(self):
        changed = False
        calls = []
        def guard():
            if changed:
                raise ValueError("Main advanced")
        def sender(*args):
            nonlocal changed
            calls.append(args)
            changed = True
            raise OSError("unacknowledged")
        with patch.object(cn, "configured_channels", return_value={"telegram": ("fake", "")}):
            with self.assertRaises(ValueError):
                cn.deliver(self.root, "built", enabled=True, fetcher=self.fetch, sender=sender,
                           revision_check=guard, sleep=lambda _: None)
        self.assertEqual(len(calls), 1)

    def test_old_edition_with_fresh_newsroom_check_is_not_technical_failure(self):
        latest = {"generated_at": "2026-11-01T08:00:00Z"}
        (self.root/"journal-latest.json").write_text(json.dumps(latest))
        for outcome in ("not_due", "edition_already_exists", "published"):
            (self.root/"journal-check.json").write_text(json.dumps({"checked_at": "2026-11-19T10:00:00Z", "outcome": outcome}))
            result = watch.diagnose(cp.health_xml(self.root, "built"), now=NOW)
            self.assertFalse(result["errors"])
            self.assertTrue(result["warnings"])

    def test_recent_edition_does_not_hide_stale_newsroom_check(self):
        (self.root/"journal-check.json").write_text(json.dumps({"checked_at": "2026-11-15T10:00:00Z", "outcome": "published"}))
        errors = watch.check(cp.health_xml(self.root, "built"), now=NOW)
        self.assertTrue(any("journal_checked_at" in e for e in errors))

    def test_unknown_heartbeat_is_explicit_not_invented_from_edition(self):
        result = watch.diagnose(cp.health_xml(self.root, "built"), now=NOW)
        self.assertFalse(result["errors"])
        self.assertTrue(any("unknown" in w for w in result["warnings"]))

    def test_scheduled_idempotence_records_real_check_without_rewriting_edition(self):
        (self.root/"journal-state.json").write_text(json.dumps({"last_date": "2026-11-19"}))
        for name in ("diario.html", "en-diary.html", "diario-feed.xml", "diary-feed.xml"):
            (self.root/name).write_text("unchanged edition")
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        with patch.object(sys, "argv", ["generate_daily_journal.py", "--root", str(self.root), "--scheduled"]), patch.object(journal, "utc_now", return_value=NOW):
            self.assertEqual(journal.main(), 0)
        self.assertTrue(all((self.root/n).read_bytes() == raw for n, raw in before.items()))
        check = json.loads((self.root/"journal-check.json").read_text())
        self.assertEqual(check["outcome"], "edition_already_exists")
        self.assertEqual(check["checked_at"], "2026-11-19T11:00:00Z")


class LocalGitDeliveryTests(unittest.TestCase):
    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.repo, text=True, stderr=subprocess.DEVNULL).strip()

    def commit(self, name, content):
        (self.repo/name).write_text(content)
        self.git("add", "--", name)
        self.git("commit", "-m", "Synthetic delivery regression fixture")
        return self.git("rev-parse", "HEAD")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.repo = root/"checkout"
        self.repo.mkdir()
        subprocess.run(["git", "init", "--bare", str(root/"remote.git")], check=True, capture_output=True)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "automated-test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("remote", "add", "origin", str(root/"remote.git"))
        self.built = self.commit("monitor.txt", "initial snapshot")
        self.git("push", "origin", "main")

    def test_exact_revision_and_receipt_only_descendants_are_allowed(self):
        self.assertEqual(revision_guard(self.repo, self.built), self.built)
        receipt = self.commit("notification-delivery.json", '{"acknowledged":true}')
        self.git("push", "origin", "main")
        self.assertEqual(revision_guard(self.repo, self.built), receipt)

    def test_remote_main_ahead_of_checkout_prevents_delivery(self):
        advanced = self.commit("monitor.txt", "next snapshot")
        self.git("push", "origin", "main")
        self.git("checkout", "--detach", self.built)
        with self.assertRaisesRegex(ValueError, "advanced"):
            revision_guard(self.repo, self.built)
        self.assertNotEqual(advanced, self.built)

    def test_unpublished_publication_change_even_if_reverted_is_not_receipt_only(self):
        self.commit("monitor.txt", "intermediate change")
        self.commit("monitor.txt", "initial snapshot")
        self.git("push", "origin", "main")
        with self.assertRaisesRegex(ValueError, "publication changes"):
            revision_guard(self.repo, self.built)

    def test_receipt_push_cannot_overwrite_a_concurrent_main_update(self):
        receipt = self.commit("notification-delivery.json", '{"acknowledged":true}')
        self.git("checkout", "--detach", self.built)
        advanced = self.commit("monitor.txt", "concurrent production update")
        self.git("push", "origin", "HEAD:refs/heads/main")
        self.git("checkout", "--detach", receipt)
        result = subprocess.run(["git", "push", "origin", "HEAD:refs/heads/main"], cwd=self.repo, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git("ls-remote", "origin", "refs/heads/main").split()[0], advanced)


class ReleaseWorkflowTests(unittest.TestCase):
    def test_workflows_serialize_delivery_and_do_not_redeploy_receipts(self):
        text = (Path(__file__).parent/".github/workflows/deploy-public.yml").read_text()
        self.assertIn("paths-ignore:\n      - notification-delivery.json", text)
        self.assertNotIn("cancel-in-progress: true", text)
        self.assertIn("needs: [build, deploy]", text)
        self.assertIn("group: ormuz-content-update", text)
        self.assertIn("CANONICAL_NOTIFICATIONS_ENABLED == 'true'", text)
        self.assertIn("ref: ${{ needs.build.outputs.revision }}", text)


if __name__ == "__main__":
    unittest.main()
