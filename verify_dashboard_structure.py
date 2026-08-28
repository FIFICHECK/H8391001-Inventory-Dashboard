#!/usr/bin/env python3
"""Verify H8391001 dashboard structure after generator/HTML changes.

Run from the repo root:  python3 scripts/verify_dashboard_structure.py
Checks (learned 2026-08-25 after the By SKU Status + Chinese-name changes):
  1. All named tbodies exist and have expected row counts
  2. By SKU Status cards carry both sides (data-side counts match CSV)
  3. Status count spans are filled
  4. No duplicate element ids (ignores string-literal 'Excel.Sheet' dup)
  5. Product names are Chinese (count rows whose rendered name starts ASCII)
  6. JS syntax (node --check) on extracted <script> blocks
Exit 0 = all pass; prints per-check results.
"""
import re
import subprocess
import sys
import csv
from collections import Counter

INDEX = 'index.html'
CSV_PATH = 'data/inventory_all.csv'

def main():
    problems = []
    html = open(INDEX, encoding='utf-8').read()

    # 1. tbody presence + rough row counts
    expect = {
        'tableAll': 472, 'tableSku': 106, 'tableNewSku': 25,
        'statusBodyOnline': 472, 'statusBodyInvisible': 472, 'statusBodyFoos': 472,
        'alertsZeroBody': 394, 'alertsLowBody': 3,
    }
    for tid, exp in expect.items():
        m = re.search(r'<tbody id="' + tid + r'">(.*?)</tbody>', html, re.S)
        if not m:
            problems.append(f'{tid}: MISSING tbody')
            continue
        rows = m.group(1).count('<tr')
        flag = '' if rows == exp else f'  (expected {exp})'
        print(f'{tid}: {rows} rows{flag}')
        if rows != exp:
            problems.append(f'{tid}: {rows} rows != {exp}')

    # 2. status card sides vs CSV
    counts = {'online': 0, 'offline': 0, 'invY': 0, 'invN': 0, 'foosY': 0, 'foosN': 0}
    with open(CSV_PATH, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            counts['online' if (r.get('Online Status') or '').upper() == 'ONLINE' else 'offline'] += 1
            counts['invY' if (r.get('Invisible') or '').upper() == 'Y' else 'invN'] += 1
            counts['foosY' if (r.get('Force Out Of Stock') or '').upper() == 'Y' else 'foosN'] += 1
    for tid, key, val in [('statusBodyOnline', 'online', 'online'), ('statusBodyOnline', 'offline', 'offline'),
                          ('statusBodyInvisible', 'invY', 'Y'), ('statusBodyInvisible', 'invN', 'N'),
                          ('statusBodyFoos', 'foosY', 'Y'), ('statusBodyFoos', 'foosN', 'N')]:
        m = re.search(r'<tbody id="' + tid + r'">(.*?)</tbody>', html, re.S)
        got = len(re.findall(r'data-side="' + val + r'"', m.group(1))) if m else -1
        exp = counts[key]
        flag = '' if got == exp else f'  (expected {exp} from CSV)'
        print(f'{tid} data-side={val}: {got}{flag}')
        if got != exp:
            problems.append(f'{tid} data-side={val}: {got} != {exp}')

    # 3. count spans
    for cid in ['statusCountOnline', 'statusCountInvisible', 'statusCountFoos']:
        m = re.search(r'id="' + cid + r'">([^<]*)<', html)
        print(f'{cid}: {m.group(1) if m else "MISSING"}')
        if not m:
            problems.append(f'{cid}: missing')

    # 4. duplicate ids (ignore the Excel.Sheet string-literal)
    ids = [i for i in re.findall(r'id="([^"]+)"', html) if i != 'Excel.Sheet']
    dups = {k: v for k, v in Counter(ids).items() if v > 1}
    print(f'duplicate ids: {dups if dups else "none"}')
    if dups:
        problems.append(f'duplicate ids: {dups}')

    # 5. Chinese-name coverage in tableAll (Latin-starting = usually legit brand prefix, report count only)
    m = re.search(r'<tbody id="tableAll">(.*?)</tbody>', html, re.S)
    if m:
        eng = [n for n in re.findall(r'<td title="([^"]{5,})">', m.group(1)) if re.match(r'^[A-Za-z]', n)]
        print(f'tableAll Latin-starting names: {len(eng)} (mostly legit brand prefixes like THANN/Bryony — check a sample)')
        for n in eng[:5]:
            print('   ', n)

    # 6. JS syntax
    scripts = re.findall(r'<script>(.*?)</script>', html, re.S)
    tmp = '/tmp/h839_scripts_check.js'
    open(tmp, 'w', encoding='utf-8').write('\n;\n'.join(scripts))
    r = subprocess.run(['node', '--check', tmp], capture_output=True, text=True)
    print(f'node --check: {"PASS" if r.returncode == 0 else "FAIL"} ({len(scripts)} script blocks)')
    if r.returncode != 0:
        problems.append('node --check failed: ' + r.stderr[-300:])

    print()
    if problems:
        print('❌ PROBLEMS:')
        for p in problems:
            print('  -', p)
        sys.exit(1)
    print('✅ all structure checks passed')

if __name__ == '__main__':
    main()
