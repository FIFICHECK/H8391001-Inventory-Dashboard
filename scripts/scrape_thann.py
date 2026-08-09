#!/usr/bin/env python3
"""Scrape THANN official site (thann.com.hk) - all product categories -> JSON.
Magento 2 site. curl blocked (HTTP 000), Playwright works.
"""
import asyncio, json, re, sys
from playwright.async_api import async_playwright

CATEGORIES = [
    "https://thann.com.hk/category/aromatherpy/aroma-diffuser.html",
    "https://thann.com.hk/category/aromatherpy/candle.html",
    "https://thann.com.hk/category/aromatherpy/essential-oil.html",
    "https://thann.com.hk/category/aromatherpy/fragrance-mist.html",
    "https://thann.com.hk/category/body/bath-massage-oils.html",
    "https://thann.com.hk/category/body/body-moisturizers.html",
    "https://thann.com.hk/category/body/body-scrubs.html",
    "https://thann.com.hk/category/body/body-soap.html",
    "https://thann.com.hk/category/body/shower-gel-shower-cream.html",
    "https://thann.com.hk/category/body/solid-perfume-time-to-refresh.html",
    "https://thann.com.hk/category/hair/conditioner.html",
    "https://thann.com.hk/category/hair/shampoo.html",
    "https://thann.com.hk/category/hair/treatment.html",
    "https://thann.com.hk/category/face-and-lips/cleanser.html",
    "https://thann.com.hk/category/face-and-lips/lip-care.html",
    "https://thann.com.hk/category/face-and-lips/masks.html",
    "https://thann.com.hk/category/face-and-lips/scrub-clay-mask.html",
    "https://thann.com.hk/category/face-and-lips/serums-cream.html",
    "https://thann.com.hk/category/face-and-lips/sunscreen.html",
    "https://thann.com.hk/category/face-and-lips/toner.html",
    # collections (aroma-themed ranges)
    "https://thann.com.hk/collection/aromatic-wood.html",
    "https://thann.com.hk/collection/oriental-essence.html",
    "https://thann.com.hk/collection/eden-breeze.html",
    "https://thann.com.hk/collection/eastern-orchard.html",
    "https://thann.com.hk/collection/earl-gray-infusion.html",
    "https://thann.com.hk/collection/rice.html",
    "https://thann.com.hk/collection/shiso.html",
    "https://thann.com.hk/collection/limited-edition.html",
]

async def scrape_page(page, url):
    """Extract products from a category page (handles pagination via ?p=2 etc)."""
    products = {}
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=45000)
        await page.wait_for_timeout(2500)
    except Exception as e:
        print(f"  !! goto failed {url}: {e}", flush=True)
        return products

    # extract items from current page
    items = await page.evaluate("""() => {
        const out = [];
        document.querySelectorAll('li.product-item, li.item.product').forEach(li => {
            const name = (li.querySelector('.product-item-link, .product.name a, strong a') || {}).textContent || '';
            const priceEl = li.querySelector('.price');
            const price = priceEl ? priceEl.textContent.trim() : '';
            const linkEl = li.querySelector('a.product-item-link, .product.name a, .product photo');
            const link = linkEl ? linkEl.href.split('?')[0] : '';
            const form = li.querySelector('form[data-product-sku]');
            const sku = form ? form.getAttribute('data-product-sku') : '';
            out.push({name: name.trim(), price, link, sku});
        });
        return out;
    }""")
    for it in items:
        if it['name'] and it['price']:
            m = re.search(r'([\d,]+\.?\d*)', it['price'].replace(',', ''))
            price_val = float(m.group(1)) if m else None
            key = it['sku'] or it['link'].split('/')[-1].replace('.html', '')
            products[key] = {
                'name': it['name'],
                'price': price_val,
                'price_display': it['price'],
                'url': it['link'],
                'sku': it['sku'],
            }

    # pagination: check for pages
    try:
        pages = await page.evaluate("""() => {
            const links = [];
            document.querySelectorAll('.pages a, .pagination a, .items.pages-items a').forEach(a => {
                const href = a.getAttribute('href');
                if (href && /[?&]p=\\d+/.test(href)) links.push(href.split('?')[0] + '?' + href.split('?')[1]);
            });
            return [...new Set(links)];
        }""")
    except Exception:
        pages = []
    return products, pages

async def main():
    all_products = {}
    seen_urls = set()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            viewport={'width': 1440, 'height': 900},
            locale='en-US',
        )
        page = await ctx.new_page()
        for cat_url in CATEGORIES:
            print(f"Scraping {cat_url}", flush=True)
            queue = [cat_url]
            while queue:
                u = queue.pop(0)
                if u in seen_urls:
                    continue
                seen_urls.add(u)
                products, pages = await scrape_page(page, u)
                for k, v in products.items():
                    all_products.setdefault(k, v)
                # add pagination pages
                for p_url in pages:
                    if p_url not in seen_urls:
                        queue.append(p_url)
            await page.wait_for_timeout(800)
        await browser.close()

    print(f"\n=== TOTAL: {len(all_products)} products ===")
    for sku in sorted(all_products)[:10]:
        p = all_products[sku]
        print(f"  {sku}: {p['name'][:50]} | {p['price_display']} | {p['url']}")

    with open('/tmp/thann_official_products.json', 'w', encoding='utf-8') as f:
        json.dump(all_products, f, ensure_ascii=False, indent=2)
    print("Saved /tmp/thann_official_products.json")

asyncio.run(main())
