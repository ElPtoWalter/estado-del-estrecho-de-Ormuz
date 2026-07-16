from __future__ import annotations
import json, os, subprocess, tempfile, unittest
from pathlib import Path
SCRIPT=Path(__file__).with_name("generate_daily_brief.py")

class DailyBriefTests(unittest.TestCase):
    def test_generator_creates_valid_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            status={"status":"INCIERTO","operational_status":"HIGH_RISK_UNCONFIRMED",
              "operational_label_es":"Riesgo elevado, estado no confirmado",
              "operational_label_en":"High risk, status unconfirmed","confidence":"ALTA",
              "checked_at":"2026-07-17T01:00:00Z","verification_ok":True,"stale":False,
              "summary_es":"No existe confirmación operativa suficiente.",
              "summary_en":"There is not enough operational confirmation.",
              "evidence":[{"signal":"RISK_RESTRICTION","title":"Test","source_name":"Official",
                "source_url":"https://example.com/a","published_at":"2026-07-17T00:00:00Z","official":True}]}
            (root/"status.json").write_text(json.dumps(status),encoding="utf-8")
            (root/"history.json").write_text("[]",encoding="utf-8")
            env=dict(os.environ,ORMUZ_ROOT=str(root))
            subprocess.run(["python",str(SCRIPT)],check=True,env=env,capture_output=True,text=True)
            brief=json.loads((root/"daily-brief.json").read_text(encoding="utf-8"))
            social=json.loads((root/"social-drafts.json").read_text(encoding="utf-8"))
            self.assertEqual(brief["status"],"INCIERTO")
            self.assertTrue(brief["verification_ok"])
            self.assertIn("utm_source=x",social["status_es"])
            self.assertTrue((root/"daily-brief-feed.xml").exists())
            self.assertTrue(list((root/"briefs").glob("*.json")))

if __name__=="__main__":
    unittest.main()
