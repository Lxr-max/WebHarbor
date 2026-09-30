#!/usr/bin/env python3
"""Download every mapped upstream image into static/images/.

Reads scraped_data/image_urls.json (local_path -> upstream URL, produced by
build_source_data.py) plus a fixed set of site-chrome images referenced by
the templates. Downloads with httpx (the CDN serves images without a browser
session), verifies magic bytes, and never overwrites a healthy file.

Usage: python3 scripts_dev/download_images.py [--force]
"""
import hashlib
import json
import pathlib
import sys
import time

import httpx

ROOT = pathlib.Path(__file__).resolve().parents[1]
IMG = ROOT / 'static' / 'images'
SCRAPE = ROOT / 'scraped_data'

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# site chrome images used by templates (hero art, spotlights, footer badges,
# app icons). Local names are stable; URLs are the real upstream assets.
SITE_IMAGES = {
    'site/hero_home.webp': 'https://assets-page-editor.tourradar.com/page-assets/019f1854-8b7b-7de8-931c-2acf89a68361/1787585455177-3d754e66_lg.webp',
    'site/spotlight_escape.webp': 'https://assets-page-editor.tourradar.com/page-assets/019f1854-8b7b-7de8-931c-2acf89a68361/1788336449605-ee13f494_lg.webp',
    'site/spotlight_plus.webp': 'https://assets-page-editor.tourradar.com/page-assets/019f1854-8b7b-7de8-931c-2acf89a68361/1783003836310-b147c2ab_lg.webp',
    'site/spotlight_solo.webp': 'https://assets-page-editor.tourradar.com/page-assets/019f1854-8b7b-7de8-931c-2acf89a68361/1782827190678-dc97ecb7_lg.webp',
    'site/spotlight_support.webp': 'https://assets-page-editor.tourradar.com/page-assets/019f1854-8b7b-7de8-931c-2acf89a68361/1782827167476-1eec317d_lg.webp',
    'site/serp_hero.webp': 'https://assets-page-editor.tourradar.com/page-assets/019f1854-8b7b-7de8-931c-2acf89a68361/1782829671618-44d88b30_sm.webp',
    'site/way_hiking.jpg': 'https://cdn.tourradar.com/s3/serp/1436x180/213061_wkGcLSF8.jpg',
    'site/way_river.jpg': 'https://cdn.tourradar.com/s3/serp/1436x180/162118_qn8ut5KA.jpg',
    'site/way_safari.jpg': 'https://cdn.tourradar.com/s3/serp/1436x180/17800_jyDuKA5d.jpeg',
    'site/way_train.jpg': 'https://cdn.tourradar.com/s3/serp/1436x180/17735_UFZjgAiJ.jpg',
    'site/way_bicycle.jpg': 'https://cdn.tourradar.com/s3/serp/1436x180/17732_uFsrecGs.jpg',
    'site/way_family.jpg': 'https://cdn.tourradar.com/s3/serp/1436x180/17785_lgCUjqiQ.jpg',
    'site/trustpilot.png': 'https://cdn.tourradar.com/images/responsive/pw/footer_images/trustpilot.png',
    'site/trustpilot-almost-excellent.png': 'https://cdn.tourradar.com/images/responsive/pw/footer_images/trustpilot-almost-excellent.png',
    'site/wyse.png': 'https://cdn.tourradar.com/im/r/pw/footer_images/wyse.png',
    'site/asta.png': 'https://cdn.tourradar.com/im/r/pw/footer_images/asta.png',
    'site/tico.png': 'https://cdn.tourradar.com/images/responsive/pw/footer_images/tico.png',
    'site/ustoa.png': 'https://cdn.tourradar.com/im/r/pw/footer_images/ustoa.png',
    'site/clia.png': 'https://cdn.tourradar.com/im/r/pw/footer_images/clia.png',
    'site/adventure_travel.png': 'https://cdn.tourradar.com/im/r/pw/footer_images/adventure_travel.png',
    'site/favicon-32x32.png': 'https://cdn.tourradar.com/images/v1790348027/fav/favicon-32x32.png',
}

MAGIC = {
    '.jpg': (b'\xff\xd8', None),
    '.jpeg': (b'\xff\xd8', None),
    '.png': (b'\x89PNG\r\n\x1a\n', None),
    '.webp': (b'RIFF', b'WEBP'),
    '.gif': (b'GIF8', None),
}


def verify(local: str, data: bytes) -> bool:
    suffix = pathlib.Path(local).suffix.lower()
    pair = MAGIC.get(suffix)
    if pair:
        head, tail = pair
        if head and not data.startswith(head):
            return False
        if suffix == '.webp':
            if len(data) < 12 or data[8:12] != tail:
                return False
        elif tail and not data.endswith(tail):
            return False
    return len(data) > 120


def sniff_fix(local: str, data: bytes):
    suffix = pathlib.Path(local).suffix.lower()
    real = None
    if data.startswith(b'\xff\xd8'):
        real = '.jpg'
    elif data.startswith(b'\x89PNG'):
        real = '.png'
    elif data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        real = '.webp'
    elif data.startswith(b'GIF8'):
        real = '.gif'
    if real and real != suffix:
        return str(pathlib.Path(local).with_suffix(real))
    return None


def main():
    force = '--force' in sys.argv
    mapping = json.loads((SCRAPE / 'image_urls.json').read_text())
    mapping.update(SITE_IMAGES)
    ok = 0
    skip = 0
    fail = []
    ext_fixes = {}
    with httpx.Client(follow_redirects=True, timeout=40,
                      headers={'User-Agent': UA,
                               'Referer': 'https://www.tourradar.com/'}) as cx:
        items = sorted(mapping.items())
        for n, (local, url) in enumerate(items):
            out = IMG / local
            if out.exists() and not force:
                skip += 1
                continue
            try:
                r = cx.get(url)
                if r.status_code != 200:
                    fail.append((local, url, r.status_code))
                    continue
                data = r.content
                fixed = sniff_fix(local, data)
                if fixed:
                    ext_fixes[local] = fixed
                    local = fixed
                    out = IMG / local
                if not verify(local, data):
                    fail.append((local, url, 'bad-bytes'))
                    continue
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
                ok += 1
            except Exception as e:
                fail.append((local, url, str(e)[:60]))
            if n % 200 == 0:
                print(f"[{n}/{len(items)}] ok={ok} skip={skip} fail={len(fail)}", flush=True)
            time.sleep(0.05)
    (SCRAPE / 'image_ext_fixes.json').write_text(json.dumps(ext_fixes, indent=1, sort_keys=True))
    (SCRAPE / 'image_failures.json').write_text(json.dumps([f[0] for f in fail], indent=1))
    print(f"downloaded={ok} skipped={skip} failed={len(fail)} fixes={len(ext_fixes)}")
    for row in fail[:20]:
        print("FAIL:", row)
    if fail:
        sys.exit(1)


if __name__ == '__main__':
    main()
