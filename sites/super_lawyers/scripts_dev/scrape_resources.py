"""Harvest the Super Lawyers legal-resources corpus
(www.superlawyers.com/resources/): the hub, the practice topic pages (with
their overview articles, FAQs and related-article rails), and a spread of
individual resource articles.

Output: source_data/resources/topics/<topic>.json and
         source_data/resources/articles/<slug>.json
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sl_browser import SITE, goto_sl, launch  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
SITE_DIR = HERE.parent
OUT = SITE_DIR / "source_data" / "resources"
TOPICS_OUT = OUT / "topics"
ARTICLES_OUT = OUT / "articles"
TOPICS_OUT.mkdir(parents=True, exist_ok=True)
ARTICLES_OUT.mkdir(parents=True, exist_ok=True)

# topics whose overview page + article rails we capture in full
TOPICS = [
    "personal-injury-plaintiff", "family-law", "criminal-defense",
    "estate-planning-and-probate", "employment-and-labor",
    "business-and-corporate", "elder-law", "real-estate",
    "motor-vehicle-accidents", "divorce", "dui-dwi", "immigration",
]
ARTICLES_PER_TOPIC = 3


def strip_tags(fragment: str) -> str:
    text = re.sub(r"<script.*?</script>", "", fragment, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return (text.replace("&amp;", "&").replace("&#39;", "'")
                .replace("&quot;", '"').replace("&nbsp;", " ")
                .replace("&#8217;", "’").replace("&#8220;", "“")
                .replace("&#8221;", "”").replace("&#8211;", "–")
                .replace("&#8212;", "—").strip())


def main_content(page_html: str) -> str:
    i = page_html.find("<main")
    j = page_html.find("</main>")
    return page_html[i:j] if i != -1 and j > i else page_html


def parse_blocks(main: str) -> list:
    """Ordered readable blocks: (tag, text)."""
    blocks = []
    for m in re.finditer(r"<(h[1-4]|p|li)[^>]*>(.*?)</\1>", main, re.S):
        tag = m.group(1)
        t = strip_tags(m.group(2))
        if not t or (tag == "li" and len(t) < 3):
            continue
        # skip nav breadcrumbs at the top
        if t in ("Home", "Legal resources") or len(t) < 2:
            continue
        blocks.append({"tag": tag, "text": t})
    return blocks


def parse_article_links(main: str) -> list:
    links, seen = [], set()
    for m in re.finditer(
            r'<a[^>]+href="(https://www\.superlawyers\.com/resources/'
            r'([a-z0-9-]+(?:/[a-z0-9-]+){1,3})/?)"[^>]*>(.*?)</a>', main, re.S):
        href, path, label = m.group(1), m.group(2), strip_tags(m.group(3))
        if href in seen or not label or label in ("Home", "Legal resources"):
            continue
        seen.add(href)
        links.append({"href": href, "path": path, "title": label})
    return links


def scrape_article(page, url: str) -> dict | None:
    goto_sl(page, url)
    html = page.content()
    main = main_content(html)
    if "<main" not in html:
        return None
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", main, re.S)
    if not h1:
        return None
    blocks = parse_blocks(main)
    # drop the leading breadcrumb <li> chain before the h1
    while blocks and blocks[0]["tag"] == "li" and blocks[0]["text"].lower() != "home":
        # breadcrumbs are lis like "Home", "Legal resources", topic...
        first = blocks[0]
        if re.match(r"^[A-Z][a-z]", first["text"]) and len(first["text"]) < 60:
            blocks.pop(0)
        else:
            break
    related = parse_article_links(main)
    return {
        "url": url, "title": strip_tags(h1.group(1)),
        "blocks": blocks, "related": related,
    }


def main() -> None:
    pw, browser, ctx = launch()
    page = ctx.new_page()

    # hub ---------------------------------------------------------------
    goto_sl(page, f"{SITE}/resources/")
    hub_html = page.content()
    hub_main = main_content(hub_html)
    topic_links = parse_article_links(hub_main)
    # topic pages are one path segment under /resources/
    topics = [t for t in topic_links if t["path"].count("/") == 0]
    print(f"[hub] {len(topics)} topic links")

    scraped_articles: dict[str, dict] = {}

    for topic in TOPICS:
        out_path = TOPICS_OUT / f"{topic}.json"
        url = f"{SITE}/resources/{topic}/"
        goto_sl(page, url)
        html = page.content()
        main = main_content(html)
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", main, re.S)
        record = {
            "url": url, "slug": topic,
            "title": strip_tags(h1.group(1)) if h1 else topic,
            "blocks": parse_blocks(main),
            "links": parse_article_links(main),
        }
        out_path.write_text(json.dumps(record, indent=1, ensure_ascii=False))
        # follow a few article links
        followed = 0
        for link in record["links"]:
            if followed >= ARTICLES_PER_TOPIC:
                break
            if link["path"].count("/") == 0 or link["title"] in (
                    "Home", "Legal resources"):
                continue
            if link["href"] in scraped_articles:
                continue
            art = scrape_article(page, link["href"])
            if not art:
                continue
            slug = link["path"].rstrip("/").replace("/", "__")
            art["path"] = link["path"]
            scraped_articles[link["href"]] = art
            (ARTICLES_OUT / f"{slug}.json").write_text(
                json.dumps(art, indent=1, ensure_ascii=False))
            followed += 1
        print(f"[topic] {topic}: {len(record['blocks'])} blocks, "
              f"+{followed} articles")

    (OUT / "_index.json").write_text(json.dumps(
        {"topics": TOPICS, "articles": sorted(scraped_articles)}, indent=1))
    print(f"[resources] done: topics={len(TOPICS)} articles={len(scraped_articles)}")
    browser.close()
    pw.stop()


if __name__ == "__main__":
    main()
