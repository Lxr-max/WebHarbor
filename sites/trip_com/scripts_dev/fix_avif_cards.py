#!/usr/bin/env python3
"""fix_avif_cards.py — last leg of the MINOR-1 de-duplication (review fix).

12 attraction card files are legacy `.avif` names created when the original
download's content-negotiation pulled AVIF bytes — which upstream only
serves for its four generic placeholder images. Every one of those 12 cards
therefore still renders the generic placeholder, and their real product
photos only exist as WebP on the upstream CDN. Re-biting the `.avif` files
with WebP bytes would be a format lie (extension vs magic bytes), so this
script instead swaps each card to a `.webp` sibling carrying a real upstream
photo of the same product:

  * downloads the attraction's own (live re-captured) photo as WebP bytes,
  * writes static/images/attractions/<id>_1.webp and removes <id>_1.avif,
  * updates source_data_images.json (the tracked path manifest the
    deterministic seed build reads) so attractions.img points at the .webp,
  * rewrites the asset inventory entry (path, bytes, sha256, source_url).

The seed database is build-generated (PYTHONHASHSEED=0 seed_data.py), so the
12 changed attractions.img values flow from the tracked manifest at image
build time; the new seed md5 is recorded in the fix receipt and the frozen
review contract's seed digests re-freeze in r2 (documented drift).
"""
import hashlib
import json
import pathlib
import re
import sys

import httpx

BASE = pathlib.Path(__file__).resolve().parent.parent
IMG = BASE / "static" / "images"
INVENTORY = BASE / "asset_inventory.json"
IMAGES_MANIFEST = BASE / "source_data_images.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "image/webp,image/*,*/*;q=0.8",
    "Referer": "https://us.trip.com/",
}
IMG_ID_RX = re.compile(r"/images?/([0-9A-Za-z]+)")


def sniff_webp(data):
    return data[:4] == b"RIFF" and data[8:12] == b"WEBP" and len(data) > 1200


def main():
    apply = "--apply" in sys.argv
    inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    images = json.loads(IMAGES_MANIFEST.read_text(encoding="utf-8"))
    live = json.loads((BASE / "scraped_data" / "attraction_photos_live.json").read_text(encoding="utf-8"))
    attractions = json.loads((BASE / "source_data_attractions.json").read_text(encoding="utf-8"))
    att_by_id = {a["id"]: a for a in attractions}

    by_url = {}
    for a in inv["assets"]:
        by_url.setdefault(a["source_url"], []).append(a["path"])
    shared_paths = {p for u, ps in by_url.items() if len(ps) > 1 for p in ps}
    used_urls = set(by_url)
    used_ids = {m.group(1) for u in by_url if (m := IMG_ID_RX.search(u))}
    shared_ids = {m.group(1) for u, ps in by_url.items() if len(ps) > 1
                  if (m := IMG_ID_RX.search(u))}

    avif_cards = sorted(p for p in shared_paths
                        if p.endswith("_1.avif") and p.split("/")[2] == "attractions")
    print(f"{len(avif_cards)} .avif attraction cards still share a source URL")
    swapped, left = [], []
    for path in avif_cards:
        aid = int(path.split("/")[-1].rsplit("_", 1)[0])
        cands = (live.get(str(aid)) or []) + (att_by_id.get(aid, {}).get("photos") or [])
        picked = None
        for url in cands:
            m = IMG_ID_RX.search(url)
            if not m or url in used_urls or m.group(1) in used_ids or m.group(1) in shared_ids:
                continue
            try:
                r = httpx.get(url, headers=HEADERS, timeout=45, follow_redirects=True)
                r.raise_for_status()
                if sniff_webp(r.content):
                    picked = (url, r.content)
                    break
            except Exception:                                       # noqa: BLE001
                continue
        if picked is None:
            left.append(path)
            continue
        url, data = picked
        new_path = path[:-len(".avif")] + ".webp"
        if apply:
            (IMG / new_path[len("static/images/"):]).write_bytes(data)
            (IMG / path[len("static/images/"):]).unlink()
            for i, a in enumerate(inv["assets"]):
                if a["path"] == path:
                    inv["assets"][i] = {"path": new_path, "bytes": len(data),
                                        "sha256": hashlib.sha256(data).hexdigest(),
                                        "source_url": url}
                    break
            paths = images["attractions"][str(aid)]
            paths[0] = new_path[len("static/images/"):]
            images["attractions"][str(aid)] = paths
        used_urls.add(url)
        used_ids.add(IMG_ID_RX.search(url).group(1))
        swapped.append((path, new_path, url))
        print(f"  SWAP {path} -> {new_path}  <- own photo {IMG_ID_RX.search(url).group(1)}")

    for p in left:
        print(f"  LEFT {p}")
    if not apply:
        print("dry-run only; pass --apply to rewrite")
        return 0

    inv["total_bytes"] = sum(a["bytes"] for a in inv["assets"])
    INVENTORY.write_text(json.dumps(inv, indent=1) + "\n", encoding="utf-8")
    IMAGES_MANIFEST.write_text(json.dumps(images, indent=1) + "\n", encoding="utf-8")

    by_url2 = {}
    for a in inv["assets"]:
        by_url2.setdefault(a["source_url"], []).append(a["path"])
    residual = {u: ps for u, ps in by_url2.items() if len(ps) > 1}
    print(f"asset count: {len(inv['assets'])}; residual shared URLs: {len(residual)} "
          f"({sum(len(p) for p in residual.values())} files)")
    for u, ps in sorted(residual.items(), key=lambda kv: -len(kv[1])):
        print(f"  STILL {len(ps)}x {u[:66]}")
        for p in ps:
            print(f"        {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
