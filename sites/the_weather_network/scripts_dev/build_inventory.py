#!/usr/bin/env python3
"""Build the tracked inline_images.json map + asset_inventory.json manifest.

Inputs:
  - /tmp capture output asset_manifest_raw.json (true source URLs for the
    assets downloaded during the 2026-09-26/27 capture passes), if present
  - static/images/inline/* (inline article body images, content-addressed by
    sha1 of the upstream URL base)
  - source_data_news.json (the upstream URL -> local file mapping for the
    inline corpus)

Outputs (both tracked in git):
  - inline_images.json: {upstream_url_base: {path, source_url, bytes, sha256}}
    — consumed by app.py render_body to rewrite body image references.
  - asset_inventory.json: exact-coverage manifest of every file under
    static/images/ + static/external_cache/ (check_asset_inventory contract).
"""
import hashlib
import json
import os
import re

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAPTURE = '/tmp/twn_scrape/out/asset_manifest_raw.json'

EXTRA_SOURCES = {
    # assets fetched in follow-up passes, with their true upstream URLs
    'maps/basemap_calgary.webp':
        'https://maps-basemap.pelmorex.com/styles/twn-dark-v2/static/-114.05,51.028,7/600x500@2x.webp',
    'maps/basemap_victoria.webp':
        'https://maps-basemap.pelmorex.com/styles/twn-dark-v2/static/-123.347,48.427,7/600x500@2x.webp',
    'maps/radar_calgary.png':
        'https://maps-api.pelmorex.com/fuse_image?layer=radar&zoom=7&lat=51.028&lon=-114.05&width=600&height=500',
    'maps/radar_victoria.png':
        'https://maps-api.pelmorex.com/fuse_image?layer=radar&zoom=7&lat=48.427&lon=-123.347&width=600&height=500',
}

TRACKING = ('counter.theconversation.com', 'engagefront', '/pxl')


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def collect_body_urls():
    """Every upstream image URL referenced from an article body (normalized)."""
    news = json.load(open(os.path.join(SITE, 'source_data_news.json')))
    urls = set()
    for a in news['articles']:
        b = a['body']
        refs = [m.group(2) for m in re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', b)]
        refs += [m.group(1) for m in re.finditer(r'<img[^>]+src="([^"]+)"', b)]
        for m in re.finditer(r'<a href="([^"]+)"', b):
            u = m.group(1)
            if re.search(r'\.(jpe?g|png|webp|gif)(\?|$)', u, re.I):
                refs.append(u)
        for u in refs:
            u = u.strip().replace('&amp;', '&')
            if u.startswith('//'):
                u = 'https:' + u
            u = u.split('?')[0]
            if not u.startswith('https://'):
                continue
            if not re.search(r'\.(jpe?g|png|webp|gif)$', u, re.I):
                continue
            if any(t in u for t in TRACKING):
                continue
            urls.add(u)
    return sorted(urls)


def build_inline_map():
    urls = collect_body_urls()
    mapping, missing = {}, []
    for u in urls:
        h = hashlib.sha1(u.encode()).hexdigest()[:16]
        found = None
        for ext in ('.webp', '.jpg', '.png', '.gif'):
            p = os.path.join(SITE, 'static', 'images', 'inline', h + ext)
            if os.path.exists(p):
                found = p
                break
        if not found:
            missing.append(u)
            continue
        data = open(found, 'rb').read()
        mapping[u] = {
            'path': f'inline/{h}{os.path.splitext(found)[1]}',
            'source_url': u,
            'bytes': len(data),
            'sha256': sha256(data),
        }
    with open(os.path.join(SITE, 'inline_images.json'), 'w') as fh:
        json.dump(mapping, fh, indent=1, sort_keys=True)
    print('inline map entries:', len(mapping), 'missing:', len(missing))
    json.dump(missing, open('/tmp/twn_scrape/out/map_missing.json', 'w'), indent=1)
    return mapping


def build_inventory(mapping):
    capture = {}
    if os.path.exists(CAPTURE):
        capture = json.load(open(CAPTURE))
    rows = []
    roots = ('static/images', 'static/external_cache')
    for root in roots:
        base = os.path.join(SITE, root)
        if not os.path.isdir(base):
            continue
        for dirpath, _dirs, files in os.walk(base):
            for f in sorted(files):
                if f == '.gitkeep':
                    continue
                p = os.path.join(dirpath, f)
                rel = os.path.relpath(p, SITE)
                data = open(p, 'rb').read()
                rel_key = rel.replace('static/images/', '')
                src = None
                if rel.startswith('static/images/inline/'):
                    src = {m['path']: m['source_url']
                           for m in mapping.values()}.get(rel_key)
                elif rel_key in capture:
                    src = capture[rel_key].get('source_url')
                elif rel_key in EXTRA_SOURCES:
                    src = EXTRA_SOURCES[rel_key]
                if not src or not src.startswith('https://'):
                    raise SystemExit(f'no upstream source URL for {rel}')
                rows.append({
                    'path': rel,
                    'bytes': len(data),
                    'sha256': sha256(data),
                    'source_url': src,
                })
    rows.sort(key=lambda r: r['path'])
    inv = {
        'schema_version': 1,
        'site': 'the_weather_network',
        'asset_count': len(rows),
        'total_bytes': sum(r['bytes'] for r in rows),
        'captured_on': '2026-09-26/27',
        'capture_method': ('Playwright-rendered pages plus direct HTTP fetches of '
                           'the resolved media URLs (images.twnmm.com and j.theweathernetwork.com '
                           'CDNs, Pelmorex public map APIs, jwplayer poster API, and the '
                           'third-party CDNs the upstream articles embed: theconversation, '
                           'wikimedia, cbc, contentful, imgix)'),
        'source_page': 'https://www.theweathernetwork.com/',
        'assets': rows,
    }
    with open(os.path.join(SITE, 'asset_inventory.json'), 'w') as fh:
        json.dump(inv, fh, indent=1)
    print('inventory assets:', len(rows), 'total bytes:', inv['total_bytes'])


if __name__ == '__main__':
    build_inventory(build_inline_map())
