"""Regression coverage for snapshot fidelity, isolated state, and local shopping.

Run with ``python -m unittest discover -s sites/cvs/tests -v``. Tests use an
isolated CVS_INSTANCE_PATH and never write to the shipped frozen seed.
"""
from __future__ import annotations

import hashlib
import html
from html.parser import HTMLParser
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

from flask import template_rendered
from werkzeug.security import check_password_hash


SITE = Path(__file__).resolve().parents[1]


class HTMLFields(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.inputs = []
        self.links = []
        self.forms = []
        self.current_form = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "input":
            self.inputs.append(values)
        elif tag == "a":
            self.links.append(values)
        elif tag == "form":
            values["controls"] = []
            self.forms.append(values)
            self.current_form = values
        if tag in {"input", "button"} and self.current_form is not None:
            self.current_form["controls"].append({"tag": tag, **values})

    def handle_endtag(self, tag):
        if tag == "form":
            self.current_form = None


class CVSAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cvs-regression-")
        cls.root = Path(cls.temp.name)
        cls.old_environment = os.environ.get("CVS_INSTANCE_PATH")
        cls.old_modules = {key: sys.modules.pop(key, None) for key in ("app", "seed_data")}
        sys.path.insert(0, str(SITE))
        os.environ["CVS_INSTANCE_PATH"] = str(cls.root / "runtime")
        cls.site = importlib.import_module("app")
        cls.app = cls.site.app
        cls.app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
        cls.seed = importlib.import_module("seed_data")
        with cls.app.app_context():
            cls.site.db.session.remove()
            cls.site.db.engine.dispose()
        cls.baseline = cls.root / "baseline.db"
        shutil.copyfile(cls.site.DB_PATH, cls.baseline)
        cls.source = json.loads((SITE / "source_data.json").read_text())

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            cls.site.db.session.remove()
            cls.site.db.engine.dispose()
        for key, previous in cls.old_modules.items():
            sys.modules.pop(key, None)
            if previous is not None:
                sys.modules[key] = previous
        sys.path.remove(str(SITE))
        if cls.old_environment is None:
            os.environ.pop("CVS_INSTANCE_PATH", None)
        else:
            os.environ["CVS_INSTANCE_PATH"] = cls.old_environment
        cls.temp.cleanup()

    def setUp(self):
        with self.app.app_context():
            self.site.db.session.remove()
            self.site.db.engine.dispose()
        shutil.copyfile(self.baseline, self.site.DB_PATH)
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            self.site.db.session.remove()
            self.site.db.engine.dispose()

    def token(self, client=None):
        client = client or self.client
        response = client.get("/account-login/look-up")
        self.assertEqual(response.status_code, 200)
        tokens = [field["value"] for field in HTMLFields(response.get_data(as_text=True)).inputs
                  if field.get("name") == "csrf_token"]
        self.assertTrue(tokens, "A real login form must expose its CSRF field")
        return tokens[0]

    def post(self, path, data=None, client=None, **kwargs):
        client = client or self.client
        values = dict(data or {})
        values["csrf_token"] = self.token(client)
        return client.post(path, data=values, **kwargs)

    def login(self, client=None, email="alice.j@test.com", **fields):
        response = self.post("/account-login/look-up", {
            "email": email, "password": "TestPass123!", **fields,
        }, client=client)
        self.assertEqual(response.status_code, 302)
        return response

    def add(self, product_id="478253", quantity=1, client=None, **fields):
        return self.post("/cart/add", {"product_id": product_id, "quantity": quantity, **fields}, client=client)

    def shipping_fields(self, **fields):
        return {"fulfillment": "shipping", "email": "qa@example.test", "recipient": "Test Customer",
                "line1": "123 Example Lane", "line2": "", "city": "Urbana", "state": "IL",
                "postal_code": "61801", **fields}

    def count(self, model):
        with self.app.app_context():
            return model.query.count()

    def cart_id(self, user_id=None):
        with self.app.app_context():
            query = self.site.CartItem.query
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
            return query.order_by(self.site.CartItem.id.desc()).first().id

    def rendered(self, path, client=None):
        captured = []
        def record(sender, template, context, **extra):
            captured.append(context)
        template_rendered.connect(record, self.app)
        try:
            response = (client or self.client).get(path)
        finally:
            template_rendered.disconnect(record, self.app)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(captured)
        return response, captured[-1]

    def test_snapshot_counts_and_missing_facts_remain_missing(self):
        with self.app.app_context():
            self.assertEqual(self.site.Product.query.count(), 40)
            self.assertEqual(self.site.Product.query.filter_by(detail_status="captured").count(), 23)
            self.assertEqual(self.site.Product.query.filter_by(detail_status="listing_only").count(), 17)
            self.assertEqual(self.site.Store.query.count(), 25)
            self.assertEqual(self.site.Page.query.count(), 4)
            self.assertEqual(self.site.Category.query.count(), 2)
            self.assertEqual(self.site.User.query.count(), 4)
            self.assertEqual(self.site.Variant.query.count(), 0)
            self.assertEqual(self.site.Product.query.filter(self.site.Product.rating.is_not(None)).count(), 18)
            for product in self.site.Product.query.filter(self.site.Product.detail_status != "captured"):
                self.assertEqual(product.description, "")
                self.assertEqual(product.details, [])
        self.assertEqual(self.client.get("/_health").json, {"ok": True, "site": "cvs", "products": 40, "stores": 25})

    def test_sale_price_is_not_a_coupon_or_previous_price(self):
        with self.app.app_context():
            sale = self.site.db.session.get(self.site.Product, "452370")
            self.assertEqual(sale.price_cents, 399)
            self.assertIn("$5.19", sale.price_text)
            self.assertIn("save $5.00", sale.price_text)
            member = self.site.db.session.get(self.site.Product, "851347")
            self.assertEqual(member.price_cents, 2499)
            self.assertIn("19.99", member.price_text)
        self.assertEqual(self.add("452370").status_code, 302)
        _, context = self.rendered("/rx/dotm/cart")
        self.assertEqual(context["subtotal_cents"], 399)

    def test_recorded_offers_are_visible_without_changing_demo_prices(self):
        examples = [
            ("452370", 399, "$5.19", "save $5.00"),
            ("851347", 2499, "ExtraCare Plus", "$19.99"),
            ("1015021", 829, "save $4.00", "Buy 1, Get 1 40% Off"),
        ]
        for product_id, price_cents, *offer_texts in examples:
            with self.subTest(product=product_id):
                client = self.app.test_client()
                response = client.get(f"/shop/product/{product_id}")
                self.assertEqual(response.status_code, 200)
                text = html.unescape(response.get_data(as_text=True))
                self.assertIn("Recorded offer details", text)
                self.assertIn("As shown on 2026-09-28", text)
                self.assertIn("Demo orders use the single-item price above.", text)
                self.assertIn("Membership prices, coupons, rewards and multi-buy offers are not applied.", text)
                self.assertIn(f'id="product-price">${price_cents / 100:.2f}</p>', text)
                for offer_text in offer_texts:
                    self.assertIn(offer_text, text)
                self.assertEqual(self.add(product_id, quantity=2, client=client).status_code, 302)
                _, context = self.rendered("/rx/dotm/cart", client)
                self.assertEqual(context["subtotal_cents"], price_cents * 2)
        text = self.client.get("/shop/product/478253").get_data(as_text=True)
        self.assertNotIn("Recorded offer details", text)

    def test_product_details_omit_source_placeholder_without_changing_snapshot(self):
        before = self.site.DB_PATH.read_bytes()
        response, context = self.rendered("/shop/product/478253")
        text = response.get_data(as_text=True)
        self.assertNotIn("Select a value", text)
        self.assertEqual([section["heading"] for section in context["detail_sections"]], ["Details"])
        self.assertIn("Sugar-free formula", text)
        with self.app.app_context():
            product = self.site.db.session.get(self.site.Product, "478253")
            self.assertIn({"heading": "Specifications", "text": "Product type\nSelect a value"}, product.details)
        response, context = self.rendered("/shop/product/476215")
        text = html.unescape(response.get_data(as_text=True))
        self.assertEqual([section["heading"] for section in context["detail_sections"]],
                         ["Details", "Ingredients", "Directions", "Warnings", "Specifications"])
        for fact in ("Replacement toothbrush heads", "Life Stage\nChild", "Not suitable for children under 3 years."):
            self.assertIn(fact, text)
        for product_id in ("7201029", "7200293", "1015021"):
            response, context = self.rendered(f"/shop/product/{product_id}")
            self.assertEqual(context["detail_sections"], [])
            self.assertIn("A full description is unavailable", response.get_data(as_text=True))
        self.assertEqual(self.site.DB_PATH.read_bytes(), before)

    def test_price_ranges_are_visible_but_cannot_enter_cart(self):
        with self.app.app_context():
            ranged = self.site.Product.query.filter(self.site.Product.price_min_cents != self.site.Product.price_max_cents).all()
            self.assertEqual(len(ranged), 3)
            records = [(p.id, p.path, p.price_text, p.purchasable, p.price_cents) for p in ranged]
        for product_id, path, price_text, purchasable, exact_price in records:
            with self.subTest(product=product_id):
                self.assertIsNone(exact_price)
                self.assertFalse(purchasable)
                text = html.unescape(self.client.get(path).get_data(as_text=True))
                self.assertIn(price_text, text)
                for form in HTMLFields(text).forms:
                    if form.get("action") == "/cart/add":
                        submit_controls = [control for control in form["controls"]
                                           if control.get("type", "submit" if control["tag"] == "button" else "text") == "submit"]
                        self.assertTrue(submit_controls)
                        self.assertTrue(all("disabled" in control for control in submit_controls))
                        quantity_controls = [control for control in form["controls"] if control.get("name") == "quantity"]
                        self.assertTrue(quantity_controls)
                        self.assertTrue(all("disabled" in control for control in quantity_controls))
                self.assertIn("Individual options and their exact prices are unavailable.", text)
                self.assertIn("Browse shampoo", text)
                self.assertEqual(self.add(product_id).status_code, 400)
        self.assertEqual(self.count(self.site.CartItem), 0)

    def test_review_counts_render_without_inferred_stars(self):
        response, context = self.rendered("/shop/category/shampoo?brand=OGX")
        text = response.get_data(as_text=True)
        self.assertEqual(len(context["products"]), 3)
        for product in context["products"]:
            self.assertIsNone(product.rating)
            count = str(product.review_count)
            self.assertTrue(count in text or f"{product.review_count:,}" in text)
        self.assertNotIn("out of 5", text)

    def test_explicit_product_ratings_render_and_filter_correctly(self):
        for product_id, rating, reviews in (("452370", 4.7, 89), ("456310", 4.6, 78),
                                            ("814313", 1.0, 1), ("478894", 4.9, 56)):
            with self.subTest(product=product_id):
                response = self.client.get(f"/shop/product/{product_id}")
                text = response.get_data(as_text=True)
                self.assertIn(f"{rating} out of 5", text)
                self.assertIn(f"{reviews} reviews", text)
        _, context = self.rendered("/shop/category/oral-care?rating=4.8")
        self.assertEqual({product.id for product in context["products"]}, {"428704", "452372", "478894"})
        for product_id in ("455627", "476215", "478253", "496783", "514695"):
            text = self.client.get(f"/shop/product/{product_id}").get_data(as_text=True)
            self.assertIn("0 reviews", text)
            self.assertNotIn("out of 5", text)

    def test_rating_sort_keeps_unrated_products_after_observed_ratings(self):
        products = []
        for page in range(1, 5):
            _, context = self.rendered(f"/search?sort=rating&page={page}")
            products.extend(context["products"])
        self.assertEqual(len({product.id for product in products}), 40)
        self.assertEqual(products[0].id, "478894")
        self.assertEqual(products[17].id, "814313")
        ratings = [product.rating for product in products[:18]]
        self.assertEqual(ratings, sorted(ratings, reverse=True))
        self.assertTrue(all(product.rating is None for product in products[18:]))

    def test_r3_detail_provenance_preserves_price_times_and_previous_failures(self):
        provenance = json.loads((SITE / "provenance.json").read_text())
        captures = {entry["id"]: entry for entry in provenance["sources"]
                    if entry.get("capture_round") == "r3" and entry["kind"] == "product_detail"}
        self.assertEqual(len(captures), 23)
        records = {product["id"]: product for product in self.source["products"]}
        for product_id, capture in captures.items():
            record = records[product_id]
            self.assertEqual(record["detail_captured_at"], capture["captured_at"])
            self.assertEqual(record["listing_captured_at"], record["captured_at"])
            for key in ("raw_ax_sha256", "raw_dom_sha256", "record_sha256"):
                self.assertRegex(capture[key], r"^[0-9a-f]{64}$")
        for product_id in ("452372", "851347"):
            self.assertEqual(records[product_id]["detail_status"], "captured")
            history = records[product_id]["detail_capture_history"]
            self.assertTrue(any(entry["status"] == "unavailable" and entry["reason"] for entry in history))
        blocked = next(entry for entry in provenance["sources"]
                       if entry.get("capture_round") == "r3" and entry["id"] == "723038")
        self.assertEqual(blocked["kind"], "product_detail_attempt")
        self.assertEqual(blocked["status"], "excluded")
        self.assertEqual(records["723038"]["detail_status"], "listing_only")

    def test_canonical_and_original_source_routes_render(self):
        with self.app.app_context():
            records = [(p.path, "/shop/product/" + p.id, p.name) for p in self.site.Product.query]
            records += [(s.path, "/store-locator/store/" + s.id, s.phone) for s in self.site.Store.query]
            records += [(c.path, "/shop/category/" + c.slug, c.name) for c in self.site.Category.query]
            records += [(p.path, "/retail/help/" + p.slug, p.title) for p in self.site.Page.query if p.slug != "help_index"]
        for original, canonical, expected in records:
            with self.subTest(path=original):
                for path in {original, canonical}:
                    response = self.client.get(path)
                    self.assertEqual(response.status_code, 200)
                    self.assertIn(expected, html.unescape(response.get_data(as_text=True)))
        for path in ("/", "/shop", "/retail/help/help_index", "/rx/dotm/cart", "/store-locator/landing"):
            self.assertEqual(self.client.get(path).status_code, 200)
        self.assertEqual(self.client.get("/shop/product/not-a-product").status_code, 404)

    def test_search_brand_price_and_literal_wildcards(self):
        _, context = self.rendered("/search?q=shampoo&brand=Dove&price_max=6&sort=price_asc")
        self.assertEqual(context["total"], 2)
        self.assertTrue(all(p.brand == "Dove" and p.price_cents <= 600 for p in context["products"]))
        self.assertNotIn("Dove Men+Care", [p.brand for p in context["products"]])
        _, context = self.rendered("/search?q=%25")
        self.assertEqual(context["total"], 0)
        _, context = self.rendered("/search?q=%27%20OR%201%3D1--")
        self.assertEqual(context["total"], 0)
        _, context = self.rendered("/shop/category/shampoo?price_min=11&price_max=12")
        self.assertIn("7200475", [p.id for p in context["products"]])

    def test_pagination_is_complete_disjoint_and_preserves_filters(self):
        seen = []
        for page in range(1, 5):
            _, context = self.rendered(f"/search?page={page}&sort=name")
            seen.extend(p.id for p in context["products"])
            self.assertEqual(context["pages"], 4)
        self.assertEqual(len(seen), 40)
        self.assertEqual(len(set(seen)), 40)
        response, context = self.rendered("/search?q=shampoo&sort=price_asc&page=1")
        next_links = [urlsplit(a.get("href", "")) for a in HTMLFields(response.get_data(as_text=True)).links
                      if parse_qs(urlsplit(a.get("href", "")).query).get("page") == ["2"]]
        self.assertTrue(next_links)
        self.assertTrue(all(parse_qs(link.query).get("q") == ["shampoo"] for link in next_links))
        self.assertTrue(all(parse_qs(link.query).get("sort") == ["price_asc"] for link in next_links))
        _, context = self.rendered("/search?page=999")
        self.assertEqual(context["page"], 4)

    def test_invalid_filters_fail_closed(self):
        for query in ("price_min=-1", "price_max=NaN", "price_max=Infinity", "price_min=oops", "rating=NaN", "rating=6"):
            with self.subTest(query=query):
                self.assertEqual(self.client.get("/search?" + query).status_code, 400)

    def test_store_filters_use_intersection_and_selection_is_local(self):
        query = "/store-locator/landing?q=Chicago&service=Accepts+WIC&service=UPS+access+point&service=Drug+disposal"
        _, context = self.rendered(query)
        self.assertEqual(context["total"], 1)
        store = context["stores"][0]
        self.assertTrue({"Accepts WIC", "UPS access point", "Drug disposal"} <= set(store.services))
        self.assertEqual(self.post("/store-locator/select/" + store.id, {"next": "//example.test/"}).location, "/store-locator/landing")
        with self.client.session_transaction() as state:
            self.assertEqual(state["selected_store"], store.id)
        with self.app.test_client().session_transaction() as state:
            self.assertNotIn("selected_store", state)

    def test_csrf_missing_invalid_and_other_session_tokens_are_rejected(self):
        other = self.app.test_client()
        for token in (None, "not-a-token", self.token(other)):
            fields = {"product_id": "478253", "quantity": 1}
            if token is not None:
                fields["csrf_token"] = token
            self.assertEqual(self.client.post("/cart/add", data=fields).status_code, 400)
        self.assertEqual(self.count(self.site.CartItem), 0)
        self.assertEqual(self.add().status_code, 302)
        self.assertEqual(self.count(self.site.CartItem), 1)

    def test_cart_ignores_posted_prices_and_owner_ids(self):
        self.assertEqual(self.add(quantity=2, price_cents="1", subtotal_cents="1", user_id="1", guest_token="attacker").status_code, 302)
        _, context = self.rendered("/rx/dotm/cart")
        self.assertEqual(context["subtotal_cents"], 1198)
        with self.app.app_context():
            row = self.site.CartItem.query.one()
            self.assertIsNone(row.user_id)
            self.assertNotEqual(row.guest_token, "attacker")

    def test_cart_rejects_invalid_quantities_and_overflow_without_partial_write(self):
        for quantity in (0, -1, 21, "1.5", "NaN", "", "many"):
            with self.subTest(quantity=quantity):
                self.assertEqual(self.add(quantity=quantity).status_code, 400)
        self.assertEqual(self.count(self.site.CartItem), 0)
        self.assertEqual(self.add(quantity=20).status_code, 302)
        self.assertEqual(self.add(quantity=1).status_code, 400)
        row_id = self.cart_id()
        self.assertEqual(self.post(f"/cart/items/{row_id}", {"quantity": 0}).status_code, 400)
        with self.app.app_context():
            self.assertEqual(self.site.CartItem.query.one().quantity, 20)
        self.assertEqual(self.post(f"/cart/items/{row_id}", {"quantity": 2}).status_code, 302)
        self.assertEqual(self.post(f"/cart/items/{row_id}/remove").status_code, 302)
        self.assertEqual(self.count(self.site.CartItem), 0)

    def test_unknown_and_cross_product_variants_are_rejected(self):
        self.assertEqual(self.add("does-not-exist").status_code, 404)
        self.assertEqual(self.add(variant_id="does-not-exist").status_code, 400)
        with self.app.app_context():
            self.site.db.session.add(self.site.Variant(id="test-option", product_id="481078", label="Regression option", price_cents=399))
            self.site.db.session.commit()
        self.assertEqual(self.add("478253", variant_id="test-option").status_code, 400)
        self.assertEqual(self.add("481078").status_code, 400)
        self.assertEqual(self.count(self.site.CartItem), 0)
        self.assertEqual(self.add("481078", variant_id="test-option", price_cents="1").status_code, 302)
        _, context = self.rendered("/rx/dotm/cart")
        self.assertEqual(context["subtotal_cents"], 399)

    def test_guest_cart_cannot_be_modified_by_another_browser(self):
        self.add()
        row_id = self.cart_id()
        other = self.app.test_client()
        self.assertEqual(self.post(f"/cart/items/{row_id}", {"quantity": 9}, client=other).status_code, 404)
        self.assertEqual(self.post(f"/cart/items/{row_id}/remove", client=other).status_code, 404)
        _, context = self.rendered("/rx/dotm/cart", other)
        self.assertEqual(context["items"], [])
        with self.app.app_context():
            self.assertEqual(self.site.CartItem.query.one().quantity, 1)

    def test_account_carts_are_isolated(self):
        self.login()
        self.add()
        row_id = self.cart_id()
        other = self.app.test_client()
        self.login(other, email="bob.c@test.com")
        self.assertEqual(self.post(f"/cart/items/{row_id}/remove", client=other).status_code, 404)
        self.assertEqual(self.post(f"/cart/items/{row_id}", {"quantity": 4}, client=other).status_code, 404)
        _, context = self.rendered("/rx/dotm/cart", other)
        self.assertEqual(context["items"], [])

    def test_login_adopts_only_current_guest_cart_without_losing_quantity(self):
        account_client = self.app.test_client()
        self.login(account_client)
        self.add(quantity=9, client=account_client)
        self.add(quantity=10)
        other_guest = self.app.test_client()
        self.add(quantity=3, client=other_guest)
        self.login()
        with self.app.app_context():
            user = self.site.User.query.filter_by(email="alice.j@test.com").one()
            row = self.site.CartItem.query.filter_by(user_id=user.id).one()
            self.assertEqual(row.quantity, 19)
            self.assertIsNone(row.guest_token)
            remaining_guest = self.site.CartItem.query.filter_by(user_id=None).one()
            self.assertEqual(remaining_guest.quantity, 3)

    def test_login_overflow_preserves_both_carts_and_authentication(self):
        account = self.app.test_client()
        self.login(account)
        self.add(quantity=15, client=account)
        self.add(product_id="481078", quantity=2)
        self.add(quantity=10)
        with self.app.app_context():
            before = [(r.id, r.user_id, r.guest_token, r.product_id, r.quantity)
                      for r in self.site.CartItem.query.order_by(self.site.CartItem.id)]
        result = self.post("/account-login/look-up", {
            "email": "alice.j@test.com", "password": "TestPass123!"})
        self.assertEqual(result.status_code, 409)
        self.assertIn(b"both carts are unchanged", result.data)
        with self.client.session_transaction() as session:
            self.assertNotIn("_user_id", session)
        with self.app.app_context():
            after = [(r.id, r.user_id, r.guest_token, r.product_id, r.quantity)
                     for r in self.site.CartItem.query.order_by(self.site.CartItem.id)]
        self.assertEqual(before, after)

    def test_checkout_validation_does_not_create_an_order_or_clear_cart(self):
        self.add()
        invalid = [self.shipping_fields(fulfillment="drone"), self.shipping_fields(email="invalid"),
                   self.shipping_fields(postal_code="not-a-zip"), self.shipping_fields(state="Illinois"),
                   {"fulfillment": "pickup", "email": "qa@example.test", "store_id": "missing"}]
        for fields in invalid:
            with self.subTest(fields=fields):
                self.assertEqual(self.post("/checkout", fields).status_code, 200)
                self.assertEqual(self.count(self.site.Order), 0)
                self.assertEqual(self.count(self.site.CartItem), 1)
        self.assertEqual(self.post("/checkout", self.shipping_fields(address_id="1")).status_code, 403)

    def test_shipping_threshold_is_inclusive_and_server_calculated(self):
        for price, expected_shipping in ((3499, 499), (3500, 0), (3501, 0)):
            with self.subTest(price=price):
                with self.app.app_context():
                    self.site.db.session.get(self.site.Product, "478253").price_cents = price
                    self.site.db.session.commit()
                self.add()
                response = self.post("/checkout", self.shipping_fields(shipping_cents="0", total_cents="1"))
                self.assertEqual(response.status_code, 302)
                with self.app.app_context():
                    order = self.site.Order.query.order_by(self.site.Order.id.desc()).first()
                    self.assertEqual(order.subtotal_cents, price)
                    self.assertEqual(order.shipping_cents, expected_shipping)
                    self.assertEqual(order.total_cents, price + expected_shipping)

    def test_guest_order_is_private_and_remains_a_guest_order_after_login(self):
        self.add(quantity=2)
        response = self.post("/checkout", self.shipping_fields(price_cents="1", total_cents="1"))
        self.assertEqual(response.status_code, 302)
        confirmation_path = response.location
        self.assertEqual(self.client.get(confirmation_path).status_code, 200)
        with self.app.app_context():
            order = self.site.Order.query.one()
            self.assertIsNone(order.user_id)
            self.assertTrue(order.guest_token)
            self.assertEqual(order.items[0]["price_cents"], 599)
            self.assertEqual(order.items[0]["quantity"], 2)
            self.assertEqual(order.total_cents, 1697)
            self.assertTrue(order.number.startswith("CVS-DEMO-"))
            self.assertEqual(self.site.CartItem.query.count(), 0)
        other = self.app.test_client()
        self.assertEqual(other.get(confirmation_path).status_code, 404)
        self.login()
        self.assertEqual(self.client.get(confirmation_path).status_code, 404)
        _, context = self.rendered("/account/order/order-history")
        self.assertEqual(context["orders"], [])
        self.post("/logout")
        self.assertEqual(self.client.get(confirmation_path).status_code, 200)

    def test_pickup_order_and_account_history_are_owned(self):
        self.login()
        self.add()
        response = self.post("/checkout", {"fulfillment": "pickup", "store_id": "8683", "email": "alice.j@test.com", "shipping_cents": "9999"})
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            order = self.site.Order.query.one()
            order_id, number = order.id, order.number
            self.assertIsNotNone(order.user_id)
            self.assertIsNone(order.guest_token)
            self.assertIsNone(order.address)
            self.assertEqual(order.shipping_cents, 0)
            self.assertEqual(order.total_cents, 599)
            self.assertIn("GREEN", order.store_address)
        self.assertIn(number, self.client.get("/account/order/order-history").get_data(as_text=True))
        self.assertEqual(self.client.get(f"/account/order/{order_id}").status_code, 200)
        other = self.app.test_client()
        self.login(other, email="bob.c@test.com")
        self.assertEqual(other.get(response.location).status_code, 404)
        self.assertEqual(other.get(f"/account/order/{order_id}").status_code, 404)
        self.assertNotIn(number, other.get("/account/order/order-history").get_data(as_text=True))

    def test_saved_addresses_are_owned_for_display_delete_and_checkout(self):
        self.login()
        address = {key: value for key, value in self.shipping_fields().items() if key not in {"fulfillment", "email"}}
        address.update(label="Regression address", user_id="2")
        self.assertEqual(self.post("/account/addresses", address).status_code, 302)
        with self.app.app_context():
            saved = self.site.Address.query.one()
            address_id = saved.id
            owner = self.site.User.query.filter_by(email="alice.j@test.com").one()
            self.assertEqual(saved.user_id, owner.id)
        other = self.app.test_client()
        self.login(other, email="bob.c@test.com")
        self.assertNotIn("Regression address", other.get("/account/addresses").get_data(as_text=True))
        self.assertEqual(self.post(f"/account/addresses/{address_id}/delete", client=other).status_code, 404)
        self.add(client=other)
        self.assertEqual(self.post("/checkout", self.shipping_fields(address_id=str(address_id)), client=other).status_code, 404)
        self.assertEqual(self.count(self.site.Order), 0)
        self.add()
        self.assertEqual(self.post("/checkout", self.shipping_fields(address_id=str(address_id), line1="Tampered")).status_code, 302)
        with self.app.app_context():
            self.assertEqual(self.site.Order.query.one().address["line1"], "123 Example Lane")
        self.assertEqual(self.post(f"/account/addresses/{address_id}/delete").status_code, 302)
        self.assertEqual(self.count(self.site.Address), 0)

    def test_guest_favorite_survives_failed_login_and_saves_idempotently(self):
        with self.app.app_context():
            product_path = self.site.db.session.get(self.site.Product, "478253").path
        response = self.post("/account/favorites/478253", {"next": "https://example.test/"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(parse_qs(urlsplit(response.location).query)["next"], [product_path])
        login_page = self.client.get(response.location)
        self.assertEqual(login_page.status_code, 200)
        next_values = [field["value"] for field in HTMLFields(login_page.get_data(as_text=True)).inputs
                       if field.get("name") == "next"]
        self.assertEqual(next_values, [product_path])
        for password in ("wrong-password", "still-wrong"):
            response = self.post("/account-login/look-up", {
                "email": "alice.j@test.com", "password": password, "next": next_values[0],
            })
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.count(self.site.Favorite), 0)
            with self.client.session_transaction() as state:
                self.assertEqual(state["pending_favorite"], "478253")
        response = self.login(next=next_values[0])
        self.assertEqual(response.location, product_path)
        landing = self.client.get(response.location)
        self.assertEqual(landing.status_code, 200)
        self.assertIn("Remove from favorites", landing.get_data(as_text=True))
        _, context = self.rendered("/account/favorites")
        self.assertEqual([product.id for product in context["products"]], ["478253"])
        with self.client.session_transaction() as state:
            self.assertNotIn("pending_favorite", state)
        self.login()
        self.assertEqual(self.count(self.site.Favorite), 1)
        self.post("/logout")
        for _ in range(2):
            self.assertEqual(self.post("/account/favorites/478253").status_code, 302)
        self.assertEqual(self.login().location, product_path)
        self.assertEqual(self.count(self.site.Favorite), 1)

    def test_guest_favorite_is_saved_after_registration(self):
        with self.app.app_context():
            product_path = self.site.db.session.get(self.site.Product, "481078").path
        self.post("/account/favorites/481078")
        fields = {"first_name": "Favorite", "last_name": "Customer", "email": "favorite@example.test",
                  "password": "LocalTest123!"}
        self.assertEqual(self.post("/account-registration/look-up", {**fields, "password": "short"}).status_code, 200)
        self.assertEqual(self.count(self.site.Favorite), 0)
        self.assertEqual(self.count(self.site.User), 4)
        with self.client.session_transaction() as state:
            self.assertEqual(state["pending_favorite"], "481078")
        response = self.post("/account-registration/look-up", fields)
        self.assertEqual(response.location, product_path)
        landing = self.client.get(response.location)
        self.assertEqual(landing.status_code, 200)
        self.assertIn("Remove from favorites", landing.get_data(as_text=True))
        with self.app.app_context():
            favorite = self.site.Favorite.query.one()
            user = self.site.User.query.filter_by(email=fields["email"]).one()
            self.assertEqual((favorite.user_id, favorite.product_id), (user.id, "481078"))
        with self.client.session_transaction() as state:
            self.assertNotIn("pending_favorite", state)
        _, context = self.rendered("/account/favorites")
        self.assertEqual([product.id for product in context["products"]], ["481078"])

    def test_pending_favorites_require_valid_product_csrf_and_own_session(self):
        for token in (None, "invalid-token", self.token(self.app.test_client())):
            fields = {} if token is None else {"csrf_token": token}
            self.assertEqual(self.client.post("/account/favorites/478253", data=fields).status_code, 400)
            with self.client.session_transaction() as state:
                self.assertNotIn("pending_favorite", state)
        self.assertEqual(self.post("/account/favorites/not-real").status_code, 404)
        with self.client.session_transaction() as state:
            self.assertNotIn("pending_favorite", state)
        self.post("/account/favorites/481078")
        self.post("/account/favorites/478253")
        self.assertEqual(self.client.post("/account/favorites/481078", data={"csrf_token": "invalid"}).status_code, 400)
        self.assertEqual(self.post("/account/favorites/not-real").status_code, 404)
        self.assertEqual(self.client.post("/account-login/look-up", data={
            "email": "alice.j@test.com", "password": "TestPass123!",
        }).status_code, 400)
        self.assertEqual(self.count(self.site.Favorite), 0)
        with self.client.session_transaction() as state:
            self.assertEqual(state["pending_favorite"], "478253")
        other = self.app.test_client()
        self.login(other, email="bob.c@test.com")
        self.assertEqual(self.count(self.site.Favorite), 0)
        response = self.login()
        self.assertEqual(self.client.get(response.location).status_code, 200)
        _, context = self.rendered("/account/favorites", other)
        self.assertEqual(context["products"], [])
        with self.app.app_context():
            favorite = self.site.Favorite.query.one()
            alice = self.site.User.query.filter_by(email="alice.j@test.com").one()
            self.assertEqual((favorite.user_id, favorite.product_id), (alice.id, "478253"))

    def test_authenticated_favorites_cannot_remove_another_users_item(self):
        self.login()
        self.assertEqual(self.post("/account/favorites/478253", {"user_id": "2", "next": "https://example.test/"}).location, "/account/favorites")
        other = self.app.test_client()
        self.login(other, email="bob.c@test.com")
        _, context = self.rendered("/account/favorites", other)
        self.assertEqual(context["products"], [])
        self.post("/account/favorites/478253", client=other)
        self.post("/account/favorites/478253", client=other)
        self.assertEqual(self.count(self.site.Favorite), 1)
        self.assertEqual(self.post("/account/favorites/not-real").status_code, 404)
        _, context = self.rendered("/account/favorites")
        self.assertEqual([p.id for p in context["products"]], ["478253"])

    def test_registration_validation_case_insensitive_uniqueness_and_hashing(self):
        fields = {"first_name": "Regression", "last_name": "User", "email": "regression@example.test", "password": "LocalTest123!"}
        for update in ({"password": "short"}, {"email": "bad-email"}, {"first_name": ""}):
            self.assertEqual(self.post("/account-registration/look-up", {**fields, **update}).status_code, 200)
            self.assertEqual(self.count(self.site.User), 4)
        self.assertEqual(self.post("/account-registration/look-up", fields).status_code, 302)
        with self.app.app_context():
            user = self.site.User.query.filter_by(email=fields["email"]).one()
            self.assertNotEqual(user.password_hash, fields["password"])
            self.assertTrue(check_password_hash(user.password_hash, fields["password"]))
        self.assertEqual(self.post("/account-registration/look-up", {**fields, "email": fields["email"].upper()}).status_code, 200)
        self.assertEqual(self.count(self.site.User), 5)
        self.assertIn(fields["email"], self.client.get("/account/dashboard").get_data(as_text=True))

    def test_profile_ignores_email_and_user_id_and_rolls_back_invalid_input(self):
        self.login()
        self.assertEqual(self.post("/account/profile", {"first_name": "Updated", "last_name": "User", "phone": "202-555-0151", "email": "changed@example.test", "user_id": "2"}).status_code, 302)
        self.assertEqual(self.post("/account/profile", {"first_name": "Should Roll Back", "last_name": "", "phone": "202-555-0000"}).status_code, 200)
        with self.app.app_context():
            user = self.site.User.query.filter_by(email="alice.j@test.com").one()
            self.assertEqual(user.first_name, "Updated")
            self.assertEqual(user.phone, "202-555-0151")
            self.assertIsNone(self.site.User.query.filter_by(email="changed@example.test").first())
            self.assertEqual(self.site.User.query.filter_by(email="bob.c@test.com").one().first_name, "Bob")

    def test_login_and_other_redirects_cannot_leave_the_mirror(self):
        unsafe = ("https://example.test/", "//example.test/", "/\\example.test/", "/\nLocation: https://example.test", "javascript:alert(1)")
        for value in unsafe:
            with self.subTest(value=value):
                self.assertEqual(self.site.local_next(value, "/account/dashboard"), "/account/dashboard")
        response = self.login(next="//example.test/")
        self.assertEqual(response.location, "/account/dashboard")
        self.post("/logout")
        self.assertEqual(self.login(next="/shop?x=1#catalog").location, "/shop?x=1#catalog")

    def test_private_pages_security_headers_and_reference_boundary(self):
        response = self.client.get("/rx/dotm/cart")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("form-action 'self'", response.headers["Content-Security-Policy"])
        self.assertIn("connect-src 'self'", response.headers["Content-Security-Policy"])
        response = self.client.get("/reference?destination=javascript:alert(1)")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("javascript:alert", response.get_data(as_text=True))
        self.assertEqual(self.client.get("/account/order/order-history").status_code, 302)

    def test_initialization_and_seed_functions_are_byte_identical_noops(self):
        before = self.site.DB_PATH.read_bytes()
        for _ in range(3):
            with self.app.app_context():
                self.site.initialize_database()
                self.seed.seed_database()
                self.seed.seed_benchmark_users()
                self.site.db.session.remove()
                self.site.db.engine.dispose()
            self.assertEqual(self.site.DB_PATH.read_bytes(), before)
        self.client.get("/_health")
        self.client.get("/")
        self.assertEqual(self.site.DB_PATH.read_bytes(), before)

    def test_fresh_process_boot_preserves_a_copied_seed_byte_for_byte(self):
        boot = self.root / "boot-copy"
        boot.mkdir(exist_ok=True)
        copied = boot / "cvs.db"
        shutil.copyfile(self.baseline, copied)
        before = hashlib.sha256(copied.read_bytes()).hexdigest()
        environment = os.environ.copy()
        environment["CVS_INSTANCE_PATH"] = str(boot)
        environment["PYTHONPATH"] = str(SITE)
        result = subprocess.run([sys.executable, "-c", "import app; print(app.app.test_client().get('/_health').status_code)"],
                                cwd=SITE, env=environment, capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "200")
        self.assertEqual(hashlib.sha256(copied.read_bytes()).hexdigest(), before)


if __name__ == "__main__":
    unittest.main()
