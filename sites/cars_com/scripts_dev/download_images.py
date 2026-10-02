#!/usr/bin/env python3
"""Download every managed image from its exact upstream URL and build
sites/cars_com/asset_inventory.json (path, bytes, sha256, source_url).

Sources: the SERP card galleries and vehicle-detail photo sets (the
cars.com image CDN platform.cstatic-images.com), research model pages
and compare pages. Every file is fetched from the exact upstream URL the
captured page rendered.

The output is deterministic: a listing's local file names depend only
on its listing id and the upstream photo order; downloads run in a
fixed thread pool for speed but every URL keeps its own destination,
and the final inventory is sorted by path.

Run:  python3 scripts_dev/download_images.py
"""
import hashlib
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SCRAP = os.path.join(ROOT, "scraped_data")
SRC = os.path.join(ROOT, "source_data")
IMG = os.path.join(ROOT, "static", "images", "upstream")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
      "Referer": "https://www.cars.com/"}

MAX_PHOTOS_PER_LISTING = 5
MAX_MODELS_PHOTOS = 4
WORKERS = 12


def load(path, default=None):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default if default is not None else {}


def safe_name(prefix, idx, url):
    ext = ".jpg"
    m = re.search(r"\.(jpe?g|png|webp)(?:$|\?)", url, re.I)
    if m:
        ext = "." + m.group(1).lower()
    return f"{prefix}-{idx:02d}{ext}"


def fetch(session, url, dest, tries=4):
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return True
    for attempt in range(tries):
        try:
            r = session.get(url, headers=UA, timeout=30)
            if r.status_code == 200 and len(r.content) > 1000:
                with open(dest, "wb") as f:
                    f.write(r.content)
                return True
        except Exception:
            pass
        time.sleep(1.0 * (attempt + 1))
    return False


def main():
    os.makedirs(IMG, exist_ok=True)
    session = requests.Session()
    inventory = []
    seen_sha = {}
    skipped_dups = 0
    failures = []

    # ---- the full fetch plan: (url, dest) pairs, deterministic order ----
    plan = []

    listings = load(os.path.join(SRC, "listings.json"), [])
    for row in listings:
        lid = row["listing_id"][:8]
        photos = (row.get("photos") or [])[:MAX_PHOTOS_PER_LISTING]
        for i, url in enumerate(photos):
            plan.append((url, os.path.join(IMG, safe_name(f"l-{lid}", i, url))))

    models = load(os.path.join(SRC, "models.json"), [])
    for row in models:
        slug = row.get("slug") or "model"
        photos = (row.get("photos") or [])[:MAX_MODELS_PHOTOS]
        for i, url in enumerate(photos):
            plan.append((url, os.path.join(IMG, safe_name(f"m-{slug[:40]}", i, url))))

    compares = load(os.path.join(SRC, "compares.json"), [])
    for row in compares:
        slug = (row.get("slug") or "cmp")[:40]
        photos = (row.get("photos") or [])[:2]
        for i, url in enumerate(photos):
            plan.append((url, os.path.join(IMG, safe_name(f"c-{slug}", i, url))))

    def work(item):
        url, dest = item
        ok = fetch(session, url, dest)
        return (url, dest, ok)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(work, plan))
    for url, dest, ok in results:
        if not ok:
            failures.append(url)
            if os.path.exists(dest) and os.path.getsize(dest) <= 1000:
                os.remove(dest)
            continue
        data = open(dest, "rb").read()
        sha = hashlib.sha256(data).hexdigest()
        if sha in seen_sha:
            os.remove(dest)
            skipped_dups += 1
            continue
        seen_sha[sha] = os.path.basename(dest)
        inventory.append({"path": f"static/images/upstream/{os.path.basename(dest)}",
                          "bytes": len(data), "sha256": sha,
                          "source_url": url})

    # ---- bind the local paths back onto the tracked source data ----
    by_url = {}
    for url, dest, ok in results:
        if ok:
            by_url[url] = f"static/images/upstream/{os.path.basename(dest)}"
    for row in listings:
        local = []
        for url in (row.get("photos") or [])[:MAX_PHOTOS_PER_LISTING]:
            if url in by_url:
                local.append(by_url[url])
        row["_local_photos"] = local
    with open(os.path.join(SRC, "listings.json"), "w") as f:
        json.dump(listings, f, indent=1)
    for row in models:
        local = []
        for url in (row.get("photos") or [])[:MAX_MODELS_PHOTOS]:
            if url in by_url:
                local.append(by_url[url])
        row["_local_photos"] = local
    with open(os.path.join(SRC, "models.json"), "w") as f:
        json.dump(models, f, indent=1)
    for row in compares:
        local = []
        for url in (row.get("photos") or [])[:2]:
            if url in by_url:
                local.append(by_url[url])
        row["_local_photos"] = local
    with open(os.path.join(SRC, "compares.json"), "w") as f:
        json.dump(compares, f, indent=1)

    inventory.sort(key=lambda r: r["path"])
    with open(os.path.join(ROOT, "asset_inventory.json"), "w") as f:
        json.dump({"schema_version": 1, "asset_count": len(inventory),
                   "assets": inventory}, f, indent=1)
    print(f"[download_images] {len(inventory)} images, {skipped_dups} duplicates skipped, "
          f"{len(failures)} failures")
    if failures:
        for u in failures[:10]:
            print(f"  [FAIL] {u[:120]}", file=sys.stderr)


if __name__ == "__main__":
    main()
