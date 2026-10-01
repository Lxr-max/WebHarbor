#!/usr/bin/env python3
"""Generate asset_inventory.json for the stanford_university mirror.

Every image under static/images/upstream/ is a real upstream download; this
manifest records its path, byte length, sha256 and the exact source URL
(byte-identical upstream duplicates are recorded with alias URLs).
"""
import hashlib
import json
import os
import sys

SITE = '/data/zhaoyang-user-projects/websyn/WebHarbor/_wh_review_tools/orch/contribute/build/stanford_university/sites/stanford_university'
IMAGES = os.path.join(SITE, 'static', 'images', 'upstream')

manifest = json.load(open('/tmp/stanford_scrape/image_download_manifest.json'))
url_by_name = {}
for row in manifest:
    if row.get('filename'):
        url_by_name.setdefault(row['filename'], []).append(row['url'])
# the upstream CDN serves WebP bytes for some .jpg URLs; the renamed local
# file keeps the original upstream source URL
for stem, url in {
    'news_stanford-global-studies-photo-contest-winners.webp':
        'https://news.stanford.edu/__data/assets/image/0032/188087/between_light_and_time_2023_south_korea_0.jpeg.webp',
}.items():
    url_by_name.setdefault(stem, []).append(url)

assets = []
for cat in sorted(os.listdir(IMAGES)):
    cat_dir = os.path.join(IMAGES, cat)
    if not os.path.isdir(cat_dir):
        continue
    for fname in sorted(os.listdir(cat_dir)):
        path = os.path.join(cat_dir, fname)
        data = open(path, 'rb').read()
        rel = f'static/images/upstream/{cat}/{fname}'
        urls = url_by_name.get(fname) or []
        row = {
            'path': rel,
            'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest(),
            'source_url': urls[0] if urls else '',
        }
        if len(urls) > 1:
            row['alias_source_urls'] = urls[1:]
        assets.append(row)

assets.sort(key=lambda r: r['path'])
out = {
    'schema_version': 1,
    'asset_count': len(assets),
    'assets': assets,
}
with open(os.path.join(SITE, 'asset_inventory.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=1, sort_keys=True)
print('assets:', len(assets))
print('total bytes:', sum(r['bytes'] for r in assets))
missing_urls = [r['path'] for r in assets if not r['source_url']]
print('rows without source url:', len(missing_urls), missing_urls[:5])
