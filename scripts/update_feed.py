#!/usr/bin/env python3
"""Update the Nikkei calendar from an explicitly authorized CSV endpoint.

URL is deliberately NOT embedded. Confirm permission for automated retrieval,
processing, and public redistribution before setting GitHub secrets.
"""
import csv
import io
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = os.getenv('AUTHORIZED_NIKKEI_CSV_URL', '').strip()
SOURCE = os.getenv('AUTHORIZED_NIKKEI_SOURCE_NAME', '').strip()
if not URL or not SOURCE:
    print('未設定: 自動取得・保存・公開が許可された配信URLと出典名が必要です')
    sys.exit(0)
if not URL.startswith('https://'):
    sys.exit('HTTPS の配信URLのみ利用できます')


def parse_csv(raw):
    # Nikkei's official Japanese CSV is usually Shift_JIS/CP932 and has a
    # single non-tabular copyright notice following the last data row.
    decoded = None
    for encoding in ('utf-8-sig', 'cp932'):
        try:
            decoded = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            pass
    if decoded is None:
        raise ValueError('CSVの文字コードを判定できません')
    reader = csv.reader(io.StringIO(decoded))
    header = next(reader, None)
    columns = {
        'date': ('データ日付', 'date'),
        'open': ('始値', 'open'),
        'high': ('高値', 'high'),
        'low': ('安値', 'low'),
        'close': ('終値', 'close'),
    }
    if not header:
        raise ValueError('CSVに見出しがありません')
    names = [x.strip().lstrip('\ufeff') for x in header]
    idx = {}
    for key, choices in columns.items():
        found = next((names.index(c) for c in choices if c in names), None)
        if found is None:
            raise ValueError('CSVの列が不足しています: ' + key)
        idx[key] = found
    rows = {}
    for row in reader:
        if not row or all(not item.strip() for item in row):
            continue
        # A single-column rights notice at the end is not a price record.
        if len(row) == 1 and ('著作' in row[0] or '無断' in row[0]):
            continue
        if len(row) != len(names):
            raise ValueError('不正な列数のCSV行が含まれています')
        ds = row[idx['date']].strip().replace('/', '-').replace('.', '-')
        day = date.fromisoformat(ds)
        if day > datetime.now(timezone.utc).date():
            raise ValueError('未来のデータが含まれています')
        values = {k: float(Decimal(row[idx[k]].strip().replace(',', ''))) for k in ('open', 'high', 'low', 'close')}
        if not all(0 < v < 1000000000 for v in values.values()):
            raise ValueError('価格が不正です')
        if values['high'] < max(values.values()) or values['low'] > min(values.values()):
            raise ValueError('四本値の大小関係が不正です')
        key = day.isoformat()
        if key in rows:
            raise ValueError('重複日付: ' + key)
        rows[key] = {'date': key, **values}
    if not rows:
        raise ValueError('有効な日次データがありません')
    return rows


def run():
    req = urllib.request.Request(URL, headers={'User-Agent': 'PersonalNikkeiCalendar/0.5'})
    with urllib.request.urlopen(req, timeout=25) as response:
        raw = response.read(20_000_001)
    if len(raw) > 20_000_000:
        raise ValueError('CSVが20MBを超えています')
    rows = parse_csv(raw)
    path = ROOT / 'data' / 'nikkei.json'
    if path.exists():
        old = json.loads(path.read_text(encoding='utf-8'))
        if old.get('schema') == 1 and isinstance(old.get('rows'), list):
            for record in old['rows']:
                rows.setdefault(record['date'], record)
    combined = [rows[key] for key in sorted(rows)]
    payload = {'schema': 1, 'status': 'ready', 'source': SOURCE,
               'updated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
               'rows': combined}
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    temp.replace(path)
    print('更新成功:', len(combined), '件、最新:', combined[-1]['date'])


if __name__ == '__main__':
    try:
        run()
    except Exception as exc:
        print('更新失敗。既存データは変更していません:', exc, file=sys.stderr)
        sys.exit(1)
