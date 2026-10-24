"""Reproduce editorial tables from the unchanged frozen CSV; no network or live data.

python reproduce.py --check       # verify committed derived tables
python reproduce.py --write       # regenerate derived tables only
"""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED_INPUT_SHA256_LF = 'de685c60a83b797b63f158052c97e52b6b2b' 'ee5e0898679625edd5664772e092'
FIELDS = ('model', 'at', 'state', 'confidence', 'traffic_ratio_available', 'traffic_snapshot_available')
WINDOWS = (('2026-09-10T00:00:00Z', '2026-10-01T00:00:00Z'),
           ('2026-10-01T00:00:00Z', '2026-10-22T00:00:00Z'))


def utc(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('A historical timestamp needs a timezone')
    return result.astimezone(timezone.utc)


def digest(path):
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def read_rows(root=ROOT):
    if digest(root/'monitor-observations.csv') != EXPECTED_INPUT_SHA256_LF:
        raise ValueError('Frozen input changed; prepare a separate dataset/version before analysing it')
    with (root / 'monitor-observations.csv').open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames) != FIELDS:
            raise ValueError('Unexpected frozen CSV schema')
        rows = list(reader)
    seen = set()
    for row in rows:
        identity = (row['model'], utc(row['at']))
        if identity in seen:
            raise ValueError('Duplicate model/timestamp: cannot silently count twice')
        seen.add(identity)
        if row['model'] not in {'legacy', 'v7'}:
            raise ValueError('Unknown model')
        if any(row[key] not in {'True', 'False'} for key in FIELDS[-2:]):
            raise ValueError('Measurement availability must be explicit')
    return sorted(rows, key=lambda r: (r['model'], utc(r['at'])))


def analyse(rows):
    models = []
    for model in ('legacy', 'v7'):
        group = [r for r in rows if r['model'] == model]
        models.append({'model': model, 'records': len(group), 'first_utc': min(r['at'] for r in group),
                       'last_utc': max(r['at'] for r in group),
                       'states': dict(sorted(Counter(r['state'] for r in group).items())),
                       'confidence': dict(sorted(Counter(r['confidence'] for r in group).items()))})
    v7 = [r for r in rows if r['model'] == 'v7']
    windows = []
    for start, stop in WINDOWS:
        group = [r for r in v7 if utc(start) <= utc(r['at']) < utc(stop)]
        windows.append({'start_inclusive_utc': start, 'end_exclusive_utc': stop,
                        'calendar_days': (utc(stop)-utc(start)).days, 'records': len(group),
                        'days_with_record': len({utc(r['at']).date() for r in group}),
                        'confidence': dict(sorted(Counter(r['confidence'] for r in group).items()))})
    per_day = Counter((r['model'], utc(r['at']).date().isoformat()) for r in rows)
    rank = defaultdict(int)
    dots = []
    for row in rows:
        day = utc(row['at']).date().isoformat()
        rank[(row['model'], day)] += 1
        dots.append({**row, 'day_utc': day, 'stack': rank[(row['model'], day)]})
    return {'models': models, 'windows': windows,
            'v7_high_confidence_dates_utc': [r['at'] for r in v7 if r['confidence'] == 'ALTA'],
            'v7_rows_with_numeric_traffic_ratio': sum(r['traffic_ratio_available'] == 'True' for r in v7),
            'v7_rows_with_traffic_snapshot': sum(r['traffic_snapshot_available'] == 'True' for r in v7),
            'daily_max_records': {m: max(n for (model, day), n in per_day.items() if model == m)
                                  for m in ('legacy', 'v7')},
            'plot_rows': dots}


def csv_text(rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def outputs(root=ROOT):
    rows = read_rows(root)
    result = analyse(rows)
    dots = result.pop('plot_rows')
    result.update({'kind': 'editorial_draft_derived_data', 'timezone': 'UTC',
                   'input_csv_sha256_lf': digest(root/'monitor-observations.csv'),
                   'human_editorial_approval': 'pending',
                   'confidence_meaning': 'Stored model label; not calibrated accuracy or probability',
                   'chart_grain': 'UTC day; stack height only separates same-day records',
                   'input_is_not': ['vessel observations', 'periodic traffic measurements', 'complete execution log']})
    model_rows = [{**{k: v for k, v in r.items() if k not in {'states', 'confidence'}},
                   'states': json.dumps(r['states'], sort_keys=True),
                   'confidence': json.dumps(r['confidence'], sort_keys=True)} for r in result['models']]
    confidence = [{'model': 'v7', 'confidence': label,
                   'records': result['models'][1]['confidence'].get(label, 0),
                   'start_utc': result['models'][1]['first_utc'], 'end_utc': result['models'][1]['last_utc']}
                  for label in ('MEDIA', 'ALTA')]
    windows = [{**{k: v for k, v in r.items() if k != 'confidence'},
                'confidence': json.dumps(r['confidence'], sort_keys=True)} for r in result['windows']]
    daily = [{'model': r['model'], 'timestamp_utc': r['at'], 'day_utc': r['day_utc'], 'stack': r['stack'],
              'state': r['state'], 'confidence': r['confidence']} for r in dots]
    return {'analysis-summary.json': json.dumps(result, ensure_ascii=False, indent=2)+'\n',
            'model-summary.csv': csv_text(model_rows), 'v7-confidence.csv': csv_text(confidence),
            'comparison-windows.csv': csv_text(windows), 'plot-records.csv': csv_text(daily)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write', action='store_true')
    mode.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for name, text in outputs().items():
        path = ROOT / name
        if args.write:
            path.write_text(text, encoding='utf-8', newline='\n')
        elif not path.exists() or path.read_text(encoding='utf-8') != text:
            raise SystemExit(f'Derived data differ: {name}')
    print('Frozen input preserved; derived tables verified.' if args.check else 'Derived tables written; frozen input unchanged.')


if __name__ == '__main__':
    main()
