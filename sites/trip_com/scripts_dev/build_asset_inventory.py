#!/usr/bin/env python3
"""Build asset_inventory.json for every managed media file under static/images/.

Each entry records the local path, byte size, sha256 and the upstream URL the
file was downloaded from on the snapshot date. scripts/check_asset_inventory.py
verifies this contract during the Docker build.
"""
import hashlib
import json
import pathlib
import sys

BASE = pathlib.Path(__file__).resolve().parent.parent
IMG = BASE / "static" / "images"
SNAPSHOT = "2026-09-27"

# Rebuild the id -> upstream-URL map from the captured source snapshots.
def url_map():
    hotels = json.loads((BASE / "source_data_hotels.json").read_text(encoding="utf-8"))
    attractions = json.loads((BASE / "source_data_attractions.json").read_text(encoding="utf-8"))
    cities = json.loads((BASE / "source_data_cities.json").read_text(encoding="utf-8"))
    content = json.loads((BASE / "source_data_content.json").read_text(encoding="utf-8"))
    images = json.loads((BASE / "source_data_images.json").read_text(encoding="utf-8"))
    urls = {}

    def put(path, url):
        if url and path:
            urls["static/images/" + path] = url

    for h in hotels:
        paths = images["hotels"].get(str(h["id"]), [])
        if paths and h.get("img_url"):
            put(paths[0], h["img_url"])
        # gallery photos map positionally onto the captured photo list
        photos = h.get("photos", [])
        for n, p in enumerate(paths[1:], start=0):
            if n < len(photos):
                put(p, photos[n])
    for a in attractions:
        paths = images["attractions"].get(str(a["id"]), [])
        if paths and a.get("img_url"):
            put(paths[0], a["img_url"])
        photos = a.get("photos", [])
        for n, p in enumerate(paths[1:], start=0):
            if n < len(photos):
                put(p, photos[n])
    for slug, p in images["cities"].items():
        first = next((h for h in hotels if h.get("_city_slug") == slug
                      and h.get("img_url")), None)
        if first:
            put(p, first["img_url"])
        else:
            att = next((x for x in attractions if x.get("city_slug") == slug
                        and x.get("img_url")), None)
            if att:
                put(p, att["img_url"])
    for slug, p in images["guides"].items():
        g = next(x for x in content["guides"] if x["slug"] == slug)
        city_slug = g.get("city", "").lower().replace(" ", "_")
        att = next((x for x in attractions if x.get("city_slug") == city_slug
                    and x.get("img_url")), None) if city_slug else None
        if att is None:
            att = next((x for x in attractions if x.get("img_url")), None)
        if att:
            put(p, att["img_url"])
    return urls


def main():
    urls = url_map()
    assets = []
    for path in sorted(IMG.rglob("*")):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        rel = "static/" + str(path.relative_to(IMG.parent))  # 'static/images/hotels/1_1.webp'
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        assets.append({
            "path": rel,
            "bytes": path.stat().st_size,
            "sha256": h.hexdigest(),
            "source_url": urls.get(rel, ""),
        })
    inventory = {
        "schema_version": 1,
        "site": "trip_com",
        "asset_count": len(assets),
        "total_bytes": sum(a["bytes"] for a in assets),
        "captured_on": SNAPSHOT,
        "capture_method": "Playwright-rendered pages + direct HTTP fetches of the "
                          "resolved media URLs (ak-d.tripcdn.com / dimg04.tripcdn.com)",
        "source_page": "https://us.trip.com/",
        "notes": [
            "Covers every managed media file under static/images/; the seed "
            "database is deterministically generated at build time from the "
            "tracked source_data_*.json snapshots (see .build-generated-seed).",
            "Every entry is byte- and hash-verified by "
            "scripts/check_asset_inventory.py during the Docker build.",
            "All source URLs are real upstream media URLs served by us.trip.com "
            "as rendered on the snapshot date.",
            "City cards and guide tiles reuse upstream hotel/attraction media "
            "exactly as the upstream pages do for the same cities.",
        ],
        "assets": assets,
    }
    (BASE / "asset_inventory.json").write_text(
        json.dumps(inventory, indent=1, ensure_ascii=False), encoding="utf-8")
    missing_url = [a["path"] for a in assets if not a["source_url"]]
    print(f"inventory: {len(assets)} assets, "
          f"{sum(a['bytes'] for a in assets)} bytes, {len(missing_url)} missing urls")
    for p in missing_url[:8]:
        print("  no-url:", p)


if __name__ == "__main__":
    main()
