#!/usr/bin/env python3
"""trader_joes — a WebHarbor mirror of https://www.traderjoes.com/

Flask + SQLite mirror of the Trader Joe's grocery portal: the home page
with its hero banner, What's New and featured product rails, the product
catalog (four top-level categories with subcategories, dietary
characteristics and fun-tag filters, six sort orders, 15-per-page
pagination), per-product detail pages carrying the captured description,
story, nutrition panels, ingredients, allergens and related products, the
recipe library with category and fun-tag filters, the store locator with
radius search and My Store selection, the announcements board with its
category filters, the Discover section (guides, stories, entertaining),
the podcast page, the Fearless Flyer e-newsletter signup and the gift
card balance inquiry — plus authenticated shopping lists seeded for four
benchmark users.

Content comes from the tracked source_data/*.json snapshots captured from
www.traderjoes.com on 2026-09-30/10-01 (see provenance.json); the SQLite
seed is materialized deterministically at image build time
(PYTHONHASHSEED=0). The shopping list, My Store preference, newsletter
subscription and gift card balance flows are original mirror code seeded
with deterministic benchmark fixtures (u_s_customs precedent).
"""
import json
import math
import os
import re
from datetime import date, datetime, timezone

from flask import (Flask, abort, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_bcrypt import Bcrypt
from flask_login import (LoginManager, UserMixin, current_user,
                         login_required, login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from markupsafe import Markup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, instance_path=os.path.join(BASE_DIR, 'instance'))
app.config["SECRET_KEY"] = os.environ.get("TRADER_JOES_SECRET_KEY") or "webharbor-trader-joes-dev-key"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'TRADER_JOES_DB_URI', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'trader_joes.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

db = SQLAlchemy(app)

# ---- deterministic schema creation -------------------------------------
# SQLAlchemy's create_all() emits CREATE INDEX statements in Table.indexes
# set order; that set is keyed by object identity, so the DDL order varies
# between processes and two seed builds would not be byte-identical. We
# therefore declare no index=True columns and create the indexes here in
# sorted order, with tables created in sorted-name order as well.
SCHEMA_INDEX_DDL = (
    'CREATE INDEX IF NOT EXISTS ix_announcements_category'
    ' ON announcements (category)',
    'CREATE INDEX IF NOT EXISTS ix_cms_pages_page'
    ' ON cms_pages (page)',
    'CREATE INDEX IF NOT EXISTS ix_editorials_kind'
    ' ON editorials (kind)',
    'CREATE INDEX IF NOT EXISTS ix_podcast_episodes_idx'
    ' ON podcast_episodes (idx)',
    'CREATE INDEX IF NOT EXISTS ix_products_category_ids'
    ' ON products (category_ids)',
    'CREATE INDEX IF NOT EXISTS ix_products_new_product'
    ' ON products (new_product)',
    'CREATE INDEX IF NOT EXISTS ix_products_promotion'
    ' ON products (promotion)',
    'CREATE INDEX IF NOT EXISTS ix_shopping_items_user_id'
    ' ON shopping_items (user_id)',
    'CREATE INDEX IF NOT EXISTS ix_stores_city'
    ' ON stores (city)',
    'CREATE INDEX IF NOT EXISTS ix_stores_state'
    ' ON stores (state)',
)


def create_schema():
    """Create all tables and indexes in a deterministic order."""
    tables = [db.metadata.tables[name]
              for name in sorted(db.metadata.tables)]
    db.metadata.create_all(db.engine, tables=tables)
    from sqlalchemy import text as _sa_text
    with db.engine.begin() as conn:
        for stmt in SCHEMA_INDEX_DDL:
            conn.execute(_sa_text(stmt))


bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to continue.'
csrf = CSRFProtect(app)

MIRROR_DATE = date(2026, 10, 1)
MIRROR_TS = '2026-10-01'
SITE_NAME = 'trader_joes'
UPSTREAM = 'https://www.traderjoes.com/'
# bcrypt hash of 'TestPass123!' — frozen so the seed DB is byte-reproducible.
BENCHMARK_PASSWORD_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')


def _load(name):
    with open(os.path.join(BASE_DIR, 'source_data', name),
              encoding='utf-8') as f:
        return json.load(f)


# ------------------------------------------------------------ image paths --

# DAM paths that were deduplicated at capture time (byte-identical upstream
# twins): both URLs render the single stored file.
_ALIAS_MAP = None


def _aliases():
    global _ALIAS_MAP
    if _ALIAS_MAP is None:
        _ALIAS_MAP = {}
        path = os.path.join(BASE_DIR, 'source_data', 'image_aliases.json')
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                _ALIAS_MAP.update(json.load(f).get('aliases', {}))
    return _ALIAS_MAP


def dam_url(dam_path):
    """Template helper: local static URL for an upstream DAM asset path.

    Every image under /content/dam/trjo/... is stored as its upstream
    webp-640 rendition (the bytes the live site serves on narrow screens),
    so the local file is the DAM path with the original extension swapped
    for .webp. A handful of upstream assets have no webp rendition and are
    stored in their original format.
    """
    if not dam_path:
        return None
    dam_path = _aliases().get(dam_path, dam_path)
    prefix = '/content/dam/trjo/'
    if not dam_path.startswith(prefix):
        # non-DAM asset (external video poster etc.) — not mirrored
        return None
    rel = dam_path[len(prefix):]
    base = rel.rsplit('.', 1)[0] if '.' in rel.rsplit('/', 1)[-1] else rel
    for ext in ('.webp', '.png', '.jpg', '.gif'):
        if os.path.exists(os.path.join(BASE_DIR, 'static', 'images',
                                       'upstream', base + ext)):
            return url_for('static', filename=f'images/upstream/{base}{ext}')
    # upstream asset that 404s on the live site (three known cases) —
    # the live pages render a broken image there as well.
    return None


app.jinja_env.globals['dam_url'] = dam_url


def toggle(values, value):
    """Facet toggle helper for Jinja: add value if absent, remove if present."""
    values = list(values or [])
    if value in values:
        return [v for v in values if v != value]
    values.append(value)
    return values


app.jinja_env.globals['toggle'] = toggle


def plain(html_text):
    """Strip tags from a captured rich-text blob for meta/list contexts."""
    if not html_text:
        return ''
    text = re.sub(r'<[^>]+>', ' ', str(html_text))
    return re.sub(r'\s+', ' ', text).replace('&nbsp;', ' ').strip()


app.jinja_env.filters['plain'] = plain


def rich(html_text):
    """Captured rich text: rewrite absolute upstream URLs and AEM content
    paths to local mirror paths so every link stays inside the site."""
    if not html_text:
        return ''
    text = str(html_text)
    text = text.replace('https://www.traderjoes.com', '')
    text = text.replace('http://www.traderjoes.com', '')
    text = text.replace('/content/trjo/us/en', '')
    text = re.sub(r'(href="[^"]*)\.html(")', r'\1\2', text)
    return text


app.jinja_env.filters['rich'] = rich
app.jinja_env.filters['from_json'] = lambda s: json.loads(s) if s else []
app.jinja_env.globals['from_json'] = lambda s: json.loads(s) if s else []
app.jinja_env.globals['product_by_sku'] = lambda sku: db.session.get(Product, sku)


def product_link(product):
    """Upstream-style PDP URL: /home/products/pdp/<url_key>-<sku>."""
    key = product.url_key or re.sub(r'[^a-z0-9]+', '-',
                                    (product.name or '').lower()).strip('-')
    return url_for('product_detail', page_key=f'{key}-{product.sku}')


app.jinja_env.globals['product_link'] = product_link


def category_link(cat):
    key = cat.url_key or 'category'
    return url_for('category', slug=key, cat_id=cat.id)


app.jinja_env.globals['category_link'] = category_link


# ----------------------------------------------------------------- models --

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    joined = db.Column(db.String(10))


class ShoppingItem(db.Model):
    __tablename__ = 'shopping_items'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sku = db.Column(db.String(16), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    added_at = db.Column(db.String(10), nullable=False)


class UserStore(db.Model):
    __tablename__ = 'user_stores'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    clientkey = db.Column(db.String(16), nullable=False)


class Subscriber(db.Model):
    __tablename__ = 'subscribers'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(190), unique=True, nullable=False)
    status = db.Column(db.String(16), nullable=False, default='subscribed')
    created_at = db.Column(db.String(10), nullable=False)


class GiftCard(db.Model):
    __tablename__ = 'gift_cards'
    card_number = db.Column(db.String(32), primary_key=True)
    balance = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(16), nullable=False, default='active')


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    path = db.Column(db.String(64), nullable=False)
    url_key = db.Column(db.String(128), nullable=False)
    product_count = db.Column(db.Integer, nullable=False, default=0)
    parent_id = db.Column(db.Integer)


class Product(db.Model):
    __tablename__ = 'products'
    sku = db.Column(db.String(16), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    item_title = db.Column(db.String(255), nullable=False)
    url_key = db.Column(db.String(255))
    retail_price = db.Column(db.Float)
    sales_size = db.Column(db.String(32))
    sales_uom_description = db.Column(db.String(32))
    primary_image = db.Column(db.String(255))
    context_image = db.Column(db.String(255))
    other_images = db.Column(db.Text)          # JSON array of DAM paths
    item_description = db.Column(db.Text)
    item_story_marketing = db.Column(db.Text)
    item_story_qil = db.Column(db.Text)
    use_and_demo = db.Column(db.Text)
    item_characteristics = db.Column(db.Text)   # JSON array
    fun_tags = db.Column(db.Text)              # JSON array
    product_label = db.Column(db.String(32))
    country_of_origin = db.Column(db.String(64))
    availability = db.Column(db.String(8))
    new_product = db.Column(db.Integer, nullable=False, default=0)
    promotion = db.Column(db.Integer, nullable=False, default=0)
    category_ids = db.Column(db.String(128), nullable=False)  # "2/8/29/32"
    category_names = db.Column(db.Text)         # JSON array
    first_published_date = db.Column(db.String(32))
    nutrition = db.Column(db.Text)              # JSON array of panels
    ingredients = db.Column(db.Text)            # JSON array
    allergens = db.Column(db.Text)              # JSON array
    related_skus = db.Column(db.Text)           # JSON array

    def chars(self):
        return json.loads(self.item_characteristics or '[]')

    def tags(self):
        return json.loads(self.fun_tags or '[]')

    def other_images_list(self):
        return json.loads(self.other_images or '[]')

    def nutrition_panels(self):
        return json.loads(self.nutrition or '[]')

    def ingredient_list(self):
        rows = json.loads(self.ingredients or '[]')
        return [r.get('ingredient') for r in rows if r.get('ingredient')]

    def allergen_list(self):
        rows = json.loads(self.allergens or '[]')
        return [r.get('ingredient') for r in rows if r.get('ingredient')]

    def related_products(self):
        skus = json.loads(self.related_skus or '[]')
        if not skus:
            return []
        found = (Product.query.filter(Product.sku.in_(skus)).all())
        order = {s: i for i, s in enumerate(skus)}
        found.sort(key=lambda p: order.get(p.sku, 999))
        return found

    def price_text(self):
        if self.availability != '1' or self.retail_price is None:
            return 'Not available'
        size = ''
        if self.sales_size:
            size = f'/{self.sales_size} {self.sales_uom_description or ""}'.rstrip()
        return f'${self.retail_price:.2f}{size}'


class Recipe(db.Model):
    __tablename__ = 'recipes'
    slug = db.Column(db.String(190), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    image_src = db.Column(db.String(255))
    categories = db.Column(db.Text)    # JSON array of tag names
    fun_tags = db.Column(db.Text)      # JSON array
    ingredients = db.Column(db.Text)   # JSON array of strings
    directions = db.Column(db.Text)    # JSON array of step blocks
    serves_min = db.Column(db.Integer)
    serves_max = db.Column(db.Integer)
    minutes_to_cook = db.Column(db.Integer)
    hours_to_cook = db.Column(db.Integer)
    minutes_to_cook2 = db.Column(db.Integer)
    hours_to_cook2 = db.Column(db.Integer)

    def cats(self):
        return json.loads(self.categories or '[]')

    def tags(self):
        return json.loads(self.fun_tags or '[]')

    def ingredient_list(self):
        return json.loads(self.ingredients or '[]')

    def direction_blocks(self):
        return json.loads(self.directions or '[]')

    def time_text(self):
        """The upstream Time rendering: each endpoint is '<H> h <M> mins'
        with the zero parts omitted, and the two captured cook times join
        as 'A - B' when the second differs ('15 mins - 25 mins',
        '55 mins - 1 h 10 mins', '7 h 35 mins - 11 h 45 mins',
        '1 h - 1 h 15 mins'); recipes whose captured times are all zero
        render no value, exactly like the live recipe pages (verified
        against www.traderjoes.com 2026-10-01: bacon-apple-brie-panini,
        zucchini-ricotta-rolls, salted-maple-walnut-pie,
        almond-butter-dipping-sauce, katsu-style-soyaki-tofu,
        scallop-ceviche, baby-corn-feta-salad)."""
        def endpoint(hours, minutes):
            parts = []
            if hours:
                parts.append(f'{hours} h')
            if minutes:
                parts.append(f'{minutes} mins')
            return ' '.join(parts)

        first = endpoint(self.hours_to_cook or 0, self.minutes_to_cook or 0)
        if not ((self.hours_to_cook2 or 0) or (self.minutes_to_cook2 or 0)):
            return first
        second = endpoint(self.hours_to_cook2, self.minutes_to_cook2)
        if second == first:
            return first
        if not first:
            return f'- {second}'
        return f'{first} - {second}'


class Store(db.Model):
    __tablename__ = 'stores'
    clientkey = db.Column(db.String(16), primary_key=True)
    uid = db.Column(db.Integer)
    name = db.Column(db.String(128), nullable=False)
    address1 = db.Column(db.String(255))
    address2 = db.Column(db.String(255))
    city = db.Column(db.String(128), nullable=False)
    state = db.Column(db.String(8), nullable=False)
    postalcode = db.Column(db.String(16))
    country = db.Column(db.String(8))
    phone = db.Column(db.String(32))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    county = db.Column(db.String(64))
    hours = db.Column(db.Text)          # JSON object day-> [open, close]
    bho = db.Column(db.Text)            # JSON array (business hours matrix)
    holiday_hours = db.Column(db.Text)
    coming_soon = db.Column(db.Integer, nullable=False, default=0)
    temp_note = db.Column(db.Text)
    holiday_note = db.Column(db.Text)
    text_comments = db.Column(db.Text)
    curbside_pickup = db.Column(db.String(8))
    liquor = db.Column(db.String(8))
    wine = db.Column(db.String(8))
    beer = db.Column(db.String(8))
    alcohol_message = db.Column(db.Text)
    parking_notes = db.Column(db.Text)
    directions_notes = db.Column(db.Text)
    about_copy = db.Column(db.Text)
    open_date = db.Column(db.String(64))
    website = db.Column(db.String(255))

    def hours_map(self):
        return json.loads(self.hours or '{}')

    def address_text(self):
        parts = [self.address1 or '']
        if self.address2:
            parts.append(self.address2)
        parts.append(f'{self.city}, {self.state} {self.postalcode or ""}')
        return ' '.join(parts).strip()

    def distance_from(self, lat, lng):
        if self.latitude is None or self.longitude is None:
            return None
        rlat, rlng = math.radians(lat), math.radians(lng)
        slat, slng = math.radians(self.latitude), math.radians(self.longitude)
        a = (math.sin((slat - rlat) / 2) ** 2
             + math.cos(rlat) * math.cos(slat)
             * math.sin((slng - rlng) / 2) ** 2)
        return 3958.7613 * 2 * math.asin(math.sqrt(a))


class Announcement(db.Model):
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(64), nullable=False)
    category_title = db.Column(db.String(64), nullable=False)
    publish_date = db.Column(db.String(10), nullable=False)
    body = db.Column(db.Text)
    image = db.Column(db.String(255))


class Editorial(db.Model):
    __tablename__ = 'editorials'
    slug = db.Column(db.String(190), primary_key=True)
    kind = db.Column(db.String(8), nullable=False)   # guide | story
    title = db.Column(db.String(255), nullable=False)
    publish_date = db.Column(db.String(10), nullable=False)
    hero = db.Column(db.String(255))
    blocks = db.Column(db.Text)          # JSON array
    product_skus = db.Column(db.Text)    # JSON array
    related = db.Column(db.Text)         # JSON object

    def block_list(self):
        return json.loads(self.blocks or '[]')

    def sku_list(self):
        return json.loads(self.product_skus or '[]')


class Entertaining(db.Model):
    __tablename__ = 'entertaining'
    slug = db.Column(db.String(190), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(64))
    publish_date = db.Column(db.String(10), nullable=False)
    description = db.Column(db.Text)
    page_path = db.Column(db.String(255))


class PodcastEpisode(db.Model):
    __tablename__ = 'podcast_episodes'
    idx = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    pub_date = db.Column(db.String(40), nullable=False)
    description = db.Column(db.Text)
    audio_url = db.Column(db.String(255))


class CMSPage(db.Model):
    __tablename__ = 'cms_pages'
    page = db.Column(db.String(64), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    h1 = db.Column(db.String(255))
    blocks = db.Column(db.Text)   # JSON array

    def block_list(self):
        return json.loads(self.blocks or '[]')


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ------------------------------------------------------------- seed gates --

def seed_database():
    if Product.query.count() > 0:
        return
    from seed_lib import build_seed
    build_seed(db, bcrypt)


def seed_benchmark_users():
    if User.query.filter_by(email='alice.j@test.com').first():
        return
    from seed_lib import build_benchmark_users
    build_benchmark_users(db, bcrypt)


# ------------------------------------------------------------ nav helpers --

NAV_L2 = None


def nav_categories():
    """Top-level product nav: the four L2 categories with L3 children
    (the tree root id=2 is the virtual Products node)."""
    global NAV_L2
    if NAV_L2 is None:
        tops = Category.query.filter_by(level=2).order_by(Category.id).all()
        NAV_L2 = []
        for top in tops:
            children = Category.query.filter_by(
                parent_id=top.id).order_by(Category.id).all()
            NAV_L2.append((top, children))
    return NAV_L2


@app.context_processor
def inject_globals():
    list_count = 0
    my_store = None
    if current_user.is_authenticated:
        list_count = db.session.query(
            db.func.sum(ShoppingItem.quantity)).filter_by(
            user_id=current_user.id).scalar() or 0
        pref = UserStore.query.filter_by(user_id=current_user.id).first()
        if pref:
            my_store = Store.query.filter_by(clientkey=pref.clientkey).first()
    return {
        'nav_categories': nav_categories,
        'shopping_list_count': list_count,
        'my_store': my_store,
        'mirror_date': MIRROR_DATE,
    }


# ------------------------------------------------------------------ routes --

@app.route('/')
def home():
    home_record = db.session.get(CMSPage, 'home')
    home_data = json.loads(home_record.blocks) if home_record else {}
    featured = []
    for sku in home_data.get('featured_products', {}).get('skus', []):
        p = Product.query.filter_by(sku=sku).first()
        if p:
            featured.append(p)
    whats_new = _sort_products(None, 'Date', Product.query.filter_by(new_product=1).all())[:5]
    recipes_raw = home_data.get('recipes', {}).get('cards', [])
    recipe_cards = []
    for card in recipes_raw:
        slug = (card.get('pagePath') or '').rsplit('/', 1)[-1]
        r = Recipe.query.filter_by(slug=slug).first()
        if r:
            recipe_cards.append({'card': card, 'recipe': r})
    anns = (Announcement.query.order_by(Announcement.publish_date.desc())
            .limit(4).all())
    hero = home_data.get('hero', {})
    hero_link = None
    if hero.get('recipeOrPdp') == 'recipe' and hero.get('link'):
        slug = hero['link'].rsplit('/', 1)[-1]
        if Recipe.query.filter_by(slug=slug).first():
            hero_link = url_for('recipe_detail', slug=slug)
    hero_guide = Editorial.query.filter_by(title=hero.get('title')).first()
    if hero_guide:
        hero_link = url_for('guide_detail', slug=hero_guide.slug)
    editorial = (Editorial.query.filter_by(kind='story')
                 .order_by(Editorial.publish_date.desc()).limit(4).all())
    return render_template('home.html', hero=hero, hero_link=hero_link,
                           whats_new=whats_new, featured=featured,
                           recipe_cards=recipe_cards,
                           announcements=anns, editorial=editorial, hero_guide=hero_guide)


@app.route('/home')
def home_alias():
    return redirect(url_for('home'))


CATEGORY_TILE = {
    'food': 'bread.webp',
    'beverages': 'water.webp',
    'flowers-plants': 'plants.webp',
    'everything-else': 'cheese.webp',
}


@app.route('/home/products')
def products_hub():
    note = ('You won\u2019t find every Trader Joe\u2019s product represented on '
            'our website. The best place to go for information about our '
            'products \u2013 old favorites and new discoveries! \u2013 is your '
            'neighborhood Trader Joe\u2019s.')
    marketing = {
        'title': "So, What's New?",
        'text': ("Fall is here, and with it comes a bounty of new products. "
                 "Pumpkin this, maple that \u2014 you get the idea. Explore "
                 "the newest items on our shelves, and grab them before "
                 "they're gone. Many are here for a limited time only!"),
    }
    return render_template('products_hub.html', note=note,
                           marketing=marketing,
                           CATEGORY_TILE=CATEGORY_TILE)


@app.route('/home/products/category/')
@app.route('/home/products/category')
def category_root():
    food = Category.query.filter_by(url_key='food').first()
    if food:
        return redirect(url_for('category', slug='food', cat_id=food.id))
    return redirect(url_for('products_hub'))


SORT_ORDERS = ['Date', "What's new", 'Going fast', 'Price Low to High',
               'Price High to Low', 'Popularity']
CHARACTERISTIC_ORDER = ['Kosher', 'Organic', 'Gluten Free', 'Vegan',
                        'Dairy Free', 'Antibiotic Free', 'Fair Trade',
                        'Vegetarian', 'Grass Fed']
PAGE_SIZE = 15


def _parse_filters(raw):
    """Upstream encodes filters as ?filters={"characteristics":["Gluten Free"]}
    (JSON, URL-encoded). Accept the upstream shape and plain repeat params."""
    chars, tags, new_only = [], [], False
    raw = raw or ''
    if raw.strip().startswith('{'):
        try:
            data = json.loads(raw)
            chars = [str(c) for c in data.get('characteristics', [])]
            tags = [str(t) for t in data.get('funTags', [])]
            new_only = bool(data.get('areNewProducts'))
        except (ValueError, AttributeError):
            pass
    else:
        chars = [c for c in re.split(r'[|,]', raw) if c]
    return chars, tags, new_only


def _sort_products(query, sort, products):
    """Apply the six upstream sort orders deterministically."""
    if sort == 'Price Low to High':
        products.sort(key=lambda p: (p.retail_price if p.retail_price is not None
                                     else 1e12, p.item_title.lower()))
    elif sort == 'Price High to Low':
        products.sort(key=lambda p: (-p.retail_price if p.retail_price is not None
                                     else -1e12, p.item_title.lower()))
    elif sort == "What's new":
        products.sort(key=lambda p: (-p.new_product,
                                      p.first_published_date or '',
                                      p.item_title.lower()))
    elif sort == 'Going fast':
        products.sort(key=lambda p: (-p.promotion,
                                      0 if (p.product_label or '').strip()
                                      else 1,
                                      p.item_title.lower()))
    elif sort == 'Popularity':
        products.sort(key=lambda p: (-len(p.tags()), p.item_title.lower()))
    else:  # Date (upstream default): newest published first
        products.sort(key=lambda p: ((p.first_published_date or ''),
                                     p.item_title.lower()), reverse=True)
    return products


@app.route('/home/products/category/<slug>-<int:cat_id>')
def category(slug, cat_id):
    cat = db.session.get(Category, cat_id)
    if cat is None:
        abort(404)
    chars, tags, new_only = _parse_filters(request.args.get('filters'))
    sort = request.args.get('sortBy', 'Date')
    if sort not in SORT_ORDERS:
        sort = 'Date'
    try:
        page = max(1, int(request.args.get('page', 1)))
    except ValueError:
        page = 1

    all_products = (Product.query.filter(
        db.or_(Product.category_ids.like(f'%/{cat_id}/%'),
               Product.category_ids.like(f'{cat_id}/%'))).all())
    if new_only:
        all_products = [p for p in all_products if p.new_product]
    if chars:
        all_products = [p for p in all_products
                        if all(c in p.chars() for c in chars)]
    if tags:
        all_products = [p for p in all_products
                        if all(t in p.tags() for t in tags)]
    all_products = _sort_products(None, sort, all_products)

    total = len(all_products)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = min(page, total_pages)
    items = all_products[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]

    # facets: characteristic values present in this category, upstream order
    present_chars = {}
    present_tags = {}
    for p in all_products:
        for c in p.chars():
            present_chars[c] = present_chars.get(c, 0) + 1
        for t in p.tags():
            present_tags[t] = present_tags.get(t, 0) + 1
    char_facets = [(c, present_chars[c]) for c in CHARACTERISTIC_ORDER
                   if c in present_chars]
    extra_chars = sorted(c for c in present_chars
                         if c not in CHARACTERISTIC_ORDER)
    char_facets += [(c, present_chars[c]) for c in extra_chars]
    tag_facets = sorted(present_tags.items())

    children = (Category.query.filter_by(parent_id=cat.id)
                .order_by(Category.id).all())
    parent = db.session.get(Category, cat.parent_id) if cat.parent_id else None

    def _facet_url(new_chars=None, new_tags=None, new_sort=None, new_page=None):
        args = {}
        filters = {}
        if new_chars is not None:
            filters['characteristics'] = new_chars
        elif chars:
            filters['characteristics'] = chars
        if new_tags is not None:
            filters['funTags'] = new_tags
        elif tags:
            filters['funTags'] = tags
        if new_only:
            filters['areNewProducts'] = True
        if filters:
            args['filters'] = json.dumps(filters)
        s = sort if new_sort is None else new_sort
        if s != 'Date':
            args['sortBy'] = s
        pg = page if new_page is None else new_page
        if pg > 1:
            args['page'] = pg
        return url_for('category', slug=slug, cat_id=cat_id, **args)

    # Upstream renders the What's New heading (not the root category
    # name "Products") when the areNewProducts filter is active.
    heading = "What's New" if new_only else cat.name

    return render_template(
        'category.html', cat=cat, parent=parent, children=children,
        products=items, total=total, page=page, total_pages=total_pages,
        char_facets=char_facets, tag_facets=tag_facets,
        active_chars=chars, active_tags=tags, sort=sort,
        facet_url=_facet_url, page_size=PAGE_SIZE, heading=heading)


@app.route('/home/products/pdp/<page_key>')
def product_detail(page_key):
    # upstream PDP URLs come in two shapes: <url_key>-<sku> and
    # <sku>-<url_key>; the sku is always the six-digit run. Captured
    # rich text also carries the upstream short form <sku> (rendered
    # locally as /home/products/pdp/<sku> after the .html strip).
    m = (re.search(r'^(\d{6})-', page_key) or re.search(r'-(\d{6})$', page_key)
         or re.fullmatch(r'(\d{6})', page_key))
    if not m:
        abort(404)
    sku = m.group(1)
    product = db.session.get(Product, sku)
    if product is None:
        abort(404)
    crumbs = []
    for cid in [int(x) for x in product.category_ids.split('/') if x]:
        c = db.session.get(Category, cid)
        if c and c.level >= 1:
            crumbs.append(c)
    return render_template('pdp.html', product=product, crumbs=crumbs)


@app.route('/home/search')
def search():
    q = (request.args.get('q') or '').strip()
    try:
        page = max(1, int(request.args.get('page', 1)))
    except ValueError:
        page = 1
    if not q:
        return render_template('search.html', q=q, products=[], recipes=[],
                               editorial=[], total=0, page=1, total_pages=1,
                               page_size=PAGE_SIZE)
    like = f'%{q.lower()}%'
    products = Product.query.filter(
        db.or_(db.func.lower(Product.item_title).like(like),
               db.func.lower(Product.name).like(like))).all()
    products = _sort_products(None, 'Date', products)
    recipes = Recipe.query.filter(
        db.or_(db.func.lower(Recipe.title).like(like),
               db.func.lower(Recipe.description).like(like))).all()
    editorial = Editorial.query.filter(
        db.or_(db.func.lower(Editorial.title).like(like),
               db.func.lower(db.func.coalesce(Editorial.blocks, ''))
               .like(like))).all()
    entertaining = Entertaining.query.filter(
        db.or_(db.func.lower(Entertaining.title).like(like),
               db.func.lower(db.func.coalesce(Entertaining.description, ''))
               .like(like))).all()
    total = len(products) + len(recipes) + len(editorial) + len(entertaining)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = min(page, total_pages)
    start = (page - 1) * PAGE_SIZE
    return render_template(
        'search.html', q=q,
        products=products[start:start + PAGE_SIZE],
        product_total=len(products),
        recipes=recipes[:PAGE_SIZE], recipe_total=len(recipes),
        editorial=(editorial + entertaining)[:PAGE_SIZE],
        editorial_total=len(editorial) + len(entertaining),
        total=total, page=page, total_pages=total_pages,
        page_size=PAGE_SIZE)


RECIPE_CATEGORIES = [
    ('appetizer', 'Appetizers & Sides'),
    ('beverages', 'Beverages'),
    ('breakfast', 'Breakfast'),
    ('lunch', 'Lunch'),
    ('dinner', 'Dinner'),
    ('desserts', 'Desserts'),
]


@app.route('/home/recipes')
def recipes():
    active = [c for c in request.args.getlist('categories') if c]
    active_tags = [t for t in request.args.getlist('funTags') if t]
    try:
        page = max(1, int(request.args.get('page', 1)))
    except ValueError:
        page = 1
    rows = Recipe.query.all()
    if active:
        rows = [r for r in rows if any(c in r.cats() for c in active)]
    if active_tags:
        rows = [r for r in rows if any(t in r.tags() for t in active_tags)]
    rows.sort(key=lambda r: r.title.lower())
    total = len(rows)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = min(page, total_pages)
    items = rows[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]
    # the upstream recipes page shows a fixed, curated chip rail
    TAG_CHIP_RAIL = ["Let's Bake!", 'Fall Faves', 'Get Cozy', 'This & Chill',
                     'Cold Front', 'Finger Food', 'Crack a Beer',
                     'Rain or Shine', 'Alfresco Dining']
    tag_chips = TAG_CHIP_RAIL

    def _url(categories=None, tags=None, new_page=None):
        args = []
        cats = active if categories is None else categories
        tgs = active_tags if tags is None else tags
        if cats:
            for c in cats:
                args.append(('categories', c))
        if tgs:
            for t in tgs:
                args.append(('funTags', t))
        pg = page if new_page is None else new_page
        if pg > 1:
            args.append(('page', pg))
        return url_for('recipes', _external=False, **dict(args))

    return render_template('recipes.html', recipes=items, total=total,
                           page=page, total_pages=total_pages,
                           categories=RECIPE_CATEGORIES, active=active,
                           active_tags=active_tags, tag_chips=tag_chips,
                           facet_url=_url, page_size=PAGE_SIZE)


@app.route('/home/recipes/<slug>')
def recipe_detail(slug):
    recipe = db.session.get(Recipe, slug)
    if recipe is None:
        abort(404)
    # products referenced by the description's pdp links
    skus = set()
    for m in re.findall(r'/home/products/pdp/[a-z0-9-]+?-(\d{6})',
                        recipe.description or ''):
        skus.add(m)
    linked = []
    for sku in sorted(skus):
        p = db.session.get(Product, sku)
        if p:
            linked.append(p)
    return render_template('recipe_detail.html', recipe=recipe,
                           linked_products=linked)


# ------------------------------------------------------------- store search

RADIUS_CHOICES = ['5', '10', '25', '50', '100']


@app.route('/home/store-search')
def store_search():
    q = (request.args.get('q') or '').strip()
    radius = request.args.get('radius', '25')
    if radius not in RADIUS_CHOICES:
        radius = '25'
    state = (request.args.get('state') or '').strip().upper()
    results = None
    origin = None
    states = sorted({s.state for s in Store.query.all()})
    if state:
        results = (Store.query.filter_by(state=state)
                   .order_by(Store.name).all())
        origin = None
    elif q:
        ql = q.lower()
        anchor = None
        zips = (Store.query.filter(Store.postalcode.like(f'{q}%'))
                .order_by(Store.postalcode).all())
        if zips:
            anchor = zips[0]
        else:
            city = (Store.query.filter(
                db.func.lower(Store.city).like(f'{ql}%'))
                .order_by(Store.city).all())
            if city:
                anchor = city[0]
            else:
                named = Store.query.filter(
                    db.func.lower(Store.name).like(f'%{ql}%')).all()
                if named:
                    anchor = named[0]
        if anchor is None:
            results = []
            origin = None
        else:
            origin = anchor
            max_miles = float(radius)
            scored = []
            for s in Store.query.all():
                d = s.distance_from(anchor.latitude, anchor.longitude)
                if d is not None and d <= max_miles:
                    scored.append((d, s))
            scored.sort(key=lambda pair: (pair[0], pair[1].name))
            results = [s for _, s in scored]
    return render_template('store_search.html', q=q, radius=radius,
                           state=state, results=results, origin=origin,
                           states=states, radius_choices=RADIUS_CHOICES)


@app.route('/home/store-search/store/<clientkey>')
def store_detail(clientkey):
    store = db.session.get(Store, clientkey)
    if store is None:
        abort(404)
    return render_template('store_detail.html', store=store)


@app.route('/home/set-my-store/<clientkey>', methods=['POST'])
@login_required
def set_my_store(clientkey):
    store = db.session.get(Store, clientkey)
    if store is None:
        abort(404)
    pref = UserStore.query.filter_by(user_id=current_user.id).first()
    if pref is None:
        pref = UserStore(user_id=current_user.id, clientkey=clientkey)
        db.session.add(pref)
    else:
        pref.clientkey = clientkey
    db.session.commit()
    next_url = request.form.get('next') or url_for('store_search')
    return redirect(next_url)


# ------------------------------------------------------------ shopping list

@app.route('/home/shopping-list')
@login_required
def shopping_list():
    items = (ShoppingItem.query.filter_by(user_id=current_user.id)
             .order_by(ShoppingItem.id).all())
    rows = []
    for item in items:
        product = db.session.get(Product, item.sku)
        if product:
            rows.append((item, product))
    total = sum(i.quantity for i, _ in rows)
    estimated_cost = sum(round(p.retail_price * 100) * i.quantity for i, p in rows if p.retail_price is not None) / 100
    prices_complete = all(p.retail_price is not None for _, p in rows)
    return render_template('shopping_list.html', rows=rows, total=total, estimated_cost=estimated_cost, prices_complete=prices_complete)


@app.route('/home/shopping-list/add/<sku>', methods=['POST'])
def shopping_list_add(sku):
    product = db.session.get(Product, sku)
    if product is None:
        abort(404)
    if not current_user.is_authenticated:
        session['post_login_redirect'] = (request.form.get('next')
                                          or url_for('shopping_list'))
        return redirect(url_for('login'))
    item = ShoppingItem.query.filter_by(user_id=current_user.id,
                                        sku=sku).first()
    if item is None:
        item = ShoppingItem(user_id=current_user.id, sku=sku, quantity=1,
                            added_at=MIRROR_TS)
        db.session.add(item)
    else:
        item.quantity += 1
    db.session.commit()
    next_url = request.form.get('next') or request.referrer or url_for('shopping_list')
    return redirect(next_url)


@app.route('/home/shopping-list/update/<int:item_id>', methods=['POST'])
@login_required
def shopping_list_update(item_id):
    item = db.session.get(ShoppingItem, item_id)
    if item is None or item.user_id != current_user.id:
        abort(404)
    action = request.form.get('action')
    if action == 'increase':
        item.quantity += 1
    elif action == 'decrease':
        item.quantity -= 1
        if item.quantity <= 0:
            db.session.delete(item)
    elif action == 'remove':
        db.session.delete(item)
    db.session.commit()
    return redirect(url_for('shopping_list'))


@app.route('/home/shopping-list/clear', methods=['POST'])
@login_required
def shopping_list_clear():
    ShoppingItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return redirect(url_for('shopping_list'))


# ------------------------------------------------------------- announcements

ANNOUNCEMENT_CATEGORIES = [
    ('customer-updates', 'Customer Updates'),
    ('store-openings', 'Store Openings'),
    ('special-trading-hours', 'Special Trading Hours'),
    ('caring-for-our-communities', 'Caring For Our Communities'),
    ('recalls', 'Recalls'),
]


@app.route('/home/announcements')
def announcements():
    active = request.args.get('category', '')
    query = Announcement.query
    if active:
        query = query.filter_by(category=active)
    rows = query.order_by(Announcement.publish_date.desc(),
                          Announcement.id.desc()).all()
    counts = {}
    for a in Announcement.query.all():
        counts[a.category] = counts.get(a.category, 0) + 1
    return render_template('announcements.html', announcements=rows,
                           categories=ANNOUNCEMENT_CATEGORIES, active=active,
                           counts=counts)


@app.route('/home/announcements/food-safety-overview')
def food_safety_overview():
    page = CMSPage.query.filter_by(page='food-safety').first()
    if page is None:
        abort(404)
    return render_template('cms_page.html', page=page,
                           crumbs=[('Home', url_for('home')),
                                   ('Announcements', url_for('announcements'))])


# ---------------------------------------------------------------- discover --

@app.route('/home/discover')
def discover():
    guides = (Editorial.query.filter_by(kind='guide')
              .order_by(Editorial.publish_date.desc()).limit(6).all())
    stories = (Editorial.query.filter_by(kind='story')
               .order_by(Editorial.publish_date.desc()).limit(6).all())
    return render_template('discover.html', guides=guides, stories=stories)


@app.route('/home/discover/guides')
def guides():
    rows = (Editorial.query.filter_by(kind='guide')
            .order_by(Editorial.publish_date.desc(),
                      Editorial.slug).all())
    return render_template('editorial_list.html', rows=rows, kind='guide')


@app.route('/home/discover/stories')
def stories():
    rows = (Editorial.query.filter_by(kind='story')
            .order_by(Editorial.publish_date.desc(),
                      Editorial.slug).all())
    return render_template('editorial_list.html', rows=rows, kind='story')


@app.route('/home/discover/guides/<slug>')
def guide_detail(slug):
    row = db.session.get(Editorial, slug)
    if row is None or row.kind != 'guide':
        abort(404)
    return render_template('editorial_detail.html', row=row)


@app.route('/home/discover/stories/<slug>')
def story_detail(slug):
    row = db.session.get(Editorial, slug)
    if row is None or row.kind != 'story':
        abort(404)
    return render_template('editorial_detail.html', row=row)


@app.route('/home/discover/entertaining')
def entertaining():
    rows = (Entertaining.query
            .order_by(Entertaining.publish_date.desc(),
                      Entertaining.slug).all())
    return render_template('entertaining.html', rows=rows)


@app.route('/home/discover/entertaining/<slug>')
def entertaining_detail(slug):
    row = db.session.get(Entertaining, slug)
    if row is None:
        # entertaining articles are editorials under a different listing
        row = db.session.get(Editorial, slug)
        if row is None:
            abort(404)
        return render_template('editorial_detail.html', row=row)
    return render_template('entertaining_detail.html', row=row)


# ----------------------------------------------------------------- podcast --

@app.route('/home/podcast')
def podcast():
    page = CMSPage.query.filter_by(page='podcast').first()
    episodes = (PodcastEpisode.query.order_by(PodcastEpisode.idx.asc())
               .limit(12).all())
    return render_template('podcast.html', page=page, episodes=episodes)


# -------------------------------------------------------------- cms pages --

def _cms_page(page_key, template='cms_page.html', **extra):
    page = CMSPage.query.filter_by(page=page_key).first()
    if page is None:
        abort(404)
    return render_template(template, page=page, **extra)


@app.route('/home/about-us')
def about_us():
    return _cms_page('about')


@app.route('/home/careers')
def careers():
    return _cms_page('careers')


@app.route('/home/contact-us')
def contact_us():
    return _cms_page('contact')


@app.route('/home/FAQ')
def faq():
    return _cms_page('faq')


@app.route('/home/neighborhood-shares')
def neighborhood_shares():
    return _cms_page('neighborhood')


# -------------------------------------------------------------- newsletter --

@app.route('/home/subscribe')
def subscribe():
    return render_template('subscribe.html', email='', done=False,
                           removed=False)


@app.route('/home/subscribe', methods=['POST'])
def subscribe_post():
    email = (request.form.get('email') or '').strip().lower()
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return render_template('subscribe.html', email=email, done=False,
                               removed=False,
                               error='Please enter a valid email address.')
    row = Subscriber.query.filter_by(email=email).first()
    if row is None:
        row = Subscriber(email=email, status='subscribed',
                         created_at=MIRROR_TS)
        db.session.add(row)
    else:
        row.status = 'subscribed'
    db.session.commit()
    return render_template('subscribe.html', email=email, done=True,
                           removed=False)


@app.route('/home/unsubscribe', methods=['GET', 'POST'])
def unsubscribe():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        row = Subscriber.query.filter_by(email=email).first()
        if row is not None and row.status == 'subscribed':
            row.status = 'unsubscribed'
            db.session.commit()
            return render_template('subscribe.html', email=email, done=False,
                                   removed=True)
        return render_template('subscribe.html', email=email, done=False,
                               removed=False, error=(
                                   'That email address is not on our '
                                   'newsletter list.'))
    return render_template('unsubscribe.html')


# -------------------------------------------------------------- gift cards --

@app.route('/home/gift-card-balance-inquiry')
def gift_card():
    return render_template('gift_card.html', card=None, error=None)


@app.route('/home/gift-card-balance-inquiry', methods=['POST'])
def gift_card_post():
    number = re.sub(r'[^0-9]', '', request.form.get('card_number') or '')
    if len(number) < 12:
        return render_template('gift_card.html', card=None, error=(
            'Please enter the full gift card number (at least 12 digits).'))
    row = GiftCard.query.filter_by(card_number=number).first()
    if row is None:
        return render_template('gift_card.html', card=None, error=(
            'We could not find a gift card with that number. Please check '
            'the number on the back of your card and try again.'))
    if row.status != 'active':
        return render_template('gift_card.html', card=None, error=(
            'This gift card is no longer active. Please call '
            '1-888-556-6619 for assistance.'))
    return render_template('gift_card.html', card=row, error=None)


# ---------------------------------------------------------------- accounts --

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html', error=None,
                               email='', name='')
    email = (request.form.get('email') or '').strip().lower()
    name = (request.form.get('name') or '').strip()
    password = request.form.get('password') or ''
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return render_template('signup.html', error=(
            'Please enter a valid email address.'), email=email, name=name)
    if len(password) < 8:
        return render_template('signup.html', error=(
            'Password must be at least 8 characters long.'), email=email,
            name=name)
    if User.query.filter_by(email=email).first():
        return render_template('signup.html', error=(
            'An account with that email already exists. Please log in '
            'instead.'), email=email, name=name)
    user = User(email=email, name=name or email.split('@')[0],
                password_hash=bcrypt.generate_password_hash(password),
                joined=MIRROR_TS)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    target = session.pop('post_login_redirect', None) or url_for('home')
    return redirect(target)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', error=None, email='')
    email = (request.form.get('email') or '').strip().lower()
    password = request.form.get('password') or ''
    user = User.query.filter_by(email=email).first()
    if user is None or not bcrypt.check_password_hash(user.password_hash,
                                                      password):
        return render_template('login.html', error=(
            'Invalid email or password.'), email=email)
    login_user(user)
    target = session.pop('post_login_redirect', None) or url_for('home')
    return redirect(target)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/home/privacy-policy')
def privacy_policy():
    return _cms_page('privacy')


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


# ------------------------------------------------------------------- boot --

def main():
    with app.app_context():
        create_schema()
        seed_database()
        seed_benchmark_users()


with app.app_context():
    create_schema()
    if os.environ.get('TRADER_JOES_AUTO_SEED', '1') == '1':
        seed_database()
        seed_benchmark_users()


if __name__ == '__main__':
    main()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 40140)))
