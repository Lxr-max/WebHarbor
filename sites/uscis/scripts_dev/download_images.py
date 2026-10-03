#!/usr/bin/env python3
"""Phase 7: download every image the mirror renders, from the upstream URL it
renders at.

Collects the image sources referenced by the captured pages (main content of
www.uscis.gov pages, newsroom detail pages, my.uscis.gov appointment landing)
plus the site chrome (seal/logo/icons) from the raw HTML, dedupes by content
hash, and stores each file under static/images/ with its upstream URL.

Run:  python3.11 download_images.py
"""
import hashlib
import json
import pathlib
import re
import time
import urllib.parse

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT / "scraped_data" / "pages"
NEWS_DIR = ROOT / "scraped_data" / "news"
OUT = ROOT / "static" / "images" / "upstream"
OUT.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
ALLOWED_HOSTS = ("www.uscis.gov", "my.uscis.gov")
IMG_RE = re.compile(r"\.(?:png|jpe?g|gif|webp|svg)(?:[?#].*)?$", re.I)

# Chrome assets (logo/seal/social icons) referenced by every page's raw HTML.
CHROME_RE = re.compile(
    r'(?:src|href|content)="((?:https://www\.uscis\.gov)?/profiles/uscisd8_gov/'
    r'themes/custom/uscis_design/assets/[^"]+\.(?:png|svg|jpg|jpeg|gif|webp))"', re.I)


def collect() -> list[tuple[str, str]]:
    """Return [(url, tag)] deduped by URL, from captured records + raw HTML chrome."""
    seen = {}
    for d in (PAGES_DIR, NEWS_DIR):
        if not d.is_dir():
            continue
        for jf in d.glob("*.json"):
            try:
                rec = json.loads(jf.read_text())
            except Exception:
                continue
            for img in rec.get("images", []):
                url = img["src"]
                if url and IMG_RE.search(url) and urllib.parse.urlsplit(url).hostname in ALLOWED_HOSTS:
                    seen.setdefault(url, f"page:{jf.stem}")
            # raw HTML: chrome + inline content images
            raw = jf.with_suffix(".html")
            if raw.exists():
                html = raw.read_text()
                for m in CHROME_RE.finditer(html):
                    url = m.group(1)
                    if url.startswith("/"):
                        url = "https://www.uscis.gov" + url
                    seen.setdefault(url.split("?")[0] if "assets/" in url else url, "chrome")
                for m in re.finditer(r'src="([^"]+)"', html):
                    url = m.group(1)
                    full = "https://www.uscis.gov" + url if url.startswith("/") else url
                    if IMG_RE.search(full) and urllib.parse.urlsplit(full).hostname in ALLOWED_HOSTS:
                        if "/sites/default/files/" in full or "/images/" in full:
                            seen.setdefault(full, f"html:{jf.stem}")
    return list(seen.items())


def ext_for(url: str, data: bytes) -> str:
    m = IMG_RE.search(url)
    ext = m.group(0).split("?")[0].rsplit(".", 1)[-1].lower() if m else "png"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        ext = "png"
    elif data[:3] == b"\xff\xd8\xff":
        ext = "jpg"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        ext = "webp"
    elif data[:3] == b"GIF":
        ext = "gif"
    elif data.startswith(b"<svg") or data.startswith(b"<?xml") and b"<svg" in data[:300]:
        ext = "svg"
    return ext


def main() -> None:
    urls = collect()
    print(f"{len(urls)} candidate image URLs")
    manifest = {}
    manifest_path = ROOT / "scraped_data" / "images_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        page.goto("https://www.uscis.gov/", timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(800)
        seen_hash = set()
        n = 0
        for url, tag in urls:
            if url in manifest:
                seen_hash.add(manifest[url]["sha256"])
                continue
            try:
                resp = page.request.get(url)
                data = resp.body()
                if resp.status != 200 or len(data) < 200:
                    continue
                ext = ext_for(url, data)
                digest = hashlib.sha256(data).hexdigest()
                if digest in seen_hash:
                    manifest[url] = {"file": None, "sha256": digest, "duplicate_of": True}
                    continue
                seen_hash.add(digest)
                name = f"{len(manifest):04d}_{re.sub(r'[^a-z0-9]+', '_', urllib.parse.urlsplit(url).path.rsplit('/', 1)[-1].rsplit('.', 1)[0].lower())[:44]}.{ext}"
                (OUT / name).write_bytes(data)
                manifest[url] = {"file": name, "sha256": digest, "bytes": len(data), "tag": tag}
                n += 1
            except Exception as exc:
                print(f"  ERR {url[:70]}: {str(exc)[:70]}")
            time.sleep(0.12)
        browser.close()
    manifest_path.write_text(json.dumps(manifest, indent=1))
    files = [v for v in manifest.values() if v.get("file")]
    print(f"downloaded {n} new; total unique images {len(files)}")


if __name__ == "__main__":
    main()
