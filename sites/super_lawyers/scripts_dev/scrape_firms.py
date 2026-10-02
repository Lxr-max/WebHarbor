"""Harvest firm profile pages from profiles.superlawyers.com.

Firms are collected from the scraped lawyer profiles (the sidebar links
the firm profile page). Each firm page captures: name, about text, the
attorney list (links to lawyer profiles), office location + static map,
and phone. Output: source_data/firms/<uuid>.json
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sl_browser import PROFILES, goto_sl, launch  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent
LAWYERS = SITE / "source_data" / "lawyers"
OUT = SITE / "source_data" / "firms"
OUT.mkdir(parents=True, exist_ok=True)

# Scrape every firm referenced by a scraped lawyer profile (the sidebar
# links the firm profile page upstream); the biggest firms come first.
MIN_REFS = 1
# Cap so the harvest stays tractable; the biggest firms come first.
MAX_FIRMS = 420


def strip_tags(fragment: str) -> str:
    text = re.sub(r"<script.*?</script>", "", fragment, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return (text.replace("&amp;", "&").replace("&#39;", "'")
                .replace("&quot;", '"').replace("&nbsp;", " ")
                .strip())


def collect_firms():
    refs: dict[str, dict] = {}
    for path in sorted(LAWYERS.glob("*.json")):
        rec = json.loads(path.read_text())
        firm = rec.get("firm") or {}
        uuid = firm.get("uuid")
        if not uuid:
            continue
        entry = refs.setdefault(uuid, {
            "name": firm.get("name"), "slug": firm.get("slug"),
            "state": firm.get("state"), "city": firm.get("city"),
            "lawyers": [],
        })
        entry["lawyers"].append(path.stem)
    return refs


def parse_firm(html: str, url: str) -> dict:
    rec = {"url": url}
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    rec["name"] = strip_tags(h1.group(1)) if h1 else None
    about = re.findall(r"<p[^>]*>(.*?)</p>",
                       html[html.find('id="about"'):] if 'id="about"' in html else "",
                       re.S) if 'id="about"' in html else []
    rec["about"] = [strip_tags(p) for p in about if len(strip_tags(p)) > 40][:6]

    attorneys = []
    ai = html.find("Attorney list")
    if ai != -1:
        chunk = html[ai:ai + 12000]
        for m in re.finditer(
                r'href="(https://profiles\.superlawyers\.com/[^"]+/lawyer/([^/]+)/'
                r'([0-9a-f-]+)\.html?)"[^>]*>(.*?)</a>', chunk):
            attorneys.append({
                "name": strip_tags(m.group(4)), "slug": m.group(2),
                "uuid": m.group(3),
            })
    rec["attorneys"] = attorneys

    office = re.search(r'id="firm_map_info"[^>]*>(.*?)</p>', html, re.S)
    if office:
        lines = [strip_tags(x) for x in
                 re.findall(r"([^<>]+)(?:<br\s*/?>|$)", office.group(1))]
        rec["office"] = [x for x in lines if x]
    else:
        rec["office"] = []
    phone = re.search(r'href="tel:([^"]+)"[^>]*>.*?([\d\-\(\)\s]{8,})</a>', html, re.S)
    rec["phone"] = phone.group(2).strip() if phone else None
    smap = re.search(r'src="(https://maps\.googleapis\.com/maps/api/staticmap[^"]+)"', html)
    rec["static_map_url"] = smap.group(1).replace("&amp;", "&") if smap else None
    return rec


def main() -> None:
    refs = collect_firms()
    ranked = sorted(refs.items(), key=lambda kv: -len(kv[1]["lawyers"]))
    todo = [(u, m) for u, m in ranked[:MAX_FIRMS]
            if len(m["lawyers"]) >= MIN_REFS
            and not (OUT / f"{u}.json").exists()]
    print(f"[firms] {len(refs)} referenced, {len(todo)} to scrape")
    pw, browser, ctx = launch()
    page = ctx.new_page()
    done = 0
    t0 = time.time()
    for uuid, meta in todo:
        url = (f"{PROFILES}/{meta['state']}/{meta['city']}/lawfirm/"
               f"{meta['slug']}/{uuid}.html")
        ok = goto_sl(page, url, tries=10)
        html = page.content()
        if not ok or "404" in page.title():
            print(f"[fail] {url}")
        try:
            rec = parse_firm(html, url)
        except Exception as exc:  # noqa: BLE001
            print(f"[parse-error] {uuid}: {exc}")
            continue
        rec.update({k: meta[k] for k in ("name", "slug", "state", "city")})
        rec["lawyers"] = meta["lawyers"]
        (OUT / f"{uuid}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        done += 1
        if done % 25 == 0:
            rate = done / (time.time() - t0)
            print(f"  {done}/{len(todo)} ({rate:.2f}/s)")
    browser.close()
    pw.stop()
    print(f"[firms] done: {done}")


if __name__ == "__main__":
    main()
