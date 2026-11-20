"""Coalesce obsolete triggers inside the writer lock; never trust generic health dates."""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID
from canonical_publication import canonical, assessment_id

RECEIPT = 'monitor-update-receipt.json'
WORKFLOW_REF = 'ElPtoWalter/estado-del-estrecho-de-Ormuz/.github/workflows/update-status.yml@refs/heads/main'


def timestamp(value):
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return dt if dt.tzinfo else None
    except ValueError:
        return None


def valid_request(value):
    try:
        return str(UUID(value)) == value and UUID(value).version == 4
    except (ValueError, AttributeError):
        return False


def receipt(root, current, now):
    try:
        value = json.loads((Path(root)/RECEIPT).read_text(encoding='utf-8'))
        checked = timestamp(value.get('validated_at'))
        if (value.get('version') != 1 or value.get('workflow_ref') != WORKFLOW_REF or
                value.get('event') not in {'schedule','workflow_dispatch'} or
                (value.get('request_id') != '' and not valid_request(value.get('request_id'))) or
                not checked or (now-checked).total_seconds() < 0 or
                value.get('assessment_id') != assessment_id(current) or
                value.get('verified_at') != (current.get('verified_at') or current.get('generated_at')) or
                any(not isinstance(value.get(n), int) or isinstance(value[n], bool) or value[n] < 1
                    for n in ('run_id','run_number','run_attempt')) or
                not re.fullmatch(r'[a-f0-9]{40}', value.get('source_checkout',''))):
            return None
        return value
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def decide(root, event, request_id='', expected='', now=None, run_number=0, run_attempt=1):
    now = now or datetime.now(timezone.utc)
    external = bool(request_id or expected)
    if event not in {'schedule','workflow_dispatch'}:
        raise ValueError('Unexpected trigger')
    if external and (event != 'workflow_dispatch' or not valid_request(request_id)):
        raise ValueError('Invalid external request')
    if not external and event == 'workflow_dispatch':
        return True, 'explicit_manual_run'
    try:
        current = canonical(root)
    except (ValueError, OSError, TypeError, AttributeError):
        if external:
            raise
        return True, 'native_run_repairs_invalid_canonical_input'
    done = receipt(root, current, now)
    # Run numbers are ordered within this workflow. A newer trigger always runs;
    # an older delayed trigger can be coalesced with a completed newer trigger.
    if (done and (now-timestamp(done['validated_at'])).total_seconds() < 50*60 and run_number > 0
            and (done['run_number'],done['run_attempt']) >= (run_number,run_attempt)):
        return False, 'trigger_already_superseded_by_validated_monitor_run'
    if external:
        verified = timestamp(current.get('verified_at') or current.get('generated_at'))
        requested = timestamp(expected)
        if not verified or not requested or (verified-now).total_seconds() > 360:
            raise ValueError('Invalid verification timestamp')
        if verified != requested:
            return False, 'snapshot_changed_since_external_check'
        if (now-verified).total_seconds() < 75*60:
            return False, 'verification_recent'
        if done and (done.get('request_id') == request_id or (now-timestamp(done['validated_at'])).total_seconds() < 50*60):
            return False, 'validated_monitor_run_already_covers_recovery'
    return True, 'external_recovery_due' if external else 'native_schedule_due'


def stamp(root, env, now=None):
    now = now or datetime.now(timezone.utc)
    current = canonical(root)
    event, request = env.get('TRIGGER_EVENT'), env.get('RECOVERY_REQUEST_ID','')
    if (event not in {'schedule','workflow_dispatch'} or (request and not valid_request(request))
            or env.get('GITHUB_WORKFLOW_REF') != WORKFLOW_REF):
        raise ValueError('Invalid receipt trigger')
    result = {'version':1, 'workflow_ref':WORKFLOW_REF, 'validated_at':now.isoformat(), 'event':event, 'request_id':request,
              'assessment_id':assessment_id(current), 'verified_at':current.get('verified_at') or current.get('generated_at'),
              'source_checkout':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()}
    for key in ('RUN_ID','RUN_NUMBER','RUN_ATTEMPT'):
        result[key.lower()] = int(env['GITHUB_'+key])
        if result[key.lower()] < 1: raise ValueError('Invalid run identity')
    (Path(root)/RECEIPT).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--stamp',action='store_true')
    p.add_argument('--export-result',type=Path)
    args=p.parse_args()
    if args.stamp:
        stamp('.',os.environ)
    elif args.export_result:
        result=json.loads(Path(RECEIPT).read_text(encoding='utf-8'))
        result['written_commit']=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        args.export_result.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as stream:
                stream.write(f"Validated monitor run: {result['run_id']} / {result['run_attempt']}\n\n"
                             f"Recovery request: {result['request_id'] or 'native/manual'}\n\n"
                             f"Written commit: {result['written_commit']}\n")
    else:
        run,reason=decide('.',os.environ.get('TRIGGER_EVENT',''),os.environ.get('RECOVERY_REQUEST_ID',''),
                          os.environ.get('RECOVERY_EXPECTED',''),run_number=int(os.environ.get('GITHUB_RUN_NUMBER','0')),
                          run_attempt=int(os.environ.get('GITHUB_RUN_ATTEMPT','1')))
        result=f'should_run={str(run).lower()}\nreason={reason}\n'
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as stream: stream.write(result)
        print(result,end='')


if __name__ == '__main__':main()
