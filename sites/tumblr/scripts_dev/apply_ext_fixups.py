#!/usr/bin/env python3
"""Rewrite source_data/*.json, applying the downloader's extension fixups.

download_images.py may ship a planned .png photo as .jpg (smaller); it records
every such rename in scraped_data/ext_fixups.json. This script rewrites the
frozen source_data snapshots so all media paths point at real files.
"""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
FIX = BASE / "scraped_data" / "ext_fixups.json"
DST = BASE / "source_data"


def main():
    fixups = json.loads(FIX.read_text(encoding="utf-8"))
    if not fixups:
        print("[fixups] nothing to do")
        return
    for path in sorted(DST.glob("*.json")):
        text = path.read_text(encoding="utf-8")
        changed = 0
        for old, new in fixups.items():
            if old in text:
                changed += text.count(old)
                text = text.replace(old, new)
        if changed:
            path.write_text(text, encoding="utf-8")
            print(f"[fixups] {path.name}: {changed} refs updated")
    print(f"[fixups] applied {len(fixups)} renames")


if __name__ == "__main__":
    main()
