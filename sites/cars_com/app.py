#!/usr/bin/env python3
"""cars_com — a WebHarbor mirror of https://www.cars.com/

Flask + SQLite mirror of Cars.com (car-shopping vertical): the home
search, the new/used/certified SERP with the upstream filter taxonomy
(stock type, price, mileage, year, make/model/trim, body style, colors,
fuel, transmission, drivetrain, cylinders, features, deal rating,
seller type, keyword, photos-only) plus sorting and pagination, listing
detail pages (price breakdown, deal analysis, price history, features &
specs, seller's notes, CPO program, history, dealer info, payment
estimator, consumer reviews), the dealer directory with filters and
dealer pages (about, hours, highlights, reviews, sales team, service
menu, inventory), the research model pages (trims, specs, consumer
reviews, expert's take), the side-by-side compare tool, the Instant
Cash Offer valuation wizard (Plate/VIN/Make tabs, vehicle, options,
condition, offer), the car loan payment calculator, and the shopper
account area (saved cars, saved searches, alerts) seeded for four
benchmark users.

Content comes from the tracked source_data/*.json snapshots captured
from cars.com on 2026-09-29 with a headful Chromium that passed the
upstream Cloudflare interstitial (see provenance.json); the SQLite seed
is materialized deterministically at image build time (PYTHONHASHSEED=0).
"""
import json
import math
from urllib.parse import urlsplit
import os
import re
from datetime import date

from flask import (Flask, abort, jsonify, redirect, render_template, request,
                   session, url_for)
from flask_bcrypt import Bcrypt
from flask_login import (LoginManager, UserMixin, current_user,
                         login_required, login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from markupsafe import Markup
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, instance_path=os.path.join(BASE_DIR, 'instance'))
app.config["SECRET_KEY"] = os.environ.get("CARS_COM_SECRET_KEY") or "webharbor-cars-com-dev-key"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'CARS_COM_DB_URI', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'cars_com.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'authn_login'
login_manager.login_message = 'Please log in to continue.'
csrf = CSRFProtect(app)

# The mirror is a frozen snapshot of the upstream site taken 2026-09-29
# (the real capture day recorded in provenance.json and the capture
# sidecars' timestamps).
MIRROR_DATE = date(2026, 9, 29)
MIRROR_TS = "2026-09-29"
# Frozen stamp baked into the benchmark seed rows (saved_cars.saved_at,
# saved_searches.created_at). Historical fixture date: the seed DB is
# byte-frozen by the grading contract, so seed_lib must keep stamping
# seed rows with exactly this value even though MIRROR_TS moved to the
# real capture day.
SEED_STAMP = "2026-10-13"
SITE_NAME = "cars_com"
UPSTREAM = "https://www.cars.com/"
# The Seattle metro: the frozen geo context every captured page carried.
DEFAULT_ZIP = "98101"
DEFAULT_CITY = "Seattle, WA"
# bcrypt hash of 'TestPass123!' — frozen so the seed DB is byte-reproducible.
BENCHMARK_PASSWORD_HASH = (
    '$2b$12$j5MKgUeZVBQRU6sTFTUh6udRyRL5TgYZlannvihfkQiJaObKqrNtq')
SOURCE = os.path.join(BASE_DIR, 'source_data')
PER_PAGE = 30

# Render-time asset integrity: a handful of the frozen corpus's photo
# references point at CDN files the upstream has purged since capture
# (they 404 on platform.cstatic-images.com today). photo_list() must never
# emit a path whose managed asset is missing, or the page ships a broken
# <img> URL (the double-prefix bug shipped exactly such 404s).
_STATIC_ROOT = os.path.join(BASE_DIR, 'static')
_photo_exists_cache = {}


def _photo_exists(repo_relative):
    hit = _photo_exists_cache.get(repo_relative)
    if hit is None:
        hit = os.path.isfile(os.path.join(_STATIC_ROOT, repo_relative))
        _photo_exists_cache[repo_relative] = hit
    return hit


def _renderable_photos(raw):
    """Stored photo paths -> renderable url_for('static') filenames:
    strip the repo-relative "static/" prefix (url_for adds its own) and
    drop references whose managed asset is not present."""
    out = []
    for p in raw:
        if p.startswith('static/'):
            p = p[len('static/'):]
        if _photo_exists(p):
            out.append(p)
    return out

# The upstream SERP sort selector, frozen exactly as captured.
SORTS = [
    ('best_match_desc', 'Best match'),
    ('list_price_asc', 'Lowest price'),
    ('list_price_desc', 'Highest price'),
    ('mileage_low', 'Lowest mileage'),
    ('mileage_high', 'Highest mileage'),
    ('distance_asc', 'Nearest location'),
    ('deal_rating', 'Best deal'),
    ('year_desc', 'Newest year'),
    ('year_asc', 'Oldest year'),
    ('newest_listed', 'Newest listed'),
    ('oldest_listed', 'Oldest listed'),
]
STOCK_TYPES = ['all', 'new_cpo', 'new', 'used', 'cpo']
STOCK_LABELS = {'all': 'New, used & CPO', 'new_cpo': 'New & CPO', 'new': 'New',
                'used': 'Used', 'cpo': 'Certified Pre-Owned'}
BODY_STYLES = ['suv', 'truck', 'sedan', 'coupe', 'hatchback', 'passenger_van',
               'convertible', 'cargo_van', 'minivan', 'wagon']
BODY_LABELS = {'suv': 'SUV', 'truck': 'Truck', 'sedan': 'Sedan', 'coupe': 'Coupe',
               'hatchback': 'Hatchback', 'passenger_van': 'Passenger Van',
               'convertible': 'Convertible', 'cargo_van': 'Cargo Van',
               'minivan': 'Minivan', 'wagon': 'Wagon'}
FUELS = ['diesel', 'e85_flex_fuel', 'electric', 'gasoline', 'hybrid', 'plug_in_hybrid']
FUEL_LABELS = {'diesel': 'Diesel', 'e85_flex_fuel': 'E85 Flex Fuel', 'electric': 'Electric',
               'gasoline': 'Gasoline', 'hybrid': 'Hybrid', 'plug_in_hybrid': 'Plug-In Hybrid'}
TRANSMISSIONS = ['automanual', 'automatic', 'cvt', 'manual', 'unknown']
TRANSMISSION_LABELS = {'automanual': 'Automanual', 'automatic': 'Automatic',
                       'cvt': 'CVT', 'manual': 'Manual', 'unknown': 'Unknown'}
DRIVETRAINS = ['all_wheel_drive', 'four_wheel_drive', 'front_wheel_drive',
               'rear_wheel_drive', 'unknown']
DRIVETRAIN_LABELS = {'all_wheel_drive': 'All-wheel Drive',
                     'four_wheel_drive': 'Four-wheel Drive',
                     'front_wheel_drive': 'Front-wheel Drive',
                     'rear_wheel_drive': 'Rear-wheel Drive', 'unknown': 'Unknown'}
CYLINDERS = ['3', '4', '5', '6', '8', '10', '12']
COLORS = ['beige', 'black', 'blue', 'brown', 'gold', 'gray', 'green', 'orange',
          'pink', 'purple', 'red', 'silver', 'teal', 'white', 'yellow']
DISTANCES = [10, 20, 30, 40, 50, 75, 100, 150, 200, 250, 500, 750, 1000, 2000, 5000]
DEAL_RATINGS = ['great', 'good', 'fair']
FEATURE_GROUPS = {
    'convenience': ['Adaptive Cruise Control', 'Automated Parking', 'Cooled Seats',
                    'Heated Seats', 'Heated Steering Wheel', 'Keyless Entry',
                    'Keyless Start', 'Navigation System', 'Power Liftgate',
                    'Remote Start'],
    'entertainment': ['Android Auto', 'Apple CarPlay', 'Bluetooth', 'Premium Sound System',
                      'Satellite Radio', 'USB Port', 'WiFi Hotspot'],
    'exterior': ['Alloy Wheels', 'Roof Rack', 'Sunroof/Moonroof', 'Tow Hitch'],
    'safety': ['Automatic Emergency Braking', 'Backup Camera', 'Blind Spot Monitor',
               'Brake Assist', 'LED Headlights', 'Lane Departure Warning',
               'Rear Cross Traffic Alert', 'Stability Control'],
    'seating': ['Leather Seats', 'Memory Seat', 'Third Row Seating'],
}
CREDIT_RATINGS = {
    'excellent': 'Excellent (780 - 850)',
    'good': 'Good (700 - 779)',
    'average': 'Average (620 - 699)',
    'fair': 'Fair (619 and below)',
}
CREDIT_APRS = {'excellent': 5.5, 'good': 7.0, 'average': 9.5, 'fair': 12.5}
LOAN_TERMS = [36, 48, 60, 72, 84]


def safe_next(target, fallback):
    if not target or not target.startswith('/') or target.startswith('//') or '\\' in target or any(ord(c) < 32 for c in target):
        return fallback
    parsed = urlsplit(target)
    return fallback if parsed.netloc or parsed.scheme else target


# --------------------------------------------------------------------- models --

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    display_name = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_benchmark = db.Column(db.Boolean, default=False)


class Listing(db.Model):
    __tablename__ = 'listings'
    id = db.Column(db.String(36), primary_key=True)
    stock_type = db.Column(db.String(12), nullable=False)  # New/Used/Certified
    year = db.Column(db.Integer, nullable=False)
    make = db.Column(db.String(40), nullable=False)
    make_slug = db.Column(db.String(40), nullable=False)
    model = db.Column(db.String(60), nullable=False)
    model_slug = db.Column(db.String(60), nullable=False)
    trim = db.Column(db.String(120))
    price = db.Column(db.Integer, nullable=False)
    mileage = db.Column(db.Integer, nullable=False, default=0)
    monthly_est = db.Column(db.Integer)
    monthly_apr = db.Column(db.Float)
    monthly_months = db.Column(db.Integer)
    body_style = db.Column(db.String(20))
    body_style_slug = db.Column(db.String(20))
    drivetrain = db.Column(db.String(30))
    drivetrain_slug = db.Column(db.String(30))
    fuel_type = db.Column(db.String(20))
    fuel_slug = db.Column(db.String(20))
    transmission = db.Column(db.String(30))
    transmission_slug = db.Column(db.String(20))
    cylinders = db.Column(db.Integer)
    exterior_color = db.Column(db.String(40))
    exterior_color_slug = db.Column(db.String(20))
    interior_color = db.Column(db.String(40))
    engine_desc = db.Column(db.String(160))
    mpg = db.Column(db.String(20))
    vin = db.Column(db.String(20))
    stock_number = db.Column(db.String(20))
    deal_badge = db.Column(db.String(20))          # Great Deal / Good Deal / Fair Deal / null
    deal_badge_desc = db.Column(db.Text)
    good_deal_low = db.Column(db.Integer)
    good_deal_high = db.Column(db.Integer)
    dealer_id = db.Column(db.Integer, db.ForeignKey('dealers.id'), nullable=True)
    seller_name = db.Column(db.String(120))
    seller_type = db.Column(db.String(20), default='dealership')  # dealership / private_seller
    city = db.Column(db.String(60))
    state = db.Column(db.String(4))
    distance_miles = db.Column(db.Integer)
    photos = db.Column(db.Text)                     # JSON: local image paths
    total_photos = db.Column(db.Integer)
    features = db.Column(db.Text)                   # JSON: feature-group dict
    seller_notes = db.Column(db.Text)
    price_breakdown = db.Column(db.Text)           # JSON: rows
    price_history = db.Column(db.Text)              # JSON: rows
    history = db.Column(db.Text)                    # JSON: owners/accidents/title
    cpo_program = db.Column(db.Text)
    consumer_recommend_pct = db.Column(db.Integer)
    consumer_rating = db.Column(db.Float)
    consumer_review_count = db.Column(db.Integer)
    consumer_categories = db.Column(db.Text)       # JSON: category -> score
    consumer_reviews = db.Column(db.Text)           # JSON: review rows
    est_apr = db.Column(db.Float)
    sales_tax_pct = db.Column(db.Float)
    has_detail = db.Column(db.Boolean, default=False)
    listed_at = db.Column(db.String(10))            # frozen ISO date, for sort

    def photo_list(self):
        # See _renderable_photos: strip the repo-relative "static/" prefix
        # so url_for('static', ...) does not double it, and never render a
        # photo whose managed asset is missing.
        return _renderable_photos(json.loads(self.photos or '[]'))

    def feature_dict(self):
        return json.loads(self.features or '{}')

    def price_breakdown_rows(self):
        return json.loads(self.price_breakdown or '[]')

    def price_history_rows(self):
        return json.loads(self.price_history or '[]')

    def history_json(self):
        return json.loads(self.history or 'null')

    def consumer_categories_json(self):
        return json.loads(self.consumer_categories or 'null')

    def consumer_reviews_rows(self):
        return json.loads(self.consumer_reviews or '[]')

    @property
    def title(self):
        bits = [self.stock_type.title() if self.stock_type != 'Certified' else 'Certified',
                str(self.year), self.make, self.model]
        t = " ".join(bits)
        if self.trim:
            t += f" {self.trim}"
        return t

    @property
    def monthly_popover(self):
        return {"down_payment": "$0", "net_trade_in": "$0",
                "months": str(self.monthly_months or 72),
                "apr": f"{self.monthly_apr or 7.0:.1f}%"}


class Dealer(db.Model):
    __tablename__ = 'dealers'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(160))
    city = db.Column(db.String(60))
    state = db.Column(db.String(4))
    zip = db.Column(db.String(10))
    phone_new = db.Column(db.String(20))
    phone_used = db.Column(db.String(20))
    phone_service = db.Column(db.String(20))
    rating = db.Column(db.Float)
    review_count = db.Column(db.Integer)
    hours = db.Column(db.Text)                     # JSON: day rows
    about = db.Column(db.Text)
    highlights = db.Column(db.Text)                # JSON: list
    reviews = db.Column(db.Text)                   # JSON: review rows
    sales_team = db.Column(db.Text)                # JSON: staff rows
    service_menu = db.Column(db.Text)              # JSON: list
    distance_miles = db.Column(db.Integer)
    makes_carried = db.Column(db.Text)             # JSON: list
    primary_make = db.Column(db.String(40))
    awards = db.Column(db.Integer)                 # "View N awards" on the dealer page

    def hours_list(self):
        return json.loads(self.hours or '[]')

    def review_list(self):
        return json.loads(self.reviews or '[]')

    def highlights_list(self):
        return json.loads(self.highlights or '[]')

    def sales_team_list(self):
        return json.loads(self.sales_team or '[]')

    def service_menu_list(self):
        return json.loads(self.service_menu or '[]')

    def makes_carried_list(self):
        return json.loads(self.makes_carried or '[]')


class ModelPage(db.Model):
    __tablename__ = 'model_pages'
    id = db.Column(db.Integer, primary_key=True)
    make = db.Column(db.String(40), nullable=False)
    make_slug = db.Column(db.String(40), nullable=False)
    model = db.Column(db.String(60), nullable=False)
    model_slug = db.Column(db.String(60), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    body_style = db.Column(db.String(30))
    safety_rating = db.Column(db.Integer)
    safety_review_count = db.Column(db.Integer)
    starting_price = db.Column(db.Integer)
    trims = db.Column(db.Text)                    # JSON: trim rows
    notable_features = db.Column(db.Text)         # JSON
    good_points = db.Column(db.Text)               # JSON
    bad_points = db.Column(db.Text)                # JSON
    expert_take = db.Column(db.Text)
    expert_author = db.Column(db.String(60))
    consumer_recommend_pct = db.Column(db.Integer)
    consumer_rating = db.Column(db.Float)
    consumer_review_count = db.Column(db.Integer)
    consumer_categories = db.Column(db.Text)
    consumer_reviews = db.Column(db.Text)         # JSON: review rows
    photos = db.Column(db.Text)                    # JSON: local image paths

    def trim_list(self):
        return json.loads(self.trims or '[]')

    def review_list(self):
        return json.loads(self.consumer_reviews or '[]')

    def photo_list(self):
        # See Listing.photo_list / _renderable_photos.
        return _renderable_photos(json.loads(self.photos or '[]'))

    def notable_features_list(self):
        return json.loads(self.notable_features or '[]')

    def good_points_list(self):
        return json.loads(self.good_points or '[]')

    def bad_points_list(self):
        return json.loads(self.bad_points or '[]')

    def consumer_categories_json(self):
        return json.loads(self.consumer_categories or 'null')


class ComparePair(db.Model):
    __tablename__ = 'compare_pairs'
    id = db.Column(db.Integer, primary_key=True)
    slug_a = db.Column(db.String(80), nullable=False)
    slug_b = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False)
    spec_rows = db.Column(db.Text)                # JSON: {label: [a, b]}
    columns = db.Column(db.Text)                  # JSON: captured compare columns

    def columns_list(self):
        return json.loads(self.columns or '[]')


class ValuationVehicle(db.Model):
    """One vehicle in the Instant Cash Offer wizard taxonomy (captured upstream)."""
    __tablename__ = 'valuation_vehicles'
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    make = db.Column(db.String(40), nullable=False)
    model = db.Column(db.String(60), nullable=False)
    trim = db.Column(db.String(120), nullable=False)
    key = db.Column(db.String(160), unique=True, nullable=False)  # year|make|model|trim
    options = db.Column(db.Text)                   # JSON: value-impacting options
    standard_features = db.Column(db.Text)         # JSON: list
    exterior_color = db.Column(db.String(40))      # captured flow color
    initial_low = db.Column(db.Integer, nullable=False)
    initial_high = db.Column(db.Integer, nullable=False)
    est_low = db.Column(db.Integer, nullable=False)
    est_high = db.Column(db.Integer, nullable=False)
    est_mileage = db.Column(db.Integer, nullable=False)

    def options_list(self):
        return json.loads(self.options or '[]')

    def standard_features_list(self):
        value = json.loads(self.standard_features or '[]')
        return [value] if isinstance(value, str) else value


class SavedCar(db.Model):
    __tablename__ = 'saved_cars'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    listing_id = db.Column(db.String(36), nullable=False)
    saved_at = db.Column(db.String(10))


class SavedSearch(db.Model):
    __tablename__ = 'saved_searches'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    query_string = db.Column(db.String(500), nullable=False)
    alert_frequency = db.Column(db.String(20), default='daily')
    created_at = db.Column(db.String(10))


class OfferRequest(db.Model):
    """An Instant Cash Offer submitted through the mirror wizard."""
    __tablename__ = 'offer_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    vehicle_key = db.Column(db.String(160), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    make = db.Column(db.String(40), nullable=False)
    model = db.Column(db.String(60), nullable=False)
    trim = db.Column(db.String(120), nullable=False)
    mileage = db.Column(db.Integer, nullable=False)
    zip = db.Column(db.String(10), nullable=False)
    exterior_color = db.Column(db.String(40))
    keys_count = db.Column(db.String(4))
    original_owner = db.Column(db.String(4))
    payments_remaining = db.Column(db.String(4))
    offer_low = db.Column(db.Integer, nullable=False)
    offer_high = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.String(10), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ------------------------------------------------------------------ jinja env --

@app.template_filter('money')
def money(value):
    if value is None:
        return "Not Priced"
    return f"${value:,.0f}"


@app.template_filter('mileagefmt')
def mileagefmt(value):
    return f"{value:,.0f}" if value is not None else "—"


def listing_sort_key(sort):
    return {
        'best_match_desc': (Listing.make, Listing.model),
        'list_price_asc': (Listing.price.asc(), Listing.mileage.asc()),
        'list_price_desc': (Listing.price.desc(), Listing.mileage.asc()),
        'mileage_low': (Listing.mileage.asc(), Listing.price.asc()),
        'mileage_high': (Listing.mileage.desc(), Listing.price.asc()),
        'distance_asc': (Listing.distance_miles.asc(), Listing.price.asc()),
        'deal_rating': (Listing.deal_badge, Listing.price.asc()),
        'year_desc': (Listing.year.desc(), Listing.price.asc()),
        'year_asc': (Listing.year.asc(), Listing.price.asc()),
        'newest_listed': (Listing.listed_at.desc(), Listing.price.asc()),
        'oldest_listed': (Listing.listed_at.asc(), Listing.price.asc()),
    }.get(sort, (Listing.price.asc(), Listing.mileage.asc()))


def _listing_filters(args):
    """Translate the upstream SERP query params into SQLAlchemy filters."""
    q = []
    stock = args.get('stock_type', 'all')
    if stock == 'new':
        q.append(Listing.stock_type == 'New')
    elif stock == 'used':
        q.append(Listing.stock_type == 'Used')
    elif stock == 'cpo':
        q.append(Listing.stock_type == 'Certified')
    elif stock == 'new_cpo':
        q.append(Listing.stock_type.in_(['New', 'Certified']))
    # a real browser submits every form control, including untouched selects
    # carrying their empty "All ..." value - empty values never filter
    for make in args.getlist('makes[]') or args.getlist('makes'):
        if make:
            q.append(Listing.make_slug == make)
    for model in args.getlist('models[]') or args.getlist('models'):
        if model:
            q.append(Listing.model_slug == model)
    for trims in args.getlist('trims[]') or args.getlist('trims'):
        if trims:
            q.append(Listing.trim == trims)
    for key, column, operator in [
        ('list_price_min', Listing.price, 'min'), ('list_price_max', Listing.price, 'max'),
        ('mileage_max', Listing.mileage, 'max'), ('year_min', Listing.year, 'min'),
        ('year_max', Listing.year, 'max'), ('maximum_distance', Listing.distance_miles, 'max')]:
        if args.get(key):
            try:
                value = int(args[key])
                if not 0 <= value <= 100000000:
                    raise ValueError()
            except ValueError:
                abort(400, description='Invalid numeric search filter.')
            q.append(column >= value if operator == 'min' else column <= value)
    for bs in args.getlist('body_style_slugs[]') or args.getlist('body_style_slugs'):
        if bs:
            q.append(Listing.body_style_slug == bs)
    for c in args.getlist('exterior_color_slugs[]') or args.getlist('exterior_color_slugs'):
        if c:
            q.append(Listing.exterior_color_slug == c)
    for f in args.getlist('fuel_slugs[]') or args.getlist('fuel_slugs'):
        if f:
            q.append(Listing.fuel_slug == f)
    for t in args.getlist('transmission_slugs[]') or args.getlist('transmission_slugs'):
        if t:
            q.append(Listing.transmission_slug == t)
    for d in args.getlist('drivetrain_slugs[]') or args.getlist('drivetrain_slugs'):
        if d:
            q.append(Listing.drivetrain_slug == d)
    for cy in args.getlist('cylinder_counts[]') or args.getlist('cylinder_counts'):
        try:
            q.append(Listing.cylinders == int(cy))
        except ValueError:
            pass
    for dr in args.getlist('deal_ratings[]') or args.getlist('deal_ratings'):
        badge = {'great': 'Great Deal', 'good': 'Good Deal', 'fair': 'Fair Deal'}.get(dr)
        if badge:
            q.append(Listing.deal_badge == badge)
    if args.get('seller_type'):
        q.append(Listing.seller_type == args['seller_type'])
    if args.get('only_with_photos') in ('1', 'true'):
        q.append(Listing.total_photos > 0)
    for feat in args.getlist('features[]'):
        group = FEATURE_GROUPS.get(feat)
        if group:
            q.append(Listing.features.like(f'%"{feat}"%'))
    keyword = (args.get('keyword') or '').strip()
    if keyword:
        like = f"%{keyword.lower()}%"
        from sqlalchemy import or_
        q.append(or_(db.func.lower(Listing.model).like(like),
                     db.func.lower(Listing.make).like(like),
                     db.func.lower(Listing.seller_notes).like(like),
                     db.func.lower(Listing.trim).like(like)))
    return q


def _search_title(args):
    bits = []
    stock = STOCK_LABELS.get(args.get('stock_type', 'all'), '')
    models = args.getlist('models[]') or args.getlist('models')
    makes = args.getlist('makes[]') or args.getlist('makes')
    if models:
        bits.append(models[0].replace('_', ' ').title())
    elif makes:
        bits.append(makes[0].replace('_', ' ').title())
    head = " ".join([b for b in [bits[0]] if b] + ["Cars"]) if bits else \
        {"new": "New Cars", "used": "Used Cars", "cpo": "Certified Cars",
         "new_cpo": "New & Certified Cars", "all": "Cars"}.get(args.get('stock_type', 'all'), "Cars")
    return f"{head} for Sale Near {DEFAULT_CITY}"


@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


@app.context_processor
def inject_globals():
    return {'MIRROR_TS': MIRROR_TS, 'DEFAULT_ZIP': DEFAULT_ZIP,
            'DEFAULT_CITY': DEFAULT_CITY, 'UPSTREAM': UPSTREAM}


# --------------------------------------------------------------------- routes --

@app.route('/_health')
def health():
    return jsonify(ok=True,
                    listings=Listing.query.count(),
                    details=Listing.query.filter_by(has_detail=True).count(),
                    dealers=Dealer.query.count(),
                    models=ModelPage.query.count(),
                    compares=ComparePair.query.count(),
                    valuations=ValuationVehicle.query.count(),
                    users=User.query.count(),
                    saved_cars=SavedCar.query.count())


@app.route('/')
def home():
    makes = sorted({(m.make_slug, m.make) for m in Listing.query.distinct(Listing.make_slug, Listing.make)})
    models = sorted({(m.model_slug, f"{m.make} {m.model}")
                     for m in Listing.query.filter(Listing.stock_type != 'Used')
                     .distinct(Listing.model_slug, Listing.make, Listing.model)})
    counts = {
        'used': Listing.query.filter_by(stock_type='Used').count(),
        'new': Listing.query.filter_by(stock_type='New').count(),
        'cpo': Listing.query.filter_by(stock_type='Certified').count(),
    }
    style_counts = {bs: Listing.query.filter_by(body_style_slug=bs).count() for bs in ('suv', 'truck', 'sedan')}
    return render_template('home.html', makes=makes, models=models, counts=counts,
                           style_counts=style_counts, zip=DEFAULT_ZIP, city=DEFAULT_CITY)


@app.route('/shopping/results/')
def shopping_results():
    args = request.args
    filters = _listing_filters(args)
    query = Listing.query.filter(*filters)
    total = query.count()
    sort = args.get('sort', 'best_match_desc')
    order = (*listing_sort_key(sort), Listing.id.asc())
    try:
        page = min(100000, max(1, int(args.get('page', 1))))
    except ValueError:
        page = 1
    pagination = query.order_by(*order).paginate(page=page, per_page=PER_PAGE,
                                                  error_out=False)
    return render_template(
        'srp.html', pagination=pagination, total=total,
        args=args, sort=sort, sorts=SORTS, zip=DEFAULT_ZIP,
        stock_labels=STOCK_LABELS, body_labels=BODY_LABELS,
        fuel_labels=FUEL_LABELS, transmission_labels=TRANSMISSION_LABELS,
        drivetrain_labels=DRIVETRAIN_LABELS, colors=COLORS, cylinders=CYLINDERS,
        deal_ratings=DEAL_RATINGS, distances=DISTANCES,
        search_title=_search_title(args),
        makes=sorted({(m.make_slug, m.make) for m in Listing.query.distinct(Listing.make_slug, Listing.make)}),
        models=sorted({(m.model_slug, m.model) for m in Listing.query.distinct(Listing.model_slug, Listing.model)}),
    )


@app.route('/shopping/new/')
def shopping_new():
    return render_template('browse.html', preset='new', title='Shop All New Cars',
                           stock='new', zip=DEFAULT_ZIP, city=DEFAULT_CITY)


@app.route('/shopping/used/')
def shopping_used():
    return render_template('browse.html', preset='used', title='Shop All Used Cars',
                           stock='used', zip=DEFAULT_ZIP, city=DEFAULT_CITY)


@app.route('/shopping/certified-preowned/')
def shopping_cpo():
    return render_template('browse.html', preset='cpo', title='Certified Pre-Owned Cars for Sale',
                           stock='cpo', zip=DEFAULT_ZIP, city=DEFAULT_CITY)


@app.route('/shopping/for-sale-by-owner/')
def shopping_fso():
    return render_template('browse.html', preset='fso', title='Cars for Sale by Owner',
                           stock='used', zip=DEFAULT_ZIP, city=DEFAULT_CITY)


@app.route('/shopping/<style>/')
def shopping_style(style):
    if style not in BODY_STYLES and style not in ('electric', 'hybrid', 'cheap'):
        abort(404)
    titles = {**{b: f"{BODY_LABELS[b]}s for Sale" for b in BODY_STYLES},
              'electric': 'Electric Cars for Sale', 'hybrid': 'Hybrid Cars for Sale',
              'cheap': 'Cheap Cars for Sale'}
    return render_template('browse.html', preset=style, title=titles[style],
                           stock='used', zip=DEFAULT_ZIP, city=DEFAULT_CITY)


@app.route('/vehicledetail/<listing_id>/')
def vehicle_detail(listing_id):
    listing = Listing.query.filter_by(id=listing_id).first_or_404()
    dealer = Dealer.query.get(listing.dealer_id) if listing.dealer_id else None
    similar = Listing.query.filter(Listing.dealer_id == listing.dealer_id,
                                    Listing.id != listing.id)\
        .order_by(Listing.price.asc()).limit(8).all() if listing.dealer_id else []
    others = Listing.query.filter(Listing.model_slug == listing.model_slug,
                                  Listing.stock_type == listing.stock_type,
                                  Listing.id != listing.id)\
        .order_by(Listing.price.asc()).limit(8).all()
    return render_template('vd.html', l=listing, dealer=dealer, similar=similar,
                           others=others, open_lead_form=request.args.get('openLeadForm'))


@app.route('/dealers/')
def dealers_index():
    args = request.args
    q = []
    try:
        if args.get('maximum_distance'):
            q.append(Dealer.distance_miles <= int(args['maximum_distance']))
    except ValueError:
        pass
    make = args.get('make')
    if make:
        q.append(Dealer.makes_carried.like(f'%"{make}"%'))
    try:
        rating = float(args.get('rating') or 0)
    except ValueError:
        rating = 0
    if rating:
        q.append(Dealer.rating >= rating)
    query = Dealer.query.filter(*q)
    total = query.count()
    sort = args.get('sort', 'rating')
    order = {'rating': (Dealer.rating.desc(), Dealer.review_count.desc()),
             'name': (Dealer.name.asc(),),
             'distance': (Dealer.distance_miles.asc(), Dealer.name.asc())}.get(sort, (Dealer.rating.desc(), Dealer.review_count.desc()))
    try:
        page = min(100000, max(1, int(args.get('page', 1))))
    except ValueError:
        page = 1
    pagination = query.order_by(*order).paginate(page=page, per_page=20, error_out=False)
    return render_template('dealers.html', pagination=pagination, total=total,
                           args=args, sort=sort, zip=DEFAULT_ZIP, city=DEFAULT_CITY,
                           makes=sorted({(m.make_slug, m.make) for m in Listing.query.distinct(Listing.make_slug, Listing.make)}))


@app.route('/dealers/<int:dealer_id>/<slug>/')
def dealer_page(dealer_id, slug):
    dealer = Dealer.query.filter_by(id=dealer_id).first_or_404()
    inventory_count = Listing.query.filter_by(dealer_id=dealer.id).count()
    return render_template('dealer.html', d=dealer, inventory_count=inventory_count)


@app.route('/dealers/<int:dealer_id>/<slug>/reviews/')
def dealer_reviews(dealer_id, slug):
    dealer = Dealer.query.filter_by(id=dealer_id).first_or_404()
    return render_template('dealer_reviews.html', d=dealer)


@app.route('/dealers/<int:dealer_id>/<slug>/inventory/')
def dealer_inventory(dealer_id, slug):
    dealer = Dealer.query.filter_by(id=dealer_id).first_or_404()
    args = request.args
    q = [Listing.dealer_id == dealer.id]
    stock = args.get('stock_type')
    if stock in ('new', 'used', 'cpo'):
        target = {'new': 'New', 'used': 'Used', 'cpo': 'Certified'}[stock]
        q.append(Listing.stock_type == target)
    make = args.get('make')
    if make:
        q.append(Listing.make_slug == make)
    listings = Listing.query.filter(*q).order_by(Listing.price.asc()).all()
    return render_template('dealer_inventory.html', d=dealer, listings=listings, args=args)


@app.route('/research/')
def research_home():
    pages = ModelPage.query.order_by(ModelPage.make, ModelPage.model).all()
    pairs = ComparePair.query.all()
    return render_template('research.html', pages=pages, pairs=pairs)


@app.route('/research/<slug>/')
def research_page(slug):
    page = ModelPage.query.filter_by(slug=slug).first_or_404()
    listings = Listing.query.filter(Listing.model_slug == page.model_slug,
                                    Listing.stock_type != 'Used')\
        .order_by(Listing.price.asc()).limit(6).all()
    return render_template('model.html', p=page, listings=listings)


@app.route('/research/compare/')
def compare_home():
    pages = ModelPage.query.order_by(ModelPage.make, ModelPage.model).all()
    pairs = ComparePair.query.order_by(ComparePair.slug).all()
    return render_template('compare_home.html', pages=pages, pairs=pairs)


@app.route('/research/compare/<slug>/')
def compare_page(slug):
    pair = ComparePair.query.filter_by(slug=slug).first_or_404()
    a = ModelPage.query.filter_by(slug=pair.slug_a).first_or_404()
    b = ModelPage.query.filter_by(slug=pair.slug_b).first_or_404()
    rows = json.loads(pair.spec_rows or '{}')
    return render_template('compare.html', pair=pair, a=a, b=b, rows=rows,
                           cols=pair.columns_list())


# ----------------------------------------------------- instant cash offer flow --

@app.route('/sell/instant-offer/')
def offer_start():
    years = sorted({v.year for v in ValuationVehicle.query.all()}, reverse=True)
    makes = sorted({v.make for v in ValuationVehicle.query.all()})
    return render_template('offer_start.html', years=years, makes=makes,
                           zip=DEFAULT_ZIP)


@app.route('/sell/instant-offer/api/models')
def offer_api_models():
    make = request.args.get('make', '')
    rows = ValuationVehicle.query.filter_by(make=make).all()
    return jsonify(sorted({r.model for r in rows}))


@app.route('/sell/instant-offer/api/trims')
def offer_api_trims():
    make = request.args.get('make', '')
    model = request.args.get('model', '')
    year = request.args.get('year', '')
    q = [ValuationVehicle.make == make, ValuationVehicle.model == model]
    if year.isdigit():
        q.append(ValuationVehicle.year == int(year))
    rows = ValuationVehicle.query.filter(*q).all()
    return jsonify(sorted({r.trim for r in rows}))


@app.route('/sell/instant-offer/vehicle/', methods=['POST'])
def offer_vehicle():
    """Step 1: pick the vehicle. Server keeps the wizard state in the session."""
    year = request.form.get('year', '')
    make = request.form.get('make', '')
    model = request.form.get('model', '')
    trim = request.form.get('trim', '')
    row = ValuationVehicle.query.filter_by(year=int(year) if year.isdigit() and len(year) == 4 else 0, make=make,
                                           model=model, trim=trim).first()
    if not row:
        years = sorted({v.year for v in ValuationVehicle.query.all()}, reverse=True)
        makes = sorted({v.make for v in ValuationVehicle.query.all()})
        return render_template('offer_start.html', years=years, makes=makes,
                               error="Pick a year, make, model and trim from the lists.",
                               zip=DEFAULT_ZIP), 400
    session.pop('offer_result', None)
    session.pop('offer_request_id', None)
    session['offer_vehicle'] = row.key
    session['offer_initial'] = [row.initial_low, row.initial_high]
    return redirect(url_for('offer_details'))


@app.route('/sell/instant-offer/details/', methods=['GET', 'POST'])
def offer_details():
    key = session.get('offer_vehicle')
    if not key:
        return redirect(url_for('offer_start'))
    row = ValuationVehicle.query.filter_by(key=key).first_or_404()
    if request.method == 'POST':
        mileage = request.form.get('mileage', '')
        zipc = request.form.get('zip', '')
        color = request.form.get('exterior_color', '')
        keys_count = request.form.get('keys', '')
        original = request.form.get('original_owner', '')
        payments = request.form.get('payments', '') or 'No'
        valid_colors = {v.exterior_color for v in ValuationVehicle.query.all()}
        if not (mileage.isdigit() and len(mileage) <= 7 and int(mileage) <= 1000000 and re.fullmatch(r'\d{5}', zipc) and color in valid_colors and keys_count in ['0', '1', '2', '3+'] and original in ['Yes', 'No'] and payments in ['Yes', 'No']):
            return render_template('offer_details.html', v=row,
                                   error="Enter a valid mileage, five-digit ZIP, color, key count and ownership details.",
                                   colors=sorted({c for c in
                                                  [r.exterior_color for r in
                                                   ValuationVehicle.query.all()] if c})), 400
        # Deterministic adjustment: the captured upstream wizard moved the
        # estimate by a fixed offset when the owner details were entered.
        try:
            mileage = int(mileage)
        except ValueError:
            mileage = row.est_mileage
        delta_low = row.est_low - row.initial_low
        adj = (row.est_mileage - mileage) // 25
        offer_low = max(0, row.initial_low + delta_low + adj)
        offer_high = offer_low + (row.initial_high - row.initial_low)
        session['offer_result'] = {
            'vehicle': f"{row.year} {row.make} {row.model} {row.trim}".strip(),
            'vehicle_key': row.key, 'mileage': mileage, 'zip': zipc,
            'color': color, 'keys': keys_count, 'original_owner': original,
            'payments': payments,
            'initial_low': row.initial_low, 'initial_high': row.initial_high,
            'offer_low': offer_low, 'offer_high': offer_high,
        }
        if current_user.is_authenticated:
            saved_request = OfferRequest(user_id=current_user.id,
                                         vehicle_key=row.key, year=row.year,
                                         make=row.make, model=row.model, trim=row.trim,
                                         mileage=session['offer_result']['mileage'], zip=session['offer_result']['zip'],
                                         exterior_color=session['offer_result']['color'],
                                         keys_count=session['offer_result']['keys'],
                                         original_owner=session['offer_result']['original_owner'],
                                         payments_remaining=session['offer_result']['payments'],
                                         offer_low=session['offer_result']['offer_low'],
                                         offer_high=session['offer_result']['offer_high'],
                                         created_at=MIRROR_TS)
            db.session.add(saved_request)
            db.session.commit()
            session['offer_request_id'] = saved_request.id
        return redirect(url_for('offer_result'))
    colors = sorted({c for c in [r.exterior_color for r in ValuationVehicle.query.all()] if c})
    return render_template('offer_details.html', v=row, colors=colors)


@app.route('/sell/instant-offer/offer/')
def offer_result():
    result = session.get('offer_result')
    if not result:
        return redirect(url_for('offer_start'))
    row = ValuationVehicle.query.filter_by(key=result['vehicle_key']).first_or_404()
    saved_request = db.session.get(OfferRequest, session.get('offer_request_id')) if current_user.is_authenticated and session.get('offer_request_id') else None
    if saved_request and saved_request.user_id != current_user.id:
        saved_request = None
    return render_template('offer_result.html', r=result, v=row, saved=saved_request)


# ------------------------------------------------------- payment calculator --

@app.route('/car-loan-calculator/', methods=['GET', 'POST'])
def loan_calculator():
    result = None
    form = {}
    error = None
    if request.method == 'POST':
        form = {k: request.form.get(k, '').strip() for k in
                ('vehicle_price', 'credit_rating', 'custom_apr', 'zip',
                 'down_payment', 'trade_in', 'cash_incentives', 'fees', 'term')}
        try:
            price = float(form['vehicle_price'] or 0)
            down = float(form['down_payment'] or 0)
            trade = float(form['trade_in'] or 0)
            incentives = float(form['cash_incentives'] or 0)
            fees = float(form['fees'] or 0)
            term = int(form['term'] or 72)
            apr = float(form['custom_apr']) if form['custom_apr'] else CREDIT_APRS.get(form['credit_rating'] or 'good', 7.0)
            if not all(math.isfinite(v) and 0 <= v <= 100000000 for v in [price, down, trade, incentives, fees]) or not math.isfinite(apr) or not 0 <= apr <= 20 or term not in LOAN_TERMS:
                raise ValueError('Invalid loan inputs')
            tax_rate = 10.25
            taxable = max(0.0, price - trade)
            sales_tax = taxable * tax_rate / 100.0
            principal = max(0.0, price + fees + sales_tax - down - trade - incentives)
            monthly_rate = apr / 100.0 / 12.0
            n = term
            if monthly_rate > 0:
                monthly = principal * monthly_rate / (1 - (1 + monthly_rate) ** (-n))
            else:
                monthly = principal / n
            total_paid = monthly * n
            result = {
                'monthly': round(monthly), 'sales_tax': round(sales_tax),
                'principal': round(principal), 'total_interest': round(total_paid - principal),
                'total_paid': round(total_paid), 'apr': apr, 'term': term,
            }
        except (ValueError, OverflowError):
            error = 'Enter nonnegative finite amounts, an APR from 0 to 20, and an available loan term.'
    return render_template('calculator.html', form=form, result=result,
                           credit_ratings=CREDIT_RATINGS, terms=LOAN_TERMS,
                           zip=DEFAULT_ZIP, error=error), (400 if error else 200)


# ------------------------------------------------------------------- accounts --

@app.route('/authn/login', methods=['GET', 'POST'])
def authn_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            target = request.args.get('next_url') or url_for('garage')
            return redirect(safe_next(target, url_for('garage')))
        return render_template('login.html', error="Invalid email or password.",
                               email=email), 401
    return render_template('login.html')


@app.route('/authn/register', methods=['GET', 'POST'])
def authn_register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '')
        if not email or not password or len(password) < 8:
            return render_template('register.html',
                                   error="Enter an email, name and a password of at least 8 characters."), 400
        if User.query.filter_by(email=email).first():
            return render_template('register.html',
                                   error="An account with that email already exists.",
                                   email=email), 400
        user = User(email=email, display_name=name or email.split('@')[0],
                    password_hash=bcrypt.generate_password_hash(password).decode())
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('garage'))
    return render_template('register.html')


@app.route('/authn/logout', methods=['POST'])
@login_required
def authn_logout():
    logout_user()
    for key in ['offer_vehicle', 'offer_initial', 'offer_result', 'offer_request_id']:
        session.pop(key, None)
    return redirect(url_for('home'))


@app.route('/profile/your-garage/')
@login_required
def garage():
    saved = db.session.query(SavedCar, Listing).join(Listing,
                                                     SavedCar.listing_id == Listing.id)\
        .filter(SavedCar.user_id == current_user.id)\
        .order_by(SavedCar.id.desc()).all()
    searches = SavedSearch.query.filter_by(user_id=current_user.id).all()
    offers = OfferRequest.query.filter_by(user_id=current_user.id).all()
    return render_template('garage.html', saved=saved, searches=searches, offers=offers)


@app.route('/save/<listing_id>/', methods=['POST'])
def save_car(listing_id):
    listing = Listing.query.filter_by(id=listing_id).first_or_404()
    if not current_user.is_authenticated:
        return redirect(url_for('authn_login', next_url=url_for('vehicle_detail', listing_id=listing_id)))
    existing = SavedCar.query.filter_by(user_id=current_user.id, listing_id=listing_id).first()
    if existing:
        db.session.delete(existing)
    else:
        db.session.add(SavedCar(user_id=current_user.id, listing_id=listing_id,
                                saved_at=MIRROR_TS))
    db.session.commit()
    return redirect(safe_next(request.form.get('next'), url_for('vehicle_detail', listing_id=listing_id)))


@app.route('/searches/save/', methods=['POST'])
@login_required
def save_search():
    query_string = request.form.get('query_string', '')
    name = request.form.get('name', '').strip() or "Search"
    freq = request.form.get('alert_frequency', 'daily')
    if freq not in ['daily', 'weekly', 'monthly', 'off']:
        abort(400)
    if not query_string.startswith('/shopping/results/'):
        query_string = '/shopping/results/' + query_string
    db.session.add(SavedSearch(user_id=current_user.id, name=name,
                               query_string=query_string, alert_frequency=freq,
                               created_at=MIRROR_TS))
    db.session.commit()
    return redirect(url_for('garage'))


# -------------------------------------------------------------------- seeds --

def seed_database():
    if Listing.query.count() > 0:
        return
    from seed_lib import seed_all
    seed_all(db, bcrypt, app)


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
    if os.environ.get('CARS_COM_AUTO_SEED', '1') == '1':
        seed_database()
        seed_benchmark_users()


if __name__ == '__main__':
    main()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 40136)))
