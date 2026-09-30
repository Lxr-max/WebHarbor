#!/usr/bin/env python3
"""disney — a WebHarbor mirror of https://www.disney.com/

Flask + SQLite mirror of the Disney.com portal: the home page hero
modules, the Movies catalog (all-movies grid with the upstream filter
taxonomy plus detail pages carrying the captured synopsis, rating,
runtime, release date, genre, director/producer/cast, awards, video
titles and image galleries), the Shows catalog (A-Z plus the upstream
genre pages) with detail pages, the Games hub, the Walt Disney World
parks finder (attractions and entertainment with the upstream park /
interest / age / height facets), the Disney Store (category grids,
product detail with captured descriptions, ratings, review counts and
scene7 image sets, guest bag + checkout), and the Live Shows vertical
(Broadway musicals hub plus the Disney On Ice touring schedule with
per-performance ticket booking), seeded for four benchmark users.

Content comes from the tracked source_data/*.json snapshots captured
from disney.com and its official sub-properties on 2026-09-29 (see
provenance.json); the SQLite seed is materialized deterministically at
image build time (PYTHONHASHSEED=0).
"""
import json
import os
import re
import secrets
from datetime import date

from flask import (Flask, abort, jsonify, redirect, render_template, request,
                   session, url_for)
from flask_bcrypt import Bcrypt
from flask_login import (LoginManager, UserMixin, current_user,
                         login_required, login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from markupsafe import Markup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, instance_path=os.path.join(BASE_DIR, 'instance'))
app.config["SECRET_KEY"] = os.environ.get("DISNEY_SECRET_KEY") or "webharbor-disney-dev-key"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DISNEY_DB_URI', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'disney.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to continue.'
csrf = CSRFProtect(app)

MIRROR_DATE = date(2026, 9, 29)
MIRROR_TS = '2026-09-29'
SITE_NAME = 'disney'
UPSTREAM = 'https://www.disney.com/'
# bcrypt hash of 'TestPass123!' — frozen so the seed DB is byte-reproducible.
BENCHMARK_PASSWORD_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')
SOURCE = os.path.join(BASE_DIR, 'source_data')


def _load(name):
    with open(os.path.join(SOURCE, name), encoding='utf-8') as f:
        return json.load(f)


# ------------------------------------------------------------- asset tables --

_INVENTORY = None


def _inventory():
    global _INVENTORY
    if _INVENTORY is None:
        _INVENTORY = {}
        path = os.path.join(BASE_DIR, 'asset_inventory.json')
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                for row in json.load(f).get('assets', []):
                    _INVENTORY[row['path'].split('/')[-1]] = row['path']
    return _INVENTORY


def asset_exists(path):
    return path in _inventory()


# ------------------------------------------------------------------- models --

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128), unique=True, nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    joined = db.Column(db.String(10))


class Favorite(db.Model):
    __tablename__ = 'favorites'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False,
                        index=True)
    item_type = db.Column(db.String(16), nullable=False)   # movie/show/attraction/product/game
    item_key = db.Column(db.String(96), nullable=False)    # slug / pid
    added_at = db.Column(db.String(10))


class HomeTile(db.Model):
    __tablename__ = 'home_tiles'
    id = db.Column(db.Integer, primary_key=True)
    eyebrow = db.Column(db.String(128))
    title = db.Column(db.Text)
    description = db.Column(db.Text)
    cta_label = db.Column(db.String(64))
    cta_url = db.Column(db.String(255))
    image = db.Column(db.String(255))


class Movie(db.Model):
    __tablename__ = 'movies'
    slug = db.Column(db.String(96), primary_key=True)
    title = db.Column(db.Text, nullable=False)
    poster = db.Column(db.String(255))
    label = db.Column(db.String(64))
    rating = db.Column(db.String(16))
    runtime = db.Column(db.String(24))
    release_date = db.Column(db.String(48))
    release_sort = db.Column(db.String(10))
    genres = db.Column(db.Text)
    synopsis = db.Column(db.Text)
    directed_by = db.Column(db.Text)
    produced_by = db.Column(db.Text)
    cast = db.Column(db.Text)
    awards = db.Column(db.Text)
    gallery = db.Column(db.Text)
    videos = db.Column(db.Text)
    streaming_on = db.Column(db.String(64))

    def genre_list(self):
        return [g for g in (self.genres or '').split('|') if g]

    def gallery_list(self):
        return [g for g in (self.gallery or '').split('|') if g]

    def video_list(self):
        return [v for v in (self.videos or '').split('|') if v]


class Show(db.Model):
    __tablename__ = 'shows'
    slug = db.Column(db.String(96), primary_key=True)
    title = db.Column(db.Text, nullable=False)
    thumb = db.Column(db.String(255))
    genres = db.Column(db.Text)
    description = db.Column(db.Text)
    rating = db.Column(db.String(16))
    release_date = db.Column(db.String(24))
    genre_line = db.Column(db.Text)
    videos = db.Column(db.Text)
    cast = db.Column(db.Text)

    def genre_list(self):
        return [g for g in (self.genres or '').split('|') if g]

    def video_list(self):
        return [v for v in (self.videos or '').split('|') if v]


class Game(db.Model):
    __tablename__ = 'games'
    slug = db.Column(db.String(96), primary_key=True)
    title = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(255))
    description = db.Column(db.Text)
    sections = db.Column(db.Text)   # JSON: [{heading, paragraphs}]

    def section_list(self):
        try:
            return json.loads(self.sections or '[]')
        except json.JSONDecodeError:
            return []


class ParkEntity(db.Model):
    __tablename__ = 'park_entities'
    key = db.Column(db.String(128), primary_key=True)   # <park>/<slug>
    slug = db.Column(db.String(96), nullable=False)
    section = db.Column(db.String(24), nullable=False)  # attractions / entertainment
    entity_id = db.Column(db.String(24))
    entity_type = db.Column(db.String(24), nullable=False)   # Attraction / Entertainment
    name = db.Column(db.Text, nullable=False)
    park_slug = db.Column(db.String(32), nullable=False, index=True)
    park = db.Column(db.String(64), nullable=False)
    interests = db.Column(db.Text)
    ages = db.Column(db.Text)
    height = db.Column(db.Integer)
    image = db.Column(db.String(255))
    alt = db.Column(db.Text)
    detail_body = db.Column(db.Text)     # JSON: sections/headings/paragraphs
    images = db.Column(db.Text)          # JSON list
    related = db.Column(db.Text)         # JSON list of hrefs

    def interest_list(self):
        return [g for g in (self.interests or '').split('|') if g]

    def age_list(self):
        return [g for g in (self.ages or '').split('|') if g]

    def detail(self):
        try:
            return json.loads(self.detail_body or '{}')
        except json.JSONDecodeError:
            return {}

    def image_list(self):
        try:
            return json.loads(self.images or '[]')
        except json.JSONDecodeError:
            return []

    def related_list(self):
        try:
            out = []
            for href in json.loads(self.related or '[]'):
                segs = href.strip('/').split('/')
                if len(segs) == 3:
                    out.append(f"{segs[1]}/{segs[2]}")
            return out
        except json.JSONDecodeError:
            return []


class Product(db.Model):
    __tablename__ = 'products'
    pid = db.Column(db.String(32), primary_key=True)
    name = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float)
    original_price = db.Column(db.Float)
    rating = db.Column(db.Float)
    reviews = db.Column(db.Integer)
    category = db.Column(db.String(64))
    subcategory = db.Column(db.String(64))
    character = db.Column(db.String(64))
    target_age = db.Column(db.String(32))
    availability = db.Column(db.String(48))
    collections = db.Column(db.Text)
    description = db.Column(db.Text)
    magic_details = db.Column(db.Text)     # JSON list
    bare_necessities = db.Column(db.Text)  # JSON list
    images = db.Column(db.Text)            # JSON list

    def collection_list(self):
        return [c for c in (self.collections or '').split('|') if c]

    def magic_list(self):
        try:
            return json.loads(self.magic_details or '[]')
        except json.JSONDecodeError:
            return []

    def bare_list(self):
        try:
            return json.loads(self.bare_necessities or '[]')
        except json.JSONDecodeError:
            return []

    def image_list(self):
        try:
            return json.loads(self.images or '[]')
        except json.JSONDecodeError:
            return []


class LiveShow(db.Model):
    __tablename__ = 'live_shows'
    slug = db.Column(db.String(64), primary_key=True)
    title = db.Column(db.Text, nullable=False)
    kind = db.Column(db.String(24), nullable=False)   # broadway / ice_tour
    url = db.Column(db.String(255))
    image = db.Column(db.String(255))
    description = db.Column(db.Text)


class IceEvent(db.Model):
    __tablename__ = 'ice_events'
    event_id = db.Column(db.String(24), primary_key=True)
    show = db.Column(db.String(64), nullable=False, index=True)
    city = db.Column(db.String(64), nullable=False)
    venue = db.Column(db.String(128))
    date_range = db.Column(db.String(48))
    buy_url = db.Column(db.String(255))
    performances = db.Column(db.Text)   # JSON: [{day, times}]

    def performance_list(self):
        try:
            return json.loads(self.performances or '[]')
        except json.JSONDecodeError:
            return []

    def first_day(self):
        perfs = self.performance_list()
        return perfs[0]['day'] if perfs else (self.date_range or '')


class CartItem(db.Model):
    __tablename__ = 'cart_items'
    id = db.Column(db.Integer, primary_key=True)
    cart_key = db.Column(db.String(48), nullable=False, index=True)
    product_pid = db.Column(db.String(32), db.ForeignKey('products.pid'),
                            nullable=False)
    qty = db.Column(db.Integer, nullable=False, default=1)


class ShopOrder(db.Model):
    __tablename__ = 'shop_orders'
    id = db.Column(db.Integer, primary_key=True)
    confirmation = db.Column(db.String(16), unique=True, nullable=False)
    email = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    items_json = db.Column(db.Text, nullable=False)
    total = db.Column(db.Float, nullable=False)
    placed_at = db.Column(db.String(10), nullable=False)


class TicketOrder(db.Model):
    __tablename__ = 'ticket_orders'
    id = db.Column(db.Integer, primary_key=True)
    confirmation = db.Column(db.String(16), unique=True, nullable=False)
    email = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    event_id = db.Column(db.String(24), db.ForeignKey('ice_events.event_id'),
                         nullable=False)
    show_title = db.Column(db.String(64), nullable=False)
    city = db.Column(db.String(64), nullable=False)
    venue = db.Column(db.String(128))
    day = db.Column(db.String(32), nullable=False)
    time = db.Column(db.String(16), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    placed_at = db.Column(db.String(10), nullable=False)


# -------------------------------------------------------------- login glue --

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ----------------------------------------------------------------- helpers --

def _img(local_name):
    """Resolve a downloaded upstream asset; None when not inventoried."""
    if not local_name:
        return None
    inv = _inventory()
    return url_for('static', filename='images/upstream/' + local_name) \
        if local_name in inv else None


def _cart_key():
    if current_user.is_authenticated:
        return f'u{current_user.id}'
    key = session.get('cart_key')
    if not key:
        key = 'c' + secrets.token_hex(12)
        session['cart_key'] = key
    return key


def _bag_rows():
    key = _cart_key()
    rows = (CartItem.query.filter_by(cart_key=key)
            .order_by(CartItem.id).all())
    out = []
    for row in rows:
        product = db.session.get(Product, row.product_pid)
        if product:
            out.append({'row': row, 'product': product,
                        'line': round((product.price or 0) * row.qty, 2)})
    return out


def _bag_total(rows=None):
    rows = rows if rows is not None else _bag_rows()
    return round(sum(r['line'] for r in rows), 2)


MOVIE_STATUS = {
    'now_playing': 'In Theaters',
    'coming_soon': 'Coming Soon',
    'streaming': 'Now on Disney+',
    '': 'In the Catalog',
}

# Upstream park display names (the finder listing labels), shared by the
# Parks & Travel hub and the attractions filter.
PARK_NAMES = {
    'magic-kingdom': 'Magic Kingdom Park',
    'epcot': 'EPCOT',
    'hollywood-studios': "Disney's Hollywood Studios",
    'animal-kingdom': "Disney's Animal Kingdom Theme Park",
    'disney-springs': 'Disney Springs',
    'typhoon-lagoon': "Disney's Typhoon Lagoon Water Park",
    'blizzard-beach': "Disney's Blizzard Beach Water Park",
    'wide-world-of-sports': 'ESPN Wide World of Sports Complex',
    'boardwalk': "Disney's BoardWalk",
    'grand-floridian-resort-and-spa': "Disney's Grand Floridian Resort & Spa",
    'port-orleans-resort-riverside': "Disney's Port Orleans Resort - Riverside",
}


def _movie_status(movie):
    if movie.release_sort and movie.release_sort > MIRROR_TS:
        return 'coming_soon'
    if movie.streaming_on:
        return 'streaming'
    if movie.release_sort and MIRROR_TS >= movie.release_sort >= '2026-07-31':
        return 'now_playing'
    return ''


# ------------------------------------------------------------------- routes --

@app.route('/')
def home():
    tiles = HomeTile.query.order_by(HomeTile.id).all()
    heroes = [{
        'eyebrow': t.eyebrow,
        'title': t.title,
        'description': t.description,
        'cta_label': t.cta_label,
        'cta_url': t.cta_url,
        'image': _img(t.image),
    } for t in tiles]
    movies = Movie.query.order_by(Movie.release_sort.desc()).limit(8).all()
    shows = Show.query.order_by(Show.title).limit(8).all()
    products = Product.query.filter(Product.price > 0) \
        .order_by(Product.rating.desc()).limit(8).all()
    games = Game.query.order_by(Game.title).all()
    # Real upstream art for the Parks & Travel card (Cinderella Castle,
    # captured with the rest of the parks finder assets).
    castle = db.session.get(ParkEntity, 'magic-kingdom/cinderella-castle')
    parks_teaser = _img(castle.image) if castle else None
    return render_template('home.html', heroes=heroes, movies=movies,
                           shows=shows, products=products, games=games,
                           parks_teaser=parks_teaser, img=_img)


@app.route('/movies')
def movies():
    q = (request.args.get('q') or '').strip()
    status = request.args.get('status') or ''
    genre = request.args.get('genre') or ''
    sort = request.args.get('sort') or 'release'
    page = max(1, int(request.args.get('page', 1) or 1))
    query = Movie.query
    if q:
        query = query.filter(Movie.title.ilike(f'%{q}%'))
    if status:
        want = status
        rows = [m for m in query.all() if _movie_status(m) == want]
    else:
        rows = query.all()
    if genre:
        rows = [m for m in rows if genre in (m.genres or '')]
    if sort == 'release' or sort not in ('title', 'rating'):
        rows.sort(key=lambda m: m.release_sort or '', reverse=True)
    elif sort == 'title':
        rows.sort(key=lambda m: m.title.lower())
    else:
        rows.sort(key=lambda m: m.rating or '')
    total = len(rows)
    per_page = 24
    start = (page - 1) * per_page
    page_rows = rows[start:start + per_page]
    genres = sorted({g for m in Movie.query.all() for g in m.genre_list()})
    return render_template('movies.html', rows=page_rows, total=total,
                           genres=genres, q=q, status=status, genre=genre,
                           sort=sort, page=page,
                           pages=max(1, -(-total // per_page)),
                           status_map=MOVIE_STATUS, img=_img,
                           movie_status=_movie_status)


@app.route('/movies/<slug>')
def movie_detail(slug):
    movie = db.session.get(Movie, slug)
    if not movie:
        abort(404)
    recs = []
    for r in (movie.videos or '').split('|'):
        if r:
            recs.append(r)
    return render_template('movie_detail.html', m=movie,
                           status_label=MOVIE_STATUS[_movie_status(movie)],
                           img=_img, gallery=movie.gallery_list(),
                           videos=movie.video_list())


@app.route('/shows')
def shows():
    q = (request.args.get('q') or '').strip()
    genre = request.args.get('genre') or ''
    sort = request.args.get('sort') or 'title'
    page = max(1, int(request.args.get('page', 1) or 1))
    query = Show.query
    if q:
        query = query.filter(Show.title.ilike(f'%{q}%'))
    if genre:
        query = query.filter(Show.genres.ilike(f'%{genre}%'))
    rows = query.all()
    order = {'title': lambda s: s.title.lower(),
             'recent': lambda s: s.slug}
    rows.sort(key=order.get(sort, order['title']))
    total = len(rows)
    per_page = 30
    start = (page - 1) * per_page
    page_rows = rows[start:start + per_page]
    genres = sorted({g for s in Show.query.all() for g in s.genre_list()})
    return render_template('shows.html', rows=page_rows, total=total,
                           genres=genres, q=q, genre=genre, sort=sort,
                           page=page, pages=max(1, -(-total // per_page)),
                           img=_img)


@app.route('/shows/<slug>')
def show_detail(slug):
    show = db.session.get(Show, slug)
    if not show:
        abort(404)
    return render_template('show_detail.html', s=show, img=_img)


@app.route('/games')
def games():
    q = (request.args.get('q') or '').strip()
    rows = Game.query.all()
    if q:
        rows = [g for g in rows if q.lower() in g.title.lower()]
    return render_template('games.html', rows=rows, q=q, total=len(rows),
                           img=_img)


@app.route('/games/<slug>')
def game_detail(slug):
    game = db.session.get(Game, slug)
    if not game:
        abort(404)
    return render_template('game_detail.html', g=game, img=_img)


@app.route('/parks')
def parks():
    counts = {}
    for slug, in db.session.query(ParkEntity.park_slug).distinct():
        counts[slug] = ParkEntity.query.filter_by(park_slug=slug).count()
    parks = [{'slug': s, 'name': PARK_NAMES.get(s, s),
              'attractions': counts.get(s, 0)} for s in counts]
    parks.sort(key=lambda p: -p['attractions'])
    return render_template('parks.html', parks=parks)


@app.route('/parks/attractions')
def attractions():
    q = (request.args.get('q') or '').strip()
    park = request.args.get('park') or ''
    etype = request.args.get('type') or ''
    interest = request.args.get('interest') or ''
    age = request.args.get('age') or ''
    height = request.args.get('height') or ''
    sort = request.args.get('sort') or 'name'
    page = max(1, int(request.args.get('page', 1) or 1))
    query = ParkEntity.query
    if park:
        query = query.filter_by(park_slug=park)
    if etype:
        query = query.filter_by(entity_type=etype)
    rows = query.all()
    if interest:
        rows = [r for r in rows if interest in r.interest_list()]
    if age:
        rows = [r for r in rows if age in r.age_list()]
    if height:
        try:
            h = int(height)
            rows = [r for r in rows if r.height and r.height >= h]
        except ValueError:
            pass
    if q:
        rows = [r for r in rows if q.lower() in r.name.lower()]
    order = {'name': lambda r: r.name.lower(),
             'park': lambda r: (r.park, r.name.lower()),
             'height': lambda r: (r.height or 0, r.name.lower())}
    rows.sort(key=order.get(sort, order['name']))
    total = len(rows)
    per_page = 30
    start = (page - 1) * per_page
    page_rows = rows[start:start + per_page]
    interests = sorted({i for r in ParkEntity.query.all() for i in r.interest_list()})
    ages = sorted({a for r in ParkEntity.query.all() for a in r.age_list()})
    return render_template('attractions.html', rows=page_rows, total=total,
                           interests=interests, ages=ages,
                           park_names=PARK_NAMES, q=q, park=park, type=etype,
                           interest=interest, age=age, height=height,
                           sort=sort, page=page,
                           pages=max(1, -(-total // per_page)), img=_img)


@app.route('/parks/attractions/<park>/<slug>')
def attraction_detail(park, slug):
    entity = db.session.get(ParkEntity, f'{park}/{slug}')
    if not entity:
        abort(404)
    detail = entity.detail()
    related = [db.session.get(ParkEntity, k)
               for k in entity.related_list()]
    related = [r for r in related if r]
    return render_template('attraction_detail.html', e=entity,
                           detail=detail, related=related[:4], img=_img)


@app.route('/shop')
def shop():
    collections = [
        ('sale', 'Sale'),
        ('clothing', 'Clothes'),
        ('accessories', 'Accessories'),
        ('toys', 'Toys'),
    ]
    featured = (Product.query.filter(Product.price > 0)
                .order_by(Product.reviews.desc().nullslast(),
                          Product.rating.desc().nullslast()).limit(10).all())
    return render_template('shop.html', collections=collections,
                           featured=featured, img=_img)


@app.route('/shop/<collection>')
def shop_collection(collection):
    if collection not in ('sale', 'clothing', 'accessories', 'toys'):
        abort(404)
    q = (request.args.get('q') or '').strip()
    category = request.args.get('category') or ''
    character = request.args.get('character') or ''
    target = request.args.get('target_age') or ''
    sort = request.args.get('sort') or 'featured'
    page = max(1, int(request.args.get('page', 1) or 1))
    query = Product.query.filter(Product.collections.ilike(f'%{collection}%'))
    if q:
        query = query.filter(Product.name.ilike(f'%{q}%'))
    if category:
        query = query.filter_by(category=category)
    if character:
        query = query.filter_by(character=character)
    if target:
        query = query.filter_by(target_age=target)
    rows = query.all()
    if sort == 'price_low':
        rows.sort(key=lambda p: (p.price or 9999))
    elif sort == 'price_high':
        rows.sort(key=lambda p: -(p.price or 0))
    elif sort == 'rating':
        rows.sort(key=lambda p: (-(p.rating or 0), -(p.reviews or 0)))
    else:
        rows.sort(key=lambda p: (-(p.reviews or 0), -(p.rating or 0)))
    total = len(rows)
    per_page = 24
    start = (page - 1) * per_page
    page_rows = rows[start:start + per_page]
    categories = sorted({p.category for p in
                          Product.query.filter(
                              Product.collections.ilike(f'%{collection}%')).all()
                          if p.category})
    characters = sorted({p.character for p in
                          Product.query.filter(
                              Product.collections.ilike(f'%{collection}%')).all()
                          if p.character})
    targets = sorted({p.target_age for p in
                       Product.query.filter(
                           Product.collections.ilike(f'%{collection}%')).all()
                       if p.target_age})
    label = {'sale': 'Sale', 'clothing': 'Clothes',
             'accessories': 'Accessories', 'toys': 'Toys'}[collection]
    return render_template('shop_collection.html', rows=page_rows,
                           total=total, categories=categories,
                           characters=characters, targets=targets,
                           collection=collection, label=label, q=q,
                           category=category, character=character,
                           target_age=target, sort=sort, page=page,
                           pages=max(1, -(-total // per_page)), img=_img)


@app.route('/shop/products/<pid>')
def product_detail(pid):
    product = db.session.get(Product, pid)
    if not product:
        abort(404)
    related = (Product.query.filter(Product.pid != pid,
                                     Product.category == product.category)
               .order_by(Product.rating.desc().nullslast()).limit(4).all())
    return render_template('product_detail.html', p=product, related=related,
                           img=_img)


@app.route('/bag')
def bag():
    rows = _bag_rows()
    return render_template('bag.html', rows=rows, total=_bag_total(rows))


@app.route('/bag/add', methods=['POST'])
def bag_add():
    pid = request.form.get('pid') or ''
    qty = max(1, int(request.form.get('qty') or 1))
    product = db.session.get(Product, pid)
    if not product:
        abort(404)
    key = _cart_key()
    row = CartItem.query.filter_by(cart_key=key, product_pid=pid).first()
    if row:
        row.qty += qty
    else:
        db.session.add(CartItem(cart_key=key, product_pid=pid, qty=qty))
    db.session.commit()
    return redirect(url_for('bag'))


@app.route('/bag/update', methods=['POST'])
def bag_update():
    row_id = int(request.form.get('row_id') or 0)
    qty = int(request.form.get('qty') or 0)
    key = _cart_key()
    row = db.session.get(CartItem, row_id)
    if row and row.cart_key == key:
        if qty <= 0:
            db.session.delete(row)
        else:
            row.qty = qty
        db.session.commit()
    return redirect(url_for('bag'))


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    rows = _bag_rows()
    if not rows:
        return redirect(url_for('shop'))
    total = _bag_total(rows)
    if request.method == 'GET':
        return render_template('checkout.html', rows=rows, total=total)
    email = (request.form.get('email') or '').strip().lower()
    name = (request.form.get('name') or '').strip()
    address = (request.form.get('address') or '').strip()
    error = None
    if '@' not in email or not name or not address:
        error = 'Enter your full name, a valid email and a shipping address.'
    if error:
        return render_template('checkout.html', rows=rows, total=total,
                               error=error)
    confirmation = 'DS' + secrets.token_hex(4).upper()[:7]
    order = ShopOrder(confirmation=confirmation, email=email, name=name,
                      items_json=json.dumps([
                          {'pid': r['product'].pid, 'name': r['product'].name,
                           'qty': r['row'].qty, 'line': r['line']}
                          for r in rows]),
                      total=total, placed_at=MIRROR_TS)
    db.session.add(order)
    for r in rows:
        db.session.delete(r['row'])
    db.session.commit()
    return redirect(url_for('order_confirmation', code=confirmation))


@app.route('/order/<code>')
def order_confirmation(code):
    order = ShopOrder.query.filter_by(confirmation=code).first_or_404()
    items = json.loads(order.items_json)
    return render_template('order_confirmation.html', order=order,
                           items=items)


@app.route('/live-shows')
def live_shows():
    musicals = LiveShow.query.filter_by(kind='broadway').order_by(LiveShow.title).all()
    tours = LiveShow.query.filter_by(kind='ice_tour').all()
    events = IceEvent.query.count()
    return render_template('live_shows.html', musicals=musicals, tours=tours,
                           events=events, img=_img)


@app.route('/live-shows/disney-on-ice')
def doi_schedule():
    q = (request.args.get('q') or '').strip()
    show = request.args.get('show') or ''
    sort = request.args.get('sort') or 'date'
    page = max(1, int(request.args.get('page', 1) or 1))
    query = IceEvent.query
    if q:
        like = r'\b' + re.escape(q) + r'\b'
        rows = [e for e in query.all()
                if re.search(like, e.city or '', re.I)
                or re.search(like, e.venue or '', re.I)]
    else:
        rows = query.all()
    if show:
        rows = [e for e in rows if e.show == show]
    if sort == 'city':
        rows.sort(key=lambda e: e.city)
    elif sort == 'show':
        rows.sort(key=lambda e: (e.show, e.city))
    else:
        rows.sort(key=lambda e: (e.date_range or '', e.city))
    total = len(rows)
    per_page = 20
    start = (page - 1) * per_page
    page_rows = rows[start:start + per_page]
    shows = sorted({e.show for e in IceEvent.query.all()})
    return render_template('doi_schedule.html', rows=page_rows, total=total,
                           shows=shows, q=q, show=show, sort=sort, page=page,
                           pages=max(1, -(-total // per_page)))


@app.route('/live-shows/disney-on-ice/<event_id>')
def doi_event(event_id):
    event = db.session.get(IceEvent, event_id)
    if not event:
        abort(404)
    return render_template('doi_event.html', e=event,
                           performances=event.performance_list())


@app.route('/live-shows/disney-on-ice/<event_id>/book', methods=['GET', 'POST'])
def book_tickets(event_id):
    event = db.session.get(IceEvent, event_id)
    if not event:
        abort(404)
    performances = event.performance_list()
    day = request.values.get('day') or ''
    time = request.values.get('time') or ''
    if day and day not in [p['day'] for p in performances]:
        day = ''
    if day and time:
        valid_times = [t for p in performances if p['day'] == day
                       for t in p['times']]
        if time not in valid_times:
            time = ''
    error = None
    if request.method == 'POST':
        day = request.form.get('day') or ''
        time = request.form.get('time') or ''
        valid_days = [p['day'] for p in performances]
        valid_times = {p['day']: p['times'] for p in performances}
        if day not in valid_days:
            day, time = '', ''
        elif time not in valid_times.get(day, []):
            time = ''
        try:
            qty = int(request.form.get('qty') or 0)
        except ValueError:
            qty = 0
        email = (request.form.get('email') or '').strip().lower()
        name = (request.form.get('name') or '').strip()
        if not day or not time:
            error = 'Choose a performance date and show time.'
        elif qty < 1 or qty > 8:
            error = 'Choose 1 to 8 tickets.'
        elif '@' not in email or not name:
            error = 'Enter your full name and a valid email.'
        if not error:
            unit = 35.0
            total = round(unit * qty, 2)
            confirmation = 'TK' + secrets.token_hex(4).upper()[:7]
            db.session.add(TicketOrder(
                confirmation=confirmation, email=email, name=name,
                event_id=event.event_id, show_title=event.show,
                city=event.city, venue=event.venue, day=day, time=time,
                qty=qty, unit_price=unit, total=total, placed_at=MIRROR_TS))
            db.session.commit()
            return redirect(url_for('ticket_confirmation', code=confirmation))
    return render_template('book_tickets.html', e=event,
                           performances=performances, day=day, time=time,
                           error=error, unit=35.0)


@app.route('/tickets/<code>')
def ticket_confirmation(code):
    order = TicketOrder.query.filter_by(confirmation=code).first_or_404()
    return render_template('ticket_confirmation.html', order=order)


@app.route('/search')
def search():
    q = (request.args.get('q') or '').strip()
    movies, shows, games, entities, products = [], [], [], [], []
    if q:
        like = f'%{q}%'
        # Full result lists: the printed section counts are the true match
        # counts, so a reported count always equals what the page lists.
        movies = Movie.query.filter(Movie.title.ilike(like)) \
            .order_by(Movie.title).all()
        shows = Show.query.filter(Show.title.ilike(like)) \
            .order_by(Show.title).all()
        games = Game.query.filter(Game.title.ilike(like)).all()
        entities = ParkEntity.query.filter(ParkEntity.name.ilike(like)) \
            .order_by(ParkEntity.name).all()
        products = Product.query.filter(Product.name.ilike(like)) \
            .order_by(Product.name).all()
    return render_template('search.html', q=q, movies=movies, shows=shows,
                           games=games, entities=entities, products=products,
                           img=_img)


# ------------------------------------------------------------------ account --

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    email = (request.form.get('email') or '').strip().lower()
    password = request.form.get('password') or ''
    user = User.query.filter_by(email=email).first()
    if user and bcrypt.check_password_hash(user.password_hash, password):
        login_user(user)
        target = request.args.get('next') or request.form.get('next')
        if target and target.startswith('/'):
            return redirect(target)
        return redirect(url_for('home'))
    return render_template('login.html', error='Invalid email or password.')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
    name = (request.form.get('name') or '').strip()
    email = (request.form.get('email') or '').strip().lower()
    password = request.form.get('password') or ''
    if not name or '@' not in email or len(password) < 8:
        return render_template(
            'signup.html',
            error='Enter your full name, a valid email and a password of at '
                  'least 8 characters.')
    if User.query.filter_by(email=email).first():
        return render_template('signup.html',
                               error='An account with that email already exists.')
    user = User(email=email, name=name,
                password_hash=bcrypt.generate_password_hash(password).decode(),
                joined=MIRROR_TS)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return redirect(url_for('home'))


@app.route('/favorites')
@login_required
def favorites():
    rows = Favorite.query.filter_by(user_id=current_user.id) \
        .order_by(Favorite.id).all()
    grouped = {'movie': [], 'show': [], 'attraction': [], 'product': [], 'game': []}
    for row in rows:
        if row.item_type == 'movie':
            item = db.session.get(Movie, row.item_key)
        elif row.item_type == 'show':
            item = db.session.get(Show, row.item_key)
        elif row.item_type == 'attraction':
            item = db.session.get(ParkEntity, row.item_key)
        elif row.item_type == 'product':
            item = db.session.get(Product, row.item_key)
        else:
            item = db.session.get(Game, row.item_key)
        grouped[row.item_type].append({'row': row, 'item': item})
    return render_template('favorites.html', grouped=grouped, img=_img)


@app.route('/favorites/toggle', methods=['POST'])
@login_required
def favorites_toggle():
    item_type = request.form.get('type') or ''
    item_key = request.form.get('key') or ''
    models = {'movie': Movie, 'show': Show, 'attraction': ParkEntity,
              'product': Product, 'game': Game}
    if item_type not in models:
        abort(400)
    # Fail closed on keys that resolve to nothing: a favorite must always
    # reference a real catalog row, or it would count without rendering.
    if not item_key or not db.session.get(models[item_type], item_key):
        abort(400)
    row = Favorite.query.filter_by(user_id=current_user.id,
                                    item_type=item_type,
                                    item_key=item_key).first()
    if row:
        db.session.delete(row)
        db.session.commit()
        return redirect(request.form.get('back') or url_for('favorites'))
    db.session.add(Favorite(user_id=current_user.id, item_type=item_type,
                           item_key=item_key, added_at=MIRROR_TS))
    db.session.commit()
    return redirect(request.form.get('back') or url_for('favorites'))


# -------------------------------------------------------------- error pages --

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


# -------------------------------------------------------------------- seeds --

def seed_database():
    if Movie.query.count() > 0:
        return
    from seed_lib import seed_all
    seed_all(db)


def seed_benchmark_users():
    from seed_lib import seed_benchmark_users as _s
    _s(db)


def main():
    with app.app_context():
        db.create_all()
        seed_database()
        seed_benchmark_users()


with app.app_context():
    db.create_all()
    if os.environ.get('DISNEY_AUTO_SEED', '1') == '1':
        seed_database()
        seed_benchmark_users()
