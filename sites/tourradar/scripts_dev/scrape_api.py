#!/usr/bin/env python3
"""API pass: fetch structured payloads for every scraped tour.

For each tour id in tour_progress.jsonl, opens /t/<id> once and fetches the
same-site JSON endpoints the live page calls:

  /api/tours/<id>/itineraries-descriptions   day descriptions, city names, intro
  /api/tour-atlas/tours/<id>/comparison      structured tour facts
  /api/tdp/best-price/all-months-prices/<id> monthly price grid

Results append to scraped_data/api/<id>.json. Skips ids already done.
"""
import json
import pathlib
import random
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRAPE = ROOT / 'scraped_data'
API = SCRAPE / 'api'
API.mkdir(exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

FETCH_JS = """async (tid) => {
  const get = async (ep) => {
    try {
      const r = await fetch(ep, {credentials: 'include'});
      const ct = r.headers.get('content-type') || '';
      if (!ct.includes('json')) return null;
      return await r.json();
    } catch (e) { return null; }
  };
  const itin = await get(`/api/tours/${tid}/itineraries-descriptions`);
  const comp = await get(`/api/tour-atlas/tours/${tid}/comparison`);
  const months = await get(`/api/tdp/best-price/all-months-prices/${tid}`);
  return {itineraries: itin, comparison: comp, best_months: months};
}"""


def main():
    ids = []
    progress = SCRAPE / 'tour_progress.jsonl'
    for line in progress.read_text().splitlines():
        try:
            rec = json.loads(line)
            if rec.get('title') and rec['title'] != '403 Forbidden':
                ids.append(rec['tour_id'])
        except Exception:
            pass
    ids = sorted(set(ids))
    todo = [i for i in ids if not (API / f"{i}.json").exists()]
    print(f"tours with progress: {len(ids)}, todo: {len(todo)}", flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True,
                                    args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000},
                                  user_agent=UA, locale="en-US")
        page = ctx.new_page()
        backoff = 0
        for n, tid in enumerate(todo):
            while True:
                try:
                    page.goto(f"https://www.tourradar.com/t/{tid}",
                              wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(5000)
                    title = page.title()
                    if '403' in title or '410' in title:
                        backoff += 1
                        wait = min(900, 240 * backoff) + random.random() * 60
                        print(f"[t/{tid}] blocked; backing off {int(wait)}s", flush=True)
                        time.sleep(wait)
                        try:
                            ctx.close()
                        except Exception:
                            pass
                        ctx = browser.new_context(
                            viewport={"width": 1440, "height": 1000},
                            user_agent=UA, locale="en-US")
                        page = ctx.new_page()
                        continue
                    backoff = 0
                    data = page.evaluate(FETCH_JS, tid)
                    if not data or (not data.get('itineraries')
                                    and not data.get('comparison')):
                        print(f"[t/{tid}] no api data", flush=True)
                    else:
                        (API / f"{tid}.json").write_text(json.dumps(data))
                        print(f"[t/{tid}] ok ({n + 1}/{len(todo)})", flush=True)
                    break
                except Exception as e:
                    print(f"[t/{tid}] ERR {str(e)[:80]}", flush=True)
                    time.sleep(15)
            time.sleep(4 + random.random() * 6)
        browser.close()
    print("DONE", flush=True)


if __name__ == '__main__':
    main()
