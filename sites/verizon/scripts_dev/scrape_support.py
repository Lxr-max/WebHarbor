#!/usr/bin/env python3
"""Phase 5: capture the support / trade-in / home content pages (real upstream).

Fetches the server-rendered AEM pages: support home, return policy,
contact us, network support, trade-in program page (steps + FAQs), the
troubleshoot landing page, and the Verizon home page. Each page's main
content block is stored as structured text for the mirror.

Run: python3.11 scrape_support.py
Output: scraped_data/pages.json, scraped_data/pages/content_*.html
"""
import html as htmllib
import json
import pathlib
import re
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "scraped_data"
(OUT / "pages").mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

PAGES = {
    "home": "https://www.verizon.com/",
    "support_home": "https://www.verizon.com/support/",
    "return_policy": "https://www.verizon.com/support/return-policy/",
    "contact_us": "https://www.verizon.com/support/contact-us/",
    "network": "https://www.verizon.com/support/network/",
    "trade_in": "https://www.verizon.com/trade-in/",
    "troubleshoot": "https://www.verizon.com/support/devices/",
    "stores_home": "https://www.verizon.com/stores/",
}


def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            if i == tries - 1:
                print(f"[support] FAIL {url}: {str(e)[:110]}")
                return ""
            time.sleep(2)


def extract_main(raw):
    """Pull the readable content out of an AEM page: strip scripts/styles/
    nav/footer chrome, keep headings + paragraph + list text."""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.S)
    text = re.sub(r"<(h[1-4])[^>]*>", r"\n\n## ", text)
    text = re.sub(r"</h[1-4]>", "\n", text)
    text = re.sub(r"<li[^>]*>", "\n- ", text)
    text = re.sub(r"<(p|div|section|br)[^>]*>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = htmllib.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def main():
    pages = {}
    for name, url in PAGES.items():
        raw = fetch(url)
        if not raw:
            continue
        (OUT / "pages" / f"content_{name}.html").write_text(raw, encoding="utf-8")
        text = extract_main(raw)
        # cut the long duplicated footer
        pages[name] = {"url": url, "text": text[:20000]}
        print(f"[support] {name}: {len(text)} chars")
        time.sleep(0.7)
    (OUT / "pages.json").write_text(json.dumps(pages, indent=1), encoding="utf-8")
    print(f"[support] captured {len(pages)} content pages")


if __name__ == "__main__":
    main()
