#!/usr/bin/env python3
"""Phase 1: capture the live smartphones gridwall (real upstream).

Walks https://www.verizon.com/smartphones/ with headless Chromium, extracts
every product tile (#productDetails): device name, PDP href + sku, monthly
price, term, retail price, promo text, and the CDN image URL. Also captures
the full rendered HTML of the page for reference.

Run: python3.11 scrape_gridwall.py
Output: scraped_data/gridwall.json, scraped_data/pages/smartphones.html
"""
import json
import pathlib
import re

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "scraped_data"
(OUT / "pages").mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

EXTRACT = r"""() => {
  const tiles = [];
  const seen = new Set();
  document.querySelectorAll('#productDetails').forEach(tile => {
    const nameEl = tile.querySelector('#gridwallProductName a');
    if (!nameEl) return;
    const name = (nameEl.getAttribute('title') || nameEl.textContent || '').trim();
    const href = nameEl.getAttribute('href') || '';
    if (!name || seen.has(href)) return;
    seen.add(href);
    const img = tile.querySelector('img');
    const imgSrc = img ? (img.getAttribute('src') || '') : '';
    const text = tile.innerText.replace(/\s+/g, ' ');
    const monthly = (text.match(/\$([0-9,]+\.[0-9]{2})\s*(?:\/mo|per month)/) || [])[1];
    const retail = (text.match(/Retail price:\s*\$([0-9,]+\.[0-9]{2})/) || [])[1];
    const term = (text.match(/for (\d+) months, 0% APR/) || [])[1];
    const promo = (tile.querySelector('[class*="promo" i]') || {}).textContent || '';
    tiles.push({name, href, img: imgSrc, monthly, retail, term,
                promo: promo.trim().replace(/\s+/g, ' ')});
  });
  return tiles;
}"""


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA, viewport={"width": 1440, "height": 4000})
        page.goto("https://www.verizon.com/smartphones/",
                  wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(12000)
        tiles = page.evaluate(EXTRACT)
        html = page.content()
        (OUT / "pages" / "smartphones.html").write_text(html, encoding="utf-8")
        browser.close()

    # split sku out of the PDP href
    for t in tiles:
        m = re.search(r"/smartphones/([a-z0-9-]+)/?\?sku=([a-z0-9]+)", t["href"])
        if m:
            t["slug"], t["sku"] = m.group(1), m.group(2)
        else:
            m = re.search(r"/smartphones/([a-z0-9-]+)/?", t["href"])
            t["slug"], t["sku"] = (m.group(1) if m else ""), ""
    (OUT / "gridwall.json").write_text(json.dumps(tiles, indent=1), encoding="utf-8")
    print(f"[gridwall] captured {len(tiles)} device tiles")


if __name__ == "__main__":
    main()
