#!/usr/bin/env python3
"""Phase 6: download the real upstream form PDFs for the forms the mirror serves.

The form detail pages (already captured by scrape_www.py) link the actual
USCIS PDFs under /sites/default/files/document/forms/. We download the form
and its instructions for the frozen form set, recording source URLs.

Run:  python3.11 download_pdfs.py
"""
import json
import pathlib
import re
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT / "scraped_data" / "pages"
OUT = ROOT / "static" / "external_cache" / "forms"
OUT.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
BASE = "https://www.uscis.gov"

# The mirror's form detail pages; the PDF links come from each captured page.
FORM_PAGES = [
    "i485", "n400", "i765", "i693", "i130", "i90", "i131", "i751",
    "i9", "n336", "ar11", "g1450", "i912", "i485a", "i485j",
]


def pdf_links(slug: str) -> list[tuple[str, str]]:
    html = (PAGES_DIR / f"{slug}.html").read_text()
    out = []
    for href, text in re.findall(r'href="([^"]+\.pdf[^"]*)"[^>]*>([^<]{0,80})', html):
        if "document/forms/" not in href and "document/guides/" not in href:
            continue
        name = href.rsplit("/", 1)[-1]
        label = text.strip()
        out.append((BASE + href, name, label))
    return out


def main() -> None:
    index = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        page.goto(BASE, timeout=60000, wait_until="domcontentloaded")
        for slug in FORM_PAGES:
            links = pdf_links(slug)
            seen = set()
            for url, name, label in links:
                if name in seen:
                    continue
                seen.add(name)
                out_path = OUT / name
                if out_path.exists():
                    continue
                try:
                    resp = page.request.get(url)
                    body = resp.body()
                    if resp.status == 200 and body[:4] == b"%PDF":
                        out_path.write_bytes(body)
                        index.append({"file": name, "bytes": len(body), "source_url": url,
                                      "page_slug": slug, "label": label})
                        print(f"  ok {name}: {len(body)} bytes ({label[:40]})")
                    else:
                        print(f"  skip {name}: status {resp.status} magic={body[:4]!r}")
                except Exception as exc:
                    print(f"  ERR {name}: {str(exc)[:90]}")
                time.sleep(0.25)
        browser.close()
    (ROOT / "scraped_data" / "pdf_index.json").write_text(json.dumps(index, indent=1))
    print(f"downloaded {len(index)} PDFs")


if __name__ == "__main__":
    main()
