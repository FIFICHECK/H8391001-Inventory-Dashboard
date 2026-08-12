#!/usr/bin/env python3
"""Fix Report tab (v2): move the 08-11 ORDER row back into Daily Order Report
table (top, newest-first) and keep the inventory row in the Daily Inventory
Report table.

v1 matched greedily from the 08-11 row through the inventory row; this version
locates rows by their exact markers:
  - order row  : href contains 'order_reports/ECOM-EXCH_DAILY_ORDER_H8391001_20260811235959.xlsx' + btn-warning
  - inv row    : href contains 'reports/inventory_report_' + btn-success + time cell '—'
"""
import os
import re

REPO = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(REPO, 'index.html')
html = open(path, encoding='utf-8').read()

report_idx = html.find('id="report"')
inv_card = html.find('📋 Daily Inventory Report', report_idx)
order_card = html.find('📦 Daily Order Report', report_idx)
assert inv_card != -1 and order_card != -1

# Daily Inventory Report tbody
inv_start = html.find('<tbody>', inv_card)
inv_end = html.find('</tbody>', inv_start) + len('</tbody>')
# Daily Order Report tbody
order_start = html.find('<tbody>', order_card)
order_end = html.find('</tbody>', order_start) + len('</tbody>')

inv_tbody = html[inv_start:inv_end]
order_tbody = html[order_start:order_end]

print('=== BEFORE ===')
print('inv rows:', inv_tbody.count('<tr'), '| order rows:', order_tbody.count('<tr'))

# --- Extract the 08-11 ORDER row from inventory tbody (if misplaced there) ---
def extract_row(tbody, marker):
    """Return (row_html, rest_tbody) for the first <tr>...</tr> containing marker."""
    m = re.search(r'<tr>.*?</tr>', tbody, re.S)
    # find the tr that contains the marker
    for m in re.finditer(r'<tr>.*?</tr>', tbody, re.S):
        if marker in m.group(0):
            return m.group(0), tbody.replace(m.group(0), '', 1)
    return None, tbody

order_row_marker = 'order_reports/ECOM-EXCH_DAILY_ORDER_H8391001_20260811235959.xlsx'
inv_row_marker = 'reports/inventory_report_'

# 1. Remove 08-11 order row from inventory tbody (it was moved there by v1)
row11, inv_tbody = extract_row(inv_tbody, order_row_marker)
if row11:
    print('removed 08-11 order row from INVENTORY tbody')
else:
    print('08-11 order row NOT in inventory tbody (already clean)')

# 2. Ensure inventory tbody has exactly ONE inventory row (btn-success / inventory_report_)
inv_rows = re.findall(r'<tr>.*?</tr>', inv_tbody, re.S)
inv_rows = [r for r in inv_rows if inv_row_marker in r]
if len(inv_rows) > 1:
    print('⚠️ multiple inventory rows in inventory tbody — keeping first')
    for extra in inv_rows[1:]:
        inv_tbody = inv_tbody.replace(extra, '', 1)
elif len(inv_rows) == 0:
    print('⚠️ inventory tbody has NO inventory row — restoring from HEAD')
    # grab the inventory row from git HEAD version
    import subprocess
    head_html = subprocess.run(['git', 'show', 'HEAD:index.html'],
                               cwd=REPO, capture_output=True, text=True).stdout
    hi = head_html.find('id="report"')
    hcard = head_html.find('📋 Daily Inventory Report', hi)
    htbody = head_html[head_html.find('<tbody>', hcard):head_html.find('</tbody>', head_html.find('<tbody>', hcard)) + 8]
    hrows = [r for r in re.findall(r'<tr>.*?</tr>', htbody, re.S) if inv_row_marker in r]
    if hrows:
        ins = inv_tbody.find('>') + 1
        inv_tbody = inv_tbody[:ins] + '\n' + hrows[0] + '\n' + inv_tbody[ins:]
        print('restored inventory row from HEAD:', ' '.join(hrows[0].split())[:120])

# 3. Insert 08-11 order row at TOP of order tbody (right after the month header tr, or very top)
if row11:
    # Put it right after the opening <tbody> (before month header) — table is newest-first
    ins = order_tbody.find('>') + 1
    order_tbody = order_tbody[:ins] + '\n' + row11 + '\n' + order_tbody[ins:]
    print('inserted 08-11 order row at top of ORDER tbody')
else:
    # check if 08-11 already in order tbody
    if '20260811' in order_tbody:
        print('08-11 order row already in ORDER tbody')
    else:
        print('⚠️ 08-11 order row missing entirely!')

# 4. Verify order tbody newest-first: 08-11, 08-10, 08-09...
order_dates = re.findall(r'<strong>(\d{4}-\d{2}-\d{2})</strong>', order_tbody)
inv_dates = re.findall(r'<strong>(\d{4}-\d{2}-\d{2})</strong>', inv_tbody)
print('=== AFTER ===')
print('inv rows:', inv_tbody.count('<tr'), '| inv dates:', inv_dates)
print('order rows:', order_tbody.count('<tr'), '| order dates (first 5):', order_dates[:5])
ok = order_dates[:3] == ['2026-08-11', '2026-08-10', '2026-08-09']
print('order newest-first OK:', ok)

html = html[:inv_start] + inv_tbody + html[inv_end:]
# order_start/order_end shifted by inv_tbody length change
order_start = html.find('<tbody>', order_card)
order_end = html.find('</tbody>', order_start) + len('</tbody>')
html = html[:order_start] + order_tbody + html[order_end:]

open(path, 'w', encoding='utf-8').write(html)
print('index.html written:', len(html))
