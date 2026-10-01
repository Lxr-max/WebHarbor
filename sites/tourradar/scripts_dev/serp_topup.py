#!/usr/bin/env python3
"""Targeted top-up: fetch /srp/d-europe and /srp/d-egypt, extract SERP cards
for tour ids 46923 / 251939 / 252256, verify presence, and merge:

  - serp_cards.json  : append parsed card dicts (deduped by tour_id)
  - tour_dests.json  : add the SERP slug(s) each tour appeared on

Only adds ids not already present; existing entries are never touched.
"""
import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from scrape_serp import CARD_JS, parse_card  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "scraped_data"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

WANT = {46923, 251939, 252256}
SLUGS = ["europe", "egypt"]


def main():
    cards = json.loads((OUT / "serp_cards.json").read_text())
    dests = json.loads((OUT / "tour_dests.json").read_text())
    have = {c["tour_id"] for c in cards}
    found = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000}, user_agent=UA, locale="en-US")
        page = ctx.new_page()
        for slug in SLUGS:
            url = f"https://www.tourradar.com/srp/d-{slug}?adults=2"
            got = set()
            for scroll_round in range(4):
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(7000)
                for _ in range(8):
                    page.mouse.wheel(0, 2500)
                    page.wait_for_timeout(900)
                page.mouse.wheel(0, 0)
                page.wait_for_timeout(800)
                for c in page.evaluate(CARD_JS):
                    if c["tour_id"] in WANT:
                        got.add(c["tour_id"])
                        found.setdefault(c["tour_id"], (slug, c))
                if got == WANT:
                    break
            print(f"[{slug}] wanted present: {sorted(got)}", flush=True)
        browser.close()

    added_cards = 0
    for tid, (slug, raw) in sorted(found.items()):
        if tid not in have:
            card = parse_card(raw)
            cards.append(card)
            have.add(tid)
            added_cards += 1
            print(f"card added for {tid}: {card.get('name','?')[:60]} price={card.get('price_current')}")
        slugs = dests.setdefault(str(tid), [])
        if slug not in slugs:
            slugs.append(slug)
            print(f"tour_dests[{tid}] += {slug} -> {slugs}")
    missing = WANT - set(found)
    if missing:
        print(f"MISSING from SERPs: {sorted(missing)}", flush=True)
        sys.exit(2)
    (OUT / "serp_cards.json").write_text(json.dumps(cards, indent=1))
    (OUT / "tour_dests.json").write_text(json.dumps(dests, indent=1))
    print(f"done: cards+={added_cards} total={len(cards)} dests={len(dests)}")


if __name__ == "__main__":
    main()
