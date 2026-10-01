#!/usr/bin/env python3
"""Second-pass scrape: discounted specials + bundles with fixed price parsing.

Extends the base scrape with:
  * ~20 games from the live specials snapshot (so the mirror's Specials
    page reflects the real current sale) — full details, reviews, news,
    and images for each.
  * bundle pages with the correct final-price parse (the bundle price is
    the first data-price-final on the page), plus appdetails for every
    bundle item so the mirror can render the bundle contents.

Run:  python3 scripts_dev/scrape2.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scrape import (OUT, S, get, save_json, fetch_image, scrape_appdetails,
                    scrape_reviews, scrape_news, discover_bundle_ids, CAPTURES,
                    note_capture, now_iso, IMG_DIR, FETCHED_IMAGES)  # noqa: E402

import requests  # noqa: E402

# Curated from the live specials snapshot: genre/price/discount spread.
PICKED_SPECIALS = [
    2161700,   # Persona 3 Reload            -70% RPG
    374320,    # DARK SOULS III               -50% Action RPG
    1888930,   # The Last of Us Part I        -50% Action Adventure
    281990,    # Stellaris                    -70% Strategy
    1771300,   # Kingdom Come: Deliverance II -60% RPG
    582660,    # Black Desert                 -90% MMO
    335300,    # DARK SOULS II: SotFS         -50% Action RPG
    2958130,   # Jurassic World Evolution 3   -33% Simulation
    2909400,   # FINAL FANTASY VII REBIRTH    -70% RPG
    2679460,   # Metaphor: ReFantazio         -60% RPG
    2186680,   # Warhammer 40,000: Rogue Trader -70% Strategy RPG
    2221490,   # The Division 2               -90% Action
    526870,    # Satisfactory                 -30% Simulation
    1462040,   # FINAL FANTASY VII REMAKE     -75% RPG
    1145350,   # Hades II                     -30% Action Roguelike
    3527290,   # PEAK                          -38% Indie Co-op
    1245620,   # Elden Ring (check discount)  Action RPG
    570940,    # DARK SOULS: REMASTERED      -50%
    1486920,   # Tempest Rising               -50% Strategy
    1706510,   # Songs of Glimmerwick         -10% Indie
]


def scrape_bundle_fixed(bundle_id):
    r = get(f'https://store.steampowered.com/bundle/{bundle_id}/', sleep=1.2)
    if r is None or r.status_code != 200:
        return None
    html = r.text
    t = re.search(r'<title>([^<]*)</title>', html)
    if not t or 'Steam' not in t.group(1):
        return None
    name = t.group(1).replace('on Steam', '').strip()
    base = re.search(r'class="bundle_base_discount">([^<]*)<', html)
    items = re.findall(r'data-ds-appid="(\d+)"', html)
    prices = [int(p) for p in re.findall(r'data-price-final="(\d+)"', html)]
    final = prices[0] if prices else None
    bd = re.search(r'data-bundlediscount="(\d+)"', html)
    return {
        'bundle_id': bundle_id,
        'name': name,
        'base_discount': base.group(1).strip() if base else '',
        'bundlediscount_pct': int(bd.group(1)) if bd else 0,
        'item_appids': items,
        'item_price_cents': prices[1:1 + len(items)] if len(prices) > len(items) else prices[:len(items)],
        'final_price_cents': final,
    }


def main():
    t0 = now_iso()
    print(f'=== steam scrape2 (specials + bundles) start {t0}', flush=True)

    details = json.loads((OUT / 'app_details.json').read_text())
    reviews = json.loads((OUT / 'reviews.json').read_text())
    news = json.loads((OUT / 'news.json').read_text())
    bundles = json.loads((OUT / 'bundles.json').read_text())

    # load image map so fetch_image dedup keeps working across passes
    stored = json.loads((OUT / 'images.json').read_text())
    FETCHED_IMAGES.update(stored)

    # ---- 1. discounted games ------------------------------------------
    for i, appid in enumerate(PICKED_SPECIALS):
        key = str(appid)
        if key in details:
            continue
        rec = scrape_appdetails(appid)
        if rec:
            details[key] = rec
            rv = scrape_reviews(appid)
            if rv:
                reviews[key] = rv
            nw = scrape_news(appid)
            if nw:
                news[key] = nw
        time.sleep(1.4)
        print(f'  .. specials detail {i + 1}/{len(PICKED_SPECIALS)}', flush=True)

    # ---- 2. bundles ------------------------------------------------------
    catalog_ids = [a for a, v in details.items() if v['type'] == 'game']
    bundle_ids = discover_bundle_ids(
        [a for a in catalog_ids if details[a].get('dlc')][:24], limit=14)
    for bid in list(bundle_ids)[:12]:
        b = scrape_bundle_fixed(bid)
        if b and b['final_price_cents'] and len(b['item_appids']) >= 2:
            bundles[str(bid)] = b
        time.sleep(1.2)
    print(f'[bundles] {len(bundles)} bundles captured', flush=True)

    # ---- 3. bundle-item appdetails (DLC rows) -----------------------------
    item_ids = set()
    for b in bundles.values():
        for aid in b['item_appids']:
            item_ids.add(str(aid))
    for i, aid in enumerate(sorted(item_ids)):
        if aid not in details:
            rec = scrape_appdetails(aid)
            if rec:
                details[aid] = rec
            time.sleep(1.2)
        print(f'  .. bundle item {i + 1}/{len(item_ids)}', flush=True)

    # ---- 4. images for new entries ----------------------------------------
    for appid, d in sorted(details.items()):
        stem = f'app{appid}'
        if d.get('header') and f'{stem}-header.jpg' not in FETCHED_IMAGES:
            fetch_image(d['header'], f'{stem}-header.jpg')
        if d.get('capsule_231') and f'{stem}-capsule.jpg' not in FETCHED_IMAGES:
            fetch_image(d['capsule_231'], f'{stem}-capsule.jpg')
        for j in range(4):
            if f'{stem}-ss{j}.jpg' not in FETCHED_IMAGES and len(d.get('screenshots', [])) > j:
                fetch_image(d['screenshots'][j]['path_full'], f'{stem}-ss{j}.jpg')
        time.sleep(0.3)
    print(f'[images] total {len(FETCHED_IMAGES)}', flush=True)

    save_json('app_details.json', details)
    save_json('reviews.json', reviews)
    save_json('news.json', news)
    save_json('bundles.json', bundles)
    save_json('images.json', FETCHED_IMAGES)

    # merge capture logs
    old = json.loads((OUT / 'captures.json').read_text())
    save_json('captures.json', old + CAPTURES)
    print(f'=== scrape2 done; details={len(details)} bundles={len(bundles)}',
          flush=True)


if __name__ == '__main__':
    main()
