#!/usr/bin/env python3
"""Build the tracked source_data/*.json corpus from scraped_data captures.

Everything here reads the parsed upstream intermediates that
scripts_dev/parse_*.py wrote into scraped_data/ and folds them into the
tracked source_data snapshots the seeder reads:

  source_data/listings.json     the vehicle corpus (SERP cards + detail pages)
  source_data/dealers.json      dealer directory + dealer pages
  source_data/models.json       research model pages
  source_data/compares.json     side-by-side comparisons
  source_data/valuation.json    Instant Cash Offer wizard taxonomy + estimates
  source_data/benchmark_users.json  authored benchmark fixtures

Run:  python3 scripts_dev/build_source_data.py
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SCRAP = os.path.join(ROOT, "scraped_data")
SRC = os.path.join(ROOT, "source_data")


def load(name, default=None):
    path = os.path.join(SCRAP, name)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default if default is not None else {}


def slugify(text):
    s = re.sub(r"[^A-Za-z0-9]+", "_", (text or "").strip())
    return s.strip("_").lower()


FUEL_SLUGS = {"Gasoline": "gasoline", "Electric": "electric", "Hybrid": "hybrid",
              "Diesel": "diesel", "Flex": "e85_flex_fuel", "Plug-In Hybrid": "plug_in_hybrid",
              "E85 Flex Fuel": "e85_flex_fuel", "Gas": "gasoline", "Unknown": None}

DRIVETRAIN_SLUGS = {"All-wheel Drive": "all_wheel_drive", "Four-wheel Drive": "four_wheel_drive",
                    "Front-wheel Drive": "front_wheel_drive", "Rear-wheel Drive": "rear_wheel_drive",
                    "All Wheel Drive": "all_wheel_drive", "Unknown": "unknown"}

TRANSMISSION_SLUGS = {"automatic": ["automatic", "a/t", "8-speed automatic", "10-speed automatic",
                                     "6-speed automatic", "9-speed automatic", "automatic transmission"],
                       "cvt": ["cvt", "continuously variable"],
                       "manual": ["manual", "m/t", "6-speed manual", "5-speed manual", "7-speed manual"],
                       "automanual": ["automanual", "dual shift mode", "dct", "automated manual"]}


def transmission_slug(text):
    t = (text or "").lower()
    for slug, needles in TRANSMISSION_SLUGS.items():
        if any(n in t for n in needles):
            return slug
    return None


def color_slug(text):
    s = (text or "").lower()
    for c in ("beige", "black", "blue", "brown", "gold", "gray", "grey", "green",
              "orange", "pink", "purple", "red", "silver", "teal", "white", "yellow"):
        if c in s:
            return "grey" if c == "grey" else c
    return None


def cylinders_from_engine(text):
    m = re.search(r"(I-4|I4|V-?(\d{1,2})|I-3|I-6|V6|V8|straight-6|4 cyl|6 cyl|8 cyl)", (text or ""))
    if not m:
        return None
    tok = m.group(0).lower()
    if "i-3" in tok or "i3" in tok:
        return 3
    if "i-4" in tok or "i4" in tok or "4 cyl" in tok:
        return 4
    if "i-5" in tok:
        return 5
    if "i-6" in tok or "6 cyl" in tok or "v6" in tok or tok == "v-6":
        return 6
    if "v8" in tok or tok == "v-8" or "8 cyl" in tok:
        return 8
    if m.group(2):
        return int(m.group(2))
    return None


def money_int(text):
    if not text:
        return None
    m = re.search(r"\$?([\d,]+)", str(text))
    return int(m.group(1).replace(",", "")) if m else None


def build_listings():
    serp = load("serp_cards.json", {"listings": []})
    vds = {v.get("listing_id"): v for v in load("vd_pages.json", []) if v.get("listing_id")}
    # SERP keys used for filter-derived stamps: a listing returned under an
    # upstream filter query carries that attribute (declared in provenance).
    serp_stamps = {}
    for l in serp.get("listings", []):
        for key in l.get("serps", []):
            serp_stamps.setdefault(l["listing_id"], set()).add(key)
    out = []
    for card in serp.get("listings", []):
        lid = card["listing_id"]
        row = {
            "listing_id": lid,
            "stock_type": {"new": "New", "used": "Used", "cpo": "Certified"}.get(
                (card.get("stocktype") or "").lower(), card.get("stocktype")),
            "year": int(card["year"]) if str(card.get("year", "")).isdigit() else None,
            "make": card.get("make"),
            "make_slug": slugify(card.get("make")),
            "model": card.get("model"),
            "model_slug": (slugify(card.get("make")) + "-" + slugify(card.get("model")))
                          if card.get("make") and card.get("model") else slugify(card.get("model")),
            "trim": card.get("trim"),
            "price": money_int(card.get("price_display") or card.get("price")),
            "price_display": card.get("price_display"),
            "mileage": money_int(card.get("mileage_display") or card.get("mileage")),
            "body_style": card.get("bodystyle"),
            "body_style_slug": slugify(card.get("bodystyle")),
            "drivetrain": card.get("drivetrain"),
            "drivetrain_slug": DRIVETRAIN_SLUGS.get(card.get("drivetrain")),
            "fuel_type": card.get("fueltype"),
            "fuel_slug": FUEL_SLUGS.get(card.get("fueltype")),
            "exterior_color": card.get("exteriorcolor"),
            "exterior_color_slug": color_slug(card.get("exteriorcolor")),
            "msrp": money_int(card.get("msrp")),
            "vin": card.get("vin"),
            "monthly_est": card.get("monthly_est"),
            "seller_name": card.get("seller_name"),
            "seller_rating": card.get("dealer_rating"),
            "location_display": card.get("location_display"),
            "deal_badge": (card.get("deal_badge") or {}).get("value")
                           if isinstance(card.get("deal_badge"), dict) else None,
            "total_photos": card.get("total_photos"),
            "photos": card.get("photos", []),
            "title": card.get("title"),
            "serps": sorted(serp_stamps.get(lid, [])),
        }
        # CPO: upstream renders the card title with a "Certified" prefix and
        # a "Certified Pre-Owned" footer banner (data-stocktype stays "Used").
        if str(card.get("title") or "").startswith("Certified") or \
                card.get("footer_banner") == "Certified Pre-Owned":
            row["stock_type"] = "Certified"
        m = re.search(r"([A-Za-z .]+), ([A-Z]{2}) \((\d+) mi\)", card.get("location_display") or "")
        if m:
            row["city"], row["state"], row["distance_miles"] = m.group(1).strip(), m.group(2), int(m.group(3))
        # filter-derived stamps from the upstream queries the card appeared in
        stamps = row["serps"]
        if not row.get("transmission_slug"):
            if any("manual" in s for s in stamps):
                row["transmission"] = "Manual"
                row["transmission_slug"] = "manual"
        if row.get("fuel_slug") is None and any("electric" in s for s in stamps):
            row["fuel_type"], row["fuel_slug"] = "Electric", "electric"
        if row.get("fuel_slug") is None and any("hybrid" in s for s in stamps):
            row["fuel_type"], row["fuel_slug"] = "Hybrid", "hybrid"
        if any("fso" in s for s in stamps):
            row["seller_type"] = "private_seller"
        else:
            row["seller_type"] = "dealership"
        # deal badge normalization: the SERP renders "Great Deal/Good Deal/Fair Deal"
        badge = row.get("deal_badge")
        if badge and badge not in ("Great Deal", "Good Deal", "Fair Deal"):
            row["deal_badge"] = None
        # merge the detail page when captured
        vd = vds.get(lid)
        if vd:
            row["has_detail"] = True
            for k in ("vin", "stock_number", "exterior_color", "interior_color",
                      "engine_desc", "mpg", "transmission", "seller_notes",
                      "cpo_program", "dealer_name", "dealer_phone", "dealer_address",
                      "dealer_hours", "dealer_reviews", "dealer_review_count",
                      "est_monthly", "apr", "sales_tax_pct"):
                if vd.get(k):
                    row[k] = vd[k]
            if vd.get("price_breakdown"):
                row["price_breakdown"] = vd["price_breakdown"]
            if vd.get("price_history"):
                row["price_history"] = vd["price_history"]
            if vd.get("history"):
                row["history"] = vd["history"]
            if vd.get("features"):
                row["features"] = vd["features"]
            if vd.get("good_deal_range"):
                row["good_deal_low"] = money_int(vd["good_deal_range"][0])
                row["good_deal_high"] = money_int(vd["good_deal_range"][1])
            if vd.get("deal_badge"):
                row["deal_badge"] = vd["deal_badge"]
            for k in ("consumer_recommend_pct", "consumer_rating", "consumer_review_count",
                      "consumer_categories", "consumer_reviews"):
                if vd.get(k) is not None:
                    row[k] = vd[k]
            if vd.get("photos"):
                row["detail_photos"] = vd["photos"]
            if vd.get("mileage_display"):
                row["mileage"] = money_int(vd["mileage_display"]) or row["mileage"]
            if vd.get("seller_notes"):
                row["seller_notes"] = vd["seller_notes"]
            if not row.get("transmission") and vd.get("transmission"):
                row["transmission"] = vd["transmission"]
        if row.get("transmission") and not row.get("transmission_slug"):
            row["transmission_slug"] = transmission_slug(row["transmission"])
        if row.get("engine_desc") and not row.get("cylinders"):
            row["cylinders"] = cylinders_from_engine(row["engine_desc"])
        if row.get("est_monthly") and not row.get("monthly_est"):
            row["monthly_est"] = row["est_monthly"]
        if row.get("apr") and not row.get("monthly_apr"):
            row["monthly_apr"] = float(row["apr"])
        if row.get("monthly_est"):
            row["monthly_months"] = 72
        out.append(row)
    return out


def build_dealers(listings):
    raw = load("dealers_raw.json", {"directory": {}, "pages": [], "review_pages": []})
    directory = raw.get("directory", {})
    pages = {p["slug"]: p for p in raw.get("pages", []) if p.get("slug")}
    pages_by_name = {p["name"]: p for p in raw.get("pages", []) if p.get("name")}
    review_pages = {r["slug"]: r for r in raw.get("review_pages", []) if r.get("slug")}
    review_pages_by_name = {r.get("dealer_name"): r for r in raw.get("review_pages", [])}
    # also derive dealer stubs from listing seller names when no directory row exists
    by_name = {}
    for slug, d in directory.items():
        by_name[d["name"]] = d
    for l in listings:
        name = l.get("dealer_name") or l.get("seller_name")
        if name and name not in by_name:
            by_name[name] = {"slug": slugify(name), "name": name,
                             "from_listing": l["listing_id"]}
    # makes carried per dealer, derived from the captured listing corpus
    # (the upstream directory cards do not expose the make list)
    makes_by_seller = {}
    for l in listings:
        name = l.get("dealer_name") or l.get("seller_name")
        if name and l.get("make"):
            makes_by_seller.setdefault(name, set()).add(l["make"])
    # seller-side facts from the corpus for dealers whose directory/detail
    # page was not captured: card star rating, review count/hours/address/
    # phone from the vehicle-detail Seller's-info blocks
    seller_facts = {}
    for l in listings:
        name = l.get("dealer_name") or l.get("seller_name")
        if not name:
            continue
        f = seller_facts.setdefault(name, {})
        if l.get("seller_rating") and "rating" not in f:
            try:
                f["rating"] = float(l["seller_rating"])
            except (TypeError, ValueError):
                pass
        if l.get("dealer_reviews") and "review_count" not in f:
            m = re.match(r"([\d,]+)", str(l["dealer_reviews"]))
            if m:
                f["review_count"] = int(m.group(1).replace(",", ""))
        if l.get("dealer_hours") and "hours" not in f:
            f["hours"] = l["dealer_hours"]
        if l.get("dealer_address") and "address" not in f:
            f["address"] = l["dealer_address"]
        if l.get("dealer_phone") and "phone_new" not in f:
            f["phone_new"] = l["dealer_phone"]
        if l.get("city") and "city" not in f:
            f["city"] = l.get("city")
        if l.get("state") and "state" not in f:
            f["state"] = l.get("state")
    out = []
    for name, d in by_name.items():
        row = dict(d)
        page = pages.get(d["slug"]) or pages_by_name.get(name)
        if page:
            # keep the upstream (hyphenated) slug/id when the page carries it
            if page.get("slug"):
                row["slug"] = page["slug"]
            if page.get("dealer_id"):
                row["dealer_id"] = page["dealer_id"]
            for k in ("hours", "about", "highlights", "sales_team", "service_menu"):
                if page.get(k):
                    row[k] = page[k]
            if page.get("detail_reviews"):
                row["detail_reviews"] = page["detail_reviews"]
            # the dealer page carries the rating/review count even when the
            # directory capture does not include this dealer
            if page.get("rating") and not row.get("rating"):
                row["rating"] = page["rating"]
            if page.get("review_count") and not row.get("review_count"):
                row["review_count"] = page["review_count"]
            if page.get("phones"):
                row["phones"] = {**(row.get("phones") or {}), **page["phones"]}
            if page.get("awards") and not row.get("awards"):
                row["awards"] = page["awards"]
        rp = review_pages.get(row.get("slug")) or review_pages_by_name.get(name)
        if rp and rp.get("reviews"):
            row["reviews"] = rp["reviews"]
        if name in makes_by_seller:
            row["makes_carried"] = sorted(makes_by_seller[name])
            row["primary_make"] = sorted(makes_by_seller[name])[0]
        for k, v in seller_facts.get(name, {}).items():
            if v is not None and not row.get(k):
                row[k] = v
        out.append(row)
    return out


def build_models():
    raw = load("research_raw.json", {"models": []})
    out = []
    for m in raw.get("models", []):
        if not m.get("year") or not m.get("trims"):
            # still keep pages that parsed the title only
            if not m.get("title_text"):
                continue
            mm = re.match(r"(\d{4}) ([A-Za-z ]+) ([A-Za-z0-9 -]+)", m["title_text"])
            if not mm:
                continue
            m["year"], m["make"], m["model"] = int(mm.group(1)), mm.group(2).strip(), mm.group(3).strip()
        if not m.get("make"):
            mm = re.match(r"(\d{4}) ([A-Za-z ]+) ([A-Za-z0-9 -]+)", m.get("title_text") or "")
            if mm:
                m["year"], m["make"], m["model"] = int(mm.group(1)), mm.group(2).strip(), mm.group(3).strip()
        m["slug"] = f"{slugify(m.get('make'))}-{slugify(m.get('model'))}-{m['year']}"
        m["model_slug"] = f"{slugify(m.get('make'))}-{slugify(m.get('model'))}"
        out.append(m)
    return out


def build_compares():
    raw = load("research_raw.json", {"compares": []})
    out = []
    for c in raw.get("compares", []):
        cols = [x for x in (c.get("columns") or [])
                if "vs." not in (x.get("name") or "") and "Add new car" not in (x.get("name") or "")]
        if len(cols) < 2 or not c.get("rows"):
            continue
        c["columns"] = cols[:2]
        out.append(c)
    return out


def build_valuation():
    raw = load("offers_raw.json", {"vehicles": [], "wizard": {}})
    return raw


def build_benchmark_users():
    """The authored benchmark fixtures (documented in provenance.json)."""
    return {
        "users": [
            {"email": "alice.j@test.com", "display": "Alice Johnson",
             "saved_cars": ["__derived__"], "saved_searches": "__derived__"},
            {"email": "bob.c@test.com", "display": "Bob Chen",
             "saved_cars": ["__derived__"], "saved_searches": "__derived__"},
            {"email": "carol.d@test.com", "display": "Carol Davis",
             "saved_cars": ["__derived__"], "saved_searches": "__derived__"},
            {"email": "dana.k@test.com", "display": "Dana Kim",
             "saved_cars": ["__derived__"], "saved_searches": "__derived__"},
        ]
    }


def main():
    os.makedirs(SRC, exist_ok=True)
    listings = build_listings()
    with open(os.path.join(SRC, "listings.json"), "w") as f:
        json.dump(listings, f, indent=1)
    dealers = build_dealers(listings)
    with open(os.path.join(SRC, "dealers.json"), "w") as f:
        json.dump(dealers, f, indent=1)
    models = build_models()
    with open(os.path.join(SRC, "models.json"), "w") as f:
        json.dump(models, f, indent=1)
    compares = build_compares()
    with open(os.path.join(SRC, "compares.json"), "w") as f:
        json.dump(compares, f, indent=1)
    valuation = build_valuation()
    with open(os.path.join(SRC, "valuation.json"), "w") as f:
        json.dump(valuation, f, indent=1)
    with open(os.path.join(SRC, "benchmark_users.json"), "w") as f:
        json.dump(build_benchmark_users(), f, indent=1)
    detail = sum(1 for l in listings if l.get("has_detail"))
    print(f"[build_source_data] listings={len(listings)} (detail={detail}) "
          f"dealers={len(dealers)} models={len(models)} "
          f"compares={len(compares)} valuation_vehicles={len(valuation.get('vehicles', []))}")


if __name__ == "__main__":
    main()
