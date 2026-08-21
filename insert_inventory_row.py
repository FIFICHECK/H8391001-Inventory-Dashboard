#!/usr/bin/env python3
"""Insert a new inventory report row into index.html Report tab (newest first)."""
import re

TS = '20260821_1409'
DATA_DATE = '2026-08-18'
TIME = '14:09'
SKU_COUNT = '448'

h = open('index.html', encoding='utf-8').read()

new_row = (
    '<tr>\n'
    '                                    <td class="align-middle"><strong>2026-08-18</strong></td>\n'
    '                                    <td class="align-middle text-muted text-center">14:09</td>\n'
    '                                    <td class="align-middle text-end">448</td>\n'
    '                                    <td class="align-middle">\n'
    '                                        <a href="reports/inventory_report_20260821_1409.csv" download class="btn btn-sm btn-success">\n'
    '                                            <i class="bi bi-download me-1"></i>\U0001F4E5 Download\n'
    '                                        </a>\n'
    '                                    </td>\n'
    '                                </tr>\n'
)

# anchor on the newest existing row's link (was 08-14 row)
anchor = '<a href="reports/inventory_report_20260817_1407.csv"'
anchor_idx = h.find(anchor)
assert anchor_idx != -1, 'anchor not found'
tr_start = h.rfind('<tr>', 0, anchor_idx)
assert tr_start != -1, 'tr_start not found'

# guard: never double-insert
if f'reports/inventory_report_{TS}.csv' in h:
    print('row already present — skip insert')
else:
    h = h[:tr_start] + new_row + h[tr_start:]
    open('index.html', 'w', encoding='utf-8').write(h)
    print('inserted new row at index', tr_start)

# verify: newest first order of inventory rows
links = re.findall(r'<a href="reports/(inventory_report_[^"]+\.csv)"', h)
print('inventory links order (first 4):', links[:4])
assert links[0] == f'inventory_report_{TS}.csv', 'new row not first'
assert len(links) >= 4, 'expected >= 4 rows'
print('OK')
