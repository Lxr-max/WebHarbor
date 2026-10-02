#!/usr/bin/env python3
"""Generate asset_inventory.json for the thumbtack mirror.

asset_inventory.json is the tracked manifest checked by the image build's
scripts/check_asset_inventory.py gate: every file under static/images/ and
static/external_cache/ with its byte length, SHA-256 and the real upstream
source URL it was downloaded from. Source URLs come from
scraped_data/image_manifest.json, which records the exact
production-next-images-cdn.thumbtack.com URL each byte stream was fetched
from on the snapshot date (2026-09-26).

Run from sites/thumbtack/: python3 build_inventory.py [--check-only]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
MANAGED_ROOTS = ("static/images", "static/external_cache")
SNAPSHOT = "2026-09-26"


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    manifest_raw = json.loads(
        (HERE / "scraped_data" / "image_manifest.json").read_text(encoding="utf-8"))
    # manifest keys are relative to static/images/; the inventory tracks
    # site-relative paths under static/images/.
    manifest = {f"static/images/{rel}": url for rel, url in manifest_raw.items()}

    actual = {}
    for root in MANAGED_ROOTS:
        base = HERE / root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.name != ".gitkeep":
                actual[str(path.relative_to(HERE))] = path

    missing = sorted(set(manifest) - set(actual))
    extra = sorted(set(actual) - set(manifest))
    if missing:
        raise SystemExit(f"manifest files missing on disk: {missing[:5]}")
    if extra:
        raise SystemExit(f"files on disk missing from manifest: {extra[:5]}")

    rows = []
    for rel in sorted(actual):
        path = actual[rel]
        rows.append({"path": rel,
                     "bytes": path.stat().st_size,
                     "sha256": sha256(path),
                     "source_url": manifest[rel]})

    doc = {
        "schema_version": 1,
        "site": "thumbtack",
        "asset_count": len(rows),
        "total_bytes": sum(r["bytes"] for r in rows),
        "captured_on": SNAPSHOT,
        "capture_method": ("Playwright-rendered pages + direct HTTP fetches of the "
                           "resolved production CDN media URLs"),
        "source_page": "https://www.thumbtack.com/",
        "notes": [
            "Covers every managed media file under static/images/; the seed "
            "database is deterministically generated at build time from the "
            "tracked source_data_*.json snapshots (see .build-generated-seed).",
            "Every entry is byte- and hash-verified by scripts/check_asset_inventory.py "
            "during the Docker build.",
            "All source URLs are real upstream media URLs served by "
            "production-next-images-cdn.thumbtack.com as rendered on the snapshot date.",
        ],
        "assets": rows,
    }

    out = HERE / "asset_inventory.json"
    if args.check_only:
        current = json.loads(out.read_text(encoding="utf-8"))
        if current != doc:
            print("asset_inventory.json is stale; regenerate it", file=__import__("sys").stderr)
            return 1
        print(f"asset_inventory.json up to date ({len(rows)} assets)")
        return 0
    out.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(f"asset_inventory.json written: {len(rows)} assets, "
          f"{doc['total_bytes']} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
