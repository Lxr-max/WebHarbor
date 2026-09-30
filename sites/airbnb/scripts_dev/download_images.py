#!/usr/bin/env python3
"""Download every managed upstream image for the airbnb mirror.

Reads source_data/*.json (built by build_source_data.py) and fetches the
exact upstream CDN URLs the mirror renders (a0.muscache.com, the im_w
resize parameter the upstream site itself uses):

  - listing photo-tour images (the captured ld_images gallery, 7 per
    listing, im_w=720) plus the SERP card photos for listings whose
    photo-tour gallery wasn't captured
  - experience cover/gallery images (4 per experience)
  - host avatars (from the captured reviews payload)
  - homepage destination-card thumbnails (first listing photo)

Produces static/images/upstream/ + asset_inventory.json (path, bytes,
sha256, source_url for every file). Idempotent: re-running refetches
nothing that already matches its sha256.

Run:  python3 scripts_dev/download_images.py
"""
import hashlib
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
SRC = os.path.join(SITE, 'source_data')
IMG_ROOT = os.path.join(SITE, 'static', 'images', 'upstream')
INVENTORY = os.path.join(SITE, 'asset_inventory.json')
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
MAX_RETRIES = 4

sys.path.insert(0, SITE)
from seed_lib import local_image  # noqa: E402  (shared URL->name mapping)


def load(name):
    with open(os.path.join(SRC, name), encoding='utf-8') as f:
        return json.load(f)


def detect_ext(data, fallback):
    """The upstream CDN serves a few avatar/media URLs as PNG regardless
    of the URL's own extension; the inventory records what was actually
    served so check_asset_inventory framing checks pass."""
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return '.png'
    if data[:3] == b'\xff\xd8\xff':
        return '.jpg'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return '.webp'
    return fallback


def fetch(url, dest):
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={'user-agent': UA,
                                                       'accept-language': 'en-US,en;q=0.9'})
            with urllib.request.urlopen(req, timeout=45) as r:
                data = r.read()
            if not data or len(data) < 500:
                raise RuntimeError(f'too small ({len(data)} bytes)')
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, 'wb') as f:
                f.write(data)
            return data
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                print(f'  FAILED {url}: {e}', file=sys.stderr)
                return None
            time.sleep(2 + attempt * 3)


def main():
    os.makedirs(IMG_ROOT, exist_ok=True)
    listings = load('listing_details.json')
    cards = load('listings.json')
    experiences = load('experience_details.json')
    exp_cards = load('experiences.json')

    planned = {}   # source_url -> local relative path
    seen_paths = set()

    def plan(url, kind, lid=None):
        if not url:
            return None
        rel = local_image(url).lstrip('/')
        if rel in seen_paths:
            return rel
        seen_paths.add(rel)
        planned[url] = rel
        return rel

    for lid, det in listings.items():
        # the captured PDP photo-tour payload carries only null placeholder
        # slots (review B1), so the real gallery is the ld_images photo-tour
        # URL set; download every URI the seed can reference
        for p in (det.get('photos') or []):
            plan(p.get('uri'), 'listing', lid)
        for u in (det.get('ld_images') or []):
            plan(u, 'listing', lid)
        if det.get('host_avatar') is None:
            for r in (det.get('reviews') or []):
                if r.get('reviewee_img'):
                    plan(r['reviewee_img'], 'host', lid)
                    break
    # card photos: the gallery fallback for listings without ld_images
    # (every card image is therefore a managed local asset too)
    for lid, card in cards.items():
        if lid not in listings:
            continue
        for u in (card.get('photos') or []):
            plan(u, 'listing', lid)
    for eid, det in experiences.items():
        for u in (det.get('photos') or []):
            plan(u, 'exp', eid)
        for a in (det.get('agenda') or []):
            if isinstance(a, dict) and a.get('image'):
                plan(a['image'], 'exp', eid)
    for eid, card in exp_cards.items():
        for u in (card.get('photos') or [])[:2]:
            plan(u, 'exp', eid)
    for lid, det in listings.items():
        for h in (det.get('highlights') or []):
            if isinstance(h, dict) and h.get('image'):
                plan(h['image'], 'listing', lid)

    print(f'planned {len(planned)} upstream images')
    inventory = {'schema_version': 1, 'asset_count': 0, 'assets': []}
    prev = {}
    if os.path.exists(INVENTORY):
        with open(INVENTORY) as f:
            for row in json.load(f).get('assets', []):
                prev[row['path']] = row

    ok = fail = 0
    for url, rel in sorted(planned.items(), key=lambda kv: kv[1]):
        dest = os.path.join(SITE, rel)
        data = None
        if os.path.exists(dest) and rel in prev and prev[rel].get('source_url') == url:
            with open(dest, 'rb') as f:
                data = f.read()
            if hashlib.sha256(data).hexdigest() != prev[rel]['sha256']:
                data = None
        if data is None:
            data = fetch(url, dest)
            time.sleep(0.35)
        if data is None:
            fail += 1
            continue
        actual = os.path.splitext(rel)[0] + detect_ext(
            data, os.path.splitext(rel)[1] or '.jpg')
        if actual != rel:
            os.replace(dest, os.path.join(SITE, actual))
        inventory['assets'].append({
            'path': actual,
            'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest(),
            'source_url': url,
        })
        ok += 1
    inventory['asset_count'] = len(inventory['assets'])
    inventory['assets'].sort(key=lambda a: a['path'])
    with open(INVENTORY, 'w') as f:
        json.dump(inventory, f, indent=1)
    print(f'downloaded/verified {ok} images, failed {fail}')
    print(f"inventory: {INVENTORY} ({inventory['asset_count']} assets)")


if __name__ == '__main__':
    main()
