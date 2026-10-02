#!/usr/bin/env python3
"""Capture the us-appliance.com content pages (support/marketing/brand) verbatim.

Stores raw HTML under scraped_data/pages/ for later normalization into
source_data_content.json. Polite pacing, no auth, anonymous GETs only.

Usage: python3 capture_pages.py
"""
from __future__ import annotations

import pathlib
import sys
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent.parent
OUT = HERE / "scraped_data" / "pages"
OUT.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

PAGES = {
    # home + main category landings
    "home": "/",
    "cooking": "/cooking.html",
    "ranges": "/ranges.html",
    "electric-ranges": "/electric-ranges.html",
    "gas-ranges": "/gas-ranges.html",
    "dual-fuel-ranges": "/dual-fuel-ranges.html",
    "induction-ranges": "/induction-ranges.html",
    "cooktops": "/cooktops.html",
    "ovens": "/ovens.html",
    "microwaves": "/microwaves.html",
    "ventilation": "/ventilation.html",
    "refrigeration": "/refrigeration.html",
    "frdore": "/frdore.html",
    "sidebyside": "/sidebyside.html",
    "builtinfridges": "/builtinfridges.html",
    "bottommount": "/bottommount.html",
    "topmount": "/topmount.html",
    "freezers": "/freezers.html",
    "wine-coolers": "/wine-coolers.html",
    "icemakers": "/icemakers.html",
    "dishwasher": "/dishwasher.html",
    "laundry": "/laundry.html",
    "washers": "/washers.html",
    "front-load": "/front-load.html",
    "top-load": "/top-load.html",
    "dryers": "/dryers.html",
    "electric-dryer": "/electric-dryer.html",
    "gas-dryers": "/gas-dryers.html",
    "appliance-packages": "/appliance-packages.html",
    "kitchen-packages": "/kitchen-packages.html",
    "lapa": "/lapa.html",
    # brands
    "shopbybrand": "/shopbybrand.html",
    "genel": "/genel.html",
    "lg1": "/lg1.html",
    "samsung": "/samsung.html",
    "whirlpool1": "/whirlpool1.html",
    "bosch1": "/bosch1.html",
    "frigidaire1": "/frigidaire1.html",
    "kitchenaid1": "/kitchenaid1.html",
    "gecafeappliances": "/gecafeappliances.html",
    "geprofileappliances": "/geprofileappliances.html",
    "ge-monogram": "/ge-monogram.html",
    "miele2": "/miele2.html",
    "viking": "/viking.html",
    "subzero1": "/subzero1.html",
    "wolfappliance": "/wolfappliance.html",
    "thermador1": "/thermador1.html",
    "maytag1": "/maytag1.html",
    "electroluxappliances": "/electroluxappliances.html",
    "speedqueen": "/speedqueen.html",
    "jennair1": "/jennair1.html",
    "fisherpaykel1": "/fisherpaykel1.html",
    # deals + promos
    "hugepricecuts": "/hugepricecuts.html",
    "clearance": "/clearance.html",
    "rebates": "/rebates.html",
    "financecenter": "/financecenter.html",
    "financeoffers": "/financeoffers.html",
    # support
    "cusser": "/cusser.html",
    "faq": "/faq.html",
    "freedelivery": "/freedelivery.html",
    "ordertracking": "/ordertracking.html",
    "contactus2": "/contactus2.html",
    "price-match-request": "/price-match-request.html",
    "testimonials": "/testimonials.html",
    "warrantyoptions": "/warrantyoptions.html",
    "returninformation": "/returninformation.html",
    "whyusappliance": "/whyusappliance.html",
    "buyingguide": "/buyingguide.html",
    "salestaxinfo": "/salestaxinfo.html",
    "instock": "/in-stock-message-2.html",
    "privacy": "/privacypolicy.html",
    # buying guides
    "guide-refrigerator": "/kitchen-refrigerator-buying-guide/",
    "guide-range": "/kitchen-range-buying-guide/",
    "guide-dishwasher": "/kitchen-dishwasher-buying-guide/",
    "guide-wallovon": "/kitchen-wall-oven-buying-guide/",
    "guide-cooktop": "/kitchen-cooktop-buying-guide/",
    "guide-microwave": "/kitchen-microwave-buying-guide/",
    "guide-washer": "/kitchen-washer-buying-guide/",
    "guide-dryer": "/kitchen-dryer-buying-guide/",
    "guide-venthood": "/kitchen-range-hood-buying-guide/",
    # account / cart shells
    "login": "/login.php",
    "cart": "/cart.php",
    # search calibration pages
    "search-ranges": "/search.php?search_query=ranges&section=product",
    "search-dishwasher-bosch": "/search.php?mode=1&search_query_adv=dishwasher&brand=55",
    "search-price-500-1000": "/search.php?mode=1&search_query_adv=range&price_from=500&price_to=1000",
    "search-content-ranges": "/search.php?section=content&search_query=ranges",
}


def fetch(path: str) -> bytes:
    req = urllib.request.Request("https://www.us-appliance.com" + path,
                                 headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def main() -> int:
    for name, path in PAGES.items():
        dest = OUT / f"{name}.html"
        if dest.exists() and dest.stat().st_size > 10000:
            print(f"[skip] {name}", flush=True)
            continue
        try:
            data = fetch(path)
            dest.write_bytes(data)
            print(f"[ok] {name} {len(data)}b", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {name} {path}: {exc}", flush=True)
        time.sleep(0.8)
    # ShopperApproved merchant reviews (testimonials widget), 3 pages
    for page in (1, 2, 3):
        dest = OUT / f"shopperapproved_p{page}.js"
        if dest.exists():
            continue
        try:
            url = ("https://www.shopperapproved.com/widgets/21100/merchant/"
                   "review-page/d2eJSVCW1H8h.js"
                   + ("?page=%d" % page if page > 1 else ""))
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                dest.write_bytes(r.read())
            print(f"[ok] shopperapproved p{page}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] shopperapproved p{page}: {exc}", flush=True)
        time.sleep(1.0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
