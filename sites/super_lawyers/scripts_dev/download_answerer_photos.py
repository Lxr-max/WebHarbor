"""One-off patch runner: download only the Ask-a-Lawyer answerer photos
(32 real upstream headshots from source_data/answers/*.json) into
static/images/answers/, merge them into asset_inventory.json, and write
source_data/answerer_photos.json (the tracked uuid -> path mapping that
seed_data.py reads).

Idempotent-ish: skips files already on disk with matching inventory rows.
Run from sites/super_lawyers/ with the agent_demo venv (httpx available).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

import httpx

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent
SRC = SITE / "source_data"
IMG = SITE / "static" / "images"

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/131.0.0.0 Safari/537.36")}


def ext_for(data: bytes) -> str:
    if data[:2] == b"\xff\xd8":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[:4] == b"GIF8":
        return ".gif"
    raise ValueError("unknown image bytes")


def main() -> None:
    manifest_path = SITE / "asset_inventory.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    by_path = {a["path"]: a for a in manifest["assets"]}

    mapping = {}
    client = httpx.Client(follow_redirects=True, timeout=60, headers=UA)
    n = 0
    for path in sorted((SRC / "answers").glob("*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        ans = rec.get("answerer") or {}
        photo = ans.get("photo_url")
        puuid = ans.get("profile_uuid")
        if not photo or not puuid:
            continue
        # already inventoried?
        existing = [p for p in by_path
                     if p.startswith(f"static/images/answers/{puuid}.")]
        if existing:
            rel = existing[0]
        else:
            r = client.get(photo,
                           headers={"Referer": "https://answers.superlawyers.com/"})
            r.raise_for_status()
            data = r.content
            ext = ext_for(data)
            rel = f"static/images/answers/{puuid}{ext}"
            (IMG / "answers").mkdir(parents=True, exist_ok=True)
            (SITE / rel).write_bytes(data)
            by_path[rel] = {
                "path": rel, "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "source_url": photo,
            }
            n += 1
        mapping[path.stem] = {
            "profile_uuid": puuid,
            "name": ans.get("name"),
            "path": rel,
        }
    client.close()

    assets = sorted(by_path.values(), key=lambda a: a["path"])
    manifest["assets"] = assets
    manifest["asset_count"] = len(assets)
    manifest_path.write_text(json.dumps(manifest, indent=1,
                                        ensure_ascii=False) + "\n")
    (SRC / "answerer_photos.json").write_text(json.dumps(
        mapping, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"[answers] downloaded {n} new photos; "
          f"inventory now {len(assets)} assets; "
          f"mapping {len(mapping)} answers")


if __name__ == "__main__":
    sys.exit(main())
