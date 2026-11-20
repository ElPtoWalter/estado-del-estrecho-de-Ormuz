"""Read-only gate, executed after checkout(main) inside the shared writer lock."""
from __future__ import annotations
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from canonical_publication import canonical


def timestamp(value):
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return dt if dt.tzinfo else None
    except ValueError:
        return None


def decide(root, event, request_id='', expected='', now=None):
    now = now or datetime.now(timezone.utc)
    external = bool(request_id or expected)
    if external and (event != 'workflow_dispatch' or not re.fullmatch(r'[a-f0-9-]{36}', request_id)):
        raise ValueError('Invalid external request')
    if not external and event == 'workflow_dispatch':
        return True, 'explicit_manual_run'
    try:
        health = json.loads((Path(root) / 'health.json').read_text(encoding='utf-8'))
        checked = timestamp(health.get('generated_at'))
    except (OSError, ValueError):
        checked = None
    if checked and (checked - now).total_seconds() > 360:
        raise ValueError('Future technical heartbeat; operator review required')
    if external:
        current = canonical(root)
        verified = timestamp(current.get('verified_at') or current.get('generated_at'))
        requested = timestamp(expected)
        if not verified or not requested or (verified - now).total_seconds() > 360:
            raise ValueError('Invalid verification timestamp')
        if verified != requested:
            return False, 'snapshot_changed_since_external_check'
        if (now - verified).total_seconds() < 75 * 60:
            return False, 'verification_recent'
    if checked and 0 <= (now - checked).total_seconds() < 50 * 60:
        return False, 'another_technical_update_already_completed'
    return True, 'external_recovery_due' if external else 'native_schedule_due'


def main():
    run, reason = decide('.', os.environ.get('TRIGGER_EVENT', ''),
                         os.environ.get('RECOVERY_REQUEST_ID', ''), os.environ.get('RECOVERY_EXPECTED', ''))
    result = f'should_run={str(run).lower()}\nreason={reason}\n'
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as stream:
            stream.write(result)
    print(result, end='')


if __name__ == '__main__':
    main()
