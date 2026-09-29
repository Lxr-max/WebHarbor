#!/usr/bin/env python3
"""Download the real upstream images listed in scraped_data/image_manifest.json.

Fetches each file from its captured production CDN URL into
static/images/<path>, with retries and a polite delay. Idempotent: existing
non-empty files are skipped. Run AFTER scripts_dev/build_source_data.py.
"""
from __future__ import annotations

import pathlib
import sys
import time

import httpx

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent
MANIFEST = SITE / 'scraped_data' / 'image_manifest.json'
IMG_ROOT = SITE / 'static' / 'images'

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')


def main():
    manifest = json.loads(MANIFEST.read_text()) if (json := __import__('json')) else None
    ok = fail = skip = 0
    failures = []
    with httpx.Client(follow_redirects=True, timeout=30, headers={'User-Agent': UA}) as cx:
        for rel, url in sorted(manifest.items()):
            dest = IMG_ROOT / rel
            if dest.exists() and dest.stat().st_size > 1000:
                skip += 1
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            got = False
            for attempt in range(3):
                try:
                    r = cx.get(url)
                    r.raise_for_status()
                    if len(r.content) < 500:
                        raise RuntimeError(f'thin response {len(r.content)}b')
                    dest.write_bytes(r.content)
                    ok += 1
                    got = True
                    break
                except Exception as e:
                    time.sleep(2 + attempt * 2)
            if not got:
                fail += 1
                failures.append((rel, url))
    print(f'downloaded={ok} skipped={skip} failed={fail}')
    for rel, url in failures:
        print('  FAIL', rel, url[:90])
    return 1 if failures else 0


if __name__ == '__main__':
    import json  # noqa: F401  (imported lazily above)
    sys.exit(main())
