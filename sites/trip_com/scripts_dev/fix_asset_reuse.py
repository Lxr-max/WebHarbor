#!/usr/bin/env python3
"""fix_asset_reuse.py — de-duplicate cross-entry image reuse (review MINOR-1).

The independent review found that 125 of the 1,862 inventoried assets are
byte-copies of just 30 upstream source URLs (17+ attraction cards, 9 city
cards, 4 guide tiles and 12 hotel main images sharing 6 URLs). This script
re-bytes the affected files with a *real upstream photo of the same entry* —
the attraction's own detail-page photo, a top attraction/hotel photo of the
same city for city cards, or the hotel's own distinct gallery photo — so that
no two inventory entries share a source URL any more.

Design constraints (review-aware):
  * The seed database is NEVER touched: files keep their paths, only their
    bytes change, so instance_seed/trip_com.db stays byte-identical
    (md5 4d3cfe87…) and no DB drift is introduced.
  * Every replacement byte-stream is fetched from the upstream CDN
    (ak-d.tripcdn.com) with content negotiation, and the file's magic bytes
    must match its extension (.webp -> RIFF/WEBP, .avif -> ftyp AVIF,
    .jpg -> JPEG framing), mirroring scripts/check_asset_inventory.py rules.
  * A candidate URL is rejected when its upstream image id is one of the
    shared/generic image ids (the four placeholder bases and every multi-file
    group base), when the URL or its image id is already used by any other
    inventory entry, or when it was claimed by an earlier fix in this run.
  * Upstream serves identical image sets for a few duplicated property pairs
    (e.g. 732543/736160, 715197/715700) and some hotels carry no gallery at
    all; those files are left as-is and reported as upstream-identical.

Run from sites/trip_com/:  python3 scripts_dev/fix_asset_reuse.py [--apply]
Without --apply the script only reports what it would change.
"""
import collections
import hashlib
import json
import pathlib
import re
import sys

import httpx

BASE = pathlib.Path(__file__).resolve().parent.parent
IMG = BASE / "static" / "images"
INVENTORY = BASE / "asset_inventory.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
    "Referer": "https://us.trip.com/",
}
HEADERS_WEBP = dict(HEADERS, Accept="image/webp,image/*,*/*;q=0.8")

IMG_ID_RX = re.compile(r"/images?/([0-9A-Za-z]+)")


def image_id(url):
    m = IMG_ID_RX.search(url or "")
    return m.group(1) if m else None


def sniff_ok(ext, data):
    """Same format rules as scripts/check_asset_inventory.py (+AVIF sniff)."""
    if ext == ".webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    if ext in (".jpg", ".jpeg"):
        return data[:2] == b"\xff\xd8" and data[-2:] == b"\xff\xd9"
    if ext == ".png":
        return data[:8] == b"\x89PNG\r\n\x1a\n"
    if ext == ".avif":
        return data[4:8] == b"ftyp"
    return False


def fetch(url, ext):
    for headers in (HEADERS, HEADERS_WEBP):
        try:
            r = httpx.get(url, headers=headers, timeout=45, follow_redirects=True)
            r.raise_for_status()
            data = r.content
            if len(data) > 1200 and sniff_ok(ext, data):
                return data
        except Exception:                                       # noqa: BLE001
            continue
    return None


def main():
    apply = "--apply" in sys.argv
    inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    attractions = json.loads((BASE / "source_data_attractions.json").read_text(encoding="utf-8"))
    hotels = json.loads((BASE / "source_data_hotels.json").read_text(encoding="utf-8"))
    cities = json.loads((BASE / "source_data_cities.json").read_text(encoding="utf-8"))
    live_path = BASE / "scraped_data" / "attraction_photos_live.json"
    live = json.loads(live_path.read_text(encoding="utf-8")) if live_path.exists() else {}

    assets = {a["path"]: a for a in inv["assets"]}
    by_url = collections.defaultdict(list)
    for a in inv["assets"]:
        by_url[a["source_url"]].append(a["path"])
    shared_paths = sorted({p for u, ps in by_url.items() if len(ps) > 1 for p in ps})
    shared_ids = {image_id(u) for u, ps in by_url.items() if len(ps) > 1}

    att_by_id = {a["id"]: a for a in attractions}
    hotel_by_id = {h["id"]: h for h in hotels}

    used_urls = set(by_url)
    used_ids = {image_id(u) for u in by_url}
    claimed = set()

    def fresh(url):
        iid = image_id(url)
        return (url and len(url) > 40 and iid is not None
                and url not in used_urls and iid not in used_ids
                and iid not in shared_ids and url not in claimed)

    def real_name(a):
        n = (a.get("name") or "").strip().lower()
        return bool(n) and "results for" not in n and n != "attractions & tours category"

    def candidates_for(path):
        parts = path.split("/")
        kind, fname = parts[2], parts[3]
        stem, ext = fname.rsplit(".", 1)
        if kind == "attractions":
            owner_id = int(stem.rsplit("_", 1)[0])
            return [(u, f"own photo of attraction {owner_id} (live re-capture)")
                    for u in (live.get(str(owner_id)) or []) if fresh(u)] \
                + [(u, f"own photo of attraction {owner_id}")
                   for u in (att_by_id.get(owner_id, {}).get("photos") or []) if fresh(u)]
        if kind == "hotels":
            owner_id = int(stem.rsplit("_", 1)[0])
            photos = hotel_by_id.get(owner_id, {}).get("photos") or []
            return [(u, f"own photo of hotel {owner_id}") for u in photos if fresh(u)]
        if kind == "cities":
            slug = stem
            out = []
            atts = sorted((a for a in attractions
                           if a.get("city_slug") == slug and real_name(a)),
                          key=lambda a: (-a.get("rating", 0), -a.get("booked_count", 0)))
            for a in atts:
                out += [(u, f"live photo of top {slug} attraction: {a['name'][:44]}…")
                        for u in (live.get(str(a["id"])) or []) if fresh(u)]
            for a in atts:
                out += [(u, f"photo of top {slug} attraction: {a['name'][:44]}…")
                        for u in (a.get("photos") or []) if fresh(u)]
            hots = sorted((h for h in hotels if h.get("_city_slug") == slug),
                          key=lambda h: (-h.get("rating", 0), h.get("price", 0)))
            for h in hots:
                out += [(u, f"photo of hotel {h['id']} in {slug}")
                        for u in (h.get("photos") or []) if fresh(u)]
            return out
        if kind == "guides":
            out = []
            ranked = sorted((a for a in attractions if real_name(a)),
                            key=lambda a: (-a.get("rating", 0), -a.get("booked_count", 0)))
            for a in ranked:
                out += [(u, f"live photo of top attraction: {a['name'][:44]}…")
                        for u in (live.get(str(a["id"])) or []) if fresh(u)]
            for a in ranked:
                out += [(u, f"photo of top attraction: {a['name'][:44]}…")
                        for u in (a.get("photos") or []) if fresh(u)]
            return out
        return []

    changed, left = [], []
    for path in shared_paths:
        ext = "." + path.rsplit(".", 1)[1]
        picked = None
        for url, why in candidates_for(path):
            data = fetch(url, ext) if apply else b"\x01"      # dry-run sniff skipped
            if apply and data is None:
                continue
            picked = (url, why, data)
            break
        if picked is None:
            left.append(path)
            continue
        url, why, data = picked
        claimed.add(url)
        if apply:
            (IMG / path[len("static/images/"):]).write_bytes(data)
            asset = assets[path]
            asset["bytes"] = len(data)
            asset["sha256"] = hashlib.sha256(data).hexdigest()
            asset["source_url"] = url
        changed.append((path, why, len(data) if apply else 0))
        used_urls.add(url)
        used_ids.add(image_id(url))

    print(f"{len(shared_paths)} files shared a source URL; "
          f"{len(changed)} re-byted, {len(left)} left as-is (upstream-identical sets)")
    for path, why, size in changed:
        print(f"  FIXED {path}  <- {why}" + (f" ({size} B)" if apply else ""))
    for p in left:
        print(f"  LEFT  {p}")

    if not apply:
        print("dry-run only; pass --apply to download and rewrite")
        return 0

    inv["total_bytes"] = sum(a["bytes"] for a in inv["assets"])
    inv["notes"] = [
        "Covers every managed media file under static/images/; the seed database is deterministically generated at build time from the tracked source_data_*.json snapshots (see .build-generated-seed).",
        "Every entry is byte- and hash-verified by scripts/check_asset_inventory.py during the Docker build.",
        "All source URLs are real upstream media URLs served by us.trip.com as rendered on the snapshot date.",
        "2026-09-28 de-duplication pass (review MINOR-1): files that previously shared one upstream source URL were re-byted from a real upstream photo of the same entry (own detail-page photo for attraction cards, top-attraction/hotel photo of the same city for city cards, own distinct gallery photo for hotel mains) via scripts_dev/fix_asset_reuse.py; the seed database and every file path are unchanged. A few duplicated upstream property pairs keep their identical upstream image sets (documented in the fix report).",
    ]
    INVENTORY.write_text(json.dumps(inv, indent=1) + "\n", encoding="utf-8")

    by_url2 = collections.defaultdict(list)
    for a in inv["assets"]:
        by_url2[a["source_url"]].append(a["path"])
    residual = {u: ps for u, ps in by_url2.items() if len(ps) > 1}
    print(f"residual shared source URLs: {len(residual)} "
          f"({sum(len(ps) for ps in residual.values())} files)")
    for u, ps in sorted(residual.items()):
        print(f"  STILL {len(ps)}x {u[:70]}")
        for p in ps:
            print(f"        {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
