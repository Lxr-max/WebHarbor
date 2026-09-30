#!/usr/bin/env python3
"""Parse captured cars.com SERP pages into the listing corpus.

Reads scraped_data/captures/serp-*.html (real upstream renders), extracts
every vehicle card (visible fields + the page's own embedded analytics
attributes), the CarsWeb.SearchController.index payload (result totals,
selected filters) and the srp_filters filter taxonomy, and writes
scraped_data/serp_cards.json (build-time intermediate).

Run:  python3 scripts_dev/parse_serp.py
"""
import json
import os
import re
import sys
from html import unescape

HERE = os.path.dirname(os.path.abspath(__file__))
CAP = os.path.join(HERE, "..", "scraped_data", "captures")
OUT = os.path.join(HERE, "..", "scraped_data")


def card_text(block):
    t = re.sub(r"<[^>]+>", " ", block)
    return " ".join(unescape(t).split())


def parse_card(block):
    """One <li> vehicle card block -> dict of the fields the SERP renders."""
    out = {}
    m = re.search(r'vehicle-card-([0-9a-f-]{36})"', block)
    if not m:
        return None
    out["listing_id"] = m.group(1)
    m = re.search(r'data-card-href="([^"]+)"', block)
    if m:
        href = unescape(m.group(1))
        out["detail_path"] = href.split("?")[0]
    out["total_photos"] = int(m.group(1)) if (m := re.search(r'total-photos="(\d+)"', block)) else None
    out["photos"] = re.findall(r'<img[^>]+src="(https://platform\.cstatic-images\.com/[^"]+)"', block)
    # title anchor carries the page's own data attributes
    m = re.search(r'<a data-card-link="" href="[^"]*?"[^>]*data-make="([^"]*)"[^>]*>', block)
    if not m:
        m = re.search(r'<a data-card-link=""[^>]*>', block)
        if not m:
            return None
    anchor = m.group(0)
    for attr in ("make", "model", "trim", "year", "price", "mileage", "vin",
                 "stocktype", "bodystyle", "drivetrain", "fueltype",
                 "exteriorcolor", "msrp", "cpoindicator"):
        mm = re.search(rf'data-{attr}="([^"]*)"', anchor)
        if mm and mm.group(1) != "":
            out[attr] = unescape(mm.group(1))
    # visible fields
    mm = re.search(r"(\$[0-9][0-9,]{2,})(?:\s*<|\s)", block)
    text = card_text(block)
    mm = re.search(r"\$(\d{1,3}(?:,\d{3})+|\d{3,})", text)
    if mm:
        out["price_display"] = mm.group(0)
    mm = re.search(r"([\d,]+) mi\.", text)
    if mm:
        out["mileage_display"] = mm.group(1)
    mm = re.search(r"Est\. \$(\d+)/mo", text)
    if mm:
        out["monthly_est"] = int(mm.group(1))
    m = re.search(r'data-monthly-payment="([^"]+)"', block)
    if m:
        try:
            mp = json.loads(unescape(m.group(1)))
            out["monthly_popover"] = {
                "down_payment": mp["popover"]["datums"][0]["display_value"]["text"],
                "net_trade_in": mp["popover"]["datums"][1]["display_value"]["text"],
                "months": mp["popover"]["datums"][2]["display_value"]["text"],
                "apr": mp["popover"]["datums"][3]["display_value"]["text"],
                "sales_tax": mp["popover"]["datums"][4]["display_value"]["text"],
            }
        except Exception:
            pass
    mm = re.search(r'data-badge-variant="([^"]*)"[^>]*data-badge-value="([^"]*)"', block) or \
         re.search(r'data-badge-value="([^"]*)"[^>]*data-badge-variant="([^"]*)"', block)
    if mm:
        vals = list(mm.groups())
        out["deal_badge"] = {"variant": vals[0] if "deal" in vals[0] else vals[1],
                             "value": vals[1] if "deal" in vals[0] else vals[0]}
    m = re.search(r'data-badge-description="([^"]*)"', block)
    if m:
        out["deal_badge"]["description"] = unescape(m.group(1))
    # dealer + rating + location
    m = re.search(r'name="star" label="Review rating"[^>]*></fuse-svg>\s*<span>([\d.]+)</span>', block)
    if m:
        out["dealer_rating"] = float(m.group(1))
    text2 = text
    # dealer name: the small span right before the rating datum
    m = re.search(r'<span class="fuse-body-small"[^>]*>([^<]+)</span>\s*'
                  r'</p>\s*<div class="datum-icon review-star">', block)
    if m:
        out["seller_name"] = unescape(m.group(1)).strip()
    m = re.search(r'name="map-marker-outline"[^>]*></fuse-svg>\s*<span>([^<]+)</span>', block)
    if m:
        out["location_display"] = unescape(m.group(1)).strip()
    # footer banner (e.g. Certified Pre-Owned / Home Delivery)
    m = re.search(r'<div class="footer-banner">\s*<div class="datum-icon[^"]*">\s*'
                  r'<fuse-svg name="([^"]+)"[^>]*></fuse-svg>\s*<span>([^<]+)</span>', block)
    if m:
        out["footer_banner"] = unescape(m.group(2)).strip()
    # title text
    m = re.search(r'<span class="fuse-body"[^>]*>\s*([^<]+?)\s*</span>', block)
    if m:
        out["title"] = unescape(m.group(1)).strip()
    return out


def parse_serp(path):
    html = open(path, encoding="utf-8").read()
    result = {"cards": [], "totals": {}, "filters": None}
    # embedded payload
    m = re.search(r'<script type="application/json" id="CarsWeb.SearchController\.index">\s*(\{.*?\})\s*</script>', html, re.S)
    if m:
        try:
            payload = json.loads(m.group(1))
            md = payload["srp_results"]["metadata"]
            result["totals"] = {
                "total_listings": md.get("total_listings"),
                "page": md.get("page"),
                "page_size": md.get("page_size"),
                "total_pages": md.get("total_pages"),
                "sort": md.get("sort"),
                "selected_filters": md.get("selected_search_filters"),
            }
            result["search_title"] = payload["srp_results"].get("search_title")
            result["filters"] = payload.get("srp_filters")
        except Exception as e:
            print(f"[warn] payload parse failed for {path}: {e}", file=sys.stderr)
    # cards
    for m in re.finditer(r'<li>\s*<fuse-card data-listing-id="([0-9a-f-]{36})"(.*?)(?=<li>\s*<fuse-card data-listing-id=|</ol>)', html, re.S):
        pass
    # simpler: split on card boundaries
    parts = re.split(r'vehicle-card-([0-9a-f-]{36})"', html)
    for i in range(1, len(parts), 2):
        lid = parts[i]
        block = parts[i + 1]
        end = block.find('<li>')
        card = parse_card(f'vehicle-card-{lid}"' + (block[:end] if end > 0 else block[:12000]))
        if card and card.get("listing_id") == lid:
            result["cards"].append(card)
    return result


def main():
    all_cards = {}
    serp_meta = {}
    taxonomies = {}
    for fn in sorted(os.listdir(CAP)):
        if not (fn.startswith("serp-") and fn.endswith(".html")):
            continue
        key = fn[:-5]
        r = parse_serp(os.path.join(CAP, fn))
        n = 0
        for card in r["cards"]:
            lid = card["listing_id"]
            if lid in all_cards:
                # merge: keep first, but note the SERPs it appeared in
                all_cards[lid].setdefault("serps", []).append(key) if key not in all_cards[lid].get("serps", []) else None
                for f in ("price_display", "mileage_display", "monthly_est", "dealer_rating", "location_display", "photos", "total_photos", "deal_badge"):
                    if f in card and f not in all_cards[lid]:
                        all_cards[lid][f] = card[f]
            else:
                card.setdefault("serps", [key])
                all_cards[lid] = card
            n += 1
        if r["cards"]:
            serp_meta[key] = {"totals": r["totals"], "search_title": r.get("search_title"), "cards": n}
        if r["filters"] and "stock_type" not in taxonomies:
            taxonomies["serp_filters"] = r["filters"]
    with open(os.path.join(OUT, "serp_cards.json"), "w") as f:
        json.dump({"listings": list(all_cards.values()), "serps": serp_meta}, f, indent=1)
    if taxonomies:
        with open(os.path.join(OUT, "serp_filters.json"), "w") as f:
            json.dump(taxonomies["serp_filters"], f, indent=1)
    print(f"[parse_serp] {len(all_cards)} unique listings from {len(serp_meta)} serps")


if __name__ == "__main__":
    main()
