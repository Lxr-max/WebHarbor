#!/usr/bin/env python3
"""Scrape the 19 energy-drink product pages into scraped_data/products/.

The product pages are server-rendered; each page yields:
  - product name / flavor / tagline / description
  - the three benefit blocks (stay alert / reduce fatigue / kickstart)
  - the ingredient cards (caffeine, taurine, B-group vitamins, sugars, water)
  - available sizes
  - the product can + scene image URLs (storyblok)
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_lib import BASE, fetch, save  # noqa: E402

SITE = Path(__file__).resolve().parents[1]
OUT = SITE / "scraped_data" / "products"

PRODUCTS = [
    "red-bull-energy-drink", "red-bull-zero", "red-bull-sugarfree",
    "red-bull-summer-edition", "red-bull-summer-edition-sugarfree",
    "red-bull-apple-edition", "red-bull-iced-edition",
    "red-bull-iced-edition-sugarfree", "red-bull-peach-edition",
    "red-bull-peach-edition-sugarfree", "red-bull-pink-edition",
    "red-bull-pink-edition-sugarfree", "red-bull-amber-edition",
    "red-bull-sea-blue-edition", "red-bull-sea-blue-edition-sugarfree",
    "red-bull-coconut-edition", "red-bull-yellow-edition",
    "red-bull-red-edition",
]

LINES = {
    "red-bull-energy-drink": "Red Bull Energy Drink",
    "red-bull-zero": "Red Bull Zero",
    "red-bull-sugarfree": "Red Bull Sugarfree",
}


def strip_tags(frag: str) -> str:
    t = re.sub(r"<[^>]+>", " ", frag)
    return re.sub(r"\s+", " ", t).strip()


def parse_product(slug: str, html: str) -> dict:
    rec = {"slug": slug, "url": f"{BASE}/us-en/energydrink/products/{slug}"}

    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
    rec["title"] = strip_tags(m.group(1)) if m else None

    m = re.search(r'property="og:title" content="([^"]+)"', html)
    rec["og_title"] = m.group(1) if m else None
    m = re.search(r'property="og:image" content="([^"]+)"', html)
    rec["og_image"] = m.group(1) if m else None
    m = re.search(r'name="description" content="([^"]+)"', html)
    rec["meta_description"] = m.group(1) if m else None

    # flavor name + description (first desktop occurrence)
    m = re.search(r'ProductEditionStageDesktop_flavor-text__pMUKw[^>]*>(.*?)</p>', html, re.S)
    rec["flavor_text"] = strip_tags(m.group(1)) if m else None

    # benefits list
    m = re.search(r'ProductEditionStageDesktop_benefits-list__n1Rj_.*?</ul>', html, re.S)
    if m:
        pts = [strip_tags(li) for li in re.findall(r"<li[^>]*>(.*?)</li>", m.group(0), re.S)]
        rec["benefits"] = [p for p in pts if p]

    # ingredient cards (unique by title) — two layouts: IngredientsList (editions)
    # and IngredientsTeaser (the original/zero/sugarfree flagship pages)
    cards = re.findall(r'IngredientsList_ingredients-ingredient__HKwA0.*?</cosmos-text>', html, re.S)
    seen, ingredients = set(), []
    for c in cards:
        t = re.search(r'IngredientsList_ingredients-ingredient-title___viH8[^>]*>(.*?)</cosmos-title>', c, re.S)
        b = re.search(r'<cosmos-text>(.*?)</cosmos-text>', c, re.S)
        if t:
            title = strip_tags(t.group(1))
            if title in seen:
                continue
            seen.add(title)
            ingredients.append({"title": title,
                                "text": strip_tags(b.group(1)) if b else ""})
    if not ingredients:
        cards = re.findall(r'IngredientsTeaser_ingredient__s9aM4.*?</cosmos-text>', html, re.S)
        for c in cards:
            t = re.search(r'IngredientsTeaser_ingredient__title__7ZhAF[^>]*>(.*?)</cosmos-title>', c, re.S)
            b = re.search(r'<cosmos-text>(.*?)</cosmos-text>', c, re.S)
            if t:
                title = strip_tags(t.group(1))
                if title in seen:
                    continue
                seen.add(title)
                ingredients.append({"title": title,
                                    "text": strip_tags(b.group(1)) if b else ""})
    rec["ingredients"] = ingredients

    # sizes
    m = re.search(r'ProductSizes_list__tC_07.*?</ul>', html, re.S)
    if m:
        sizes = [strip_tags(s) for s in re.findall(r'<cosmos-badge>(.*?)</cosmos-badge>', m.group(0), re.S)]
        rec["sizes"] = [s for s in sizes if s]
    else:
        m = re.search(r'ProductSizes_product-sizes__Yc0Ze[^>]*>(.*?)</div>', html, re.S)
        if m:
            sizes = [strip_tags(li) for li in re.findall(r"<li[^>]*>(.*?)</li>", m.group(0), re.S)]
            rec["sizes"] = [s for s in sizes if s]

    # product images: can images with alt text, so each product's OWN can
    # can be picked (pages also render other products' cans in the strip)
    cans = []
    seen = set()
    for m in re.finditer(r"<img[^>]+>", html):
        tag = m.group(0)
        alt = re.search(r'alt="([^"]*)"', tag)
        src = re.search(r'src="([^"]+)"', tag)
        if not src or "storyblok" not in src.group(1):
            continue
        url = src.group(1)
        if url in seen:
            continue
        seen.add(url)
        cans.append({"alt": (alt.group(1) if alt else "").strip(), "url": url})
    rec["can_images"] = cans
    scene = sorted(set(re.findall(
        r'https://www\.redbull\.com/energydrink/v1/resources/storyblok/images/f/287059/2314x1380/[^"\'\s\\]+', html)))
    rec["scene_images"] = [s for s in scene if "/m/1000x0" in s or "/m/1500x0" in s][:2]

    return rec


def main() -> None:
    listing = fetch(f"{BASE}/energydrink").decode("utf-8", "replace")
    save(OUT / "_listing.html", listing.encode())
    for slug in PRODUCTS:
        out = OUT / f"{slug}.json"
        if out.exists():
            continue
        url = f"{BASE}/us-en/energydrink/products/{slug}"
        try:
            html = fetch(url).decode("utf-8", "replace")
        except Exception as e:                                 # noqa: BLE001
            print(f"  !! {slug}: {e}")
            continue
        save(OUT / f"{slug}.html", html.encode())
        rec = parse_product(slug, html)
        rec["line"] = LINES.get(slug, "Red Bull Editions")
        save(out, rec)
        print(f"  ok {slug}: {rec['title']!r} sizes={rec.get('sizes')} "
              f"ingredients={len(rec['ingredients'])} cans={len(rec['can_images'])}")
        time.sleep(0.3)
    print("done")


if __name__ == "__main__":
    main()
