"""CVS offline research mirror with source-backed data and local demo shopping."""
from __future__ import annotations

import math
import os
import re
import secrets
import shutil
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError
from sqlalchemy import CheckConstraint, UniqueConstraint, func, or_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = Path(os.environ.get("CVS_INSTANCE_PATH", str(BASE_DIR / "instance"))).resolve()
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = INSTANCE_DIR / "cvs.db"
SEED_PATH = BASE_DIR / "instance_seed" / "cvs.db"
if not DB_PATH.exists() and SEED_PATH.is_file() and os.environ.get("CVS_SEED_FROM_SOURCE") != "1":
    shutil.copyfile(SEED_PATH, DB_PATH)

app = Flask(__name__, instance_path=str(INSTANCE_DIR))
app.config.update(
    SECRET_KEY=os.environ.get("CVS_SECRET_KEY", "webharbor-cvs-offline-benchmark-secret-v1"),
    SQLALCHEMY_DATABASE_URI="sqlite:///" + str(DB_PATH),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    MAX_CONTENT_LENGTH=1024 * 1024,
    WTF_CSRF_TIME_LIMIT=None,
)
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


class SnapshotMeta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference_date = db.Column(db.String(10), nullable=False, default="2026-09-28")
    home_assets = db.Column(db.JSON, nullable=False, default=dict)
    source_revision = db.Column(db.String(100), nullable=True)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(32), nullable=False, default="")


class Category(db.Model):
    slug = db.Column(db.String(100), primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    path = db.Column(db.String(500), unique=True, nullable=False)
    image_path = db.Column(db.String(500), nullable=False, default="")


class Product(db.Model):
    id = db.Column(db.String(100), primary_key=True)
    name = db.Column(db.String(600), nullable=False)
    brand = db.Column(db.String(200), nullable=False, default="")
    category_slug = db.Column(db.String(100), db.ForeignKey("category.slug"), nullable=False)
    path = db.Column(db.String(1000), unique=True, nullable=False)
    price_cents = db.Column(db.Integer, nullable=True)
    price_min_cents = db.Column(db.Integer, nullable=True)
    price_max_cents = db.Column(db.Integer, nullable=True)
    price_text = db.Column(db.String(200), nullable=False, default="Price not captured")
    rating = db.Column(db.Float, nullable=True)
    review_count = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text, nullable=False, default="")
    details = db.Column(db.JSON, nullable=False, default=list)
    features = db.Column(db.JSON, nullable=False, default=list)
    image_paths = db.Column(db.JSON, nullable=False, default=list)
    source_url = db.Column(db.Text, nullable=False)
    captured_at = db.Column(db.String(50), nullable=False, default="")
    detail_status = db.Column(db.String(50), nullable=False, default="listing_only")
    variants = db.relationship("Variant", backref="product", lazy="select", order_by="Variant.id")
    __table_args__ = (CheckConstraint("price_cents IS NULL OR price_cents >= 0"),)

    @property
    def primary_image(self):
        return self.image_paths[0] if self.image_paths else ""

    @property
    def purchasable(self):
        return any(v.price_cents is not None for v in self.variants) if self.variants else self.price_cents is not None


class Variant(db.Model):
    id = db.Column(db.String(150), primary_key=True)
    product_id = db.Column(db.String(100), db.ForeignKey("product.id"), nullable=False)
    label = db.Column(db.String(300), nullable=False)
    price_cents = db.Column(db.Integer, nullable=True)
    source_sku = db.Column(db.String(150), nullable=True)
    __table_args__ = (CheckConstraint("price_cents IS NULL OR price_cents >= 0"),)


class Store(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(300), nullable=False)
    path = db.Column(db.String(1000), unique=True, nullable=False)
    address = db.Column(db.String(500), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(2), nullable=False)
    postal_code = db.Column(db.String(12), nullable=False)
    phone = db.Column(db.String(40), nullable=False)
    store_type = db.Column(db.String(100), nullable=False, default="")
    services = db.Column(db.JSON, nullable=False, default=list)
    store_hours = db.Column(db.JSON, nullable=False, default=list)
    pharmacy_hours = db.Column(db.JSON, nullable=False, default=list)
    pharmacy_lunch = db.Column(db.String(150), nullable=True)
    nearby_ids = db.Column(db.JSON, nullable=False, default=list)
    nearby_stores = db.Column(db.JSON, nullable=False, default=list)
    about_text = db.Column(db.Text, nullable=False, default="")
    source_url = db.Column(db.Text, nullable=False)
    captured_at = db.Column(db.String(50), nullable=False, default="")


class Page(db.Model):
    slug = db.Column(db.String(150), primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    path = db.Column(db.String(1000), unique=True, nullable=False)
    body_html = db.Column(db.Text, nullable=False)
    source_url = db.Column(db.Text, nullable=False)
    captured_at = db.Column(db.String(50), nullable=False, default="")


class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    recipient = db.Column(db.String(160), nullable=False)
    line1 = db.Column(db.String(200), nullable=False)
    line2 = db.Column(db.String(200), nullable=False, default="")
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(2), nullable=False)
    postal_code = db.Column(db.String(12), nullable=False)
    label = db.Column(db.String(50), nullable=False, default="Home")

    def as_dict(self):
        return {key: getattr(self, key) for key in ("recipient", "line1", "line2", "city", "state", "postal_code")}


class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.String(100), db.ForeignKey("product.id"), nullable=False)
    __table_args__ = (UniqueConstraint("user_id", "product_id"),)


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    guest_token = db.Column(db.String(100), nullable=True)
    product_id = db.Column(db.String(100), db.ForeignKey("product.id"), nullable=False)
    variant_id = db.Column(db.String(150), db.ForeignKey("variant.id"), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    product = db.relationship(Product)
    variant = db.relationship(Variant)
    __table_args__ = (
        CheckConstraint("quantity BETWEEN 1 AND 20"),
        CheckConstraint("(user_id IS NULL AND guest_token IS NOT NULL) OR (user_id IS NOT NULL AND guest_token IS NULL)"),
    )


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(80), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    guest_token = db.Column(db.String(100), nullable=True)
    placed_at = db.Column(db.String(40), nullable=False)
    status = db.Column(db.String(60), nullable=False, default="Demo order placed")
    items = db.Column(db.JSON, nullable=False)
    subtotal_cents = db.Column(db.Integer, nullable=False)
    shipping_cents = db.Column(db.Integer, nullable=False)
    total_cents = db.Column(db.Integer, nullable=False)
    fulfillment = db.Column(db.String(20), nullable=False)
    store_address = db.Column(db.String(600), nullable=True)
    address = db.Column(db.JSON, nullable=True)
    email = db.Column(db.String(254), nullable=False)
    __table_args__ = (CheckConstraint("(user_id IS NULL AND guest_token IS NOT NULL) OR (user_id IS NOT NULL AND guest_token IS NULL)"),)


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


@app.template_filter("money")
def money(cents):
    return "Price not captured" if cents is None else f"${cents / 100:,.2f}"


def local_next(candidate, fallback="/"):
    if not candidate or not candidate.startswith("/") or candidate.startswith("//"):
        return fallback
    if "\\" in candidate or any(ord(c) < 32 for c in candidate):
        return fallback
    parsed = urlsplit(candidate)
    return candidate if not parsed.scheme and not parsed.netloc else fallback


def guest_token():
    if "guest_token" not in session:
        session["guest_token"] = secrets.token_urlsafe(32)
    return session["guest_token"]


def owned_cart_query():
    if current_user.is_authenticated:
        return CartItem.query.filter_by(user_id=current_user.id)
    return CartItem.query.filter_by(user_id=None, guest_token=guest_token())


def cart_rows():
    items = []
    subtotal = 0
    for row in owned_cart_query().order_by(CartItem.id).all():
        price = row.variant.price_cents if row.variant else row.product.price_cents
        if price is None:
            abort(409, description="This cart item no longer has a captured price. Remove it before checking out.")
        line_cents = price * row.quantity
        subtotal += line_cents
        items.append({"record": row, "product": row.product, "variant": row.variant, "line_cents": line_cents})
    return items, subtotal


def totals(subtotal, fulfillment="shipping"):
    shipping = 0 if fulfillment == "pickup" or subtotal == 0 or subtotal >= 3500 else 499
    return {"subtotal_cents": subtotal, "shipping_cents": shipping, "total_cents": subtotal + shipping}


def quantity_from_form():
    try:
        quantity = int(request.form.get("quantity", "1"))
    except (ValueError, TypeError):
        abort(400, description="Quantity must be an integer from 1 to 20.")
    if not 1 <= quantity <= 20:
        abort(400, description="Quantity must be from 1 to 20.")
    return quantity


def form_text(key, maximum, required=True):
    value = request.form.get(key, "").strip()
    if (required and not value) or len(value) > maximum:
        raise ValueError(f"Enter a valid {key.replace('_', ' ')}.")
    return value


def valid_email(value):
    return bool(len(value) <= 254 and re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value))


def address_from_form():
    result = {key: form_text(key, limit, required=key != "line2") for key, limit in
              (("recipient", 160), ("line1", 200), ("line2", 200), ("city", 100), ("state", 2), ("postal_code", 12))}
    result["state"] = result["state"].upper()
    if not re.fullmatch(r"[A-Z]{2}", result["state"]) or not re.fullmatch(r"\d{5}(?:-\d{4})?", result["postal_code"]):
        raise ValueError("Enter a two-letter U.S. state and valid ZIP code.")
    return result


@app.context_processor
def common_context():
    meta = db.session.get(SnapshotMeta, 1)
    selected = db.session.get(Store, session.get("selected_store")) if session.get("selected_store") else None
    count = owned_cart_query().with_entities(func.coalesce(func.sum(CartItem.quantity), 0)).scalar()
    return {"categories": Category.query.order_by(Category.name).all(), "cart_count": count,
            "selected_store": selected, "home_assets": meta.home_assets if meta else {},
            "site_reference_date": meta.reference_date if meta else "2026-09-28"}


@app.after_request
def response_headers(response):
    response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; font-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.path.startswith(("/account", "/cart", "/checkout", "/order", "/rx/dotm/cart")):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/")
def index():
    return render_template("index.html", featured=Product.query.order_by(Product.id).limit(8).all())


@app.route("/shop")
def shop():
    return render_template("shop.html", featured=Product.query.order_by(Product.id).limit(12).all())


def catalog_view(category=None):
    filters = {key: request.args.get(key, "").strip() for key in ("q", "brand", "price_min", "price_max", "sort", "rating")}
    query = Product.query
    if category:
        query = query.filter_by(category_slug=category.slug)
    brands = [row[0] for row in query.with_entities(Product.brand).distinct().order_by(Product.brand).all() if row[0]]
    if filters["q"]:
        pattern = "%" + filters["q"].replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        query = query.filter(or_(Product.name.ilike(pattern, escape="\\"), Product.brand.ilike(pattern, escape="\\")))
    if filters["brand"]:
        query = query.filter(Product.brand == filters["brand"])
    for key, lower in (("price_min", True), ("price_max", False)):
        if filters[key]:
            try:
                number = Decimal(filters[key])
                if not number.is_finite() or number < 0 or number > 1000000:
                    raise ValueError
                cents = int(number * 100)
            except (InvalidOperation, ValueError):
                abort(400, description="Enter a valid nonnegative price.")
            # Ranges are included by overlap, retaining their original price text.
            low = func.coalesce(Product.price_cents, Product.price_min_cents)
            high = func.coalesce(Product.price_cents, Product.price_max_cents)
            query = query.filter(high >= cents if lower else low <= cents)
    if filters["rating"]:
        try:
            rating = float(filters["rating"])
            if not 0 <= rating <= 5:
                raise ValueError
        except ValueError:
            abort(400, description="Enter a rating between 0 and 5.")
        query = query.filter(Product.rating >= rating)
    price_sort = func.coalesce(Product.price_cents, Product.price_min_cents)
    order = {"price_asc": (price_sort.is_(None), price_sort.asc()),
             "price_desc": (price_sort.is_(None), price_sort.desc()),
             "rating": (Product.rating.is_(None), Product.rating.desc()),
             "name": (Product.name.asc(),), "relevance": (Product.id.asc(),)}
    if filters["sort"] not in order:
        filters["sort"] = "relevance"
    query = query.order_by(*order[filters["sort"]], Product.id)
    total = query.count()
    pages = max(1, math.ceil(total / 12))
    page = request.args.get("page", 1, type=int)
    page = max(1, min(page, pages))
    def pagination_url(page_number):
        params = request.args.to_dict(flat=False)
        params["page"] = [str(page_number)]
        return request.path + "?" + urlencode(params, doseq=True)
    return render_template("catalog.html", category=category, products=query.offset((page - 1) * 12).limit(12).all(),
                           total=total, page=page, pages=pages, brands=brands, filters=filters, pagination_url=pagination_url)


@app.route("/shop/category/<slug>")
def catalog(slug):
    return catalog_view(db.get_or_404(Category, slug))


@app.route("/search")
def search():
    return catalog_view()


@app.route("/shop/product/<product_id>")
def product_detail(product_id):
    product = db.get_or_404(Product, product_id)
    favorite = current_user.is_authenticated and Favorite.query.filter_by(user_id=current_user.id, product_id=product.id).first() is not None
    # An unselected source form field is not a product specification. Keep the
    # original snapshot intact while omitting this empty section from the page.
    detail_sections = [section for section in product.details
                       if not (section.get("heading") == "Specifications"
                               and section.get("text", "").split() == ["Product", "type", "Select", "a", "value"])]
    return render_template("product.html", product=product, variants=product.variants, favorite=favorite,
                           detail_sections=detail_sections)


@app.route("/rx/dotm/cart")
def cart():
    items, subtotal = cart_rows()
    return render_template("cart.html", items=items, **totals(subtotal))


@app.post("/cart/add")
def cart_add():
    product = db.get_or_404(Product, request.form.get("product_id", ""))
    variant_id = request.form.get("variant_id") or None
    variant = db.session.get(Variant, variant_id) if variant_id else None
    if variant_id and (variant is None or variant.product_id != product.id):
        abort(400, description="Choose a valid option for this product.")
    if product.variants and variant is None:
        abort(400, description="Choose a product option.")
    if (variant.price_cents if variant else product.price_cents) is None:
        abort(400, description="This option does not have a captured exact price and cannot be added to the demo cart.")
    quantity = quantity_from_form()
    row = owned_cart_query().filter_by(product_id=product.id, variant_id=variant_id).first()
    if row:
        if row.quantity + quantity > 20:
            abort(400, description="The maximum quantity is 20 per cart item.")
        row.quantity += quantity
    else:
        row = CartItem(product_id=product.id, variant_id=variant_id, quantity=quantity,
                       user_id=current_user.id if current_user.is_authenticated else None,
                       guest_token=None if current_user.is_authenticated else guest_token())
        db.session.add(row)
    db.session.commit()
    flash("Added to your demo cart.", "success")
    return redirect(url_for("cart"))


@app.post("/cart/items/<int:item_id>")
def cart_update(item_id):
    row = owned_cart_query().filter_by(id=item_id).first_or_404()
    row.quantity = quantity_from_form()
    db.session.commit()
    return redirect(url_for("cart"))


@app.post("/cart/items/<int:item_id>/remove")
def cart_remove(item_id):
    db.session.delete(owned_cart_query().filter_by(id=item_id).first_or_404())
    db.session.commit()
    return redirect(url_for("cart"))


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items, subtotal = cart_rows()
    if not items:
        flash("Add an item before checking out.", "info")
        return redirect(url_for("cart"))
    fulfillment = request.form.get("fulfillment", "shipping")
    if request.method == "POST":
        try:
            if fulfillment not in {"shipping", "pickup"}:
                raise ValueError("Choose shipping or store pickup.")
            email = form_text("email", 254).lower()
            if not valid_email(email):
                raise ValueError("Enter a valid email address.")
            address = None
            store_address = None
            if fulfillment == "shipping":
                address_id = request.form.get("address_id", "")
                if address_id:
                    if not current_user.is_authenticated:
                        abort(403)
                    address_record = Address.query.filter_by(id=address_id, user_id=current_user.id).first_or_404()
                    address = address_record.as_dict()
                else:
                    address = address_from_form()
            else:
                store = db.session.get(Store, request.form.get("store_id", ""))
                if store is None:
                    raise ValueError("Choose a pickup store.")
                store_address = f"{store.address}, {store.city}, {store.state} {store.postal_code}"
            amounts = totals(subtotal, fulfillment)
            order = Order(number="CVS-DEMO-" + secrets.token_hex(5).upper(),
                          user_id=current_user.id if current_user.is_authenticated else None,
                          guest_token=None if current_user.is_authenticated else guest_token(),
                          placed_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                          items=[{"product_id": item["product"].id, "name": item["product"].name,
                                  "variant_label": item["variant"].label if item["variant"] else "",
                                  "quantity": item["record"].quantity,
                                  "price_cents": item["line_cents"] // item["record"].quantity,
                                  "line_cents": item["line_cents"]} for item in items],
                          fulfillment=fulfillment, store_address=store_address, address=address, email=email, **amounts)
            db.session.add(order)
            for item in items:
                db.session.delete(item["record"])
            db.session.commit()
            return redirect(url_for("confirmation", order_id=order.id))
        except ValueError as error:
            flash(str(error), "error")
    return render_template("checkout.html", items=items, addresses=Address.query.filter_by(user_id=current_user.id).all() if current_user.is_authenticated else [],
                           stores=Store.query.order_by(Store.city, Store.address).all(), **totals(subtotal, fulfillment))


def authorized_order(order_id):
    query = Order.query.filter_by(id=order_id)
    if current_user.is_authenticated:
        query = query.filter_by(user_id=current_user.id)
    else:
        query = query.filter_by(user_id=None, guest_token=guest_token())
    return query.first_or_404()


@app.route("/order-confirmation/<int:order_id>")
def confirmation(order_id):
    return render_template("confirmation.html", order=authorized_order(order_id))


def adopt_guest_cart(user):
    token = session.get("guest_token")
    if not token:
        return
    rows = CartItem.query.filter_by(user_id=None, guest_token=token).all()
    # Validate the whole merge before changing any row: login must never drop
    # requested quantities or partially transfer the guest cart.
    for row in rows:
        existing = CartItem.query.filter_by(user_id=user.id, product_id=row.product_id, variant_id=row.variant_id).first()
        if existing and existing.quantity + row.quantity > 20:
            raise ValueError("Signing in would exceed the 20-item limit for a product. Reduce its guest-cart quantity before signing in; both carts are unchanged.")
    for row in rows:
        existing = CartItem.query.filter_by(user_id=user.id, product_id=row.product_id, variant_id=row.variant_id).first()
        if existing:
            existing.quantity += row.quantity
            db.session.delete(row)
        else:
            row.user_id, row.guest_token = user.id, None
    # Guest orders stay attached to their original browser session; logging in
    # does not silently associate historical guest orders with an account.
    db.session.commit()


def save_pending_favorite(user):
    product_id = session.get("pending_favorite")
    if not product_id:
        return None
    product = db.session.get(Product, product_id)
    if product is None:
        session.pop("pending_favorite", None)
        return None
    if Favorite.query.filter_by(user_id=user.id, product_id=product.id).first() is None:
        db.session.add(Favorite(user_id=user.id, product_id=product.id))
        db.session.commit()
    session.pop("pending_favorite", None)
    flash("Saved to favorites.", "success")
    return product.path


@app.route("/account-login/look-up", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form.get("email", "").strip().lower()).first()
        if user and check_password_hash(user.password_hash, request.form.get("password", "")):
            try:
                adopt_guest_cart(user)
            except ValueError as error:
                db.session.rollback()
                flash(str(error), "error")
                return render_template("login.html"), 409
            login_user(user)
            favorite_path = save_pending_favorite(user)
            return redirect(favorite_path or local_next(request.form.get("next") or request.args.get("next"), url_for("account")))
        flash("Email or password was not recognized. Use a local demo account.", "error")
    return render_template("login.html")


@app.route("/account-registration/look-up", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            first_name, last_name = form_text("first_name", 80), form_text("last_name", 80)
            email = form_text("email", 254).lower()
            password = form_text("password", 128)
            if not valid_email(email):
                raise ValueError("Enter a valid email address.")
            if len(password) < 8:
                raise ValueError("Use a password with at least 8 characters.")
            if User.query.filter_by(email=email).first():
                raise ValueError("A local account already uses this email address.")
            user = User(email=email, first_name=first_name, last_name=last_name, password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            adopt_guest_cart(user)
            login_user(user)
            favorite_path = save_pending_favorite(user)
            flash("Your local demo account is ready.", "success")
            return redirect(favorite_path or url_for("account"))
        except ValueError as error:
            flash(str(error), "error")
        except IntegrityError:
            db.session.rollback()
            flash("A local account already uses this email address.", "error")
    return render_template("register.html")


@app.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


def favorite_products():
    return Product.query.join(Favorite, Favorite.product_id == Product.id).filter(Favorite.user_id == current_user.id).order_by(Product.name).all()


@app.route("/account/dashboard")
@login_required
def account():
    return render_template("account.html", user=current_user, addresses=Address.query.filter_by(user_id=current_user.id).all(),
                           orders=Order.query.filter_by(user_id=current_user.id).order_by(Order.id.desc()).all(), favorite_products=favorite_products())


@app.route("/account/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        try:
            current_user.first_name, current_user.last_name = form_text("first_name", 80), form_text("last_name", 80)
            current_user.phone = form_text("phone", 32, required=False)
            db.session.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("profile"))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "error")
    return render_template("profile.html", user=current_user)


@app.route("/account/addresses", methods=["GET", "POST"])
@login_required
def addresses():
    if request.method == "POST":
        try:
            values = address_from_form()
            label = form_text("label", 50, required=False) or "Home"
            db.session.add(Address(user_id=current_user.id, label=label, **values))
            db.session.commit()
            flash("Address saved to this local account.", "success")
            return redirect(url_for("addresses"))
        except ValueError as error:
            flash(str(error), "error")
    return render_template("addresses.html", addresses=Address.query.filter_by(user_id=current_user.id).order_by(Address.id).all())


@app.post("/account/addresses/<int:address_id>/delete")
@login_required
def address_delete(address_id):
    db.session.delete(Address.query.filter_by(id=address_id, user_id=current_user.id).first_or_404())
    db.session.commit()
    return redirect(url_for("addresses"))


@app.route("/account/favorites")
@login_required
def favorites():
    return render_template("favorites.html", products=favorite_products())


@app.post("/account/favorites/<product_id>")
def favorite_toggle(product_id):
    product = db.get_or_404(Product, product_id)
    if not current_user.is_authenticated:
        session["pending_favorite"] = product.id
        flash("Sign in to save this product to favorites.", "info")
        return redirect(url_for("login", next=product.path))
    favorite = Favorite.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if favorite:
        db.session.delete(favorite)
        flash("Removed from favorites.", "success")
    else:
        db.session.add(Favorite(user_id=current_user.id, product_id=product_id))
        flash("Saved to favorites.", "success")
    db.session.commit()
    return redirect(local_next(request.form.get("next"), url_for("favorites")))


@app.route("/account/order/order-history")
@login_required
def orders():
    return render_template("orders.html", orders=Order.query.filter_by(user_id=current_user.id).order_by(Order.id.desc()).all())


@app.route("/account/order/<int:order_id>")
@login_required
def order_detail(order_id):
    return render_template("order.html", order=authorized_order(order_id))


@app.route("/store-locator/landing")
def stores():
    query_text = request.args.get("q", request.args.get("address", "")).strip()
    selected_services = request.args.getlist("service")
    all_stores = Store.query.order_by(Store.city, Store.address).all()
    services = sorted({service for store in all_stores for service in store.services})
    search_terms = re.findall(r"[^\W_]+", query_text.casefold())

    def matches_address(store):
        if not query_text:
            return True
        address = f"{store.address} {store.city} {store.state} {store.postal_code}".casefold()
        normalized = " ".join(re.findall(r"[^\W_]+", address))
        return bool(search_terms) and all(term in normalized for term in search_terms)

    matches = [store for store in all_stores if matches_address(store)
               and all(service in store.services for service in selected_services)]
    return render_template("stores.html", stores=matches, total=len(matches), query=query_text,
                           selected_services=selected_services, services=services)


@app.route("/store-locator/store/<store_id>")
def store_detail(store_id):
    store = db.get_or_404(Store, store_id)
    nearby = [record for id_ in store.nearby_ids if (record := db.session.get(Store, str(id_))) is not None]
    return render_template("store.html", store=store, nearby=nearby)


@app.post("/store-locator/select/<store_id>")
def store_select(store_id):
    db.get_or_404(Store, store_id)
    session["selected_store"] = store_id
    flash("Store selected for this browser session.", "success")
    return redirect(local_next(request.form.get("next"), url_for("stores")))


@app.route("/retail/help/help_index")
def help_index():
    return render_template("help.html", pages=Page.query.order_by(Page.title).all())


@app.route("/retail/help/<slug>")
def policy(slug):
    return render_template("policy.html", page=db.get_or_404(Page, slug))


@app.route("/reference")
def reference():
    destination = request.args.get("destination", "https://www.cvs.com/")
    try:
        valid = urlsplit(destination).scheme in {"http", "https"} and bool(urlsplit(destination).netloc)
    except ValueError:
        valid = False
    if not valid:
        destination = "https://www.cvs.com/"
    return render_template("reference.html", destination=destination, title="Outside this offline mirror")


@app.route("/<path:original_path>")
def captured_path(original_path):
    path = "/" + original_path.rstrip("/")
    product = Product.query.filter_by(path=path).first()
    if product:
        return product_detail(product.id)
    category = Category.query.filter_by(path=path).first()
    if category:
        return catalog_view(category)
    store = Store.query.filter_by(path=path).first()
    if store:
        return store_detail(store.id)
    page = Page.query.filter_by(path=path).first()
    if page:
        return render_template("policy.html", page=page)
    abort(404)


@app.route("/_health")
def health():
    ready = db.session.get(SnapshotMeta, 1) is not None and Product.query.count() > 0 and Store.query.count() > 0
    return {"ok": ready, "site": "cvs", "products": Product.query.count(), "stores": Store.query.count()}, 200 if ready else 503


@app.errorhandler(CSRFError)
def csrf_error(error):
    return render_template("error.html", status=400, title="Form expired", message="Refresh the page and submit the form again."), 400


@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(409)
@app.errorhandler(413)
def client_error(error):
    return render_template("error.html", status=error.code, title=error.name, message=error.description), error.code


def initialize_database():
    # CREATE TABLE IF NOT EXISTS is a no-op for an existing frozen database.
    db.create_all()
    if db.session.get(SnapshotMeta, 1) is None:
        from seed_data import seed_database
        seed_database()
    from seed_data import seed_benchmark_users
    seed_benchmark_users()


with app.app_context():
    initialize_database()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "40121")), debug=False)
