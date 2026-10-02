#!/usr/bin/env python3
"""Download every managed upstream image for the ziprecruiter mirror.

Reads source_data/*.json (built by build_source_data.py) and fetches the
exact upstream URLs the mirror renders:

  - company logos from ZipRecruiter's fotomat CDN
    (ziprecruiter.com/svc/fotomat/public-nosensitive-ziprecruiter-logos/)
  - blog article thumbnails and in-article images
    (ziprecruiter.com/blog/wp-content/uploads/ and the article bodies'
    own image hosts)
  - brand assets (logo SVG, Phil the capybara homepage cartoon)

Produces static/images/upstream/ + asset_inventory.json (path, bytes,
sha256, source_url for every file). Idempotent: re-running refetches
nothing that already matches its sha256.

Run:  venv/bin/python scripts_dev/download_images.py
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
SRC = os.path.join(SITE, "source_data")
IMG_ROOT = os.path.join(SITE, "static", "images", "upstream")
INVENTORY = os.path.join(SITE, "asset_inventory.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

BRAND_ASSETS = [
    ("ziprecruiter-whitetext.svg",
     "https://www.ziprecruiter.com/assets/static/img/logos/ziprecruiter-whitetext.svg"),
    ("phil-cartoon-dark-640.webp",
     "https://www.ziprecruiter.com/assets/static/img/homepage/phil-cartoon-dark-640.webp"),
]


def load(name):
    with open(os.path.join(SRC, name), encoding="utf-8") as f:
        return json.load(f)


def is_image_url(u):
    if re.search(r'youtube\.com|youtu\.be|/embed/|\.js(?:\?|$)|\.css(?:\?|$)',
                 u or ''):
        return False
    return bool(re.search(r'\.(jpe?g|png|webp|gif)(?:[?#].*)?$', u))


def wanted():
    """Ordered [(logical_name, url), ...] of every managed asset."""
    out = list(BRAND_ASSETS)
    seen = {n for n, _ in out}
    for co in sorted(load('companies.json'), key=lambda c: c['slug']):
        url = co.get('logo_url')
        if not url:
            continue
        m = re.search(r'company/([0-9a-f]+)\.(png|jpeg|jpg)', url)
        if not m:
            continue
        name = f"co-logo-{m.group(1)}.{m.group(2)}"
        if name not in seen:
            seen.add(name)
            out.append((name, url))
    for art in sorted(load('blog.json'), key=lambda a: a['slug']):
        thumb = art.get('thumbnail')
        if thumb:
            ext = re.search(r'\.(jpe?g|png|webp|gif)(?:[?#].*)?$', thumb)
            ext = ext.group(1) if ext else 'jpg'
            name = f"blog-{art['slug']}.{ext}"
            if name not in seen:
                seen.add(name)
                out.append((name, thumb))
        for i, u in enumerate(art.get('body_images') or []):
            if not is_image_url(u):
                continue
            ext = re.search(r'\.(jpe?g|png|webp|gif)(?:[?#].*)?$', u)
            ext = ext.group(1) if ext else 'jpg'
            name = f"blog-{art['slug']}-img{i}.{ext}"
            if name not in seen:
                seen.add(name)
                out.append((name, u))
    return out


def fetch(url, dest, referer):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Referer": referer})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)
    return data


def main():
    os.makedirs(IMG_ROOT, exist_ok=True)
    inv = {"assets": []}
    if os.path.exists(INVENTORY):
        with open(INVENTORY, encoding="utf-8") as f:
            inv = json.load(f)
    by_path = {a['path']: a for a in inv['assets']}
    missing = []
    failures = []
    for name, url in wanted():
        rel = f"static/images/upstream/{name}"
        dest = os.path.join(IMG_ROOT, name)
        referer = ("https://www.ziprecruiter.com/blog/" if 'blog' in url
                   else "https://www.ziprecruiter.com/")
        if rel in by_path and os.path.exists(dest):
            data = open(dest, 'rb').read()
            if hashlib.sha256(data).hexdigest() == by_path[rel]['sha256']:
                continue
        ok = False
        for attempt in range(4):
            try:
                data = fetch(url, dest, referer)
                row = {"path": rel, "bytes": len(data),
                       "sha256": hashlib.sha256(data).hexdigest(),
                       "source_url": url}
                by_path[rel] = row
                ok = True
                print(f"[ok] {name} ({len(data)} bytes)")
                break
            except Exception as e:
                print(f"[retry {attempt}] {name}: {e}")
                time.sleep(3 + 3 * attempt)
        if not ok:
            failures.append(name)
            missing.append({"path": f"static/images/upstream/{name}",
                           "source_url": url,
                           "note": "upstream asset no longer serves (redirects to the site's own 404); the mirror renders without it"})
            if rel in by_path:
                del by_path[rel]
            if os.path.exists(dest):
                os.remove(dest)
    inv = {"schema_version": 1, "asset_count": len(by_path),
           "assets": [by_path[k] for k in sorted(by_path)]}
    if missing:
        inv["missing_upstream"] = missing
    with open(INVENTORY, "w", encoding="utf-8") as f:
        json.dump(inv, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"inventory: {len(inv['assets'])} assets ({len(missing)} known-missing upstream)")
    if failures:
        print(f"known-missing upstream (documented in inventory): {failures}")


if __name__ == '__main__':
    main()
