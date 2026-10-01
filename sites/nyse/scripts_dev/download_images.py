#!/usr/bin/env python3
"""Download every upstream image the mirror renders into
static/images/upstream/ and write the tracked asset_inventory.json.

Sources:
- the bell-calendar event images (one per captured ceremony),
- the homepage collage + 'what's next' feature images,
- the listings hub hero and feature images,
- the history-of-NYSE photo collection.

Every file is fetched from its exact upstream URL with curl, verified to
be a real image (magic bytes), and recorded with byte length + sha256 in
asset_inventory.json — the same contract the repo's check_asset_inventory
gate enforces.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
SOURCE = os.path.join(SITE, 'source_data')
IMAGES = os.path.join(SITE, 'static', 'images', 'upstream')
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')
BASE = 'https://www.nyse.com'


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def load(name):
    with open(os.path.join(SOURCE, name), encoding='utf-8') as f:
        return json.load(f)


def collect_urls():
    urls = {}

    def add(path, alt=''):
        if not path:
            return
        if path.startswith('/publicdocs'):
            url = BASE + path
        elif path.startswith('https://'):
            url = path
        else:
            return
        if 'favicon' in url or 'NYSEConnect' in url:
            return
        if url.rsplit('.', 1)[-1].lower() not in (
                'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'):
            return
        urls[url] = (alt or '')

    for event in load('bell_events.json'):
        add(event.get('image'))
    home = load('home_content.json')
    for c in home.get('collage', []):
        add(c)
    for item in home.get('whats_next', []):
        add(item.get('image'))
    for image in load('history_content.json').get('images', []):
        add(image['src'], image.get('alt', ''))
    listings = load('listings_content.json')
    add(listings.get('hero_image'))
    # Feature tiles captured on the upstream listings hub.
    for path in ('/publicdocs/images/NYSE_Trading_Floor_New_Branding-alt.jpg',
                 '/publicdocs/images/Rubrik_Experience_Square.jpg',
                 '/publicdocs/images/NYSE_Logo_Primary.svg'):
        add(path)
    return urls


def fetch(url, dest):
    for attempt in range(6):
        proc = subprocess.run(
            ['curl', '-sL', '--max-time', '60', '-A', UA,
             '-w', '\n%{http_code}', '-o', dest, url],
            capture_output=True, text=True)
        code = (proc.stdout.strip().splitlines() or ['000'])[-1]
        if code == '200' and os.path.exists(dest) and os.path.getsize(dest):
            return True
        if code == '429':
            time.sleep(45.0 * (attempt + 1))
            continue
        time.sleep(5.0)
    return False


def looks_like_image(path):
    with open(path, 'rb') as f:
        head = f.read(256)
    if head.startswith(b'\x89PNG') or head.startswith(b'\xff\xd8\xff') \
            or head[:6] in (b'GIF87a', b'GIF89a') \
            or head.startswith(b'RIFF') or head.startswith(b'\x00\x00\x01\x00'):
        return True
    return b'<svg' in head or head.lstrip().startswith(b'<?xml')


def real_extension(path):
    """The extension the bytes deserve — upstream occasionally serves PNG
    bytes at .jpg paths (and vice versa), and the repo's inventory gate
    enforces that the saved extension describes the real bytes."""
    with open(path, 'rb') as f:
        head = f.read(32)
    if head.startswith(b'\x89PNG'):
        return '.png'
    if head.startswith(b'\xff\xd8\xff'):
        return '.jpg'
    if head[:6] in (b'GIF87a', b'GIF89a'):
        return '.gif'
    if head.startswith(b'RIFF'):
        return '.webp'
    if b'<svg' in head or head.lstrip().startswith(b'<?xml'):
        return '.svg'
    return None


def main():
    os.makedirs(IMAGES, exist_ok=True)
    urls = collect_urls()
    print(f'[images] {len(urls)} upstream images to fetch', flush=True)
    inventory = []
    failed = []
    for i, (url, alt) in enumerate(sorted(urls.items()), 1):
        name = url.split('/')[-1].split('?')[0]
        dest = os.path.join(IMAGES, name)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            pass
        else:
            ok = fetch(url, dest)
            if not ok or not looks_like_image(dest):
                failed.append(url)
                if os.path.exists(dest):
                    os.remove(dest)
                continue
        # Re-key the local name to the real byte format when the upstream
        # path extension lies about the content (recorded honestly in the
        # inventory: source_url keeps the upstream path).
        ext = real_extension(dest)
        if ext and not name.lower().endswith(ext):
            fixed = os.path.splitext(name)[0] + ext
            os.rename(dest, os.path.join(IMAGES, fixed))
            name = fixed
            dest = os.path.join(IMAGES, name)
        digest = sha256(dest)
        prior = next((row for row in inventory
                      if row['sha256'] == digest), None)
        if prior is not None:
            # Two upstream URLs serve byte-identical artwork (upstream
            # reuses ceremony art under "(N)"-suffixed names). Keep one
            # physical file and record the alias URL honestly instead of
            # shipping duplicate bytes.
            prior.setdefault('also_served_at', []).append(url)
            os.remove(dest)
        else:
            inventory.append({'path': f'static/images/upstream/{name}',
                              'source_url': url,
                              'bytes': os.path.getsize(dest),
                              'sha256': digest})
        if i % 25 == 0:
            print(f'  {i}/{len(urls)}', flush=True)
    inventory.sort(key=lambda row: row['path'])
    with open(os.path.join(SITE, 'asset_inventory.json'), 'w') as f:
        json.dump({'schema_version': 1,
                   'asset_count': len(inventory),
                   'assets': inventory}, f, indent=1, sort_keys=True)
    print(f'[images] {len(inventory)} downloaded, {len(failed)} failed',
          flush=True)
    for u in failed:
        print('  FAILED', u, flush=True)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
