#!/usr/bin/env python3
"""Phase 4: harvest the newsroom (alerts + news releases) lists and details.

Reads the already-captured list pages, walks their pagination on the live
site, and fetches every linked detail page for the frozen snapshot.

Run:  python3.11 scrape_news.py
"""
import json
import pathlib
import re
import time

from playwright.sync_api import sync_playwright

from scrape_www import extract  # same extraction contract as phase 1

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT / "scraped_data" / "pages"
OUT = ROOT / "scraped_data" / "news"
OUT.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
BASE = "https://www.uscis.gov"

LISTS = [
    ("/newsroom/alerts", "alerts"),
    ("/newsroom/news-releases", "news_releases"),
    ("/newsroom/all-news", "all_news"),
]
DETAIL_DIR_RE = re.compile(r"^https://www\.uscis\.gov/newsroom/(alerts|news-releases|all-news)/[a-z0-9-]{8,}$")
LIST_PAGES = 3  # how many list pages to walk per list


def main() -> None:
    index_path = OUT / "_index.json"
    index = {"items": []}
    seen = set()
    if index_path.exists():
        index = json.loads(index_path.read_text())
        seen = {i["url"] for i in index["items"]}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(user_agent=UA, viewport={"width": 1366, "height": 1000})
        page = ctx.new_page()
        for path, slug in LISTS:
            for pg_no in range(LIST_PAGES):
                url = BASE + path + (f"?page={pg_no}" if pg_no else "")
                try:
                    page.goto(url, timeout=60000, wait_until="domcontentloaded")
                    page.wait_for_timeout(1800)
                    links = page.eval_on_selector_all(
                        "main a[href]",
                        "els => els.map(e => [e.getAttribute('href'), e.textContent.trim()])")
                    found = 0
                    for href, text in links:
                        if not href:
                            continue
                        if href.startswith("/"):
                            href = BASE + href
                        if DETAIL_DIR_RE.match(href) and href not in seen:
                            index["items"].append({"url": href, "list": slug, "list_page": pg_no,
                                                   "teaser": text[:220]})
                            seen.add(href)
                            found += 1
                    print(f"list {slug} page {pg_no}: +{found} (total {len(seen)})")
                except Exception as exc:
                    print(f"  list ERR {slug}#{pg_no}: {str(exc)[:90]}")
                time.sleep(0.4)
        # fetch details
        done = 0
        for item in index["items"]:
            slug = item["url"].rstrip("/").rsplit("/", 1)[-1]
            out_json = OUT / f"{slug}.json"
            out_html = OUT / f"{slug}.html"
            if out_json.exists():
                continue
            try:
                resp = page.goto(item["url"], timeout=60000, wait_until="domcontentloaded")
                page.wait_for_timeout(1600)
                if not resp or resp.status != 200:
                    print(f"  skip {slug}: status {resp.status if resp else '?'}")
                    continue
                html = page.content()
                out_html.write_text(html)
                rec = extract(html)
                # news pages carry a release date
                m = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+20\d\d", html)
                rec["release_date"] = m.group(0) if m else ""
                rec["url"] = item["url"]
                out_json.write_text(json.dumps(rec, indent=1))
                done += 1
                print(f"  ok {slug[:56]}: '{rec['title'][:48]}' date={rec['release_date']} secs={len(rec['sections'])}")
            except Exception as exc:
                print(f"  ERR {slug[:40]}: {str(exc)[:90]}")
            time.sleep(0.3)
        browser.close()
        index_path.write_text(json.dumps(index, indent=1))
        print(f"details done={done} total_items={len(index['items'])}")


if __name__ == "__main__":
    main()
