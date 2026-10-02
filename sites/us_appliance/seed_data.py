#!/usr/bin/env python3
"""Deterministic build-time seeder for the US Appliance mirror.

Reads the tracked source_data_*.json snapshots (captured from
www.us-appliance.com on 2026-09-28/29) and materializes the SQLite database.

Determinism notes: every table is inserted with SQLAlchemy Core
``insert()`` statements whose parameter lists are built in a fixed order from
the tracked snapshots, so the physical row order — and therefore the SQLite
file bytes — are identical on every build. The benchmark users use a frozen
SHA-256 password hash. Idempotent at the function level: every seed function
early-returns when its tables are already populated. Run with
PYTHONHASHSEED=0 during the image build.
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    with open(os.path.join(BASE_DIR, name), encoding="utf-8") as fh:
        return json.load(fh)


def _hash(password):
    import hashlib
    digest = hashlib.sha256()
    digest.update(f"webharbor-us_appliance:{password}".encode("utf-8"))
    return digest.hexdigest()


BENCHMARK_PASSWORD_HASH = _hash("TestPass123!")


# ---------------------------------------------------------------- catalog --
def build_seed(db):
    """Populate the catalog tables. Early-returns when already seeded."""
    from app import (Brand, BuyingGuide, Category, ContentBlock, FaqItem,
                     MerchantReview, Product, ProductRelated, Rebate)

    if Product.query.count() > 0:
        return

    products = _load("source_data_products.json")
    cats = _load("source_data_categories.json")
    brands = _load("source_data_brands.json")
    content = _load("source_data_content.json")

    # ---- categories (flatten the tree in fixed pre-order) ----
    cat_rows = []

    def walk(nodes, parent_id=None):
        pos = 0
        for n in nodes:
            cat_rows.append((n, parent_id, pos))
            pos += 1
            walk(n.get("children") or [], n["id"])

    walk(cats["tree"])

    brand_root_ids = set()
    for top in cats["tree"]:
        if top["name"] == "Shop By Brand":
            def collect_ids(n):
                brand_root_ids.add(n["id"])
                for c in n.get("children") or []:
                    collect_ids(c)
            collect_ids(top)

    tiles_by_slug = cats.get("landing_tiles") or {}
    category_rows = [
        {"id": n["id"], "name": n["name"], "slug": n["path"],
         "parent_id": parent_id,
         "is_brand": n["id"] in brand_root_ids,
         "position": pos,
         "blurb": "",
         "tile_groups": json.dumps(tiles_by_slug.get(n["path"]) or [],
                                   ensure_ascii=False)}
        for n, parent_id, pos in cat_rows
    ]
    category_rows.sort(key=lambda r: r["id"])
    db.session.execute(db.insert(Category), category_rows)

    # ---- brands ----
    db.session.execute(db.insert(Brand), [
        {"id": b["id"], "name": b["name"], "slug": b["slug"],
         "product_count": b.get("product_count", 0)}
        for b in brands["list"]
    ])

    # ---- products (list order = tracked capture order) ----
    product_rows = []
    for position, p in enumerate(products):
        cf = p.get("custom") or {}
        product_rows.append({
            "id": p["id"], "name": p["name"], "slug": p["slug"],
            "sku": p["sku"], "mpn": p["mpn"], "brand": p["brand"],
            "price": p["price"], "retail_price": p["retail_price"],
            "availability": p["availability"], "in_stock": p["in_stock"],
            "description": p["description"], "blurb": p["blurb"],
            "width": p["width"], "height": p["height"], "depth": p["depth"],
            "weight": p["weight"], "color": cf.get("color", ""),
            "promo_message": cf.get("promo-message", ""),
            "promo_under": cf.get("promo-message-under-image", ""),
            "badge": cf.get("badge", ""),
            "pdf_name": cf.get("pdf-1-name", ""),
            "pdf_link": cf.get("pdf-1-link", ""),
            "free_shipping": cf.get("free-standard-shipping") == "yes",
            "zip_availability": cf.get("zip-code-availability") == "yes",
            "pageviews": int(cf.get("pageviews") or 0),
            "review_count": p["review_count"], "rating_sum": p["rating_sum"],
            "card_image": p.get("card_image", ""),
            "gallery": json.dumps(p.get("gallery") or []),
            "color_options": json.dumps(
                (cf.get("color-options") or "").split()),
            "category_ids": json.dumps([c["id"] for c in p["categories"]]),
            "position": position,
        })
    # Insert in primary-key order so the b-tree fills deterministically.
    product_rows.sort(key=lambda r: r["id"])
    db.session.execute(db.insert(Product), product_rows)

    # ---- related products (frequently bought together) ----
    related_rows = []
    for p in products:
        for i, rel in enumerate(p.get("related") or []):
            related_rows.append({"product_id": p["id"], "related_id": rel["id"],
                                 "position": i})
    related_rows.sort(key=lambda r: (r["product_id"], r["position"]))
    db.session.execute(db.insert(ProductRelated), related_rows)

    # ---- merchant reviews (ShopperApproved capture) ----
    review_rows = [
        {"id": r["id"], "name": r["name"], "review_date": r["date"],
         "rating": r["rating"], "comments": r["comments"],
         "verified": r["verified"],
         "service_rating": r.get("service_rating"),
         "delivery_rating": r.get("delivery_rating"),
         "price_rating": r.get("price_rating"),
         "product_rating": r.get("product_rating")}
        for r in content.get("reviews", [])
    ]
    review_rows.sort(key=lambda r: r["id"])
    db.session.execute(db.insert(MerchantReview), review_rows)

    # ---- rebates ----
    rebate_rows = []
    rid = 1
    for group in brands.get("rebates", []):
        for item in group.get("rebates", []):
            rebate_rows.append({"id": rid, "brand": group["name"],
                                "title": item["title"],
                                "expires": item.get("expires", ""),
                                "pdf": item.get("pdf", "")})
            rid += 1
    rebate_rows.sort(key=lambda r: r["id"])
    db.session.execute(db.insert(Rebate), rebate_rows)

    # ---- buying guides ----
    db.session.execute(db.insert(BuyingGuide), [
        {"id": i, "slug": g["slug"], "title": g["title"], "body": g["text"]}
        for i, g in enumerate(content.get("buying_guides", []), start=1)
    ])

    # ---- FAQ items ----
    db.session.execute(db.insert(FaqItem), [
        {"id": i, "question": item["q"], "answer": item["a"],
         "links_json": json.dumps(item.get("links", []))}
        for i, item in enumerate(content.get("faq", []), start=1)
    ])

    # ---- content blocks ----
    db.session.execute(db.insert(ContentBlock), [
        {"key": key,
         "payload": json.dumps(content[key], ensure_ascii=False)}
        for key in ("home", "delivery", "carriers", "order_tracking_intro",
                    "finance_offers", "finance_steps", "finance_center_intro",
                    "customer_service_hub", "contact", "reviews_meta",
                    "buying_guides_intro", "deals", "returns_text",
                    "why_us_text", "warranty_text", "clearance_text",
                    "salestax_text", "instock_text", "site_facts",
                    "content_results_ranges")
        if key in content
    ])

    db.session.commit()


# ---------------------------------------------------------- benchmark users --
USERS = [
    {"email": "alice.j@test.com", "name": "Alice Johnson",
     "phone": "248-555-0143"},
    {"email": "bob.c@test.com", "name": "Bob Chen",
     "phone": "313-555-0187"},
    {"email": "carol.d@test.com", "name": "Carol Davis",
     "phone": "616-555-0122"},
    {"email": "david.k@test.com", "name": "David Kim",
     "phone": "734-555-0166"},
]

# Seeded orders: deterministic fixtures for the account / order-tracking
# surfaces. Products are chosen by id from the captured catalog.
ORDER_PLAN = [
    {"number": "10001", "user": 0, "status": "Delivered",
     "placed": "2026-09-12", "eta": "2026-09-24",
     "method": "In-Home Delivery", "shipping": 199.0,
     "carrier": "R+L Carriers", "tracking": "RL774912",
     "items": [(21476, 1), (26611, 1)], "state": "MI", "city": "Troy",
     "financing": "15 Months Special Financing",
     "events": [("Order Placed", "2026-09-12", "We received your order."),
                ("Order Prepared", "2026-09-16",
                 "Your order is prepared for shipment."),
                ("Shipped", "2026-09-17",
                 "Shipped via R+L Carriers. Pro # RL774912."),
                ("In Transit", "2026-09-22", "Your shipment is on its way."),
                ("Out for Delivery", "2026-09-24",
                 "The delivery crew will arrive today."),
                ("Delivered", "2026-09-24",
                 "Delivered and placed in your room of choice.")]},
    {"number": "10002", "user": 0, "status": "Shipped",
     "placed": "2026-09-25", "eta": "2026-10-06",
     "method": "Standard Delivery", "shipping": 0.0,
     "carrier": "Maersk", "tracking": "MN-88231340",
     "items": [(25555, 1)], "state": "MI", "city": "Troy",
     "financing": "15 Months Special Financing",
     "events": [("Order Placed", "2026-09-25", "We received your order."),
                ("Order Prepared", "2026-09-27",
                 "Your order is prepared for shipment."),
                ("Shipped", "2026-09-28",
                 "Shipped via Maersk. Tracking # MN-88231340.")]},
    {"number": "10003", "user": 1, "status": "In Transit",
     "placed": "2026-09-23", "eta": "2026-10-02",
     "method": "Standard Delivery", "shipping": 0.0,
     "carrier": "Valley Companies", "tracking": "VC559201",
     "items": [(16435, 1)], "state": "OH", "city": "Columbus",
     "financing": "",
     "events": [("Order Placed", "2026-09-23", "We received your order."),
                ("Order Prepared", "2026-09-25",
                 "Your order is prepared for shipment."),
                ("Shipped", "2026-09-26",
                 "Shipped via Valley Companies. Tracking # VC559201."),
                ("In Transit", "2026-09-28",
                 "Your shipment is on its way.")]},
    {"number": "10004", "user": 1, "status": "Processing",
     "placed": "2026-09-27", "eta": "2026-10-08",
     "method": "Standard Delivery", "shipping": 0.0,
     "carrier": "", "tracking": "",
     "items": [(19525, 1)], "state": "OH", "city": "Columbus",
     "financing": "",
     "events": [("Order Placed", "2026-09-27", "We received your order.")]},
    {"number": "10005", "user": 2, "status": "Out for Delivery",
     "placed": "2026-09-26", "eta": "2026-09-29",
     "method": "Standard Delivery", "shipping": 0.0,
     "carrier": "FedEx", "tracking": "774912345678",
     "items": [(21577, 1), (21779, 1)], "state": "IL", "city": "Naperville",
     "financing": "",
     "events": [("Order Placed", "2026-09-26", "We received your order."),
                ("Order Prepared", "2026-09-27",
                 "Your order is prepared for shipment."),
                ("Shipped", "2026-09-28",
                 "Shipped via FedEx. Tracking # 774912345678."),
                ("Out for Delivery", "2026-09-29",
                 "The delivery crew will arrive today.")]},
    {"number": "10006", "user": 2, "status": "Cancelled",
     "placed": "2026-09-20", "eta": None,
     "method": "Standard Delivery", "shipping": 0.0,
     "carrier": "", "tracking": "",
     "items": [(18945, 1)], "state": "IL", "city": "Naperville",
     "financing": "",
     "events": [("Order Placed", "2026-09-20", "We received your order."),
                ("Cancelled", "2026-09-21",
                 "Order cancelled within the 48-hour window.")]},
    {"number": "10007", "user": 3, "status": "Processing",
     "placed": "2026-09-28", "eta": "2026-10-09",
     "method": "Standard Delivery", "shipping": 0.0,
     "carrier": "", "tracking": "",
     "items": [(22905, 1)], "state": "MI", "city": "Ann Arbor",
     "financing": "",
     "events": [("Order Placed", "2026-09-28", "We received your order.")]},
    {"number": "10008", "user": 3, "status": "Delivered",
     "placed": "2026-08-30", "eta": "2026-09-10",
     "method": "Standard Delivery", "shipping": 0.0,
     "carrier": "R+L Carriers", "tracking": "RL770388",
     "items": [(19842, 1)], "state": "MI", "city": "Ann Arbor",
     "financing": "",
     "events": [("Order Placed", "2026-08-30", "We received your order."),
                ("Order Prepared", "2026-09-02",
                 "Your order is prepared for shipment."),
                ("Shipped", "2026-09-03",
                 "Shipped via R+L Carriers. Pro # RL770388."),
                ("In Transit", "2026-09-08", "Your shipment is on its way."),
                ("Out for Delivery", "2026-09-10",
                 "The delivery crew will arrive today."),
                ("Delivered", "2026-09-10", "Delivered to your curb.")]},
]


def build_benchmark_users(db):
    """Seed the four benchmark users and their order history."""
    from app import (Order, OrderEvent, OrderItem, Product, User)
    from datetime import date

    if User.query.count() > 0:
        return

    def d(s):
        return date(*map(int, s.split("-"))) if s else None

    db.session.execute(db.insert(User), [
        {"id": i, "email": u["email"],
         "password_hash": BENCHMARK_PASSWORD_HASH,
         "name": u["name"], "phone": u["phone"],
         "created_on": d("2026-08-15")}
        for i, u in enumerate(USERS, start=1)
    ])

    order_rows = []
    item_rows = []
    event_rows = []
    for j, plan in enumerate(ORDER_PLAN, start=1):
        user = USERS[plan["user"]]
        subtotal = 0.0
        for pid, qty in plan["items"]:
            product = db.session.get(Product, pid)
            subtotal += (product.price or 0.0) * qty if product else 0.0
        subtotal = round(subtotal, 2)
        tax = round(subtotal * 0.06, 2) if plan["state"] == "MI" else 0.0
        total = round(subtotal + plan["shipping"] + tax, 2)
        order_rows.append({
            "id": j, "number": plan["number"], "user_id": plan["user"] + 1,
            "email": user["email"], "ship_name": user["name"],
            "ship_address": f"{plan['number']} Maple Street",
            "ship_city": plan["city"], "ship_state": plan["state"],
            "ship_zip": {"MI": "48083", "OH": "43215",
                         "IL": "60563"}[plan["state"]],
            "phone": user["phone"], "status": plan["status"],
            "shipping_method": plan["method"],
            "shipping_cost": plan["shipping"],
            "subtotal": subtotal, "tax": tax, "total": total,
            "carrier": plan["carrier"], "tracking": plan["tracking"],
            "placed_on": d(plan["placed"]), "eta": d(plan["eta"]),
            "financing": plan["financing"],
        })
        for product_id, qty in plan["items"]:
            product = db.session.get(Product, product_id)
            if product is None:
                continue
            item_rows.append({"order_id": j, "product_id": product.id,
                              "name": product.name, "qty": qty,
                              "price": product.price or 0.0})
        for k, (step, when, note) in enumerate(plan["events"], start=1):
            event_rows.append({"order_id": j, "step": step,
                               "happened_on": d(when), "note": note})

    db.session.execute(db.insert(Order), order_rows)
    db.session.execute(db.insert(OrderItem), item_rows)
    db.session.execute(db.insert(OrderEvent), event_rows)
    db.session.commit()


# ------------------------------------------------------------------- entry --
# Thin wrapper: importing app.py already materializes the seed inside
# `with app.app_context():` (db.create_all + the gated seed_database /
# seed_benchmark_users); __main__ re-runs the same gated path as a no-op so
# this entry point is idempotent. Run with PYTHONHASHSEED=0 during the image
# build so the SQLite output is byte-reproducible.
if __name__ == "__main__":
    from app import app  # noqa: F401  (import triggers the gated bootstrap)
