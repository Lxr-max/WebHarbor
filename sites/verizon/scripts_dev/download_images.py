#!/usr/bin/env python3
"""Phase 6: download every upstream image referenced by the scraped data.

Real upstream media only: device gallery shots from ss7.vzw.com (the CDN
URLs the live PDPs render), store interior/exterior photos from
assets.verizon.com (the URLs embedded in the store-locator flight data),
homepage hero shots, and the Verizon wordmark (decoded from the upstream
gnav stylesheet's data URI, since no standalone logo file is published).
Every file is recorded in scraped_data/image_manifest.json with its
sha256, byte size, source URL and the records that use it.

Run: python3.11 download_images.py
"""
import base64
import hashlib
import json
import pathlib
import re
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "scraped_data"
IMG = ROOT / "static" / "images"
(IMG / "devices").mkdir(parents=True, exist_ok=True)
(IMG / "stores").mkdir(parents=True, exist_ok=True)
(IMG / "chrome").mkdir(parents=True, exist_ok=True)
(IMG / "home").mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

GNAV_CSS = "https://www.verizon.com/etc/designs/vzwcom/gnav20/core.css"

manifest = []


def fetch(url, tries=3, binary=True):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read()
        except Exception as e:
            if i == tries - 1:
                print(f"[img] FAIL {url}: {str(e)[:90]}")
                return None
            time.sleep(2)


def save(data, rel, source_url, used_by):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    manifest.append({
        "file": rel,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "source_url": source_url,
        "used_by": used_by,
    })


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def download_device_images():
    devices = json.loads((OUT / "devices.json").read_text())
    for dev in devices:
        slug = dev.get("slug")
        color_images = dev.get("color_images") or {}
        used = [dev.get("name")]
        # ensure the default-color hero is always present: fall back to the
        # first gallery image list captured on the page
        if not color_images and dev.get("imgs"):
            color_images = {"default": [i["src"] for i in dev["imgs"]][:4]}
        for color, urls in color_images.items():
            cslug = slugify(color)
            for n, url in enumerate(urls):
                data = fetch(url)
                if not data:
                    continue
                ext = ".jpg"
                save(data, f"static/images/devices/{slug}-{cslug}-{n}{ext}",
                     url, used)
                time.sleep(0.25)


def download_store_images():
    stores = json.loads((OUT / "stores.json").read_text())["stores"]
    # every store in the Washington locator cities + a sample across states
    picked = []
    for st in stores:
        if st["locator_state"] == "washington":
            picked.append(st)
    by_state = {}
    for st in stores:
        by_state.setdefault(st["locator_state"], []).append(st)
    for state, rows in by_state.items():
        if state != "washington":
            picked.extend(rows[:12])
    seen = set()
    for st in picked:
        code = (st.get("storeUrl") or "").rstrip("/").split("-")[-1]
        if not code.startswith("r") or code in seen:
            continue
        seen.add(code)
        for kind in ("exteriorImageUrl", "interiorImageUrl"):
            url = st.get(kind)
            if not url:
                continue
            data = fetch(url)
            if not data:
                continue
            save(data, f"static/images/stores/{code}-{'outside' if kind == 'exteriorImageUrl' else 'inside'}.jpg",
                 url, [st.get("storeName"), st.get("city")])
            time.sleep(0.25)


def download_home_images():
    html = (OUT / "pages" / "js_home.html").read_text(encoding="utf-8")
    seen = set()
    for url in re.findall(r"https://ss7\.vzw\.com/is/image/VerizonWireless/[A-Za-z0-9_-]+", html):
        if url in seen:
            continue
        seen.add(url)
        if len(seen) > 4:
            break
        data = fetch(url)
        if data:
            name = url.rsplit("/", 1)[1]
            save(data, f"static/images/home/{name.lower()}.jpg", url, ["home"])


def extract_logo():
    css = fetch(GNAV_CSS, binary=True)
    if not css:
        return
    text = css.decode("utf-8", "replace")
    m = re.search(
        r"\.gnav20-logoBlackBg\{background-image:url\('data:image/svg\+xml;"
        r"charset=utf-8;base64,([A-Za-z0-9+/=]+)'\)", text)
    if not m:
        print("[img] logo data URI not found in gnav css")
        return
    svg = base64.b64decode(m.group(1))
    save(svg, "static/images/chrome/verizon-wordmark-black.svg", GNAV_CSS,
         ["site chrome: gnav20-logoBlackBg wordmark"])


def main():
    download_device_images()
    download_store_images()
    download_home_images()
    extract_logo()
    (OUT / "image_manifest.json").write_text(
        json.dumps(manifest, indent=1), encoding="utf-8")
    total = sum(m["bytes"] for m in manifest)
    print(f"[img] downloaded {len(manifest)} files, {total/1e6:.1f} MB total")


if __name__ == "__main__":
    main()
