#!/usr/bin/env python3
"""Phase 5b: capture client-rendered content pages (real upstream).

The Verizon home page and the support Contact Us page are client-rendered
widgets; plain fetches return an empty shell, so render them with headless
Chromium and capture the visible text (plus the rendered HTML for the
image collector).

Run: python3.11 scrape_js_pages.py
Output: scraped_data/js_pages.json, scraped_data/pages/js_*.html
"""
import json
import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "scraped_data"
(OUT / "pages").mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

PAGES = {
    "home": "https://www.verizon.com/",
    "contact_us": "https://www.verizon.com/support/contact-us/",
    "support_home": "https://www.verizon.com/support/",
    "troubleshoot": "https://www.verizon.com/support/devices/",
    "stores_home": "https://www.verizon.com/stores/",
    "plans_home": "https://www.verizon.com/plans/",
    "deals": "https://www.verizon.com/loyalty/",
    "accessories": "https://www.verizon.com/accessories-verizon/",
}


def main():
    pages = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA, viewport={"width": 1440, "height": 3600})
        for name, url in PAGES.items():
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(8000)
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(1500)
                text = page.evaluate("() => document.body.innerText")
                (OUT / "pages" / f"js_{name}.html").write_text(
                    page.content(), encoding="utf-8")
                pages[name] = {"url": url, "title": page.title(),
                               "text": text[:22000]}
                print(f"[js] {name}: {len(text)} chars, title={page.title()[:60]}")
            except Exception as e:
                print(f"[js] FAIL {name}: {str(e)[:110]}")
        browser.close()
    (OUT / "js_pages.json").write_text(json.dumps(pages, indent=1), encoding="utf-8")
    print(f"[js] captured {len(pages)} pages")


if __name__ == "__main__":
    main()
