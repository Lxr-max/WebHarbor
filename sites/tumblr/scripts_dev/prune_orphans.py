#!/usr/bin/env python3
"""Delete any file under static/images/ that the download manifest no longer
references (e.g. avatars of note-writers that dropped out of a refreshed
notes snapshot). Keeps the shipped tree == the manifest exactly."""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
MANIFEST = BASE / "scraped_data" / "image_manifest.json"
FIXUPS = BASE / "scraped_data" / "ext_fixups.json"


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    fixups = json.loads(FIXUPS.read_text(encoding="utf-8")) \
        if FIXUPS.is_file() else {}
    keep = {fixups.get(r["path"], r["path"]) for r in manifest}
    removed = 0
    for path in (BASE / "static" / "images").rglob("*"):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        rel = path.relative_to(BASE).as_posix()
        if rel not in keep:
            path.unlink()
            removed += 1
    print(f"[prune] removed {removed} orphan files; kept {len(keep)}")


if __name__ == "__main__":
    main()
