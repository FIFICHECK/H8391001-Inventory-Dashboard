#!/usr/bin/env python3
"""Inject regenerated salesTrendData into index.html + update Report tab row + header date."""
import re, sys, os

REPO = os.path.dirname(os.path.abspath(__file__))
js = open(os.path.join(REPO, 'data', 'sales_trend_data.js'), encoding='utf-8').read()
html = open(os.path.join(REPO, 'index.html'), encoding='utf-8').read()

# 1. Extract new data block
m = re.search(r'const salesTrendData = (\{.*?\});\s*$', js, re.DOTALL)
assert m, "cannot find salesTrendData in generated js"
new_block = m.group(0)

# 2. Replace embedded block in index.html
marker = '// Sales Trend Data (embedded from order reports)'
idx = html.find(marker)
assert idx != -1, "marker not found"
start = html.find('const salesTrendData =', idx)
assert start != -1, "const not found after marker"
end = html.find('};', start)
assert end != -1
end += 2
old_block = html[start:end]
print(f"old block: {len(old_block)} chars | new block: {len(new_block)} chars")
assert '2026-08-10' in new_block, "new block missing 08-10!"
html = html[:start] + new_block + html[end:]

# 3. Update header Order Report date (latest 235959 = 2026-08-10)
header_new = '📅 Order Report: 2026-08-10 (23:59:59)'
# find existing header pattern
hpat = re.compile(r'📅 Order Report: [\d\-]+ \(23:59:59\)')
if hpat.search(html):
    html = hpat.sub(header_new, html)
    print("header updated to:", header_new)
else:
    print("WARNING: header pattern not found; skipping header update")

# 4. Add Report tab row for 2026-08-10 (only if not already present)
row_marker = 'ECOM-EXCH_DAILY_ORDER_H8391001_20260810'
if row_marker in html:
    print("08-10 row already present; skip")
else:
    # Find the Daily Order Report table body region — search for the newest existing row (08-09)
    anchor = 'ECOM-EXCH_DAILY_ORDER_H8391001_20260809235959.xlsx'
    a_idx = html.find(anchor)
    assert a_idx != -1, "08-09 anchor row not found"
    # The anchor is inside an <a href=...> link within a <tr>...</tr>; find the enclosing <tr>
    tr_start = html.rfind('<tr', 0, a_idx)
    tr_end = html.find('</tr>', a_idx) + len('</tr>')
    old_tr = html[tr_start:tr_end]
    print("anchor tr:\n", old_tr[:400])

    # Build new row: 2026-08-10 / 23:59 / $3,376.00 / download btn-warning
    new_tr = old_tr.replace('20260809235959', '20260810235959')
    new_tr = new_tr.replace('2026-08-09', '2026-08-10')
    new_tr = new_tr.replace('$31,203.50', '$3,376.00')  # if GMV shown in row
    # fallback: replace any $X,XXX.XX figure generically via regex if the above misses
    if '$3,376.00' not in new_tr:
        new_tr = re.sub(r'\$[\d,]+\.\d{2}', '$3,376.00', new_tr, count=1)
    html = html[:tr_end] + new_tr + html[tr_end:]
    print("inserted new tr after 08-09 row")

open(os.path.join(REPO, 'index.html'), 'w', encoding='utf-8').write(html)
print("index.html written, size:", len(html))
