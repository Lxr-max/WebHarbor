#!/usr/bin/env python3
"""Resilient slow tour-detail scraper: 1 worker, incremental saves, 403 backoff.

Usage: python3 scrape_slow.py <ids_file> <progress_jsonl>
Appends one JSON line per scraped tour to progress_jsonl; skips ids already done.
"""
import json
import pathlib
import random
import sys
import time

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from scrape_tours import scrape_tour  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def main():
    ids_file, progress = sys.argv[1], sys.argv[2]
    ids = [int(x) for x in pathlib.Path(ids_file).read_text().split() if x.strip()]
    done = set()
    ppath = pathlib.Path(progress)
    if ppath.exists():
        for line in ppath.read_text().splitlines():
            try:
                done.add(json.loads(line)["tour_id"])
            except Exception:
                pass
    todo = [i for i in ids if i not in done]
    print(f"todo {len(todo)} / {len(ids)}", flush=True)
    with ppath.open("a") as sink, sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(
            viewport={"width": 1440, "height": int(980 + random.random() * 80)},
            user_agent=UA, locale="en-US")
        page = ctx.new_page()
        backoff = 0
        for n, tid in enumerate(todo):
            while True:
                try:
                    rec = scrape_tour(page, tid)
                    if rec.get("title") == "403 Forbidden" or (not rec.get("title")):
                        backoff += 1
                        wait = min(900, 240 * backoff) + random.random() * 60
                        print(f"[t/{tid}] blocked; backing off {int(wait)}s (n={backoff})", flush=True)
                        time.sleep(wait)
                        # fresh context after a block
                        try:
                            ctx.close()
                        except Exception:
                            pass
                        ctx = browser.new_context(
                            viewport={"width": 1440, "height": int(980 + random.random() * 80)},
                            user_agent=UA, locale="en-US")
                        page = ctx.new_page()
                        continue
                    backoff = 0
                    sink.write(json.dumps(rec) + "\n")
                    sink.flush()
                    print(f"[t/{tid}] ok ({n+1}/{len(todo)}) days={len(rec.get('days_raw') or [])} deps={len(rec.get('departures_raw') or [])}", flush=True)
                    break
                except Exception as e:
                    print(f"[t/{tid}] ERR {str(e)[:90]}", flush=True)
                    time.sleep(20)
            time.sleep(6 + random.random() * 8)
        browser.close()
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
