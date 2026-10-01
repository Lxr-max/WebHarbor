#!/usr/bin/env python3
"""Download every upstream image the mirror renders into static/images/
and record the per-file inventory (sha256 + source URL).

Files are named <category>/<slug>.<ext> where <ext> is detected from the
actual magic bytes (jpg/png/gif/webp/svg), never assumed from the URL.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_lib import fetch, UA  # noqa: E402

SITE = Path(__file__).resolve().parents[1]
SOURCE = SITE / "source_data"
IMAGES = SITE / "static" / "images"
INVENTORY = SITE / "asset_inventory.json"

MAGIC = [
    (b"\xff\xd8\xff", "jpg"),
    (b"\x89PNG", "png"),
    (b"GIF8", "gif"),
    (b"RIFF", "webp"),      # RIFF....WEBP
    (b"\x00\x00\x00\x18ftypavif", "avif"),
]


IMG_ACCEPT = "image/png,image/jpeg;q=0.9"


def detect(data: bytes) -> str:
    for magic, ext in MAGIC:
        if data.startswith(magic):
            if ext == "webp" and data[8:12] != b"WEBP":
                continue
            return ext
    if data[4:8] == b"ftyp" and data[8:12] in (b"avif", b"avis"):
        return "avif"
    if data.lstrip().startswith(b"<svg") or b"<svg" in data[:600]:
        return "svg"
    raise ValueError(f"unknown image format: {data[:12].hex()}")


def load(name):
    return json.loads((SOURCE / name).read_text(encoding="utf-8"))


class Downloader:
    def __init__(self):
        self.records = []
        self.seen_urls = {}
        self.seen_hashes = {}
        self.name_map = {}

    def download(self, category: str, name: str, url: str) -> str | None:
        """Fetch url -> static/images/<category>/<name>.<ext>; returns the
        repo-relative path. Duplicate URLs and byte-identical files are
        reused (recorded once). Files already on disk are not refetched."""
        if not url:
            return None
        if url in self.seen_urls:
            existing = self.seen_urls[url]
            self.name_map[f"{category}/{name}"] = "/" + existing
            return existing
        for ext in ("jpg", "png", "webp", "gif", "avif", "svg"):
            existing = SITE / f"static/images/{category}/{name}.{ext}"
            if existing.is_file():
                rel = f"static/images/{category}/{name}.{ext}"
                data = existing.read_bytes()
                digest = hashlib.sha256(data).hexdigest()
                self.records.append({"path": rel, "bytes": len(data),
                                     "sha256": digest, "source_url": url})
                self.seen_urls[url] = rel
                self.seen_hashes[digest] = rel
                self.name_map[f"{category}/{name}"] = "/" + rel
                return rel
        try:
            data = fetch(url, headers={"User-Agent": UA, "Accept": IMG_ACCEPT},
                         timeout=60, retries=2)
            ext = detect(data)
        except Exception as e:                                 # noqa: BLE001
            print(f"  !! {category}/{name}: {e}")
            return None
        digest = hashlib.sha256(data).hexdigest()
        if digest in self.seen_hashes:
            # byte-identical upstream file already stored under another name:
            # reuse the file, record the second source URL separately
            existing = self.seen_hashes[digest]
            self.seen_urls[url] = existing
            self.name_map[f"{category}/{name}"] = "/" + existing
            return existing
        rel = f"static/images/{category}/{name}.{ext}"
        path = SITE / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self.records.append({"path": rel, "bytes": len(data), "sha256": digest,
                             "source_url": url})
        self.seen_urls[url] = rel
        self.seen_hashes[digest] = rel
        self.name_map[f"{category}/{name}"] = "/" + rel
        return rel

    def finish(self) -> None:
        doc = {
            "schema_version": 1,
            "site": "red_bull",
            "asset_count": len(self.records),
            "assets": sorted(self.records, key=lambda r: r["path"]),
        }
        INVENTORY.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                             encoding="utf-8")
        map_path = SITE / "scraped_data" / "image_map.json"
        map_path.parent.mkdir(parents=True, exist_ok=True)
        map_path.write_text(json.dumps(self.name_map, indent=1, sort_keys=True),
                            encoding="utf-8")
        print(f"inventory: {len(self.records)} files -> {INVENTORY}")


def main() -> None:
    d = Downloader()

    # ---- products (storyblok can + scene images) ----
    for p in load("products.json")["products"]:
        d.download("products/cans", p["slug"], p["can_image"])
        d.download("products/scenes", p["slug"], p["scene_image"])
        time.sleep(0.15)

    # ---- events (hero/og image) ----
    for e in load("events.json")["events"]:
        d.download("events", e["slug"], e["hero_image"] or e["image"])
        time.sleep(0.15)

    # ---- series ----
    for s in load("event_series.json")["series"]:
        d.download("series", s["slug"], s["image"])

    # ---- athletes ----
    for a in load("athletes.json")["athletes"]:
        d.download("athletes", a["slug"], a["hero_image"])
        time.sleep(0.15)

    # ---- films / shows ----
    for f in load("films.json")["films"]:
        d.download("films", f["slug"], f["image"])
        time.sleep(0.1)
    for s in load("shows.json")["shows"]:
        d.download("shows", s["slug"], s["image"])
        time.sleep(0.1)

    # ---- stories ----
    for s in load("stories.json")["stories"]:
        d.download("stories", s["slug"], s["hero_image"])
        time.sleep(0.15)

    # ---- shop (curated subset: every product with an image, up to 200) ----
    shop = load("shop_products.json")["products"]
    picked = [p for p in shop if p["images"]][:200]
    for p in picked:
        src = p["images"][0]
        if "?" in src:
            src = src + "&width=800"
        else:
            src = src + "?width=800"
        d.download("shop", p["handle"], src)
        time.sleep(0.15)

    # ---- site chrome: Red Bull wordmark/logo from the upstream header ----
    d.download("site", "redbull-logo",
               "https://www.redbull.com/v3/resources/images/client/header/redbullcom-logo_double-with-text.svg")
    d.download("site", "favicon-32",
               "https://www.redbull.com/v3/resources/images/client/favicons/favicon-32.png")

    d.finish()


if __name__ == "__main__":
    main()
