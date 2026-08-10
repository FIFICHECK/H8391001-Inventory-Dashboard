#!/usr/bin/env python3
"""
align_sales_trend_to_csv.py — Align sales_trend_data.js to the user's by_sku CSV.

Run AFTER regenerate_sales_trend.py (which produces raw Exchange-based data).
This script applies:
1. Monthly charts (gmv_by_month / gmv_by_sku_monthly / qty_by_sku_monthly /
   gmv_by_brand_monthly) → CSV monthly values (authoritative).
2. Per-month scaling of daily data (gmv_by_date, gmv_by_sku_daily, qty_by_sku_daily,
   gmv_by_brand_daily, gmv_by_day_of_week, gmv_by_date_hour) so each month sums
   exactly to the CSV total.
3. Rounding-residual normalization (normalize_monthly) — every month matches to the CENT.
4. 其他 Others aggregate row for daily SKU charts (top-50 tail).
5. Qty integer normalization.
6. Summary block: total_gmv = CSV 1-7 + Exchange Aug; this/last/month_before_last.

Usage: python3 scripts/align_sales_trend_to_csv.py
Reads: data/sales_trend_data.js, <by_sku_csv path> (arg or default cache path)
Writes: data/sales_trend_data.js (same filename as regenerate_sales_trend.py)
"""
import json
import os
import re
import sys
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_JS = os.path.join(REPO, 'data/sales_trend_data.js')
DEFAULT_CSV = '/home/snkwok/.hermes/profiles/hermes1/cache/documents/doc_e8b50865f63f_by_sku_-_2026-08-10T120958.438.csv'
CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV

# Months present in CSV (Jan-Jul 2026). Aug stays Exchange-sourced.
CSV_MONTHS = ['2026-01', '2026-02', '2026-03', '2026-04', '2026-05', '2026-06', '2026-07']
ALL_MONTHS = CSV_MONTHS + ['2026-08']


def load_csv_monthly(path):
    """Parse user by_sku CSV (UTF-16 LE tab-delimited) → {month: {sku: {gmv, orders, qty}}}."""
    import csv
    import io
    raw = open(path, 'rb').read()
    text = raw.decode('utf-16')
    reader = csv.reader(io.StringIO(text), delimiter='\t')
    rows = list(reader)
    monthly = {}
    for i, m in enumerate(CSV_MONTHS):
        monthly[m] = {}
        for r in rows[2:]:
            if len(r) < 38 or not r[1].strip():
                continue
            sku = r[1]

            def num(v):
                if not v or not v.strip():
                    return 0
                return float(v.replace(',', ''))

            g = num(r[9 + i])
            o = num(r[23 + i])
            q = num(r[30 + i])
            if g or o or q:
                monthly[m][sku] = {'gmv': g, 'orders': o, 'qty': q}
    return monthly


def load_data():
    js = open(DATA_JS, encoding='utf-8').read()
    m = re.search(r'const salesTrendData = (\{.*?\});\s*$', js, re.S)
    return json.loads(m.group(1)), js


def save_data(data):
    out = 'const salesTrendData = ' + json.dumps(data, ensure_ascii=False) + ';\n'
    open(DATA_JS, 'w', encoding='utf-8').write(out)


def normalize_monthly(targets, labels, vals):
    """Adjust per-day values so each month's sum exactly equals the target."""
    month_idx = defaultdict(list)
    for i, d in enumerate(labels):
        month_idx[d[:7]].append(i)
    out = list(vals)
    for mth, idxs in month_idx.items():
        if mth not in targets:
            continue
        target = targets[mth]
        cur = sum(out[i] for i in idxs)
        diff = round(target - cur, 2)
        if abs(diff) < 0.005:
            continue
        big = max(idxs, key=lambda i: out[i])
        out[big] = round(out[big] + diff, 2)
        new_sum = sum(out[i] for i in idxs)
        if abs(new_sum - target) > 0.005:
            for cand in sorted(idxs, key=lambda i: -out[i])[1:]:
                diff2 = round(target - sum(out[i] for i in idxs), 2)
                if abs(diff2) < 0.005:
                    break
                out[cand] = round(out[cand] + diff2, 2)
    return out


def main():
    if not os.path.exists(CSV_PATH):
        print(f'⚠️ by_sku CSV not found ({CSV_PATH}) — skipping CSV alignment (keeping Exchange-based data)')
        return
    csv_monthly = load_csv_monthly(CSV_PATH)
    data, js = load_data()

    csv_totals = {mth: round(sum(v['gmv'] for v in skus.values()), 2)
                  for mth, skus in csv_monthly.items()}
    csv_orders = {mth: round(sum(v['orders'] for v in skus.values()))
                  for mth, skus in csv_monthly.items()}
    csv_qty = {mth: round(sum(v['qty'] for v in skus.values()))
               for mth, skus in csv_monthly.items()}

    # --- 1. Monthly charts from CSV (Aug from Exchange) ---
    aug_idx = data['gmv_by_month']['labels'].index('2026-08') if '2026-08' in data['gmv_by_month']['labels'] else None
    aug_gmv = round(sum(v for d, v in zip(data['gmv_by_date']['labels'], data['gmv_by_date']['data'])
                        if d.startswith('2026-08')), 2)
    aug_orders = data['summary']['this_month']['orders']
    month_gmv = [csv_totals.get(m, 0) for m in CSV_MONTHS] + [aug_gmv]
    month_orders = [csv_orders.get(m, 0) for m in CSV_MONTHS] + [aug_orders]
    data['gmv_by_month'] = {'labels': ALL_MONTHS, 'data': month_gmv}

    # gmv_by_sku_monthly from CSV per-SKU (all CSV SKUs), Aug from Exchange daily
    all_skus = sorted(set().union(*[set(s.keys()) for s in csv_monthly.values()]))
    labels = data['gmv_by_date']['labels']
    exch_skus = data['gmv_by_sku_daily']['skus']
    sd = data['gmv_by_sku_daily']
    qd = data['qty_by_sku_daily']
    aug_sku_gmv = defaultdict(float)
    aug_sku_qty = defaultdict(float)
    for di, dl in enumerate(sd['labels']):
        if dl.startswith('2026-08'):
            for si, sku in enumerate(exch_skus):
                aug_sku_gmv[sku] += sd['data'][di][si]
                aug_sku_qty[sku] += qd['data'][di][si]

    sku_monthly_data, qty_monthly_data = [], []
    for mth in ALL_MONTHS:
        g_row, q_row = [], []
        for sku in all_skus:
            if mth in csv_monthly:
                g_row.append(round(csv_monthly[mth].get(sku, {}).get('gmv', 0), 2))
                q_row.append(round(csv_monthly[mth].get(sku, {}).get('qty', 0), 2))
            else:
                g_row.append(round(aug_sku_gmv.get(sku, 0), 2))
                q_row.append(round(aug_sku_qty.get(sku, 0), 2))
        sku_monthly_data.append(g_row)
        qty_monthly_data.append(q_row)
    data['gmv_by_sku_monthly'] = {'labels': ALL_MONTHS, 'skus': all_skus, 'data': sku_monthly_data}
    data['qty_by_sku_monthly'] = {'labels': ALL_MONTHS, 'skus': all_skus, 'data': qty_monthly_data}
    data['gmv_by_brand_monthly'] = {'labels': ALL_MONTHS, 'brands': ['THANN'],
                                    'data': [[round(g, 2)] for g in month_gmv]}

    # --- 2. Per-month scale factors ---
    exchange_month = defaultdict(float)
    for d, v in zip(labels, data['gmv_by_date']['data']):
        exchange_month[d[:7]] += v
    scale = {}
    for mth in csv_totals:
        ex = exchange_month.get(mth, 0)
        scale[mth] = csv_totals[mth] / ex if ex else 1.0

    # --- 3. Scale daily GMV ---
    new_gmv = []
    for d, v in zip(labels, data['gmv_by_date']['data']):
        mth = d[:7]
        new_gmv.append(round(v * scale[mth], 2) if mth in scale else v)
    data['gmv_by_date']['data'] = new_gmv
    data['gmv_by_date']['data'] = normalize_monthly(csv_totals, labels, new_gmv)

    # --- 4. Scale daily SKU data + qty ---
    for key in ['gmv_by_sku_daily', 'qty_by_sku_daily']:
        sku_data = data[key]['data']
        new_sku = []
        for di, dl in enumerate(sku_data):
            mth = data[key]['labels'][di][:7]
            if mth in scale:
                new_sku.append([round(v * scale[mth], 2) for v in dl])
            else:
                new_sku.append(dl)
        data[key]['data'] = new_sku

    # --- 5. 其他 Others row for daily SKU charts ---
    for key, total_key in [('gmv_by_sku_daily', 'gmv_by_date'), ('qty_by_sku_daily', None)]:
        sku_data = data[key]
        oi = sku_data['skus'].index('其他 Others') if '其他 Others' in sku_data['skus'] else None
        if oi is None:
            sku_data['skus'] = sku_data['skus'] + ['其他 Others']
            oi = len(sku_data['skus']) - 1
            for di in range(len(sku_data['data'])):
                sku_data['data'][di] = sku_data['data'][di] + [0.0]
        for di, dl in enumerate(sku_data['labels']):
            mth = dl[:7]
            top_sum = sum(sku_data['data'][di][:oi])
            if key == 'gmv_by_sku_daily':
                total = data['gmv_by_date']['data'][di]
            else:
                if mth in csv_qty:
                    ex_qty = 0
                    for di2, dl2 in enumerate(sku_data['labels']):
                        if dl2.startswith(mth):
                            ex_qty += sum(data['qty_by_sku_daily']['data'][di2][:oi])
                    factor = csv_qty[mth] / ex_qty if ex_qty else 1.0
                    total = sum(data['qty_by_sku_daily']['data'][di][:oi]) * factor
                else:
                    total = sum(data['qty_by_sku_daily']['data'][di][:oi])
            sku_data['data'][di][oi] = round(total - top_sum, 2)

    # --- 6. DayOfWeek re-aggregate (7 days) + scale ---
    DAY_EN = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    DAY_CN = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    # Rebuild from scaled gmv_by_date
    dow_agg = [0.0] * 7
    from datetime import datetime
    for d, v in zip(labels, data['gmv_by_date']['data']):
        dt = datetime.strptime(d, '%Y-%m-%d')
        wd = (dt.weekday() + 1) % 7  # Mon=0
        dow_agg[wd] += v
    data['gmv_by_day_of_week'] = {'labels': [f'{DAY_CN[i]} {DAY_EN[i]}' for i in range(7)],
                                  'data': [round(v, 2) for v in dow_agg]}

    # --- 7. Hourly scale (per-date proportional + residual) ---
    dh = data['gmv_by_date_hour']
    norm_daily = dict(zip(labels, data['gmv_by_date']['data']))
    for ds, arr in dh['data'].items():
        target = norm_daily.get(ds)
        if target is None:
            continue
        cur = sum(arr)
        if abs(cur - target) > 0.005:
            if cur > 0:
                f = target / cur
                arr = [round(v * f, 2) for v in arr]
            diff = round(target - sum(arr), 2)
            if abs(diff) > 0.004:
                big = max(range(24), key=lambda h: arr[h])
                arr[big] = round(arr[big] + diff, 2)
            dh['data'][ds] = arr
    hour_totals = [0.0] * 24
    for ds, arr in dh['data'].items():
        for h in range(24):
            hour_totals[h] += arr[h]
    data['gmv_by_hour']['data'] = [round(v, 2) for v in hour_totals]

    # --- 8. Brand daily scale ---
    bd = data['gmv_by_brand_daily']
    for mth, target in csv_totals.items():
        idxs = [i for i, d in enumerate(bd['labels']) if d.startswith(mth)]
        if not idxs:
            continue
        cur = sum(sum(bd['data'][i]) for i in idxs)
        diff = round(target - cur, 2)
        if abs(diff) < 0.005:
            continue
        big = max(idxs, key=lambda i: sum(bd['data'][i]))
        bd['data'][big][0] = round(bd['data'][big][0] + diff, 2)

    # --- 9. Qty integer normalization (daily) ---
    qd = data['qty_by_sku_daily']
    for i in range(len(qd['data'])):
        qd['data'][i] = [round(v) for v in qd['data'][i]]
    oi = qd['skus'].index('其他 Others')
    for mth, target in csv_qty.items():
        idxs = [i for i, d in enumerate(qd['labels']) if d.startswith(mth)]
        if not idxs:
            continue
        cur = sum(sum(qd['data'][i]) for i in idxs)
        diff = target - cur
        if diff == 0:
            continue
        big = max(idxs, key=lambda i: qd['data'][i][oi])
        qd['data'][big][oi] = qd['data'][big][oi] + diff

    # --- 10. Summary ---
    total_gmv = round(sum(csv_totals.values()) + aug_gmv, 2)
    total_orders = sum(csv_orders.values()) + aug_orders
    data['summary']['total_gmv'] = total_gmv
    data['summary']['total_orders'] = total_orders
    data['summary']['avg_order_value'] = round(total_gmv / total_orders, 2) if total_orders else 0
    data['summary']['date_range'] = '2026-01-01 to 2026-08-09'
    data['summary']['this_month'] = {'label': '2026-08', 'gmv': aug_gmv, 'orders': aug_orders,
                                     'avg': round(aug_gmv / aug_orders, 2) if aug_orders else 0}
    data['summary']['last_month'] = {'label': '2026-07', 'gmv': csv_totals['2026-07'],
                                     'orders': csv_orders['2026-07'],
                                     'avg': round(csv_totals['2026-07'] / csv_orders['2026-07'], 2)}
    data['summary']['month_before_last'] = {'label': '2026-06', 'gmv': csv_totals['2026-06'],
                                            'orders': csv_orders['2026-06'],
                                            'avg': round(csv_totals['2026-06'] / csv_orders['2026-06'], 2)}

    save_data(data)
    print(f'✅ aligned: total ${total_gmv:,.2f} / {total_orders} orders')
    for mth in ALL_MONTHS:
        tot = data['gmv_by_month']['data'][data['gmv_by_month']['labels'].index(mth)]
        csv_v = csv_totals.get(mth, 0)
        mark = '✅' if abs(tot - csv_v) < 0.005 else '❌'
        print(f'  {mth}: ${tot:,.2f} vs CSV ${csv_v:,.2f} {mark}')


if __name__ == '__main__':
    main()
