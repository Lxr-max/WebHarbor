#!/usr/bin/env python3
"""Download every managed image from its live upstream URL.

Policy (repo contract, see asset_inventory.json): each file is fetched from
the exact upstream URL the mirror renders it at — Wanderlog's CDN
(itin-dev.wanderlogstatic.com freeImage / freeImageSmall / emoji) and the
landing-page assets served by wanderlog.com/p/. No placeholders, no
duplicates (keys are deduped by content sha256), no stretching: every file
keeps its upstream bytes untouched.

Run from sites/wanderlog:  python3 scripts_dev/download_images.py
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
SRC = os.path.join(SITE, "source_data")
IMG = os.path.join(SITE, "static", "images", "upstream")
CDN = "https://itin-dev.wanderlogstatic.com"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"}

socket.setdefaulttimeout(25)


def load(name):
    with open(os.path.join(SRC, name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def fetch(url, retries=3):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.5 + attempt)
    raise RuntimeError(f"download failed: {url}: {last}")


def ext_for(data: bytes) -> str:
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    raise ValueError("unknown image format")


class Downloader:
    def __init__(self):
        self.manifest = []            # rows: path, bytes, sha256, source_url
        self.by_sha = {}              # sha256 -> path (duplicate guard)
        self.by_name = set()          # logical name guard (first URL wins)
        self.failed = []
        # resume support: reuse rows whose file still exists on disk
        inv_path = os.path.join(SITE, "asset_inventory.json")
        if os.path.exists(inv_path):
            with open(inv_path, encoding="utf-8") as f:
                for row in json.load(f).get("assets", []):
                    if os.path.exists(os.path.join(SITE, row["path"])):
                        self.manifest.append(row)
                        self.by_sha[row["sha256"]] = row["path"]
                        self.by_name.add(os.path.basename(row["path"]).rsplit(".", 1)[0])
            print(f"[images] resuming with {len(self.manifest)} existing assets")

    def add(self, name: str, url: str) -> None:
        """Fetch url, store as static/images/upstream/<name>.<ext>."""
        if name in self.by_name:
            return
        if any(r["source_url"] == url for r in self.manifest):
            self.by_name.add(name)
            return
        self.by_name.add(name)
        # resume: a file for this logical name may already be on disk
        existing = None
        for cand in os.listdir(IMG):
            if cand.rsplit(".", 1)[0] == name:
                existing = os.path.join(IMG, cand)
                break
        if existing:
            with open(existing, "rb") as f:
                data = f.read()
            sha = hashlib.sha256(data).hexdigest()
            if sha in self.by_sha:
                return
            rel = f"static/images/upstream/{os.path.basename(existing)}"
            self.manifest.append({"path": rel, "bytes": len(data), "sha256": sha,
                                  "source_url": url})
            self.by_sha[sha] = rel
            return
        try:
            data = fetch(url)
        except Exception as exc:  # noqa: BLE001
            self.failed.append((url, str(exc)))
            return
        sha = hashlib.sha256(data).hexdigest()
        if sha in self.by_sha:
            return
        ext = ext_for(data)
        rel = f"static/images/upstream/{name}{ext}"
        path = os.path.join(SITE, rel)
        with open(path, "wb") as f:
            f.write(data)
        self.manifest.append({"path": rel, "bytes": len(data), "sha256": sha,
                              "source_url": url})
        self.by_sha[sha] = rel
        print(f"[images] {len(self.manifest)} {name}", flush=True)

    def report(self):
        print(f"[images] downloaded {len(self.manifest)} unique files")
        if self.failed:
            print(f"[images] FAILED {len(self.failed)}:")
            for url, err in self.failed[:20]:
                print("   ", url, err)
            return False
        return True


def slugify(text: str) -> str:
    out = []
    for ch in text.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in " -_":
            out.append("-")
    return "".join(out).strip("-")[:60] or "img"


def main() -> int:
    os.makedirs(IMG, exist_ok=True)
    d = Downloader()

    geos = load("geos")["destinations"]
    sections = load("explore_sections")["sections"]
    lists = load("geo_categories")["lists"]
    places = load("places")["places"]
    guides = load("guides")["guides"]
    profiles = load("profiles")
    landing = load("landing")

    # -- site chrome -------------------------------------------------------
    d.add("logo", "https://wanderlog.com/assets/logoWithText.png")
    d.add("logo-white", "https://wanderlog.com/assets/logoWithText-white.png")

    # -- destination heroes + nearby ----------------------------------------
    for gid, g in geos.items():
        if g.get("imageKey"):
            d.add(f"geo-{slugify(g['name'])}", f"{CDN}/freeImage/{g['imageKey']}")
        for n in g.get("nearby", []):
            if n.get("imageKey"):
                d.add(f"geo-{slugify(n['name'])}",
                      f"{CDN}/freeImageSmall/{n['imageKey']}")

    # -- explore section place cards ----------------------------------------
    for gid, secs in sections.items():
        for sec in secs:
            for b in sec["blocks"]:
                if b.get("selectedImageKey"):
                    d.add(f"place-{slugify(b['name'])}",
                          f"{CDN}/freeImageSmall/{b['selectedImageKey']}")

    # -- geo category list headers + ranked places ---------------------------
    for cid, lst in lists.items():
        if lst.get("headerImageKey"):
            d.add(f"cat-{cid}", f"{CDN}/freeImage/{lst['headerImageKey']}")
        for p in lst["places"]:
            if p.get("selectedImageKey"):
                d.add(f"place-{slugify(p['name'])}",
                      f"{CDN}/freeImageSmall/{p['selectedImageKey']}")

    # -- guides: header + place photos ---------------------------------------
    for key, g in guides.items():
        if g.get("headerImageKey"):
            d.add(f"guide-{key}", f"{CDN}/freeImage/{g['headerImageKey']}")
        for s in g["sections"]:
            for b in s["blocks"]:
                if b.get("kind") == "place" and b.get("selectedImageKey"):
                    d.add(f"place-{slugify(b['name'])}",
                          f"{CDN}/freeImageSmall/{b['selectedImageKey']}")

    # -- user avatars (upstream serves profile pictures under profilePicture/)
    for u in profiles["users"]:
        key = (u["user"] or {}).get("profilePictureKey")
        if key:
            d.add(f"user-{slugify(u['user']['username'])}", f"{CDN}/profilePicture/{key}")
    for grp in ("visitGeosLeaders", "countriesLeaders"):
        for u in profiles["leaderboard"].get(grp, [])[:10]:
            if u.get("profilePictureKey"):
                d.add(f"user-{slugify(u['username'])}",
                      f"{CDN}/profilePicture/{u['profilePictureKey']}")

    # -- landing page assets (served at wanderlog.com/p/) --------------------
    for group in ("press", "explore_cards", "guide_cards", "feature_images",
                  "avatars"):
        for i, rel in enumerate(landing["assets"].get(group, [])):
            d.add(f"landing-{group}-{i}",
                  "https://wanderlog.com/p/" + rel.replace(" ", "%20"))

    # -- category emoji icons -------------------------------------------------
    emojis = set()
    for g in geos.values():
        for c in g.get("categories", []):
            if c.get("emoji"):
                emojis.add(c["emoji"])
    for cid, lst in lists.items():
        pass  # lists reuse the explore-page emoji set
    for e in sorted(emojis):
        d.add(f"emoji-{e}", f"{CDN}/emoji/{e}.png")

    ok = d.report()
    with open(os.path.join(SITE, "asset_inventory.json"), "w", encoding="utf-8") as f:
        json.dump({"schema_version": 1, "asset_count": len(d.manifest),
                   "assets": d.manifest}, f, indent=1, sort_keys=True)
    print(f"[images] inventory written: {len(d.manifest)} assets")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
