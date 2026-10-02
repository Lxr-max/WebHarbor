"""Harvest the static Super Lawyers pages: about, selection process,
attorney FAQ, for-lawyers hub, digital magazines, marketing solutions, and
the corporate contact page. Output: source_data/static_pages.json
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
OUT = SITE_DIR / "source_data" / "static_pages.json"

PAGES = {
    "about": f"{SITE}/about/",
    "selection_process": f"{SITE}/about/selection-process/",
    "attorney_faq": f"{SITE}/about/attorney-faq/",
    "for_lawyers": f"{SITE}/for-lawyers/",
    "digital_magazines": f"{SITE}/for-lawyers/digital-magazines/",
    "marketing_solutions": f"{SITE}/marketing-solutions/",
    "contact": f"{SITE}/contact.html",
    "top_lists_hub": f"{SITE}/top-lists/",
}


def strip_tags(fragment: str) -> str:
    text = re.sub(r"<script.*?</script>", "", fragment, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return (text.replace("&amp;", "&").replace("&#39;", "'")
                .replace("&quot;", '"').replace("&nbsp;", " ").strip())


def parse_page(html: str) -> dict:
    i, j = html.find("<main"), html.find("</main>")
    main = html[i:j] if i != -1 and j > i else html
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", main, re.S)
    blocks = []
    for m in re.finditer(r"<(h[1-4]|p|li)[^>]*>(.*?)</\1>", main, re.S):
        tag, t = m.group(1), strip_tags(m.group(2))
        if not t or (tag == "li" and len(t) < 3):
            continue
        if t in ("Home", "About", "For Lawyers"):
            continue
        blocks.append({"tag": tag, "text": t})
    links = []
    seen = set()
    for m in re.finditer(r'<a[^>]+href="([^"#]+)"[^>]*>([^<]+)</a>', main):
        href, label = m.group(1), strip_tags(m.group(2))
        if href in seen or not label or len(label) < 2:
            continue
        seen.add(href)
        links.append({"href": href, "label": label})
    return {
        "title": strip_tags(h1.group(1)) if h1 else None,
        "blocks": blocks, "links": links[:80],
    }


def main() -> None:
    pw, browser, ctx = launch()
    page = ctx.new_page()
    result = {}
    for key, url in PAGES.items():
        ok = goto_sl(page, url, tries=20)
        html = page.content()
        if not ok:
            print(f"[retry] {url}")
            ok = goto_sl(page, url, tries=20)
            html = page.content()
        result[key] = parse_page(html)
        result[key]["url"] = url
        print(f"[ok] {key}: {len(result[key]['blocks'])} blocks")
    OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False))
    print("[static] saved", len(result), "pages")
    browser.close()
    pw.stop()


if __name__ == "__main__":
    main()
