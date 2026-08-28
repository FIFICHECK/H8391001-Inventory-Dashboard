#!/usr/bin/env python3
"""Post-inject verification for H8391001 sales-trend data in index.html.

Run AFTER inject_sales_trend.py / inject_multi_order_rows.py (and BEFORE
scripts/generate_inventory_dashboard.py if you want to catch issues early).

Encodes the verification traps documented in the skill (2026-08-12..08-27):
1. `const salesTrendData = ` marker exists; extract the FULL statement by
   brace-walk. (The old regex `const salesTrendData = (\{.*?\});\s*$` FAILS —
   more JS follows the block so the `\s*$` anchor never matches; and a bare
   braces-only file makes `node --check` PASS vacuously on an empty file.)
2. Newest *235959 date (globbed from reports/order_reports/) is inside the block.
3. Report-tab order rows: scoped to the ORDER table region (a naive
   document-wide `<strong>YYYY-MM-DD</strong>` search matches the Daily
   Inventory row's date cell FIRST when both share the newest date), every
   order date after its (newest) month header, dates newest-first.
4. Header `📅 Order Report:` date equals the newest 235959 date.

Writes the full statement (prefix + block + trailing `;`) to /tmp/stmt.js —
`node --check` on THAT file is the JS-validity gate (bare `{...}` fails:
top-level braces parse as a block statement and string-literal labels are
invalid). Exit code 0 = all checks pass.

Usage: python3.12 scripts/verify_sales_trend_state.py   (no openpyxl needed)
"""
import glob, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)

h = open('index.html', encoding='utf-8').read()
files = sorted(glob.glob('reports/order_reports/ECOM-EXCH_DAILY_ORDER_H8391001_*235959.xlsx'))
assert files, 'no *235959.xlsx files found in reports/order_reports/'
newest = os.path.basename(files[-1])
m = re.search(r'_(\d{8})235959\.xlsx$', newest)
newest_date = f'{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:8]}'
print(f'newest 235959: {newest} -> {newest_date}')

ok = True
def check(name, cond):
    global ok
    print(('PASS' if cond else 'FAIL') + ' | ' + name)
    ok = ok and cond

# 1. brace-walk extraction of the full statement
s = h.find('const salesTrendData = ')
check('salesTrendData marker found', s != -1)
if s == -1:
    sys.exit(1)
start = h.find('{', s)
depth, i = 0, start
while True:
    if h[i] == '{':
        depth += 1
    elif h[i] == '}':
        depth -= 1
        if depth == 0:
            break
    i += 1
stmt = h[s:i + 2]  # prefix + block + trailing ';'
open('/tmp/stmt.js', 'w', encoding='utf-8').write(stmt)
check(f'block extraction sane ({len(stmt)} chars)', 100_000 < len(stmt) < 1_000_000)

# 2. newest date present
check(f'newest date {newest_date} inside block', newest_date in stmt)

# 3. scoped order-table row order
first_link = h.find('order_reports/ECOM-EXCH_DAILY_ORDER_H8391001_')
seg = h[h.rfind('<table', 0, first_link):h.find('</table>', first_link)]
hdrs = re.findall(r'📅 2026年 \S+', seg)
check('month header(s) found in order table', bool(hdrs))
if hdrs:
    hdr_idx = seg.find(hdrs[0])  # newest month header is first (table newest-first)
    date_strs = re.findall(r'<strong>(\d{4}-\d{2}-\d{2})</strong>', seg)
    check('order rows after month header',
          all(seg.find(f'<strong>{d}</strong>') > hdr_idx for d in date_strs))
    check('order rows newest-first (>=10 dates)',
          len(date_strs) >= 10 and date_strs == sorted(date_strs, reverse=True))

# 4. header date
mh = re.search(r'Order Report: (\d{4}-\d{2}-\d{2})', h)
check(f'header date == {newest_date}', bool(mh) and mh.group(1) == newest_date)

print('\nNext: node --check /tmp/stmt.js   (exit 0 = embedded JS valid)')
sys.exit(0 if ok else 1)
