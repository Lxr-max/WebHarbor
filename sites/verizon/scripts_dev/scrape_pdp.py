#!/usr/bin/env python3
"""Phase 2: capture device PDPs (real upstream structured data).

For every gridwall device, open its PDP (?sku=...) and extract:
color options, storage options, payment-term grid (12/24/36/48-month
prices + full retail), current color/storage pricing, ship-window text,
promo banners, the spec-compare rows (battery / screen / camera / storage
/ reviews), rating, and the gallery image URLs.

Run: python3.11 scrape_pdp.py
Output: scraped_data/devices.json, scraped_data/pages/pdp/<slug>.html
"""
import json
import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "scraped_data"
(OUT / "pages" / "pdp").mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# NOTE: this is a plain (non-raw) Python string; every backslash below is
# written as a JS-source single backslash, so the browser receives the
# intended regex literals.
EXTRACT = r"""() => {
  const text = document.body.innerText;
  const pick = (re) => { const m = text.match(re); return m ? m[1].trim() : null; };
  const colors = [];
  document.querySelectorAll('[aria-label^="Color "]').forEach(e => {
    const t = (e.getAttribute('aria-label') || '').replace(/^Color\s+/, '').trim();
    if (t && !colors.includes(t)) colors.push(t);
  });
  const storage = [];
  document.querySelectorAll('button, [role="button"], label, input[type="radio"]').forEach(e => {
    const t = (e.textContent || e.value || '').trim();
    const m = t.match(/^(\d+\s?(GB|TB))\b/);
    if (m && !storage.includes(m[1])) storage.push(m[1]);
  });
  const terms = {};
  [12, 24, 36, 48].forEach(mo => {
    const m = text.match(new RegExp(mo + ' mos\\s*\\$([0-9,]+\\.[0-9]{2})/mo'));
    if (m) terms[mo] = m[1];
  });
  const full = pick(/Pay in full today\s*\$([0-9,]+\.[0-9]{2})/);
  const promo = [];
  document.querySelectorAll('[class*="promo" i], [class*="badge" i]').forEach(e => {
    const t = (e.textContent || '').trim().replace(/\s+/g, ' ');
    if (t && t.length < 140 && !promo.includes(t)) promo.push(t);
  });
  const savings = pick(/\$([0-9]+) savings/);
  const ship = pick(/Ships between ([^\n]+)/);
  const rating = pick(/([0-9.]+) out of 5 rating/);
  const reviews = pick(/\(([0-9.,K]+) reviews\)/);
  const imgs = [];
  document.querySelectorAll('img').forEach(i => {
    const src = i.currentSrc || i.src || '';
    const alt = i.alt || '';
    if (src.indexOf('ss7.vzw.com/is/image/') >= 0) {
      const clean = src.split('?')[0];
      if (!imgs.find(x => x.src === clean)) imgs.push({src: clean, alt});
    }
  });
  const specs = {};
  document.querySelectorAll('h3, h2').forEach(h => {
    const t = (h.textContent || '').trim();
    if (!/^(Battery life|Screen|Camera|Reviews|Storage)$/.test(t)) return;
    const block = h.parentElement;
    if (!block) return;
    const bt = (block.innerText || '').replace(/\s+/g, ' ').trim();
    specs[t] = bt.slice(0, 1000);
  });
  return {colors, storage, terms, full, promo: promo.slice(0, 8), savings,
          ship, rating, reviews, imgs: imgs.slice(0, 24), specs};
}"""

GALLERY_IMGS = r"""() => {
  const imgs = [];
  document.querySelectorAll('img').forEach(i => {
    const src = i.currentSrc || i.src || '';
    if (src.indexOf('ss7.vzw.com/is/image/') >= 0) {
      const clean = src.split('?')[0];
      if (!imgs.includes(clean)) imgs.push(clean);
    }
  });
  return imgs;
}"""


def main():
    gridwall = json.loads((OUT / "gridwall.json").read_text())
    devices = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA, viewport={"width": 1440, "height": 3200})
        for tile in gridwall:
            url = tile["href"]
            if not url.startswith("https"):
                url = "https://www.verizon.com" + url
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(9000)
                page.mouse.wheel(0, 1600)
                page.wait_for_timeout(1500)
                data = page.evaluate(EXTRACT)
                data['color_images'] = {}
                for color in list(data.get('colors') or [])[:8]:
                    try:
                        page.click(f'[aria-label="Color {color}"]', timeout=8000)
                        page.wait_for_timeout(2200)
                        shots = page.evaluate(GALLERY_IMGS)
                        keep = shots[:6] if not data['color_images'] else shots[:2]
                        data['color_images'][color] = keep
                    except Exception:
                        pass
                if data.get('colors'):
                    try:
                        page.click(f'[aria-label="Color {data["colors"][0]}"]', timeout=8000)
                        page.wait_for_timeout(1200)
                    except Exception:
                        pass
                data.update({
                    "name": tile["name"], "slug": tile["slug"], "sku": tile["sku"],
                    "grid_monthly": tile.get("monthly"),
                    "grid_retail": tile.get("retail"),
                    "title": page.title(),
                })
                devices.append(data)
                (OUT / "pages" / "pdp" / f"{tile['slug']}.html").write_text(
                    page.content(), encoding="utf-8")
                print(f"[pdp] {tile['name'][:44]}: colors={len(data['colors'])} "
                      f"storage={data['storage']} terms={data['terms']} full={data['full']}")
            except Exception as e:
                print(f"[pdp] FAIL {tile['name']}: {str(e)[:120]}")
                devices.append({"name": tile["name"], "slug": tile["slug"],
                                "sku": tile["sku"], "error": str(e)[:200]})
        browser.close()
    (OUT / "devices.json").write_text(json.dumps(devices, indent=1), encoding="utf-8")
    print(f"[pdp] captured {len(devices)} devices")


if __name__ == "__main__":
    main()
