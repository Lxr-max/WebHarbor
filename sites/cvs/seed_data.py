"""Build the frozen CVS snapshot. Runtime handlers query SQLite only."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from urllib.parse import urlsplit

FIXTURE_USERS = [
    ("Alice", "Johnson", "alice.j@test.com"),
    ("Bob", "Chen", "bob.c@test.com"),
    ("Carol", "Davis", "carol.d@test.com"),
    ("David", "Kim", "david.k@test.com"),
]


def fixture_password_hash(email):
    """Deterministic hashes for the explicitly public benchmark credentials."""
    salt = "webharbor-cvs-demo-" + email.split("@")[0]
    digest = hashlib.pbkdf2_hmac("sha256", b"TestPass123!", salt.encode(), 600000).hex()
    return f"pbkdf2:sha256:600000${salt}${digest}"


def app_module():
    # Running app.py as a script must reuse its models rather than importing it
    # a second time under a different module name.
    import sys
    main = sys.modules.get("__main__")
    if main is not None and getattr(main, "__file__", "").endswith("/app.py") and hasattr(main, "Product"):
        return main
    import app
    return app


def seed_database():
    module = app_module()
    db = module.db
    if db.session.get(module.SnapshotMeta, 1) is not None:
        return
    source_path = Path(__file__).with_name("source_data.json")
    if not source_path.is_file():
        return
    data = json.loads(source_path.read_text())
    for row in data.get("categories", []):
        db.session.add(module.Category(slug=row["slug"], name=row["name"], path=row.get("path", "/shop/category/" + row["slug"]), image_path=row.get("image_path", "")))
    db.session.flush()
    product_fields = {"name", "brand", "category_slug", "price_cents", "price_min_cents", "price_max_cents", "price_text", "rating", "review_count", "description", "details", "features", "image_paths", "source_url", "captured_at", "detail_status"}
    for row in data.get("products", []):
        product_id = str(row["id"])
        values = {key: row[key] for key in product_fields if key in row}
        source_url = row.get("source_url", "https://www.cvs.com/shop/product/" + product_id)
        path = row.get("path") or urlsplit(source_url).path
        db.session.add(module.Product(id=product_id, path=path, **values))
        for index, variant in enumerate(row.get("variants", [])):
            db.session.add(module.Variant(id=str(variant.get("id", f"{product_id}-{index}")), product_id=product_id,
                                          label=variant["label"], price_cents=variant.get("price_cents"), source_sku=variant.get("source_sku")))
    for row in data.get("stores", []):
        store_id = str(row.get("id", row.get("store_id")))
        source_url = row["source_url"]
        nearby = row.get("nearby_ids", [v["store_id"] for v in row.get("nearby_stores", [])])
        db.session.add(module.Store(id=store_id, name=row.get("name", row["address"]), path=row.get("path") or urlsplit(source_url).path,
                                    address=row.get("street", row["address"]), city=row["city"], state=row["state"], postal_code=row.get("postal_code", row.get("zip", "")),
                                    phone=row["phone"], store_type=row.get("store_type", ""), services=row.get("services", []), store_hours=row.get("store_hours", []),
                                    pharmacy_hours=row.get("pharmacy_hours", []), pharmacy_lunch=row.get("pharmacy_lunch"), nearby_ids=[str(i) for i in nearby],
                                    nearby_stores=row.get("nearby_stores", []), about_text=row.get("about_text", ""),
                                    source_url=source_url, captured_at=row.get("captured_at", "")))
    for row in data.get("pages", []):
        db.session.add(module.Page(slug=row["slug"], title=row["title"], path=row["path"], body_html=row["body_html"], source_url=row["source_url"], captured_at=row.get("captured_at", "")))
    db.session.add(module.SnapshotMeta(id=1, reference_date=data.get("reference_date", "2026-09-28"), home_assets=data.get("home_assets", {}), source_revision=data.get("source_revision")))
    db.session.commit()


def seed_benchmark_users():
    module = app_module()
    db = module.db
    if module.User.query.filter_by(email="alice.j@test.com").first() is not None:
        return
    for first, last, email in FIXTURE_USERS:
        db.session.add(module.User(first_name=first, last_name=last, email=email,
                                   password_hash=fixture_password_hash(email)))
    db.session.commit()


if __name__ == "__main__":
    module = app_module()
    with module.app.app_context():
        module.db.create_all()
        seed_database()
        seed_benchmark_users()
        print("CVS seed ready:", module.Product.query.count(), "products;", module.Store.query.count(), "stores;", module.User.query.count(), "users")
