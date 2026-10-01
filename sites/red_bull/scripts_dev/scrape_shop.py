#!/usr/bin/env python3
"""Scrape the Red Bull Shop US (www.redbullshopus.com, Shopify) catalog
into scraped_data/shop/.

Uses the public Shopify products.json endpoint (3 pages x 100 products)
plus the product detail pages for the curated subset, and records the
CDN image URLs the products actually render.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_lib import fetch, save  # noqa: E402

SITE = Path(__file__).resolve().parents[1]
OUT = SITE / "scraped_data" / "shop"
SHOP = "https://www.redbullshopus.com"


def main() -> None:
    products = []
    for page in range(1, 5):
        url = f"{SHOP}/products.json?limit=100&page={page}"
        body = fetch(url, headers={"User-Agent": fetch.__globals__["UA"],
                                  "Accept": "application/json"})
        d = json.loads(body.decode("utf-8"))
        batch = d.get("products", [])
        print(f"  page {page}: {len(batch)} products")
        products.extend(batch)
        if len(batch) < 100:
            break
        time.sleep(0.4)
    # de-dup by handle
    seen, uniq = set(), []
    for p in products:
        if p["handle"] in seen:
            continue
        seen.add(p["handle"])
        uniq.append(p)
    save(OUT / "products.json", {"source": f"{SHOP}/products.json",
                                 "count": len(uniq), "products": uniq})
    print(f"saved {len(uniq)} unique products")

    # collections listing (nav categories)
    for path, name in [("/collections", "collections"),
                       ("/collections/apparel", "collection_apparel"),
                       ("/collections/headwear", "collection_headwear")]:
        try:
            body = fetch(f"{SHOP}{path}")
            save(OUT / f"{name}.html", body)
            print(f"  {name}: {len(body)} bytes")
        except Exception as e:                                 # noqa: BLE001
            print(f"  !! {name}: {e}")
        time.sleep(0.4)


if __name__ == "__main__":
    main()
