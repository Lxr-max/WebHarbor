#!/usr/bin/env python3
"""Phase 2: harvest every form's fee-calculator record.

The public fee calculator at /feecalculator is a Drupal view: selecting a
form in the dropdown issues a views/ajax request and renders the G-1055 fee
rows for that form. The styled combobox lags one selection behind when driven
synthetically, so we reload the page per form and verify the rendered block
matches the selected label before capturing it.

Run:  python3.11 scrape_fee_api.py
"""
import json
import pathlib
import time

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "scraped_data" / "fees"
OUT.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
URL = "https://www.uscis.gov/feecalculator"


def parse_rows(html: str) -> list[dict]:
    """Fee rows from the rendered detail block (Filing Category | fees...)."""
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for table in soup.find_all("table"):
        headers = [" ".join(th.get_text(" ", strip=True).split()) for th in table.find_all("th")]
        for tr in table.find_all("tr"):
            cells = [" ".join(td.get_text(" ", strip=True).split()) for td in tr.find_all("td")]
            if cells and any(cells):
                rows.append({"headers": headers, "cells": cells})
    return rows


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(user_agent=UA, viewport={"width": 1366, "height": 1000})
        page = ctx.new_page()
        page.goto(URL, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        opts = page.eval_on_selector_all(
            "select#form-fee-title option",
            "els => els.map(o => ({v: o.value, t: o.text.trim()}))",
        )
        opts = [o for o in opts if o["v"]]
        print(f"{len(opts)} form options")
        ok = 0
        for idx, opt in enumerate(opts):
            nid, label = opt["v"], opt["t"]
            out_path = OUT / f"{nid}.json"
            captured = False
            for attempt in range(3):
                try:
                    page.goto(URL, timeout=60000, wait_until="domcontentloaded")
                    page.wait_for_timeout(1800 + 500 * attempt)
                    page.evaluate(
                        """([sel, val]) => {
                            const s = document.querySelector(sel);
                            s.value = val;
                            s.dispatchEvent(new Event('change', {bubbles: true}));
                        }""",
                        ["select#form-fee-title", nid],
                    )
                    # wait for the rendered block to name this form
                    for _ in range(12):
                        page.wait_for_timeout(500)
                        txt = page.inner_text("main")
                        if label[:40] in txt and "Select a form to view details" not in txt:
                            captured = True
                            break
                    if captured:
                        html = page.inner_html("main")
                        text = page.inner_text("main")
                        rec = {
                            "nid": nid, "label": label, "text": text,
                            "rows": parse_rows(html),
                        }
                        out_path.write_text(json.dumps(rec, indent=1))
                        ok += 1
                        if idx % 20 == 0:
                            print(f"  {idx}: {label[:58]} rows={len(rec['rows'])}")
                        break
                except Exception as exc:
                    print(f"  ERR {label[:40]}#{attempt}: {str(exc)[:80]}")
            if not captured:
                print(f"  FAIL {label[:60]}")
            time.sleep(0.2)
        (ROOT / "scraped_data" / "fees_index.json").write_text(
            json.dumps([{"nid": o["v"], "label": o["t"]} for o in opts], indent=1)
        )
        browser.close()
        print(f"done ok={ok}/{len(opts)}")


if __name__ == "__main__":
    main()
