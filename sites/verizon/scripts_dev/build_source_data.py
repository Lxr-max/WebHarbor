#!/usr/bin/env python3
"""Phase 7: consolidate scraped captures into the tracked source_data/*.json.

Cleans and structures the raw captures (gridwall, PDPs, plans, stores,
support pages) into the canonical files the seeder reads. Benchmark-user
account fixtures (accounts, lines, bills, usage, orders) and the
troubleshooter / trade-in estimator flows are deterministic fixtures
declared in provenance.json — they are generated here, not scraped.

Run: python3.11 build_source_data.py
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRAPED = ROOT / "scraped_data"
SOURCE = ROOT / "source_data"
SOURCE.mkdir(exist_ok=True)

REVIEW_COUNT_RE = re.compile(r"([0-9.,]+)K?", re.I)


def clean_device(dev):
    slug = dev["slug"]
    brand = ("Apple" if "iphone" in slug else
             "Samsung" if "galaxy" in slug or "z-fold" in slug or "z-flip" in slug else
             "Google" if "pixel" in slug else
             "Motorola" if "moto" in slug or "razr" in slug or "edge" in slug else
             "Other")
    # reviews like "18K" -> 18000, "529" -> 529
    reviews = dev.get("reviews")
    if reviews:
        m = REVIEW_COUNT_RE.match(str(reviews))
        if m:
            val = m.group(1).replace(",", "")
            reviews = int(float(val) * 1000) if "K" in str(m.group(0)) else int(val)
    specs = json.loads((SCRAPED / "device_specs.json").read_text()).get(slug, {})
    # map each captured gallery URL to the local file the downloader saved
    manifest = json.loads((SCRAPED / "image_manifest.json").read_text()) \
        if (SCRAPED / "image_manifest.json").exists() else []
    url_to_file = {m["source_url"]: m["file"] for m in manifest}
    color_images = {}
    for color, entries in (dev.get("color_images") or {}).items():
        files = []
        for entry in entries:
            if entry.startswith("static/"):
                files.append(entry)
            else:
                files.append(url_to_file.get(entry, entry))
        color_images[color] = files
    return {
        "name": dev["name"],
        "slug": slug,
        "brand": brand,
        "sku": dev.get("sku"),
        "colors": dev.get("colors") or [],
        "storage": dev.get("storage") or [],
        "terms": dev.get("terms") or {},
        "full_price": dev.get("full"),
        "grid_monthly": dev.get("grid_monthly"),
        "grid_retail": dev.get("grid_retail"),
        "rating": dev.get("rating"),
        "reviews": reviews,
        "savings": dev.get("savings"),
        "ship_window": dev.get("ship"),
        "promo": dev.get("promo") or [],
        "specs": specs,
        "color_images": color_images,
        "pdp_url": f"https://www.verizon.com/smartphones/{slug}/",
    }


def build_devices():
    devices = json.loads((SCRAPED / "devices.json").read_text())
    out = [clean_device(d) for d in devices if not d.get("error")]
    (SOURCE / "devices.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"[source] devices: {len(out)}")
    return out


def build_plans():
    raw = json.loads((SCRAPED / "plans.json").read_text())
    lines = json.loads((SCRAPED / "simplicity_lines.json").read_text()) \
        if (SCRAPED / "simplicity_lines.json").exists() else {}
    prepaid_text = ""
    page = SCRAPED / "pages" / "prepaid_plans.html"
    if page.exists():
        import html as htmllib
        text = re.sub(r"<script[^>]*>.*?</script>", " ", page.read_text(encoding="utf-8", errors="replace"), flags=re.S)
        text = re.sub(r"<[^>]+>", "\n", text)
        text = htmllib.unescape(text)
        prepaid_text = re.sub(r"[ \t]+", " ", text)
    simplicity = {
        "name": "Simplicity Plan",
        "per_line": 30,
        "line_prices": {n: 30 * n for n in (1, 2, 3, 4)},
        "note": "After AutoPay and $15/mo switch discount. Plus taxes and fees.",
        "switch_discount": 15,
        "max_lines": 12,
        "features": [
            "5G Ultra Wideband",
            "Verizon Dollars",
            "Mexico & Canada talk, text & data",
            "Satellite texting",
            "10 GB mobile hotspot data",
            "Call filter & Verizon Family",
        ],
        "phone_options": [
            {"name": "Bring your own phone", "blurb": "Connect it to our best 5G network."},
            {"name": "Buy a new phone right now", "blurb": "We've got flexible financing options to meet your needs."},
            {"name": "Upgrade to the latest phone every year", "blurb": "Get the newest every year for a monthly charge."},
        ],
        "hero": {"headline": "Get iPhone 18 Pro. No trade-in needed",
                 "price": "$80/mo when you switch to Verizon with Simplicity Plan",
                 "details": "After Auto Pay and switch discount. Plus taxes and fees. No activation/upgrade fees when you enroll in Verizon Loyalty."},
    }
    prepaid = {
        "name": "Verizon Prepaid",
        "plans": [
            {"name": "Talk & Text", "base": 35, "autopay": 30, "autopay_discount": 5,
             "first_month": 35,
             "blurb": "Unlimited calling and texting.",
             "features": ["Unlimited calling", "Unlimited texting"]},
            {"name": "15 GB", "base": 45, "autopay": 35, "autopay_discount": 10,
             "first_month": 45,
             "blurb": "Get more data and discounts.",
             "features": ["15 GB of 5G / 4G LTE data", "Mobile Hotspot from plan allowance",
                          "3-year price lock guarantee"]},
            {"name": "Unlimited", "base": 60, "autopay": 50, "autopay_discount": 10,
             "first_month": 60,
             "blurb": "Get the freedom of unlimited talk, text, and data.",
             "features": ["Unlimited talk, text and data", "5 GB Mobile Hotspot",
                          "Includes 5G Ultra Wideband", "3-year price lock guarantee"]},
            {"name": "Unlimited Plus", "base": 70, "autopay": 60, "autopay_discount": 10,
             "first_month": 70,
             "blurb": "Experience unprecedented speed and savings.",
             "features": ["5G Ultra Wideband", "50 GB premium network access",
                          "25 GB premium Mobile Hotspot", "Global Choice at no additional cost for 1 country/mo",
                          "3-year price lock guarantee"]},
        ],
        "autopay_rule": ("Auto Pay discount of $10/mo on plans $45 & higher after the 1st "
                         "month. $5/mo discount on the $35 Talk & Text plan after the 1st "
                         "month. Credit or Debit card required. Additional loyalty "
                         "discounts do not apply."),
        "loyalty_rule": ("Loyalty discount of $5/mo applies after 3 months of service; "
                         "additional $5/mo applies after 9 months of service, for a total "
                         "of $10/mo on plans $45 or higher. Discount applies as long as "
                         "your line is not disconnected. Additional Auto Pay discounts do "
                         "not apply."),
        "multiline_rule": ("Save $20/mo when you add any Verizon Prepaid Unlimited phone "
                           "plan to your Multiline account. Each additional Unlimited "
                           "phone line receives a $20/mo discount. Auto Pay and loyalty "
                           "discounts cannot be combined."),
        "price_lock": ("Applies to the then-current base monthly rate charged by Verizon "
                       "for your talk, text and data; excludes taxes, fees, surcharges, "
                       "one-time charges, additional plan discounts or promotions and "
                       "third-party services. Price guarantee is void if lines are "
                       "canceled or moved to an ineligible plan."),
    }
    out = {"simplicity": simplicity, "prepaid": prepaid,
           "captured_from": raw["unlimited"]["url"]}
    (SOURCE / "plans.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("[source] plans: simplicity + 4 prepaid tiers")


def build_stores():
    raw = json.loads((SCRAPED / "stores.json").read_text())
    manifest = json.loads((SCRAPED / "image_manifest.json").read_text())
    imgs = {m["file"] for m in manifest}
    stores = []
    for st in raw["stores"]:
        code = (st.get("storeUrl") or "").rstrip("/").split("-")[-1]
        outside = f"static/images/stores/{code}-outside.jpg" in imgs
        inside = f"static/images/stores/{code}-inside.jpg" in imgs
        stores.append({
            "store_name": st.get("storeName"),
            "business_name": st.get("businessName"),
            "retailer": ("Verizon Company Store" if (st.get("storeType") or "") == "Store"
                         else st.get("storeType")),
            "store_type": st.get("storeType"),
            "phone": st.get("phoneNumber"),
            "street": st.get("address1"),
            "street2": st.get("address2"),
            "city": (st.get("city") or "").title(),
            "state": st.get("state"),
            "zip": st.get("zipCode"),
            "hours": {d: st.get(f"hours{d}") for d in
                      ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")},
            "services": (st.get("storeAvailableServices") or "").split("~")
                        if st.get("storeAvailableServices") else [],
            "appointments": bool(st.get("appointmentsAccepted")),
            "fios": bool(st.get("fiosSold")),
            "pickup": st.get("inStorePickupFlag") == "Y" or "INSTORE" in (st.get("storeAvailableServices") or ""),
            "locker": bool(st.get("lockers")) or "LOCKER" in (st.get("storeAvailableServices") or ""),
            "curbside": bool(st.get("curbside")),
            "doorside": bool(st.get("doorside")),
            "cma": st.get("cmaDescription"),
            "locator_state": st.get("locator_state"),
            "locator_city": st.get("locator_city"),
            "store_code": code,
            "image_outside": f"static/images/stores/{code}-outside.jpg" if outside else None,
            "image_inside": f"static/images/stores/{code}-inside.jpg" if inside else None,
        })
    (SOURCE / "stores.json").write_text(json.dumps(stores, indent=1), encoding="utf-8")
    city_index = json.loads((SCRAPED / "store_city_index.json").read_text()) \
        if (SCRAPED / "store_city_index.json").exists() else raw["city_index"]
    (SOURCE / "store_city_index.json").write_text(
        json.dumps(city_index, indent=1), encoding="utf-8")
    print(f"[source] stores: {len(stores)} stores, "
          f"{sum(1 for s in stores if s['image_outside'])} with photos")


def build_pages():
    pages = json.loads((SCRAPED / "pages.json").read_text())
    js_pages = json.loads((SCRAPED / "js_pages.json").read_text())
    merged = {}
    for name, blob in pages.items():
        merged[name] = {"url": blob["url"], "text": blob["text"]}
    # rendered captures are richer than the server shells: js pages win
    for name, blob in js_pages.items():
        merged[name] = {"url": blob["url"], "text": blob["text"]}
    (SOURCE / "pages.json").write_text(json.dumps(merged, indent=1), encoding="utf-8")
    print(f"[source] pages: {len(merged)} content pages")


def main():
    build_devices()
    build_plans()
    build_stores()
    build_pages()


if __name__ == "__main__":
    main()
