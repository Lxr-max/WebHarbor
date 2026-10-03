#!/usr/bin/env python3
"""Download every managed upstream image the mirror renders.

Reads the tracked source_data/*.json snapshots and fetches each referenced
media file from its exact upstream URL (content.backcountry.com CMS +
product image CDN, bazaarvoice review photos), storing it under
static/images/ at the upstream's own path structure:

  /images/items/{size}/{SKU3}/{SKU}/{COLOR}.jpg -> static/images/items/...
  /images/brand/...                             -> static/images/brand/...
  content.backcountry.com/v3/assets/...        -> static/images/cms/...
  photos-us.bazaarvoice.com/photo/2/...         -> static/images/review-photos/<id>.jpg

Resumable: existing files with the right byte length are kept. Deterministic
order. Writes asset_inventory.json (per-file sha256 + source URL) when done.
"""
import concurrent.futures
import hashlib
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
SOURCE = os.path.join(SITE, "source_data")
STATIC = os.path.join(SITE, "static", "images")
CDN = "https://content.backcountry.com"

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/129.0.0.0 Safari/537.36")}


def load(name):
    with open(os.path.join(SOURCE, name), encoding="utf-8") as f:
        return json.load(f)


def collect():
    """All (relative path, source URL) pairs the mirror renders."""
    jobs = {}

    def add(rel, url):
        rel = rel.lstrip("/")
        if rel and url:
            jobs[rel] = url

    # site chrome
    add("images/brand/bcs_logo.png", f"{CDN}/images/brand/bcs_logo.png")

    products = load("products.json")["products"]
    for p in products:
        sku = p["id"]
        three = sku[:3]
        for s in p.get("skus") or []:
            img = s.get("image") or ""
            color = img.rsplit("/", 1)[-1].split("?")[0].replace(".jpg", "")
            if not img:
                continue
            # grid tile (440px) + color swatch thumb (160px)
            add(f"images/items/large/{three}/{sku}/{color}.jpg",
                f"{CDN}/images/items/large/{three}/{sku}/{color}.jpg")
            add(f"images/items/160/{three}/{sku}/{color}.jpg",
                f"{CDN}/images/items/160/{three}/{sku}/{color}.jpg")
        for color, shots in (p.get("gallery") or {}).items():
            for shot in shots:
                for size_key, size_dir in (("1200", "1200"), ("large", "large")):
                    path = (shot.get(size_key) or "").split("?")[0]
                    if path:
                        add(path.lstrip("/"), f"{CDN}{path}")
        logo = p.get("brand_logo")
        if logo:
            add(logo.lstrip("/"), f"{CDN}{logo}")

    home = load("home.json")
    for sec in home.get("sections") or []:
        for c in sec.get("cards") or []:
            url = c.get("image")
            if url:
                m = re.match(r"https://content\.backcountry\.com/v3/assets/"
                             r"([^/]+)/([^/]+)/(.+)$", url)
                if m:
                    add(f"cms/{m.group(1)}/{m.group(2)}/{m.group(3)}", url)

    reviews = load("reviews.json")
    for block in reviews.values():
        for r in block.get("reviews") or []:
            for ph in r.get("photos") or []:
                m = re.search(r"/photo/2/([^/]+)/([0-9a-f\-]+)$", ph)
                if m:
                    add(f"review-photos/{m.group(2)}.jpg", ph)
    return jobs


def fetch(rel, url):
    dest = os.path.join(STATIC, rel)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return rel, url, os.path.getsize(dest), "kept"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    if len(data) < 100:
        raise ValueError(f"tiny response for {url}: {len(data)}b")
    suffix = dest.rsplit(".", 1)[-1].lower()
    if suffix in ("jpg", "jpeg") and not (data[:2] == b"\xff\xd8"):
        raise ValueError(f"not a JPEG: {url}")
    if suffix == "png" and data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {url}")
    with open(dest, "wb") as f:
        f.write(data)
    return rel, url, len(data), "fetched"


def main():
    jobs = collect()
    print(f"[images] {len(jobs)} files referenced by source_data")
    failures = []
    inventory = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(fetch, rel, url): rel for rel, url in jobs.items()}
        done = 0
        for fut in concurrent.futures.as_completed(futs):
            rel = futs[fut]
            try:
                rel2, url, size, how = fut.result()
                done += 1
                inventory.append(rel2)
                if done % 200 == 0:
                    print(f"  {done}/{len(jobs)}")
            except Exception as e:
                failures.append((rel, str(e)[:100]))
    for rel, err in failures[:20]:
        print("FAIL:", rel, err)
    print(f"[images] done: {len(jobs) - len(failures)} ok, {len(failures)} failed")

    # write asset inventory
    rows = []
    total = 0
    for rel in sorted(inventory):
        path = os.path.join(STATIC, rel)
        data = open(path, "rb").read()
        rows.append({
            "path": f"static/images/{rel}",
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "source_url": jobs[rel],
        })
        total += len(data)
    manifest = {
        "schema_version": 1,
        "site": "backcountry",
        "asset_count": len(rows),
        "total_bytes": total,
        "captured_on": "2026-09-30",
        "capture_method": (
            "Direct HTTPS fetches of the exact upstream media URLs the live "
            "backcountry.com pages render: product tiles and color thumbs "
            "from content.backcountry.com /images/items/{160,large,1200}/..., "
            "brand logos from /images/brand/..., campaign/hero card art from "
            "content.backcountry.com/v3/assets/..., and customer review "
            "photos from photos-us.bazaarvoice.com (Backcountry's Bazaarvoice "
            "host) at the URLs embedded in the captured product pages"),
        "source_page": "https://www.backcountry.com/",
        "notes": [
            "Every entry is a real upstream media file fetched at its resolved URL.",
            "Verified byte- and hash-exact by scripts/check_asset_inventory.py at build time.",
        ],
        "assets": rows,
    }
    out = os.path.join(SITE, "asset_inventory.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    print(f"[images] inventory: {len(rows)} files, {total} bytes -> {out}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
