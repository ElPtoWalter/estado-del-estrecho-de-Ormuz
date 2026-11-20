import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from recovery_preflight import decide
from publication_needed import needed
from workflow_cadence import analyse
import canonical_publication as cp
import generate_daily_brief as brief
import generate_daily_journal as journal
from test_recovery_pipeline import assessment

NOW = datetime(2026, 11, 19, 13, tzinfo=timezone.utc)
REQUEST = '12345678-1234-1234-1234-123456789abc'


class ExternalRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.a = assessment(hour=11)
        self.save('operational-intelligence.json', self.a)
        self.save('status.json', {'status': 'ABIERTO', 'operational_intelligence': self.a, 'verification_ok': True})
        self.save('health.json', {'generated_at': '2026-11-19T11:00:00Z'})

    def save(self, name, value):
        (self.root/name).write_text(json.dumps(value), encoding='utf-8')

    def gate(self, event='workflow_dispatch', request=REQUEST, expected='2026-11-19T11:00:00Z'):
        return decide(self.root,event,request,expected,NOW)

    def test_external_due_manual_always_and_native_due(self):
        self.assertTrue(self.gate()[0])
        self.assertTrue(self.gate(request='',expected='')[0])
        self.assertTrue(self.gate(event='schedule',request='',expected='')[0])

    def test_native_wins_external_reads_latest_main_inside_lock(self):
        self.a['generated_at']='2026-11-19T12:59:00Z'
        self.save('operational-intelligence.json',self.a)
        self.save('status.json',{'operational_intelligence':self.a})
        self.assertEqual(self.gate(),(False,'snapshot_changed_since_external_check'))

    def test_external_wins_native_skips_recent_technical_check(self):
        self.save('health.json',{'generated_at':'2026-11-19T12:59:00Z'})
        self.assertFalse(self.gate(event='schedule',request='',expected='')[0])
        self.assertFalse(self.gate()[0])
        self.assertTrue(self.gate(request='',expected='')[0])

    def test_recent_check_with_carried_forward_old_verification_also_deduplicates(self):
        self.save('health.json',{'generated_at':'2026-11-19T12:15:00Z'})
        self.assertEqual(self.gate(),(False,'another_technical_update_already_completed'))

    def test_invalid_inputs_and_future_technical_heartbeat_fail_closed(self):
        for args in [dict(request='bad'),dict(event='schedule'),dict(expected='invalid')]:
            with self.assertRaises(ValueError):self.gate(**args)
        self.save('health.json',{'generated_at':'2099-01-01T00:00:00Z'})
        with self.assertRaises(ValueError):self.gate()

    def test_gate_does_not_write_any_data(self):
        before={p.name:p.read_bytes() for p in self.root.iterdir()}
        self.gate()
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir()})

    def test_only_exact_commit_plus_six_html_skips_pages(self):
        commit='b'*40
        def fetch(url):
            return cp.health_xml(self.root,commit) if url.endswith('.xml') else f'<meta name="ormuz-assessment" content="{cp.assessment_id(self.a)}">'
        self.save('daily-brief.json',{'assessment_id':cp.assessment_id(self.a),'source_checked_at':self.a['generated_at']})
        self.assertFalse(needed(self.root,commit,fetch))
        self.assertTrue(needed(self.root,'c'*40,fetch))
        self.assertTrue(needed(self.root,commit,lambda url: b'invalid'))
        self.assertTrue(needed(self.root,commit,lambda url: fetch(url) if url.endswith('.xml') else 'old HTML'))

    def test_real_brief_and_skipped_journal_never_reverify_v7(self):
        protected=['status.json','operational-intelligence.json','health.json']
        before={n:(self.root/n).read_bytes() for n in protected}
        # Actual generators, isolated files and an explicit clock, no provider requests.
        with patch.object(brief,'ROOT',self.root), patch.object(brief,'datetime') as clock:
            clock.now.return_value=NOW+timedelta(days=1)
            self.assertEqual(brief.main(),0)
        self.save('journal-state.json',{'last_date':'2026-11-20'})
        with patch('sys.argv',['generate_daily_journal.py','--root',str(self.root),'--scheduled']), patch.object(journal,'utc_now',return_value=NOW+timedelta(days=1)):
            self.assertEqual(journal.main(),0)
        self.assertEqual(before,{n:(self.root/n).read_bytes() for n in protected})
        result=json.loads((self.root/'daily-brief.json').read_text(encoding='utf-8'))
        self.assertEqual(result['source_checked_at'],'2026-11-19T11:00:00Z')
        self.assertNotEqual(result['generated_at'],result['source_checked_at'])

    def test_cadence_partial_eligibility_and_delay_uncertainty(self):
        runs={'total_count':1,'runs':[{'event':'schedule','created_at':'2026-11-19T12:54:00Z','conclusion':'success'}]}
        report=analyse(runs,NOW,[37])
        self.assertEqual(report['expected_nominal_slots'],168)
        self.assertEqual(report['apparently_unrepresented_slots_count_only'],167)
        self.assertIsNone(report['confirmed_original_schedule_delay'])
        recent=analyse({'total_count':0,'runs':[]},NOW,[13,43],NOW-timedelta(hours=1))
        self.assertEqual(recent['expected_nominal_slots'],2)
        with self.assertRaises(ValueError):analyse({**runs,'total_count':1000},NOW,[37])

    def test_workflow_writer_lock_gate_and_publication_condition_remain_present(self):
        root=Path(__file__).parent
        update=(root/'.github/workflows/update-status.yml').read_text(encoding='utf-8')
        self.assertIn('group: ormuz-content-update',update)
        self.assertIn('cancel-in-progress: false',update)
        self.assertLess(update.index('ref: main'),update.index('run: python recovery_preflight.py'))
        self.assertIn('RECOVERY_REQUEST_ID: ${{ inputs.recovery_request_id }}',update)
        deploy=(root/'.github/workflows/deploy-public.yml').read_text(encoding='utf-8')
        self.assertIn("if: needs.build.outputs.publish == 'true'",deploy)

    def test_external_code_config_and_docs_never_qualify_as_public_assets(self):
        from build_public_site import copy_asset, public_html_path
        for name in ['external-watch/snapshot.mjs','external-watch/wrangler.toml',
                     'external-watch/github.mjs','external-watch/.dev.vars','recovery_preflight.py',
                     'docs/ACTIVACION_VIGILANCIA_EXTERNA.md']:
            self.assertFalse(copy_asset(Path(name)),name)
        self.assertFalse(public_html_path(Path('external-watch/diagnostic.html')))


if __name__=='__main__':unittest.main()
