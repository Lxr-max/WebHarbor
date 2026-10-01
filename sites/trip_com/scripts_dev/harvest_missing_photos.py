#!/usr/bin/env python3
"""harvest_missing_photos.py — live re-capture of upstream product photos.

The 2026-09-27 snapshot captured no detail-page photos for 61 attractions
(upstream's listing served its generic placeholder card image for them, and
the original detail harvest only visited a handful of pages per city). To fix
the review's MINOR-1 cross-entry image reuse those cards need a real photo of
their own product, so this script re-captures the upstream detail pages
(us.trip.com/things-to-do/detail/<id>/) and records every product image URL
they render. The URLs are consumed by fix_asset_reuse.py; the bytes are
fetched from the upstream CDN and pinned in asset_inventory.json, so the
inventory remains the provenance record (re-capture date disclosed there).

Output: scraped_data/attraction_photos_live.json  {attraction_id: [urls]}
Run from sites/trip_com/:  python3 scripts_dev/harvest_missing_photos.py
"""
import json
import pathlib
import sys
import time

from playwright.sync_api import sync_playwright

BASE = pathlib.Path(__file__).resolve().parent.parent
OUT = BASE / "scraped_data" / "attraction_photos_live.json"

EXTRACT = """() => {
  const out = [];
  document.querySelectorAll('img').forEach(im => {
    const src = im.currentSrc || im.src || '';
    if (/ak-\\w+\\.tripcdn\\.com\\/images\\//.test(src) && !out.includes(src))
      out.push(src);
  });
  return out;
}"""


def is_real_name(name):
    """Filter harvest artifacts: a few captured cards carry the listing
    section header instead of the product name."""
    n = (name or "").strip().lower()
    return bool(n) and "results for" not in n and n != "attractions & tours category"


def targets():
    """Every attraction whose card file still shares a source URL (with or
    without captured photos), the top real-named attraction of the cities
    whose cards are still shared, and the two attractions with shared spare
    files."""
    inv = json.loads((BASE / "asset_inventory.json").read_text(encoding="utf-8"))
    attractions = json.loads((BASE / "source_data_attractions.json").read_text(encoding="utf-8"))
    cities = json.loads((BASE / "source_data_cities.json").read_text(encoding="utf-8"))
    by_url = {}
    for a in inv["assets"]:
        by_url.setdefault(a["source_url"], []).append(a["path"])
    shared = {p for u, ps in by_url.items() if len(ps) > 1 for p in ps}
    ids = set()
    for p in shared:
        parts = p.split("/")
        if parts[2] != "attractions" or not parts[3].endswith(tuple(f"_1.{e}" for e in ("webp", "avif", "jpg", "png"))):
            continue
        ids.add(int(parts[3].rsplit("_", 1)[0]))
    # top real-named attraction of each city whose card file is still shared
    for c in cities:
        card = f"static/images/cities/{c['slug']}.webp"
        if card in shared:
            top = sorted((a for a in attractions
                          if a.get("city_slug") == c["slug"] and is_real_name(a.get("name"))),
                         key=lambda a: (-a.get("rating", 0), -a.get("booked_count", 0)))
            if top:
                ids.add(top[0]["id"])
    # spare-file pair owners
    ids |= {101406278, 115126185}
    return sorted(ids)


def main():
    only = [int(x) for x in sys.argv[1:]] or targets()
    print(f"harvesting {len(only)} upstream detail pages…", flush=True)
    photos = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"))
        for n, aid in enumerate(only, 1):
            if str(aid) in photos:
                continue
            url = f"https://us.trip.com/things-to-do/detail/{aid}/?locale=en-US&curr=USD"
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=40000)
                page.wait_for_timeout(2500)
                # scroll to trigger lazy-loaded gallery photos
                for _ in range(6):
                    page.mouse.wheel(0, 1400)
                    page.wait_for_timeout(700)
                imgs = page.evaluate(EXTRACT)
                photos[str(aid)] = imgs
                print(f"  [{n}/{len(only)}] {aid}: {len(imgs)} photos", flush=True)
            except Exception as exc:                            # noqa: BLE001
                print(f"  [{n}/{len(only)}] {aid} FAILED: {str(exc)[:90]}", flush=True)
            if n % 10 == 0:
                OUT.write_text(json.dumps(photos, indent=1), encoding="utf-8")
            time.sleep(0.4)
        browser.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(photos, indent=1), encoding="utf-8")
    got = sum(1 for v in photos.values() if v)
    print(f"saved {got}/{len(photos)} pages with photos -> {OUT}")


if __name__ == "__main__":
    main()
