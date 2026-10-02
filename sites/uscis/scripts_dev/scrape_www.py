#!/usr/bin/env python3
"""Phase 1: batch scrape of public www.uscis.gov Drupal pages.

Fetches a fixed page set with a real headless Chromium (uscis.gov sits behind
an Akamai bot filter that 403s plain HTTP clients), saving the rendered HTML
plus an extracted main-content record to scraped_data/pages/.

Run:  python3.11 scrape_www.py            (skips already-fetched slugs)
      python3.11 scrape_www.py --refresh (re-fetch everything)
"""
import json
import pathlib
import re
import sys
import time

from bs4 import BeautifulSoup, Tag
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "scraped_data" / "pages"
OUT.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
BASE = "https://www.uscis.gov"

# (path, slug) — the frozen page set for the mirror snapshot.
PAGES = [
    ("/", "home"),
    ("/topics", "topics"),
    ("/citizenship", "citizenship"),
    ("/citizenship-resource-center/learn-about-citizenship", "learn_about_citizenship"),
    ("/citizenship-resource-center/learn-about-citizenship/naturalization-eligibility-tool-0", "eligibility_tool"),
    ("/citizenship/find-study-materials-and-resources/study-for-the-test", "study_for_the_test"),
    ("/citizenship-resource-center/naturalization-test-and-study-resources/2025-civics-test", "civics_2025"),
    ("/citizenship-resource-center/new-us-citizens", "new_us_citizens"),
    ("/green-card", "green_card"),
    ("/green-card/green-card-eligibility-categories", "gc_eligibility_categories"),
    ("/green-card/green-card-processes-and-procedures", "gc_processes"),
    ("/green-card/green-card-processes-and-procedures/adjustment-of-status", "adjustment_of_status"),
    ("/green-card/green-card-processes-and-procedures/concurrent-filing-of-form-i-485", "concurrent_i485"),
    ("/green-card/while-your-green-card-application-is-pending-with-uscis", "gc_pending"),
    ("/green-card/after-receiving-a-decision", "gc_after_decision"),
    ("/green-card/after-we-grant-your-green-card", "gc_after_grant"),
    ("/green-card/after-we-grant-your-green-card/replace-your-green-card", "gc_replace"),
    ("/working-in-the-united-states", "working"),
    ("/working-in-the-united-states/permanent-workers", "permanent_workers"),
    ("/working-in-the-united-states/h-1b-specialty-occupations", "h1b"),
    ("/i-765", "i765"),
    ("/i-693", "i693"),
    ("/humanitarian", "humanitarian"),
    ("/humanitarian/temporary-protected-status", "tps"),
    ("/humanitarian/refugees-and-asylum", "refugees_asylum"),
    ("/humanitarian/consideration-of-deferred-action-for-childhood-arrivals-daca", "daca"),
    ("/humanitarian/abused-spouses-children-and-parents", "vawa"),
    ("/family", "family"),
    ("/family/family-of-us-citizens", "family_us_citizens"),
    ("/family/family-of-green-card-holders-permanent-residents", "family_lpr"),
    ("/adoption", "adoption"),
    ("/military/military", "military"),
    ("/visit-the-us", "visit_the_us"),
    ("/i-9-central", "i9_central"),
    ("/tools", "tools"),
    ("/tools/uscis-tools-and-resources", "uscis_tools_resources"),
    ("/tools/find-a-civil-surgeon", "find_civil_surgeon"),
    ("/tools/designated-civil-surgeons", "designated_civil_surgeons"),
    ("/tools/designated-civil-surgeons/vaccination-requirements", "vaccination_requirements"),
    ("/tools/while-my-case-is-pending", "while_case_pending"),
    ("/tools/glossary", "glossary"),
    ("/feecalculator", "feecalculator"),
    ("/forms", "forms"),
    ("/forms/filing-fees", "filing_fees"),
    ("/forms/filing-fees/forms-processed-at-a-uscis-lockbox", "lockbox_fees"),
    ("/forms/filing-fees/additional-information-on-filing-a-fee-waiver", "fee_waiver"),
    ("/forms/filing-fees/poverty-guidelines", "poverty_guidelines"),
    ("/i-485", "i485"),
    ("/n-400", "n400"),
    ("/i-130", "i130"),
    ("/i-90", "i90"),
    ("/i-131", "i131"),
    ("/i-751", "i751"),
    ("/i-9", "i9"),
    ("/n-336", "n336"),
    ("/ar-11", "ar11"),
    ("/g-1450", "g1450"),
    ("/file-online", "file_online"),
    ("/file-online/forms-available-to-file-online", "forms_file_online"),
    ("/online-filing-options", "online_filing_options"),
    ("/newsroom", "newsroom"),
    ("/newsroom/alerts", "alerts"),
    ("/newsroom/news-releases", "news_releases"),
    ("/newsroom/all-news", "all_news"),
    ("/about-us", "about_us"),
    ("/about-us/find-a-uscis-office", "find_office"),
    ("/about-us/find-a-uscis-office/field-offices", "field_offices"),
    ("/about-us/find-a-uscis-office/application-support-centers", "asc_list"),
    ("/about-us/uscis-office-closings", "office_closings"),
    ("/contactcenter", "contact_center"),
    ("/avoid-scams", "avoid_scams"),
    ("/save/benefit-and-license-applicants/save-casecheck", "save_casecheck"),
    ("/records/request-records-through-the-freedom-of-information-act-or-privacy-act", "foia"),
    ("/administrative-appeals/aao-processing-times", "aao_processing_times"),
    ("/es", "home_es"),
]

IMG_RE = re.compile(r"\.(?:png|jpe?g|gif|webp|svg)(?:[?#].*)?$", re.I)


def absolutize(url: str) -> str | None:
    if not url:
        return None
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return BASE + url
    if url.startswith("http"):
        return url
    return None


def extract(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup.find(id="main-content") or soup.body
    record = {"title": "", "last_reviewed": "", "alerts": [], "sections": [], "images": [], "links": [], "tables": []}
    h1 = main.find("h1", class_="page-title") or main.find("h1")
    if h1:
        record["title"] = h1.get_text(" ", strip=True)
    else:
        t = soup.find("title")
        record["title"] = (t.get_text(" ", strip=True).rsplit("|", 1)[0] if t else "").strip()
    # "Last Reviewed/Updated:" marker
    m = re.search(r"Last Reviewed/Updated:?\s*</[^>]+>\s*<[^>]*>\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", html)
    if m:
        record["last_reviewed"] = m.group(1)
    # alert banners (uscis usa-alert blocks)
    for alert in main.select(".usa-alert, .alert"):
        at = alert.select_one(".usa-alert__heading, h3")
        kind = ""
        for cls in alert.get("class", []):
            if "alert-" in cls or cls in ("info", "warning", "error", "success"):
                kind = cls.split("--")[-1].replace("usa-alert-", "") or cls
        text = alert.get_text(" ", strip=True)
        if text and len(text) < 900:
            record["alerts"].append({"type": kind, "text": " ".join(text.split())})
    # headings + paragraphs in document order: a section is every h2-h4, and its
    # paragraphs are the p/li/dl text that follow it before the next heading.
    # (This captures accordion panels and card/teaser blocks alike.)
    for junk in main.select("nav, script, style, form.usa-search, .usa-footer, .admin-feedback-form"):
        junk.extract()
    current = None
    seen_sections = []
    for node in main.descendants:
        if not isinstance(node, Tag):
            continue
        if re.match("^h[2-4]$", node.name or ""):
            heading = " ".join(node.get_text(" ", strip=True).split())
            if not heading:
                continue
            current = {"heading": heading, "paragraphs": []}
            seen_sections.append(current)
        elif current is not None and node.name in ("p", "li", "dd"):
            txt = " ".join(node.get_text(" ", strip=True).split())
            if txt and len(txt) < 700 and txt not in current["paragraphs"]:
                current["paragraphs"].append(txt)
    for sec in seen_sections:
        sec["paragraphs"] = sec["paragraphs"][:30]
        if sec["paragraphs"] or len(sec["heading"]) > 2:
            record["sections"].append(sec)
    if not record["sections"]:
        # pages whose body is plain paragraphs/tables with no subheadings
        paras = []
        for node in main.find_all(["p", "li"], recursive=True):
            txt = " ".join(node.get_text(" ", strip=True).split())
            if txt and len(txt) < 700 and txt not in paras:
                paras.append(txt)
        if paras:
            record["sections"].append({"heading": "", "paragraphs": paras[:30]})
    # tables inside main (several USCIS pages carry their data as tables)
    record["tables"] = []
    for table in main.find_all("table"):
        headers = [" ".join(th.get_text(" ", strip=True).split()) for th in table.find_all("th")][:12]
        rows = []
        for tr in table.find_all("tr")[:60]:
            cells = [" ".join(td.get_text(" ", strip=True).split()) for td in tr.find_all(["td", "th"])]
            if cells and any(cells):
                rows.append(cells[:12])
        if rows:
            record["tables"].append({"headers": headers, "rows": rows})
    # images inside main
    for img in main.find_all("img"):
        src = absolutize(img.get("src") or img.get("data-src") or "")
        if not src or not IMG_RE.search(src):
            continue
        record["images"].append({"src": src, "alt": " ".join((img.get("alt") or "").split())[:180]})
    # links inside main
    for a in main.find_all("a", href=True):
        href = absolutize(a["href"])
        if not href:
            continue
        text = " ".join(a.get_text(" ", strip=True).split())
        if text and len(text) < 220:
            record["links"].append({"text": text, "href": href})
    return record


def main() -> None:
    refresh = "--refresh" in sys.argv
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(user_agent=UA, viewport={"width": 1366, "height": 1000}, locale="en-US")
        page = ctx.new_page()
        done = skipped = failed = 0
        for path, slug in PAGES:
            html_path = OUT / f"{slug}.html"
            if html_path.exists() and not refresh:
                skipped += 1
                continue
            url = BASE + path
            try:
                resp = page.goto(url, timeout=60000, wait_until="domcontentloaded")
                page.wait_for_timeout(1600)
                status = resp.status if resp else None
                if status == 404:
                    print(f"  404 {slug} {path}")
                    failed += 1
                    continue
                html = page.content()
                html_path.write_text(html)
                record = extract(html)
                record.update({"url": url, "status": status})
                (OUT / f"{slug}.json").write_text(json.dumps(record, indent=1))
                done += 1
                print(f"  ok {slug}: {status} '{record['title'][:58]}' secs={len(record['sections'])} imgs={len(record['images'])}")
            except Exception as exc:
                failed += 1
                print(f"  ERR {slug}: {str(exc)[:110]}")
            time.sleep(0.35)
        browser.close()
        print(f"done={done} skipped={skipped} failed={failed}")


if __name__ == "__main__":
    main()
