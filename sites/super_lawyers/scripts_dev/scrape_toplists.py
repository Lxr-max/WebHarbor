"""Harvest Super Lawyers top lists (www.superlawyers.com/top-lists/).

Captures the state/region directory, the per-state list index (current +
historical), and the list detail pages (the ranked attorney grid with
photos and firm names). Output: source_data/toplists.json
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sl_browser import SITE, goto_sl, launch  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
SITE_DIR = HERE.parent
OUT = SITE_DIR / "source_data" / "toplists.json"

# states/regions to harvest lists for (where our lawyer data is dense)
STATES = ["washington", "illinois", "new-york", "california", "georgia",
          "massachusetts", "colorado", "texas", "florida"]
LISTS_PER_STATE = 6


def strip_tags(fragment: str) -> str:
    text = re.sub(r"<script.*?</script>", "", fragment, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return (text.replace("&amp;", "&").replace("&#39;", "'")
                .replace("&quot;", '"').strip())


def parse_state_lists(html: str) -> list:
    lists = []
    seen = set()
    for m in re.finditer(
            r'<a[^>]+href="((?:https://www\.superlawyers\.com)?/top-lists/'
            r'[a-z0-9-]+/[a-z0-9-]+/[0-9a-f]{16,}/?)"[^>]*>(.*?)</a>',
            html, re.S):
        href, title = m.group(1), strip_tags(m.group(2))
        if href in seen or title.lower().startswith("show more"):
            continue
        seen.add(href)
        lists.append({"href": href, "title": title})
    return lists


def pick_lists(lists: list, per_state: int) -> list:
    """Prefer the current-year flagship lists, then fill with the rest."""
    priority = []
    for want in ("Top 10: 2026", "Top 50: 2026 Women", "Top 100: 2026",
                 "Top 25: 2026 Women", "Top 5: 2026"):
        for item in lists:
            if item["title"].startswith(want) and item not in priority:
                priority.append(item)
    for item in lists:
        if len(priority) >= per_state:
            break
        if item not in priority:
            priority.append(item)
    return priority[:per_state]


def main() -> None:
    pw, browser, ctx = launch()
    page = ctx.new_page()

    # 1. the top-lists hub (region directory)
    goto_sl(page, f"{SITE}/top-lists/")
    hub_html = page.content()
    regions = []
    for m in re.finditer(
            r'<a[^>]+href="https://www\.superlawyers\.com/top-lists/([a-z0-9-]+)/"[^>]*>([^<]+)</a>',
            hub_html):
        regions.append({"slug": m.group(1), "name": m.group(2).strip()})

    result = {"regions": regions, "states": {}}
    for state in STATES:
        goto_sl(page, f"{SITE}/top-lists/{state}/")
        html = page.content()
        lists = pick_lists(parse_state_lists(html), LISTS_PER_STATE)
        state_entry = {"lists": []}
        for item in lists:
            href = item["href"]
            if href.startswith("http"):
                detail_url = href
            else:
                detail_url = f"{SITE}{href}"
            goto_sl(page, detail_url, tries=14)
            dhtml = page.content()
            lawyers = []
            for m in re.finditer(
                    r'<a href="(https://profiles\.superlawyers\.com/([^/]+)/([^/]+)/lawyer/'
                    r'([^/]+)/([0-9a-f-]+)\.html?[^"]*)">\s*<img[^>]+src="([^"]+)"'
                    r'[^>]*>\s*<span[^>]*>([^<]+)</span>\s*</a>\s*([^<]*)', dhtml):
                lawyers.append({
                    "name": m.group(7).strip(), "state": m.group(2),
                    "city": m.group(3), "slug": m.group(4),
                    "uuid": m.group(5), "photo_url": m.group(6),
                    "profile_href": m.group(1),
                    "firm": m.group(8).strip() or None,
                })
            state_entry["lists"].append({
                "href": item["href"], "title": item["title"],
                "lawyers": lawyers,
            })
            print(f"[ok] {item['title']}: {len(lawyers)} lawyers")
        result["states"][state] = state_entry

    OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False))
    print(f"[toplists] saved: regions={len(regions)} states={len(result['states'])}")
    browser.close()
    pw.stop()


if __name__ == "__main__":
    main()
