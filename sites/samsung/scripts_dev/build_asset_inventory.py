#!/usr/bin/env python3
"""Build the tracked asset_inventory.json for the samsung mirror.

Every file under static/images/ is recorded with its sha256, byte size and
the exact upstream URL it was fetched from (scraped_data/image_sources.json,
written by the real-capture pipeline). Byte-reproducible: stable ordering,
no wall clock, no RNG.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
IMAGES = BASE / "static" / "images"
RAW = BASE / "scraped_data"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    sources = json.loads((RAW / "image_sources.json").read_text(encoding="utf-8"))
    by_name = {}
    for url, name in sources.items():
        by_name.setdefault(name, url)
    rows = []
    for path in sorted(IMAGES.rglob("*")):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        rel = path.relative_to(BASE).as_posix()
        url = by_name.get(path.name)
        if not url:
            raise SystemExit(f"no upstream source recorded for {path.name}")
        rows.append({
            "path": rel,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "source_url": url,
        })
    manifest = {
        "schema_version": 1,
        "asset_count": len(rows),
        "assets": rows,
    }
    out = BASE / "asset_inventory.json"
    out.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    total = sum(r["bytes"] for r in rows)
    print(f"[inventory] {len(rows)} assets, {total / 1_000_000:.1f} MB")


if __name__ == "__main__":
    main()
