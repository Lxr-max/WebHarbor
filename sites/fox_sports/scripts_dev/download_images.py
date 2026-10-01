#!/usr/bin/env python3
"""Download every upstream image referenced by the seed into
static/images/upstream/ and write asset_inventory.json.

Every file is fetched from its exact upstream source URL (recorded per file
in the inventory with bytes + sha256). The naming function mirrors
seed_lib.asset_name so the database rows resolve to these files.
"""
from __future__ import annotations

import concurrent.futures as cf
import hashlib
import json
import subprocess
import sys
from pathlib import Path

SNIFF = {
    'jpg': lambda d: d[:2] == b'\xff\xd8' and d[-2:] == b'\xff\xd9',
    'jpeg': lambda d: d[:2] == b'\xff\xd8' and d[-2:] == b'\xff\xd9',
    'png': lambda d: d[:8] == b'\x89PNG\r\n\x1a\n',
    'webp': lambda d: d[:4] == b'RIFF' and d[8:12] == b'WEBP',
    'gif': lambda d: d[:6] in (b'GIF87a', b'GIF89a'),
}


def sniff_ext(data):
    for ext, test in SNIFF.items():
        if ext in ('jpg', 'jpeg') and test(data):
            return '.jpg'
        if ext not in ('jpg', 'jpeg') and test(data):
            return '.' + ext
    return None


HERE = Path(__file__).resolve().parent
SITE = HERE.parent
OUT = SITE / 'static' / 'images' / 'upstream'
SOURCE = SITE / 'source_data'

sys.path.insert(0, str(SITE))
from seed_lib import asset_name  # noqa: E402

CHROME_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def load(name):
    return json.loads((SOURCE / name).read_text(encoding='utf-8'))


def collect_urls():
    urls = {}

    def add(u):
        if u and u.startswith('http'):
            urls[u] = None

    for row in load('teams.json'):
        add(row.get('logo'))
    standings = load('standings.json')
    for row in standings['nfl'] + standings['mlb']:
        add(row.get('logo'))
    for row in load('stories.json'):
        add(row.get('image'))
    for row in load('shows.json'):
        add(row.get('art'))
        for ep in row.get('episodes', []):
            add(ep.get('thumb'))
    for row in load('personalities.json'):
        add(row.get('art'))
        for vid in row.get('videos', []):
            add(vid.get('thumb'))
    home = load('home.json')
    for tile in home.get('live_tiles_img', []) + home.get('moments_img', []):
        add(tile)
    return sorted(urls)


def fetch(url, out_path):
    from urllib.parse import quote
    url = quote(url, safe=":/?=&%+$;,@~#!()*-")
    cmd = ['curl', '-sL', '--max-time', '45', '-A', CHROME_UA,
           '-H', 'Accept: image/jpeg,image/png;q=0.9,image/webp;q=0.8',
           '--compressed', '-o', str(out_path), '-w', '%{http_code}',
           url]
    for attempt in range(4):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            status = int(r.stdout.strip() or 0)
            size = out_path.stat().st_size if out_path.exists() else 0
            if status == 200 and size > 500:
                with open(out_path, 'rb') as f:
                    head = f.read(12)
                if head[:3] == b'\xff\xd8\xff' or head[:8] == b'\x89PNG\r\n\x1a\n' \
                        or (head[:4] == b'RIFF' and head[8:12] == b'WEBP') \
                        or head[:6] in (b'GIF87a', b'GIF89a'):
                    return True
        except (subprocess.TimeoutExpired, ValueError):
            pass
        out_path.unlink(missing_ok=True)
    return False


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    urls = collect_urls()
    print(f'{len(urls)} referenced upstream images')
    failures = []

    def work(u):
        name = asset_name(u)
        out = OUT / name
        if out.exists() and out.stat().st_size > 500:
            return u, name, True
        ok = fetch(u, out)
        if not ok:
            failures.append(u)
            out.unlink(missing_ok=True)
            return u, name, False
        data = out.read_bytes()
        real = sniff_ext(data)
        if real and not name.endswith(real):
            final = name.rsplit('.', 1)[0] + real
            out.rename(OUT / final)
            return u, final, True
        return u, name, True

    results = []
    with cf.ThreadPoolExecutor(max_workers=10) as ex:
        for i, res in enumerate(ex.map(work, urls)):
            results.append(res)
            if (i + 1) % 200 == 0:
                print(f'  {i + 1}/{len(urls)}', flush=True)

    assets = []
    for u, name, ok in results:
        path = OUT / name
        if not ok or not path.exists():
            continue
        data = path.read_bytes()
        assets.append({
            'path': f'static/images/upstream/{name}',
            'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest(),
            'source_url': u,
        })
    assets.sort(key=lambda a: a['path'])
    manifest = {'schema_version': 1, 'asset_count': len(assets),
                'assets': assets}
    (SITE / 'asset_inventory.json').write_text(
        json.dumps(manifest, indent=1), encoding='utf-8')
    print(f'inventory: {len(assets)} assets')
    if failures:
        print(f'FAILED ({len(failures)}):')
        for u in failures[:20]:
            print('  ', u[:140])
        sys.exit(1)


if __name__ == '__main__':
    main()
