#!/usr/bin/env python3
"""Capture the specialized license plate catalog: listing pages (35 x 10)
plus every plate detail page, and save per-category listings so each plate's
category is captured from the upstream facet navigation. Raw HTML lands in
scraped_data/plates/; build_source_data.py parses it into source_data.
"""
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from scrape_pages import fetch  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "scraped_data" / "plates"
BASE = "https://www.dmv.virginia.gov"
SEARCH = "/vehicles/license-plates/search"

# Facet ids from the upstream facet links (plate_category taxonomy terms).
CATEGORIES = {
    "special-interest": "286?x",  # resolved below from the listing page
}


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    # 1) listing pages
    for pg in range(1, 36):
        out = RAW / f"list-{pg:02d}.html"
        if out.exists():
            continue
        url = f"{BASE}{SEARCH}?pg={pg}" if pg > 1 else f"{BASE}{SEARCH}"
        out.write_bytes(fetch(url))
        print(f"[plates] listing page {pg}")
        time.sleep(1.0)
    # 2) resolve category facet ids + counts from page 1
    first = (RAW / "list-01.html").read_text(encoding="utf-8")
    facets = re.findall(
        r'href="(/vehicles/license-plates/search\?f%5B0%5D=plate_category%3A(\d+))"'
        r'[^>]*data-drupal-facet-item-count="(\d+)"[^>]*>\s*<span class="facet-item__value">'
        r"([^<]+)</span>", first)
    cat_map = {name.strip().lower().replace(" ", "-"): (fid, count)
               for _href, fid, count, name in facets}
    print(f"[plates] facets: {cat_map}")
    for slug, (fid, _count) in cat_map.items():
        for pg in range(1, 40):
            out = RAW / f"cat-{slug}-{pg:02d}.html"
            if out.exists():
                continue
            url = f"{BASE}{SEARCH}?f%5B0%5D=plate_category%3A{fid}"
            if pg > 1:
                url += f"&pg={pg}"
            data = fetch(url)
            out.write_bytes(data)
            m = re.search(r"Displaying (\d+) - (\d+) of (\d+)", data.decode("utf-8", "replace"))
            if m and int(m.group(2)) >= int(m.group(3)):
                break
            time.sleep(1.0)
        print(f"[plates] category {slug} done")
    # 3) detail pages for every plate
    slugs = set()
    for f in sorted(RAW.glob("list-*.html")):
        html = f.read_text(encoding="utf-8")
        slugs.update(re.findall(
            r'href="/vehicles/license-plates/search/([a-z0-9-]+)"', html))
    print(f"[plates] {len(slugs)} detail pages to capture")
    for i, slug in enumerate(sorted(slugs)):
        out = RAW / f"detail-{slug}.html"
        if out.exists():
            continue
        out.write_bytes(fetch(f"{BASE}{SEARCH}/{slug}"))
        if (i + 1) % 25 == 0:
            print(f"[plates] {i + 1}/{len(slugs)} details")
        time.sleep(0.7)
    print(f"[plates] done: {len(slugs)} details")
    return 0


if __name__ == "__main__":
    sys.exit(main())
