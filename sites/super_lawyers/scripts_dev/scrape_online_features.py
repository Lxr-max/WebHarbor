"""Scrape the online-exclusive feature articles referenced by the already
harvested magazine articles' related rails (24 /articles/online-features/
slugs). Run after the profile backfill; writes
source_data/articles/online-features__<slug>.json.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from scrape_articles import parse_article  # noqa: E402
from sl_browser import launch  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
SITE_DIR = HERE.parent
ARTICLES = SITE_DIR / "source_data" / "articles"


def main() -> None:
    slugs = sorted({
        m for p in ARTICLES.glob("*.json")
        for m in re.findall(r"articles/online-features/([a-z0-9-]+)/",
                            (p).read_text(encoding="utf-8"))
    })
    print(f"[online-features] {len(slugs)} referenced slugs")
    pw, browser, ctx = launch()
    page = ctx.new_page()
    saved = 0
    for slug in slugs:
        out = ARTICLES / f"online-features__{slug}.json"
        if out.exists():
            continue
        url = f"https://www.superlawyers.com/articles/online-features/{slug}/"
        try:
            rec = parse_article(page, url)
        except Exception as exc:  # noqa: BLE001
            print(f"  [fail] {slug}: {exc}")
            continue
        if not rec:
            print(f"  [miss] {slug}")
            continue
        rec.update({"state": "online-features", "slug": slug})
        out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        saved += 1
        print(f"  [ok] {rec['title'][:60]}")
    browser.close()
    pw.stop()
    print(f"[online-features] saved {saved}")


if __name__ == "__main__":
    main()
