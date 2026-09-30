#!/usr/bin/env python3
"""Capture the full us-appliance.com catalog via the BigCommerce GraphQL API.

The storefront GraphQL token is embedded in every upstream page; we read a
fresh one from the homepage HTML each run. Paginates site.products (50 per
page) and stores every product verbatim under scraped_data/catalog/.

Usage: python3 capture_catalog.py [--start N]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent.parent
SCRAPE = HERE / "scraped_data" / "catalog"
SCRAPE.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

PRODUCT_FIELDS = """
        entityId
        name
        sku
        path
        mpn
        upc
        brand { name entityId }
        plainTextDescription
        description
        prices { price { value formatted } retailPrice { value formatted } }
        height { value unit }
        width { value unit }
        depth { value unit }
        weight { value unit }
        availabilityV2 { status }
        inventory { isInStock }
        reviewSummary { numberOfReviews summationOfRatings }
        customFields { edges { node { name value } } }
        images { edges { node { url(width: 640) altText isDefault } } }
        categories { edges { node { entityId name path } } }
        relatedProducts { edges { node { entityId name path } } }
"""


def get_token() -> str:
    req = urllib.request.Request("https://www.us-appliance.com/",
                                 headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        html = r.read().decode("utf-8", "replace")
    m = re.search(r"Bearer (eyJ[A-Za-z0-9_.\-]+)", html)
    if not m:
        raise RuntimeError("no GraphQL token found on homepage")
    return m.group(1)


def gql(token: str, query: str) -> dict:
    req = urllib.request.Request(
        "https://www.us-appliance.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + token,
                 "User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode())
        except Exception:  # noqa: BLE001
            if attempt == 3:
                raise
            time.sleep(3 * (attempt + 1))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=0)
    args = ap.parse_args()

    token = get_token()
    print("[token] ok", flush=True)

    # category tree once
    tree = gql(token, """{ site { categoryTree { entityId name path
        children { entityId name path children { entityId name path } } } } }""")
    (SCRAPE / "category_tree.json").write_text(
        json.dumps(tree["data"]["site"]["categoryTree"], indent=1),
        encoding="utf-8")
    print("[tree] saved", flush=True)

    page = max(args.start, 0)
    cursor = None
    total = 0
    while True:
        base = "products(first: 50"
        if cursor:
            base += f', after: "{cursor}"'
        base += ")"
        q = "{ site { " + base + " { pageInfo { hasNextPage endCursor } " \
             "edges { node {" + PRODUCT_FIELDS + "} } } } }"
        d = gql(token, q)
        if "errors" in d:
            print(d["errors"], flush=True)
            return 1
        conn = d["data"]["site"]["products"]
        out = SCRAPE / f"page_{page:03d}.json"
        out.write_text(json.dumps(conn, indent=1), encoding="utf-8")
        total += len(conn["edges"])
        print(f"[page {page:03d}] +{len(conn['edges'])} total={total} "
              f"hasNext={conn['pageInfo']['hasNextPage']}", flush=True)
        if not conn["pageInfo"]["hasNextPage"]:
            break
        cursor = conn["pageInfo"]["endCursor"]
        page += 1
        if page % 25 == 0:  # refresh token periodically
            token = get_token()
            print("[token] refreshed", flush=True)
    print("DONE total:", total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
