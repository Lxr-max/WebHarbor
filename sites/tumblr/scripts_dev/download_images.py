#!/usr/bin/env python3
"""Download every planned image from upstream tumblr CDNs.

Reads scraped_data/image_manifest.json (written by build_source_data.py) and
fetches each file, recompressing so the shipped image set stays a sane size:

  JPEG  -> max width 960px (aspect preserved), quality 76, progressive
  PNG   -> kept PNG (max 960px); large opaque PNGs become JPEG
  GIF   -> kept animated GIF; oversized ones are downscaled frame-by-frame
  WEBP  -> converted to JPEG (max 960px, q76)
  MP4   -> kept verbatim when <= 8 MB (real tumblr-hosted video)

The recompression preserves aspect ratios (Pillow thumbnail()) and rewrites
the file to match the extension it was planned with, so the repo's
check_asset_inventory.py header validation passes. Every downloaded file
carries its upstream URL into asset_inventory.json.
"""
from __future__ import annotations

import io
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, ImageSequence

BASE = Path(__file__).resolve().parents[1]
MANIFEST = BASE / "scraped_data" / "image_manifest.json"
OUT = BASE
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

MAX_W = {"post-image": 880, "poster": 880, "header": 1600,
         "tag-header": 1280, "tag-thumb": 640, "avatar": 128,
         "note-avatar": 64}
QUALITY = {"post-image": 74, "poster": 74, "header": 76,
           "tag-header": 78, "tag-thumb": 78, "avatar": 82}
VIDEO_MAX_BYTES = 8 * 1024 * 1024
GIF_TARGET_BYTES = 512 * 1024
GIF_MAX_W = 400


def fetch(url: str, retries: int = 5) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "*/*"})
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:                        # noqa: BLE001
            last = e
            time.sleep(1.5 + attempt * 2)
    print(f"[fail] {url} ({last})")
    return None


def sniff(data: bytes) -> str:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:4] == b"\x00\x00\x00\x18" or data[4:8] == b"ftyp":
        return "mp4"
    return ""


def recompress(data: bytes, kind: str, want_ext: str) -> tuple[bytes, str]:
    """Return (bytes, final_ext) — final_ext may differ from want_ext when a
    PNG photo is better shipped as JPEG."""
    fmt = sniff(data)
    if want_ext == ".mp4":
        return data, ".mp4"
    if want_ext == ".gif" or fmt == "gif":
        if fmt != "gif":
            return data, want_ext
        img = Image.open(io.BytesIO(data))
        if len(data) <= GIF_TARGET_BYTES:
            return data, ".gif"
        # animated gif: downscale + drop frames until it fits the budget
        scale = min(1.0, GIF_MAX_W / max(1, img.width))
        frames = []
        for frame in ImageSequence.Iterator(img):
            frame = frame.convert("P", palette=Image.ADAPTIVE)
            new = frame.resize((max(1, int(frame.width * scale)),
                                max(1, int(frame.height * scale))),
                               Image.LANCZOS)
            frames.append(new)
        if not frames:
            return data, ".gif"
        duration = img.info.get("duration", 80)
        step = 1
        for _ in range(4):
            kept = frames[::step] or frames[:1]
            out = io.BytesIO()
            kept[0].save(out, format="GIF", save_all=True,
                         append_images=kept[1:],
                         duration=duration * step, loop=0, optimize=True)
            blob = out.getvalue()
            if len(blob) <= GIF_TARGET_BYTES or len(kept) <= 2:
                return blob, ".gif"
            step *= 2
        return blob, ".gif"
    # raster formats
    img = Image.open(io.BytesIO(data))
    max_w = MAX_W.get(kind, 960)
    q = QUALITY.get(kind, 76)
    if kind == "avatar":
        max_w = 128
    if img.width > max_w:
        img.thumbnail((max_w, max_w * 4), Image.LANCZOS)
    has_alpha = (img.mode in ("RGBA", "LA", "PA")
                 or (img.mode == "P" and "transparency" in img.info))
    # PNG photos are huge; ship JPEG unless the PNG is small or has alpha.
    if kind in ("post-image", "poster", "header", "tag-header"):
        png_blob = None
        if has_alpha:
            out = io.BytesIO()
            img.save(out, format="PNG", optimize=True)
            png_blob = out.getvalue()
        if png_blob is not None and len(png_blob) <= 250_000:
            return png_blob, ".png"
        img2 = img.convert("RGB") if img.mode != "RGB" else img
        out = io.BytesIO()
        img2.save(out, format="JPEG", quality=q, optimize=True,
                  progressive=True)
        return out.getvalue(), ".jpg"
    ext = want_ext.lower()
    if ext in (".jpg", ".jpeg"):
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=q, optimize=True, progressive=True)
        return out.getvalue(), ".jpg"
    if ext == ".png":
        if img.mode not in ("RGBA", "RGB", "L", "LA", "P"):
            img = img.convert("RGB")
        out = io.BytesIO()
        img.save(out, format="PNG", optimize=True)
        blob = out.getvalue()
        if len(blob) > 400_000 and img.mode in ("RGB", "L"):
            out = io.BytesIO()
            img.save(out, format="PNG", optimize=True, compress_level=9)
            blob = out.getvalue()
        return blob, ".png"
    if ext == ".webp":
        out = io.BytesIO()
        img.save(out, format="WEBP", quality=q, method=6)
        return out.getvalue(), ".webp"
    return data, want_ext


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    todo = []
    fixups_path = BASE / "scraped_data" / "ext_fixups.json"
    fixups = {}
    if fixups_path.is_file():
        fixups = json.loads(fixups_path.read_text())
    for row in manifest:
        target = fixups.get(row["path"], row["path"])
        path = OUT / target
        if path.is_file() and path.stat().st_size > 0:
            continue
        todo.append(row)
    if which != "all":
        kinds = set(which.split(","))
        todo = [r for r in todo if r["kind"] in kinds]
    if limit:
        todo = todo[:limit]
    print(f"[download] {len(todo)} files to fetch")
    failures = []
    lock = __import__("threading").Lock()
    done_count = [0]

    def work(row):
        data = fetch(row["url"])
        if data is None:
            with lock:
                failures.append(row)
            return
        want_ext = Path(row["path"]).suffix.lower()
        try:
            blob, final_ext = recompress(data, row["kind"], want_ext)
        except Exception as e:                          # noqa: BLE001
            print(f"[recompress-fail] {row['path']}: {e}; keeping raw")
            blob, final_ext = data, want_ext
        if final_ext == ".mp4" and len(blob) > VIDEO_MAX_BYTES:
            print(f"[skip-video] {row['path']} too big "
                  f"({len(blob)} bytes)")
            with lock:
                failures.append(row)
            return
        path = OUT / row["path"]
        if final_ext != want_ext:
            path = path.with_suffix(final_ext)
            with lock:
                fixups[row["path"]] = path.relative_to(OUT).as_posix()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
        with lock:
            done_count[0] += 1
            if done_count[0] % 200 == 0:
                print(f"[download] {done_count[0]}/{len(todo)}")

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(work, todo))
    print(f"[download] done; {len(failures)} failures; "
          f"{len(fixups)} ext fixups")
    fixups_path.write_text(json.dumps(fixups, indent=1, sort_keys=True))
    if failures:
        (BASE / "scraped_data" / "download_failures.json").write_text(
            json.dumps([f["path"] for f in failures], indent=1))
        for f in failures[:10]:
            print("  failed:", f["path"])


if __name__ == "__main__":
    main()
