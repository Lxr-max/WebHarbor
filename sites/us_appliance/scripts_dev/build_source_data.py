#!/usr/bin/env python3
"""Normalize scraped_data/ into the frozen source_data_*.json snapshots.

Reads:
  scraped_data/catalog/*.json            - GraphQL product pages + category tree
  scraped_data/pages/*.html              - content pages captured verbatim
  scraped_data/pages/shopperapproved_*.js - merchant review widget payloads

Writes (site root):
  source_data_products.json     - full catalog (6k+ products, real prices/specs)
  source_data_categories.json   - category tree + landing-page tiles + nav
  source_data_brands.json       - brands (ids, landing paths, logo strip, rebates)
  source_data_content.json      - support pages content (faq, delivery, finance,
                                  reviews, guides, carriers, home tiles, ...)
  source_data_images.json       - manifest of every upstream image to download

Everything in the output files is upstream-derived; mirror-native fixtures
(benchmark users/orders) are built by seed_data.py, not here.
"""
from __future__ import annotations

import html as htmllib
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent.parent
SCRAPE = HERE / "scraped_data"
CAT = SCRAPE / "catalog"
PAGES = SCRAPE / "pages"

UA_TAG = "captured 2026-09-28/29 from https://www.us-appliance.com/"

# custom fields that are meaningful on the storefront; the rest (pageviews,
# revenue, ATC-*, discount codes) are internal merchandising fields.
KEEP_CUSTOM_FIELDS = {
    "color", "free-standard-shipping", "promo-message", "promo-message-under-image",
    "energy-guide-label", "quickship", "stock-message", "install",
    "pdf-1-name", "pdf-1-link", "pdf-2-name", "pdf-2-link",
    "color-options", "zip-code-availability", "badge", "buy-now", "pageviews",
}


def read(p):
    return p.read_text(encoding="utf-8", errors="replace")


def strip_tags(seg):
    seg = re.sub(r"<script.*?</script>", " ", seg, flags=re.S)
    seg = re.sub(r"<style.*?</style>", " ", seg, flags=re.S)
    seg = re.sub(r"<br\s*/?>", "\n", seg)
    seg = re.sub(r"</(p|h\d|li|div|tr)>", "\n", seg)
    seg = re.sub(r"<[^>]+>", " ", seg)
    seg = htmllib.unescape(seg)
    seg = re.sub(r"[ \t]+", " ", seg)
    return re.sub(r"\n\s*\n+", "\n", seg).strip()


def text_of_match(pattern, html, group=1, flags=0):
    m = re.search(pattern, html, flags)
    return m.group(group) if m else ""


# ---------------------------------------------------------------- products --
def build_products():
    products = []
    for path in sorted(CAT.glob("page_*.json")):
        conn = json.loads(read(path))
        for edge in conn["edges"]:
            n = edge["node"]
            brand = (n.get("brand") or {}).get("name") or ""
            prices = n.get("prices") or {}
            price = ((prices.get("price") or {}).get("value"))
            retail = ((prices.get("retailPrice") or {}).get("value"))
            cf = {}
            for cedge in n.get("customFields", {}).get("edges", []):
                c = cedge["node"]
                if c["name"] in KEEP_CUSTOM_FIELDS and c["name"] not in cf:
                    cf[c["name"]] = c["value"]
            images = []
            for iedge in n.get("images", {}).get("edges", []):
                im = iedge["node"]
                images.append({"url": im["url"], "alt": im.get("altText") or "",
                               "default": bool(im.get("isDefault"))})
            cats = [{"id": c["node"]["entityId"], "name": c["node"]["name"],
                     "path": c["node"]["path"]}
                    for c in n.get("categories", {}).get("edges", [])]
            related = [{"id": r["node"]["entityId"], "name": r["node"]["name"],
                        "path": r["node"]["path"]}
                       for r in n.get("relatedProducts", {}).get("edges", [])]
            reviews = n.get("reviewSummary") or {}
            products.append({
                "id": n["entityId"],
                "name": n["name"],
                "slug": n["path"].strip("/").replace(".html", ""),
                "sku": n.get("sku") or "",
                "mpn": n.get("mpn") or "",
                "brand": brand,
                "price": price,
                "retail_price": retail,
                "availability": (n.get("availabilityV2") or {}).get("status", ""),
                "in_stock": bool((n.get("inventory") or {}).get("isInStock")),
                "description": n.get("description") or "",
                "blurb": (n.get("plainTextDescription") or "")[:400],
                "width": ((n.get("width") or {}).get("value")),
                "height": ((n.get("height") or {}).get("value")),
                "depth": ((n.get("depth") or {}).get("value")),
                "weight": ((n.get("weight") or {}).get("value")),
                "custom": cf,
                "review_count": reviews.get("numberOfReviews") or 0,
                "rating_sum": reviews.get("summationOfRatings") or 0,
                "images": images,
                "categories": cats,
                "related": related,
            })
    return products


# ------------------------------------------------------------- category nav --
def build_categories():
    tree = json.loads(read(CAT / "category_tree.json"))

    def clean(node, parent_id=None):
        return {
            "id": node["entityId"],
            "name": node["name"],
            "path": node["path"].strip("/").replace(".html", ""),
            "parent": parent_id,
            "children": [clean(c, node["entityId"]) for c in node.get("children", [])],
        }
    tree_out = [clean(n) for n in tree]

    # landing-page tiles ("Shop by ...") scraped from each captured landing
    tiles = {}
    for path in sorted(PAGES.glob("*.html")):
        slug = path.stem
        html = read(path)
        seg = html[html.find("<body"):]
        seg_t = re.sub(r"<script.*?</script>", " ", seg, flags=re.S)
        groups = []
        for gm in re.finditer(
                r'<h2[^>]*>\s*(Shop by[^<]{2,60}|Shop [A-Z][^<]{2,40})\s*</h2>(.*?)(?=<h2|<footer|</section>|<div class="page-content|Sign up for deals)',
                seg_t, re.S):
            block = gm.group(2)
            items = []
            for m in re.finditer(
                    r'<a href="([^"]+)">\s*<div class="ysw-c-slide__img">\s*'
                    r'<img src="([^"]+)" alt="([^"]*)"\s*>.*?'
                    r'<span class="ysw-c-slide__title">([^<]+)</span>', block, re.S):
                items.append({"href": m.group(1), "img": m.group(2),
                              "alt": m.group(3), "title": m.group(4).strip()})
            if items:
                groups.append({"heading": gm.group(1).strip(), "items": items})
        if groups:
            tiles[slug] = groups
    return tree_out, tiles


# ------------------------------------------------------------------ brands --
def build_brands(products, categories):
    # brand list from the advanced-search dropdown (id -> name)
    search_html = read(PAGES / "search-ranges.html")
    opts = re.findall(r'<option value="(\d+)"\s*>([^<]+)</option>',
                      search_html)
    form_brands = {int(i): n.strip() for i, n in opts}

    # rebates by brand
    rebates_html = read(PAGES / "rebates.html")
    i = rebates_html.find("const brands = [")
    blob = rebates_html[i + len("const brands = "):]
    depth = 0
    end = 0
    for k, ch in enumerate(blob):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = k + 1
                break
    blob = blob[:end]
    blob = re.sub(r",(\s*[}\]])", r"\1", blob)
    blob = re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)", r'\1"\2"\3', blob)
    rebate_data = json.loads(blob)

    # landing page per brand: category-tree brand categories
    brand_pages = {}
    for cat in categories:
        for child in cat.get("children", []):
            if child["name"].lower().endswith(("appliances", "refrigerators",
                                                "undercounter", "hoods",
                                                "grills", "laundry")):
                first = child["name"].split()[0]
                brand_pages.setdefault(child["name"], {})["path"] = child["path"]
                brand_pages.setdefault(child["name"], {})["id"] = child["id"]

    # homepage logo strip
    home_html = read(PAGES / "home.html")
    strip = re.findall(
        r'src="(https://cdn11\.bigcommerce\.com/[^"]*image-manager/[^"]+)"[^>]*alt="([^"]*)"',
        home_html)

    # products give brand->count
    counts = {}
    slugs = {}
    for p in products:
        if p["brand"]:
            counts[p["brand"]] = counts.get(p["brand"], 0) + 1

    brands = []
    for bid, name in sorted(form_brands.items(), key=lambda kv: kv[1].lower()):
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        brands.append({"id": bid, "name": name, "slug": slug,
                       "product_count": counts.get(name, 0)})
    return {"list": brands, "rebates": rebate_data, "logo_strip": strip}


# ----------------------------------------------------------------- content --
def build_content():
    content = {}

    # ---- FAQ
    faq_html = read(PAGES / "faq.html")
    faq_body = faq_html[faq_html.find('page-content page-content--full'):]
    faqs = []
    for m in re.finditer(r"<h2>([^<]+)</h2>(.*?)(?=<h2>|</p>\s*<div|</div>)",
                         faq_body, re.S):
        q = m.group(1).strip()
        a_html = m.group(2)
        a = re.sub(r"<[^>]+>", " ", a_html)
        a = htmllib.unescape(re.sub(r"\s+", " ", a)).strip()
        # links inside answers
        links = re.findall(r'href="([^"]+)"[^>]*>([^<]+)<', a_html)
        faqs.append({"q": q, "a": a, "links": [{"href": l, "text": t.strip()} for l, t in links]})
    content["faq"] = faqs

    # ---- delivery page (structured blocks)
    dl_html = read(PAGES / "freedelivery.html")
    content["delivery"] = {
        "hero_title": "Nationwide Delivery",
        "hero_line": "Free Delivery on Orders Over $999",
        "hero_sub": ("Nationwide curbside delivery included — no matter how "
                     "many appliances you order."),
        "how_it_works": [
            ("Select Your Appliances", "Browse online or call our experts for personalized advice"),
            ("Place Your Order", "Safe, secure checkout with flexible financing options"),
            ("Get Tracking Info", "Receive updates as your order is dispatched and en route"),
            ("Schedule Delivery", "Our freight carrier contacts you to arrange a convenient time"),
        ],
        "options": [
            {"name": "Standard Delivery", "tag": "Most Popular", "price": "FREE",
             "blurb": ("On all major appliance orders over $999. Only $99 on "
                       "orders under $999. If one item qualifies for free "
                       "shipping, your entire order ships free."),
             "bullets": ["Curbside / driveway drop-off",
                         "Carrier schedules a delivery window with you",
                         "Tracking info provided after shipment",
                         "Signature required on delivery"]},
            {"name": "In-Home Delivery", "tag": "Premium", "price": "$199 / order",
             "blurb": ("Your appliances are brought inside and placed in an "
                       "accessible room of your choice — up to one flight of stairs."),
             "bullets": ["Unboxing & packaging removal included",
                         "Room placement up to 1 flight of stairs",
                         "Old unit haul-away available — call for details",
                         "Select at checkout"]},
        ],
        "small_rates": [
            ("Microwave ovens", "$99 flat / order (unlimited items)"),
            ("Accessories & cookware", "$9 / order"),
            ("Items under 5 lbs", "$5.99 / order"),
        ],
        "times": [("Major Appliances", "1–3 weeks",
                   "Freight carrier will contact you to schedule"),
                  ("Accessories & Small Items", "1–2 weeks",
                   "Shipped via UPS / FedEx with tracking")],
        "extra_charges": ["Pro-style or 400+ lb appliances",
                          "Appliance doesn't fit through door",
                          "Remote area deliveries", "Ferry deliveries",
                          "Bulk orders", "Post-shipment address changes",
                          "Select area zip codes"],
    }

    # ---- order tracking carriers
    ot_html = read(PAGES / "ordertracking.html")
    ot_body = ot_html[ot_html.find("<body"):]
    ot_body = re.sub(r"<script.*?</script>", " ", ot_body, flags=re.S)
    seg = ot_body[ot_body.find("Below you will find"):]
    seg_txt = strip_tags(seg)
    content["order_tracking_intro"] = ("Below you will find links to our Shipping "
                                       "partners that will allow you to track your "
                                       "shipment. Please note that it may take "
                                       "24-48 hours for the shipping company to "
                                       "post the tracking information in their "
                                       "systems.")
    content["carriers"] = [
        {"name": "R+L Carriers", "field": "Pro #", "phone": "1-800-543-5589"},
        {"name": "Maersk", "field": "tracking number", "phone": "1-800-447-4568"},
        {"name": "Valley Companies", "field": "tracking number", "phone": ""},
        {"name": "FedEx", "field": "tracking number", "phone": "1-800-463-3339"},
    ]

    # ---- financing
    fo_html = read(PAGES / "financeoffers.html")
    content["finance_offers"] = [
        {"name": "Special Finance Offer",
         "headline": "0% Interest If Paid In Full In 15 Months",
         "terms": ("On purchases of qualifying appliances with your US "
                   "Appliance credit card. Interest will be charged to your "
                   "account from the purchase date if the promotional purchase "
                   "is not paid in full within 15 months. Minimum monthly "
                   "payments required."),
         "brands": ["Bosch", "GE", "Cafe", "Frigidaire", "Electrolux",
                    "KitchenAid", "Whirlpool", "Maytag"]},
        {"name": "Storewide Special Finance Offer",
         "headline": "0% Interest If Paid In Full In 6 Months Storewide",
         "terms": ("On purchases of $200 or more with your US Appliance "
                   "credit card. Interest will be charged to your account "
                   "from the purchase date if the promotional purchase is not "
                   "paid in full within 6 months. Minimum monthly payments "
                   "required."),
         "brands": ["All Brands Storewide"]},
    ]
    content["finance_steps"] = [
        ("1. Apply Now", "Click Apply Now and get a decision in minutes."),
        ("2. Approval", "Once approved you will receive an Account Number"),
        ("3. Call to Order", "Call 877-628-9913 to place your order"),
    ]
    fc_html = read(PAGES / "financecenter.html")
    fc_body = fc_html[fc_body.find("<body") if False else 0:]
    m = re.search(r"<p>(Finance your next appliance purchase[^<]+)</p>", fc_html)
    content["finance_center_intro"] = (m.group(1) if m else
        "Finance your next appliance purchase with special financing promotions "
        "from leading brands, 6 month special financing site wide, or the no "
        "credit needed leasing option.")

    # ---- customer service hub (nav sections from cusser.html)
    cs_html = read(PAGES / "cusser.html")
    cs_body = cs_html[cs_html.find("<body"):]
    cs_body = re.sub(r"<script.*?</script>", " ", cs_body, flags=re.S)
    hub = []
    for hm in re.finditer(
            r'<h2 class="eyTwo">([^<]+)</h2>(.*?)(?=<h2 class="eyTwo"|</td>|</tbody>)',
            cs_body, re.S):
        section = hm.group(1).strip()
        items = re.findall(r'href="([^"]+)"[^>]*>(?:<span[^>]*>)?([^<]+)', hm.group(2))
        seen = set()
        clean = []
        for href, text in items:
            text = text.strip()
            if not text or (href, text) in seen:
                continue
            seen.add((href, text))
            # map upstream urls to mirror routes
            path = href.replace("https://www.us-appliance.com", "") \
                      .replace("http://www.us-appliance.com", "")
            clean.append({"href": path, "text": text})
        if clean:
            hub.append({"section": section, "items": clean})
    content["customer_service_hub"] = hub

    # ---- contact
    content["contact"] = {
        "sales": {"hours": "Monday - Friday: 8am - 6pm EST.",
                  "phone": "Call 877-628-9913 (toll-free)"},
        "service": {"hours": "Monday - Friday: 9am - 6pm EST.",
                    "phone": "Call 877-628-9913 (toll-free)"},
        "address": ["US Appliance", "111 Corporate Drive", "Auburn Hills, MI 48326"],
        "fax": "(248) 364-0701 fax",
    }

    # ---- testimonials (ShopperApproved merchant reviews)
    reviews = []
    for p in (1, 2, 3):
        f = PAGES / f"shopperapproved_p{p}.js"
        if not f.exists():
            continue
        js = read(f)
        i = js.find("tempReviews=")
        if i < 0:
            continue
        blob = js[i + len("tempReviews="):]
        depth = 0
        end = 0
        in_str = False
        esc = False
        for k, ch in enumerate(blob):
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = k + 1
                    break
        blob = blob[:end].replace("!0", "true").replace("!1", "false")
        data = json.loads(blob)
        for r in data["reviews"]["data"]:
            reviews.append({
                "id": r["FeedbackId"],
                "name": r.get("DisplayName") or "Anonymous",
                "date": r.get("ReviewDate") or "",
                "rating": float(r.get("Overall") or 0),
                "comments": r.get("Comments") or "",
                "verified": bool(r.get("VerifiedReview")),
                "customer_service": r.get("CustomerService"),
                "delivery": r.get("Delivery"),
                "price": r.get("Price"),
                "product": r.get("Product"),
            })
    content["reviews"] = reviews
    content["reviews_meta"] = {"total": 20841, "site_rating": 4.9,
                               "pct_4_or_5": "97%"}

    # ---- buying guides
    guides = []
    guide_map = {
        "guide-refrigerator": "Refrigerator Buying Guide",
        "guide-range": "Range Buying Guide",
        "guide-dishwasher": "Dishwasher Buying Guide",
        "guide_wallovon": "Wall Oven Buying Guide",
        "guide_cooktop": "Cooktop Buying Guide",
        "guide_microwave": "Microwave Buying Guide",
        "guide_washer": "Washer Buying Guide",
        "guide_dryer": "Dryer Buying Guide",
        "guide_venthood": "Vent Hood Buying Guide",
    }
    for stem, title in guide_map.items():
        f = PAGES / f"{stem}.html"
        if not f.exists():
            continue
        ghtml = read(f)
        gbody = ghtml[ghtml.find("<body"):]
        gbody = re.sub(r"<script.*?</script>", " ", gbody, flags=re.S)
        gbody = re.sub(r"<style.*?</style>", " ", gbody, flags=re.S)
        m = re.search(r"<h1[^>]*>([^<]+)</h1>", gbody)
        i = gbody.find("<h1")
        seg = gbody[i:i + 30000]
        seg = re.sub(r"<(h2)[^>]*>", "\n## ", seg)
        seg = re.sub(r"</h2>", "\n", seg)
        text = strip_tags(seg)
        guides.append({"slug": stem.split("-")[-1].split("_")[-1] if "_" not in stem else stem.split("_")[-1],
                       "title": title, "text": text[:9000]})
    content["buying_guides"] = guides
    content["buying_guides_intro"] = (
        "Our quick read appliance buying guides help you make smart decisions "
        "for your home. Stop guessing and start shopping with confidence. From "
        "refrigerators and washing machines to ovens and dishwashers, get "
        "expert advice and know what to look for when selecting an appliance "
        "to perfectly fit your needs.")

    # ---- homepage
    home_html = read(PAGES / "home.html")
    hbody = home_html[home_html.find("<body"):]
    hbody = re.sub(r"<script.*?</script>", " ", hbody, flags=re.S)
    hbody = re.sub(r"<style.*?</style>", " ", hbody, flags=re.S)
    # brand names from the advanced-search dropdown resolve logo -> brand slug
    search_html2 = read(PAGES / "search-ranges.html")
    form_names = {oname.strip().lower(): oname.strip()
                  for _oid, oname in re.findall(
                          r'<option value="(\d+)"\s*>([^<]+)</option>',
                          search_html2)}
    logo_files = [
        ("LG", "lglogohome.png"), ("GE", "gelogohome.png"),
        ("KitchenAid", "kitchenaidlogohome.png"),
        ("Frigidaire", "frigidarielogohome.png"), ("Cafe", "cafeapplogo.png"),
        ("U-Line", "ulinelogo.png"), ("Miele", "mielelogohmbg.png"),
        ("Viking", "vikinglogohome.png"), ("Whirlpool", "whirllogohome.png"),
    ]
    def brand_slug(label):
        special = {"GE": "General Electric", "Cafe": "Cafe",
                   "U-Line": "U-Line"}
        target = form_names.get(special.get(label, label).lower(), label)
        return re.sub(r"[^a-z0-9]+", "-", target.lower()).strip("-")
    logo_strip = [{"label": label, "slug": brand_slug(label), "file": fname}
                  for label, fname in logo_files]
    cat_tiles = []
    for m in re.finditer(
            r'<a href="([^"]+)"><img class="zn-nodrag" src="([^"]+)" alt="([^"]*)"',
            hbody):
        cat_tiles.append({"href": m.group(1), "img": m.group(2), "alt": m.group(3)})
    hero = re.search(
        r'<p class="_heading"[^>]*>([^<]+)</p>.*?<div class="_description"[^>]*><p>([^<]+)</p>.*?'
        r'href="([^"]+)"[^>]*class="button[^"]*"[^>]*>([^<]+)</a>',
        hbody, re.S)
    promos = re.findall(
        r'href="(https://www\.us-appliance\.com/[^"]+)"[^>]*>\s*<img[^>]*src="(https://media\.zenobuilder\.com/[^"]+)"[^>]*alt="([^"]*)"',
        hbody)
    content["home"] = {
        "hero": {"img": "https://cdn11.bigcommerce.com/s-ad6dymslsc/images/stencil/original/image-manager/leave-background.jpg?t=1789643203",
                 "heading": hero.group(1) if hero else "Huge Fall Savings",
                 "description": hero.group(2) if hero else "Big Savings on Major Appliances!",
                 "button_text": hero.group(4).strip() if hero else "SHOP DEALS",
                 "button_href": hero.group(3) if hero else "/hugepricecuts.html"},
        "category_tiles": cat_tiles,
        "promo_banners": [{"href": h, "img": i, "alt": a} for h, i, a in promos],
        "logo_strip": logo_strip,
        "order_confidence": {"heading": "Order With Confidence",
                             "line": "Real talk from real people",
                             "button": "Read Reviews",
                             "href": "/testimonials.html"},
    }

    # ---- deals page
    hp_html = read(PAGES / "hugepricecuts.html")
    content["deals"] = {
        "heading": "Huge Fall Sale!",
        "blurb": "Look for lower prices in cart on select items",
        "note": ("Manufacturer rules prevent us from showing the lowest prices "
                 "until item is in cart. Add select items to cart to see your "
                 "exclusive discount"),
        "featured_brands": ["LG", "Frigidaire", "GE", "KitchenAid"],
        "category_links": [
            ("French Door Refrigerators", "/frdore.html?query=c232&on_sale=1"),
            ("Side by Side Refrigerators", "/sidebyside.html?query=c251&on_sale=1"),
            ("Gas Ranges", "/gas-ranges.html?query=c407&on_sale=1"),
            ("Electric Ranges", "/electric-ranges.html?query=c380&on_sale=1"),
            ("Appliance Packages", "/appliance-packages.html?query=c34&on_sale=1"),
            ("Dishwashers", "/dishwasher.html?query=c172&on_sale=1"),
            ("Front Load Washers", "/front-load.html?query=c493&on_sale=1"),
            ("Top Load Washers", "/top-load.html?query=c505&on_sale=1"),
            ("Electric Cooktops", "/electric-cooktops.html?query=c295&on_sale=1"),
            ("Gas Cooktops", "/gas-cooktops.html?query=c308&on_sale=1"),
        ],
    }

    # ---- static page bodies (return policy, why us, warranty, clearance)
    def page_text(name, limit=8000):
        try:
            t = read(PAGES / f"{name}.html")
        except FileNotFoundError:
            return ""
        b = t[t.find("<body"):]
        b = re.sub(r"<script.*?</script>", " ", b, flags=re.S)
        b = re.sub(r"<style.*?</style>", " ", b, flags=re.S)
        i = b.find("<h1")
        if i < 0:
            return ""
        return strip_tags(b[i:i + 40000])[:limit]

    content["returns_text"] = page_text("returninformation")
    content["why_us_text"] = page_text("whyusappliance")
    content["warranty_text"] = page_text("warrantyoptions")
    content["clearance_text"] = page_text("clearance")
    content["salestax_text"] = page_text("salestaxinfo")
    content["instock_text"] = page_text("instock")

    # ---- search content-tab calibration (news & information results)
    sc_html = read(PAGES / "search-content-ranges.html")
    sc_body = sc_html[sc_html.find("<body"):]
    sc_body = re.sub(r"<script.*?</script>", " ", sc_body, flags=re.S)
    articles = re.findall(
        r'href="(https://www\.us-appliance\.com/[^"]+\.html)"[^>]*class="listItem-title[^"]*"[^>]*>\s*([^<]+)<',
        sc_body)
    content["content_results_ranges"] = [{"href": h, "title": t.strip()}
                                         for h, t in articles]

    # ---- misc real strings
    content["site_facts"] = {
        "phone": "877-628-9913",
        "address": "111 Corporate Drive, Auburn Hills, MI 48326",
        "founded": "Founded in 1963 and online since 1999",
        "hours": "Monday - Friday: 8am - 6pm EST.",
        "free_shipping_threshold": 999,
        "under_threshold_shipping": 99,
        "in_home_delivery": 199,
        "price_match": ("If you find a better price at another legitimate "
                        "authorized retailer, we will not only match the price "
                        "but we'll match 110% of the difference!"),
        "cancel_window": ("Orders can be canceled within 48 hours of placing "
                          "the order without any fee as long as the order has "
                          "not shipped."),
    }
    return content


# ------------------------------------------------------------------ images --
def to_320w(url):
    """Map a stencil CDN url to its 320w variant (an upstream-served size)."""
    return re.sub(r"/stencil/[^/]+/", "/stencil/320w/", url)


def assign_local_images(products, content):
    """Assign local static/images paths to every product / tile / banner.

    Returns the download manifest [{path, source_url}] and, as a side effect,
    annotates:
      products:  card_image, gallery (local paths)
      content["_landing_tiles"][slug][g]["items"][i]["img_local"]
      content["home"]["category_tiles"][i]["img_local"] etc.
    """
    jobs = {}          # local path -> source url
    url_index = {}     # source url -> local path (dedupe identical upstream files)

    def add(local, url):
        if not url:
            return ""
        if url in url_index:
            return url_index[url]
        if local not in jobs:
            jobs[local] = url
            url_index[url] = local
            return local
        n = 1
        while f"{local[:-4]}_{n}{local[-4:]}" in jobs:
            n += 1
        local2 = f"{local[:-4]}_{n}{local[-4:]}"
        jobs[local2] = url
        url_index[url] = local2
        return local2

    def ext_of(url):
        return ".png" if ".png" in url else ".jpg"

    # products: card (default image) + gallery extras at upstream 320w
    for p in products:
        pid = p["id"]
        default_idx = 0
        for i, im in enumerate(p["images"]):
            if im["default"]:
                default_idx = i
        if p["images"]:
            im = p["images"][default_idx]
            p["card_image"] = add(f"products/{pid}_card{ext_of(im['url'])}",
                                  to_320w(im["url"]))
        else:
            p["card_image"] = ""
        gallery = []
        if p["availability"] == "Available":
            g = 0
            for i, im in enumerate(p["images"]):
                if i == default_idx:
                    continue
                if g >= 2:
                    break
                local = add(f"products/{pid}_g{g}{ext_of(im['url'])}",
                            to_320w(im["url"]))
                if local:
                    gallery.append(local)
                g += 1
        p["gallery"] = gallery

    # landing tiles from every captured category page
    tiles = content.get("_landing_tiles") or {}
    for slug, groups in tiles.items():
        n = 0
        for grp in groups:
            for item in grp["items"]:
                url = item["img"]
                item["img_local"] = add(
                    f"category_tiles/{slug}_{n}{ext_of(url)}", url)
                n += 1

    # homepage assets
    home = content["home"]
    home["hero"]["img_local"] = add("home/hero.jpg", home["hero"]["img"])
    n = 0
    for tile in home["category_tiles"]:
        tile["img_local"] = add(f"home/tile_{n}{ext_of(tile['img'])}",
                                tile["img"])
        n += 1
    for logo in home["logo_strip"]:
        add(f"home/logo_{logo['label'].lower().replace('-', '')}.png",
            f"https://cdn11.bigcommerce.com/s-ad6dymslsc/images/stencil/original/image-manager/{logo['file'].split('?')[0]}")
    n = 0
    for promo in home["promo_banners"]:
        promo["img_local"] = add(f"home/promo_{n}{ext_of(promo['img'])}",
                                 promo["img"])
        n += 1
    add("site/logo.png",
        "https://cdn11.bigcommerce.com/s-ad6dymslsc/images/stencil/295x60/us_appliance_logo492tr_1775129438__08136.original.png")
    add("home/reviews.png",
        "https://cdn11.bigcommerce.com/s-ad6dymslsc/images/stencil/original/image-manager/reviewsumsha.png")

    return [{"path": k, "source_url": v} for k, v in sorted(jobs.items())]


def main():
    products = build_products()
    print("products:", len(products))
    categories, landing_tiles = build_categories()
    print("categories:", len(categories))
    brands = build_brands(products, categories)
    content = build_content()
    content["_landing_tiles"] = landing_tiles

    images = assign_local_images(products, content)
    (HERE / "source_data_products.json").write_text(
        json.dumps(products, ensure_ascii=False), encoding="utf-8")
    (HERE / "source_data_categories.json").write_text(
        json.dumps({"tree": categories, "landing_tiles": landing_tiles},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    (HERE / "source_data_brands.json").write_text(
        json.dumps(brands, ensure_ascii=False, indent=1), encoding="utf-8")
    (HERE / "source_data_content.json").write_text(
        json.dumps(content, ensure_ascii=False, indent=1), encoding="utf-8")
    (HERE / "source_data_images.json").write_text(
        json.dumps(images, ensure_ascii=False, indent=1), encoding="utf-8")
    print("images to download:", len(images))

    # per-brand product counts for a sanity print
    counts = {}
    for p in products:
        counts[p["brand"]] = counts.get(p["brand"], 0) + 1
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:12]
    print("top brands:", top)
    avail = sum(1 for p in products if p["availability"] == "Available")
    print("available:", avail, "of", len(products))


if __name__ == "__main__":
    main()
