#!/usr/bin/env python3
"""Inject regenerated salesTrendData into index.html + update Report tab row + header date.

DYNAMIC version (2026-08-12): derives the newest 235959 report from
reports/order_reports/ instead of hardcoding dates (the 08-11 run hardcoded
2026-08-10 and silently failed to add the next day's row).

MONTH-ROLLOVER version (2026-09-03): when the newest report starts a NEW month,
the script now inserts that month's header (e.g. "📅 2026年 十月") at the TOP of
the order table and places the new daily row directly under it. Previously the
new month's rows sat under the previous month's header (Sep 2026 rows lived
under the "八月" header for 3 cron runs before being noticed).
"""
import glob
import os
import re

import openpyxl

REPO = os.path.dirname(os.path.abspath(__file__))
js = open(os.path.join(REPO, 'data', 'sales_trend_data.js'), encoding='utf-8').read()
html = open(os.path.join(REPO, 'index.html'), encoding='utf-8').read()

# 0. Newest 235959 order report on disk (authoritative for header + row)
files = glob.glob(os.path.join(REPO, 'reports', 'order_reports',
                               'ECOM-EXCH_DAILY_ORDER_H8391001_*235959.xlsx'))
dates = sorted({re.search(r'_(\d{8})235959\.xlsx$', f).group(1) for f in files})
assert dates, "no 235959 order reports found"
newest = dates[-1]
prev = dates[-2]
newest_disp = f"{newest[:4]}-{newest[4:6]}-{newest[6:]}"
prev_disp = f"{prev[:4]}-{prev[4:6]}-{prev[6:]}"
# GMV from row 2 col 6 of the newest report
wb = openpyxl.load_workbook(
    os.path.join(REPO, 'reports', 'order_reports',
                 f'ECOM-EXCH_DAILY_ORDER_H8391001_{newest}235959.xlsx'),
    data_only=True)
gmv = wb.active.cell(row=2, column=6).value or 0
gmv_str = f"${gmv:,.2f}"
print(f"newest={newest_disp} gmv={gmv_str} (prev={prev_disp})")

# 1. Extract new data block
m = re.search(r'const salesTrendData = (\{.*?\});\s*$', js, re.S)
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
html = html[:start] + new_block + html[end:]

# 3. Update header Order Report date (newest 235959)
header_new = f'📅 訂單報表: {newest_disp} (23:59:59)'
hpat = re.compile(r'📅 (?:Order Report|訂單報表): [\d\-]+ \(23:59:59\)')
if hpat.search(html):
    html = hpat.sub(header_new, html)
    print("header updated to:", header_new)
else:
    print("WARNING: header pattern not found; skipping header update")

# 4. Add Report tab row for newest date (only if not already present)
row_marker = f'ECOM-EXCH_DAILY_ORDER_H8391001_{newest}'
if row_marker in html:
    print(f"{newest_disp} row already present; skip")
else:
    month_names = ['一月', '二月', '三月', '四月', '五月', '六月',
                   '七月', '八月', '九月', '十月', '十一月', '十二月']
    cur_hdr_txt = f'📅 {newest[:4]}年 {month_names[int(newest[4:6]) - 1]}'
    anchor = f'ECOM-EXCH_DAILY_ORDER_H8391001_{prev}235959.xlsx'
    a_idx = html.find(anchor)
    assert a_idx != -1, f"anchor row {prev_disp} not found"
    tr_start = html.rfind('<tr', 0, a_idx)
    tr_end = html.find('</tr>', a_idx) + len('</tr>')
    old_tr = html[tr_start:tr_end]
    new_tr = old_tr.replace(prev, newest)
    new_tr = new_tr.replace(prev_disp, newest_disp)
    new_tr = re.sub(r'\$[\d,]+\.\d{2}', gmv_str, new_tr, count=1)
    if cur_hdr_txt not in html:
        # Month rollover: add the new month's header at the TOP of the order table
        # and place the new row directly under it (rows are newest-first).
        first_link = html.find('order_reports/ECOM-EXCH_DAILY_ORDER_H8391001_')
        assert first_link != -1, "order table not found"
        tbl_start = html.rfind('<table', 0, first_link)
        tbody_idx = html.find('<tbody>', tbl_start)
        assert tbody_idx != -1 and tbody_idx < first_link, "order tbody not found"
        region = html[tbody_idx:first_link]
        hdr_re = re.compile(r'(<tr style="background:#f0f0f0;font-weight:bold;color:#555;">\s*'
                            r'<td colspan="4" class="text-start ps-3">'
                            r'<span style="font-size:0.85rem;">)(📅 \d{4}年 [^<\s]+)'
                            r'(</span></td>\s*</tr>)')
        mh = hdr_re.search(region)
        assert mh, "no month header row in order table"
        new_hdr_row = mh.group(1) + cur_hdr_txt + mh.group(3)
        ins = tbody_idx + mh.start()
        html = html[:ins] + new_hdr_row + html[ins:]
        ins_row = ins + len(new_hdr_row)
        html = html[:ins_row] + new_tr + html[ins_row:]
        print(f"month rollover: header {cur_hdr_txt} + {newest_disp} row inserted at top")
    else:
        # insert BEFORE the anchor row (table is newest-first)
        html = html[:tr_start] + new_tr + html[tr_start:]
        print(f"inserted {newest_disp} tr before {prev_disp} row")

open(os.path.join(REPO, 'index.html'), 'w', encoding='utf-8').write(html)
print("index.html written, size:", len(html))
