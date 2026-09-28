from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKFLOWS = ROOT / ".github" / "workflows"


class Phase1WorkflowTests(unittest.TestCase):
    def text(self, name: str) -> str:
        return (WORKFLOWS / name).read_text(encoding="utf-8")

    def test_hourly_monitor_is_lightweight_and_has_no_daily_newsroom(self) -> None:
        workflow = self.text("update-status.yml")
        self.assertNotIn("python -m unittest", workflow)
        self.assertNotIn("install_v11.py", workflow)
        self.assertNotIn("generate_daily_journal.py", workflow)
        self.assertIn("operational_intelligence_v7.py", workflow)
        self.assertIn("generate_health.py", workflow)

    def test_daily_newsroom_is_separate_from_ci(self) -> None:
        workflow = self.text("diario-ormuz.yml")
        self.assertIn("generate_daily_journal.py --scheduled", workflow)
        self.assertNotIn("python -m unittest", workflow)

    def test_ci_runs_full_python_and_ui_suites_only_for_code_changes(self) -> None:
        workflow = self.text("phase1-newsroom-ci.yml")
        self.assertIn("python -m unittest discover -v", workflow)
        self.assertIn("node --test test_public_ui.cjs", workflow)
        self.assertIn('paths:', workflow)

    def test_deploy_builds_and_validates_without_repeating_ci(self) -> None:
        workflow = self.text("deploy-public.yml")
        self.assertIn("python build_public_site.py", workflow)
        self.assertIn("python check_public_links.py _site", workflow)
        self.assertNotIn("python -m unittest", workflow)

    def test_no_workflow_prints_ai_secrets(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in WORKFLOWS.glob("*.yml"))
        forbidden = (
            "echo $GEMINI_API_KEY",
            "echo ${GEMINI_API_KEY}",
            "echo $OPENROUTER_API_KEY",
            "echo ${OPENROUTER_API_KEY}",
        )
        for value in forbidden:
            self.assertNotIn(value, combined)


if __name__ == "__main__":
    unittest.main()
