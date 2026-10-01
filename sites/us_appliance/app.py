#!/usr/bin/env python3
"""US Appliance mirror — Flask application.

Mirrors https://www.us-appliance.com/ (BigCommerce storefront, appliance
e-commerce): category landing pages with "Shop by" tiles and faceted product
grids (brand / price / on-sale filters, sort, pagination), keyword search with
Products / News & Information tabs and the advanced-search form, product pages
with galleries, model codes, Now/Was pricing, availability ZIP check, color
variants and frequently-bought-together rails, cart with free-shipping
threshold rules, guest + account checkout with delivery options, account area
with order history, order tracking by order number/email plus carrier links,
brand zones, deals, manufacturer rebates, financing offers, delivery info,
ShopperApproved customer reviews, buying guides, FAQ and the customer-service
hub.

All runtime content comes from the SQLite seed DB built by seed_data.py from
the frozen source_data_*.json snapshots captured from www.us-appliance.com on
2026-09-28/29 (see provenance.json). No handler reads scraped JSON at request
time.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from datetime import date, datetime, timedelta

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from markupsafe import Markup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, instance_path=os.path.join(BASE_DIR, "instance"))
app.config["SECRET_KEY"] = os.environ.get("US_APPLIANCE_SECRET_KEY",
                                          "webharbor-us_appliance-dev-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "US_APPLIANCE_DB_URI",
    f"sqlite:///{BASE_DIR}/instance/us_appliance.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["WTF_CSRF_TIME_LIMIT"] = None

os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)

db = SQLAlchemy(app)

# CSRF protection (same WebHarbor convention as the other recent mirror
# sites): every state-changing POST form carries a flask-wtf token; the
# read-only ZIP availability JSON endpoint is exempted like the AJAX
# endpoints on allrecipes / amazon.
csrf = CSRFProtect(app)

# Frozen snapshot date: every relative label is computed against it so pages
# render identically at any time.
MIRROR_TODAY = date(2026, 9, 29)
PASSWORD_NAMESPACE = "webharbor-us_appliance"
PASSWORD = "TestPass123!"

PAGE_SIZE = 12

# Per-page <title> overrides captured verbatim from the upstream site
# (www.us-appliance.com, 2026-09-28/29 snapshot). Upstream serves a unique
# SEO title per page; these are the ones for the task-relevant category
# landing/grids. Pages not listed keep the site-wide default title.
CATEGORY_PAGE_TITLES = {
    "cooking": "Big Selection of Ranges, Cooktops, Ovens and more",
    "refrigeration": ("Best Refrigerators 2026: Shop French Door, "
                      "Counter-Depth & Smart Fridges | US-Appliance"),
    "laundry": "Best Washers and Dryers 2026 | Laundry",
    "appliance-packages": "Appliance Packages | Bundled Kitchen Appliances",
    "gas-ranges": ('Gas Ranges for Sale | 30", 36" & Pro-Style | '
                   'Top Brands | US Appliance'),
    "electric-ranges": ("Electric Ranges for Sale | Freestanding, Slide-In "
                        "& Double Oven | US Appliance"),
    "dishwasher": "Best Dishwashers 2026: Buy Dishwashers Online at Best Prices",
    "frdore": ("Best French Door Refrigerators 2026: Shop 3-Door, 4-Door "
               "& Counter-Depth | US-Appliance"),
    "sidebyside": ("Side by Side Refrigerators | Side by Side Fridge | "
                   "Refrigerators"),
    "front-load": "Front Loads - US Appliance",
    "top-load": "Top Loads - US Appliance",
}

# Upstream <title> for each buying-guide detail page (frozen capture).
GUIDE_PAGE_TITLES = {
    "refrigerator": "Kitchen Refrigerator Buying Guide",
    "range": "Kitchen Range Buying Guide",
    "dishwasher": "Dishwasher Buying Guide",
    "wallovon": "Kitchen wall oven buying guide",
    "cooktop": "Kitchen cooktops buying guide",
    "microwave": "microwave buying guide",
    "washer": "Washer Buying Guide",
    "dryer": "Dryer Buying Guide",
    "venthood": "Kitchen ventilation buying guide",
}

# ---- captured upstream business rules (freedelivery/faq pages) --------------
FREE_SHIPPING_THRESHOLD = 999      # major appliance orders >= $999 ship free
UNDER_THRESHOLD_SHIPPING = 99      # orders under $999: flat $99
IN_HOME_DELIVERY = 199             # in-home delivery upgrade per order
SALE_ENDS = "Sale ends Sept 30"    # captured promo-message on sale items
MI_TAX_RATE = 0.06                 # sales tax charged for MI deliveries


def stable_password_hash(raw_password: str) -> str:
    digest = hashlib.sha256()
    digest.update(f"{PASSWORD_NAMESPACE}:{raw_password}".encode("utf-8"))
    return digest.hexdigest()


def money(value):
    if value is None:
        return ""
    return f"${value:,.2f}"


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(160), unique=True, nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    is_brand = db.Column(db.Boolean, default=False)
    position = db.Column(db.Integer, default=0)
    blurb = db.Column(db.Text, default="")
    tile_groups = db.Column(db.Text, default="[]")   # JSON landing tiles

    parent = db.relationship("Category", remote_side=[id],
                             backref="children")

    def tile_groups_list(self):
        try:
            return json.loads(self.tile_groups or "[]")
        except ValueError:
            return []

    def landing_image(self):
        for grp in self.tile_groups_list():
            for item in grp["items"]:
                if item["href"].strip("/").replace(".html", "") == self.slug:
                    return item["img_local"]
        for grp in self.tile_groups_list():
            if grp["items"]:
                return grp["items"][0]["img_local"]
        return ""

    def descendant_ids(self):
        out = [self.id]
        for child in self.children:
            out.extend(child.descendant_ids())
        return out


class Brand(db.Model):
    __tablename__ = "brands"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    product_count = db.Column(db.Integer, default=0)


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(400), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    sku = db.Column(db.String(120), default="")
    mpn = db.Column(db.String(120), default="")
    brand = db.Column(db.String(120), default="", index=True)
    price = db.Column(db.Float)                    # None -> hidden (call/us)
    retail_price = db.Column(db.Float)             # "Was" price when on sale
    availability = db.Column(db.String(40), default="Available")
    in_stock = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text, default="")   # features HTML (captured)
    blurb = db.Column(db.String(500), default="")
    width = db.Column(db.Float)
    height = db.Column(db.Float)
    depth = db.Column(db.Float)
    weight = db.Column(db.Float)
    color = db.Column(db.String(120), default="")
    promo_message = db.Column(db.String(200), default="")
    promo_under = db.Column(db.String(300), default="")
    badge = db.Column(db.String(60), default="")
    pdf_name = db.Column(db.String(200), default="")
    pdf_link = db.Column(db.String(300), default="")
    free_shipping = db.Column(db.Boolean, default=False)
    zip_availability = db.Column(db.Boolean, default=False)
    pageviews = db.Column(db.Integer, default=0)
    review_count = db.Column(db.Integer, default=0)
    rating_sum = db.Column(db.Integer, default=0)
    card_image = db.Column(db.String(200), default="")
    gallery = db.Column(db.Text, default="[]")     # JSON [local paths]
    color_options = db.Column(db.Text, default="[]")  # JSON sibling slugs
    position = db.Column(db.Integer, default=0)

    category_ids = db.Column(db.Text, default="[]")   # JSON [cat ids]

    def gallery_list(self):
        try:
            return json.loads(self.gallery or "[]")
        except ValueError:
            return []

    def color_options_list(self):
        try:
            return json.loads(self.color_options or "[]")
        except ValueError:
            return []

    def category_id_list(self):
        try:
            return json.loads(self.category_ids or "[]")
        except ValueError:
            return []

    @property
    def is_available(self):
        return self.availability == "Available"

    @property
    def savings(self):
        if self.price is not None and self.retail_price \
                and self.retail_price > self.price:
            return round(self.retail_price - self.price, 2)
        return 0.0

    @property
    def on_sale(self):
        return self.savings > 0

    def rating(self):
        if self.review_count and self.rating_sum:
            return round(self.rating_sum / self.review_count, 1)
        return 0.0


class ProductRelated(db.Model):
    __tablename__ = "product_related"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"),
                            nullable=False, index=True)
    related_id = db.Column(db.Integer, nullable=False)
    position = db.Column(db.Integer, default=0)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(160), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(120), default="")
    phone = db.Column(db.String(40), default="")
    created_on = db.Column(db.Date, default=MIRROR_TODAY)


class CartItem(db.Model):
    __tablename__ = "cart_items"
    id = db.Column(db.Integer, primary_key=True)
    cart_token = db.Column(db.String(64), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"),
                           nullable=False)
    qty = db.Column(db.Integer, default=1)
    added = db.Column(db.Integer, default=0)

    product = db.relationship("Product")


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    email = db.Column(db.String(160), nullable=False)
    ship_name = db.Column(db.String(120), default="")
    ship_address = db.Column(db.String(200), default="")
    ship_city = db.Column(db.String(80), default="")
    ship_state = db.Column(db.String(4), default="")
    ship_zip = db.Column(db.String(12), default="")
    phone = db.Column(db.String(40), default="")
    status = db.Column(db.String(30), default="Processing")
    shipping_method = db.Column(db.String(40), default="Standard Delivery")
    shipping_cost = db.Column(db.Float, default=0.0)
    subtotal = db.Column(db.Float, default=0.0)
    tax = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    carrier = db.Column(db.String(60), default="")
    tracking = db.Column(db.String(60), default="")
    placed_on = db.Column(db.Date, default=MIRROR_TODAY)
    eta = db.Column(db.Date)
    financing = db.Column(db.String(60), default="")

    items = db.relationship("OrderItem", backref="order",
                            order_by="OrderItem.id")
    events = db.relationship("OrderEvent", backref="order",
                              order_by="OrderEvent.id")

    def step_label(self):
        return {
            "Processing": "Order Placed",
            "Prepared": "Order Prepared",
            "Shipped": "Shipped",
            "In Transit": "In Transit",
            "Out for Delivery": "Out for Delivery",
            "Delivered": "Delivered",
            "Cancelled": "Cancelled",
        }.get(self.status, self.status)


class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"),
                         nullable=False, index=True)
    product_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(400), default="")
    qty = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, default=0.0)


class OrderEvent(db.Model):
    __tablename__ = "order_events"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"),
                         nullable=False, index=True)
    step = db.Column(db.String(40), default="")
    happened_on = db.Column(db.Date)
    note = db.Column(db.String(200), default="")


class MerchantReview(db.Model):
    __tablename__ = "merchant_reviews"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), default="")
    review_date = db.Column(db.String(20), default="")
    rating = db.Column(db.Float, default=5.0)
    comments = db.Column(db.Text, default="")
    verified = db.Column(db.Boolean, default=True)
    service_rating = db.Column(db.Float)
    delivery_rating = db.Column(db.Float)
    price_rating = db.Column(db.Float)
    product_rating = db.Column(db.Float)


class Rebate(db.Model):
    __tablename__ = "rebates"
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(80), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    expires = db.Column(db.String(40), default="")
    pdf = db.Column(db.String(300), default="")


class BuyingGuide(db.Model):
    __tablename__ = "buying_guides"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(60), unique=True, nullable=False)
    title = db.Column(db.String(120), nullable=False)
    body = db.Column(db.Text, default="")


class FaqItem(db.Model):
    __tablename__ = "faq_items"
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(300), nullable=False)
    answer = db.Column(db.Text, default="")
    links_json = db.Column(db.Text, default="[]")

    def links(self):
        try:
            return json.loads(self.links_json or "[]")
        except ValueError:
            return []


class ContentBlock(db.Model):
    __tablename__ = "content_blocks"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    payload = db.Column(db.Text, default="{}")

    def data(self):
        try:
            return json.loads(self.payload or "{}")
        except ValueError:
            return {}


class PriceMatchRequest(db.Model):
    __tablename__ = "price_match_requests"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), default="")
    email = db.Column(db.String(160), default="")
    phone = db.Column(db.String(40), default="")
    product = db.Column(db.String(300), default="")
    competitor = db.Column(db.String(160), default="")
    competitor_price = db.Column(db.Float, default=0.0)
    url = db.Column(db.String(400), default="")
    created_on = db.Column(db.Date, default=MIRROR_TODAY)


class NewsletterSubscriber(db.Model):
    __tablename__ = "newsletter_subscribers"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(160), nullable=False)
    created_on = db.Column(db.Date, default=MIRROR_TODAY)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def get_content(key, default=None):
    block = ContentBlock.query.filter_by(key=key).first()
    if block:
        return block.data()
    return default if default is not None else {}


def cart_token() -> str:
    token = session.get("cart_token")
    if not token:
        token = hashlib.sha256(
            f"cart:{os.urandom(16).hex()}".encode()).hexdigest()[:32]
        session["cart_token"] = token
    return token


def current_user():
    uid = session.get("uid")
    if not uid:
        return None
    return db.session.get(User, uid)


def cart_items():
    """Cart rows for the current session/user (user cart wins when logged in)."""
    user = current_user()
    if user:
        return CartItem.query.filter(
            (CartItem.user_id == user.id) |
            ((CartItem.cart_token == cart_token())
             & (CartItem.user_id.is_(None)))).all()
    return CartItem.query.filter_by(cart_token=cart_token(),
                                    user_id=None).all()


def cart_summary(items):
    subtotal = 0.0
    count = 0
    for row in items:
        if row.product.price is not None:
            subtotal += row.product.price * row.qty
        count += row.qty
    qualifies = any(p.free_shipping for p in
                    [r.product for r in items]) or subtotal >= FREE_SHIPPING_THRESHOLD
    shipping = 0.0 if (qualifies or not items) else float(UNDER_THRESHOLD_SHIPPING)
    return {"items": items, "count": count, "subtotal": round(subtotal, 2),
            "shipping": shipping, "qualifies": qualifies}


def scored_search(query, rows, fields):
    words = [w for w in re.split(r"[^a-z0-9]+", query.lower()) if w]
    out = []
    for row in rows:
        if isinstance(row, dict):
            text = " ".join(str(row.get(f) or "").lower() for f in fields)
            key = row.get("id") or row.get("title")
        else:
            text = " ".join(str(getattr(row, f) or "").lower() for f in fields)
            key = row.id
        score = sum(1 for w in words if w in text)
        if score:
            out.append((score, key, row))
    out.sort(key=lambda sr: (-sr[0], str(sr[1])))
    return [r for _, _, r in out]


def next_order_number():
    last = Order.query.order_by(Order.id.desc()).first()
    if not last:
        return 10001
    try:
        return max(int(re.sub(r"\D", "", last.number) or 10000), last.id) + 1
    except ValueError:
        return 10001


# --------------------------------------------------------------------------- #
# Template context
# --------------------------------------------------------------------------- #
@app.context_processor
def inject_globals():
    top_categories = Category.query.filter_by(parent_id=None) \
        .order_by(Category.position).all()
    for cat in top_categories:
        cat.kids = Category.query.filter_by(parent_id=cat.id) \
            .order_by(Category.position).all()
    cart = cart_summary(cart_items())
    return {
        "nav_categories": top_categories,
        "nav_brands": Brand.query.order_by(Brand.name).all(),
        "cart_count": cart["count"],
        "cart_subtotal": cart["subtotal"],
        "site_facts": get_content("site_facts", {}),
        "current_user": current_user(),
        "mirror_today": MIRROR_TODAY,
    }


app.jinja_env.globals["money"] = money


@app.template_filter("dmy")
def dmy(value):
    if not value:
        return ""
    if isinstance(value, str):
        return value
    return value.strftime("%b %-d, %Y")


# --------------------------------------------------------------------------- #
# Routes — home
# --------------------------------------------------------------------------- #
@app.route("/")
def home():
    home_data = get_content("home", {})
    deals = Product.query.filter(Product.retail_price > Product.price) \
        .filter(Product.availability == "Available") \
        .order_by((Product.retail_price - Product.price).desc()) \
        .limit(8).all()
    quickship = Product.query.filter(Product.availability == "Available") \
        .order_by(Product.pageviews.desc()).limit(8).all()
    return render_template("index.html", home=home_data, deals=deals,
                           quickship=quickship)


# --------------------------------------------------------------------------- #
# Category / brand / product pages (upstream URL shape: /<slug>.html)
# --------------------------------------------------------------------------- #
@app.route("/<slug>.html")
def page_by_slug(slug):
    slug = (slug or "").strip().strip("/")
    cat = Category.query.filter_by(slug=slug).first()
    if cat:
        return render_category(cat)
    product = Product.query.filter_by(slug=slug).first()
    if product:
        return render_product(product)
    abort(404)


def category_products(cat):
    """Products mapped to this category subtree (captured category refs)."""
    ids = cat.descendant_ids()
    rows = Product.query.filter(Product.availability == "Available") \
        .order_by(Product.position).all()
    return [p for p in rows if set(p.category_id_list()) & set(ids)]


def render_category(cat):
    products = category_products(cat)
    query = request.args.get("query") or ""
    filters = {
        "brand": request.args.getlist("brand"),
        "price_from": request.args.get("price_from", ""),
        "price_to": request.args.get("price_to", ""),
        "on_sale": request.args.get("on_sale", ""),
        "sort": request.args.get("sort", "featured"),
        "page": request.args.get("page", 1, type=int),
    }
    filtered = products
    if filters["brand"]:
        filtered = [p for p in filtered if p.brand in filters["brand"]]
    try:
        lo = float(filters["price_from"]) if filters["price_from"] else None
    except ValueError:
        lo = None
    try:
        hi = float(filters["price_to"]) if filters["price_to"] else None
    except ValueError:
        hi = None
    if lo is not None:
        filtered = [p for p in filtered if p.price is not None and p.price >= lo]
    if hi is not None:
        filtered = [p for p in filtered if p.price is not None and p.price <= hi]
    if filters["on_sale"] in ("1", "on", "today"):
        filtered = [p for p in filtered if p.on_sale]
    sort = filters["sort"]
    if sort == "priceasc":
        filtered = sorted(filtered, key=lambda p: (p.price is None, p.price or 0))
    elif sort == "pricedesc":
        filtered = sorted(filtered, key=lambda p: (p.price is None, -(p.price or 0)))
    elif sort in ("alphaasc",):
        filtered = sorted(filtered, key=lambda p: p.name.lower())
    elif sort in ("alphadesc",):
        filtered = sorted(filtered, key=lambda p: p.name.lower(), reverse=True)
    elif sort == "avgcustomerreview":
        filtered = sorted(filtered,
                          key=lambda p: (-p.rating(), -p.review_count))
    elif sort == "bestselling":
        filtered = sorted(filtered, key=lambda p: -p.pageviews)
    elif sort == "newest":
        filtered = sorted(filtered, key=lambda p: -p.id)
    page = max(1, filters["page"])
    total = len(filtered)
    pages = max(1, math.ceil(total / PAGE_SIZE))
    page = min(page, pages)
    window = filtered[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]
    brands_in_cat = sorted({p.brand for p in products if p.brand})
    crumbs = []
    node = cat
    while node:
        crumbs.insert(0, node)
        node = node.parent
    return render_template(
        "category.html", cat=cat, products=window, total=total,
        pages=pages, page=page, filters=filters,
        brands_in_cat=brands_in_cat, crumbs=crumbs,
        heading=f"{cat.name}" if not cat.parent else cat.name,
        page_title=CATEGORY_PAGE_TITLES.get(cat.slug, ""))


def render_product(product):
    related_rows = ProductRelated.query.filter_by(product_id=product.id) \
        .order_by(ProductRelated.position).all()
    related = []
    for row in related_rows:
        rel = db.session.get(Product, row.related_id)
        if rel:
            related.append(rel)
    color_variants = []
    for slug in product.color_options_list():
        variant = Product.query.filter_by(slug=slug).first()
        if variant:
            color_variants.append(variant)
    cat_node = None
    if product.category_id_list():
        cat_node = db.session.get(Category, product.category_id_list()[0])
    crumbs = []
    node = cat_node
    while node:
        crumbs.insert(0, node)
        node = node.parent
    return render_template("product.html", p=product, related=related,
                           color_variants=color_variants, crumbs=crumbs,
                           sale_ends=SALE_ENDS)


@app.route("/shopbybrand.html")
def brands_index():
    brands = Brand.query.order_by(Brand.name).all()
    rebates = {r.brand for r in Rebate.query.all()}
    return render_template("brands.html", brands=brands,
                           rebate_brands=rebates)


@app.route("/brand/<slug>")
def brand_page(slug):
    brand = Brand.query.filter_by(slug=slug).first_or_404()
    products = Product.query.filter(Product.brand == brand.name,
                                    Product.availability == "Available") \
        .order_by(Product.position).all()
    sort = request.args.get("sort", "featured")
    if sort == "priceasc":
        products.sort(key=lambda p: (p.price is None, p.price or 0, p.id))
    total = len(products)
    pages = max(1, math.ceil(total / PAGE_SIZE))
    page = min(pages, max(1, request.args.get("page", 1, type=int)))
    products = products[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]
    return render_template("brand_detail.html", brand=brand, sort=sort,
                           products=products, total=total, pages=pages, page=page)


# --------------------------------------------------------------------------- #
# Search (upstream: /search.php)
# --------------------------------------------------------------------------- #
@app.route("/search.php")
def search():
    query = (request.args.get("search_query")
             or request.args.get("search_query_adv") or "").strip()
    section = request.args.get("section", "product")
    brand = request.args.get("brand", "")
    price_from = request.args.get("price_from", "")
    price_to = request.args.get("price_to", "")
    sort = request.args.get("sort", "bestselling")
    page = max(1, request.args.get("page", 1, type=int))

    all_products = Product.query.filter(
        Product.availability == "Available").order_by(Product.position).all()
    results = scored_search(query, all_products,
                            ["name", "brand", "mpn", "blurb", "sku"]) \
        if query else all_products
    if brand:
        results = [p for p in results if p.brand == brand]
    try:
        lo = float(price_from) if price_from else None
    except ValueError:
        lo = None
    try:
        hi = float(price_to) if price_to else None
    except ValueError:
        hi = None
    if lo is not None:
        results = [p for p in results if p.price is not None and p.price >= lo]
    if hi is not None:
        results = [p for p in results if p.price is not None and p.price <= hi]
    if sort == "priceasc":
        results = sorted(results, key=lambda p: (p.price is None, p.price or 0))
    elif sort == "pricedesc":
        results = sorted(results, key=lambda p: (p.price is None, -(p.price or 0)))
    elif sort == "alphaasc":
        results = sorted(results, key=lambda p: p.name.lower())
    elif sort == "alphadesc":
        results = sorted(results, key=lambda p: p.name.lower(), reverse=True)
    elif sort == "avgcustomerreview":
        results = sorted(results, key=lambda p: (-p.rating(), -p.review_count))
    elif sort == "featured":
        results = sorted(results, key=lambda p: p.position)

    total = len(results)
    pages = max(1, math.ceil(total / PAGE_SIZE))
    page = min(page, pages)
    window = results[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]

    # content tab (News & Information): guides + FAQ entries
    guides = BuyingGuide.query.all()
    faqs = FaqItem.query.all()
    content_rows = []
    for g in guides:
        content_rows.append({"title": g.title,
                             "href": f"/guides/{g.slug}.html",
                             "text": g.body[:400]})
    for f in faqs:
        content_rows.append({"title": f.question, "href": "/faq.html",
                            "text": f.answer[:400]})
    content_hits = scored_search(query, content_rows, ["title", "text"]) \
        if query else []

    brand_names = sorted({p.brand for p in all_products if p.brand})
    return render_template(
        "search.html", query=query, section=section, results=window,
        total=total, pages=pages, page=page, brand=brand,
        price_from=price_from, price_to=price_to, sort=sort,
        content_hits=content_hits, content_total=len(content_hits),
        brand_names=brand_names)


# --------------------------------------------------------------------------- #
# Cart (upstream: /cart.php)
# --------------------------------------------------------------------------- #
@app.route("/cart.php", methods=["GET", "POST"])
def cart():
    if request.method == "POST":
        action = request.args.get("action", "")
        if action == "add":
            pid = request.form.get("product_id", type=int)
            qty = request.form.get("qty", type=int) if "qty" in request.form else 1
            if qty is None or not 1 <= qty <= 20:
                flash("Choose a quantity from 1 to 20.")
                return redirect(url_for("cart")), 400
            product = db.session.get(Product, pid) if pid else None
            if product and product.is_available:
                user = current_user()
                row = CartItem.query.filter_by(
                    cart_token=cart_token(), user_id=user.id if user else None,
                    product_id=pid).first()
                if row:
                    row.qty = min(20, row.qty + qty)
                else:
                    db.session.add(CartItem(cart_token=cart_token(),
                                            user_id=user.id if user else None,
                                            product_id=pid, qty=qty))
                db.session.commit()
                flash("The item has been added")
                return redirect(url_for("cart"))
        if action == "update":
            for row in cart_items():
                try:
                    qty = int(request.form.get(f"qty_{row.id}", row.qty))
                except ValueError:
                    qty = row.qty
                if qty <= 0:
                    db.session.delete(row)
                else:
                    row.qty = min(qty, 20)
            db.session.commit()
            return redirect(url_for("cart"))
        if action == "remove":
            rid = request.form.get("item", type=int)
            row = db.session.get(CartItem, rid) if rid else None
            if row and row in cart_items():
                db.session.delete(row)
                db.session.commit()
            return redirect(url_for("cart"))
        return redirect(url_for("cart"))
    summary = cart_summary(cart_items())
    return render_template("cart.html", summary=summary,
                           free_threshold=FREE_SHIPPING_THRESHOLD,
                           in_home=IN_HOME_DELIVERY)


# --------------------------------------------------------------------------- #
# Checkout + order confirmation
# --------------------------------------------------------------------------- #
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items = cart_items()
    if not items:
        return redirect(url_for("cart"))
    user = current_user()
    errors = {}
    form = {k: "" for k in ("name", "address", "city", "state", "zip",
                            "phone", "card_number", "card_expiry", "card_cvv",
                            "email")}
    if user:
        form["email"] = user.email
        form["name"] = user.name
    summary = cart_summary(items)
    if request.method == "POST":
        for key in form:
            form[key] = request.form.get(key, "").strip()
        shipping_method = request.form.get("shipping_method", "standard")
        financing = request.form.get("financing", "")
        errors = {}
        if shipping_method not in {"standard", "in_home"}:
            errors["shipping_method"] = "Choose a delivery method"
        if financing not in {"", "15 Months Special Financing", "6 Months Storewide Financing"}:
            errors["financing"] = "Choose an available payment option"
        if not form["name"]:
            errors["name"] = "Name is required"
        if not form["address"]:
            errors["address"] = "Address is required"
        if not form["city"]:
            errors["city"] = "City is required"
        if len(form["state"]) != 2:
            errors["state"] = "Use a 2-letter state code"
        if not re.match(r"^\d{5}$", form["zip"]):
            errors["zip"] = "Use a 5-digit ZIP"
        if not re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", form["email"]):
            errors["email"] = "Enter a valid email"
        card = re.sub(r"\D", "", form["card_number"])
        if len(card) != 16:
            errors["card_number"] = "Enter a 16-digit card number"
        if not re.match(r"^\d{2}/\d{2}$", form["card_expiry"]):
            errors["card_expiry"] = "Use MM/YY"
        if not re.match(r"^\d{3,4}$", form["card_cvv"]):
            errors["card_cvv"] = "3 or 4 digits"
        if not errors:
            in_home = shipping_method == "in_home"
            shipping_cost = float(IN_HOME_DELIVERY) if in_home \
                else summary["shipping"]
            tax = round(summary["subtotal"] * MI_TAX_RATE, 2) \
                if form["state"].upper() == "MI" else 0.0
            total = round(summary["subtotal"] + shipping_cost + tax, 2)
            order = Order(
                number=str(next_order_number()),
                user_id=user.id if user else None,
                email=form["email"], ship_name=form["name"],
                ship_address=form["address"], ship_city=form["city"],
                ship_state=form["state"].upper(), ship_zip=form["zip"],
                phone=form["phone"], status="Processing",
                shipping_method="In-Home Delivery" if in_home
                else "Standard Delivery",
                shipping_cost=shipping_cost,
                subtotal=summary["subtotal"], tax=tax, total=total,
                placed_on=MIRROR_TODAY, financing=financing)
            db.session.add(order)
            db.session.flush()
            for row in items:
                db.session.add(OrderItem(
                    order_id=order.id, product_id=row.product_id,
                    name=row.product.name, qty=row.qty,
                    price=row.product.price or 0.0))
            db.session.add(OrderEvent(order_id=order.id, step="Order Placed",
                                      happened_on=MIRROR_TODAY,
                                      note="We received your order."))
            for row in items:
                db.session.delete(row)
            db.session.commit()
            session["confirmed_order"] = order.number
            return redirect(url_for("order_confirmation",
                                    number=order.number))
    return render_template("checkout.html", summary=summary, form=form,
                           errors=errors, in_home=IN_HOME_DELIVERY,
                           free_threshold=FREE_SHIPPING_THRESHOLD)


@app.route("/order-confirmation/<number>")
def order_confirmation(number):
    order = Order.query.filter_by(number=number).first_or_404()
    user = current_user()
    if session.get("confirmed_order") != order.number and not (user and order.user_id == user.id):
        abort(404)
    return render_template("order_confirmation.html", order=order)


# --------------------------------------------------------------------------- #
# Account (upstream: /login.php, /account.php)
# --------------------------------------------------------------------------- #
@app.route("/login.php", methods=["GET", "POST"])
def login():
    action = request.args.get("action", "")
    if action == "create_account":
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            name = request.form.get("name", "").strip()
            if User.query.filter_by(email=email).first():
                flash("An account with this email already exists")
            elif not re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
                flash("Enter a valid email address")
            elif len(password) < 8:
                flash("Password must be at least 8 characters")
            else:
                user = User(email=email,
                            password_hash=stable_password_hash(password),
                            name=name or email.split("@")[0])
                db.session.add(user)
                db.session.commit()
                session["uid"] = user.id
                flash("Welcome! Your account has been created.")
                return redirect(url_for("account"))
        return render_template("register.html")
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.password_hash == stable_password_hash(password):
            session["uid"] = user.id
            # merge guest cart into the user cart
            for row in CartItem.query.filter_by(cart_token=cart_token(),
                                                user_id=None).all():
                row.user_id = user.id
            db.session.commit()
            return redirect(url_for("account"))
        flash("Wrong email or password")
        return render_template("login.html"), 401
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("uid", None)
    return redirect(url_for("home"))


@app.route("/account.php")
def account():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    orders = Order.query.filter_by(email=user.email) \
        .order_by(Order.id.desc()).all()
    return render_template("account.html", user=user, orders=orders)


@app.route("/account.php/orders/<int:order_id>")
def account_order(order_id):
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    order = db.session.get(Order, order_id)
    if not order or order.email.lower() != user.email.lower():
        abort(404)
    return render_template("order_detail.html", order=order)


# --------------------------------------------------------------------------- #
# Order tracking
# --------------------------------------------------------------------------- #
@app.route("/ordertracking.html", methods=["GET", "POST"])
def order_tracking():
    carriers = get_content("carriers", [])
    intro = get_content("order_tracking_intro", "")
    found = None
    number = request.form.get("order_number", "").strip() \
        if request.method == "POST" else ""
    email = request.form.get("email", "").strip() if request.method == "POST" else ""
    if request.method == "POST":
        order = Order.query.filter_by(number=number).first()
        if order and order.email.lower() == email.lower():
            found = order
        elif order:
            found = "mismatch"
    return render_template("ordertracking.html", carriers=carriers,
                           intro=intro, found=found, number=number,
                           email=email)


# --------------------------------------------------------------------------- #
# Availability ZIP check
# --------------------------------------------------------------------------- #
@app.route("/availability", methods=["POST"])
@csrf.exempt
def availability():
    pid = request.form.get("product_id", type=int)
    zip_code = request.form.get("zip", "").strip()
    product = db.session.get(Product, pid) if pid else None
    if not product:
        return jsonify({"ok": False, "message": "Product not found"})
    if not re.match(r"^\d{5}$", zip_code):
        return jsonify({"ok": False, "message": "Enter a 5-digit ZIP code"})
    if not product.is_available:
        return jsonify({"ok": True,
                        "message": "This item is discontinued. "
                                    "Contact us for a great deal on a "
                                    "comparable model."})
    if zip_code.startswith(("967", "968", "995", "996", "997", "998", "999", "006", "007", "008", "009")):
        return jsonify({"ok": False, "message": "We offer delivery to the "
                        "continental United States only."})
    msg = ("Good news — this item is available for delivery to your area. "
           "QUICKSHIP - Ships in 1-2 business days."
           if product.badge == "Best Seller" or product.free_shipping else
           "Good news — this item is available for delivery to your area.")
    return jsonify({"ok": True, "message": msg})


# --------------------------------------------------------------------------- #
# Static support pages
# --------------------------------------------------------------------------- #
@app.route("/faq.html")
def faq_page():
    items = FaqItem.query.order_by(FaqItem.id).all()
    return render_template("faq.html", items=items)


@app.route("/cusser.html")
def customer_service():
    hub = get_content("customer_service_hub", [])
    return render_template("customer_service.html", hub=hub)


@app.route("/freedelivery.html")
def delivery_page():
    data = get_content("delivery", {})
    return render_template("delivery.html", d=data,
                           threshold=FREE_SHIPPING_THRESHOLD,
                           in_home=IN_HOME_DELIVERY)


@app.route("/rebates.html")
def rebates_page():
    rows = Rebate.query.order_by(Rebate.brand, Rebate.id).all()
    by_brand = {}
    for r in rows:
        by_brand.setdefault(r.brand, []).append(r)
    return render_template("rebates.html",
                           by_brand=sorted(by_brand.items()))


@app.route("/financecenter.html")
def finance_center():
    intro = get_content("finance_center_intro", "")
    offers = get_content("finance_offers", [])
    return render_template("finance_center.html", intro=intro, offers=offers)


@app.route("/financeoffers.html")
def finance_offers():
    offers = get_content("finance_offers", [])
    steps = get_content("finance_steps", [])
    return render_template("finance_offers.html", offers=offers, steps=steps)


@app.route("/testimonials.html")
def testimonials():
    page = max(1, request.args.get("page", 1, type=int))
    per_page = 20
    total = MerchantReview.query.count()
    pages = max(1, math.ceil(total / per_page))
    page = min(page, pages)
    rows = MerchantReview.query.order_by(MerchantReview.id.desc()) \
        .offset((page - 1) * per_page).limit(per_page).all()
    meta = get_content("reviews_meta", {})
    avg = 0.0
    if total:
        avg = round(sum(r.rating for r in rows) / len(rows), 1)
    return render_template("testimonials.html", reviews=rows, meta=meta,
                           pages=pages, page=page, total=total, avg=avg)


@app.route("/buyingguide.html")
def buying_guides():
    guides = BuyingGuide.query.order_by(BuyingGuide.id).all()
    intro = get_content("buying_guides_intro", "")
    return render_template("guides.html", guides=guides, intro=intro)


@app.route("/guides/<slug>.html")
def buying_guide(slug):
    guide = BuyingGuide.query.filter_by(slug=slug).first_or_404()
    return render_template("guide_detail.html", guide=guide,
                           page_title=GUIDE_PAGE_TITLES.get(guide.slug, ""))


@app.route("/contactus2.html")
def contact():
    return render_template("contact.html", data=get_content("contact", {}))


@app.route("/us-appliance-warranties.html")
def us_warranty_landing():
    # Upstream target of the FAQ warranty answer's "More details" link
    # (https://www.us-appliance.com/us-appliance-warranties.html): a short
    # landing page whose whole body is a single line, mirrored verbatim.
    # Hardcoded here (not a content_blocks row) so the frozen seed stays
    # byte-identical.
    return render_template("text_page.html", title="US Appliance Warranties",
                          page_title="US Appliance Warranties",
                          text="Learn More about US Appliance warranties")


# Upstream support pages reachable from the Customer Service hub and the
# FAQ installation answer (audit-rail dead-link crawl findings). Mirrored
# verbatim (upstream body HTML incl. legacy name anchors) as templates; no
# seed/content_blocks change so the frozen seed stays byte-identical.
@app.route("/orderinformation.html")
def ordering_information():
    return render_template("support_orderinformation.html")


@app.route("/info.html")
def about_info():
    return render_template("support_info.html")


@app.route("/privacypolicy.html")
def privacy_policy():
    return render_template("support_privacypolicy.html")


@app.route("/security1.html")
def secure_shopping():
    return render_template("support_security1.html")


@app.route("/aftersaleshelp.html")
def after_sales_help():
    return render_template("support_aftersaleshelp.html")


@app.route("/product-recalls.html")
def product_recalls():
    return render_template("support_product_recalls.html")


@app.route("/major-appliance-delivery-and-installation-guide/")
def major_appliance_guide():
    return render_template("support_major_guide.html")


@app.route("/price-match-request.html", methods=["GET", "POST"])
def price_match():
    if request.method == "POST":
        req = PriceMatchRequest(
            name=request.form.get("name", "").strip(),
            email=request.form.get("email", "").strip(),
            phone=request.form.get("phone", "").strip(),
            product=request.form.get("product", "").strip(),
            competitor=request.form.get("competitor", "").strip(),
            competitor_price=request.form.get("price", 0.0, type=float),
            url=request.form.get("url", "").strip())
        db.session.add(req)
        db.session.commit()
        return render_template("price_match.html", submitted=True,
                               req=req)
    return render_template("price_match.html", submitted=False, req=None)


def _text_page(key, title, page_title=""):
    return render_template("text_page.html", title=title,
                           text=get_content(key, ""),
                           page_title=page_title or title)


@app.route("/returninformation.html")
def returns_page():
    return _text_page("returns_text", "Returns", "Returns")


@app.route("/whyusappliance.html")
def why_us():
    return _text_page("why_us_text", "Why Shop US Appliance",
                      "Shop US Appliance for the Lowest Online Prices")


@app.route("/warrantyoptions.html")
def warranty_page():
    return _text_page("warranty_text", "US Appliance Service Plans",
                      "US Appliance Service Plans - US Appliance")


@app.route("/in-stock-message-2.html")
def instock_page():
    return _text_page("instock_text", "Stock Item", "Stock Item")


@app.route("/salestaxinfo.html")
def salestax_page():
    return _text_page("salestax_text", "Sales Tax Information",
                      "Sales Tax Information")


@app.route("/clearance.html")
def clearance_page():
    deals = Product.query.filter(Product.retail_price > Product.price) \
        .filter(Product.availability == "Available") \
        .order_by((Product.retail_price - Product.price).desc()).limit(12).all()
    return render_template("clearance.html", text=get_content("clearance_text", ""),
                           deals=deals)


@app.route("/hugepricecuts.html")
def deals_page():
    data = get_content("deals", {})
    deals = Product.query.filter(Product.retail_price > Product.price) \
        .filter(Product.availability == "Available") \
        .order_by((Product.retail_price - Product.price).desc()).limit(24).all()
    return render_template("deals.html", d=data, deals=deals)


@app.route("/newsletter", methods=["POST"])
def newsletter():
    email = request.form.get("nl_email", "").strip().lower()
    if re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) and \
            not NewsletterSubscriber.query.filter_by(email=email).first():
        db.session.add(NewsletterSubscriber(email=email))
        db.session.commit()
        flash("Thanks! You are signed up for deals and offers.")
    return redirect(request.form.get("next") or url_for("home"))


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #
@app.route("/_health")
def health():
    try:
        counts = {
            "ok": True,
            "site": "us_appliance",
            "products": Product.query.count(),
            "categories": Category.query.count(),
            "brands": Brand.query.count(),
            "reviews": MerchantReview.query.count(),
            "rebates": Rebate.query.count(),
            "guides": BuyingGuide.query.count(),
            "faq": FaqItem.query.count(),
            "users": User.query.count(),
            "orders": Order.query.count(),
        }
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(exc)}), 500
    return jsonify(counts)


# --------------------------------------------------------------------------- #
# 404
# --------------------------------------------------------------------------- #
@app.errorhandler(404)
def not_found(_err):
    return render_template("404.html"), 404


# --------------------------------------------------------------------------- #
# Bootstrap
# --------------------------------------------------------------------------- #
def create_schema():
    """Create every table in a fixed, dependency-valid order.

    SQLAlchemy's metadata.sorted_tables breaks ties non-deterministically
    across processes, which shifts SQLite root-page assignment and breaks
    byte-reproducible seed builds. Iterating db.metadata.tables (definition
    order, which is already FK-topological for this app) keeps the table DDL
    sequence identical on every build.

    Explicit secondary indexes are emitted in the parent column's
    definition order for the same reason: ``Table.indexes`` iterates in
    object-identity order that varies per process (e.g. ix_products_slug /
    ix_products_brand swap root pages across builds), which would otherwise
    make the seed file non-byte-reproducible despite PYTHONHASHSEED=0.
    """
    from sqlalchemy.schema import CreateTable, CreateIndex
    with db.engine.begin() as conn:
        from sqlalchemy import inspect
        inspector = inspect(conn)
        existing = set(inspector.get_table_names())
        for table in db.metadata.tables.values():
            if table.name in existing:
                continue
            conn.execute(CreateTable(table))
            col_pos = {c.name: i for i, c in enumerate(table.columns)}
            for idx in sorted(table.indexes,
                              key=lambda ix: min(col_pos[c.name]
                                                 for c in ix.columns)):
                conn.execute(CreateIndex(idx))


def seed_database():
    if Product.query.count() > 0:
        return
    from seed_data import build_seed
    build_seed(db)


def seed_benchmark_users():
    if User.query.count() > 0:
        return
    from seed_data import build_benchmark_users
    build_benchmark_users(db)


BOOTSTRAP = os.environ.get("WEBSYN_SKIP_BOOTSTRAP") != "1"
if BOOTSTRAP:
    with app.app_context():
        create_schema()
        seed_database()
        seed_benchmark_users()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 40125)),
            debug=False, use_reloader=False)
