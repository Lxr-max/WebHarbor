#!/usr/bin/env python3
"""Phase 10: build asset_inventory.json for the mirror's managed assets.

Every file under static/images/ and static/external_cache/ is recorded with
its byte size, sha256, and the exact upstream URL it was fetched from (the
image manifest from download_images.py and the PDF index carry the source
URLs). The output matches the contract enforced by the repo-wide
scripts/check_asset_inventory.py verifier.

Run:  python3.11 build_asset_inventory.py
"""
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANAGED_ROOTS = ("static/images", "static/external_cache")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    manifest = json.loads((ROOT / "scraped_data" / "images_manifest.json").read_text())
    url_by_file = {}
    for url, entry in manifest.items():
        name = entry.get("chrome_file") or entry.get("file")
        if name:
            prefix = "static/images/chrome/" if entry.get("chrome_file") else "static/images/upstream/"
            url_by_file[prefix + name] = url
    pdf_index = json.loads((ROOT / "scraped_data" / "pdf_index.json").read_text())
    for pdf in pdf_index:
        url_by_file[f"static/external_cache/forms/{pdf['file']}"] = pdf["source_url"]

    assets = []
    for root in MANAGED_ROOTS:
        base = ROOT / root
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.name != ".gitkeep":
                rel = str(path.relative_to(ROOT))
                src = url_by_file.get(rel)
                if src is None:
                    raise SystemExit(f"missing source URL for {rel}")
                assets.append({
                    "path": rel,
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                    "source_url": src,
                })
    out = {
        "schema_version": 1,
        "site": "uscis",
        "asset_count": len(assets),
        "assets": assets,
    }
    (ROOT / "asset_inventory.json").write_text(json.dumps(out, indent=1))
    print(f"asset_inventory.json: {len(assets)} assets")


if __name__ == "__main__":
    main()
