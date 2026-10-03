#!/usr/bin/env python3
"""Regenerate the tracked asset inventory for the Ticketmaster mirror.

Walks static/images, records every managed asset with its byte size, SHA-256
digest and the upstream https URL it was captured from, and validates the
image framing (JPEG/PNG/GIF headers) the same way the repo-level
scripts/check_asset_inventory.py gate does. The URL map is derived from the
capture manifest produced by the staging pass (staged_manifest.json) plus the
homepage city-tile URLs; run scripts_dev/build_source_data.py first when
re-capturing assets.
"""
import hashlib
import json
import os
import pathlib
import re
import sys

SITE = pathlib.Path(__file__).resolve().parent.parent
IMG_ROOT = SITE / 'static' / 'images'

# upstream URL provenance map captured on 2026-09-27 (tracked alongside this
# script so the inventory stays reproducible without the scrape workspace)
STAGED = json.loads((SITE / 'scripts_dev' / 'staged_manifest.json').read_text())
CITY_URLS = {slug.replace('/discover/', ''): url for slug, name, url in
             json.loads((SITE / 'scripts_dev' / 'city_urls.json').read_text())}


def source_url(rel):
    """Map a staged path back to the upstream URL it was downloaded from."""
    if rel in STAGED:
        return STAGED[rel]
    if rel.startswith('static/images/cities/'):
        slug = pathlib.Path(rel).stem.replace('city_', '')
        return CITY_URLS.get(slug)
    return None


def verify_format(path, data):
    suffix = path.suffix.lower()
    if suffix in ('.jpg', '.jpeg'):
        if not (data[:2] == b'\xff\xd8' and data[-2:] == b'\xff\xd9'):
            raise ValueError(f'invalid JPEG framing: {path}')
    elif suffix == '.png':
        if data[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError(f'invalid PNG header: {path}')
    elif suffix == '.gif':
        if data[:3] != b'GIF':
            raise ValueError(f'invalid GIF header: {path}')
    else:
        raise ValueError(f'unexpected asset suffix: {path}')


def main():
    rows = []
    for path in sorted(IMG_ROOT.rglob('*')):
        if not path.is_file() or path.name == '.gitkeep' or path.name.endswith('.json'):
            continue
        rel = str(path.relative_to(SITE))
        data = path.read_bytes()
        verify_format(path, data)
        url = source_url(rel)
        if not url or not url.startswith('https://'):
            raise ValueError(f'no upstream source URL recorded for {rel}')
        rows.append({
            'path': rel,
            'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest(),
            'source_url': url,
        })
    manifest = {
        'schema_version': 1,
        'site': 'ticketmaster',
        'captured': '2026-09-27',
        'asset_count': len(rows),
        'assets': rows,
    }
    (SITE / 'asset_inventory.json').write_text(json.dumps(manifest, indent=1) + '\n')
    print(f'[inventory] {len(rows)} assets recorded')
    if len(sys.argv) > 1 and sys.argv[1] == '--check':
        expected = {r['path'] for r in rows}
        actual = {str(p.relative_to(SITE)) for p in IMG_ROOT.rglob('*')
                  if p.is_file() and p.name != '.gitkeep' and not p.name.endswith('.json')}
        assert expected == actual, (expected ^ actual)


if __name__ == '__main__':
    main()
