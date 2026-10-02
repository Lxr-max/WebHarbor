"""Extract the fixed upstream taxonomy structures from the captured HTML
into tracked JSON files:

- practice_categories.json: the 20 top-level practice categories with their
  sub-practice (slug, name) pairs, from the attorneys.superlawyers.com home
  capture (browse-by-practice-area section).
- toplist_regions.json: the 41 Top Lists regions (display name + slug) from
  the www.superlawyers.com/top-lists/ capture.

Run from sites/super_lawyers/ (any python3).
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent
SRC = SITE / "scraped_data"
OUT = SITE / "source_data"


def main() -> None:
    # ---- practice categories -----------------------------------------------
    src = (SRC / "attorneys_home.html").read_text(encoding="utf-8",
                                                  errors="replace")
    i = src.find('id="browse-practice-areas"')
    seg = src[i:]
    parts = re.split(r"<h3[^>]*>", seg)[1:]
    categories = []
    for part in parts:
        name = re.match(r"\s*([^<]+)", part).group(1).strip()
        name = (name.replace("&amp;", "&"))
        links = re.findall(
            r'<a href="https://attorneys\.superlawyers\.com/([^/"]+)/"'
            r'[^>]*>\s*([^<]+?)\s*</a>', part)
        subs = [{"slug": s, "name": n.replace("&amp;", "&")}
                for s, n in links]
        if subs:
            categories.append({"name": name, "practices": subs})
    (OUT / "practice_categories.json").write_text(json.dumps(
        categories, indent=1, ensure_ascii=False) + "\n")
    total = sum(len(c["practices"]) for c in categories)
    print(f"practice_categories: {len(categories)} categories, "
          f"{total} practices")

    # ---- toplist regions -----------------------------------------------------
    src = (SRC / "top_lists.html").read_text(encoding="utf-8",
                                             errors="replace")
    regions = re.findall(
        r'<a href="https://www\.superlawyers\.com/top-lists/([^/"]+)/"'
        r'[^>]*>([^<]+)</a>', src)
    seen, region_rows = set(), []
    for slug, name in regions:
        if slug in seen:
            continue
        seen.add(slug)
        region_rows.append({"slug": slug, "name": name.strip()})
    (OUT / "toplist_regions.json").write_text(json.dumps(
        region_rows, indent=1, ensure_ascii=False) + "\n")
    print(f"toplist_regions: {len(region_rows)} regions")


if __name__ == "__main__":
    sys.exit(main())
