"""Offline, reproducible aggregate analysis. Detailed API input stays private.

Usage: python workflow_cadence.py PRIVATE.json --end ISO --minutes 37
The run API does not expose nominal scheduled_for. Lag is an ambiguous proxy.
"""
import argparse
import json
from datetime import datetime, timedelta, timezone
from recovery_preflight import timestamp


def analyse(data, end, minutes, eligible=None):
    start = end - timedelta(days=7)
    eligible_start = max(start, eligible) if eligible else start
    slots = []
    t = eligible_start.replace(minute=0, second=0, microsecond=0)
    while t < end:
        slots.extend(t.replace(minute=m) for m in minutes if eligible_start <= t.replace(minute=m) < end)
        t += timedelta(hours=1)
    all_runs = data['runs']
    if all_runs and len(all_runs) < data['total_count'] and min(timestamp(r['created_at']) for r in all_runs) > start:
        raise ValueError('Pagination incomplete for the seven-day window')
    selected = [r for r in all_runs if eligible_start <= timestamp(r['created_at']) < end and r['event'] == 'schedule']
    times = sorted(timestamp(r['created_at']) for r in selected)
    lags = [min((t - t.replace(minute=m, second=0, microsecond=0)).total_seconds() % 3600 for m in minutes) / 60 for t in times]
    daily = []
    for offset in range(8):
        day = (start + timedelta(days=offset)).date().isoformat()
        a = sum(s.date().isoformat() == day for s in slots)
        b = sum(t.date().isoformat() == day for t in times)
        if a or b:
            daily.append({'utc_date': day, 'nominal_slots': a, 'observed_schedule_runs': b})
    return {'window_start': start.isoformat(), 'window_end': end.isoformat(), 'eligible_from': eligible_start.isoformat(),
            'expected_nominal_slots': len(slots), 'observed_schedule_runs': len(selected),
            'success': sum(r['conclusion'] == 'success' for r in selected),
            'failed': sum(r['conclusion'] == 'failure' for r in selected),
            'cancelled': sum(r['conclusion'] == 'cancelled' for r in selected),
            'other_or_pending': sum(r['conclusion'] not in {'success', 'failure', 'cancelled'} for r in selected),
            'apparently_unrepresented_slots_count_only': max(0, len(slots) - len(selected)),
            'manual_runs_in_window': sum(r['event'] == 'workflow_dispatch' and start <= timestamp(r['created_at']) < end for r in all_runs),
            'maximum_created_gap_hours': max(((b-a).total_seconds()/3600 for a,b in zip(times,times[1:])), default=None),
            'confirmed_original_schedule_delay': None,
            'ambiguous_preceding_slot_proxy_minutes': {'within_5': sum(x <= 5 for x in lags), 'over_5': sum(x > 5 for x in lags), 'over_30': sum(x > 30 for x in lags)},
            'limitations': 'No scheduled_for in API; counts do not identify which original slots were delayed or dropped. Partial UTC boundary days retained.',
            'daily': daily}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input')
    p.add_argument('--end', required=True)
    p.add_argument('--minutes', type=int, nargs='+', required=True)
    p.add_argument('--eligible-from')
    a = p.parse_args()
    if any(x < 0 or x > 59 for x in a.minutes):
        p.error('minutes must be 0..59')
    with open(a.input, encoding='utf-8') as stream:
        data = json.load(stream)
    print(json.dumps(analyse(data, timestamp(a.end), a.minutes, timestamp(a.eligible_from) if a.eligible_from else None), indent=2))
