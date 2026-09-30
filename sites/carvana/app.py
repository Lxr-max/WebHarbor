#!/usr/bin/env python3
"""carvana — a WebHarbor mirror of https://www.carvana.com/

Flask + SQLite mirror of Carvana (used-car e-commerce vertical): the home
search, the car SERP with the upstream filter taxonomy (make, model, body
style, price, year, mileage, fuel, transmission, drivetrain, features) and
pagination, vehicle detail pages with the captured photo galleries, key
specs, features, vehicle history, inspection highlights and owner reviews,
the per-vehicle financing monthly-payment estimator (down payment, term,
credit tier over the captured APR), the checkout purchase flow with
delivery scheduling, the sell-your-car instant-offer flow, the account area
(favorites, orders with status timelines, profile) and the upstream content
pages (how it works, financing, help, reviews, certified program, vending
machine, vehicle protection plans, insurance, repairs, EV guide, value
tracker) seeded for four benchmark users.

Content comes from the tracked source_data/*.json snapshots captured from
carvana.com on 2026-09-29 with a headful Chromium that rendered the real
site behind its Cloudflare bot management (see provenance.json); the
SQLite seed is materialized deterministically at image build time
(PYTHONHASHSEED=0).
"""
import json
import math
import os
import re

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
app.config["SECRET_KEY"] = os.environ.get("CARVANA_SECRET_KEY") or "webharbor-carvana-dev-key"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'CARVANA_DB_URI', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'carvana.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'authn_login'
login_manager.login_message = 'Please log in to continue.'
csrf = CSRFProtect(app)

# The mirror is a frozen snapshot of the upstream site taken 2026-09-29.
MIRROR_DATE = "2026-09-29"
SITE_NAME = "carvana"
UPSTREAM = "https://www.carvana.com/"
# bcrypt hash of 'TestPass123!' — frozen so the seed DB is byte-reproducible.
BENCHMARK_PASSWORD_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')
SOURCE = os.path.join(BASE_DIR, 'source_data')

PER_PAGE = 24          # upstream SRP page size
DEFAULT_APR = 0.0699   # captured upstream default APR (6.99%)
# Credit-tier APRs as the upstream soft-pull modal presents them.
CREDIT_TIERS = [
    ('excellent', 'Excellent (781+)', 0.0549),
    ('great', 'Great (720-780)', 0.0624),
    ('good', 'Good (660-719)', 0.0699),
    ('fair', 'Fair (600-659)', 0.0874),
    ('poor', 'Poor (<600)', 0.1199),
]
TERMS = [36, 48, 60, 66, 72, 75, 84]
BODY_STYLES = ['Sedan', 'SUV', 'Truck', 'Hatchback', 'Coupe', 'Convertible',
               'Wagon', 'Minivan']
FUEL_TYPES = ['Gas', 'Electric', 'Hybrid', 'Diesel', 'Flex Fuel']
SORTS = {
    'relevance': 'Best match',
    'price_asc': 'Price: low to high',
    'price_desc': 'Price: high to low',
    'mileage_asc': 'Mileage: low to high',
    'year_desc': 'Year: newest',
}


def _load(name):
    with open(os.path.join(SOURCE, name), encoding='utf-8') as f:
        return json.load(f)


# --------------------------------------------------------- asset resolution --

_INVENTORY = None


def _inventory():
    global _INVENTORY
    if _INVENTORY is None:
        _INVENTORY = {}
        path = os.path.join(BASE_DIR, 'asset_inventory.json')
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                for row in json.load(f).get('assets', []):
                    fname = os.path.basename(row['path'])
                    _INVENTORY[fname.rsplit('.', 1)[0]] = row['path']
    return _INVENTORY


def img(name):
    """URL for a managed upstream asset by logical name (None if absent)."""
    inv = _inventory()
    rel = inv.get(name) or inv.get(name.rsplit('.', 1)[0])
    if not rel:
        return None
    return '/' + rel


@app.template_filter('money')
def money(v):
    return f"${v:,.0f}" if v is not None else '—'


@app.template_filter('mileage')
def mileage_fmt(v):
    return f"{v:,} miles" if v is not None else '—'


# ------------------------------------------------------------------- models --

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(160), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_benchmark = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.String(10), nullable=False, default='2026-09-01')


class Profile(db.Model):
    __tablename__ = 'profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False,
                       unique=True)
    user = db.relationship('User')
    phone = db.Column(db.String(40))
    street = db.Column(db.String(160))
    city = db.Column(db.String(100))
    state = db.Column(db.String(8))
    zip5 = db.Column(db.String(10))
    about = db.Column(db.Text)


class Vehicle(db.Model):
    """One captured upstream vehicle row (SRP card + VDP detail merge)."""
    __tablename__ = 'vehicles'
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, unique=True, nullable=False)
    stock_number = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    make = db.Column(db.String(60), nullable=False)
    model = db.Column(db.String(80), nullable=False)
    trim = db.Column(db.String(120))
    body_style = db.Column(db.String(30), nullable=False)
    mileage = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    previous_price = db.Column(db.Integer)
    kbb_value = db.Column(db.Integer)
    msrp = db.Column(db.Integer)
    exterior_color = db.Column(db.String(60))
    interior_color = db.Column(db.String(60))
    fuel_type = db.Column(db.String(30))
    mpg_combined = db.Column(db.Integer)
    transmission = db.Column(db.String(80))
    drivetrain = db.Column(db.String(30))
    engine = db.Column(db.String(160))
    seating = db.Column(db.Integer)
    doors = db.Column(db.Integer)
    vin = db.Column(db.String(24))
    city = db.Column(db.String(80))
    state = db.Column(db.String(8))
    offering = db.Column(db.String(20))
    single_owner = db.Column(db.Boolean, default=False)
    accident_free = db.Column(db.Boolean, default=True)
    prior_uses = db.Column(db.String(120))     # comma list
    card_image = db.Column(db.String(80))      # logical asset name
    hero_image = db.Column(db.String(80))
    gallery = db.Column(db.Text)              # JSON list of logical names
    interior_image = db.Column(db.String(80))
    badges = db.Column(db.Text)                # JSON list of badge strings
    highlights = db.Column(db.Text)           # JSON list of highlight strings
    features = db.Column(db.Text)              # JSON list of feature strings
    installed_options = db.Column(db.Text)     # JSON list of option names
    narratives = db.Column(db.Text)            # JSON list of bullet dicts
    inspection = db.Column(db.Text)            # JSON list of inspection facts
    warranty_text = db.Column(db.String(200))
    in_service_date = db.Column(db.String(20))
    price_dropped_at = db.Column(db.String(20))
    apr = db.Column(db.String(8))               # captured default APR, e.g. '6.99'
    default_term = db.Column(db.Integer)       # captured default term months
    estimated_taxes_fees = db.Column(db.Integer)
    has_detail = db.Column(db.Boolean, default=False)   # full VDP capture exists

    def badge_list(self):
        return json.loads(self.badges or '[]')

    def highlight_list(self):
        return json.loads(self.highlights or '[]')

    def feature_list(self):
        return json.loads(self.features or '[]')

    def option_list(self):
        return json.loads(self.installed_options or '[]')

    def narrative_list(self):
        return json.loads(self.narratives or '[]')

    def inspection_list(self):
        return json.loads(self.inspection or '[]')

    def gallery_list(self):
        return json.loads(self.gallery or '[]')

    def prior_use_display(self):
        uses = [u for u in (self.prior_uses or '').split(',') if u]
        if not uses:
            return '—'
        return ', '.join(uses)

    def title(self):
        return f"{self.year} {self.make} {self.model}"

    def subtitle(self):
        return f"{self.trim or self.body_style}"

    def url(self):
        return url_for('vehicle_detail', vehicle_id=self.vehicle_id)

    def card_image_url(self):
        return img(self.card_image) if self.card_image else None

    def hero_image_url(self):
        return img(self.hero_image) if self.hero_image else None

    def interior_image_url(self):
        return img(self.interior_image) if self.interior_image else None

    def gallery_urls(self):
        return [img(n) for n in self.gallery_list() if img(n)]

    def default_apr(self):
        return float(self.apr) if self.apr else DEFAULT_APR * 100

    # -------------------------------------------------- payment mathematics --

    def financed_principal(self, down_payment=0, trade_credit=0,
                           include_taxes_fees=True):
        """Amount financed: price minus cash/trade credits plus the
        captured estimated taxes & fees (the upstream estimate includes
        them, so the mirror does too)."""
        principal = self.price - (down_payment or 0) - (trade_credit or 0)
        if include_taxes_fees and self.estimated_taxes_fees:
            principal += self.estimated_taxes_fees
        return max(principal, 0)

    def monthly_payment(self, down_payment=0, term=None, apr_percent=None,
                        trade_credit=0):
        """Standard amortization: M = P*r / (1 - (1+r)^-n).

        Mirrors the upstream estimator: principal = price + captured
        estimated taxes & fees - down payment - trade credit, monthly
        rate r = apr/12, n = term months.
        """
        term = int(term or self.default_term or 72)
        apr = float(apr_percent if apr_percent is not None else self.default_apr())
        principal = self.financed_principal(down_payment, trade_credit)
        r = apr / 100.0 / 12.0
        if principal <= 0:
            return 0
        if r <= 0:
            return principal / term
        return principal * r / (1 - math.pow(1 + r, -term))


class Favorite(db.Model):
    __tablename__ = 'favorites'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'),
                           nullable=False)
    saved_at = db.Column(db.String(10), nullable=False, default=MIRROR_DATE)
    vehicle = db.relationship('Vehicle')

    __table_args__ = (db.UniqueConstraint('user_id', 'vehicle_id',
                                          name='uq_fav_user_vehicle'),)


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User')
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'),
                           nullable=False)
    vehicle = db.relationship('Vehicle')
    payment_type = db.Column(db.String(20), nullable=False)   # cash | finance
    down_payment = db.Column(db.Integer, default=0)
    trade_credit = db.Column(db.Integer, default=0)
    term_months = db.Column(db.Integer)
    apr = db.Column(db.String(8))
    monthly_payment = db.Column(db.Integer)
    delivery_date = db.Column(db.String(20), nullable=False)
    delivery_slot = db.Column(db.String(40), nullable=False)
    delivery_city = db.Column(db.String(100), nullable=False)
    delivery_state = db.Column(db.String(8), nullable=False)
    delivery_street = db.Column(db.String(160), nullable=False)
    delivery_zip = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(40), nullable=False, default='Order placed')
    created_at = db.Column(db.String(10), nullable=False, default=MIRROR_DATE)

    def events(self):
        return (OrderEvent.query.filter_by(order_id=self.id)
                .order_by(OrderEvent.occurred_at, OrderEvent.id).all())


class OrderEvent(db.Model):
    __tablename__ = 'order_events'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    status = db.Column(db.String(60), nullable=False)
    note = db.Column(db.String(240))
    occurred_at = db.Column(db.String(20), nullable=False, default=MIRROR_DATE)


class TradeInOffer(db.Model):
    """A completed sell-your-car instant offer."""
    __tablename__ = 'trade_in_offers'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User')
    vin = db.Column(db.String(24), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    make = db.Column(db.String(60), nullable=False)
    model = db.Column(db.String(80), nullable=False)
    trim = db.Column(db.String(120))
    mileage = db.Column(db.Integer, nullable=False)
    condition = db.Column(db.String(40))
    offer_amount = db.Column(db.Integer, nullable=False)
    offer_code = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.String(10), nullable=False, default=MIRROR_DATE)


class VehicleReview(db.Model):
    """Owner reviews captured from the upstream reviews API."""
    __tablename__ = 'vehicle_reviews'
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, nullable=False)   # upstream vehicleId
    make_model = db.Column(db.String(120))
    rating = db.Column(db.Integer)
    review_date = db.Column(db.String(12))
    author = db.Column(db.String(60))
    text = db.Column(db.Text)


class SearchSnapshot(db.Model):
    """Upstream SERP context for the captured search pages."""
    __tablename__ = 'search_snapshots'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), nullable=False)   # srp_all, srp_make_honda...
    url = db.Column(db.String(200), nullable=False)
    upstream_total = db.Column(db.Integer, nullable=False)
    page1_order = db.Column(db.Text)                 # JSON [vehicle_id, ...]

    def order_ids(self):
        return json.loads(self.page1_order or '[]')


class HelpArticle(db.Model):
    """A captured /help/<section>/<article>/ Q&A page."""
    __tablename__ = 'help_articles'
    id = db.Column(db.Integer, primary_key=True)
    section = db.Column(db.String(60), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)

    def url(self):
        return url_for('help_article', section=self.section,
                       slug=self.slug)


@login_manager.user_loader
def load_user(uid):
    return db.session.get(User, int(uid))


# -------------------------------------------------------------- page helpers --

def _facet_makes():
    """Make/model taxonomy from the captured upstream facet payload."""
    rows = Vehicle.query.with_entities(Vehicle.make, Vehicle.model).distinct().all()
    makes = {}
    for make, model in sorted(rows):
        makes.setdefault(make, []).append(model)
    return makes


def _slider_ranges():
    prices = [v.price for v in Vehicle.query.all()]
    miles = [v.mileage for v in Vehicle.query.all()]
    years = [v.year for v in Vehicle.query.all()]
    return {
        'price_min': min(prices) if prices else 0,
        'price_max': max(prices) if prices else 100000,
        'mileage_min': min(miles) if miles else 0,
        'mileage_max': max(miles) if miles else 200000,
        'year_min': min(years) if years else 2010,
        'year_max': max(years) if years else 2027,
    }


def _apply_filters(query, args):
    """The upstream SERP filter taxonomy, driven by query params."""
    def _int(name, default=None):
        try:
            return int(args.get(name, ''))
        except (TypeError, ValueError):
            return default

    make = args.get('make', '').strip()
    model = args.get('model', '').strip()
    body = args.get('body', '').strip()
    fuel = args.get('fuel', '').strip()
    transmission = args.get('transmission', '').strip()
    drivetrain = args.get('drivetrain', '').strip()
    price_min = _int('price_min')
    price_max = _int('price_max')
    year_min = _int('year_min')
    year_max = _int('year_max')
    mileage_min = _int('mileage_min')
    mileage_max = _int('mileage_max')
    payment_max = _int('payment_max')
    single_owner = args.get('single_owner', '').strip()
    accident_free = args.get('accident_free', '').strip()
    q = query
    if make:
        q = q.filter(Vehicle.make == make)
    if model:
        q = q.filter(Vehicle.model == model)
    if body:
        q = q.filter(Vehicle.body_style == body)
    if fuel:
        q = q.filter(Vehicle.fuel_type == fuel)
    if transmission:
        q = q.filter(Vehicle.transmission.ilike(f'%{transmission}%'))
    if drivetrain:
        q = q.filter(Vehicle.drivetrain == drivetrain)
    if price_min is not None:
        q = q.filter(Vehicle.price >= price_min)
    if price_max is not None:
        q = q.filter(Vehicle.price <= price_max)
    if year_min is not None:
        q = q.filter(Vehicle.year >= year_min)
    if year_max is not None:
        q = q.filter(Vehicle.year <= year_max)
    if mileage_min is not None:
        q = q.filter(Vehicle.mileage >= mileage_min)
    if mileage_max is not None:
        q = q.filter(Vehicle.mileage <= mileage_max)
    if payment_max is not None:
        q = q.filter(Vehicle.price <= payment_max * 12)  # coarse prefilter
    if single_owner:
        q = q.filter(Vehicle.single_owner.is_(True))
    if accident_free:
        q = q.filter(Vehicle.accident_free.is_(True))
    return q


def _sort_results(query, sort):
    if sort == 'price_asc':
        return query.order_by(Vehicle.price.asc(), Vehicle.vehicle_id.asc())
    if sort == 'price_desc':
        return query.order_by(Vehicle.price.desc(), Vehicle.vehicle_id.asc())
    if sort == 'mileage_asc':
        return query.order_by(Vehicle.mileage.asc(), Vehicle.vehicle_id.asc())
    if sort == 'year_desc':
        return query.order_by(Vehicle.year.desc(), Vehicle.vehicle_id.asc())
    return query.order_by(Vehicle.vehicle_id.asc())


def _search(args):
    """Search over the captured corpus the way the upstream SERP does:
    keyword match on year/make/model/trim/body, then the filter panel."""
    terms = [t for t in re.split(r'\s+', args.get('q', '').strip()) if t]
    query = Vehicle.query
    for t in terms:
        like = f"%{t}%"
        query = query.filter(db.or_(
            Vehicle.make.ilike(like), Vehicle.model.ilike(like),
            Vehicle.trim.ilike(like), Vehicle.body_style.ilike(like),
            db.cast(Vehicle.year, db.String).ilike(like)))
    query = _apply_filters(query, args)
    return _sort_results(query, args.get('sort', 'relevance'))


def _active_filters(args):
    """Filter chips the SRP shows for the current query."""
    labels = []
    for key, label in (('make', 'Make'), ('model', 'Model'),
                      ('body', 'Body style'), ('fuel', 'Fuel'),
                      ('transmission', 'Transmission'),
                      ('drivetrain', 'Drivetrain')):
        val = args.get(key, '').strip()
        if val:
            labels.append((key, f"{label}: {val}"))
    for key, label in (('price_min', 'Min price'), ('price_max', 'Max price'),
                      ('year_min', 'Min year'), ('year_max', 'Max year'),
                      ('mileage_min', 'Min mileage'),
                      ('mileage_max', 'Max mileage')):
        val = args.get(key, '').strip()
        if val:
            labels.append((key, f"{label}: {val}"))
    if args.get('single_owner', '').strip():
        labels.append(('single_owner', 'Single owner'))
    if args.get('accident_free', '').strip():
        labels.append(('accident_free', 'Accident free'))
    return labels


# -------------------------------------------------------------------- routes --

@app.route('/')
def home():
    makes = _facet_makes()
    popular = [
        ('honda', 'Civic'), ('honda', 'Accord'), ('toyota', 'Camry'),
        ('toyota', 'Corolla'), ('toyota', 'RAV4'), ('tesla', 'Model 3'),
        ('tesla', 'Model Y'), ('ford', 'F-150'), ('ford', 'Mustang'),
        ('jeep', 'Wrangler'), ('chevrolet', 'Silverado 1500'),
        ('nissan', 'Altima'), ('hyundai', 'Elantra'), ('kia', 'Forte'),
        ('bmw', '3 Series'), ('mercedes-benz', 'C-Class'),
        ('mazda', 'CX-5'), ('subaru', 'Outback'),
    ]
    count = Vehicle.query.count()
    body_counts = {}
    for b in BODY_STYLES:
        body_counts[b] = Vehicle.query.filter_by(body_style=b).count()
    featured = (Vehicle.query.filter(Vehicle.has_detail.is_(True))
                .order_by(Vehicle.vehicle_id).limit(6).all())
    return render_template('home.html', makes=makes, popular=popular,
                           count=count, featured=featured,
                           body_styles=BODY_STYLES,
                           body_counts=body_counts)


@app.route('/cars')
@app.route('/cars/')
def cars_search():
    args = request.args
    results = _search(args)
    total = results.count()
    try:
        page = max(1, int(args.get('page', 1)))
    except ValueError:
        page = 1
    pagination = results.paginate(page=page, per_page=PER_PAGE,
                                  error_out=False)
    snapshot = None
    if not args:
        snap = SearchSnapshot.query.filter_by(key='srp_all').first()
        if snap:
            snapshot = snap
    return render_template(
        'cars_search.html', vehicles=pagination.items, total=total,
        pagination=pagination, args=args, makes=_facet_makes(),
        ranges=_slider_ranges(), body_styles=BODY_STYLES,
        fuel_types=FUEL_TYPES, sorts=SORTS,
        active=_active_filters(args), snapshot=snapshot)


@app.route('/cars/<path:slug>')
def cars_landing(slug):
    """Upstream SEO landing pages: /cars/<make> and /cars/<make>-<model>."""
    slug = slug.strip('/')
    if '-' not in slug:
        make = slug.replace('-', ' ').strip()
        target = Vehicle.query.filter(
            db.func.lower(Vehicle.make) == db.func.lower(make)).first()
        if not target:
            abort(404)
        results = _search(request.args.clone() if hasattr(request.args, 'clone')
                          else request.args) if False else None
        args = dict(request.args)
        args['make'] = target.make
        return redirect(url_for('cars_search', **args))
    # make-model: first segment is the make, rest joined is the model
    head, rest = slug.split('-', 1)
    make = head.replace('-', ' ').strip()
    model = rest.replace('-', ' ').strip()
    target = Vehicle.query.filter(
        db.func.lower(Vehicle.make) == db.func.lower(make),
        db.func.lower(Vehicle.model) == db.func.lower(model)).first()
    if not target:
        # hyphenated makes: mercedes-benz-c-class -> make Mercedes-Benz,
        # model C-Class (upstream keeps the model's own hyphens)
        for m in _facet_makes():
            prefix = m.lower().replace(' ', '-') + '-'
            if slug.lower().startswith(prefix):
                model_slug = slug[len(prefix):]
                target = Vehicle.query.filter(
                    db.func.lower(Vehicle.make) == db.func.lower(m),
                    db.func.lower(Vehicle.model) == model_slug.lower()).first()
                if target:
                    make = m
                    break
    if not target:
        abort(404)
    args = dict(request.args)
    args['make'] = target.make
    args['model'] = target.model
    return redirect(url_for('cars_search', **args))


@app.route('/vehicle/<int:vehicle_id>')
def vehicle_detail(vehicle_id):
    vehicle = Vehicle.query.filter_by(vehicle_id=vehicle_id).first_or_404()
    reviews = (VehicleReview.query.filter_by(vehicle_id=vehicle_id)
              .order_by(VehicleReview.review_date.desc()).limit(4).all())
    review_total = (VehicleReview.query.filter_by(vehicle_id=vehicle_id)
                    .count())
    similar = (Vehicle.query
               .filter(Vehicle.body_style == vehicle.body_style,
                       Vehicle.vehicle_id != vehicle.vehicle_id)
               .order_by(Vehicle.price.asc()).limit(3).all())
    # default estimate exactly as the upstream card renders it
    est = int(round(vehicle.monthly_payment(down_payment=0)))
    saved = False
    if current_user.is_authenticated:
        saved = (Favorite.query.filter_by(user_id=current_user.id,
                                         vehicle_id=vehicle.id).first()
                 is not None)
    return render_template('vehicle_detail.html', v=vehicle, reviews=reviews,
                           review_total=review_total, similar=similar,
                           est=est, saved=saved,
                           credit_tiers=CREDIT_TIERS, terms=TERMS)


@app.route('/vehicle/<int:vehicle_id>/payment-estimate', methods=['POST'])
def payment_estimate(vehicle_id):
    """The VDP payment estimator: real amortization over the captured APR."""
    vehicle = Vehicle.query.filter_by(vehicle_id=vehicle_id).first_or_404()
    try:
        down = max(0, int(request.form.get('down_payment', '0') or 0))
    except ValueError:
        down = 0
    try:
        term = int(request.form.get('term', str(vehicle.default_term or 72)))
    except ValueError:
        term = vehicle.default_term or 72
    if term not in TERMS:
        term = vehicle.default_term or 72
    tier = request.form.get('credit_tier', 'good')
    apr = next((a for key, _label, a in CREDIT_TIERS if key == tier),
               DEFAULT_APR)
    monthly = int(round(vehicle.monthly_payment(down_payment=down,
                                                term=term,
                                                apr_percent=apr * 100)))
    tier_label = next((label for key, label, _a in CREDIT_TIERS if key == tier),
                      tier)
    return render_template('payment_estimate.html', v=vehicle, down=down,
                           term=term, tier=tier, tier_label=tier_label,
                           apr=apr, monthly=monthly,
                           credit_tiers=CREDIT_TIERS, terms=TERMS)


@app.route('/vehicle/<int:vehicle_id>/favorite', methods=['GET', 'POST'])
@login_required
def favorite_toggle(vehicle_id):
    """POST toggles the saved state from the VDP button. GET completes the
    anonymous save flow: an anonymous "Save this car" click bounces to
    login with ?next=<this URL>, and the post-login GET lands here — it
    saves the car (idempotently) and returns to the vehicle page instead
    of dead-ending on a POST-only route (405)."""
    vehicle = Vehicle.query.filter_by(vehicle_id=vehicle_id).first_or_404()
    existing = Favorite.query.filter_by(user_id=current_user.id,
                                        vehicle_id=vehicle.id).first()
    if request.method == 'GET':
        if not existing:
            db.session.add(Favorite(user_id=current_user.id,
                                   vehicle_id=vehicle.id))
            db.session.commit()
        return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))
    db.session.add(Favorite(user_id=current_user.id, vehicle_id=vehicle.id))
    db.session.commit()
    return redirect(url_for('vehicle_detail', vehicle_id=vehicle_id))


# ----------------------------------------------------------- checkout flow --

DELIVERY_SLOTS = [
    '8:00 AM - 10:00 AM', '10:00 AM - 12:00 PM', '12:00 PM - 2:00 PM',
    '2:00 PM - 4:00 PM', '4:00 PM - 6:00 PM', '6:00 PM - 8:00 PM',
]


def _delivery_dates():
    """Seven delivery dates frozen relative to the mirror snapshot date."""
    from datetime import date, timedelta
    base = date(2026, 9, 29)
    return [(base + timedelta(days=d)).isoformat() for d in range(1, 8)]


@app.route('/vehicle/<int:vehicle_id>/checkout', methods=['GET', 'POST'])
@login_required
def checkout(vehicle_id):
    vehicle = Vehicle.query.filter_by(vehicle_id=vehicle_id).first_or_404()
    if request.method == 'GET':
        step = request.args.get('step', 'payment')
        return render_template('checkout.html', v=vehicle, step=step,
                               credit_tiers=CREDIT_TIERS, terms=TERMS,
                               delivery_dates=_delivery_dates(),
                               delivery_slots=DELIVERY_SLOTS)
    # POST: the single-page checkout submit (payment + delivery together)
    f = request.form
    payment_type = f.get('payment_type')
    if payment_type not in ('cash', 'finance'):
        return render_template('checkout.html', v=vehicle, step='payment',
                               credit_tiers=CREDIT_TIERS, terms=TERMS,
                               delivery_dates=_delivery_dates(),
                               delivery_slots=DELIVERY_SLOTS,
                               error='Choose how you want to pay.')
    down = 0
    term = None
    apr = None
    monthly = None
    if payment_type == 'finance':
        try:
            down = max(0, int(f.get('down_payment', '0') or 0))
        except ValueError:
            down = 0
        try:
            term = int(f.get('term', '72'))
        except ValueError:
            term = 72
        if term not in TERMS:
            term = 72
        tier = f.get('credit_tier', 'good')
        apr = next((a for key, _label, a in CREDIT_TIERS if key == tier),
                   DEFAULT_APR)
        monthly = int(round(vehicle.monthly_payment(down_payment=down, term=term,
                                                    apr_percent=apr * 100)))
    trade = f.get('trade_in', 'no') == 'yes'
    trade_credit = 0
    if trade:
        try:
            trade_credit = max(0, int(f.get('trade_credit', '0') or 0))
        except ValueError:
            trade_credit = 0
    delivery_date = f.get('delivery_date', '')
    delivery_slot = f.get('delivery_slot', '')
    street = f.get('street', '').strip()
    city = f.get('city', '').strip()
    state = f.get('state', '').strip().upper()
    zip5 = f.get('zip', '').strip()
    if (delivery_date not in _delivery_dates() or delivery_slot not in
            DELIVERY_SLOTS or not street or not city or len(state) != 2
            or not re.match(r'^\d{5}$', zip5)):
        return render_template('checkout.html', v=vehicle, step='delivery',
                               credit_tiers=CREDIT_TIERS, terms=TERMS,
                               delivery_dates=_delivery_dates(),
                               delivery_slots=DELIVERY_SLOTS,
                               error='Complete the delivery details to '
                                     'schedule your delivery.')
    existing = Order.query.filter_by(user_id=current_user.id,
                                     vehicle_id=vehicle.id).first()
    if existing:
        return redirect(url_for('account_orders'))
    order = Order(
        order_number=f"CV-{200000 + 13 * (Order.query.with_entities(db.func.max(Order.id)).scalar() or 0) + current_user.id}",
        user_id=current_user.id, vehicle_id=vehicle.id,
        payment_type=payment_type, down_payment=down,
        trade_credit=trade_credit, term_months=term,
        apr=(f"{apr*100:.2f}" if apr is not None else None),
        monthly_payment=monthly, delivery_date=delivery_date,
        delivery_slot=delivery_slot, delivery_street=street, delivery_city=city,
        delivery_state=state, delivery_zip=zip5,
        status='Delivery scheduled')
    db.session.add(order)
    db.session.flush()
    db.session.add(OrderEvent(order_id=order.id, status='Order placed',
                              note='Order placed online',
                              occurred_at=MIRROR_DATE))
    db.session.add(OrderEvent(
        order_id=order.id, status='Delivery scheduled',
        note=(f"Delivery scheduled for {delivery_date} "
              f"({delivery_slot}) to {city}, {state}"),
        occurred_at=MIRROR_DATE))
    db.session.commit()
    return redirect(url_for('order_confirmation', order_number=order.order_number))


@app.route('/order/<order_number>')
@login_required
def order_confirmation(order_number):
    order = Order.query.filter_by(order_number=order_number,
                                   user_id=current_user.id).first_or_404()
    return render_template('order_confirmation.html', order=order)


# ------------------------------------------------------------- account area --

@app.route('/account')
@login_required
def account_home():
    return redirect(url_for('account_favorites'))


@app.route('/account/favorites')
@login_required
def account_favorites():
    favs = (Favorite.query.filter_by(user_id=current_user.id)
            .order_by(Favorite.id.desc()).all())
    return render_template('account_favorites.html', favorites=favs)


@app.route('/account/favorites/<int:vehicle_id>/remove', methods=['POST'])
@login_required
def favorite_remove(vehicle_id):
    vehicle = Vehicle.query.filter_by(vehicle_id=vehicle_id).first_or_404()
    Favorite.query.filter_by(user_id=current_user.id,
                             vehicle_id=vehicle.id).delete()
    db.session.commit()
    return redirect(url_for('account_favorites'))


@app.route('/account/orders')
@login_required
def account_orders():
    orders = (Order.query.filter_by(user_id=current_user.id)
              .order_by(Order.id.desc()).all())
    offers = (TradeInOffer.query.filter_by(user_id=current_user.id)
              .order_by(TradeInOffer.id.desc()).all())
    return render_template('account_orders.html', orders=orders,
                           offers=offers)


@app.route('/account/orders/<order_number>/cancel', methods=['POST'])
@login_required
def order_cancel(order_number):
    order = Order.query.filter_by(order_number=order_number,
                                  user_id=current_user.id).first_or_404()
    if order.status not in ('Cancelled', 'Delivered'):
        order.status = 'Cancelled'
        db.session.add(OrderEvent(order_id=order.id, status='Cancelled',
                                  note='Order cancelled by customer',
                                  occurred_at=MIRROR_DATE))
        db.session.commit()
    return redirect(url_for('account_orders'))


@app.route('/account/profile', methods=['GET', 'POST'])
@login_required
def account_profile():
    profile = Profile.query.filter_by(user_id=current_user.id).first()
    if request.method == 'POST':
        f = request.form
        if not profile:
            profile = Profile(user_id=current_user.id)
            db.session.add(profile)
        profile.phone = f.get('phone', '').strip()
        profile.street = f.get('street', '').strip()
        profile.city = f.get('city', '').strip()
        profile.state = f.get('state', '').strip().upper()
        profile.zip5 = f.get('zip', '').strip()
        profile.about = f.get('about', '').strip()
        db.session.commit()
        return redirect(url_for('account_profile'))
    return render_template('account_profile.html', profile=profile)


# ------------------------------------------------------------ sell your car --

@app.route('/sell-my-car')
def sell_my_car():
    return render_template('sell_intro.html')


@app.route('/sell-my-car/offer', methods=['GET', 'POST'])
def sell_offer():
    """The instant-offer flow: plate/VIN, then condition questions, then a
    deterministic offer computed from the captured valuation data."""
    if request.method == 'GET':
        return render_template('sell_form.html')
    f = request.form
    vin = f.get('vin', '').strip().upper()
    mileage = f.get('mileage', '').strip()
    if len(vin) < 11 or not re.match(r'^[A-HJ-NPR-Z0-9]+$', vin):
        return render_template('sell_form.html',
                               error='Enter the full VIN (17 characters, '
                                     'no I/O/Q).')
    try:
        mileage = int(mileage)
    except (TypeError, ValueError):
        return render_template('sell_form.html',
                               error='Enter the current mileage.')
    if not (0 <= mileage <= 300000):
        return render_template('sell_form.html',
                               error='Mileage must be between 0 and 300,000.')
    # deterministic valuation from the captured KBB baseline table
    from seed_lib import vehicle_baseline, condition_multiplier
    base = vehicle_baseline(vin)
    condition = f.get('condition', 'good')
    offer = int(round(base * condition_multiplier(condition) * (1 - min(mileage, 250000) / 500000.0)))
    session['sell_offer'] = {'vin': vin, 'mileage': mileage,
                             'condition': condition, 'offer': offer,
                             'year': f.get('year', ''),
                             'make': f.get('make', ''),
                             'model': f.get('model', ''),
                             'trim': f.get('trim', '')}
    return render_template('sell_offer.html', vin=vin, mileage=mileage,
                           condition=condition, offer=offer)


@app.route('/sell-my-car/offer/claim', methods=['POST'])
@login_required
def sell_claim():
    data = session.get('sell_offer')
    if not data:
        return redirect(url_for('sell_my_car'))
    offer = TradeInOffer(user_id=current_user.id, vin=data['vin'],
                         year=int(data.get('year') or 2020),
                         make=data.get('make') or '—',
                         model=data.get('model') or '—',
                         trim=data.get('trim') or None,
                         mileage=data['mileage'], condition=data['condition'],
                         offer_amount=data['offer'],
                         offer_code=f"TI-{91000 + TradeInOffer.query.count() * 13}")
    db.session.add(offer)
    db.session.commit()
    session.pop('sell_offer', None)
    return redirect(url_for('account_orders'))


# --------------------------------------------------------------- auth pages --

@app.route('/authn/login', methods=['GET', 'POST'])
def authn_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(
                user.password_hash, request.form.get('password', '')):
            login_user(user)
            return redirect(request.args.get('next')
                            or url_for('account_home'))
        return render_template('authn_login.html',
                               error='Invalid email or password.')
    return render_template('authn_login.html')


@app.route('/authn/register', methods=['GET', 'POST'])
def authn_register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        name = request.form.get('display_name', '').strip()
        password = request.form.get('password', '')
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            return render_template('authn_register.html',
                                   error='Enter a valid email address.')
        if len(password) < 8:
            return render_template('authn_register.html',
                                   error='Password must be at least 8 '
                                         'characters.')
        if User.query.filter_by(email=email).first():
            return render_template('authn_register.html',
                                   error='An account with that email already '
                                         'exists.')
        user = User(email=email, display_name=name or email.split('@')[0],
                    password_hash=bcrypt.generate_password_hash(password),
                    is_benchmark=False, created_at=MIRROR_DATE)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('account_home'))
    return render_template('authn_register.html')


@app.route('/authn/logout')
@login_required
def authn_logout():
    logout_user()
    return redirect(url_for('home'))


# ---------------------------------------------------------- content pages ----

def _content_page(name, title):
    pages = _load('content_pages.json')
    page = pages.get(name)
    if not page:
        abort(404)
    return render_template('content_page.html', page=page,
                           title=title or page.get('title', name))


@app.route('/how-it-works')
def how_it_works():
    return _content_page('how_it_works', None)


@app.route('/financing')
def financing():
    return _content_page('financing', None)


@app.route('/faq')
def faq():
    articles = (HelpArticle.query.order_by(HelpArticle.category,
                                          HelpArticle.id).all())
    categories = []
    for a in articles:
        if a.category not in [c for c, _ in categories]:
            categories.append((a.category, []))
        categories[-1][1].append(a)
    return render_template('help_hub.html', categories=categories,
                           title='Carvana Help & Support')


@app.route('/help/<section>/<path:slug>')
def help_article(section, slug):
    article = HelpArticle.query.filter_by(
        section=section, slug=slug).first_or_404()
    related = (HelpArticle.query.filter(HelpArticle.section == section,
                                        HelpArticle.id != article.id)
               .order_by(HelpArticle.id).limit(4).all())
    return render_template('help_article.html', a=article, related=related)


@app.route('/reviews')
def reviews_page():
    return _content_page('reviews', None)


@app.route('/certified-program')
def certified_program():
    return _content_page('certified_program', None)


@app.route('/vending-machine')
def vending_machine():
    return _content_page('vending_machine', None)


@app.route('/vehicle-protection-plans')
def vehicle_protection_plans():
    return _content_page('vehicle_protection_plans', None)


@app.route('/insurance')
def insurance():
    return _content_page('insurance', None)


@app.route('/repairs')
def repairs():
    return _content_page('repairs', None)


@app.route('/guide-to-buying-a-used-ev')
def guide_to_buying_a_used_ev():
    return _content_page('guide_to_buying_a_used_ev', None)


@app.route('/value-tracker')
def value_tracker():
    return _content_page('value_tracker', None)


# --------------------------------------------------------------------- misc --

@app.route('/_health')
def health():
    return jsonify(ok=True, site=SITE_NAME,
                   vehicles=Vehicle.query.count(),
                   details=Vehicle.query.filter_by(has_detail=True).count(),
                   users=User.query.count(),
                   reviews=VehicleReview.query.count(),
                   snapshots=SearchSnapshot.query.count())


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.context_processor
def _base_context():
    saved_count = 0
    if current_user.is_authenticated:
        saved_count = Favorite.query.filter_by(
            user_id=current_user.id).count()
    return {
        'header_makes': sorted(_facet_makes().keys()),
        'saved_count': saved_count,
        'logo_url': img('combo-desktop-carvana') or img('carvana-logo'),
        'snapshot_date': MIRROR_DATE,
        'vehicle_count': Vehicle.query.count(),
    }


# --------------------------------------------------------------------- seeds --

def seed_database():
    if Vehicle.query.count() > 0:
        return
    from seed_lib import seed_all
    seed_all(db, app)


def seed_benchmark_users():
    if User.query.filter_by(is_benchmark=True).count() >= 4:
        return
    from seed_lib import seed_benchmark
    seed_benchmark(db, bcrypt, app)


def main():
    with app.app_context():
        db.create_all()
        seed_database()
        seed_benchmark_users()


with app.app_context():
    db.create_all()
    if os.environ.get('CARVANA_AUTO_SEED', '1') == '1':
        seed_database()
        seed_benchmark_users()


if __name__ == '__main__':
    main()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 40193)))
