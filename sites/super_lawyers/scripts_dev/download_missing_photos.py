"""Patch runner: download only the lawyer photo variants that are not yet
in asset_inventory.json (new lawyers from the card/toplist backfills and
the featured lawyers of the online-features articles), then merge them
into the inventory. Reuses download_assets.py's URL discovery.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

import httpx

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent
SRC = SITE / "source_data"
IMG = SITE / "static" / "images"

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/131.0.0.0 Safari/537.36")}


def ext_for(data: bytes) -> str:
    if data[:2] == b"\xff\xd8":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[:4] == b"GIF8":
        return ".gif"
    raise ValueError("unknown image bytes")


def main() -> None:
    manifest_path = SITE / "asset_inventory.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    by_path = {a["path"]: a for a in manifest["assets"]}
    have_uuids = {}
    for path in by_path:
        if path.startswith("static/images/lawyers/"):
            name = path.rsplit("/", 1)[1]
            uuid = name.split(".")[0].replace("_card", "").replace("_top", "")
            have_uuids.setdefault(uuid, set()).add(path)

    # (rel_path, url, referer) triples to fetch
    wanted: list[tuple[str, str, str]] = []

    def want(uuid: str, suffix: str, url: str, referer: str) -> None:
        if not url or not uuid:
            return
        variants = have_uuids.get(uuid, set())
        kind = f"_{suffix}" if suffix else ""
        if any(kind in p for p in variants):
            return
        wanted.append((f"lawyers/{uuid}{kind}", url, referer))

    for path in sorted((SRC / "lawyers").glob("*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        want(path.stem, "", rec.get("photo_url"),
             "https://profiles.superlawyers.com/")
    for path in sorted((SRC / "listings").glob("*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        for card in rec.get("cards", []):
            want(card.get("profile_uuid"), "card", card.get("photo_url"),
                 "https://attorneys.superlawyers.com/")
    tops = json.loads((SRC / "toplists.json").read_text(encoding="utf-8"))
    for state, entry in tops.get("states", {}).items():
        for lst in entry.get("lists", []):
            for lw in lst.get("lawyers", []):
                want(lw.get("uuid"), "top", lw.get("photo_url"),
                     "https://www.superlawyers.com/")
    for path in sorted((SRC / "articles").glob("*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        for lw in rec.get("featured_lawyers") or []:
            # lawyers whose upstream photo slot is the shared headshot icon
            # render through the placeholder asset instead of a per-uuid copy
            if "icon-headshot" in (lw.get("photo_url") or ""):
                continue
            want(lw.get("uuid"), "", lw.get("photo_url"),
                 "https://www.superlawyers.com/")

    print(f"[photos] {len(wanted)} new variants to download")
    client = httpx.Client(follow_redirects=True, timeout=60, headers=UA)
    n = 0
    for rel, url, referer in wanted:
        try:
            r = client.get(url, headers={"Referer": referer})
            r.raise_for_status()
            data = r.content
        except Exception as exc:  # noqa: BLE001
            print(f"  [fail] {rel}: {exc}")
            continue
        # the wanted key has no extension; find the ext from bytes
        stem = rel
        ext = ext_for(data)
        final = f"static/images/{stem}{ext}"
        (IMG / f"{stem}{ext}").parent.mkdir(parents=True, exist_ok=True)
        (SITE / final).write_bytes(data)
        by_path[final] = {
            "path": final, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "source_url": url,
        }
        n += 1
    client.close()

    assets = sorted(by_path.values(), key=lambda a: a["path"])
    manifest["assets"] = assets
    manifest["asset_count"] = len(assets)
    manifest_path.write_text(json.dumps(manifest, indent=1,
                                        ensure_ascii=False) + "\n")
    print(f"[photos] downloaded {n}; inventory now {len(assets)} assets")


if __name__ == "__main__":
    sys.exit(main())
