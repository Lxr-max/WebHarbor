"""Build asset_inventory.json from the download manifest.

The inventory is the tracked manifest of every managed runtime asset
(static/images/**) with sha256 + bytes + the upstream source URL, matching the
schema scripts/check_asset_inventory.py verifies.
"""
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "scraped_data" / "image_manifest.json"
IMG = ROOT / "static" / "images"

def main():
    manifest = json.load(open(MANIFEST))
    rows = []
    for rel in sorted(manifest):
        path = IMG / rel
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        assert digest == manifest[rel]["sha256"], f"manifest stale for {rel}"
        rows.append({
            "path": f"static/images/{rel}",
            "bytes": len(data),
            "sha256": digest,
            "source_url": manifest[rel]["source_url"],
        })
    out = {"schema_version": 1, "asset_count": len(rows), "assets": rows}
    (ROOT / "asset_inventory.json").write_text(json.dumps(out, indent=1) + "\n")
    total = sum(r["bytes"] for r in rows)
    print(f"inventory: {len(rows)} assets, {total/1e6:.1f} MB")

if __name__ == "__main__":
    main()
