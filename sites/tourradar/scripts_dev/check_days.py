#!/usr/bin/env python3
"""Re-scrape the itinerary days for one tour id (arg) and print Day-by-Day
titles, to check whether a flaky day block (e.g. 251939 Day 6) comes through
on a second pass. Does NOT write anything."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from scrape_tours import ITINERARY_JS, DAYS_JS, UA  # noqa: E402

from playwright.sync_api import sync_playwright

tid = int(sys.argv[1])
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000},
                              user_agent=UA, locale="en-US")
    page = ctx.new_page()
    page.goto(f"https://www.tourradar.com/t/{tid}",
              wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(7000)
    page.evaluate(ITINERARY_JS)
    page.wait_for_timeout(1200)
    days = page.evaluate(DAYS_JS)
    print("days:", len(days))
    for d in days:
        first = d['text'].split('\n')[:4]
        print(f" Day {d['day']}: {' | '.join(first)[:100]}")
    browser.close()
