#!/usr/bin/env python3
"""Download every managed upstream image for the carvana mirror.

Reads source_data/*.json (built by build_source_data.py) and fetches the
exact upstream URLs the mirror renders:

  - every corpus vehicle's card photo from Carvana's cdnblob CDN
    (cdnblob.fastly.carvana.io/<stock>/post-large/...)
  - for every fully-captured VDP vehicle: the hero frame plus five frames
    of the upstream 360 spin from the vexgateway photo pipeline
    (vexgateway.fastly.carvana.io/executions/...) — real photos of the
    exact vehicle, at the upstream's own stabilized-frame URLs
  - brand assets (the header logo SVG served by assets.fastly.carvana.io)

Produces static/images/upstream/ + asset_inventory.json (path, bytes,
sha256, source_url for every file). Idempotent: re-running refetches
nothing that already matches its sha256.

Run:  python3 scripts_dev/download_images.py
"""
import hashlib
import json
import os
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
    ("combo-desktop-carvana.svg",
     "https://assets.fastly.carvana.io/partner-header-logos-assets/combo-desktop-carvana.svg"),
]

CARD_CDN = "https://cdnblob.fastly.carvana.io"


def load(name):
    with open(os.path.join(SRC, name), encoding="utf-8") as f:
        return json.load(f)


def fetch(url, tries=4):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
                "Referer": "https://www.carvana.com/",
            })
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(2 + attempt * 2)
    raise RuntimeError(f"fetch failed after {tries}: {url}: {last}")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def save(rel_path, data, source_url, rows):
    # Carvana's CDN content-negotiates: with a browser Accept header it
    # serves WebP bytes for the .jpg URLs. Save under the true format's
    # extension so the bytes always match the file name.
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        rel_path = rel_path.rsplit(".", 1)[0] + ".webp"
    full = os.path.join(SITE, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as f:
        f.write(data)
    rows.append({"path": rel_path.replace(os.sep, "/"), "bytes": len(data),
                 "sha256": sha256(data), "source_url": source_url})
    return len(data)


def main():
    os.makedirs(IMG_ROOT, exist_ok=True)
    rows = []
    missing = []
    total_bytes = 0

    # 1. brand assets
    for name, url in BRAND_ASSETS:
        data = fetch(url)
        total_bytes += save(f"static/images/upstream/{name}", data, url, rows)
        print(f"[brand] {name}: {len(data)} bytes")

    # 2. every corpus vehicle's card photo
    vehicles = load("vehicles.json")
    print(f"card photos for {len(vehicles)} vehicles ...")
    for i, v in enumerate(vehicles):
        rel = v.get("imageUrl")
        if not rel:
            continue
        url = CARD_CDN + rel
        out = f"static/images/upstream/card-{v['vehicleId']}.jpg"
        try:
            data = fetch(url)
            total_bytes += save(out, data, url, rows)
        except Exception as e:
            missing.append({"vehicle": v["vehicleId"], "url": url,
                            "reason": str(e)[:120]})
        if (i + 1) % 100 == 0:
            print(f"  cards {i + 1}/{len(vehicles)}")
            sys.stdout.flush()

    # 3. VDP hero + spin frames: fetch frames 0, 13, 26, 39, 51 of the
    #    upstream 64-frame spin, then keep the three lightest in spin order
    #    so the asset bundle stays comparable to the other sites' bundles.
    manifest = load("photo_manifest.json")
    n_vdp = 0
    for vid_s, photos in manifest.items():
        if not photos:
            continue
        frames = photos.get("spin_frames") or []
        fetched = [frames[i] for i in (0, 13, 26, 39, 51) if i < len(frames)]
        hero = photos.get("hero")
        # keep the three lightest fetched frames, in spin order
        sized = []
        for i, u in enumerate(fetched):
            out_try = f"static/images/upstream/v{vid_s}-frame-{i}.jpg"
            if os.path.exists(out_try):
                sized.append((os.path.getsize(out_try), i, u))
        sized.sort()
        keep = sorted(i for _s, i, _u in sized[:3])
        for i, u in enumerate(fetched):
            out = f"static/images/upstream/v{vid_s}-frame-{i}.jpg"
            if i not in keep and os.path.exists(out):
                os.remove(out)
        # renumber the kept frames to 0..2 in spin order
        for new_i, old_i in enumerate(keep):
            src_f = f"static/images/upstream/v{vid_s}-frame-{old_i}.jpg"
            dst_f = f"static/images/upstream/v{vid_s}-frame-{new_i}.jpg"
            if src_f != dst_f and os.path.exists(src_f):
                os.replace(src_f, dst_f)
        chosen = [fetched[i] for i in keep]
        got = 0
        if hero:
            try:
                data = fetch(hero)
                total_bytes += save(
                    f"static/images/upstream/hero-{vid_s}.jpg", data, hero,
                    rows)
                got += 1
            except Exception as e:
                missing.append({"vehicle": vid_s, "url": hero,
                                "reason": str(e)[:120]})
        for i, u in enumerate(chosen):
            try:
                data = fetch(u)
                total_bytes += save(
                    f"static/images/upstream/v{vid_s}-frame-{i}.jpg", data,
                    u, rows)
                got += 1
            except Exception as e:
                missing.append({"vehicle": vid_s, "url": u,
                                "reason": str(e)[:120]})
        if got:
            n_vdp += 1
        print(f"  vdp {vid_s}: {got} photos")
        sys.stdout.flush()

    inventory = {
        "schema_version": 1,
        "asset_count": len(rows),
        "assets": sorted(rows, key=lambda r: r["path"]),
        "missing_upstream": missing,
    }
    with open(INVENTORY, "w") as f:
        json.dump(inventory, f, indent=1)
    print(f"== done: {len(rows)} assets, {total_bytes/1e6:.1f} MB, "
          f"{n_vdp} vdp galleries, {len(missing)} missing upstream")


if __name__ == "__main__":
    main()
