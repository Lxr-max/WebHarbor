#!/usr/bin/env python3
"""Build asset_inventory.json for the tumblr mirror.

Covers every file under static/images/ (the site's managed asset roots) with
its byte size, sha256 and the upstream tumblr CDN URL it was fetched from
(scraped_data/image_manifest.json + ext_fixups.json carry the mapping).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
MANIFEST = BASE / "scraped_data" / "image_manifest.json"
FIXUPS = BASE / "scraped_data" / "ext_fixups.json"
OUT = BASE / "asset_inventory.json"


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    fixups = json.loads(FIXUPS.read_text(encoding="utf-8")) \
        if FIXUPS.is_file() else {}
    source_for = {}
    for row in manifest:
        actual = fixups.get(row["path"], row["path"])
        source_for[actual] = row["url"]

    assets = []
    for path in sorted((BASE / "static" / "images").rglob("*")):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        rel = path.relative_to(BASE).as_posix()
        data = path.read_bytes()
        assets.append({
            "path": rel,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "source_url": source_for.get(rel, "https://www.tumblr.com/"),
        })

    inventory = {
        "schema_version": 1,
        "site": "tumblr",
        "asset_count": len(assets),
        "assets": assets,
    }
    OUT.write_text(json.dumps(inventory, indent=1), encoding="utf-8")
    total = sum(a["bytes"] for a in assets)
    print(f"[inventory] {len(assets)} assets, {total/1e6:.1f} MB total")
    missing_src = [a["path"] for a in assets
                   if a["source_url"] == "https://www.tumblr.com/"]
    if missing_src:
        print(f"[inventory] WARNING: {len(missing_src)} assets without a "
              f"mapped source URL: {missing_src[:5]}")


if __name__ == "__main__":
    main()
