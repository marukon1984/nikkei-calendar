#!/usr/bin/env python3
"""Read an expressly authorized CSV endpoint and update a validated public JSON feed.
No source URL is embedded, searched or scraped. Configuration via secrets only.
"""
import csv,io,json,os,sys,urllib.request
from datetime import date,datetime,timezone
from pathlib import Path
from decimal import Decimal,InvalidOperation

ROOT=Path(__file__).resolve().parents[1]
URL=os.environ.get('AUTHORIZED_NIKKEI_CSV_URL','').strip()
SOURCE=os.environ.get('AUTHORIZED_NIKKEI_SOURCE_NAME','').strip()
if not URL or not SOURCE:
    print('未設定: 配信元URLと出典名を設定するまで取得しません')
    sys.exit(0)
if not URL.startswith('https://'):
    sys.exit('HTTPS の配信URLのみ許可します')
try:
    req=urllib.request.Request(URL,headers={'User-Agent':'PersonalNikkeiCalendar/0.4 (authorized CSV feed)'})
    with urllib.request.urlopen(req,timeout=25) as resp:
        raw=resp.read(20_000_001)
    if len(raw)>20_000_000:raise ValueError('ファイルサイズが20MBを超えました')
    text=raw.decode('utf-8-sig')
    reader=csv.DictReader(io.StringIO(text))
    required={'date','open','high','low','close'}
    if not reader.fieldnames or not required.issubset({s.strip() for s in reader.fieldnames}):raise ValueError('CSVの列が不足: date,open,high,low,close')
    rows={}
    for r in reader:
        date_key=r['date'].strip()
        parsed=date.fromisoformat(date_key)
        if parsed.isoformat()!=date_key or parsed>datetime.now(timezone.utc).date():raise ValueError('日付が不正: '+date_key)
        p={k:float(Decimal(r[k].strip())) for k in ('open','high','low','close')}
        if not all(0<v<1_000_000_000 for v in p.values()):raise ValueError('価格が不正')
        if p['high']<max(p.values()) or p['low']>min(p.values()):raise ValueError('OHLCが不正')
        if date_key in rows:raise ValueError('同一ファイル内で日付重複: '+date_key)
        rows[date_key]={'date':date_key,**p}
    if not rows:raise ValueError('データが空です')
    destination=ROOT/'data'/'nikkei.json'
    # Keep previously verified history. A truncated daily feed never deletes it.
    if destination.exists():
        current=json.loads(destination.read_text())
        if current.get('schema')==1 and isinstance(current.get('rows'),list):
            for old in current['rows']:
                if old['date'] not in rows:rows[old['date']]=old
    clean=[rows[k] for k in sorted(rows)]
    payload={'schema':1,'status':'ready','source':SOURCE,'updated_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),'rows':clean}
    temp=destination.with_suffix('.json.tmp')
    temp.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n')
    temp.replace(destination)
    print('正常に更新:',len(clean),'件、最新日:',clean[-1]['date'])
except Exception as e:
    print('取得・検証エラー。前回の公開データは変更しません:',str(e),file=sys.stderr)
    sys.exit(1)
