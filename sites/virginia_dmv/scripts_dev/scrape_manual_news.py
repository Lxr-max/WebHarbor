#!/usr/bin/env python3
"""Capture the Virginia Driver's Manual study-guide data served by the
upstream dmv-manuals SPA backend (transactions.dmv.virginia.gov/dmvapimanuals):
the table of contents, the manual section copy, and the sample knowledge-exam
question bank. Also captures the newsroom listing and articles.
"""
import json
import pathlib
import re
import sys
import time
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from scrape_pages import fetch  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANUAL = ROOT / "scraped_data" / "manual"
NEWS = ROOT / "scraped_data" / "news"
BASE = "https://www.dmv.virginia.gov"
API = "https://transactions.dmv.virginia.gov/dmvapimanuals/api"


def scrape_manual() -> None:
    MANUAL.mkdir(parents=True, exist_ok=True)
    for name, url in [
        ("tboc.json", f"{API}/manual/tboc?manualID=1"),
        ("sections.json", f"{API}/manual/sections?manualID=1"),
        ("quiz.json", f"{API}/manual/quiz?manualID=1&sectionID=1"),
        ("tboc2.json", f"{API}/manual/tboc?manualID=2"),
    ]:
        out = MANUAL / name
        if out.exists():
            continue
        out.write_bytes(fetch(url))
        print(f"[manual] {name}: {out.stat().st_size} bytes")
        time.sleep(1.0)


def scrape_news() -> None:
    NEWS.mkdir(parents=True, exist_ok=True)
    listing = NEWS / "list-1.html"
    if not listing.exists():
        listing.write_bytes(fetch(f"{BASE}/news"))
        print("[news] listing page 1")
    html = listing.read_text(encoding="utf-8")
    slugs = sorted(set(re.findall(r'href="/news/([a-z0-9-]+)"', html)))
    print(f"[news] {len(slugs)} article slugs on page 1")
    for pg in range(2, 8):
        out = NEWS / f"list-{pg}.html"
        if out.exists():
            html2 = out.read_text(encoding="utf-8")
        else:
            data = fetch(f"{BASE}/news?pg={pg}")
            out.write_bytes(data)
            html2 = data.decode("utf-8", "replace")
            print(f"[news] listing page {pg}")
            time.sleep(0.8)
        page_slugs = sorted(set(re.findall(r'href="/news/([a-z0-9-]+)"', html2)))
        if not page_slugs:
            break
        slugs = sorted(set(slugs) | set(page_slugs))
    print(f"[news] {len(slugs)} total article slugs")
    for i, slug in enumerate(slugs):
        out = NEWS / f"article-{slug}.html"
        if out.exists():
            continue
        out.write_bytes(fetch(f"{BASE}/news/{slug}"))
        if (i + 1) % 20 == 0:
            print(f"[news] {i + 1}/{len(slugs)}")
        time.sleep(0.7)


def main() -> None:
    scrape_manual()
    scrape_news()


if __name__ == "__main__":
    main()
