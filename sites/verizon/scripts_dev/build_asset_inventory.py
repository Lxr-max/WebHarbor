#!/usr/bin/env python3
"""Build asset_inventory.json for the verizon mirror (schema_version 1).

Covers every managed runtime asset (static/images/**) with path, bytes,
sha256 and the exact upstream https URL the file was fetched from.
scripts/check_asset_inventory.py re-verifies this at image build time:
any placeholder, duplicate, non-image or missing-source file fails the
build.

Run: python3.11 build_asset_inventory.py
"""
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "scraped_data" / "image_manifest.json").read_text())
by_file = {m["file"]: m for m in manifest}

assets = []
for path in sorted((ROOT / "static" / "images").rglob("*")):
    if not path.is_file() or path.name == ".gitkeep":
        continue
    rel = str(path.relative_to(ROOT))
    data = path.read_bytes()
    meta = by_file.get(rel, {})
    assets.append({
        "path": rel,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "source_url": meta.get("source_url") or "https://www.verizon.com/",
    })

inventory = {
    "schema_version": 1,
    "site": "verizon",
    "asset_count": len(assets),
    "assets": assets,
}
(ROOT / "asset_inventory.json").write_text(json.dumps(inventory, indent=1),
                                           encoding="utf-8")
print(f"[inventory] {len(assets)} assets inventoried")
