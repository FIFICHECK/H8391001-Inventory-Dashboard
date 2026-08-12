#!/usr/bin/env python3
"""Reconstruct the user's by_sku CSV (UTF-16 LE tab-delimited) from the last
CSV-aligned sales_trend_data.js (committed at HEAD before regeneration).

The original uploaded CSV (doc_e8b50865f63f_...) was removed from the hermes
cache documents dir, which made align_sales_trend_to_csv.py silently skip on
cron runs -> monthly figures revert to raw Exchange sums. This script rebuilds
the CSV from the ALIGNED monthly SKU data (gmv_by_sku_monthly /
qty_by_sku_monthly are CSV-derived for Jan-Jul), so alignment can be restored.

Notes:
- load_csv_monthly() only uses gmv/orders/qty TOTALS per month; per-SKU order
  distribution does not matter, so each month's total orders is placed on the
  first SKU row (r[23+i]).
- Monthly CSV order totals (Jan-Jul): 2273/3039/1979/2310/3635/2078/1007
  (documented in h8391001-inventory-dashboard skill KPI reference).
- Output layout must satisfy: len(r) >= 38, r[1]=SKU, r[9+i]=gmv,
  r[23+i]=orders, r[30+i]=qty for i in 0..6 (months 2026-01..2026-07).
"""
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, 'data/by_sku_2026-01-07.tsv')

CSV_MONTHS = ['2026-01', '2026-02', '2026-03', '2026-04', '2026-05', '2026-06', '2026-07']
MONTH_ORDERS = [2273, 3039, 1979, 2310, 3635, 2078, 1007]  # CSV order counts (skill KPI ref)

src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, 'data/sales_trend_data.js')
js = open(src, encoding='utf-8').read()
m = re.search(r'const salesTrendData = (\{.*?\});\s*$', js, re.S)
data = json.loads(m.group(1))

gmv_m = data['gmv_by_sku_monthly']   # labels: 8 months, skus: 114, data: [month][sku]
qty_m = data['qty_by_sku_monthly']
skus = gmv_m['skus']
m_idx = {lab: i for i, lab in enumerate(gmv_m['labels'])}

rows = []
header1 = ['store', 'SKU'] + [''] * 36
header2 = ['', ''] + [''] * 36
rows.append('\t'.join(header1))
rows.append('\t'.join(header2))

for si, sku in enumerate(skus):
    row = [''] * 38
    row[1] = sku
    for mi, mth in enumerate(CSV_MONTHS):
        idx = m_idx.get(mth)
        if idx is None:
            continue
        g = gmv_m['data'][idx][si]
        q = qty_m['data'][idx][si]
        if g or q:
            row[9 + mi] = f'{g:,.2f}' if g else ''
            row[30 + mi] = f'{int(q):,}' if q else ''
    # monthly total orders on first SKU row of each month
    if si == 0:
        for mi, o in enumerate(MONTH_ORDERS):
            if o:
                row[23 + mi] = f'{o:,}'
    rows.append('\t'.join(row))

text = '\n'.join(rows) + '\n'
raw = text.encode('utf-16')
if not raw.startswith(b'\xff\xfe'):
    raw = b'\xff\xfe' + raw
open(OUT, 'wb').write(raw)
print(f'Wrote {OUT} ({len(raw)} bytes, {len(rows)} rows)')
