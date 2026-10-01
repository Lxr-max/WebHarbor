#!/usr/bin/env python3
"""Build the tracked source_data/ snapshot from scraped_data/ captures.

Deterministic: stable ordering, no wall clock, no RNG. The output files
(games.json, search_snapshots.json, reviews.json, news.json, bundles.json)
are committed to git and seed the mirror database at image build time; the
raw captures stay in scraped_data/ (gitignored).

Also copies every fetched image from scraped_data/images/ into
static/images/ so the site serves the real upstream bytes, and records
image_sources.json for the asset-inventory builder.

Run:  python3 scripts_dev/build_source_data.py
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
RAW = SITE / 'scraped_data'
SRC = SITE / 'source_data'
IMAGES = SITE / 'static' / 'images'


def slugify(text):
    text = re.sub(r'[^A-Za-z0-9]+', '-', str(text)).strip('-').lower()
    return text


def load(name):
    return json.loads((RAW / name).read_text(encoding='utf-8'))


def main():
    SRC.mkdir(parents=True, exist_ok=True)
    IMAGES.mkdir(parents=True, exist_ok=True)

    details = load('app_details.json')
    reviews = load('reviews.json')
    news = load('news.json')
    bundles = load('bundles.json')
    snapshots = load('search_snapshots.json')
    image_map = load('images.json')

    # every image referenced below must exist locally
    for name, meta in sorted(image_map.items()):
        src = RAW / 'images' / name
        if not src.is_file():
            raise SystemExit(f'missing scraped image: {name}')
        dst = IMAGES / name
        if not dst.is_file():
            shutil.copy2(src, dst)

    # which appids are needed? every full game + any bundle item
    bundle_items = set()
    for b in bundles.values():
        bundle_items.update(str(a) for a in b.get('item_appids', []))

    # review summary per appid (from the live appreviews API)
    summaries = {}
    for appid, rv in reviews.items():
        pos = rv.get('total_positive') or 0
        total = rv.get('total_reviews') or 0
        pct = round(100 * pos / total) if total else 0
        summaries[appid] = {
            'review_score_desc': rv.get('review_score_desc') or '',
            'review_pct': pct,
            'total_positive': pos,
            'total_negative': rv.get('total_negative') or 0,
            'total_reviews': total,
        }

    # fallback review summary from the search snapshots
    snap_desc = {}
    for key in ('topsellers', 'newreleases', 'specials', 'freegames', 'under10'):
        for row in snapshots.get(key, []):
            snap_desc.setdefault(row['appid'], row)

    games_out = []
    for appid in sorted(details, key=lambda a: int(a)):
        d = details[appid]
        keep = d['type'] == 'game' or appid in bundle_items
        if not keep:
            continue
        stem = f'app{appid}'
        summary = summaries.get(appid) or {}
        if not summary and appid in snap_desc:
            row = snap_desc[appid]
            summary = {
                'review_score_desc': row.get('review_desc', ''),
                'review_pct': int(row.get('review_pct') or 0),
                'total_positive': 0,
                'total_negative': 0,
                'total_reviews': int(row.get('review_count') or 0),
            }
        header = f'{stem}-header.jpg' if f'{stem}-header.jpg' in image_map else ''
        capsule = ''
        if f'{stem}-capsule.jpg' in image_map:
            capsule = f'{stem}-capsule.jpg'
        elif f'capsule-{appid}.jpg' in image_map:
            # the search snapshot already fetched the same capsule bytes
            capsule = f'capsule-{appid}.jpg'
        screens = [f'{stem}-ss{j}.jpg' for j in range(4)
                   if f'{stem}-ss{j}.jpg' in image_map]
        rec = {
            'appid': d['appid'],
            'slug': slugify(d['name']),
            'name': d['name'],
            'type': d['type'],
            'is_free': bool(d.get('is_free')),
            'short_desc': d.get('short_desc', ''),
            'about': d.get('about', ''),
            'detailed_desc': d.get('detailed_desc', ''),
            'supported_languages': d.get('supported_languages', ''),
            'release_date': d.get('release_date', ''),
            'coming_soon': bool(d.get('coming_soon')),
            'price_cents': d.get('price_cents'),
            'initial_cents': d.get('initial_cents'),
            'discount_pct': d.get('discount_pct', 0) or 0,
            'header_img': header,
            'capsule_img': capsule,
            'platforms': d.get('platforms', {}),
            'genres': [g for g in d.get('genres', [])
                       if g not in ('Early Access', 'Web Publishing')],
            'categories': d.get('categories', [])[:12],
            'publishers': d.get('publishers', []),
            'developers': d.get('developers', []),
            'achievements_total': d.get('achievements_total'),
            'required_age': d.get('required_age', 0) or 0,
            'dlc_apps': [a for a in d.get('dlc', []) if str(a) in details],
            'screens': screens,
            'pc_requirements': d.get('pc_requirements', {}),
            'mac_requirements': d.get('mac_requirements', {}),
            'linux_requirements': d.get('linux_requirements', {}),
            'review_score_desc': summary.get('review_score_desc', ''),
            'review_pct': summary.get('review_pct', 0),
            'total_positive': summary.get('total_positive', 0),
            'total_negative': summary.get('total_negative', 0),
            'total_reviews': summary.get('total_reviews', 0),
        }
        games_out.append(rec)

    # reviews / news: keep only rows whose game survived
    kept_ids = {str(g['appid']) for g in games_out}
    reviews_out = {a: rv for a, rv in reviews.items() if a in kept_ids}
    news_out = {a: nw for a, nw in news.items() if a in kept_ids}

    # bundles: resolve item lists to catalog apps, keep only bundles whose
    # items are all present, and record slugs
    bundles_out = {}
    for bid, b in sorted(bundles.items(), key=lambda kv: int(kv[0])):
        items = [str(a) for a in b.get('item_appids', [])]
        if not all(a in kept_ids for a in items):
            continue
        prices = b.get('item_price_cents', [])
        if len(prices) < len(items):
            prices = (prices * len(items))[:len(items)]
        bundles_out[bid] = {
            'bundle_id': b['bundle_id'],
            'slug': slugify(b['name']),
            'name': b['name'],
            'base_discount': b.get('base_discount', ''),
            'bundlediscount_pct': b.get('bundlediscount_pct', 0),
            'item_appids': [int(a) for a in items],
            'item_price_cents': prices,
            'final_price_cents': b.get('final_price_cents', 0),
        }

    def dump(name, data):
        (SRC / name).write_text(
            json.dumps(data, ensure_ascii=False, indent=1, sort_keys=False),
            encoding='utf-8')
        size = (SRC / name).stat().st_size
        print(f'[source] {name}: {len(data)} records, {size} B')

    dump('games.json', games_out)
    dump('search_snapshots.json', snapshots)
    dump('reviews.json', reviews_out)
    dump('news.json', news_out)
    dump('bundles.json', bundles_out)

    # image source map for the asset-inventory builder
    (RAW / 'image_sources.json').write_text(
        json.dumps({meta['url']: name for name, meta in sorted(image_map.items())},
                   indent=1, sort_keys=True), encoding='utf-8')

    n_games = len([g for g in games_out if g['type'] == 'game'])
    n_dlc = len(games_out) - n_games
    print(f'[source] {len(games_out)} products ({n_games} games, {n_dlc} dlc), '
          f'{len(reviews_out)} review sets, {len(news_out)} news sets, '
          f'{len(bundles_out)} bundles, {len(image_map)} images')


if __name__ == '__main__':
    main()
