"""Freeze reproducible editorial inputs; never update the operational classifier.

Run explicitly for a new draft. Published builds do not regenerate these snapshots.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path


def timestamp(value):
    result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Historical timestamps must include a timezone')
    return result.astimezone(timezone.utc)


def monitor_rows(root):
    output = []
    for filename, model, date_key, state_key in (
        ('history.json', 'legacy', 'at', 'status'),
        ('operational-intelligence-history.json', 'v7', 'generated_at', 'state'),
    ):
        data = json.loads((root / filename).read_text(encoding='utf-8'))
        seen = set()
        for item in data:
            date = timestamp(item[date_key]).isoformat().replace('+00:00', 'Z')
            if date in seen:
                raise ValueError(f'{filename}: duplicate timestamp {date}; resolve before comparing')
            seen.add(date)
            output.append({'model': model, 'at': date, 'state': item[state_key],
                           'confidence': item.get('confidence', 'UNKNOWN'),
                           'traffic_ratio_available': item.get('traffic_ratio_estimate') is not None,
                           'traffic_snapshot_available': item.get('traffic_snapshot') is not None})
    return sorted(output, key=lambda row: (row['model'], row['at']))


def compare_windows(rows, days=21):
    if days <= 0:
        raise ValueError('Window length must be positive')
    selected = [row for row in rows if row['model'] == 'v7']
    if not selected:
        return []
    end = max(timestamp(row['at']) for row in selected).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    results = []
    for start, stop in ((end-timedelta(days=2*days), end-timedelta(days=days)), (end-timedelta(days=days), end)):
        group = [row for row in selected if start <= timestamp(row['at']) < stop]
        results.append({'start_inclusive': start.isoformat(), 'end_exclusive': stop.isoformat(),
                        'calendar_days': days, 'records': len(group),
                        'days_with_retained_record': len({row['at'][:10] for row in group}),
                        'states': dict(Counter(row['state'] for row in group)),
                        'confidence': dict(Counter(row['confidence'] for row in group)),
                        'records_with_traffic_ratio': sum(row['traffic_ratio_available'] for row in group)})
    return results


def build_snapshot(root, output):
    output.mkdir(parents=True, exist_ok=True)
    rows = monitor_rows(root)
    with (output / 'monitor-observations.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    by_model = {}
    for model in ('legacy', 'v7'):
        group = [row for row in rows if row['model'] == model]
        by_model[model] = {'records': len(group), 'first': group[0]['at'], 'last': group[-1]['at'],
                           'states': dict(Counter(row['state'] for row in group))}
    result = {'generated_at': datetime.now(timezone.utc).isoformat(), 'kind': 'unreviewed_editorial_snapshot',
              'models': by_model, 'comparison': compare_windows(rows),
              'hash_normalization': 'UTF-8 input bytes with CRLF normalized to LF; no JSON reformatting',
              'inputs_sha256': {name: hashlib.sha256((root / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                                for name in ('history.json', 'operational-intelligence-history.json')},
              'limitations': ['Retained decisions, not AIS measurements or periodic observations.',
                              'Models have different definitions; do not concatenate them into one traffic series.',
                              'Absence of a retained record is not proof of absent traffic or an outage.',
                              'Record counts cannot estimate closure hours, transit volumes, accuracy or risk.']}
    (output / 'monitor-summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).parent)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_snapshot(args.root, args.output), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
