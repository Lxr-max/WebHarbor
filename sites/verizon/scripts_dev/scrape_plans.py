#!/usr/bin/env python3
"""Phase 3: capture the plans pages (real upstream).

Captures the postpaid Simplicity Plan page (line-count selector pricing,
plan features, discount terms) and the Verizon Prepaid plans page (plan
tiers, autopay / loyalty discount rules, price-lock guarantee, device
promo). Renders with headless Chromium because the plan widgets are
client-side, and steps the line selector 1-4 to record each price point.

Run: python3.11 scrape_plans.py
Output: scraped_data/plans.json, scraped_data/pages/plans_*.html
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


def get_text(page):
    return page.evaluate("() => document.body.innerText")


def snapshot(page, name):
    (OUT / "pages" / f"{name}.html").write_text(page.content(), encoding="utf-8")


def scrape_unlimited(page):
    page.goto("https://www.verizon.com/plans/unlimited/",
              wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(8000)
    snapshot(page, "plans_unlimited")
    result = {"url": "https://www.verizon.com/plans/unlimited/",
              "title": page.title(), "lines": {}}
    # step the line-count selector 1..4 and record the price shown
    for lines in (1, 2, 3, 4):
        try:
            btn = page.query_selector('button[aria-label*="quantity"], '
                                      'button[aria-label*="lines"], '
                                      'button:has-text("+")')
            if lines == 1:
                price = _price(get_text(page))
                result["lines"][lines] = price
            else:
                if btn:
                    btn.click()
                    page.wait_for_timeout(2500)
                price = _price(get_text(page))
                result["lines"][lines] = price
        except Exception as e:
            result["lines"][lines] = {"error": str(e)[:100]}
    text = get_text(page)
    result["full_text"] = text[:9000]
    return result


def _price(text):
    m = re.search(r"\$([0-9]{2,3})(?:\s*/month)?\s*\n?(\d+)?", text)
    out = {}
    pm = re.findall(r"\$([0-9]{2,3}(?:\.[0-9]{2})?)\s*(?:/month|/mo)", text)
    out["prices_seen"] = pm[:12]
    tm = re.search(r"Total quantity:\s*(\d+)", text)
    out["total_lines"] = tm.group(1) if tm else None
    dm = re.search(r"After AutoPay and \$([0-9]+)/mo switch discount", text)
    out["switch_discount"] = dm.group(1) if dm else None
    return out


def scrape_prepaid(page):
    page.goto("https://www.verizon.com/prepaid/plans/",
              wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(9000)
    snapshot(page, "prepaid_plans")
    text = get_text(page)
    result = {"url": "https://www.verizon.com/prepaid/plans/",
              "title": page.title(), "full_text": text[:16000]}
    # pull every plan card heading + price pair
    cards = page.evaluate(r"""() => {
      const out = [];
      document.querySelectorAll('[class*="plan" i], section, [class*="card" i]').forEach(s => {
        const t = (s.innerText || '').replace(/\s+/g, ' ').trim();
        const pm = t.match(/^\$?([0-9]{2,3})\/mo with Auto Pay/i) || t.match(/\$([0-9]{2,3})\/mo with Auto Pay/i);
        if (pm && t.length < 1400) {
          const head = (s.querySelector('h1,h2,h3,h4') || {}).textContent || '';
          out.push({head: head.trim().slice(0, 80), price: pm[1], text: t.slice(0, 1000)});
        }
      });
      return out;
    }""")
    result["cards"] = cards
    return result


def main():
    plans = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA, viewport={"width": 1440, "height": 3200})
        plans["unlimited"] = scrape_unlimited(page)
        plans["prepaid"] = scrape_prepaid(page)
        browser.close()
    (OUT / "plans.json").write_text(json.dumps(plans, indent=1), encoding="utf-8")
    print("[plans] captured unlimited + prepaid pages")


if __name__ == "__main__":
    main()
