#!/usr/bin/env python3
"""Speedo mirror — Flask application.

Mirrors speedo.com (UK swimwear store): catalog browsing with facets/sort/
pagination, product detail with size/colour variants and size guides, cart
drawer + cart page, guest or signed-in checkout with delivery options and
discount codes, account (orders / wishlist / addresses / cards / profile),
swimwear + goggles recommendation quizzes, wishlist with consent flow,
contact form with case tracking, blog, Team Speedo athletes, Our Story,
size guides, FAQs, returns/delivery/klarna/discounts info pages and the
collection hub pages. All catalog and content data is real, captured from
the upstream site (see source_data.json + provenance.json).
"""
import json
import os
import re
from datetime import date

from flask import (Flask, render_template, request, redirect, url_for,
                   flash, session, abort, jsonify)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from flask_bcrypt import Bcrypt
from flask_wtf import CSRFProtect
from urllib.parse import urlsplit

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = "webharbor-speedo-dev-key"
# Tests point the app at a scratch copy of the seed via SPEEDO_DB_PATH so
# stateful checks never touch the live worktree database.
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'SPEEDO_DB_PATH', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'speedo.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

csrf = CSRFProtect(app)
app.config["WTF_CSRF_TIME_LIMIT"] = None
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please sign in to access your account.'
login_manager.login_message_category = 'info'

app.jinja_env.filters['from_json'] = json.loads

# Deterministic reference date: upstream data was captured 2026-09-26 and all
# seeded dates (orders, contact cases, quiz saves) are pinned relative to it.
MIRROR_REFERENCE_DATE = date(2026, 9, 26)

STOP_WORDS = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or',
              'is', 'it', 'by', 'with', 'my', 'your'}

FREE_SHIPPING_THRESHOLD = 50.0


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), default='')
    created_at = db.Column(db.DateTime, default=None)
    accepts_marketing = db.Column(db.Boolean, default=False)

    def set_password(self, raw):
        self.password_hash = bcrypt.generate_password_hash(raw).decode('utf-8')

    def check_password(self, raw):
        return bcrypt.check_password_hash(self.password_hash, raw)

    def cart_count(self):
        return sum(i.qty for i in CartItem.query.filter_by(user_id=self.id).all())

    def wishlist_count(self):
        return WishlistItem.query.filter_by(user_id=self.id).count()


class Address(db.Model):
    __tablename__ = 'addresses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    label = db.Column(db.String(60), default='Home')
    first_name = db.Column(db.String(80), default='')
    last_name = db.Column(db.String(80), default='')
    line1 = db.Column(db.String(200), nullable=False)
    line2 = db.Column(db.String(200), default='')
    city = db.Column(db.String(100), nullable=False)
    postcode = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(60), default='United Kingdom')
    phone = db.Column(db.String(30), default='')
    is_default = db.Column(db.Boolean, default=False)


class PaymentCard(db.Model):
    __tablename__ = 'payment_cards'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    label = db.Column(db.String(60), default='Personal')
    brand = db.Column(db.String(30), nullable=False)
    last4 = db.Column(db.String(4), nullable=False)
    exp_month = db.Column(db.Integer, nullable=False)
    exp_year = db.Column(db.Integer, nullable=False)
    is_default = db.Column(db.Boolean, default=False)


class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(60), nullable=False)
    hub_page = db.Column(db.String(80), default='')
    sort = db.Column(db.Integer, default=0)


class NavGroup(db.Model):
    """A named block inside a department's mega-menu (Featured / Swimwear / ...)."""
    __tablename__ = 'nav_groups'
    id = db.Column(db.Integer, primary_key=True)
    department_slug = db.Column(db.String(40), nullable=False)
    name = db.Column(db.String(60), nullable=False)
    kind = db.Column(db.String(20), default='collection')   # collection | page | custom
    sort = db.Column(db.Integer, default=0)


class NavLink(db.Model):
    __tablename__ = 'nav_links'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('nav_groups.id'), nullable=False)
    text = db.Column(db.String(120), nullable=False)
    href = db.Column(db.String(200), nullable=False)
    is_promo = db.Column(db.Boolean, default=False)          # big promo tile
    promo_image = db.Column(db.String(300), default='')
    promo_heading = db.Column(db.String(120), default='')
    sort = db.Column(db.Integer, default=0)


class Collection(db.Model):
    __tablename__ = 'collections'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(160), nullable=False)
    department_slug = db.Column(db.String(40), nullable=False)
    in_mega_menu = db.Column(db.Boolean, default=False)
    facet_set = db.Column(db.String(30), default='swimwear')  # swimwear | goggles | accessories
    sort = db.Column(db.Integer, default=0)

    memberships = db.relationship('CollectionMembership', backref='collection',
                                  lazy=True, order_by='CollectionMembership.position',
                                  cascade='all, delete-orphan')

    def product_count(self):
        return CollectionMembership.query.filter_by(collection_id=self.id).count()


class CollectionMembership(db.Model):
    __tablename__ = 'collection_memberships'
    id = db.Column(db.Integer, primary_key=True)
    collection_id = db.Column(db.Integer, db.ForeignKey('collections.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    position = db.Column(db.Integer, default=0)


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    sku = db.Column(db.String(40), default='')
    department_slug = db.Column(db.String(40), nullable=False)
    category = db.Column(db.String(80), default='')          # swimsuit / jammer / goggles / ...
    colourway_group = db.Column(db.String(160), default='')
    colour = db.Column(db.String(80), default='')
    colour_swatch = db.Column(db.String(60), default='')      # css colour value
    price = db.Column(db.Float, nullable=False, default=0.0)
    compare_at_price = db.Column(db.Float, default=0.0)       # regular price when on sale
    description = db.Column(db.Text, default='')
    delivery = db.Column(db.Text, default='')
    specs = db.Column(db.Text, default='{}')                  # JSON dict
    images = db.Column(db.Text, default='[]')                 # JSON list, relative to /static/images/
    activity = db.Column(db.String(60), default='')
    fabric = db.Column(db.String(80), default='')
    back_shape = db.Column(db.String(60), default='')
    lens_type = db.Column(db.String(60), default='')
    collection_line = db.Column(db.String(80), default='')    # Essentials / Fastskin / Biofuse ...
    is_new = db.Column(db.Boolean, default=False)
    is_sale = db.Column(db.Boolean, default=False)
    is_bestseller = db.Column(db.Boolean, default=False)
    is_exclusive = db.Column(db.Boolean, default=False)
    sold_out = db.Column(db.Boolean, default=False)
    is_kids = db.Column(db.Boolean, default=False)
    upstream_url = db.Column(db.String(400), default='')
    sort = db.Column(db.Integer, default=0)

    sizes = db.relationship('ProductSize', backref='product', lazy=True,
                            order_by='ProductSize.sort', cascade='all, delete-orphan')

    def spec(self, key):
        try:
            return (json.loads(self.specs or '{}') or {}).get(key, '')
        except Exception:
            return ''

    def spec_items(self):
        try:
            return list((json.loads(self.specs or '{}') or {}).items())
        except Exception:
            return []

    def image_list(self):
        return json.loads(self.images or '[]')

    def size_values(self):
        return [s.size for s in self.sizes]

    def available_sizes(self):
        return [s.size for s in self.sizes if not s.sold_out]

    def colourway_siblings(self):
        if not self.colourway_group:
            return []
        return (Product.query.filter(Product.colourway_group == self.colourway_group,
                                     Product.id != self.id)
                .order_by(Product.sort).all())

    def collections_in(self):
        rows = (CollectionMembership.query
                .filter_by(product_id=self.id)
                .join(Collection, Collection.id == CollectionMembership.collection_id)
                .order_by(Collection.sort).all())
        return [r.collection for r in rows]


class ProductSize(db.Model):
    __tablename__ = 'product_sizes'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    size = db.Column(db.String(20), nullable=False)
    sold_out = db.Column(db.Boolean, default=False)
    sort = db.Column(db.Integer, default=0)


class CartItem(db.Model):
    __tablename__ = 'cart_items'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    size = db.Column(db.String(20), default='')
    qty = db.Column(db.Integer, default=1)
    added_at = db.Column(db.String(10), default='')

    product = db.relationship('Product', lazy=True)


class WishlistItem(db.Model):
    __tablename__ = 'wishlist_items'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    added_at = db.Column(db.String(10), default='')

    product = db.relationship('Product', lazy=True)


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(30), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # null for guest checkout
    email = db.Column(db.String(160), default='')
    status = db.Column(db.String(30), default='Processing')
    subtotal = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    shipping_method = db.Column(db.String(60), default='')
    shipping = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    discount_code = db.Column(db.String(30), default='')
    ship_name = db.Column(db.String(160), default='')
    ship_line1 = db.Column(db.String(200), default='')
    ship_line2 = db.Column(db.String(200), default='')
    ship_city = db.Column(db.String(100), default='')
    ship_postcode = db.Column(db.String(20), default='')
    ship_country = db.Column(db.String(60), default='United Kingdom')
    card_brand = db.Column(db.String(30), default='')
    card_last4 = db.Column(db.String(4), default='')
    tracking_number = db.Column(db.String(40), default='')
    placed_on = db.Column(db.String(10), nullable=False)

    items = db.relationship('OrderItem', backref='order', lazy=True,
                            cascade='all, delete-orphan')

    def item_count(self):
        return sum(i.qty for i in self.items)


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product_name = db.Column(db.String(255), nullable=False)
    product_slug = db.Column(db.String(255), default='')
    size = db.Column(db.String(20), default='')
    qty = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, default=0.0)

    product = db.relationship('Product', lazy=True)


class DiscountCode(db.Model):
    __tablename__ = 'discount_codes'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False)
    kind = db.Column(db.String(20), default='percent')        # percent | fixed
    value = db.Column(db.Float, default=0.0)
    min_spend = db.Column(db.Float, default=0.0)
    description = db.Column(db.String(200), default='')


class Athlete(db.Model):
    __tablename__ = 'athletes'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    team = db.Column(db.String(80), default='')
    quote = db.Column(db.String(300), default='')
    bio = db.Column(db.Text, default='')
    hero_image = db.Column(db.String(300), default='')
    portrait_image = db.Column(db.String(300), default='')
    card_image = db.Column(db.String(300), default='')
    sort = db.Column(db.Integer, default=0)


class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(160), unique=True, nullable=False)
    title = db.Column(db.String(240), nullable=False)
    published = db.Column(db.String(20), default='')
    summary = db.Column(db.String(400), default='')
    body = db.Column(db.Text, default='')
    image = db.Column(db.String(300), default='')
    sort = db.Column(db.Integer, default=0)


class ContentPage(db.Model):
    __tablename__ = 'content_pages'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, default='')                     # JSON list of blocks
    hero_image = db.Column(db.String(300), default='')
    is_hub = db.Column(db.Boolean, default=False)
    hub_department = db.Column(db.String(40), default='')
    featured_products = db.Column(db.Text, default='[]')     # JSON list of product slugs
    sort = db.Column(db.Integer, default=0)

    def blocks(self):
        try:
            return json.loads(self.body or '[]')
        except Exception:
            return []

    def featured_slugs(self):
        try:
            return json.loads(self.featured_products or '[]')
        except Exception:
            return []


class FaqEntry(db.Model):
    __tablename__ = 'faq_entries'
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(300), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    sort = db.Column(db.Integer, default=0)


class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'
    id = db.Column(db.Integer, primary_key=True)
    case_ref = db.Column(db.String(30), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    first_name = db.Column(db.String(80), default='')
    last_name = db.Column(db.String(80), default='')
    email = db.Column(db.String(160), default='')
    category = db.Column(db.String(80), default='')
    subcategory = db.Column(db.String(120), default='')
    order_number = db.Column(db.String(40), default='')
    address_line = db.Column(db.String(200), default='')
    postcode = db.Column(db.String(20), default='')
    message = db.Column(db.Text, default='')
    submitted_on = db.Column(db.String(10), default='')
    status = db.Column(db.String(30), default='Open')


class NewsletterSignup(db.Model):
    __tablename__ = 'newsletter_signups'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(160), nullable=False)
    signed_up_on = db.Column(db.String(10), default='')


class QuizResponse(db.Model):
    __tablename__ = 'quiz_responses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    quiz = db.Column(db.String(30), nullable=False)          # swimsuit | goggles
    answers = db.Column(db.Text, default='{}')               # JSON dict
    result_slugs = db.Column(db.Text, default='[]')          # JSON list
    saved_on = db.Column(db.String(10), default='')


# ---------------------------------------------------------------------------
# Size guide tables (real upstream measurement tables)
# ---------------------------------------------------------------------------

SIZE_GUIDES = json.load(open(os.path.join(BASE_DIR, 'size_guide_data.json'),
                             encoding='utf-8'))


# ---------------------------------------------------------------------------
# Auth plumbing
# ---------------------------------------------------------------------------

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tokens(query):
    return [t.lower() for t in re.split(r'\W+', query)
            if t.lower() not in STOP_WORDS and len(t) > 1]


def scored_search(query, products, fields=('name', 'category', 'fabric',
                                           'collection_line', 'description')):
    tokens = _tokens(query)
    if not tokens:
        return products
    phrase = re.sub(r'\s+', ' ', query.strip().lower())
    results = []
    for p in products:
        name = (p.name or '').lower()
        text = ' '.join((getattr(p, f) or '') for f in fields
                        if isinstance(getattr(p, f), str)).lower()
        score = sum(1 for t in tokens if t in text)
        if score > 0:
            if phrase and phrase in name:
                score += 3
            elif tokens and all(t in name for t in tokens):
                score += 1
            results.append((p, score))
    results.sort(key=lambda x: (-x[1], x[0].sort))
    return [r[0] for r in results]


SORT_OPTIONS = [
    ('manual', 'Featured'),
    ('best-selling', 'Bestselling'),
    ('title-ascending', 'Title A-Z'),
    ('title-descending', 'Title Z-A'),
    ('price-ascending', 'Price - Low to High'),
    ('price-descending', 'Price - High to Low'),
    ('created-ascending', 'Oldest to Newest'),
    ('created-descending', 'Newest to Oldest'),
]


def apply_sort(products, sort):
    if sort == 'title-ascending':
        return sorted(products, key=lambda p: p.name)
    if sort == 'title-descending':
        return sorted(products, key=lambda p: p.name, reverse=True)
    if sort == 'price-ascending':
        return sorted(products, key=lambda p: p.price)
    if sort == 'price-descending':
        return sorted(products, key=lambda p: -p.price)
    if sort == 'created-ascending':
        return sorted(products, key=lambda p: (not p.is_new, p.sort), reverse=False)
    if sort == 'created-descending':
        return sorted(products, key=lambda p: (p.is_new, -p.sort), reverse=False)
    if sort == 'best-selling':
        return sorted(products, key=lambda p: (not p.is_bestseller, p.sort))
    return products


COLOUR_CSS = {
    'black': '#000000', 'white': '#ffffff', 'navy': '#000080', 'blue': '#005fff',
    'red': '#e5271e', 'green': '#22b325', 'grey': '#808080', 'gray': '#808080',
    'pink': '#ffb6c1', 'purple': '#800080', 'teal': '#008080', 'orange': '#ff8c00',
    'yellow': '#ffd700', 'clear': '#cfe8ff', 'smoke': '#6d6d6d', 'mirror': '#b8c4cc',
    'multi': 'linear-gradient(135deg,#e5271e,#005fff)', 'coloured': 'linear-gradient(135deg,#e5271e,#ffd700)',
    'iridescent': 'linear-gradient(135deg,#b8c4cc,#800080)',
}


def colour_css(name):
    key = (name or '').strip().lower()
    for token, css in COLOUR_CSS.items():
        if key.startswith(token):
            return css
    return '#888888'


app.jinja_env.filters['colour_css'] = colour_css


def _facet_set_for(department):
    if department == 'goggles':
        return 'goggles'
    if department == 'accessories':
        return 'accessories'
    return 'swimwear'


def _price_bounds(products):
    prices = [p.price for p in products] or [0]
    return min(prices), max(prices)


def _facet_options(products, facet_set):
    """Compute facet value -> count like the upstream facets (with counts)."""
    facets = []
    price_lo, price_hi = _price_bounds(products)
    facets.append({'key': 'price', 'name': 'Price', 'type': 'range',
                   'min': price_lo, 'max': price_hi})
    size_counts = {}
    for p in products:
        for s in p.sizes:
            if s.size and s.size.lower() != 'onesz' and s.size.lower() != 'one size':
                size_counts[s.size] = size_counts.get(s.size, 0) + 1
    ordered_sizes = _sort_sizes(size_counts)
    if ordered_sizes:
        facets.append({'key': 'size', 'name': 'Size', 'type': 'list',
                       'options': ordered_sizes})
    colour_counts = {}
    for p in products:
        if p.colour:
            colour_counts[p.colour] = colour_counts.get(p.colour, 0) + 1
    if colour_counts:
        facets.append({'key': 'colour', 'name': 'Colour', 'type': 'swatch',
                       'options': sorted(colour_counts.items(), key=lambda x: -x[1])})
    cat_counts = {}
    for p in products:
        if p.category:
            cat_counts[p.category] = cat_counts.get(p.category, 0) + 1
    if cat_counts:
        facets.append({'key': 'category', 'name': 'Category', 'type': 'list',
                       'options': sorted(cat_counts.items())})
    if facet_set == 'swimwear':
        back_counts = {}
        for p in products:
            if p.back_shape:
                back_counts[p.back_shape] = back_counts.get(p.back_shape, 0) + 1
        if back_counts:
            facets.append({'key': 'back_shape', 'name': 'Back Shape', 'type': 'list',
                           'options': sorted(back_counts.items())})
    fabric_counts = {}
    for p in products:
        if p.fabric:
            fabric_counts[p.fabric] = fabric_counts.get(p.fabric, 0) + 1
    if fabric_counts:
        facets.append({'key': 'fabric', 'name': 'Fabric', 'type': 'list',
                       'options': sorted(fabric_counts.items())})
    act_counts = {}
    for p in products:
        if p.activity:
            act_counts[p.activity] = act_counts.get(p.activity, 0) + 1
    if act_counts:
        facets.append({'key': 'activity', 'name': 'Activity', 'type': 'list',
                       'options': sorted(act_counts.items())})
    if facet_set == 'goggles':
        lens_counts = {}
        for p in products:
            if p.lens_type:
                lens_counts[p.lens_type] = lens_counts.get(p.lens_type, 0) + 1
        if lens_counts:
            facets.append({'key': 'lens_type', 'name': 'Lens Type', 'type': 'list',
                           'options': sorted(lens_counts.items())})
    return facets


def _sort_sizes(size_counts):
    def key(item):
        s = item[0]
        try:
            return (0, float(s), '')
        except ValueError:
            pass
        order = ['2XS', 'XS', 'S', 'M', 'L', 'XL', '2XL', '3XL', '4XL', '5XL']
        if s.upper() in order:
            return (1, order.index(s.upper()), '')
        if re.match(r'^\d+-\d+ ?(yrs?|years?)$', s, re.I):
            return (2, float(s.split('-')[0]), '')
        if s.lower() in ('onesz', 'one size'):
            return (3, 0, '')
        return (4, 0, s)
    return sorted(size_counts.items(), key=lambda kv: (key(kv)[0], key(kv)[1], key(kv)[2]))


def _match_facets(products, args):
    size = args.get('size', '')
    colour = args.get('colour', '')
    category = args.get('category', '')
    back_shape = args.get('back_shape', '')
    fabric = args.get('fabric', '')
    activity = args.get('activity', '')
    lens_type = args.get('lens_type', '')
    price_min = args.get('price_min', '')
    price_max = args.get('price_max', '')
    out = []
    for p in products:
        if size and size not in p.size_values():
            continue
        if colour and p.colour != colour:
            continue
        if category and p.category != category:
            continue
        if back_shape and p.back_shape != back_shape:
            continue
        if fabric and p.fabric != fabric:
            continue
        if activity and p.activity != activity:
            continue
        if lens_type and p.lens_type != lens_type:
            continue
        if price_min:
            try:
                if p.price < float(price_min):
                    continue
            except ValueError:
                pass
        if price_max:
            try:
                if p.price > float(price_max):
                    continue
            except ValueError:
                pass
        out.append(p)
    return out


PAGE_SIZE = 24


def _collection_products(collection):
    rows = (CollectionMembership.query
            .filter_by(collection_id=collection.id)
            .order_by(CollectionMembership.position).all())
    products = []
    for r in rows:
        p = db.session.get(Product, r.product_id)
        if p:
            products.append(p)
    return products


def _cart_rows():
    """Unified view of the cart: session cart for guests, DB cart for users."""
    rows = []
    if current_user.is_authenticated:
        for item in CartItem.query.filter_by(user_id=current_user.id).order_by(CartItem.id).all():
            rows.append({'product': item.product, 'size': item.size,
                         'qty': item.qty, 'key': f"db-{item.id}"})
    else:
        for i, row in enumerate(session.get('cart', [])):
            p = Product.query.filter_by(slug=row.get('slug')).first()
            if p:
                rows.append({'product': p, 'size': row.get('size', ''),
                             'qty': row.get('qty', 1), 'key': f"ss-{i}"})
    return rows


def _cart_summary():
    rows = _cart_rows()
    subtotal = sum(r['product'].price * r['qty'] for r in rows)
    code = session.get('discount_code', '')
    discount = 0.0
    discount_code = None
    if code:
        discount_code = DiscountCode.query.filter_by(code=code).first()
        if discount_code and subtotal >= discount_code.min_spend:
            if discount_code.kind == 'percent':
                discount = round(subtotal * discount_code.value / 100.0, 2)
            else:
                discount = min(discount_code.value, subtotal)
    total = max(0.0, round(subtotal - discount, 2))
    remaining = max(0.0, FREE_SHIPPING_THRESHOLD - total)
    return {'rows': rows, 'subtotal': round(subtotal, 2), 'discount': round(discount, 2),
            'total': total, 'remaining': round(remaining, 2),
            'code': code if discount_code else '', 'discount_code': discount_code,
            'count': sum(r['qty'] for r in rows)}


def _session_wishlist():
    return session.get('wishlist', [])


def _wishlist_slugs():
    if current_user.is_authenticated:
        return [w.product.slug for w in
                WishlistItem.query.filter_by(user_id=current_user.id).order_by(WishlistItem.id)]
    return _session_wishlist()


def _merge_session_carts():
    """On login, fold the guest cart + wishlist into the account."""
    cart = session.pop('cart', [])
    for row in cart:
        p = Product.query.filter_by(slug=row.get('slug')).first()
        if not p:
            continue
        existing = CartItem.query.filter_by(user_id=current_user.id,
                                            product_id=p.id, size=row.get('size', '')).first()
        if existing:
            existing.qty = min(50, existing.qty + row.get('qty', 1))
        else:
            db.session.add(CartItem(user_id=current_user.id, product_id=p.id,
                                    size=row.get('size', ''), qty=row.get('qty', 1)))
    wl = session.pop('wishlist', [])
    for slug in wl:
        p = Product.query.filter_by(slug=slug).first()
        if p and not WishlistItem.query.filter_by(user_id=current_user.id,
                                                  product_id=p.id).first():
            db.session.add(WishlistItem(user_id=current_user.id, product_id=p.id))
    db.session.commit()


# The frozen content-page seed carries 25 upstream pages; the one upstream
# nav target it does not carry is the Speedo DMC landing page
# (/pages/speedo-dmc, linked by the Accessories > Explore menu). Rewire that
# nav entry to the stocked DMC collection — the same href upstream itself uses
# for the "Speedo DMC Fins" entries in the Women/Men menus and the target of
# the homepage promo tile CTA (404 fix; review diff item #3).
NAV_HREF_FALLBACKS = {'/pages/speedo-dmc': '/collections/speedo-dmc-all'}


def _nav_tree():
    departments = Department.query.order_by(Department.sort).all()
    tree = []
    for d in departments:
        groups = (NavGroup.query.filter_by(department_slug=d.slug)
                  .order_by(NavGroup.sort).all())
        blocks = []
        for g in groups:
            links = (NavLink.query.filter_by(group_id=g.id)
                     .order_by(NavLink.sort).all())
            blocks.append({'name': g.name, 'kind': g.kind,
                           'links': [{'text': l.text,
                                      'href': NAV_HREF_FALLBACKS.get(l.href, l.href),
                                      'is_promo': l.is_promo,
                                      'promo_image': l.promo_image,
                                      'promo_heading': l.promo_heading} for l in links]})
        tree.append({'slug': d.slug, 'name': d.name, 'hub_page': d.hub_page,
                     'blocks': blocks})
    return tree


def _sort_key_product(p):
    return p.sort


@app.context_processor
def inject_globals():
    return {
        'nav_tree': _nav_tree,
        'cart_summary': _cart_summary,
        'cart_count': _cart_summary()['count'],
        'wishlist_count': len(_wishlist_slugs()),
        'reference_date': MIRROR_REFERENCE_DATE,
        'sort_options': SORT_OPTIONS,
    }


def local_target(value, fallback):
    target = urlsplit(value or '')
    return (value if value and value.startswith('/') and not value.startswith('//')
            and not target.netloc and not target.scheme and '\\' not in value else fallback)


def _product_cards(products):
    """Card view models matching the upstream grid card markup."""
    cards = []
    for p in products:
        siblings = p.colourway_siblings()
        group = ([p] + siblings) if siblings else [p]
        from_prices = sorted({round(x.price, 2) for x in group})
        price_from = len(from_prices) > 1
        cards.append({
            'product': p,
            'price_from': price_from,
            'swatches': [{'slug': s.slug, 'colour': s.colour,
                          'swatch': s.colour_swatch, 'name': s.name} for s in group[:6]],
        })
    return cards


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    def collection_cards(slug, limit=12):
        c = Collection.query.filter_by(slug=slug).first()
        if not c:
            return []
        return _product_cards(_collection_products(c)[:limit])

    fastskin_new = collection_cards('women-fastskin', 10)
    new_arrivals = collection_cards('women-new-arrivals', 12)
    bestsellers = collection_cards('women-bestsellers', 12)
    essentials = collection_cards('women-essentials', 12)
    sale = collection_cards('women-sale', 12)
    return render_template('index.html', fastskin_new=fastskin_new,
                          new_arrivals=new_arrivals, bestsellers=bestsellers,
                          essentials=essentials, sale=sale)


@app.route('/collections/<slug>')
def collection(slug):
    c = Collection.query.filter_by(slug=slug).first_or_404()
    products = _collection_products(c)
    sort = request.args.get('sort_by', 'manual')
    products = apply_sort(products, sort)
    facets = _facet_options(products, c.facet_set)
    products = _match_facets(products, request.args)

    try:
        page = max(1, int(request.args.get('page', '1')))
    except ValueError:
        page = 1
    total = len(products)
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, pages)
    window = products[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]

    active = {k: v for k, v in request.args.items()
              if k in ('size', 'colour', 'category', 'back_shape', 'fabric',
                       'activity', 'lens_type', 'price_min', 'price_max') and v}

    def url_for_page(p, **overrides):
        args = dict(request.args)
        args.pop('page', None)
        args.update({k: v for k, v in overrides.items() if v is not None})
        if p > 1:
            args['page'] = p
        return url_for('collection', slug=slug, **args)

    return render_template('collection.html', c=c, products=window,
                           cards=_product_cards(window), total=total, page=page,
                           pages=pages, facets=facets, active=active,
                           sort=sort, url_for_page=url_for_page)


@app.route('/search')
def search():
    q = (request.args.get('q') or '').strip()
    products = Product.query.order_by(Product.sort).all()
    results = scored_search(q, products) if q else []
    sort = request.args.get('sort_by', 'manual')
    results = apply_sort(results, sort)
    total = len(results)
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    return render_template('search.html', q=q, cards=_product_cards(results[:PAGE_SIZE]),
                           total=total, pages=pages, page=1, sort=sort)


@app.route('/products/<slug>')
def product_detail(slug):
    p = Product.query.filter_by(slug=slug).first_or_404()
    siblings = p.colourway_siblings()
    related = []
    for c in p.collections_in():
        for rp in _collection_products(c):
            if rp.id != p.id and rp not in related:
                related.append(rp)
        if len(related) >= 8:
            break
    size_guide = SIZE_GUIDES.get(_guide_key(p), None)
    return render_template('product.html', p=p, siblings=siblings,
                           related=_product_cards(related[:8]), size_guide=size_guide)


def _guide_key(p):
    if p.department_slug == 'women':
        return 'women'
    if p.department_slug == 'men':
        return 'men'
    if p.is_kids:
        return 'kids'
    return 'accessories'


# ---------------------------------------------------------------------------
# Cart & checkout
# ---------------------------------------------------------------------------

@app.route('/cart')
def cart():
    return render_template('cart.html', summary=_cart_summary())


def _do_cart_add(product, size, qty):
    if current_user.is_authenticated:
        existing = CartItem.query.filter_by(user_id=current_user.id,
                                            product_id=product.id, size=size).first()
        if existing:
            existing.qty = min(50, existing.qty + qty)
        else:
            db.session.add(CartItem(user_id=current_user.id, product_id=product.id,
                                    size=size, qty=qty))
        db.session.commit()
    else:
        cart = session.get('cart', [])
        for row in cart:
            if row.get('slug') == product.slug and row.get('size') == size:
                row['qty'] = min(50, row['qty'] + qty)
                break
        else:
            cart.append({'slug': product.slug, 'size': size, 'qty': qty})
        session['cart'] = cart
        session.modified = True


@app.route('/cart/add', methods=['POST'])
def cart_add():
    slug = request.form.get('slug', '')
    product = Product.query.filter_by(slug=slug).first()
    if not product:
        abort(404)
    size = request.form.get('size', '')
    if product.sizes and not size:
        size = product.available_sizes()[0] if product.available_sizes() else ''
    if product.sizes and size not in product.size_values():
        size = ''
    if product.sizes and not size:
        flash('Please choose a size.', 'error')
        return redirect(url_for('product_detail', slug=slug))
    try:
        qty = max(1, int(request.form.get('quantity', '1')))
    except ValueError:
        qty = 1
    qty = min(50, qty)
    _do_cart_add(product, size, qty)
    if request.headers.get('X-Requested-With') == 'fetch':
        return jsonify({'ok': True, 'count': _cart_summary()['count']})
    return redirect(url_for('cart'))


@app.route('/cart/update', methods=['POST'])
def cart_update():
    key = request.form.get('key', '')
    try:
        qty = max(0, int(request.form.get('quantity', '1')))
    except ValueError:
        qty = 1
    qty = min(50, qty)
    if key.startswith('db-'):
        item = db.session.get(CartItem, int(key[3:]))
        if item and item.user_id == current_user.id:
            if qty == 0:
                db.session.delete(item)
            else:
                item.qty = qty
            db.session.commit()
    elif key.startswith('ss-'):
        cart = session.get('cart', [])
        try:
            idx = int(key[3:])
        except ValueError:
            idx = -1
        if 0 <= idx < len(cart):
            if qty == 0:
                cart.pop(idx)
            else:
                cart[idx]['qty'] = qty
            session['cart'] = cart
            session.modified = True
    return redirect(url_for('cart'))


@app.route('/cart/remove', methods=['POST'])
def cart_remove():
    return cart_update()


@app.route('/cart/discount', methods=['POST'])
def cart_discount():
    code = (request.form.get('code') or '').strip().upper()
    if not code:
        session.pop('discount_code', None)
    else:
        dc = DiscountCode.query.filter_by(code=code).first()
        if dc:
            session['discount_code'] = code
            flash(f'Discount code {code} applied.', 'success')
        else:
            flash(f'Discount code {code} is not valid.', 'error')
    return redirect(url_for('cart'))


SHIPPING_METHODS = [
    ('standard', 'Standard Delivery', '3–5 working days', 5.99,
     'Free over £50. Monday to Saturday.'),
    ('express', 'Express Delivery', 'Next working day', 8.99,
     'Order before 3pm Monday to Friday.'),
    ('intl-standard', 'Standard International', '5–12 working days', 12.99,
     'Tracked delivery. Free over £75.'),
    ('intl-express', 'Express International', '4–7 working days', 24.99,
     'Tracked delivery worldwide.'),
]


def _shipping_cost(method, total):
    for key, _n, _t, price, _d in SHIPPING_METHODS:
        if key == method:
            if key == 'standard' and total >= FREE_SHIPPING_THRESHOLD:
                return 0.0
            if key == 'intl-standard' and total >= 75.0:
                return 0.0
            return price
    return SHIPPING_METHODS[0][3]


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    summary = _cart_summary()
    if not summary['rows']:
        return redirect(url_for('cart'))
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip()
        first = (request.form.get('first_name') or '').strip()
        last = (request.form.get('last_name') or '').strip()
        line1 = (request.form.get('line1') or '').strip()
        city = (request.form.get('city') or '').strip()
        postcode = (request.form.get('postcode') or '').strip()
        country = request.form.get('country', 'United Kingdom')
        method = request.form.get('shipping_method', 'standard')
        card_number = re.sub(r'\D', '', request.form.get('card_number', ''))
        errors = []
        if method not in {m[0] for m in SHIPPING_METHODS}:
            errors.append('Choose a valid delivery method.')
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            errors.append('Enter a valid email address.')
        if not first or not last:
            errors.append('Enter your first and last name.')
        if not line1:
            errors.append('Enter your street address.')
        if not city:
            errors.append('Enter your city.')
        if not re.match(r'^[A-Za-z0-9 \-]{3,10}$', postcode):
            errors.append('Enter a valid postcode.')
        if len(card_number) < 15 or len(card_number) > 19:
            errors.append('Enter a valid card number.')
        exp_month = request.form.get('exp_month', '')
        exp_year = request.form.get('exp_year', '')
        if not (exp_month.isdigit() and 1 <= int(exp_month) <= 12):
            errors.append('Enter a valid card expiry month.')
        if not (exp_year.isdigit() and len(exp_year) == 2):
            errors.append('Enter a valid card expiry year.')
        cvc = request.form.get('cvc', '')
        if not (cvc.isdigit() and len(cvc) in (3, 4)):
            errors.append('Enter a valid security code.')
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('checkout.html', summary=summary,
                                   shipping_methods=SHIPPING_METHODS,
                                   form=request.form)
        # place order
        order_number = 'SP' + str(100000 + Order.query.count() + 1)
        shipping = _shipping_cost(method, summary['total'])
        total = round(summary['total'] + shipping, 2)
        brand = 'Visa' if card_number[:1] == '4' else ('Mastercard' if card_number[:1] == '5' else 'Visa')
        order = Order(order_number=order_number,
                      user_id=current_user.id if current_user.is_authenticated else None,
                      email=email, status='Processing',
                      subtotal=summary['subtotal'], discount=summary['discount'],
                      shipping_method=next(n for k, n, _t, _p, _d in SHIPPING_METHODS if k == method),
                      shipping=shipping, total=total,
                      discount_code=summary['code'],
                      ship_name=f"{first} {last}".strip(), ship_line1=line1,
                      ship_line2=request.form.get('line2', ''),
                      ship_city=city, ship_postcode=postcode, ship_country=country,
                      card_brand=brand, card_last4=card_number[-4:],
                      tracking_number='',
                      placed_on=MIRROR_REFERENCE_DATE.isoformat())
        db.session.add(order)
        for row in summary['rows']:
            db.session.add(OrderItem(order=order, product_id=row['product'].id,
                                     product_name=row['product'].name,
                                     product_slug=row['product'].slug,
                                     size=row['size'], qty=row['qty'],
                                     unit_price=row['product'].price))
        # clear the cart
        if current_user.is_authenticated:
            CartItem.query.filter_by(user_id=current_user.id).delete()
        else:
            session.pop('cart', None)
        session.pop('discount_code', None)
        db.session.commit()
        return redirect(url_for('order_confirmation', order_number=order_number))
    return render_template('checkout.html', summary=summary,
                           shipping_methods=SHIPPING_METHODS, form={})


@app.route('/order/confirmation/<order_number>')
def order_confirmation(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    return render_template('order_confirmation.html', order=order)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(request.form.get('password', '')):
            login_user(user)
            _merge_session_carts()
            target = request.args.get('next') or url_for('account')
            if not local_target(target, url_for('account')).startswith('/'):
                target = url_for('account')
            return redirect(target)
        flash('Incorrect email or password.', 'error')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        name = (request.form.get('name') or '').strip()
        password = request.form.get('password', '')
        errors = []
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            errors.append('Enter a valid email address.')
        if User.query.filter_by(email=email).first():
            errors.append('An account with that email already exists.')
        if not name:
            errors.append('Enter your name.')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('register.html', form=request.form)
        user = User(email=email, name=name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        _merge_session_carts()
        flash('Welcome to Speedo. Your account is ready.', 'success')
        return redirect(url_for('account'))
    return render_template('register.html', form={})


@app.route('/logout', methods=['POST'])
def logout():
    logout_user()
    return redirect(url_for('index'))


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------

@app.route('/account')
@login_required
def account():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.id.desc()).all()
    return render_template('account.html', orders=orders)


@app.route('/account/orders/<order_number>')
@login_required
def account_order(order_number):
    order = Order.query.filter_by(order_number=order_number,
                                  user_id=current_user.id).first_or_404()
    return render_template('order_detail.html', order=order)


@app.route('/account/profile', methods=['GET', 'POST'])
@login_required
def account_profile():
    if request.method == 'POST':
        current_user.name = (request.form.get('name') or current_user.name).strip()
        current_user.phone = (request.form.get('phone') or '').strip()
        current_user.accepts_marketing = bool(request.form.get('accepts_marketing'))
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('account_profile'))
    return render_template('edit_profile.html')


@app.route('/account/addresses', methods=['GET', 'POST'])
@login_required
def account_addresses():
    if request.method == 'POST':
        if request.form.get('delete_id'):
            addr = db.session.get(Address, int(request.form['delete_id']))
            if addr and addr.user_id == current_user.id:
                db.session.delete(addr)
                db.session.commit()
            return redirect(url_for('account_addresses'))
        line1 = (request.form.get('line1') or '').strip()
        city = (request.form.get('city') or '').strip()
        postcode = (request.form.get('postcode') or '').strip()
        if not line1 or not city or not re.match(r'^[A-Za-z0-9 \-]{3,10}$', postcode):
            flash('Enter a complete address.', 'error')
        else:
            if request.form.get('make_default'):
                for a in Address.query.filter_by(user_id=current_user.id):
                    a.is_default = False
            db.session.add(Address(user_id=current_user.id,
                                   label=request.form.get('label', 'Home'),
                                   first_name=request.form.get('first_name', ''),
                                   last_name=request.form.get('last_name', ''),
                                   line1=line1, line2=request.form.get('line2', ''),
                                   city=city, postcode=postcode,
                                   phone=request.form.get('phone', ''),
                                   is_default=bool(request.form.get('make_default'))))
            db.session.commit()
            flash('Address saved.', 'success')
        return redirect(url_for('account_addresses'))
    addresses = Address.query.filter_by(user_id=current_user.id).order_by(Address.id).all()
    return render_template('addresses.html', addresses=addresses)


@app.route('/account/payment', methods=['GET', 'POST'])
@login_required
def account_payment():
    if request.method == 'POST':
        if request.form.get('delete_id'):
            card = db.session.get(PaymentCard, int(request.form['delete_id']))
            if card and card.user_id == current_user.id:
                db.session.delete(card)
                db.session.commit()
            return redirect(url_for('account_payment'))
        number = re.sub(r'\D', '', request.form.get('card_number', ''))
        exp_month = request.form.get('exp_month', '')
        exp_year = request.form.get('exp_year', '')
        if len(number) < 15 or len(number) > 19:
            flash('Enter a valid card number.', 'error')
        elif not (exp_month.isdigit() and 1 <= int(exp_month) <= 12) or not (exp_year.isdigit() and len(exp_year) == 2):
            flash('Enter a valid expiry date.', 'error')
        else:
            brand = 'Visa' if number[:1] == '4' else ('Mastercard' if number[:1] == '5' else 'Visa')
            if request.form.get('make_default'):
                for c in PaymentCard.query.filter_by(user_id=current_user.id):
                    c.is_default = False
            db.session.add(PaymentCard(user_id=current_user.id,
                                       label=request.form.get('label', 'Personal'),
                                       brand=brand, last4=number[-4:],
                                       exp_month=int(exp_month), exp_year=int(exp_year),
                                       is_default=bool(request.form.get('make_default'))))
            db.session.commit()
            flash('Card saved.', 'success')
        return redirect(url_for('account_payment'))
    cards = PaymentCard.query.filter_by(user_id=current_user.id).order_by(PaymentCard.id).all()
    return render_template('payment.html', cards=cards)


@app.route('/account/wishlist')
@login_required
def account_wishlist():
    items = (WishlistItem.query.filter_by(user_id=current_user.id)
             .order_by(WishlistItem.id).all())
    return render_template('wishlist.html', items=items,
                           cards=_product_cards([w.product for w in items]))


@app.route('/wishlist')
def wishlist():
    if current_user.is_authenticated:
        return redirect(url_for('account_wishlist'))
    slugs = _session_wishlist()
    products = [Product.query.filter_by(slug=s).first() for s in slugs]
    products = [p for p in products if p]
    return render_template('wishlist.html', items=None, cards=_product_cards(products))


@app.route('/wishlist/add', methods=['POST'])
def wishlist_add():
    slug = request.form.get('slug', '')
    product = Product.query.filter_by(slug=slug).first()
    if not product:
        abort(404)
    if current_user.is_authenticated:
        if not WishlistItem.query.filter_by(user_id=current_user.id,
                                            product_id=product.id).first():
            db.session.add(WishlistItem(user_id=current_user.id, product_id=product.id))
            db.session.commit()
    else:
        wl = session.get('wishlist', [])
        if slug not in wl:
            wl.append(slug)
            session['wishlist'] = wl
            session.modified = True
    if request.headers.get('X-Requested-With') == 'fetch':
        return jsonify({'ok': True})
    return redirect(request.form.get('next') or url_for('wishlist'))


@app.route('/wishlist/remove', methods=['POST'])
def wishlist_remove():
    slug = request.form.get('slug', '')
    product = Product.query.filter_by(slug=slug).first()
    if product and current_user.is_authenticated:
        row = WishlistItem.query.filter_by(user_id=current_user.id,
                                           product_id=product.id).first()
        if row:
            db.session.delete(row)
            db.session.commit()
    else:
        wl = session.get('wishlist', [])
        if slug in wl:
            wl.remove(slug)
            session['wishlist'] = wl
            session.modified = True
    return redirect(request.form.get('next') or url_for('wishlist'))


# ---------------------------------------------------------------------------
# Quizzes
# ---------------------------------------------------------------------------

SWIMSUIT_QUIZ = json.load(open(os.path.join(BASE_DIR, 'quiz_data.json'),
                              encoding='utf-8'))['swimsuit']
GOGGLES_QUIZ = json.load(open(os.path.join(BASE_DIR, 'quiz_data.json'),
                             encoding='utf-8'))['goggles']


def _quiz_state(quiz_key):
    return session.get(f'quiz_{quiz_key}', {})


def _swimsuit_recommendations(answers):
    dept = 'women' if answers.get('who', 'women') == "Women's" else 'men'
    activity = answers.get('swim', 'Fitness')
    style = answers.get('style', '')
    pref = answers.get('pref', '')
    products = Product.query.filter_by(department_slug=dept).order_by(Product.sort).all()
    pool = [p for p in products if p.activity == activity and not p.sold_out]
    if not pool:
        pool = [p for p in products if p.activity == activity]
    if not pool:
        pool = products
    if style:
        style_map = {
            'One-Piece': ('Swimsuit', 'Kneeskin'),
            'Two-Piece': ('Bikini', 'Tankini', 'Two Piece'),
            'Fastskin Ignite': ('Ignite',),
            'Fastskin Valor': ('Valor',),
            'Fastskin Intent': ('Intent',),
            'Jammers': ('Jammer',),
            'Briefs': ('Brief',),
            'Swim Shorts': ('Shorts',),
            'Aquashorts': ('Aquashorts',),
        }
        keys = style_map.get(style, ())
        if keys:
            styled = [p for p in pool if any(k.lower() in (p.category or '').lower()
                                             or k.lower() in p.name.lower() for k in keys)]
            if styled:
                pool = styled
    if pref == 'Classic Black':
        black = [p for p in pool if 'black' in (p.colour or '').lower()
                 or 'black' in p.name.lower()]
        if black:
            pool = black
    elif pref == 'Bold Prints':
        prints = [p for p in pool if '/' in (p.colour or '') or 'Print' in p.name
                  or 'Printed' in p.name]
        if prints:
            pool = prints
    elif pref == 'Minimal':
        minimal = [p for p in pool if (p.colour or '').count('/') == 0]
        if minimal:
            pool = minimal
    return pool[:3]


def _goggles_recommendations(answers):
    who = answers.get('who', 'Adults')
    swim = answers.get('swim', 'Fitness')
    lens = answers.get('lens', 'All lens types')
    products = Product.query.filter(Product.department_slug == 'goggles')
    if who == 'Kids':
        kids = [p for p in products if p.is_kids]
        pool = kids if kids else list(products)
    else:
        pool = [p for p in products if not p.is_kids]
    by_swim = [p for p in pool if p.activity in
               ({'Open Water & Recreation': ('Recreation', 'Outdoor Swim'),
                 'Fitness': ('Fitness',),
                 'Training': ('Training',),
                 'Racing': ('Racing',)}.get(swim, ()))]
    if by_swim:
        pool = by_swim
    lens_map = {'Clear': 'Clear', 'Colour': 'Coloured', 'Smoke': 'Smoke',
                'Mirror': 'Mirrored', 'Polarised': 'Polarised'}
    want = lens_map.get(lens, '')
    if want:
        by_lens = [p for p in pool if want.lower() in (p.lens_type or '').lower()
                   or want.lower() in p.name.lower()]
        if by_lens:
            pool = by_lens
    return pool[:3]


def _quiz_options(quiz_key, step, state):
    """Resolve the option list for a quiz step (handles conditional options)."""
    quiz = SWIMSUIT_QUIZ if quiz_key == 'swimsuit' else GOGGLES_QUIZ
    step_data = quiz['steps'][step]
    if 'options_by_prev' in step_data:
        prev = quiz['steps'][step - 1]
        swim = state.get(str(step - 1), '')
        who = state.get('0', '')
        by_prev = step_data['options_by_prev']
        if swim == 'Racing':
            return by_prev['Racing']
        if who == "Women's":
            return by_prev['women_default']
        if who == "Men's" and swim == 'Recreation':
            return by_prev['men_recreation']
        return by_prev['men_default']
    return step_data['options']


def _swimsuit_step_count(state):
    """Racing paths end after the Fastskin-model question (no style-preference step)."""
    if state.get('2', '') in ('Fastskin Ignite', 'Fastskin Valor', 'Fastskin Intent'):
        return 3
    return len(SWIMSUIT_QUIZ['steps'])


@app.route('/pages/swimsuit-quiz', methods=['GET', 'POST'])
def swimsuit_quiz():
    steps = SWIMSUIT_QUIZ['steps']
    state = _quiz_state('swimsuit')
    if request.method == 'POST':
        action = request.form.get('action', 'answer')
        if action == 'restart':
            session.pop('quiz_swimsuit', None)
            return redirect(url_for('swimsuit_quiz'))
        step_index = int(request.form.get('step', '0'))
        value = request.form.get('value', '')
        if value:
            state[str(step_index)] = value
            session['quiz_swimsuit'] = state
            session.modified = True
        nxt = step_index + 1
        if nxt >= _swimsuit_step_count(state):
            return redirect(url_for('swimsuit_quiz_results'))
        return redirect(url_for('swimsuit_quiz', step=nxt))
    try:
        step = max(0, int(request.args.get('step', '0')))
    except ValueError:
        step = 0
    total_steps = _swimsuit_step_count(state)
    step = min(step, total_steps - 1)
    current = dict(steps[step])
    current['options'] = _quiz_options('swimsuit', step, state)
    return render_template('quiz.html', quiz_key='swimsuit', quiz=SWIMSUIT_QUIZ,
                           step=step, step_data=current, state=state,
                           total_steps=total_steps)


@app.route('/pages/swimsuit-quiz/results')
def swimsuit_quiz_results():
    state = _quiz_state('swimsuit')
    mapped = {'who': state.get('0', ''), 'swim': state.get('1', ''),
              'style': state.get('2', ''), 'pref': state.get('3', '')}
    recs = _swimsuit_recommendations(mapped)
    return render_template('quiz_results.html', quiz_key='swimsuit',
                           quiz=SWIMSUIT_QUIZ, answers=mapped, cards=_product_cards(recs))


@app.route('/pages/goggles-quiz', methods=['GET', 'POST'])
def goggles_quiz():
    steps = GOGGLES_QUIZ['steps']
    state = _quiz_state('goggles')
    if request.method == 'POST':
        action = request.form.get('action', 'answer')
        if action == 'restart':
            session.pop('quiz_goggles', None)
            return redirect(url_for('goggles_quiz'))
        step_index = int(request.form.get('step', '0'))
        value = request.form.get('value', '')
        if value:
            state[str(step_index)] = value
            session['quiz_goggles'] = state
            session.modified = True
        nxt = step_index + 1
        if nxt >= len(steps):
            return redirect(url_for('goggles_quiz_results'))
        return redirect(url_for('goggles_quiz', step=nxt))
    try:
        step = max(0, int(request.args.get('step', '0')))
    except ValueError:
        step = 0
    step = min(step, len(steps) - 1)
    current = dict(steps[step])
    current['options'] = _quiz_options('goggles', step, state)
    return render_template('quiz.html', quiz_key='goggles', quiz=GOGGLES_QUIZ,
                           step=step, step_data=current, state=state,
                           total_steps=len(steps))


@app.route('/pages/goggles-quiz/results')
def goggles_quiz_results():
    state = _quiz_state('goggles')
    mapped = {'who': state.get('0', 'Adults'), 'swim': state.get('1', 'Fitness'),
              'lens': state.get('2', 'All lens types')}
    recs = _goggles_recommendations(mapped)
    return render_template('quiz_results.html', quiz_key='goggles',
                           quiz=GOGGLES_QUIZ, answers=mapped, cards=_product_cards(recs))


# ---------------------------------------------------------------------------
# Content pages
# ---------------------------------------------------------------------------

@app.route('/pages/<slug>')
def content_page(slug):
    page = ContentPage.query.filter_by(slug=slug).first_or_404()
    template = 'hub_page.html' if page.is_hub else 'content_page.html'
    featured = []
    for s in page.featured_slugs():
        p = Product.query.filter_by(slug=s).first()
        if p:
            featured.append(p)
    athletes = Athlete.query.order_by(Athlete.sort).all()
    return render_template(template, page=page, athletes=athletes,
                           featured=_product_cards(featured))


@app.route('/pages/team-speedo')
def team_speedo():
    athletes = Athlete.query.order_by(Athlete.sort).all()
    return render_template('team_speedo.html', athletes=athletes)


@app.route('/pages/team-speedo-<slug>')
def athlete_detail(slug):
    athlete = Athlete.query.filter_by(slug=slug).first_or_404()
    articles = Article.query.order_by(Article.sort).limit(3).all()
    return render_template('athlete.html', a=athlete, articles=articles)


@app.route('/blogs/news/')
def blog_index():
    articles = Article.query.order_by(Article.sort).all()
    return render_template('blog_index.html', articles=articles)


@app.route('/blogs/news/<slug>')
def blog_article(slug):
    article = Article.query.filter_by(slug=slug).first_or_404()
    return render_template('blog_article.html', a=article)


@app.route('/pages/faqs')
def faqs():
    entries = FaqEntry.query.order_by(FaqEntry.sort).all()
    return render_template('faqs.html', entries=entries)


@app.route('/pages/size-guides')
def size_guides():
    return render_template('size_guides.html', guides=SIZE_GUIDES)


@app.route('/pages/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        first = (request.form.get('first_name') or '').strip()
        last = (request.form.get('last_name') or '').strip()
        email = (request.form.get('email') or '').strip()
        category = request.form.get('category', '')
        subcategory = request.form.get('subcategory', '')
        message = (request.form.get('message') or '').strip()
        errors = []
        if not first or not last:
            errors.append('Enter your first and last name.')
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            errors.append('Enter a valid email address.')
        if not category:
            errors.append('Choose a category.')
        if not message or len(message) < 10:
            errors.append('Tell us a bit more (at least 10 characters).')
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('contact.html', form=request.form)
        case_ref = 'CAS' + str(100000 + ContactMessage.query.count() + 1)
        db.session.add(ContactMessage(case_ref=case_ref,
                                      user_id=current_user.id if current_user.is_authenticated else None,
                                      first_name=first, last_name=last, email=email,
                                      category=category, subcategory=subcategory,
                                      order_number=(request.form.get('order_number') or '').strip(),
                                      address_line=(request.form.get('address_line') or '').strip(),
                                      postcode=(request.form.get('postcode') or '').strip(),
                                      message=message,
                                      submitted_on=MIRROR_REFERENCE_DATE.isoformat()))
        db.session.commit()
        return render_template('contact.html', case_ref=case_ref, form={})
    return render_template('contact.html', form={})


@app.route('/newsletter', methods=['POST'])
def newsletter():
    email = (request.form.get('email') or '').strip()
    if re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        db.session.add(NewsletterSignup(email=email,
                                        signed_up_on=MIRROR_REFERENCE_DATE.isoformat()))
        db.session.commit()
        flash('Thanks for joining the Speedo community. Your welcome code is '
              'WELCOME15 — 15% off your first order.', 'success')
    else:
        flash('Enter a valid email address.', 'error')
    return redirect(request.form.get('next') or url_for('index'))


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.route('/_health')
def health():
    from _health import health
    return health()


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def seed_database():
    if Product.query.count() > 0:
        return
    from seed_data import run_seed
    run_seed(db, Department, NavGroup, NavLink, Collection, CollectionMembership,
             Product, ProductSize, Athlete, Article, ContentPage, FaqEntry,
             DiscountCode)


def seed_benchmark_users():
    if User.query.filter_by(email='alice.j@test.com').first():
        return
    from seed_data import run_seed_users
    run_seed_users(db, User, Address, PaymentCard, CartItem, WishlistItem,
                   Order, OrderItem, Product)


with app.app_context():
    db.create_all()
    seed_database()
    seed_benchmark_users()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
