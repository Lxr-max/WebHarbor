#!/usr/bin/env python3
"""Download every upstream image and PDF the mirror serves, into
static/images/ and static/external_cache/, recording per-file sha256 +
resolved source URL in asset_inventory.json (the check_asset_inventory
gate reads that file at build time).

Images are captured at the exact upstream style URLs the live pages render
(max_650x650 for plates, 16x9/2x1/5x2 styles for page art, raw files for
news art). No placeholders, no duplicates: each file is downloaded once from
its own upstream URL.
"""
import hashlib
import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from scrape_pages import fetch  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
IMG = ROOT / "static" / "images"
CACHE = ROOT / "static" / "external_cache"
BASE = "https://www.dmv.virginia.gov"


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def slugname(url: str) -> str:
    tail = url.rsplit("/", 1)[-1]
    tail = re.sub(r"\?.*$", "", tail)
    tail = re.sub(r"%20", "_", tail)
    tail = re.sub(r"[^A-Za-z0-9._-]", "_", tail)
    # avoid collisions between styles of the same file: keep the style tag
    style = ""
    m = re.search(r"/styles/([^/]+)/public/", url)
    if m:
        style = m.group(1) + "__"
    return f"{style}{tail}"


def collect_urls() -> dict[str, list[str]]:
    """category -> [upstream path, ...] in deterministic order."""
    out = {"plates": [], "pages": [], "news": [], "chrome": []}
    seen = set()

    def add(cat, url):
        if url not in seen:
            seen.add(url)
            out[cat].append(url)

    # plates: the card art for all 342 plates — capture BOTH upstream
    # styles the live pages render (max_650x650 on the search grid,
    # small on the detail pages)
    plates = json.loads((ROOT / "source_data" / "plates.json").read_text())
    for p in plates:
        if p["image"]:
            add("plates", p["image"])
            add("plates", p["image"].replace("/styles/small/", "/styles/max_650x650/"))
    # pages + news: every /sites/default/files image on the captured pages
    for d, cat in (("pages", "pages"), ("news", "news")):
        for f in sorted((ROOT / "scraped_data" / d).glob("*.html")):
            html = f.read_text(encoding="utf-8")
            for m in re.finditer(r'<img[^>]*src="(/sites/default/files/[^"]+?)(?:\?[^"]*)?"', html):
                add(cat, m.group(1))
            for m in re.finditer(r'style="[^"]*url\(\'?(/sites/default/files/[^\'"?]+)', html):
                add(cat, m.group(1))
    # site chrome: the theme pin art + favicon
    add("chrome", "/themes/gesso/dist/images/map-pin-csc.png")
    add("chrome", "/themes/gesso/dist/images/map-pin.png")
    add("chrome", "/themes/gesso/dist/images/map-pin-any.svg")
    return out


def collect_pdfs() -> list[tuple[str, str]]:
    """(upstream path, category) for PDFs the mirror serves."""
    pdfs = [("/sites/default/files/forms/dmv201.pdf", "fees")]
    # every Driver/Vehicle/Other/Transportation Safety/Dealer category form
    forms = json.loads((ROOT / "source_data" / "forms.json").read_text())
    for f in forms:
        if f["language"] == "English" and f["category"] in (
                "Driver", "Vehicle", "Other", "Transportation Safety", "Dealer"):
            pdfs.append((f["pdf"], "forms"))
    return pdfs


def main() -> int:
    IMG.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    inventory = {}
    if (ROOT / "asset_inventory.json").exists():
        inventory = json.loads((ROOT / "asset_inventory.json").read_text())
    for cat, urls in collect_urls().items():
        catdir = IMG / cat
        catdir.mkdir(exist_ok=True)
        for i, url in enumerate(urls):
            name = slugname(url)
            dest = catdir / name
            if dest.exists() and dest.stat().st_size > 0:
                continue
            data = fetch(BASE + url)
            if not data[:4] in (b"\x89PNG", b"\xff\xd8\xff", b"GIF8", b"<svg", b"RIFF") and not data.startswith(b"\x89PNG"):
                # svg text or other; still save, but sanity-check non-empty
                if len(data) < 200:
                    print(f"[images] suspicious {url}: {len(data)} bytes")
            dest.write_bytes(data)
            inventory[str(dest.relative_to(ROOT))] = {
                "sha256": sha256(data), "source_url": BASE + url,
                "bytes": len(data)}
            if (i + 1) % 40 == 0:
                print(f"[images] {cat}: {i + 1}/{len(urls)}")
            time.sleep(0.35)
        print(f"[images] {cat}: {len(urls)} done")
    # PDFs
    for url, cat in collect_pdfs():
        name = slugname(url)
        dest = CACHE / cat
        dest.mkdir(parents=True, exist_ok=True)
        fdest = dest / name
        if fdest.exists() and fdest.stat().st_size > 0:
            continue
        data = fetch(BASE + url)
        fdest.write_bytes(data)
        inventory[str(fdest.relative_to(ROOT))] = {
            "sha256": sha256(data), "source_url": BASE + url,
            "bytes": len(data)}
        time.sleep(0.5)
    (ROOT / "asset_inventory.json").write_text(
        json.dumps({
            "schema_version": 1,
            "site": "virginia_dmv",
            "asset_count": len(inventory),
            "assets": [
                {"path": p, "sha256": meta["sha256"], "bytes": meta["bytes"],
                 "source_url": meta["source_url"]}
                for p, meta in sorted(inventory.items())],
        }, indent=1), encoding="utf-8")
    print(f"[assets] inventory entries: {len(inventory)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
