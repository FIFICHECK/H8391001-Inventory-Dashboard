#!/usr/bin/env python3
"""H8391001 Inventory Dashboard Generator
Reads data/inventory_all.csv (447 SKUs) and fills ALL tabs of index.html:
- KPI cards, tab labels, header dates
- tableAll / tableSku / Brand / Category Type / Category Full
- SKU Status cards (Online / Invisible / Force OOS)
- Alerts (Zero / Low) / New SKU
Price Check tab is rendered dynamically from price_check_data.json (unchanged).
"""
import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from urllib.parse import quote

REPO = os.path.expanduser('~/H8391001-Inventory-Dashboard')
os.chdir(REPO)

INDEX = 'index.html'
CSV_PATH = 'data/inventory_all.csv'
PRICE_CHECK = 'data/price_check_data.json'

CATEGORY_TYPE_MAPPING = {
    "AA11": "超級市場",
    "AA13": "個人護理",
    "AA16": "健康及醫療用品",
    "AA18": "美容化妝",
    "AA32": "家電及電子產品",
}

def load_rows():
    rows = []
    with open(CSV_PATH, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            sku = (r.get('Merchant SKU ID') or '').strip()
            if not sku:
                continue
            rows.append({
                'sku': sku,
                'name': (r.get('SKU Name') or '').strip(),
                'name_chi': (r.get('SKU Name (Chi)') or '').strip(),
                'stock': int(float((r.get('StockLevel') or 0) or 0)),
                'online': (r.get('Online Status') or '').strip().upper(),
                'invisible': (r.get('Invisible') or '').strip().upper(),
                'foos': (r.get('Force Out Of Stock') or '').strip().upper(),
                'brand': (r.get('Brand Name (EN)') or '').strip() or 'Unknown',
                'cat_code': (r.get('Primary Category Code') or '').strip(),
                'cat_name': (r.get('Primary Category Name (CHI)') or '').strip(),
                'create_date': (r.get('Create Date') or '').strip(),
            })
    return rows

def get_status(inv):
    if inv == 0:
        return 'zero', '🚫 Zero (0)'
    elif inv < 10:
        return 'low', '⚠️ 低庫存 (1-9)'
    elif inv < 50:
        return 'normal', '🟢 Normal (10-49)'
    return 'high', '🔵 High (50+)'

def esc(s, limit=70):
    s = str(s)[:limit]
    return (s.replace('&', '&amp;')
             .replace('<', '&lt;')
             .replace('>', '&gt;')
             .replace('"', '&quot;')
             .replace("'", '&#39;'))

def sku_row(row, show_brand=True, is_new=False):
    sku = esc(row['sku'], 25)
    name = esc(row['name_chi'] or row['name'])
    inv = row['stock']
    cls, label = get_status(inv)
    badge = f'<span class="badge badge-{cls}">{label}</span>'
    new_badge = '<span class="badge badge-new" style="background:#FF6B35;color:white;margin-left:4px;">🆕 新</span>' if is_new else ''
    brand_lower = row['brand'].lower().replace('"', '&quot;')
    sku_url = f"https://www.hktvmall.com/hktv/p/{row['sku'].replace(' ', '')}"
    onclick = f"showDetail('{sku}',\"{name}\",{inv},'{cls}')"
    brand_html = f'<td class="text-muted" style="font-size:0.75rem">{esc(row["brand"], 30)}</td>' if show_brand else ''
    return (f'<tr data-brand="{brand_lower}" onclick="{onclick}">'
            f'<td><a href="{sku_url}" target="_blank" onclick="event.stopPropagation()"><code>{sku}</code></a></td>'
            f'<td title="{name}">{name[:55]}{"..." if len(name) > 55 else ""}</td>'
            f'<td class="text-end">{inv:,}</td><td>{badge}{new_badge}</td>{brand_html}</tr>')

def status_card_row(row):
    sku = esc(row['sku'], 25)
    name = esc(row['name_chi'] or row['name'])
    inv = row['stock']
    cls, label = get_status(inv)
    badge = f'<span class="badge badge-{cls}">{label}</span>'
    sku_url = f"https://www.hktvmall.com/hktv/p/{row['sku'].replace(' ', '')}"
    onclick = f"showDetail('{sku}',\"{name}\",{inv},'{cls}')"
    return (f'<tr onclick="{onclick}">'
            f'<td><a href="{sku_url}" target="_blank" onclick="event.stopPropagation()"><code>{sku}</code></a></td>'
            f'<td title="{name}">{name[:55]}{"..." if len(name) > 55 else ""}</td>'
            f'<td class="text-end">{inv:,}</td><td>{badge}</td></tr>')

def status_card_full_row(row, dim):
    """Row for the By SKU Status cards — includes a data-side attr + a badge column
    showing WHICH side of the dimension the SKU is on (online/offline, Y/N, Y/N).
    dim: 'online' | 'invisible' | 'foos'"""
    sku = esc(row['sku'], 25)
    name = esc(row['name_chi'] or row['name'])
    inv = row['stock']
    cls, label = get_status(inv)
    badge = f'<span class="badge badge-{cls}">{label}</span>'
    sku_url = f"https://www.hktvmall.com/hktv/p/{row['sku'].replace(' ', '')}"
    onclick = f"showDetail('{sku}',\"{name}\",{inv},'{cls}')"
    if dim == 'online':
        side = 'online' if row['online'] == 'ONLINE' else 'offline'
        side_badge = ('<span class="badge" style="background:#0d6efd;color:white">🌐 Online</span>'
                      if side == 'online'
                      else '<span class="badge" style="background:#6c757d;color:white">⚫ Offline</span>')
    elif dim == 'invisible':
        side = 'Y' if row['invisible'] == 'Y' else 'N'
        side_badge = ('<span class="badge" style="background:#ffc107;color:#212529">👁️ Invisible Y</span>'
                      if side == 'Y'
                      else '<span class="badge" style="background:#198754;color:white">👀 Visible N</span>')
    else:  # foos
        side = 'Y' if row['foos'] == 'Y' else 'N'
        side_badge = ('<span class="badge" style="background:#dc3545;color:white">🚫 強制缺貨</span>'
                      if side == 'Y'
                      else '<span class="badge" style="background:#198754;color:white">✅ Available</span>')
    return (f'<tr data-side="{side}" onclick="{onclick}">'
            f'<td><a href="{sku_url}" target="_blank" onclick="event.stopPropagation()"><code>{sku}</code></a></td>'
            f'<td title="{name}">{name[:55]}{"..." if len(name) > 55 else ""}</td>'
            f'<td class="text-end">{inv:,}</td><td>{badge}</td><td>{side_badge}</td></tr>')

def main():
    rows = load_rows()
    print(f'📊 Loaded {len(rows)} SKUs from {CSV_PATH}')

    # ---- derived stats ----
    total_products = len(rows)
    total_stock = sum(r['stock'] for r in rows)
    zero_count = sum(1 for r in rows if r['stock'] == 0)
    low_count = sum(1 for r in rows if 0 < r['stock'] < 10)
    normal_count = sum(1 for r in rows if 10 <= r['stock'] < 50)
    high_count = sum(1 for r in rows if r['stock'] >= 50)
    online_count = sum(1 for r in rows if r['online'] == 'ONLINE')
    offline_count = total_products - online_count
    inv_y = sum(1 for r in rows if r['invisible'] == 'Y')
    inv_n = total_products - inv_y
    foos_y = sum(1 for r in rows if r['foos'] == 'Y')
    foos_n = total_products - foos_y

    # NEW SKU detection (14 days)
    NEW_DAYS = 14
    cutoff = datetime.now() - timedelta(days=NEW_DAYS)
    new_skus = set()
    for r in rows:
        cd = r['create_date']
        if not cd or cd == 'nan':
            continue
        try:
            if datetime.strptime(cd, '%d-%b-%Y') >= cutoff:
                new_skus.add(r['sku'])
        except ValueError:
            pass
    new_sku_count = len(new_skus)
    print(f'🆕 New SKUs (within {NEW_DAYS}d): {new_sku_count}')

    # ---- Build rows ----
    all_rows = ''.join(sku_row(r, is_new=r['sku'] in new_skus) for r in sorted(rows, key=lambda x: x['stock'], reverse=True))
    online_rows = ''.join(sku_row(r, is_new=r['sku'] in new_skus) for r in sorted((x for x in rows if x['online'] == 'ONLINE'), key=lambda x: x['stock'], reverse=True))
    zero_rows = ''.join(status_card_row(r) for r in sorted((x for x in rows if x['stock'] == 0), key=lambda x: x['name']))
    low_rows = ''.join(status_card_row(r) for r in sorted((x for x in rows if 0 < x['stock'] < 10), key=lambda x: x['stock']))
    new_sku_rows = ''.join(sku_row(r, is_new=True) for r in sorted((x for x in rows if x['sku'] in new_skus), key=lambda x: x['stock'], reverse=True)) if new_skus else ''

    # Brand summary
    brand_summary = defaultdict(lambda: {'count': 0, 'stock': 0})
    for r in rows:
        b = r['brand'] if r['brand'] != 'Unknown' or r['sku'] else r['brand']
        brand_summary[b]['count'] += 1
        brand_summary[b]['stock'] += r['stock']
    brand_rows_html = ''
    for b, d in sorted(brand_summary.items(), key=lambda x: x[1]['stock'], reverse=True)[:50]:
        hktv_url = f'https://www.hktvmall.com/hktv/s/H8391001?page=0&q=%3Arelevance%3Abrand%3A{quote(b, safe="")}%3Astreet%3Amain%3Astore%3AH8391001%3A'
        brand_rows_html += f'<tr><td><strong>{esc(b, 30)}</strong></td><td class="text-center">{d["count"]}</td><td class="text-end">{d["stock"]:,}</td><td><a href="{hktv_url}" target="_blank" class="btn btn-sm btn-outline-primary">🔍 HKTVmall</a></td></tr>'

    # Category data
    cat_type = defaultdict(lambda: {'name': '', 'products': 0, 'stock': 0, 'zero': 0, 'low': 0, 'normal': 0, 'high': 0, 'online': 0, 'offline': 0, 'inv_y': 0, 'foos_y': 0})
    cat_full = defaultdict(lambda: {'name': '', 'products': 0, 'stock': 0, 'zero': 0, 'low': 0, 'normal': 0, 'high': 0, 'online': 0, 'offline': 0, 'inv_y': 0, 'foos_y': 0})
    for r in rows:
        code = r['cat_code']
        prefix = code[:4] if len(code) >= 4 else 'OTHER'
        for store, key in ((cat_type, prefix), (cat_full, code)):
            store[key]['products'] += 1
            store[key]['stock'] += r['stock']
            store[key]['zero'] += 1 if r['stock'] == 0 else 0
            store[key]['low'] += 1 if 0 < r['stock'] < 10 else 0
            store[key]['normal'] += 1 if 10 <= r['stock'] < 50 else 0
            store[key]['high'] += 1 if r['stock'] >= 50 else 0
            store[key]['online'] += 1 if r['online'] == 'ONLINE' else 0
            store[key]['offline'] += 0 if r['online'] == 'ONLINE' else 1
            store[key]['inv_y'] += 1 if r['invisible'] == 'Y' else 0
            store[key]['foos_y'] += 1 if r['foos'] == 'Y' else 0
        if code:
            cat_type[prefix]['name'] = CATEGORY_TYPE_MAPPING.get(prefix, '其他')
            cat_full[code]['name'] = r['cat_name']

    def cat_row_html(key, data, is_type):
        inv_badge = f"<span class='badge bg-warning text-dark'>{data['inv_y']}</span>" if data['inv_y'] > 0 else f"<span class='badge bg-success'>{data['inv_y']}</span>"
        foos_badge = f"<span class='badge bg-danger'>{data['foos_y']}</span>" if data['foos_y'] > 0 else f"<span class='badge bg-success'>{data['foos_y']}</span>"
        online_badge = f'<span class="badge bg-success">{data["online"]}</span> / <span class="badge bg-secondary">{data["offline"]}</span>'
        if is_type:
            return f'''<tr data-type="{key}">
<td><strong>{data['name']}</strong></td>
<td class="text-muted"><code>{key}</code></td>
<td class="text-center">{data['products']}</td>
<td class="text-end">{data['stock']:,}</td>
<td class="text-center"><span class="badge badge-zero">{data['zero']}</span></td>
<td class="text-center"><span class="badge badge-low">{data['low']}</span></td>
<td class="text-center"><span class="badge badge-normal">{data['normal']}</span></td>
<td class="text-center"><span class="badge badge-high">{data['high']}</span></td>
<td class="text-center">{online_badge}</td>
<td class="text-center">{inv_badge}</td>
<td class="text-center">{foos_badge}</td>
</tr>'''
        primary_online = 'online' if data['online'] >= data['offline'] else 'offline'
        primary_inv = 'Y' if data['inv_y'] > 0 else 'N'
        primary_foos = 'Y' if data['foos_y'] > 0 else 'N'
        return f'''<tr data-online="{primary_online}" data-invisible="{primary_inv}" data-foos="{primary_foos}">
<td><code>{key}</code></td>
<td>{data['name']}</td>
<td class="text-center">{data['products']}</td>
<td class="text-end">{data['stock']:,}</td>
<td class="text-center"><span class="badge badge-zero">{data['zero']}</span></td>
<td class="text-center"><span class="badge badge-low">{data['low']}</span></td>
<td class="text-center"><span class="badge badge-normal">{data['normal']}</span></td>
<td class="text-center"><span class="badge badge-high">{data['high']}</span></td>
<td class="text-center">{online_badge}</td>
<td class="text-center">{inv_badge}</td>
<td class="text-center">{foos_badge}</td>
</tr>'''

    type_rows = ''.join(cat_row_html(k, v, True) for k, v in sorted(cat_type.items(), key=lambda x: x[1]['products'], reverse=True))
    full_rows = ''.join(cat_row_html(k, v, False) for k, v in sorted(cat_full.items(), key=lambda x: x[1]['products'], reverse=True) if k and k != 'nan')

    # SKU Status cards rows — FULL lists, side-first sort (offline→online, invisible Y→N, foos Y→N),
    # then stock descending within each side group.
    def _side_first_key(r, dim):
        if dim == 'online':
            grp = 0 if r['online'] != 'ONLINE' else 1   # Offline group first, then Online
        elif dim == 'invisible':
            grp = 0 if r['invisible'] == 'Y' else 1     # Invisible Y first, then Visible N
        else:
            grp = 0 if r['foos'] == 'Y' else 1          # Force OOS first, then Available
        return (grp, -r['stock'])

    online_s_rows = ''.join(status_card_full_row(r, 'online') for r in sorted(rows, key=lambda x: _side_first_key(x, 'online')))
    invisible_y_rows = ''.join(status_card_full_row(r, 'invisible') for r in sorted(rows, key=lambda x: _side_first_key(x, 'invisible')))
    foos_y_rows = ''.join(status_card_full_row(r, 'foos') for r in sorted(rows, key=lambda x: _side_first_key(x, 'foos')))

    # Brand options
    brand_options = '<option value="all">All Brands</option>'
    for b in sorted(brand_summary.keys()):
        brand_options += f'<option value="{b.lower().replace(chr(34), "&quot;")}">{esc(b, 40)}</option>'

    # Report date: read from the raw report CSV (kept in reports/) which has the
    # "Date,YYYY/MM/DD" header line — inventory_all.csv is cleaned (header stripped).
    # Glob newest inventory_report_*.csv first (filename is download-time-stamped).
    import glob as _glob
    report_date = ''
    candidates = sorted(_glob.glob('reports/inventory_report_*.csv'), reverse=True) + [CSV_PATH]
    for candidate in candidates:
        try:
            with open(candidate, encoding='utf-8-sig') as f:
                for line in f:
                    if line.startswith('Date,'):
                        report_date = line.split(',')[1].strip().replace('/', '-')
                        break
        except Exception:
            continue
        if report_date:
            break
    if not report_date:
        report_date = datetime.now().strftime('%Y-%m-%d')
    print(f'📅 Report date from CSV: {report_date}')
    generated_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Order report date: use the newest order report file if present, else N/A
    order_report_date_str = 'N/A'
    try:
        order_files = [f for f in os.listdir('reports/order_reports') if f.lower().endswith('.xlsx')]
        if order_files:
            # Parse date from filename: ECOM-EXCH_DAILY_ORDER_H8391001_YYYYMMDD235959.xlsx
            import re as _re
            order_files_dates = []
            for f in order_files:
                m = _re.search(r'_(\d{8})235959\.xlsx$', f)
                if m:
                    order_files_dates.append((f, m.group(1)))
            if order_files_dates:
                newest, latest_date_str = max(order_files_dates, key=lambda x: x[1])
                try:
                    latest_dt = datetime.strptime(latest_date_str, '%Y%m%d')
                    order_report_date_str = latest_dt.strftime('%Y-%m-%d') + ' (23:59:59)'
                except ValueError:
                    order_report_date_str = 'N/A'
    except Exception:
        pass
    print(f'📦 Order report date: {order_report_date_str}')

    # Price check count
    try:
        pcd = json.load(open(PRICE_CHECK, encoding='utf-8'))
        price_count = len(pcd)
    except Exception:
        price_count = total_products

    # ==================== Patch index.html ====================
    html = open(INDEX, encoding='utf-8').read()
    orig_len = len(html)

    # 1. Header dates
    html = re.sub(r'📅 Inventory Report: [^&]+', f'📅 Inventory Report: {report_date}', html)
    html = re.sub(r'📅 Order Report: [^|]+', f'📅 Order Report: {order_report_date_str}', html)
    html = re.sub(r'🔄 [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9:]{8}', f'🔄 {generated_time}', html)

    # 2. KPI cards — regex on label anchor; robust to ANY current value
    #    (2026-08-28 fix: old replace-on-'0' pattern no-oped once cards held
    #    non-zero values, freezing them at stale numbers)
    kpi_cards = [
        ('var(--primary)', '📦 總 SKU 數',      str(total_products)),
        ('var(--success)', '📊 總庫存',     f'{total_stock:,}'),
        ('var(--danger)',  '🚫 Zero (0)',        str(zero_count)),
        ('var(--warning)', '⚠️ 低庫存 (1-9)',       str(low_count)),
        ('var(--success)', '🟢 Normal (10-49)',  str(normal_count)),
        ('var(--primary)', '🔵 High (50+)',      str(high_count)),
    ]
    for _kpi_color, _kpi_label, _kpi_value in kpi_cards:
        _kpi_pat = re.compile(r'(<div class="kpi-value" style="color:' + re.escape(_kpi_color) + r'">)[^<]*(</div><div class="kpi-label">)' + re.escape(_kpi_label))
        _kpi_html, _kpi_n = _kpi_pat.subn(
            lambda m, v=_kpi_value, l=_kpi_label: m.group(1) + v + m.group(2) + l,
            html)
        if _kpi_n == 0:
            print(f'⚠️ KPI card not found: {_kpi_label}')
        else:
            html = _kpi_html
            print(f'✅ KPI {_kpi_label} -> {_kpi_value}')

    # 3. Tab labels
    html = re.sub(r'(data-bs-target="#all">📋 )[^<]*', rf'\g<1>全部 ({total_products})', html)
    html = re.sub(r'(data-bs-target="#skuid">🔢 網上 SKU)[^<]*', rf'\g<1> ({online_count})', html)
    html = re.sub(r'(data-bs-target="#brand">🏷️ )[^<]*', rf'\g<1>品牌 ({len(brand_summary)})', html)
    html = re.sub(r'(data-bs-target="#alerts">⚠️ 警示)[^<]*', rf'\g<1> ({zero_count + low_count})', html)
    html = re.sub(r'(data-bs-target="#newsku">🆕 新 SKU)[^<]*', rf'\g<1> ({new_sku_count})', html)
    html = re.sub(r'(data-bs-target="#pricecheck">💰 價格檢查)[^<]*', rf'\g<1> ({price_count})', html)

    # 4. tableAll tbody
    def replace_tbody(html, tbody_id, content):
        pattern = re.compile(r'(<tbody[^>]*id="' + re.escape(tbody_id) + r'"[^>]*>).*?(</tbody>)', re.S)
        m = pattern.search(html)
        if not m:
            print(f'⚠️ tbody #{tbody_id} not found')
            return html
        return pattern.sub(lambda mm: mm.group(1) + content + mm.group(2), html)

    html = replace_tbody(html, 'tableAll', all_rows)
    html = replace_tbody(html, 'tableSku', online_rows)
    html = replace_tbody(html, 'categoryTypeBody', type_rows)
    html = replace_tbody(html, 'categoryFullBody', full_rows)
    html = replace_tbody(html, 'tableNewSku', new_sku_rows)

    # 5. Brand table tbody (first tbody after #brand pane, no id)
    brand_pattern = re.compile(r'(id="brand">.*?<tbody>)(.*?)(</tbody>)', re.S)
    m = brand_pattern.search(html)
    if m:
        html = brand_pattern.sub(lambda mm: mm.group(1) + brand_rows_html + mm.group(3), html, count=1)
    else:
        print('⚠️ brand tbody not found')

    # 6. Brand filter options
    for sel_id in ['brandAll', 'brandSku']:
        pattern = re.compile(r'(<select id="' + sel_id + r'"[^>]*>)(.*?)(</select>)', re.S)
        m = pattern.search(html)
        if m:
            html = pattern.sub(lambda mm: mm.group(1) + brand_options + mm.group(3), html, count=1)

    # 7. SKU Status cards: replace count spans + tbody (id-based — cards show ALL SKUs, filterable by data-side)
    def replace_count(html, count_id, text):
        pattern = re.compile(r'(id="' + re.escape(count_id) + r'">)[^<]*')
        m = pattern.search(html)
        if not m:
            print(f'⚠️ count span #{count_id} not found')
            return html
        return pattern.sub(lambda mm: mm.group(1) + text, html)

    html = replace_count(html, 'statusCountOnline', f'{online_count} online / {offline_count} offline')
    html = replace_count(html, 'statusCountInvisible', f'{inv_y} Y / {inv_n} N')
    html = replace_count(html, 'statusCountFoos', f'{foos_y} Y / {foos_n} N')

    html = replace_tbody(html, 'statusBodyOnline', online_s_rows)
    html = replace_tbody(html, 'statusBodyInvisible', invisible_y_rows)
    html = replace_tbody(html, 'statusBodyFoos', foos_y_rows)

    # 8. Alerts cards: Zero + Low (id-based)
    html = re.sub(r'(🚫 零庫存 \()[^)]*', rf'\g<1>{zero_count}', html)
    html = re.sub(r'(⚠️ 低庫存 \()[^)]*', rf'\g<1>{low_count}', html)
    html = replace_tbody(html, 'alertsZeroBody', zero_rows)
    html = replace_tbody(html, 'alertsLowBody', low_rows)

    # 9. Category footer date
    html = re.sub(r'(\* 數據日期: )[^|]+', rf'\g<1>{report_date}', html)

    # 9b. Report tab row: show DATA date (from CSV) not download time.
    # Pattern: first inventory report row in the Report tab — replace the date cell
    # (a <strong>YYYY-MM-DD</strong>) inside the Daily Inventory Report table.
    # Find the report pane, take the first <strong>date</strong> after the inventory table header.
    report_pane = html.find('id="report"')
    if report_pane > -1:
        pane = html[report_pane:]
        # Only the first table (Daily Inventory Report 下載) — locate its <strong> cell
        inv_table_end = pane.find('Daily Order Report')
        if inv_table_end == -1:
            inv_table_end = min(len(pane), 6000)
        inv_seg = pane[:inv_table_end]
        strong_m = re.search(r'<strong>(\d{4}-\d{2}-\d{2})</strong>', inv_seg)
        if strong_m:
            html = html[:report_pane] + inv_seg[:strong_m.start()] + f'<strong>{report_date}</strong>' + inv_seg[strong_m.end():] + pane[inv_table_end:]
            print(f'📋 Report tab date updated to {report_date}')
        else:
            print('⚠️ Report tab date cell not found (no inventory report row?)')

    # 10. Subtitle (store name)
    html = html.replace('Hong Kong online Community pharmacy superstore', 'THANN')

    open(INDEX, 'w', encoding='utf-8').write(html)
    print(f'✅ index.html updated: {orig_len} → {len(html)} bytes')
    print(f'   KPI: {total_products} SKUs / {total_stock:,} stock | zero={zero_count} low={low_count} normal={normal_count} high={high_count}')
    print(f'   Online: {online_count} | Invisible Y: {inv_y} | FOOS Y: {foos_y} | New: {new_sku_count}')
    print(f'   Categories: {len(cat_type)} types / {len([k for k in cat_full if k and k != "nan"])} full')

if __name__ == '__main__':
    main()
