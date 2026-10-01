#!/usr/bin/env python3
"""Download the real upstream images for the mirror into static/images/.

Reads the source_data_*.json snapshots (upstream URLs captured on 2026-09-27)
and writes:
  static/images/hotels/<hotel_id>_<n>.<ext>     (5 photos per bookable hotel)
  static/images/attractions/<attraction_id>_<n>.<ext>
  static/images/cities/<slug>.<ext>             (city card image)
  static/images/guides/<slug>.<ext>             (guide tile image)
plus source_data_images.json mapping ids -> local paths (used by seed_data.py).

Usage: python3 scripts_dev/download_images.py [--workers N]
"""
import concurrent.futures
import json
import pathlib
import re
import sys
import urllib.parse

import httpx

BASE = pathlib.Path(__file__).resolve().parent.parent
IMG = BASE / "static" / "images"
IMG.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
    "Referer": "https://us.trip.com/",
}


def ext_for(url, content_type=""):
    if "webp" in url or "webp" in content_type:
        return ".webp"
    if ".png" in url or "png" in content_type:
        return ".png"
    return ".jpg"


def fetch(client, url, dest):
    try:
        r = client.get(url, headers=HEADERS, timeout=40)
        r.raise_for_status()
        if len(r.content) < 1200:
            return None
        dest.write_bytes(r.content)
        return {"url": url, "bytes": len(r.content), "path": str(dest.relative_to(IMG))}
    except Exception:  # noqa: BLE001
        return None


def main():
    workers = 8
    if "--workers" in sys.argv:
        workers = int(sys.argv[sys.argv.index("--workers") + 1])

    hotels = json.loads((BASE / "source_data_hotels.json").read_text(encoding="utf-8"))
    attractions = json.loads((BASE / "source_data_attractions.json").read_text(encoding="utf-8"))
    cities = json.loads((BASE / "source_data_cities.json").read_text(encoding="utf-8"))
    content = json.loads((BASE / "source_data_content.json").read_text(encoding="utf-8"))

    jobs = []          # (dest_path, url)
    manifest = {"hotels": {}, "attractions": {}, "cities": {}, "guides": {}}

    for h in hotels:
        paths = []
        # card image first
        if h.get("img_url"):
            ext = ext_for(h["img_url"])
            jobs.append((f"hotels/{h['id']}_1{ext}", h["img_url"]))
            paths.append(f"hotels/{h['id']}_1{ext}")
        # gallery photos (skip the first if it duplicates the card)
        for n, photo in enumerate(h.get("photos", [])[:5], start=1):
            if not photo:
                continue
            ext = ext_for(photo)
            p = f"hotels/{h['id']}_{n}{ext}"
            if p not in [x[0] for x in jobs[-6:]]:
                jobs.append((p, photo))
                paths.append(p)
        if paths:
            manifest["hotels"][str(h["id"])] = paths

    for a in attractions:
        if a.get("img_url"):
            ext = ext_for(a["img_url"])
            p = f"attractions/{a['id']}_1{ext}"
            jobs.append((p, a["img_url"]))
            manifest["attractions"][str(a["id"])] = [p]
        if a.get("photos"):
            for n, photo in enumerate(a.get("photos", [])[:4], start=2):
                if not photo:
                    continue
                ext = ext_for(photo)
                p = f"attractions/{a['id']}_{n}{ext}"
                jobs.append((p, photo))
                manifest["attractions"].setdefault(str(a["id"]), []).append(p)

    # city cards: hotel card image per hotel city, attraction image otherwise
    for c in cities:
        first = next((h for h in hotels if h.get("_city_slug") == c["slug"]
                      and h.get("img_url")), None)
        if not first:
            att = next((a for a in attractions if a.get("city_slug") == c["slug"]
                        and a.get("img_url")), None)
            if att:
                ext = ext_for(att["img_url"])
                p = f"cities/{c['slug']}{ext}"
                jobs.append((p, att["img_url"]))
                manifest["cities"][c["slug"]] = p
            continue
        ext = ext_for(first["img_url"])
        p = f"cities/{c['slug']}{ext}"
        jobs.append((p, first["img_url"]))
        manifest["cities"][c["slug"]] = p

    # guide tiles: attraction photo of the matching city, else the city card
    for g in content["guides"]:
        city = g.get("city", "")
        slug = city.lower().replace(" ", "_")
        src = None
        if slug:
            att = next((a for a in attractions if a.get("city_slug") == slug
                        and a.get("img_url")), None)
            src = att["img_url"] if att else None
        if not src and slug and slug in manifest["cities"]:
            city_img = manifest["cities"][slug]
            manifest["guides"][g["slug"]] = city_img
            continue
        if not src:
            any_att = next((a for a in attractions if a.get("img_url")), None)
            src = any_att["img_url"] if any_att else None
        if src:
            ext = ext_for(src)
            p = f"guides/{g['slug']}{ext}"
            jobs.append((p, src))
            manifest["guides"][g["slug"]] = p

    print(f"downloading {len(jobs)} images with {workers} workers", flush=True)
    ok = fail = 0
    with httpx.Client(follow_redirects=True, timeout=45) as client:
        def work(job):
            rel, url = job
            dest = IMG / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists() and dest.stat().st_size > 1200:
                return rel
            res = fetch(client, url, dest)
            return rel if res else None

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            for res in ex.map(work, jobs):
                if res:
                    ok += 1
                else:
                    fail += 1
    (BASE / "source_data_images.json").write_text(
        json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"done: {ok} ok, {fail} failed", flush=True)


if __name__ == "__main__":
    main()
