#!/usr/bin/env python3
"""Capture the DMV forms catalog (43 listing pages x 10 forms) with the
upstream language/category facets, plus the DMV office locations listing
(all-locations) and every location detail page. Raw HTML lands in
scraped_data/forms/ and scraped_data/locations/.
"""
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from scrape_pages import fetch  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
FORMS = ROOT / "scraped_data" / "forms"
LOCS = ROOT / "scraped_data" / "locations"
BASE = "https://www.dmv.virginia.gov"


def scrape_forms() -> None:
    FORMS.mkdir(parents=True, exist_ok=True)
    for pg in range(1, 44):
        out = FORMS / f"list-{pg:02d}.html"
        if out.exists():
            continue
        url = f"{BASE}/forms" if pg == 1 else f"{BASE}/forms?pg={pg}"
        out.write_bytes(fetch(url))
        print(f"[forms] listing page {pg}")
        time.sleep(0.8)


def scrape_locations() -> None:
    LOCS.mkdir(parents=True, exist_ok=True)
    listing = LOCS / "all-locations.html"
    if not listing.exists():
        listing.write_bytes(fetch(f"{BASE}/all-locations"))
        print("[locations] listing captured")
    html = listing.read_text(encoding="utf-8")
    links = re.findall(r'<a href="(/locations/(?:dmv-selects/)?[a-z0-9-]+)"', html)
    slugs = sorted(set(links))
    print(f"[locations] {len(slugs)} detail pages to capture")
    for i, path in enumerate(slugs):
        name = path.rsplit("/", 1)[-1]
        kind = "dmv-select" if "dmv-selects/" in path else "csc"
        out = LOCS / f"{kind}-{name}.html"
        if out.exists():
            continue
        out.write_bytes(fetch(f"{BASE}{path}"))
        if (i + 1) % 25 == 0:
            print(f"[locations] {i + 1}/{len(slugs)}")
        time.sleep(0.7)
    print("[locations] done")


def main() -> None:
    scrape_forms()
    scrape_locations()


if __name__ == "__main__":
    main()
