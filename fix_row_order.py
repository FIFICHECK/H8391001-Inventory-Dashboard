#!/usr/bin/env python3
"""Fix Report tab row order: move 2026-08-10 row to be FIRST (before 08-09), newest-first."""
import re, os

REPO = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(REPO, 'index.html')
html = open(path, encoding='utf-8').read()

# Extract the 08-10 row we inserted (its full <tr>...</tr>)
m10 = re.search(r'(<tr>\s*<td class="align-middle"><strong>2026-08-10</strong></td>.*?</tr>)', html, re.DOTALL)
assert m10, "08-10 row not found"
row10 = m10.group(1)

# Remove it
html = html.replace(row10, '', 1)

# Find the 08-09 row start and insert BEFORE it
anchor = '<td class="align-middle"><strong>2026-08-09</strong></td>'
a_idx = html.find(anchor)
assert a_idx != -1, "08-09 anchor not found"
tr_start = html.rfind('<tr', 0, a_idx)
html = html[:tr_start] + row10 + '\n' + html[tr_start:]

open(path, 'w', encoding='utf-8').write(html)
print("08-10 row moved to top of August list")

# Verify order
idx10 = html.find('<strong>2026-08-10</strong>')
idx09 = html.find('<strong>2026-08-09</strong>')
idx08 = html.find('<strong>2026-08-08</strong>')
print("order 10<09<08:", idx10 < idx09 < idx08)
