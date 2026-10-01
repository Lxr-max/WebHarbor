#!/usr/bin/env python3
"""Select the image subset to download and emit the download manifest."""
import json
import os

SRC = '/tmp/stanford_scrape/source_data'
OUT = '/tmp/stanford_scrape/image_download_manifest.json'

manifest = []


def add(category, url, filename):
    manifest.append({'category': category, 'url': url, 'filename': filename})


# home images
home = json.load(open(f'{SRC}/home.json'))
for img in home['images']:
    add('home', img['url'], img['filename'])

# icons
for icon in ['favicon.ico', 'icon1.png', 'icon2.png', 'icon3.png', 'icon4.png', 'icon5.png']:
    add('icons', f'https://www.stanford.edu/{icon}', icon)
add('icons', 'https://coursedog-images-public.s3.us-east-2.amazonaws.com/stanford/Block_S_1_color_red.png', 'block_s_red.png')

# admissions
ADM = [
    ('https://admission.stanford.edu/assets/cardinal/images/banners/apply/banner.jpg', 'adm_apply_banner.jpg'),
    ('https://admission.stanford.edu/assets/cardinal/images/banners/plan/bannerL.jpg', 'adm_plan_banner.jpg'),
    ('https://admission.stanford.edu/assets/cardinal/images/banners/plan/admits-walking-quad.jpg', 'adm_admits_walking_quad.jpg'),
    ('https://admission.stanford.edu/assets/cardinal/images/banners/plan/aw-checkin.jpg', 'adm_aw_checkin.jpg'),
    ('https://admission.stanford.edu/assets/cardinal/images/banners/plan/studying-meyer-green.jpg', 'adm_studying_meyer_green.jpg'),
    ('https://admission.stanford.edu/assets/cardinal/images/banners/plan/tree-green-library.jpg', 'adm_tree_green_library.jpg'),
    ('https://admission.stanford.edu/assets/cardinal/images/afford_banner1.jpg', 'adm_afford_banner.jpg'),
    ('https://admission.stanford.edu/assets/cardinal/images/afford-art-gallery.jpg', 'adm_afford_art_gallery.jpg'),
    ('https://admission.stanford.edu/assets/cardinal/images/afford-rodin-sculpture-garden.jpg', 'adm_afford_rodin.jpg'),
    ('https://admission.stanford.edu/assets/cardinal/images/afford-white-plaza.jpg', 'adm_afford_white_plaza.jpg'),
    ('https://admission.stanford.edu/assets/cardinal/images/publications/stanford_viewbook_cover.jpg', 'adm_viewbook.jpg'),
    ('https://admission.stanford.edu/assets/cardinal/images/org/thumb_application_deadlines_fee2.jpg', 'adm_thumb_deadlines.jpg'),
    ('https://admission.stanford.edu/assets/cardinal/images/org/thumb_freshman_requirements_process2.jpg', 'adm_thumb_requirements.jpg'),
    ('https://admission.stanford.edu/assets/cardinal/images/stanford-white@2x.png', 'stanford_white.png'),
]
for url, name in ADM:
    add('admissions', url, name)

# libraries
libs = json.load(open(f'{SRC}/libraries.json'))
for lib in libs['libraries']:
    slug = lib['slug']
    add('libraries', f'https://library.stanford.edu/libraries/{slug}', None)  # placeholder; replaced below
manifest = [m for m in manifest if m['category'] != 'libraries']
import re
for lib in libs['libraries']:
    slug = lib['slug']
    p = f'/tmp/stanford_scrape/libraries/{slug}.html'
    if not os.path.exists(p):
        continue
    lraw = open(p).read()
    m = re.search(r'<img[^>]+src="/_next/image\?url=([^&"]+)&', lraw)
    if m:
        from urllib.parse import unquote
        add('libraries', unquote(m.group(1)), f'library_{slug}.jpg')

# faculty photos: up to 12 per department, prefer with photo + bio
faculty = json.load(open(f'{SRC}/faculty.json'))
by_dept = {}
for p in faculty:
    by_dept.setdefault(p['department'], []).append(p)
for dept, members in sorted(by_dept.items()):
    scored = sorted(members, key=lambda m: (not m['photo_url'], not (m['bio'] or ''), -(m['publication_count'] or 0)))
    for m in scored[:12]:
        if m['photo_url']:
            add('faculty', m['photo_url'], f"faculty_{m['profile_id']}.jpg")

# events photos: up to 260 (already sorted featured/verified/photo first)
events = json.load(open(f'{SRC}/events.json'))
n = 0
for e in events:
    if n >= 260:
        break
    if e.get('photo_url'):
        add('events', e['photo_url'], f"event_{e['id']}.jpg")
        n += 1

# news og:images: 150 most recent with images
news = json.load(open(f'{SRC}/news.json'))
n = 0
seen = set()
for r in news:
    if n >= 150:
        break
    url = r.get('og_image')
    if not url or url in seen:
        continue
    seen.add(url)
    slug = r['slug']
    ext = '.jpg'
    m = re.search(r'\.(jpe?g|png|webp|gif)', url, re.I)
    if m:
        ext = '.' + m.group(1).lower().replace('jpeg', 'jpg')
    add('news', url, f'news_{slug}{ext}')
    n += 1

json.dump(manifest, open(OUT, 'w'), indent=1)
from collections import Counter
print(Counter(m['category'] for m in manifest))
print('total:', len(manifest))
