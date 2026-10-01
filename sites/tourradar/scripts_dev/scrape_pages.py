#!/usr/bin/env python3
"""Phase C: slow scrape of landing pages (destinations, operators, book-now
room samples, static pages). One page at a time with generous delays.

Usage: python3 scrape_pages.py
Writes scraped_data/pages/<name>.json records.
"""
import json
import pathlib
import random
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "scraped_data" / "pages"
OUT.mkdir(parents=True, exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

DESTS = ["japan", "egypt", "morocco", "south-africa", "china", "india",
         "new-zealand", "philippines", "sri-lanka", "thailand", "vietnam",
         "croatia", "greece", "iceland", "ireland", "italy", "portugal",
         "scotland", "spain", "turkey", "canada", "costa-rica", "usa",
         "argentina", "brazil", "chile", "peru", "mexico", "kenya",
         "tanzania", "namibia", "jordan", "nepal", "france", "england",
         "germany", "switzerland", "indonesia", "australia", "europe",
         "africa", "asia", "latin-america"]

STYLES = ["adventure", "bicycle", "hiking-trekking", "northern-lights",
          "river-cruise", "in-depth-cultural", "coach-bus", "train-rail",
          "beach", "family", "private", "safari", "sailing", "polar",
          "food-culinary", "health-spa-wellness", "overland-truck",
          "wildlife", "festival-events"]

REGIONS_B = ["south-america", "eastern-europe", "great-britain-uk",
             "nordic-scandinavia"]

PLACES_V = ["islands-bali", "islands-greek-islands", "islands-sicily",
            "mountain-annapurna", "mountain-everest", "mountain-machu-picchu",
            "mountain-mount-kilimanjaro", "national-park-grand-canyon",
            "region-amalfi-coast", "region-antarctica-south-pole",
            "region-arctic-north-pole", "region-golden-triangle-southeast-asia",
            "region-great-barrier-reef", "region-holy-land", "region-patagonia",
            "region-tuscany", "river-danube", "river-douro", "river-main",
            "river-mekong", "river-nile", "river-rhine", "state-alaska",
            "state-california"]

OPERATORS = ["intrepid", "g-adventures", "contiki", "globus", "collette",
             "trafalgar", "cosmos", "expat-explore-travel", "topdeck",
             "exodus-travels", "explore", "intro-travel", "one-life-adventures",
             "trutravels", "europamundo", "stunning-tours", "vio-travel",
             "wonderful-holidays-uk", "the-dragon-trip", "aborigen-tours",
             "click-tours", "stm-tours-llc", "realistic-asia", "macbackpackers",
             "travel-talk", "bamba", "goway", "exodus", "g-adventures",
             "explore!", "intrepid", "topdeck"]

STATIC_PAGES = [
    ("about", "https://www.tourradar.com/about"),
    ("contact", "https://www.tourradar.com/contact"),
    ("trust", "https://www.tourradar.com/trust"),
    ("cancellation-policy", "https://www.tourradar.com/cancellation-policy"),
    ("terms-conditions", "https://www.tourradar.com/terms-conditions"),
    ("privacy", "https://www.tourradar.com/privacy"),
    ("operators-list", "https://www.tourradar.com/operators-list"),
    ("reviews-of-tourradar", "https://www.tourradar.com/reviews-of-tourradar"),
    ("sales-escape-sale", "https://www.tourradar.com/sales/escape-sale"),
    ("solo", "https://www.tourradar.com/s/solo"),
    ("group", "https://www.tourradar.com/group"),
    ("moments", "https://www.tourradar.com/moments"),
    ("organized-adventures", "https://www.tourradar.com/organized-adventures"),
    ("deals-europe", "https://www.tourradar.com/deals/europe"),
    ("deals-asia", "https://www.tourradar.com/deals/asia"),
    ("deals-africa", "https://www.tourradar.com/deals/africa"),
    ("deals-latin-america", "https://www.tourradar.com/deals/latin-america"),
    ("deals-north-america", "https://www.tourradar.com/deals/north-america"),
    ("deals-australia-oceania", "https://www.tourradar.com/deals/australia-oceania"),
    ("i-africa-safari", "https://www.tourradar.com/i/africa-safari"),
    ("llp-rise", "https://www.tourradar.com/llp/rise"),
    ("mlp-tourradar-benefits", "https://www.tourradar.com/mlp/tourradar-benefits"),
    ("login", "https://www.tourradar.com/login"),
    ("wishlist-new", "https://www.tourradar.com/wishlists/new"),
]

# book-now room samples: (tour_id, date, n) — real guaranteed departures
BOOK_SAMPLES = [
    ("46923", "14.03.2027", 2),
    ("255", "05.04.2027", 2),
    ("259264", "01.10.2026", 2),
]


def capture(page, url, name, extra_js=None, wait=7000):
    rec = {"name": name, "url": url}
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(wait)
    rec["title"] = page.title()
    rec["text"] = page.evaluate("() => document.body.innerText")
    rec["url_final"] = page.url
    rec["images"] = page.evaluate(
        "() => [...document.querySelectorAll('img')].map(i => ({src: i.currentSrc || i.src, alt: (i.alt||'').slice(0,100)})).filter(x => x.src && !x.src.includes('data:'))")
    rec["links"] = page.evaluate(
        "() => [...document.querySelectorAll('a')].map(a => ({h: a.getAttribute('href'), t: (a.innerText||'').trim().slice(0,50)})).filter(x => x.h && !x.h.startsWith('#')).slice(0, 400)")
    if extra_js:
        rec["extra"] = page.evaluate(extra_js)
    (OUT / f"{name}.json").write_text(json.dumps(rec, indent=1))
    print(f"[{name}] ok ({len(rec['text'])} chars)", flush=True)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000}, user_agent=UA, locale="en-US")
        page = ctx.new_page()
        jobs = []
        for d in DESTS:
            jobs.append((f"d-{d}", f"https://www.tourradar.com/d/{d}"))
        for s in STYLES:
            jobs.append((f"f-{s}", f"https://www.tourradar.com/f/{s}"))
        for b in REGIONS_B:
            jobs.append((f"b-{b}", f"https://www.tourradar.com/b/{b}"))
        for v in PLACES_V:
            jobs.append((f"v-{v}", f"https://www.tourradar.com/v/{v}"))
        for o in OPERATORS:
            jobs.append((f"o-{o}", f"https://www.tourradar.com/o/{o}"))
        for name, url in STATIC_PAGES:
            jobs.append((name, url))
        for tid, date, n in BOOK_SAMPLES:
            jobs.append((f"booknow-{tid}",
                         f"https://www.tourradar.com/book-now/{tid}?date={date}&type=book&travellers[1]={n}"))
        for name, url in jobs:
            if (OUT / f"{name}.json").exists():
                continue
            for attempt in range(4):
                try:
                    capture(page, url, name, wait=9000 if name.startswith("booknow") else 7000)
                    break
                except Exception as e:
                    print(f"[{name}] ERR {str(e)[:90]}", flush=True)
                    time.sleep(15)
            time.sleep(14 + random.random() * 8)
        browser.close()
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
