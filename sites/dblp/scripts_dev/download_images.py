#!/usr/bin/env python3
"""Download the upstream images this mirror renders and pin them by sha256.

Every image the templates reference is fetched from its exact upstream
dblp.org URL (no placeholders, no substitutions, no resizing); the result
is static/images/upstream/<name> plus the tracked asset_inventory.json
pinning each file's sha256 + source URL. Re-running the script verifies
existing files byte-for-byte and only re-downloads what changed.
"""
import hashlib
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
IMG_DIR = os.path.join(SITE, 'static', 'images', 'upstream')
INVENTORY = os.path.join(SITE, 'asset_inventory.json')

BASE = 'https://dblp.org/img/'

# logical name -> upstream path (every entry is rendered by the templates)
IMAGES = {
    'logo.320x120.png': 'logo.320x120.png',
    'dblp.icon.120x120.png': 'dblp.icon.120x120.png',
    'dblp.icon.152x152.png': 'dblp.icon.152x152.png',
    'dblp.icon.192x192.png': 'dblp.icon.192x192.png',
    'favicon.ico': 'favicon.ico',
    'n.png': 'n.png',
    'paper.dark.16x16.png': 'paper.dark.16x16.png',
    'info.dark.16x16.png': 'info.dark.16x16.png',
    'bibtex.dark.16x16.png': 'bibtex.dark.16x16.png',
    'download.dark.16x16.png': 'download.dark.16x16.png',
    'bmftr-logo-bottom.png': 'bmftr-logo-bottom.png',
    'dfg-logo-bottom.png': 'dfg-logo-bottom.png',
    'leibniz-logo-bottom.png': 'leibniz-logo-bottom.png',
    'lzi-logo-bottom.png': 'lzi-logo-bottom.png',
    'rlp-logo-bottom.png': 'rlp-logo-bottom.png',
    'sl-logo-bottom.png': 'sl-logo-bottom.png',
    'utr-logo-bottom.png': 'utr-logo-bottom.png',
    'cc0.80x15.black.png': 'cc0.80x15.black.png',
}

UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like '
      'Gecko) Chrome/129.0.0.0 Safari/537.36')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read()


def main():
    os.makedirs(IMG_DIR, exist_ok=True)
    assets = []
    missing = []
    for name, path in sorted(IMAGES.items()):
        url = BASE + path
        out = os.path.join(IMG_DIR, name)
        if not (os.path.exists(out) and os.path.getsize(out) > 0):
            status, body = fetch(url)
            if status != 200:
                raise SystemExit(f'upstream {url} -> {status}')
            if not body.startswith(b'\x89PNG') and not name.endswith('.ico'):
                raise SystemExit(f'{url}: not a PNG ({body[:8]!r})')
            with open(out, 'wb') as f:
                f.write(body)
            print('fetched', name, len(body), 'bytes')
        assets.append({
            'path': f'static/images/upstream/{name}',
            'bytes': os.path.getsize(out),
            'sha256': sha256(out),
            'source_url': url,
        })
    inventory = {
        'schema_version': 1,
        'asset_count': len(assets),
        'assets': assets,
        'missing_upstream': missing,
    }
    with open(INVENTORY, 'w') as f:
        json.dump(inventory, f, indent=1, sort_keys=True)
        f.write('\n')
    print(f'asset_inventory.json: {len(assets)} images pinned')


if __name__ == '__main__':
    main()
