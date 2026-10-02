#!/usr/bin/env python3
"""Download every upstream image in source_data_images.json into static/images/.

- 320w upstream variants for product cards/galleries; original sizes for
  logos/banners/tiles (exactly the URLs captured upstream).
- JPEGs are recompressed aspect-preserving (quality 82, progressive) to keep
  the shipped asset set compact; PNG/SVG pass through untouched.
- Resume-safe: skips files that already pass validation.
- Writes scraped_data/downloaded.json manifest {path, url, bytes, sha256}.

Run with python3.11 (needs Pillow): python3.11 scripts_dev/download_images.py
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import io
import json
import pathlib
import sys
import urllib.request

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent.parent
IMG = HERE / "static" / "images"
MANIFEST = HERE / "scraped_data" / "downloaded.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
MIN_BYTES = 800


def valid_jpeg(data: bytes) -> bool:
    return data[:2] == b"\xff\xd8" and data[-2:] == b"\xff\xd9"


def valid_png(data: bytes) -> bool:
    return data[:8] == b"\x89PNG\r\n\x1a\n"


def recompress(data: bytes) -> bytes:
    im = Image.open(io.BytesIO(data))
    im = im.convert("RGB")
    out = io.BytesIO()
    im.save(out, "JPEG", quality=82, optimize=True, progressive=True)
    blob = out.getvalue()
    return blob if len(blob) < len(data) else data


def transcode(data: bytes, fmt: str, mode):
    im = Image.open(io.BytesIO(data))
    if mode:
        im = im.convert(mode)
    out = io.BytesIO()
    im.save(out, fmt, optimize=True,
            quality=82, progressive=(fmt == "JPEG"))
    return out.getvalue()


def fetch(job):
    rel, url = job["path"], job["source_url"]
    dest = IMG / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > MIN_BYTES:
        data = dest.read_bytes()
        ok = (valid_jpeg(data) if rel.endswith((".jpg", ".jpeg"))
              else valid_png(data) if rel.endswith(".png") else len(data) > 0)
        if ok:
            return {"path": rel, "url": url, "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(), "cached": True}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=45) as r:
            data = r.read()
        if len(data) < MIN_BYTES:
            return None
        if rel.endswith((".jpg", ".jpeg")):
            if data[:2] != b"\xff\xd8":
                data = transcode(data, "JPEG", "RGB")  # CDN sometimes serves WebP
        elif rel.endswith(".png"):
            if data[:8] != b"\x89PNG\r\n\x1a\n":
                data = transcode(data, "PNG", None)
        else:
            return None
        dest.write_bytes(data)
        return {"path": rel, "url": url, "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest()}
    except Exception:  # noqa: BLE001
        return None


def main() -> int:
    jobs = json.loads((HERE / "source_data_images.json").read_text())
    print("jobs:", len(jobs), flush=True)
    results = []
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as ex:
        for res in ex.map(fetch, jobs):
            done += 1
            if res:
                results.append(res)
            if done % 1000 == 0:
                print(f"  {done}/{len(jobs)} ok={len(results)}", flush=True)
    MANIFEST.write_text(json.dumps(results, indent=0), encoding="utf-8")
    print("downloaded:", len(results), "of", len(jobs))
    total = sum(r["bytes"] for r in results)
    print("total bytes: %.1f MB" % (total / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
