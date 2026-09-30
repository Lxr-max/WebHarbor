#!/usr/bin/env python3
"""Build asset_inventory.json — the tracked manifest of every managed asset.

Reads source_data_images.json (the download manifest plan) and verifies every
file on disk under static/images, recording bytes, sha256 and the upstream
source URL for each. Mirrors the contract enforced by
scripts/check_asset_inventory.py (schema_version 1).

Usage: python3 scripts_dev/build_asset_inventory.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
IMG = HERE / "static" / "images"


def main() -> int:
    jobs = json.loads((HERE / "source_data_images.json").read_text())
    rows = []
    for job in sorted(jobs, key=lambda j: j["path"]):
        path = IMG / job["path"]
        if not path.is_file():
            print(f"[FAIL] missing {job['path']}", file=sys.stderr)
            return 1
        data = path.read_bytes()
        rows.append({
            "path": "static/images/" + job["path"],
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "source_url": job["source_url"],
        })
    # also verify no unmanaged files exist
    managed = {r["path"].replace("static/images/", "", 1) for r in rows}
    actual = {str(p.relative_to(IMG))
              for p in IMG.rglob("*") if p.is_file() and p.name != ".gitkeep"}
    extra = actual - managed
    if extra:
        print(f"[FAIL] unmanaged files: {sorted(extra)[:5]}", file=sys.stderr)
        return 1
    manifest = {"schema_version": 1, "asset_count": len(rows), "assets": rows}
    (HERE / "asset_inventory.json").write_text(
        json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"[inventory] {len(rows)} assets, "
          f"{sum(r['bytes'] for r in rows) / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
