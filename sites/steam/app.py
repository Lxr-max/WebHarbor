#!/usr/bin/env python3
"""steam — a WebHarbor mirror of https://store.steampowered.com/

Flask + SQLite mirror of the Steam game store, rebuilt from real upstream
captures (probe 2026-10-01: HTTP 200 on every core endpoint):

  * Store home — the live top-sellers / new-releases / specials rails and
    the genre taxonomy captured from the store front page.
  * Search — the real search facet set: free-text term, genre, max price,
    OS support, review score, discounts-only, four sort orders, pagination.
  * Game detail — per-app pages with the real price/discount, short and
    full descriptions, genres, categories, publisher/developer credits,
    release date, review summary, screenshot gallery, the real Windows
    (and where published Mac/Linux) system requirements, and DLC lists.
  * Reviews — per-app review browsing with the real review-score summary
    and real user reviews (author, playtime, helpful votes, text),
    filterable by recommendation and sortable by recency/helpfulness.
  * Specials — the live discounted catalog with original price, discount
    percent and final price.
  * Bundles — real Steam bundles with their item lists, per-item prices,
    bundle price and the savings versus buying the items separately.
  * Publisher & developer pages — per-creator rosters with game counts
    and price ranges, reachable from every game's detail page.
  * News — the real per-app news feeds (titles, feeds, dates, bodies)
    aggregated into a hub, per-game pages and per-item pages.
  * Wishlist, cart, checkout and order history (CSRF-protected), plus the
    account surface (signup, login, orders).

Every content record and every image under static/images/ comes from the
live upstream (see provenance.json and asset_inventory.json); the only
authored rows are the four benchmark user accounts and their fixture
wishlists/orders. The SQLite seed is materialized deterministically at
image build time (PYTHONHASHSEED=0).
"""
import json
import os
import re
import unicodedata
from datetime import datetime, timezone

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_bcrypt import Bcrypt
from flask_login import (LoginManager, UserMixin, current_user,
                         login_required, login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from markupsafe import Markup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, instance_path=os.path.join(BASE_DIR, 'instance'))
app.config["SECRET_KEY"] = os.environ.get("STEAM_SECRET_KEY") or \
    "webharbor-steam-dev-key"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'STEAM_DB_URI',
    f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'steam.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please sign in to continue.'
csrf = CSRFProtect(app)

MIRROR_TS = '2026-10-01'
SITE_NAME = 'steam'
UPSTREAM = 'https://store.steampowered.com/'
SOURCE = os.path.join(BASE_DIR, 'source_data')


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# bcrypt hash of 'TestPass123!' — frozen so the seed DB is byte-reproducible.
BENCHMARK_PASSWORD_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')

GENRE_ORDER = ['Action', 'Adventure', 'Massively Multiplayer', 'RPG',
               'Strategy', 'Simulation', 'Sports', 'Racing', 'Indie',
               'Casual', 'Free To Play']

SORT_LABELS = {
    'Relevance_DESC': 'Relevance',
    'Released_DESC': 'Release Date',
    'Name_ASC': 'Name',
    'Price_ASC': 'Price (low to high)',
    'Price_DESC': 'Price (high to low)',
}

REVIEW_FILTERS = {
    'all': 'All Reviews',
    'positive': 'Positive Only',
    'mixed': 'Mixed Only',
    'negative': 'Negative Only',
}

REVIEW_SORTS = {
    'recent': 'Most Recent',
    'helpful': 'Most Helpful',
}

PRICE_POINTS = [0, 5, 10, 15, 20, 30, 40, 50, 60]


def _load(name):
    with open(os.path.join(SOURCE, name), encoding='utf-8') as f:
        return json.load(f)


def _slugify(text):
    text = unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore')
    text = text.decode('ascii').lower()
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return text


def _now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _money(cents):
    if cents is None:
        return ''
    return f"${cents / 100:,.2f}"


@app.template_filter('money')
def _money_filter(cents):
    return _money(cents)


@app.template_global('_img')
def _img(path):
    if not path:
        return url_for('static', filename='images/steam-logo.png')
    return url_for('static', filename='images/' + path)


@app.template_global('qs_without_page')
def _qs_without_page():
    """Current query string minus the page param, for pager links."""
    pairs = [(k, v) for k, v in request.args.items(multi=True) if k != 'page']
    text = '&'.join(f'{k}={v}' for k, v in pairs)
    return ('?' + text) if text else ''


@app.template_global('qs_for')
def _qs_for(**overrides):
    """Current query string with specific params replaced."""
    merged = {k: v for k, v in request.args.items()}
    merged.update(overrides)
    pairs = [(k, v) for k, v in merged.items() if k != 'page']
    text = '&'.join(f'{k}={v}' for k, v in pairs)
    return ('?' + text) if text else ''


@app.template_filter('slugify')
def _slugify_filter(text):
    return _slugify(text)


@app.template_filter('hours')
def _hours_filter(minutes):
    try:
        return f"{float(minutes) / 60:,.1f}"
    except (TypeError, ValueError):
        return ''


@app.template_filter('datefmt')
def _datefmt_filter(ts):
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc) \
            .strftime('%B %-d, %Y')
    except (TypeError, ValueError, OSError):
        return ''


# ------------------------------------------------------------------ models --

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, unique=True, nullable=False)
    pw_hash = db.Column(db.Text, nullable=False)

    orders = db.relationship('Order', backref='user', lazy=True)
    wishlist = db.relationship('WishlistItem', backref='user', lazy=True)


class Game(db.Model):
    __tablename__ = 'games'
    id = db.Column(db.Integer, primary_key=True)
    appid = db.Column(db.Integer, unique=True, nullable=False)
    slug = db.Column(db.Text, unique=True, nullable=False)
    name = db.Column(db.Text, nullable=False)
    type = db.Column(db.Text, default='game')
    is_free = db.Column(db.Boolean, default=False)
    short_desc = db.Column(db.Text, default='')
    about = db.Column(db.Text, default='')
    detailed_desc = db.Column(db.Text, default='')
    supported_languages = db.Column(db.Text, default='')
    release_date = db.Column(db.Text, default='')
    coming_soon = db.Column(db.Boolean, default=False)
    price_cents = db.Column(db.Integer)
    initial_cents = db.Column(db.Integer)
    discount_pct = db.Column(db.Integer, default=0)
    header_img = db.Column(db.Text, default='')
    capsule_img = db.Column(db.Text, default='')
    platforms = db.Column(db.Text, default='{}')
    genres = db.Column(db.Text, default='[]')
    categories = db.Column(db.Text, default='[]')
    publishers = db.Column(db.Text, default='[]')
    developers = db.Column(db.Text, default='[]')
    review_score_desc = db.Column(db.Text, default='')
    review_pct = db.Column(db.Integer, default=0)
    total_positive = db.Column(db.Integer, default=0)
    total_negative = db.Column(db.Integer, default=0)
    total_reviews = db.Column(db.Integer, default=0)
    achievements_total = db.Column(db.Integer)
    required_age = db.Column(db.Integer, default=0)
    dlc_apps = db.Column(db.Text, default='[]')
    topseller_rank = db.Column(db.Integer)
    newrelease_rank = db.Column(db.Integer)

    @property
    def genre_list(self):
        return json.loads(self.genres)

    @property
    def category_list(self):
        return json.loads(self.categories)

    @property
    def publisher_list(self):
        return json.loads(self.publishers)

    @property
    def developer_list(self):
        return json.loads(self.developers)

    @property
    def platform_map(self):
        return json.loads(self.platforms)

    @property
    def dlc_list(self):
        return json.loads(self.dlc_apps)

    @property
    def final_price(self):
        return self.price_cents if self.price_cents is not None else 0

    @property
    def url(self):
        return url_for('app_page', appid=self.appid, slug=self.slug)


class Screenshot(db.Model):
    __tablename__ = 'screenshots'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    path_full = db.Column(db.Text, default='')
    idx = db.Column(db.Integer, default=0)


class SysReq(db.Model):
    __tablename__ = 'sysreqs'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    os = db.Column(db.Text, nullable=False)        # windows / mac / linux
    level = db.Column(db.Text, nullable=False)      # minimum / recommended
    specs = db.Column(db.Text, nullable=False, default='{}')

    @property
    def spec_map(self):
        return json.loads(self.specs)


class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    recommendationid = db.Column(db.Text, unique=True, nullable=False)
    author = db.Column(db.Text, nullable=False)
    author_games = db.Column(db.Integer, default=0)
    author_reviews = db.Column(db.Integer, default=0)
    playtime_forever = db.Column(db.Integer, default=0)
    playtime_at_review = db.Column(db.Integer, default=0)
    voted_up = db.Column(db.Boolean, default=True)
    votes_up = db.Column(db.Integer, default=0)
    votes_funny = db.Column(db.Integer, default=0)
    steam_purchase = db.Column(db.Boolean, default=True)
    received_for_free = db.Column(db.Boolean, default=False)
    early_access = db.Column(db.Boolean, default=False)
    text = db.Column(db.Text, nullable=False, default='')
    timestamp_created = db.Column(db.Integer, default=0)
    language = db.Column(db.Text, default='english')


class NewsItem(db.Model):
    __tablename__ = 'newsitems'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    gid = db.Column(db.Text, unique=True, nullable=False)
    title = db.Column(db.Text, nullable=False)
    url = db.Column(db.Text, default='')
    is_external_url = db.Column(db.Boolean, default=False)
    author = db.Column(db.Text, default='')
    contents = db.Column(db.Text, default='')
    feedlabel = db.Column(db.Text, default='')
    date = db.Column(db.Integer, default=0)
    feedname = db.Column(db.Text, default='')


class Bundle(db.Model):
    __tablename__ = 'bundles'
    id = db.Column(db.Integer, primary_key=True)
    bundle_id = db.Column(db.Integer, unique=True, nullable=False)
    slug = db.Column(db.Text, nullable=False)
    name = db.Column(db.Text, nullable=False)
    base_discount = db.Column(db.Text, default='')
    final_price_cents = db.Column(db.Integer, default=0)

    items = db.relationship('BundleItem', backref='bundle', lazy=True,
                            order_by='BundleItem.idx')


class BundleItem(db.Model):
    __tablename__ = 'bundle_items'
    id = db.Column(db.Integer, primary_key=True)
    bundle_id = db.Column(db.Integer, db.ForeignKey('bundles.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    individual_price_cents = db.Column(db.Integer, default=0)
    idx = db.Column(db.Integer, default=0)


class CartItem(db.Model):
    __tablename__ = 'cart_items'
    id = db.Column(db.Integer, primary_key=True)
    cart_key = db.Column(db.Text, nullable=False, index=True)
    kind = db.Column(db.Text, nullable=False)       # game | bundle
    game_id = db.Column(db.Integer)
    bundle_id = db.Column(db.Integer)
    qty = db.Column(db.Integer, nullable=False, default=1)

    @property
    def unit_price(self):
        if self.kind == 'bundle':
            b = db.session.get(Bundle, self.bundle_id)
            return b.final_price_cents if b else 0
        g = db.session.get(Game, self.game_id)
        return g.final_price if g else 0

    @property
    def total(self):
        return self.unit_price * self.qty

    @property
    def title(self):
        if self.kind == 'bundle':
            b = db.session.get(Bundle, self.bundle_id)
            return b.name if b else ''
        g = db.session.get(Game, self.game_id)
        return g.name if g else ''


class WishlistItem(db.Model):
    __tablename__ = 'wishlist_items'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    added_ts = db.Column(db.Text, nullable=False)


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.Text, unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    email = db.Column(db.Text, nullable=False)
    full_name = db.Column(db.Text, nullable=False)
    address1 = db.Column(db.Text, nullable=False)
    city = db.Column(db.Text, nullable=False)
    state = db.Column(db.Text, nullable=False)
    zipcode = db.Column(db.Text, nullable=False)
    payment_method = db.Column(db.Text, nullable=False)
    subtotal = db.Column(db.Integer, nullable=False)
    tax = db.Column(db.Integer, nullable=False, default=0)
    total = db.Column(db.Integer, nullable=False)
    placed_at = db.Column(db.Text, nullable=False)

    items = db.relationship('OrderItem', backref='order', lazy=True)


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    kind = db.Column(db.Text, nullable=False)
    game_id = db.Column(db.Integer)
    bundle_id = db.Column(db.Integer)
    title = db.Column(db.Text, nullable=False)
    unit_price = db.Column(db.Integer, nullable=False)
    qty = db.Column(db.Integer, nullable=False, default=1)


# ------------------------------------------------------------------ helpers --

def _cart_key():
    key = session.get('cart_key')
    if not key:
        key = os.urandom(16).hex()
        session['cart_key'] = key
    return key


def _cart_items():
    return CartItem.query.filter_by(cart_key=_cart_key()) \
        .order_by(CartItem.id).all()


def _cart_subtotal():
    return sum(item.total for item in _cart_items())


def _game_or_404(appid):
    game = Game.query.filter_by(appid=appid).first()
    if not game:
        abort(404)
    return game


def _review_score_bucket(desc):
    desc = (desc or '').lower()
    if 'overwhelmingly positive' in desc:
        return 'positive'
    if 'very positive' in desc or desc == 'positive':
        return 'positive'
    if 'mostly positive' in desc:
        return 'positive'
    if 'mixed' in desc:
        return 'mixed'
    return 'negative'


def _parse_search_args(args):
    """The real search facet set, mirrored as GET form fields."""
    term = (args.get('term') or '').strip()[:120]
    genre = args.get('genre') or ''
    maxprice = args.get('maxprice') or ''
    os_filter = args.get('os') or ''
    review_type = args.get('review_type') or ''
    specials_only = args.get('specials') == '1'
    sort = args.get('sort') or 'Relevance_DESC'
    if sort not in SORT_LABELS:
        sort = 'Relevance_DESC'
    try:
        page = max(1, int(args.get('page') or 1))
    except ValueError:
        page = 1
    return {
        'term': term, 'genre': genre, 'maxprice': maxprice,
        'os': os_filter, 'review_type': review_type,
        'specials_only': specials_only, 'sort': sort, 'page': page,
    }


def _search_query(f):
    q = Game.query.filter(Game.coming_soon.is_(False),
                           Game.type == 'game')
    if f['term']:
        # upstream search tokenizes on whitespace and matches every token
        # (so "counter strike" hits "Counter-Strike"); tokens match inside
        # the name or the short description, case-insensitively
        for tok in f['term'].lower().split():
            if not tok:
                continue
            like = f"%{tok}%"
            q = q.filter(db.or_(db.func.lower(Game.name).like(like),
                                db.func.lower(Game.short_desc).like(like)))
    if f['genre']:
        q = q.filter(Game.genres.contains(f'"{f["genre"]}"'))
    if f['maxprice'] == 'free':
        q = q.filter(Game.is_free.is_(True))
    elif f['maxprice']:
        try:
            cap = int(float(f['maxprice']) * 100)
            # a numeric cap means paid games up to that price; the Free
            # option below covers the zero-price catalog
            q = q.filter(Game.price_cents > 0, Game.price_cents <= cap)
        except ValueError:
            pass
    if f['os']:
        q = q.filter(Game.platforms.contains(f'"{f["os"]}": true'))
    if f['review_type'] and f['review_type'] != 'all':
        want = {'positive': ('overwhelmingly positive', 'very positive',
                             'mostly positive', 'positive'),
                'mixed': ('mixed',),
                'negative': ('mostly negative', 'negative',
                             'overwhelmingly negative')}[f['review_type']]
        cond = db.or_(*[db.func.lower(Game.review_score_desc).contains(w)
                        for w in want])
        q = q.filter(cond)
    if f['specials_only']:
        q = q.filter(Game.discount_pct > 0)
    order = {
        'Released_DESC': None,
        'Name_ASC': None,
        'Price_ASC': None,
        'Price_DESC': None,
    }
    if f['sort'] == 'Released_DESC':
        # Steam dates are stored as "Mon D, YYYY" text; sort by the real
        # date (newest first), not by catalog id — ties keep catalog order.
        month_rank = db.case({m: i for i, m in enumerate(
            ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'], 1)},
            value=db.func.substr(Game.release_date, 1, 3))
        day = db.cast(db.func.substr(Game.release_date, 5,
                       db.func.instr(Game.release_date, ',') - 5), db.Integer)
        year = db.cast(db.func.substr(Game.release_date, -4), db.Integer)
        q = q.order_by(year.desc(), month_rank.desc(), day.desc(),
                       Game.id.desc())
    elif f['sort'] == 'Name_ASC':
        q = q.order_by(Game.name.asc(), Game.id.asc())
    elif f['sort'] == 'Price_ASC':
        q = q.order_by(Game.price_cents.asc(), Game.id.asc())
    elif f['sort'] == 'Price_DESC':
        q = q.order_by(Game.price_cents.desc(), Game.id.asc())
    else:
        # Relevance: live top-seller rank first, then stable appid order.
        q = q.order_by(Game.topseller_rank.asc().nullslast(), Game.id.asc())
    return q


PAGE_SIZE = 25


# ------------------------------------------------------------------- routes --

@app.route('/')
def home():
    topsellers = Game.query.filter(Game.topseller_rank.isnot(None)) \
        .order_by(Game.topseller_rank).limit(12).all()
    if not topsellers:
        topsellers = Game.query.order_by(Game.id).limit(12).all()
    specials = Game.query.filter(Game.discount_pct > 0) \
        .order_by(Game.discount_pct.desc(), Game.id).limit(12).all()
    newreleases = Game.query.filter(Game.newrelease_rank.isnot(None)) \
        .order_by(Game.newrelease_rank).limit(12).all()
    if not newreleases:
        newreleases = Game.query.order_by(Game.id.desc()).limit(12).all()
    genres = GENRE_ORDER
    counts = {
        'games': Game.query.count(),
        'specials': Game.query.filter(Game.discount_pct > 0).count(),
        'free': Game.query.filter(Game.is_free.is_(True)).count(),
        'bundles': Bundle.query.count(),
        'reviews': Review.query.count(),
        'news': NewsItem.query.count(),
    }
    return render_template('home.html', topsellers=topsellers,
                           specials=specials, newreleases=newreleases,
                           genres=genres, counts=counts)


@app.route('/search/')
def search():
    f = _parse_search_args(request.args)
    q = _search_query(f)
    total = q.count()
    games = q.offset((f['page'] - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    pages = max(1, -(-total // PAGE_SIZE))
    return render_template('search.html', games=games, f=f, total=total,
                           pages=pages, genres=GENRE_ORDER,
                           sorts=SORT_LABELS, price_points=PRICE_POINTS,
                           review_filters=REVIEW_FILTERS)


@app.route('/specials/')
def specials():
    f = _parse_search_args(request.args)
    f['specials_only'] = True
    q = _search_query(f)
    total = q.count()
    games = q.offset((f['page'] - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    pages = max(1, -(-total // PAGE_SIZE))
    return render_template('specials.html', games=games, f=f, total=total,
                           pages=pages, genres=GENRE_ORDER,
                           sorts=SORT_LABELS, price_points=PRICE_POINTS,
                           review_filters=REVIEW_FILTERS)


@app.route('/genre/<slug>/')
def genre_page(slug):
    label = next((g for g in GENRE_ORDER if _slugify(g) == slug), None)
    if not label:
        abort(404)
    f = _parse_search_args(request.args)
    f['genre'] = label
    q = _search_query(f)
    total = q.count()
    games = q.offset((f['page'] - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    pages = max(1, -(-total // PAGE_SIZE))
    return render_template('genre.html', games=games, f=f, total=total,
                           pages=pages, label=label, genres=GENRE_ORDER,
                           sorts=SORT_LABELS, price_points=PRICE_POINTS,
                           review_filters=REVIEW_FILTERS)


@app.route('/app/<int:appid>/')
@app.route('/app/<int:appid>/<slug>/')
def app_page(appid, slug=None):
    game = _game_or_404(appid)
    shots = Screenshot.query.filter_by(game_id=game.id) \
        .order_by(Screenshot.idx).all()
    reqs = SysReq.query.filter_by(game_id=game.id) \
        .order_by(SysReq.os, SysReq.level).all()
    news = NewsItem.query.filter_by(game_id=game.id) \
        .order_by(NewsItem.date.desc()).limit(4).all()
    bundles = Bundle.query.join(BundleItem) \
        .filter(BundleItem.game_id == game.id).all()
    dlcs = Game.query.filter(Game.appid.in_(game.dlc_list)).all() \
        if game.dlc_list else []
    in_wishlist = False
    if current_user.is_authenticated:
        in_wishlist = WishlistItem.query.filter_by(
            user_id=current_user.id, game_id=game.id).first() is not None
    return render_template('app.html', game=game, shots=shots, reqs=reqs,
                           news=news, bundles=bundles, dlcs=dlcs,
                           in_wishlist=in_wishlist)


@app.route('/app/<int:appid>/reviews/')
def app_reviews(appid):
    game = _game_or_404(appid)
    which = request.args.get('filter') or 'all'
    if which not in REVIEW_FILTERS:
        which = 'all'
    sort = request.args.get('sort') or 'recent'
    if sort not in REVIEW_SORTS:
        sort = 'recent'
    try:
        page = max(1, int(request.args.get('page') or 1))
    except ValueError:
        page = 1
    q = Review.query.filter_by(game_id=game.id)
    if which == 'positive':
        q = q.filter(Review.voted_up.is_(True))
    elif which == 'negative':
        q = q.filter(Review.voted_up.is_(False))
    if sort == 'helpful':
        q = q.order_by(Review.votes_up.desc(), Review.timestamp_created.desc())
    else:
        q = q.order_by(Review.timestamp_created.desc())
    total = q.count()
    reviews = q.offset((page - 1) * 10).limit(10).all()
    pages = max(1, -(-total // 10))
    pos = Review.query.filter_by(game_id=game.id, voted_up=True).count()
    neg = Review.query.filter_by(game_id=game.id, voted_up=False).count()
    return render_template('reviews.html', game=game, reviews=reviews,
                          which=which, sort=sort, page=page, pages=pages,
                          total=total, pos=pos, neg=neg,
                          review_filters=REVIEW_FILTERS,
                          review_sorts=REVIEW_SORTS)


@app.route('/bundle/<int:bundle_id>/')
@app.route('/bundle/<int:bundle_id>/<slug>/')
def bundle_page(bundle_id, slug=None):
    bundle = Bundle.query.filter_by(bundle_id=bundle_id).first()
    if not bundle:
        abort(404)
    items = []
    for bi in bundle.items:
        g = db.session.get(Game, bi.game_id)
        items.append({'item': bi, 'game': g})
    subtotal = sum(bi.individual_price_cents for bi in bundle.items)
    savings = max(0, subtotal - bundle.final_price_cents)
    return render_template('bundle.html', bundle=bundle, items=items,
                           subtotal=subtotal, savings=savings)


def _creator_page(kind, slug):
    """Match creator by slug of its exact stored name (small catalog, so
    the match runs in Python over the same deterministic ordering)."""
    games = Game.query.filter(Game.coming_soon.is_(False),
                              Game.type == 'game') \
        .order_by(Game.price_cents.desc(), Game.name).all()
    matched = []
    label = None
    for game in games:
        names = game.publisher_list if kind == 'publisher' else game.developer_list
        for name in names:
            if _slugify(name) == slug:
                label = name
                matched.append(game)
                break
    if label is None:
        abort(404)
    return render_template('creator.html', kind=kind, label=label,
                           games=matched)


@app.route('/developer/<slug>/')
def developer_page(slug):
    return _creator_page('developer', slug)


@app.route('/publisher/<slug>/')
def publisher_page(slug):
    return _creator_page('publisher', slug)


@app.route('/news/')
def news_hub():
    try:
        page = max(1, int(request.args.get('page') or 1))
    except ValueError:
        page = 1
    q = NewsItem.query.order_by(NewsItem.date.desc())
    total = q.count()
    items = q.offset((page - 1) * 15).limit(15).all()
    pages = max(1, -(-total // 15))
    return render_template('news_hub.html', items=items, page=page,
                           pages=pages, total=total)


@app.route('/news/<int:appid>/')
def news_game(appid):
    game = _game_or_404(appid)
    items = NewsItem.query.filter_by(game_id=game.id) \
        .order_by(NewsItem.date.desc()).all()
    return render_template('news_game.html', game=game, items=items)


@app.route('/news/item/<gid>/')
def news_item(gid):
    item = NewsItem.query.filter_by(gid=gid).first()
    if not item:
        abort(404)
    game = db.session.get(Game, item.game_id)
    return render_template('news_item.html', item=item, game=game)


# ------------------------------------------------------------------ shopping --

@app.route('/cart/')
def cart():
    items = _cart_items()
    subtotal = sum(item.total for item in items)
    return render_template('cart.html', items=items, subtotal=subtotal)


@app.route('/cart/add', methods=['POST'])
def cart_add():
    kind = request.form.get('kind') or 'game'
    qty = max(1, min(10, int(request.form.get('qty') or 1)))
    if kind == 'bundle':
        bid = request.form.get('bundle_id')
        bundle = Bundle.query.filter_by(bundle_id=int(bid)).first() \
            if bid and bid.isdigit() else None
        if not bundle:
            flash('That bundle is not available.', 'error')
            return redirect(url_for('cart'))
        existing = CartItem.query.filter_by(
            cart_key=_cart_key(), kind='bundle',
            bundle_id=bundle.id).first()
        if existing:
            existing.qty = qty
        else:
            db.session.add(CartItem(cart_key=_cart_key(), kind='bundle',
                                    bundle_id=bundle.id, qty=qty))
        db.session.commit()
        flash(f'{bundle.name} was added to your cart.', 'success')
        return redirect(url_for('cart'))
    appid = request.form.get('appid')
    game = Game.query.filter_by(appid=int(appid)).first() \
        if appid and appid.isdigit() else None
    if not game:
        flash('That product is not available.', 'error')
        return redirect(url_for('cart'))
    existing = CartItem.query.filter_by(
        cart_key=_cart_key(), kind='game', game_id=game.id).first()
    if existing:
        existing.qty = qty
    else:
        db.session.add(CartItem(cart_key=_cart_key(), kind='game',
                                game_id=game.id, qty=qty))
    db.session.commit()
    flash(f'{game.name} was added to your cart.', 'success')
    return redirect(url_for('cart'))


@app.route('/cart/update', methods=['POST'])
def cart_update():
    item = CartItem.query.filter_by(
        id=int(request.form.get('item_id') or 0),
        cart_key=_cart_key()).first()
    if item:
        try:
            qty = int(request.form.get('qty'))
            if 1 <= qty <= 10:
                item.qty = qty
                db.session.commit()
        except ValueError:
            pass
    return redirect(url_for('cart'))


@app.route('/cart/remove', methods=['POST'])
def cart_remove():
    item = CartItem.query.filter_by(
        id=int(request.form.get('item_id') or 0),
        cart_key=_cart_key()).first()
    if item:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('cart'))


@app.route('/checkout/', methods=['GET', 'POST'])
@login_required
def checkout():
    items = _cart_items()
    if not items:
        flash('Your cart is empty.', 'error')
        return redirect(url_for('cart'))
    subtotal = sum(item.total for item in items)
    if request.method == 'POST':
        data = {k: (request.form.get(k) or '').strip()
                for k in ('full_name', 'email', 'address1', 'city', 'state',
                          'zipcode', 'payment_method')}
        if not all(data.values()):
            flash('Please fill in every field.', 'error')
        elif '@' not in data['email'] or '.' not in data['email']:
            flash('Please enter a valid email address.', 'error')
        else:
            order = Order(
                order_no=f'ST-{1000 + Order.query.count() + 1}',
                user_id=current_user.id,
                email=data['email'], full_name=data['full_name'],
                address1=data['address1'], city=data['city'],
                state=data['state'], zipcode=data['zipcode'],
                payment_method=data['payment_method'],
                subtotal=subtotal, tax=0, total=subtotal,
                placed_at=_now_iso())
            db.session.add(order)
            db.session.flush()
            for item in items:
                db.session.add(OrderItem(
                    order_id=order.id, kind=item.kind,
                    game_id=item.game_id, bundle_id=item.bundle_id,
                    title=item.title, unit_price=item.unit_price,
                    qty=item.qty))
                db.session.delete(item)
            db.session.commit()
            return redirect(url_for('order_page', order_no=order.order_no))
    return render_template('checkout.html', items=items, subtotal=subtotal)


@app.route('/order/<order_no>/')
@login_required
def order_page(order_no):
    order = Order.query.filter_by(order_no=order_no,
                                  user_id=current_user.id).first()
    if not order:
        abort(404)
    return render_template('order.html', order=order)


# ------------------------------------------------------------------ wishlist --

@app.route('/wishlist/toggle', methods=['POST'])
@login_required
def wishlist_toggle():
    appid = request.form.get('appid')
    game = Game.query.filter_by(appid=int(appid)).first() \
        if appid and appid.isdigit() else None
    if game:
        existing = WishlistItem.query.filter_by(
            user_id=current_user.id, game_id=game.id).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            flash(f'{game.name} was removed from your wishlist.', 'success')
        else:
            db.session.add(WishlistItem(user_id=current_user.id,
                                        game_id=game.id,
                                        added_ts=_now_iso()))
            db.session.commit()
            flash(f'{game.name} was added to your wishlist.', 'success')
    return redirect(request.form.get('next') or url_for('wishlist'))


@app.route('/wishlist/')
@login_required
def wishlist():
    items = WishlistItem.query.filter_by(user_id=current_user.id) \
        .order_by(WishlistItem.id).all()
    entries = []
    for w in items:
        g = db.session.get(Game, w.game_id)
        if g:
            entries.append({'entry': w, 'game': g})
    return render_template('wishlist.html', entries=entries)


# -------------------------------------------------------------------- account --

@app.route('/account/')
@login_required
def account():
    orders = Order.query.filter_by(user_id=current_user.id) \
        .order_by(Order.id.desc()).all()
    return render_template('account.html', orders=orders)


@app.route('/account/login/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('account'))
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.pw_hash, password):
            login_user(user)
            target = request.args.get('next')
            if target and target.startswith('/'):
                return redirect(target)
            return redirect(url_for('account'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html')


@app.route('/account/signup/', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('account'))
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        if not name or len(name) < 2:
            flash('Please enter your name.', 'error')
        elif '@' not in email or '.' not in email:
            flash('Please enter a valid email address.', 'error')
        elif len(password) < 8:
            flash('Your password must be at least 8 characters.', 'error')
        elif User.query.filter_by(email=email).first():
            flash('An account with that email already exists.', 'error')
        else:
            pw_hash = bcrypt.generate_password_hash(password)
            if isinstance(pw_hash, bytes):
                pw_hash = pw_hash.decode('utf-8')
            user = User(name=name, email=email, pw_hash=pw_hash)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for('account'))
    return render_template('signup.html')


@app.route('/account/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


# --------------------------------------------------------------------- health --

@app.route('/_health')
def health():
    return jsonify({
        'ok': True,
        'site': SITE_NAME,
        'games': Game.query.count(),
        'reviews': Review.query.count(),
        'news': NewsItem.query.count(),
        'bundles': Bundle.query.count(),
        'bundle_items': BundleItem.query.count(),
        'screenshots': Screenshot.query.count(),
        'sysreqs': SysReq.query.count(),
        'users': User.query.count(),
        'wishlist_items': WishlistItem.query.count(),
        'orders': Order.query.count(),
    })


# ---------------------------------------------------------------------- seeds --

def _parse_requirements(html_text):
    """Parse a Steam requirement block into labeled spec fields."""
    if not html_text:
        return {}
    specs = {}
    for m in re.finditer(r'<li>(.*?)</li>', html_text, re.S):
        clean = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        mm = re.match(r'(.+?)\s*:\s*(.+)', clean, re.S)
        if mm:
            key = mm.group(1).strip().rstrip('*').strip()
            value = mm.group(2).strip()
            if key and value:
                specs[key] = value
    if not specs:
        text = re.sub(r'<br\s*/?>', '\n', html_text)
        text = re.sub(r'<[^>]+>', '\n', text)
        for line in text.splitlines():
            line = line.strip(' \t*·-')
            mm = re.match(r'(.+?)\s*:\s*(.+)', line)
            if mm:
                key = mm.group(1).strip().rstrip('*').strip()
                value = mm.group(2).strip()
                if key and value:
                    specs[key] = value
    return specs


def seed_database():
    if Game.query.count() > 0:
        return

    games = _load('games.json')
    snapshots = _load('search_snapshots.json')
    reviews = _load('reviews.json')
    news = _load('news.json')
    bundles = _load('bundles.json')
    seen_gids = set()

    rank_top = {}
    for row in snapshots.get('topsellers', []):
        if row['appid'] not in rank_top:
            rank_top[row['appid']] = len(rank_top) + 1
    rank_new = {}
    for row in snapshots.get('newreleases', []):
        if row['appid'] not in rank_new:
            rank_new[row['appid']] = len(rank_new) + 1

    appid_to_id = {}
    for rec in games:
        appid = str(rec['appid'])
        game = Game(
            appid=rec['appid'],
            slug=rec['slug'],
            name=rec['name'],
            type=rec.get('type', 'game'),
            is_free=rec.get('is_free', False),
            short_desc=rec.get('short_desc', ''),
            about=rec.get('about', ''),
            detailed_desc=rec.get('detailed_desc', ''),
            supported_languages=rec.get('supported_languages', ''),
            release_date=rec.get('release_date', ''),
            coming_soon=rec.get('coming_soon', False),
            price_cents=rec.get('price_cents'),
            initial_cents=rec.get('initial_cents'),
            discount_pct=rec.get('discount_pct', 0) or 0,
            header_img=rec.get('header_img', ''),
            capsule_img=rec.get('capsule_img', ''),
            platforms=json.dumps(rec.get('platforms', {})),
            genres=json.dumps(rec.get('genres', [])),
            categories=json.dumps(rec.get('categories', [])[:12]),
            publishers=json.dumps(rec.get('publishers', [])),
            developers=json.dumps(rec.get('developers', [])),
            review_score_desc=rec.get('review_score_desc', ''),
            review_pct=rec.get('review_pct', 0),
            total_positive=rec.get('total_positive', 0),
            total_negative=rec.get('total_negative', 0),
            total_reviews=rec.get('total_reviews', 0),
            achievements_total=rec.get('achievements_total'),
            required_age=rec.get('required_age', 0) or 0,
            dlc_apps=json.dumps(rec.get('dlc_apps', [])),
            topseller_rank=rank_top.get(appid),
            newrelease_rank=rank_new.get(appid),
        )
        db.session.add(game)
        db.session.flush()
        appid_to_id[appid] = game.id

        for j, path in enumerate(rec.get('screens', [])):
            db.session.add(Screenshot(game_id=game.id, path_full=path,
                                       idx=j))
        for os_name, block in (('windows', 'pc_requirements'),
                               ('mac', 'mac_requirements'),
                               ('linux', 'linux_requirements')):
            req = rec.get(block) or {}
            for level in ('minimum', 'recommended'):
                specs = _parse_requirements(req.get(level))
                if specs:
                    db.session.add(SysReq(
                        game_id=game.id, os=os_name, level=level,
                        specs=json.dumps(specs)))

    for appid, rv in reviews.items():
        game_id = appid_to_id.get(appid)
        if not game_id:
            continue
        for r in rv.get('reviews', []):
            db.session.add(Review(
                game_id=game_id,
                recommendationid=str(r['recommendationid']),
                author=r.get('author', ''),
                author_games=r.get('author_games', 0) or 0,
                author_reviews=r.get('author_reviews', 0) or 0,
                playtime_forever=r.get('playtime_forever', 0) or 0,
                playtime_at_review=r.get('playtime_at_review', 0) or 0,
                voted_up=bool(r.get('voted_up')),
                votes_up=r.get('votes_up', 0) or 0,
                votes_funny=r.get('votes_funny', 0) or 0,
                steam_purchase=bool(r.get('steam_purchase')),
                received_for_free=bool(r.get('received_for_free')),
                early_access=bool(r.get('early_access')),
                text=r.get('review', ''),
                timestamp_created=r.get('timestamp_created', 0) or 0,
                language=r.get('language', 'english')))

    for appid, nw in news.items():
        game_id = appid_to_id.get(appid)
        if not game_id:
            continue
        for it in nw.get('items', []):
            if it['gid'] in seen_gids:
                continue  # shared feed item already recorded under its first game
            seen_gids.add(it['gid'])
            db.session.add(NewsItem(
                game_id=game_id, gid=str(it['gid']), title=it.get('title', ''),
                url=it.get('url', ''),
                is_external_url=bool(it.get('is_external_url')),
                author=it.get('author', ''), contents=it.get('contents', ''),
                feedlabel=it.get('feedlabel', ''),
                date=it.get('date', 0) or 0,
                feedname=it.get('feedname', '')))

    for bid, b in bundles.items():
        bundle = Bundle(
            bundle_id=int(bid), slug=b.get('slug', ''),
            name=b.get('name', ''),
            base_discount=b.get('base_discount', ''),
            final_price_cents=b.get('final_price_cents', 0))
        db.session.add(bundle)
        db.session.flush()
        for idx, appid in enumerate(b.get('item_appids', [])):
            game_id = appid_to_id.get(str(appid))
            if not game_id:
                continue
            price = b.get('item_price_cents', [None] * (idx + 1))
            individual = price[idx] if idx < len(price) else None
            db.session.add(BundleItem(
                bundle_id=bundle.id, game_id=game_id,
                individual_price_cents=individual or 0, idx=idx))

    db.session.commit()


def seed_benchmark_users():
    if User.query.filter_by(email='alice.j@test.com').first():
        return

    users = [
        ('Alice Johnson', 'alice.j@test.com'),
        ('Bob Smith', 'bob.s@test.com'),
        ('Carol Martinez', 'carol.m@test.com'),
        ('Dana Kim', 'dana.k@test.com'),
    ]
    for name, email in users:
        db.session.add(User(name=name, email=email,
                            pw_hash=BENCHMARK_PASSWORD_HASH))
    db.session.flush()

    # deterministic fixture wishlists (game slugs resolved after flush)
    def gid(slug):
        return db.session.query(Game.id).filter_by(slug=slug).scalar()

    wish = [
        (1, ['counter-strike-2', 'dota-2']),
        (2, ['elden-ring', 'baldur-s-gate-3']),
        (3, ['stardew-valley', 'terraria', 'hades']),
        (4, ['cyberpunk-2077']),
    ]
    for user_id, slugs in wish:
        for n, slug in enumerate(slugs):
            game_id = gid(slug)
            if game_id:
                db.session.add(WishlistItem(
                    user_id=user_id, game_id=game_id,
                    added_ts=f'2026-09-{10 + n:02d}T12:00:00Z'))

    # deterministic fixture orders
    fixtures = [
        ('ST-1001', 1, 'alice.j@test.com', 'Alice Johnson',
         '42 Pipeline Way', 'Bellevue', 'WA', '98004', 'Visa',
         [('game', 'left-4-dead-2'), ('game', 'portal-2')]),
        ('ST-1002', 2, 'bob.s@test.com', 'Bob Smith',
         '7 Coast Road', 'Austin', 'TX', '78701', 'Mastercard',
         [('game', 'elden-ring')]),
        ('ST-1003', 3, 'carol.m@test.com', 'Carol Martinez',
         '12 Farm Lane', 'Portland', 'OR', '97201', 'Visa',
         [('game', 'stardew-valley'), ('game', 'terraria')]),
    ]
    for (order_no, user_id, email, full_name, address1, city, state,
         zipcode, payment, lines) in fixtures:
        subtotal = 0
        order = Order(order_no=order_no, user_id=user_id, email=email,
                      full_name=full_name, address1=address1, city=city,
                      state=state, zipcode=zipcode, payment_method=payment,
                      subtotal=0, tax=0, total=0,
                      placed_at=f'2026-09-2{user_id}T10:00:00Z')
        db.session.add(order)
        db.session.flush()
        for kind, slug in lines:
            g = Game.query.filter_by(slug=slug).first()
            if not g:
                continue
            db.session.add(OrderItem(order_id=order.id, kind='game',
                                     game_id=g.id, title=g.name,
                                     unit_price=g.final_price, qty=1))
            subtotal += g.final_price
        order.subtotal = subtotal
        order.total = subtotal
    db.session.commit()


def main():
    with app.app_context():
        db.create_all()
        seed_database()
        seed_benchmark_users()


with app.app_context():
    if not os.environ.get('WEBSYN_SKIP_BOOTSTRAP'):
        main()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 40140))
    app.run(host='0.0.0.0', port=port, debug=False)
