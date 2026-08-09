#!/usr/bin/env python3
"""H8391001 Price Check data builder.
Matching strategy (strict, no fuzzy to avoid false positives):
  1. Exact SKU match: H8391001_S_<CODE> == official SKU (e.g. AW0117)
  2. Prefix match: SKU code starts with official SKU (e.g. AW0230FREEGIFT -> AW0230)
  3. Size-aware: only match when product size tokens agree (e.g. 320ml vs 60ml never match)
No match -> official_price = null, diff = null (dashboard shows '—')

Output: data/price_check_data.json
"""
import json, os, re, csv

REPO = os.path.expanduser('~/H8391001-Inventory-Dashboard')
os.chdir(REPO)

def load_inventory():
    path = 'data/inventory_all.csv'
    rows = []
    with open(path, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for r in reader:
            sku = r.get('Merchant SKU ID') or ''
            if not sku:
                continue
            rsp = (r.get('Original Price') or '').strip()
            psp = (r.get('Discount Price') or '').strip()
            rows.append({
                'sku': sku.strip(),
                'name_en': (r.get('SKU Name') or '').strip(),
                'name_chi': (r.get('SKU Name (Chi)') or '').strip(),
                'brand': (r.get('Brand Name (EN)') or r.get('Brand Name (CHI)') or '').strip(),
                'rsp': float(rsp) if rsp else None,
                'psp': float(psp) if psp else None,
                'stock': (r.get('StockLevel') or '').strip(),
                'status': (r.get('Online Status') or '').strip(),
            })
    return rows

def extract_size(name):
    """Extract size tokens like 320ML, 60ML, 100G, 40G from a name."""
    m = re.findall(r'(\d+(?:\.\d+)?)\s*(ML|G|GR|KG|L)', name, re.I)
    return [(float(v), u.upper()) for v, u in m]

def size_compatible(name1, name2):
    """Check if two product names have compatible sizes (both must agree if present)."""
    s1 = extract_size(name1)
    s2 = extract_size(name2)
    if not s1 or not s2:
        return True  # one side has no size info - allow (prefix matches handled separately)
    # allow if any size token overlaps
    for v1, u1 in s1:
        for v2, u2 in s2:
            if u1 == u2 and abs(v1 - v2) < 0.01:
                return True
    return False

def main():
    inv = load_inventory()
    with open('data/thann_official_prices.json', encoding='utf-8') as f:
        official = json.load(f)

    output = []
    exact = prefix = none = 0
    prefix_details = []
    for row in inv:
        sku = row['sku']
        m = re.match(r'H8391001_S_([A-Za-z0-9]+)', sku)
        code = m.group(1) if m else sku

        osku = None
        match_type = None

        if code in official:
            osku, match_type = code, 'exact'
        else:
            # prefix match: find official SKU that is a prefix of code
            # e.g. AW0230FREEGIFT -> AW0230 ; also AW0632A -> AW0632
            candidates = [s for s in official if code.startswith(s)]
            if candidates:
                # pick the longest matching prefix
                best = max(candidates, key=len)
                # verify size compatibility (unless it's a FREEGIFT/GWP which is same product)
                if size_compatible(row['name_en'], official[best]['name']) or 'FREEGIFT' in code.upper() or 'GWP' in code.upper():
                    osku, match_type = best, 'prefix'
                else:
                    prefix_details.append((code, row['name_en'][:40], best, official[best]['name'][:40], 'size-mismatch'))

        if osku:
            if match_type == 'exact':
                exact += 1
            else:
                prefix += 1
            op = official[osku]
            diff = round(row['psp'] - op['price'], 2) if row['psp'] and op['price'] else None
            row['official_sku'] = osku
            row['official_name'] = op['name']
            row['official_price'] = op['price']
            row['official_url'] = op['url']
            row['match_type'] = match_type
            row['diff'] = diff  # PSP - official
        else:
            none += 1
            row['official_sku'] = None
            row['official_name'] = None
            row['official_price'] = None
            row['official_url'] = None
            row['match_type'] = None
            row['diff'] = None

        output.append(row)

    with open('data/price_check_data.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Total: {len(output)} | exact: {exact} | prefix: {prefix} | no-match: {none}")
    if prefix_details:
        print(f"\n--- size-mismatch rejected ({len(prefix_details)}) ---")
        for d in prefix_details[:15]:
            print(f"  {d}")

    # Show a few good matches
    print("\n--- Sample matches ---")
    shown = 0
    for e in output:
        if e['official_sku'] and shown < 15:
            print(f"  {e['sku'][-15:]}: {e['name_en'][:35]} | PSP={e['psp']} 官網={e['official_price']} diff={e['diff']} [{e['match_type']}]")
            shown += 1

if __name__ == '__main__':
    main()
