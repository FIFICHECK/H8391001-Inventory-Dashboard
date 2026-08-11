#!/usr/bin/env python3
"""Merge ALL ECOM-EXCH_DAILY_ORDER_H8391001_*235959.xlsx into data/order_data.json (deep-merge)."""
import openpyxl, json, glob, os, re, sys
from collections import defaultdict

REPO = os.path.dirname(os.path.abspath(__file__))
XLSX_DIR = os.path.join(REPO, 'reports', 'order_reports')
OUT = os.path.join(REPO, 'data', 'order_data.json')

gmv_daily = defaultdict(float)
gmv_hourly = defaultdict(lambda: defaultdict(float))
gmv_sku_daily = defaultdict(lambda: defaultdict(float))
qty_sku_daily = defaultdict(lambda: defaultdict(float))
gmv_brand_daily = defaultdict(lambda: defaultdict(float))
order_count_daily = defaultdict(int)
sku_names = {}
brand_names = {}
sku_brand_map = {}

files = sorted(glob.glob(os.path.join(XLSX_DIR, 'ECOM-EXCH_DAILY_ORDER_H8391001_*235959.xlsx')))
print(f"Merging {len(files)} xlsx files...")

for f in files:
    try:
        wb = openpyxl.load_workbook(f, data_only=True)
        ws = wb.active
    except Exception as e:
        print(f"  SKIP {os.path.basename(f)}: {e}")
        continue
    for row in ws.iter_rows(min_row=6, values_only=True):
        order_date = row[6]
        order_time = row[7]
        sku_id_raw = row[17]
        brand_cn = row[19]
        qty = row[23]
        unit_price = row[24]
        discount = row[25]
        gmv = row[26]

        if not order_date or not sku_id_raw:
            continue
        date_str = str(order_date)[:10]
        if not date_str[:4].isdigit():
            continue  # filter "Order Date" header leak

        hour = 0
        if order_time:
            time_str = str(order_time)
            if ':' in time_str:
                try:
                    hour = int(time_str.split(':')[0])
                except Exception:
                    hour = 0

        full_sku = f'H8391001_S_{sku_id_raw}'
        try:
            qty_val = float(qty) if qty else 0
            price_val = float(unit_price) if unit_price else 0
            disc_val = float(discount) if discount else 0
            gmv_val = float(gmv) if gmv else (qty_val * price_val - disc_val)
        except Exception:
            gmv_val = 0

        gmv_daily[date_str] += gmv_val
        gmv_hourly[date_str][hour] += gmv_val
        gmv_sku_daily[full_sku][date_str] += gmv_val
        qty_sku_daily[full_sku][date_str] += qty_val
        brand = str(brand_cn) if brand_cn else 'Unknown'
        gmv_brand_daily[brand][date_str] += gmv_val
        order_count_daily[date_str] += 1
        sku_names[full_sku] = row[21] if row[21] else sku_names.get(full_sku, '')
        brand_names[brand] = brand
        sku_brand_map[full_sku] = brand

# --- Filter header leaks (per skill: "SKU brand (Chinese)" etc. leak into maps) ---
BAD_KEYS = {'SKU brand', 'SKU brand\n(Chinese)', 'SKU brand (Chinese)', 'H8391001_S_SKU ID',
            'Order Date', 'SKU Name', 'SKU Name\n(English)', 'SKU Name (English)'}
for coll in (brand_names,):
    for k in list(coll.keys()):
        if k in BAD_KEYS or 'SKU brand' in k or k == 'Unknown' and len(coll) > 1:
            del coll[k]
for coll in (sku_names, sku_brand_map, gmv_sku_daily, qty_sku_daily):
    for k in list(coll.keys()):
        if k in BAD_KEYS or 'SKU ID' in k:
            del coll[k]
for k in list(gmv_brand_daily.keys()):
    if k in BAD_KEYS or 'SKU brand' in k:
        del gmv_brand_daily[k]

output = {
    'gmv_daily': dict(gmv_daily),
    'gmv_hourly': {k: dict(v) for k, v in gmv_hourly.items()},
    'gmv_sku_daily': {k: dict(v) for k, v in gmv_sku_daily.items()},
    'qty_sku_daily': {k: dict(v) for k, v in qty_sku_daily.items()},
    'gmv_brand_daily': {k: dict(v) for k, v in gmv_brand_daily.items()},
    'order_count_daily': dict(order_count_daily),
    'sku_names': sku_names,
    'sku_brand_map': sku_brand_map,
    'brand_names': dict(brand_names),
    'generated': 'merge_all_235959'
}

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

days = sorted(gmv_daily.keys())
print(f"Orders: {sum(order_count_daily.values())}, GMV: ${sum(gmv_daily.values()):.2f}")
print(f"Days: {len(days)} ({days[0]} -> {days[-1]})")
print(f"SKUs: {len(sku_names)}, Brands: {len(brand_names)}")
