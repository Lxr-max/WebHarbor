#!/usr/bin/env python3
"""Fetch wanderlog.com pages and record their __MOBX_STATE__ SSR snapshots.

Every captured page is stored under sites/wanderlog/scraped_data/ as the raw
HTML plus the parsed __MOBX_STATE__ JSON (the same server-rendered document a
browser receives). Downstream build scripts turn these into the tracked
source_data/*.json snapshots.

Run from sites/wanderlog:  python3 scripts_dev/scrape_pages.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
OUT = os.path.join(SITE, "scraped_data")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

DECODER = json.JSONDecoder()


def fetch(url: str, retries: int = 3) -> str:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept-Language": "en-US,en;q=0.9"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(3 + 3 * attempt)
    raise RuntimeError(f"fetch failed: {url}: {last}")


def mobx_state(html: str):
    m = re.search(r"window\.__MOBX_STATE__ = (.*?)\n(?=</script>|<(?:!|script))", html, flags=re.S)
    if not m:
        m = re.search(r"window\.__MOBX_STATE__ = (.*?)\s*</script>", html, flags=re.S)
    if not m:
        return None
    try:
        data, _ = DECODER.raw_decode(m.group(1))
        return data
    except json.JSONDecodeError:
        return None


def capture(name: str, url: str, save_html: bool = False) -> dict | None:
    html = fetch(url)
    state = mobx_state(html)
    entry = {"url": url, "state": state}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(entry, f, ensure_ascii=False, sort_keys=True)
    if save_html:
        with open(os.path.join(OUT, name + ".html"), "w", encoding="utf-8") as f:
            f.write(html)
    ok = "ok" if state else "NO-STATE"
    print(f"[capture] {name}: {len(html)} bytes, state={ok}")
    return state


def main() -> int:
    # -- landing + marketing surfaces -----------------------------------
    capture("home", "https://wanderlog.com/", save_html=True)
    capture("hotels_landing", "https://wanderlog.com/hotels", save_html=True)

    # -- destination explore pages --------------------------------------
    geos = [
        (1, "tokyo"), (9613, "london"), (9614, "paris"), (9616, "rome"),
        (9617, "barcelona"), (58144, "new-york-city"), (58147, "san-francisco"),
        (58148, "las-vegas"), (7, "singapore"), (4, "bangkok"),
        (9625, "amsterdam"), (86647, None),
    ]
    for gid, slug in geos:
        url = f"https://wanderlog.com/explore/{gid}/{slug}" if slug else f"https://wanderlog.com/explore/{gid}"
        capture(f"explore_{gid}", url)
        time.sleep(1.0)

    # -- geo category list pages (real ranked place lists) --------------
    lists = json.load(open(os.path.join(HERE, "capture_lists.json"), encoding="utf-8"))
    for name, gid, slug in lists:
        capture(f"list_{name}", f"https://wanderlog.com/list/geoCategory/{gid}/{slug}")
        time.sleep(1.0)

    # -- guide (shared trip) views --------------------------------------
    guides = json.load(open(os.path.join(HERE, "capture_guides.json"), encoding="utf-8"))
    for key, slug in guides:
        capture(f"guide_{key}", f"https://wanderlog.com/view/{key}/{slug}")
        time.sleep(1.0)

    # -- place detail pages ---------------------------------------------
    places = json.load(open(os.path.join(HERE, "capture_places.json"), encoding="utf-8"))
    for pid in places:
        capture(f"place_{pid}", f"https://wanderlog.com/place/details/{pid}")
        time.sleep(0.8)

    print("[capture] done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
