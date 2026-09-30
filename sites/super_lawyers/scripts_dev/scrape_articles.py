"""Harvest Super Lawyers attorney feature articles
(www.superlawyers.com/articles/): the hub rails (recent magazine articles,
online exclusives, states) and a spread of feature-article detail pages
(title, subtitle, body, featured lawyers with photos, related articles).

Output: source_data/articles/<state>__<slug>.json
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
OUT = SITE_DIR / "source_data" / "articles"
OUT.mkdir(parents=True, exist_ok=True)

ARTICLES = 10


def strip_tags(fragment: str) -> str:
    text = re.sub(r"<script.*?</script>", "", fragment, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return (text.replace("&amp;", "&").replace("&#39;", "'")
                .replace("&quot;", '"').replace("&nbsp;", " ")
                .replace("&#8217;", "’").replace("&#8220;", "“")
                .replace("&#8221;", "”").replace("&#8216;", "‘").strip())


def main_content(html: str) -> str:
    i, j = html.find("<main"), html.find("</main>")
    return html[i:j] if i != -1 and j > i else html


def parse_article(page, url: str) -> dict | None:
    goto_sl(page, url)
    html = page.content()
    if "<main" not in html or "404" in page.title():
        return None
    main = main_content(html)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", main, re.S)
    if not h1:
        return None
    blocks = []
    for m in re.finditer(r"<(h[1-4]|p|li)[^>]*>(.*?)</\1>", main, re.S):
        tag, t = m.group(1), strip_tags(m.group(2))
        if not t or (tag == "li" and len(t) < 3):
            continue
        if t in ("Home", "Attorney feature articles"):
            continue
        blocks.append({"tag": tag, "text": t})
    # featured lawyers
    featured = []
    for m in re.finditer(
            r'<img class="rounded-3" src="([^"]+)" alt="([^"]*)"[^>]*>.*?'
            r'<h3 class="mb-0"><a[^>]+href="https://profiles\.superlawyers\.com/'
            r'([^/]+)/([^/]+)/lawyer/([^/]+)/([0-9a-f-]+)\.html?"[^>]*>([^<]+)</a>',
            main, re.S):
        featured.append({
            "name": m.group(7).strip(), "state": m.group(3), "city": m.group(4),
            "slug": m.group(5), "uuid": m.group(6), "photo_url": m.group(1),
        })
    # related article links
    related, seen = [], set()
    for m in re.finditer(
            r'<a[^>]+href="(https://www\.superlawyers\.com/articles/'
            r'([a-z0-9-]+)/([a-z0-9-]+)/?)"[^>]*>(.*?)</a>', main, re.S):
        href, label = m.group(1), strip_tags(m.group(4))
        if href in seen or not label or label in ("Home",):
            continue
        seen.add(href)
        related.append({"href": href, "state": m.group(2),
                        "slug": m.group(3), "title": label})
    h2 = re.search(r"<h2[^>]*>(.*?)</h2>", main, re.S)
    return {
        "url": url, "title": strip_tags(h1.group(1)),
        "subtitle": strip_tags(h2.group(1)) if h2 else None,
        "blocks": blocks, "featured_lawyers": featured[:6],
        "related": related[:8],
    }


def main() -> None:
    pw, browser, ctx = launch()
    page = ctx.new_page()
    goto_sl(page, f"{SITE}/articles/")
    hub = main_content(page.content())
    links, seen = [], set()
    for m in re.finditer(
            r'<a[^>]+href="(https://www\.superlawyers\.com/articles/'
            r'([a-z0-9-]+)/([a-z0-9-]+)/?)"[^>]*>(.*?)</a>', hub, re.S):
        href, label = m.group(1), strip_tags(m.group(4))
        if href in seen or not label or label in ("Home",):
            continue
        seen.add(href)
        links.append({"href": href, "state": m.group(2),
                      "slug": m.group(3), "title": label})
    print(f"[articles hub] {len(links)} links")
    saved = 0
    for link in links:
        if saved >= ARTICLES:
            break
        rec = parse_article(page, link["href"])
        if not rec:
            continue
        rec.update({"state": link["state"], "slug": link["slug"]})
        (OUT / f"{link['state']}__{link['slug']}.json").write_text(
            json.dumps(rec, indent=1, ensure_ascii=False))
        saved += 1
        print(f"[article] {rec['title'][:60]} ({len(rec['blocks'])} blocks)")
    print(f"[articles] saved {saved}")
    browser.close()
    pw.stop()


if __name__ == "__main__":
    main()
