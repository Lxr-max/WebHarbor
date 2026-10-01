#!/usr/bin/env python3
"""Real-capture pipeline for the samsung mirror (build-time only).

Captures the live upstream (www.samsung.com/us and its public catalog/spec
APIs) into scraped_data/ (gitignored). The tracked source_data/*.json
snapshots are derived from these captures by build_source_data.py; nothing
is invented here.

Phases (run in order):
  catalog  pf_search for every registered category (full result set)
  buy      buy-page __NEXT_DATA__ payloads for the flagship configurators
  specs    smartphone family list + spec-compare tables
  support  support / warranty / contact pages (static HTML)
  home     home page (static HTML)
  images   download every image the mirror renders (from the curated lists)

Usage: python3 scrape.py <phase>   (or: all)
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "scraped_data"
RAW.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.samsung.com/",
    "Origin": "https://www.samsung.com",
}
PF_URL = "https://sribsrch.ecom.samsung.com/estoresearch-api/v1/scom/us/pf_search"
SPEC_COMPARE = ("https://searchapi.samsung.com/v6/front/b2c/product/mktpd/spec/compare/"
                "?siteCode=us&categoryCode=SMARTPHONE&modelList=")
FAMILY_LIST = ("https://searchapi.samsung.com/v6/front/b2c/product/family/list/newhybris"
               "?siteCode=us&saleSkuYN=N&onlyRequestSkuYN=N&commonCodeYN=N&displayFlagUseYN=N&modelList=")

# category_code -> (mirror slug, upstream hub path)
CATEGORIES = [
    ("01010000", "smartphones", "/us/smartphones/"),
    ("01020000", "tablets", "/us/tablets/"),
    ("01030000", "watches", "/us/watches/"),
    ("01040000", "audio", "/us/audio-sound/"),
    ("01050000", "mobile-accessories", "/us/mobile-accessories/"),
    ("04010000", "tvs", "/us/tvs/"),
    ("08010000", "laundry", "/us/home-appliances/laundry/"),
    ("08030000", "refrigerators", "/us/home-appliances/refrigerators/"),
]

# flagship configurators whose buy page is mirrored verbatim; resolved from the
# catalog captures in phase_buy (mlpUrl of the named family), never hard-coded.
BUY_FAMILIES = {
    "smartphones": ["Galaxy S26 Ultra", "Galaxy S26+", "Galaxy Z Fold8 Ultra", "Galaxy Z Flip8"],
    "tablets": ["Galaxy Tab S11 Ultra"],
    "watches": ["Galaxy Watch9"],
    "tvs": ["Micro RGB R95H", "OLED S90H"],
    "refrigerators": ["BESPOKE RF9000", "Mega Capacity 3-Door"],
    "laundry": ["Bespoke Ultra Capacity AI Front Load Washer"],
}

SUPPORT_PAGES = [
    ("support_home", "/us/support/"),
    ("warranty", "/us/support/warranty/"),
    ("contact", "/us/support/contact/"),
    ("service", "/us/support/service/"),
    ("legal_tv", "/us/support/legal/LGL10000312/"),
    ("legal_appliances", "/us/support/legal/LGL10000309/"),
]


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def get(s: requests.Session, url: str, *, tries: int = 4, sleep: float = 4.0) -> requests.Response:
    for attempt in range(tries):
        try:
            r = s.get(url, timeout=60)
        except requests.RequestException as e:
            print(f"  ! {e}; retrying")
            time.sleep(sleep)
            continue
        if r.status_code == 200:
            time.sleep(2.0)
            return r
        if r.status_code in (403, 429, 503) and attempt < tries - 1:
            print(f"  ! HTTP {r.status_code}; backing off {sleep * (attempt + 1):.0f}s")
            time.sleep(sleep * (attempt + 1))
            continue
        r.raise_for_status()
    raise RuntimeError(f"GET failed after retries: {url}")


def phase_catalog(s: requests.Session) -> None:
    for code, slug, hub in CATEGORIES:
        out = RAW / f"pf_{slug}.json"
        if out.exists():
            print(f"[catalog] {slug}: cached")
            continue
        payload = {
            "clientCode": "b2c", "clientName": "scom_pf", "firstSearchYN": "true",
            "countryCode": "us", "storeID": "us", "startIndex": 0,
            "requestCount": 400, "category_code": code, "filters": "[]",
            "sort": "recommended",
        }
        r = s.post(PF_URL, data=payload, timeout=60)
        if r.status_code != 200:
            print(f"[catalog] {slug}: HTTP {r.status_code}, retry once after pause")
            time.sleep(20)
            r = s.post(PF_URL, data=payload, timeout=60)
            r.raise_for_status()
        data = r.json()
        total = data.get("searchTotalCount", 0)
        results = data.get("searchResults", [])
        print(f"[catalog] {slug}: {total} total, {len(results)} fetched")
        out.write_text(json.dumps(data, indent=1), encoding="utf-8")
        time.sleep(6.0)


def buy_slugs() -> list[str]:
    """Resolve flagship buy slugs from the captured catalog data."""
    slugs: list[str] = []
    for _, cat, _ in CATEGORIES:
        wants = BUY_FAMILIES.get(cat, [])
        if not wants:
            continue
        pf = json.loads((RAW / f"pf_{cat}.json").read_text(encoding="utf-8"))
        for want in wants:
            for item in pf.get("searchResults", []):
                fam = item.get("familyMktName") or ""
                name = item.get("productDisplayName") or item.get("name") or ""
                if want.lower() in fam.lower() or want.lower() in name.lower():
                    mlp = item.get("mlpUrl") or item.get("pdpURL") or ""
                    if mlp.startswith("/us/"):
                        slug = mlp[len("/us/"):].strip("/")
                        if slug not in slugs:
                            slugs.append(slug)
                    break
    return slugs


def phase_buy(s: requests.Session) -> None:
    for slug in buy_slugs():
        out = RAW / f"buy_{slug.replace('/', '_')}.json"
        if out.exists():
            print(f"[buy] {slug}: cached")
            continue
        url = f"https://www.samsung.com/us/{slug}/buy/"
        r = s.get(url, timeout=60)
        if r.status_code == 404:
            print(f"[buy] {slug}: buy page 404 (skipped)")
            time.sleep(3.0)
            continue
        if r.status_code != 200:
            r = get(s, url)
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                      r.text, re.S)
        if not m:
            print(f"[buy] {slug}: no __NEXT_DATA__ (skipped)")
            continue
        data = json.loads(m.group(1))
        out.write_text(json.dumps(data, indent=1), encoding="utf-8")
        print(f"[buy] {slug}: captured ({len(m.group(1))} bytes)")
        time.sleep(5.0)


def phase_specs(s: requests.Session) -> None:
    out = RAW / "spec_smartphones.json"
    if not out.exists():
        models = ("SM-F976,SM-F971,SM-F776,SM-S741,SM-A576,SM-A376,SM-S948,SM-S947,"
                  "SM-S942,SM-F966,SM-F766,SM-F761,SM-S937,SM-S938,SM-S936,SM-S931,"
                  "SM-F956,SM-F741,SM-S721,SM-S928,SM-S926,SM-S921,SM-F731,SM-F946,SM-S711")
        r = get(s, SPEC_COMPARE + models)
        out.write_text(json.dumps(r.json(), indent=1), encoding="utf-8")
        print(f"[specs] spec compare: {len(out.read_text())} bytes")
    fam = RAW / "family_smartphones.json"
    if not fam.exists():
        r = get(s, FAMILY_LIST + ("SM-F976UZVFXAA,SM-F976UDGAXAA,SM-F971ULVFXAA,"
                                  "SM-F971UZGAXAA,SM-F776ULIEXAA,SM-F776ULGAXAA,"
                                  "SM-S741ULGAVZW,SM-A576UDBAXAA,SM-A376ULVAXAA,"
                                  "SM-S948UZVEXAA,SM-S948UZSEXAA,SM-S947UZVEXAA,"
                                  "SM-S947UZSEXAA,SM-S942UZVFXAA,SM-S942UZSFXAA,"
                                  "SM-F966UDBAXAA,SM-F966ULGAXAA,SM-F766UDBEXAA,"
                                  "SM-F766ULGAXAA,SM-F761UZWAXAA,SM-S937UZKEXAA,"
                                  "SM-S938UZKAXAA,SM-S938UZDAXAA,SM-S936UZSAXAA,"
                                  "SM-S936UZKAXAA,SM-S931UZSEXAA,SM-S931UZKEXAA,"
                                  "SM-F956UZSAXAA,SM-F956UAKAXAA,SM-F741UZSAXAA,"
                                  "SM-F741UAKAXAA,SM-S721ULBEXAA,SM-S928UZVEXAA,"
                                  "SM-S928ULGEXAA,SM-S926UZKAXAA,SM-S926ULGAXAA,"
                                  "SM-S921UZKEXAA,SM-S921ULGEXAA,SM-F731UZAAXAA,"
                                  "SM-F946UZKAXAA,SM-F946UZBEXAA,SM-S711UZOEXAA"))
        fam.write_text(json.dumps(r.json(), indent=1), encoding="utf-8")
        print(f"[specs] family list: {len(fam.read_text())} bytes")


def phase_support(s: requests.Session) -> None:
    for name, path in SUPPORT_PAGES:
        out = RAW / f"support_{name}.html"
        if out.exists():
            print(f"[support] {name}: cached")
            continue
        r = get(s, "https://www.samsung.com" + path)
        out.write_text(r.text, encoding="utf-8")
        print(f"[support] {name}: {len(r.text)} bytes")
        time.sleep(4.0)


def phase_home(s: requests.Session) -> None:
    out = RAW / "home.html"
    if out.exists():
        print("[home] cached")
        return
    r = get(s, "https://www.samsung.com/us/")
    out.write_text(r.text, encoding="utf-8")
    print(f"[home] {len(r.text)} bytes")


def wanted_images() -> list[str]:
    """Every upstream image URL the mirror renders, in a stable order."""
    urls: list[str] = []
    seen: set[str] = set()

    def add(u: str | None) -> None:
        if not u or u in seen:
            return
        if not u.startswith("https://images.samsung.com/") and \
           not u.startswith("https://image-us.samsung.com/") and \
           not u.startswith("https://www.samsung.com/"):
            return
        seen.add(u)
        urls.append(u)

    for _, slug, _ in CATEGORIES:
        pf = json.loads((RAW / f"pf_{slug}.json").read_text(encoding="utf-8"))
        for item in pf.get("searchResults", []):
            add(item.get("images", {}).get("largeImage", {}).get("url"))
    for slug in buy_slugs():
        p = RAW / f"buy_{slug.replace('/', '_')}.json"
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        pd = data.get("props", {}).get("pageProps", {}).get("productData", {})
        for prod in pd.get("products", []):
            add(prod.get("defaultImage"))
        # home heroes
    home = (RAW / "home.html").read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r'https://images\.samsung\.com(/[^"\'\s?]+?\.(?:jpg|png|webp))', home):
        add("https://images.samsung.com" + m.group(1))
    for m in re.finditer(r'(?<!:)//images\.samsung\.com(/[^"\'\s?]+?\.(?:jpg|png|webp))', home):
        add("https://images.samsung.com" + m.group(1))
    for m in re.finditer(r'//image-us\.samsung\.com(/[^"\'\s?]+?\.(?:jpg|png|webp))', home):
        add("https://image-us.samsung.com" + m.group(1))
    # support category icons (SVG on the live warranty page)
    for name in ["support_warranty", "support_support_home"]:
        p = RAW / f"{name}.html"
        if not p.exists():
            continue
        shtml = p.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r'(?:https:)?//image-us\.samsung\.com(/[^"\'\s?]+?\.svg)', shtml):
            add("https://image-us.samsung.com" + m.group(1))
    return urls


def phase_images(s: requests.Session) -> None:
    urls = wanted_images()
    print(f"[images] {len(urls)} upstream images wanted")
    manifest = {}
    mf_path = RAW / "image_sources.json"
    if mf_path.exists():
        manifest = json.loads(mf_path.read_text(encoding="utf-8"))
    for i, url in enumerate(urls):
        key = url.split("?")[0].rsplit("/", 1)[-1]
        stem = re.sub(r"[^A-Za-z0-9._-]", "_", key)
        if not re.search(r"\.(jpg|png|webp|svg)$", stem, re.I):
            stem += ".png"
        local = manifest.get(url)
        if local and (BASE / "static" / "images" / local).exists():
            continue
        r = get(s, url, tries=3)
        dest = BASE / "static" / "images" / stem
        n = 2
        while dest.exists() and dest.read_bytes() != r.content:
            dest = BASE / "static" / "images" / f"{n}_{stem}"
            n += 1
        dest.write_bytes(r.content)
        manifest[url] = dest.name
        if (i + 1) % 25 == 0:
            mf_path.write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
            print(f"[images] {i + 1}/{len(urls)}")
        time.sleep(0.7)
    mf_path.write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
    print(f"[images] done: {len(manifest)} files recorded")


def main() -> None:
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    s = session()
    steps = [phase_catalog, phase_buy, phase_specs, phase_support, phase_home, phase_images]
    if phase != "all":
        steps = [f for f in steps if f.__name__ == "phase_" + phase]
        if not steps:
            raise SystemExit(f"unknown phase: {phase}")
    for step in steps:
        step(s)


if __name__ == "__main__":
    main()
