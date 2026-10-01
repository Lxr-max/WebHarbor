#!/usr/bin/env python3
"""Build asset_inventory.json for the microsoft_azure mirror (schema_version 1).

Covers every managed runtime asset (static/images/**) with path, bytes,
sha256 and the exact upstream https URL the file was fetched from.
scripts/check_asset_inventory.py re-verifies this at image build time:
any placeholder, duplicate, non-image or missing-source file fails the
build.

The download manifest (scraped_data/download_manifest.json, gitignored)
records the source URL of every file; the images themselves ship via the
pinned asset archive.

Run: python3 scripts_dev/build_asset_inventory.py
"""
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "scraped_data" / "download_manifest.json").read_text())
by_path = {m["path"]: m for m in manifest}

assets = []
for path in sorted((ROOT / "static" / "images").rglob("*")):
    if not path.is_file() or path.name == ".gitkeep":
        continue
    rel = str(path.relative_to(ROOT))
    data = path.read_bytes()
    meta = by_path.get(rel.replace("static/images/", ""))
    if meta is None:
        # the header logo is fetched directly in the documented scrape pass
        if rel == "static/images/home/microsoft-logo.png":
            meta = {"url": "https://uhf.microsoft.com/images/microsoft/RE1Mu3b.png"}
        else:
            raise SystemExit(f"no source URL recorded for {rel}")
    assets.append({
        "path": rel,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "source_url": meta["url"],
    })

inventory = {
    "schema_version": 1,
    "site": "microsoft_azure",
    "asset_count": len(assets),
    "assets": assets,
}
(ROOT / "asset_inventory.json").write_text(json.dumps(inventory, indent=1) + "\n",
                                           encoding="utf-8")
print(f"wrote asset_inventory.json with {len(assets)} assets")
