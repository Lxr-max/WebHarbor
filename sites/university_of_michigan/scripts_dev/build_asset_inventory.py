#!/usr/bin/env python3
"""Build asset_inventory.json for the university_of_michigan mirror.

Walks static/images/ (the only managed root this site uses), records
path/bytes/sha256 plus the upstream source URL for every file (from the
scrape manifest), and validates the byte format of each image.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
MANIFEST = Path("/tmp/umich_scrape/site_images.json")


def main() -> int:
    rows = []
    src_by_dest = {}
    if MANIFEST.exists():
        data = json.loads(MANIFEST.read_text())
        for rec in data["selected"].values():
            src_by_dest["static/images/" + rec["dest"]] = rec["url"]
    seen_sha = set()
    for path in sorted((SITE / "static" / "images").rglob("*")):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        rel = path.relative_to(SITE).as_posix()
        blob = path.read_bytes()
        sha = hashlib.sha256(blob).hexdigest()
        if sha in seen_sha:
            print(f"DUPLICATE sha256 {sha[:12]} at {rel}", file=sys.stderr)
            return 1
        seen_sha.add(sha)
        if blob[:3] == b"\xff\xd8\xff":
            pass
        elif blob[:8] == b"\x89PNG\r\n\x1a\n":
            pass
        elif blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
            pass
        else:
            print(f"UNKNOWN FORMAT {rel}", file=sys.stderr)
            return 1
        rows.append({
            "path": rel,
            "bytes": len(blob),
            "sha256": sha,
            "source_url": src_by_dest.get(rel, ""),
        })
    missing_src = [r["path"] for r in rows if not r["source_url"]]
    if missing_src:
        print(f"MISSING SOURCE URL: {missing_src[:5]}", file=sys.stderr)
        return 1
    out = {
        "schema_version": 1,
        "site": "university_of_michigan",
        "asset_count": len(rows),
        "assets": rows,
    }
    (SITE / "asset_inventory.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"asset_inventory.json: {len(rows)} assets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
