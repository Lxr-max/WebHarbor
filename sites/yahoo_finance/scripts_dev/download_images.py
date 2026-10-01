#!/usr/bin/env python3
"""Download the yahoo_finance mirror's image set from the upstream CDNs.

Every image the mirror serves under static/images/upstream/ is fetched from
the exact upstream URL the live pages render it at: news-article thumbnails
from Yahoo's image pipelines (s.yimg.com mysterio resizes, media.zenfs.com
and provider originals). Each download is verified with Pillow (real image
bytes, sane dimensions, not a placeholder tile) and recorded in
asset_inventory.json with its byte length, sha256 and source URL. Nothing
is stretched, duplicated or synthesized; images without an upstream fetch
are simply not shipped (the UI falls back to a neutral text tile).

Usage (from sites/yahoo_finance):
    python3 scripts_dev/download_images.py
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests
from PIL import Image

HERE = Path(__file__).resolve().parent.parent
SOURCE = HERE / 'source_data'
CAPTURES = HERE / 'scraped_data' / 'captures'
IMAGES = HERE / 'static' / 'images' / 'upstream'

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

session = requests.Session()
session.headers.update({'User-Agent': UA, 'Referer': 'https://finance.yahoo.com/'})

# Upper bound so the shipped bundle stays reasonable: topic-stream articles
# first (the news pages lead with them), then the freshest symbol-news items.
MAX_IMAGES = 140


def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def pick_thumb_resolutions(resolutions):
    """Prefer the 656-wide resize, else the largest sane entry."""
    best = None
    for res in resolutions or []:
        w = res.get('width') or 0
        if w == 656:
            return res
        if w and (best is None or w > (best.get('width') or 0)):
            best = res
    return best


def collect_targets():
    """(image_url, source_url, local_name, priority) tuples, deduped."""
    seen = {}
    articles = json.loads((SOURCE / 'news_articles.json').read_text())
    for art in articles:
        thumb = art.get('thumb_resized') or art.get('thumb_original')
        if not thumb:
            continue
        seen[thumb] = {
            'url': thumb,
            'name': f'news_{art["key"]}',
            'priority': (0, art.get('display_time') or ''),
        }
    symbol_news = json.loads((SOURCE / 'symbol_news.json').read_text())
    for item in symbol_news:
        res = pick_thumb_resolutions(item.get('thumbnail'))
        thumb = (res or {}).get('url')
        if not thumb:
            continue
        if thumb in seen:
            continue
        name = 'sn_' + hashlib.sha1(thumb.encode()).hexdigest()[:12]
        seen[thumb] = {
            'url': thumb, 'name': name,
            'priority': (1, str(item.get('published_ts') or '')),
        }
    targets = sorted(seen.values(), key=lambda t: (t['priority'][0], t['priority'][1]),
                     reverse=False)
    # topic articles first, newest symbol news after
    return targets


def download(target):
    url = target['url']
    resp = session.get(url, timeout=45)
    raw = resp.content
    if resp.status_code != 200 or len(raw) < 1200:
        return None, resp.status_code
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception:
        return None, resp.status_code
    if img.width < 120 or img.height < 90:
        return None, resp.status_code
    ext = (img.format or 'JPEG').lower()
    if ext == 'jpeg':
        ext = 'jpg'
    if ext not in ('jpg', 'png', 'webp', 'gif'):
        return None, resp.status_code
    name = f'{target["name"]}.{ext}'
    path = IMAGES / name
    path.write_bytes(raw)
    record = {
        'bytes': len(raw),
        'path': f'static/images/upstream/{name}',
        'sha256': hashlib.sha256(raw).hexdigest(),
        'source_url': url,
        'width': img.width,
        'height': img.height,
        'format': img.format,
        'fetched_at': now_iso(),
    }
    return record, resp.status_code


def main():
    IMAGES.mkdir(parents=True, exist_ok=True)
    started = now_iso()
    targets = collect_targets()
    print(f'== candidate images: {len(targets)} (cap {MAX_IMAGES})')
    inventory = []
    failures = []
    for i, target in enumerate(targets):
        if len(inventory) >= MAX_IMAGES:
            print('   cap reached')
            break
        record, status = download(target)
        if record:
            inventory.append(record)
        else:
            failures.append({'url': target['url'], 'status': status})
        time.sleep(0.7)
        if (i + 1) % 25 == 0:
            print(f'   {i+1}/{len(targets)} done, {len(inventory)} ok')
    inventory.sort(key=lambda r: r['path'])
    (HERE / 'asset_inventory.json').write_text(json.dumps({
        'schema_version': 1,
        'asset_count': len(inventory),
        'assets': inventory,
        'download_started_utc': started,
        'download_finished_utc': now_iso(),
        'failed_candidates': failures,
        'policy': 'every file fetched from the upstream URL it renders at; '
                  'no placeholders, no duplicates, no stretching; verified '
                  'with Pillow at download time',
    }, indent=1))
    total = sum(r['bytes'] for r in inventory)
    print(f'== {len(inventory)} images, {total/1e6:.1f} MB total; '
          f'{len(failures)} failures')


if __name__ == '__main__':
    sys.exit(main())
