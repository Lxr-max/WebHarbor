#!/usr/bin/env python3
"""airbnb — a WebHarbor mirror of https://www.airbnb.com/

Flask + SQLite mirror of Airbnb's short-term-rental vertical: the home
search, the Stays SERP with the upstream filter taxonomy (price range
with the captured histogram, type of place, rooms and beds, standout
stays, booking options, amenities, property types), listing detail pages
with the full captured descriptions/amenities/host blocks/house
rules/sleeping arrangements, the 365-day availability calendars, the
review pages with the captured review-tag taxonomy, the request-to-book
flow with per-night price breakdowns, wishlists, and the Experiences
vertical (category search, detail pages with the captured agenda,
guest requirements and accessibility facts, and booking) seeded for
four benchmark users.

Content comes from the tracked source_data/*.json snapshots captured
from airbnb.com on 2026-09-30 (see provenance.json); the SQLite seed is
materialized deterministically at image build time (PYTHONHASHSEED=0).
"""
import json
import math
from urllib.parse import urlsplit
import os
import secrets
from datetime import date, timedelta

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
app.config["SECRET_KEY"] = os.environ.get("AIRBNB_SECRET_KEY") or "webharbor-airbnb-dev-key"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'AIRBNB_DB_URI', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'airbnb.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to continue.'
csrf = CSRFProtect(app)

# The mirror is a frozen snapshot of the upstream site taken 2026-09-30.
MIRROR_DATE = date(2026, 9, 30)
MIRROR_TS = "2026-09-30"
SITE_NAME = "airbnb"
UPSTREAM = "https://www.airbnb.com/"
# bcrypt hash of 'TestPass123!' — frozen so the seed DB is byte-reproducible.
BENCHMARK_PASSWORD_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')
SOURCE = os.path.join(BASE_DIR, 'source_data')


def _load(name):
    with open(os.path.join(SOURCE, name), encoding='utf-8') as f:
        return json.load(f)


def localized_text(value):
    """Unpack upstream localized wrapper payloads to their human text.

    The captured airbnb JSON wraps several human-readable strings in
    localization envelopes, e.g. experience agenda stop titles as
    {'__typename': 'ListingDescription', 'localizedValue':
    {'localizedString': ...}}, listing highlight bodies as
    {'__typename': 'LocalizedContent', 'localizedContent': ...}, and
    house-rules/safety item descriptions as {'__typename': 'PdpUGCText',
    'content': {...}} or {'__typename': 'LocalizedText', 'text': ...}.
    Rendering the envelopes verbatim leaks Python dict repr into the
    page (review r2 finding: B4 residual on 69/80 experience PDPs and
    the ``None — {…}`` highlights on 96/96 listing PDPs), so every
    localized field is unpacked to its inner text at render time.
    Unknown shapes render as None — never as a repr."""
    if isinstance(value, str) or value is None:
        return value
    if isinstance(value, dict):
        for key in ('localizedContent', 'localizedString', 'text'):
            inner = value.get(key)
            if isinstance(inner, str):
                return inner
        for key in ('localizedValue', 'content'):
            nested = value.get(key)
            if nested is not None:
                inner = localized_text(nested)
                if inner is not None:
                    return inner
    return None


def unpack_rule_groups(payload):
    """House-rules/safety payloads: unpack each group item's description
    envelope (PdpUGCText / LocalizedText) to its text — never a repr."""
    groups = []
    for g in (payload.get('groups') or []):
        items = []
        for i in (g.get('items') or []):
            item = {'title': i.get('title')}
            desc = localized_text(i.get('description'))
            if desc:
                item['description'] = desc
            items.append(item)
        groups.append({'title': g.get('title'), 'items': items})
    out = dict(payload)
    out['groups'] = groups
    return out


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
                    _INVENTORY[row['path']] = row
    return _INVENTORY


def asset_exists(path):
    return path in _inventory()


# ------------------------------------------------------------------- models --

class Destination(db.Model):
    __tablename__ = 'destinations'
    slug = db.Column(db.String(64), primary_key=True)
    label = db.Column(db.String(128), nullable=False)
    city = db.Column(db.String(64), nullable=False)
    region = db.Column(db.String(64), nullable=False)
    seo_title = db.Column(db.Text)
    seo_subtitle = db.Column(db.Text)
    filter_panel = db.Column(db.Text)      # captured upstream facet panel
    serp_total = db.Column(db.Integer)     # upstream result count (context)


class Listing(db.Model):
    __tablename__ = 'listings'
    id = db.Column(db.String(32), primary_key=True)
    destination_slug = db.Column(db.String(64), db.ForeignKey('destinations.slug'),
                                 nullable=False, index=True)
    name = db.Column(db.Text, nullable=False)
    title = db.Column(db.Text)
    property_type = db.Column(db.String(32))
    room_category = db.Column(db.String(32))     # entire/private/shared
    city = db.Column(db.String(128))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    rating = db.Column(db.Float)
    reviews_count = db.Column(db.Integer, default=0)
    is_new = db.Column(db.Boolean, default=False)
    is_superhost = db.Column(db.Boolean, default=False)
    is_guest_favorite = db.Column(db.Boolean, default=False)
    instant_book = db.Column(db.Boolean, default=False)
    pets_allowed = db.Column(db.Boolean, default=False)
    max_guest_capacity = db.Column(db.Integer)
    free_cancellation = db.Column(db.Boolean, default=False)
    subtitle = db.Column(db.Text)
    person_capacity = db.Column(db.Integer)
    bedrooms = db.Column(db.Integer)
    beds = db.Column(db.Integer)
    baths = db.Column(db.Float)
    bed_lines = db.Column(db.Text)        # captured "1 king bed" style lines
    nightly_price = db.Column(db.Float)   # captured nightly rate (USD)
    quote_total = db.Column(db.Float)     # captured trip price for the default window
    quote_nights = db.Column(db.Integer)
    quote_checkin = db.Column(db.String(10))
    quote_checkout = db.Column(db.String(10))
    range2_total = db.Column(db.Float)
    range2_nights = db.Column(db.Integer)
    description_html = db.Column(db.Text)
    address_locality = db.Column(db.String(128))
    amenity_count = db.Column(db.Integer, default=0)
    photos = db.Column(db.Text)           # JSON: [{uri, alt, caption}]
    amenities = db.Column(db.Text)        # JSON: [{title, items[]}]
    amenity_flags = db.Column(db.Text)    # JSON: {normalized_name: true}
    highlights = db.Column(db.Text)       # JSON: [{title, body}]
    house_rules = db.Column(db.Text)      # JSON
    safety = db.Column(db.Text)           # JSON
    sleeping = db.Column(db.Text)         # JSON
    things_to_know = db.Column(db.Text)   # JSON
    quality = db.Column(db.Text)          # JSON (category ratings, percentile)
    similar = db.Column(db.Text)          # JSON (upstream carousel)
    explore = db.Column(db.Text)          # JSON: nearby-city links
    calendar = db.Column(db.Text)         # JSON: {date: available}
    host_name = db.Column(db.String(128))
    host_superhost = db.Column(db.Boolean, default=False)
    host_years = db.Column(db.String(64))
    host_avatar = db.Column(db.String(255))
    serp_position = db.Column(db.Integer)   # upstream SERP order

    def photo_list(self):
        return json.loads(self.photos or '[]')

    def bed_line_list(self):
        """Render-ready bed lines. The stored column is a JSON array of
        captured '1 king bed' style lines; render the unpacked lines, never
        the raw JSON text (audit finding on the r3 tree: every listing PDP
        showed the stored [\"...\"] string verbatim)."""
        try:
            data = json.loads(self.bed_lines or '[]')
        except (TypeError, ValueError):
            return []
        if isinstance(data, list):
            return [str(x) for x in data if x]
        return [str(data)] if data else []

    def amenity_groups(self):
        return json.loads(self.amenities or '[]')

    def amenity_flag_set(self):
        return set(json.loads(self.amenity_flags or '{}').keys())

    def calendar_map(self):
        return json.loads(self.calendar or '{}')


class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.String(32), db.ForeignKey('listings.id'),
                           nullable=False, index=True)
    upstream_id = db.Column(db.String(64))
    reviewer = db.Column(db.String(128))
    reviewer_location = db.Column(db.String(128))
    rating = db.Column(db.Integer)
    text = db.Column(db.Text)
    localized_date = db.Column(db.String(64))
    created_at = db.Column(db.String(10))
    host_response = db.Column(db.Text)


class ReviewTag(db.Model):
    __tablename__ = 'review_tags'
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.String(32), db.ForeignKey('listings.id'),
                           nullable=False, index=True)
    name = db.Column(db.String(64))
    count = db.Column(db.Integer)


class Experience(db.Model):
    __tablename__ = 'experiences'
    id = db.Column(db.String(16), primary_key=True)
    city_slug = db.Column(db.String(64), db.ForeignKey('destinations.slug'),
                          nullable=False, index=True)
    name = db.Column(db.Text, nullable=False)
    byline = db.Column(db.Text)
    theme = db.Column(db.String(64))
    rating = db.Column(db.Float)
    rating_count = db.Column(db.Integer, default=0)
    price_per_guest = db.Column(db.Float)
    badges = db.Column(db.Text)            # JSON list of texts
    photos = db.Column(db.Text)            # JSON list of urls
    description = db.Column(db.Text)
    host_name = db.Column(db.String(128))
    highlights = db.Column(db.Text)        # JSON
    things_to_know = db.Column(db.Text)    # JSON
    accessibility = db.Column(db.Text)     # JSON list
    guest_requirements = db.Column(db.Text)  # JSON
    agenda = db.Column(db.Text)            # JSON [{title, body, image}]
    whats_you_doing = db.Column(db.Text)   # JSON list of paragraphs
    meeting_text = db.Column(db.Text)      # JSON list of paragraphs
    reviews = db.Column(db.Text)          # JSON [{rating, comments, ...}]
    offerings = db.Column(db.Text)        # JSON [{start, end, price}]
    location_city = db.Column(db.String(128))

    def photo_list(self):
        return json.loads(self.photos or '[]')

    def badge_list(self):
        """Flatten the captured badge payload ([['Original'], ...]) to texts."""
        out = []
        for b in json.loads(self.badges or '[]'):
            if isinstance(b, (list, tuple)):
                out.extend(str(x) for x in b if x)
            elif b:
                out.append(str(b))
        return out

    def highlight_list(self):
        """Captured highlights with the upstream localized/null names
        unpacked — RECOGNITION rows carry a null name and only text, so
        render the text alone, never a 'None' placeholder."""
        out = []
        for h in json.loads(self.highlights or '[]'):
            entry = {'name': localized_text(h.get('name')),
                     'text': localized_text(h.get('text'))}
            if entry['name'] or entry['text']:
                out.append(entry)
        return out

    def things_list(self):
        return json.loads(self.things_to_know or '[]')

    def accessibility_list(self):
        return json.loads(self.accessibility or '[]')

    def requirements(self):
        """Captured guest_requirements dict (min_age, children_allowed,
        infants_allowed) — parsed, never rendered as a JSON string."""
        return json.loads(self.guest_requirements or '{}')

    def doing_list(self):
        return json.loads(self.whats_you_doing or '[]')

    def meeting_list(self):
        return json.loads(self.meeting_text or '[]')

    def agenda_list(self):
        """Captured agenda stops, with the upstream localized stop titles
        unpacked to their text (never a dict repr)."""
        stops = []
        for a in json.loads(self.agenda or '[]'):
            stops.append({
                'title': localized_text(a.get('title')),
                'body': localized_text(a.get('body')),
                'image': a.get('image'),
            })
        return stops

    def review_list(self):
        return json.loads(self.reviews or '[]')

    def offering_list(self):
        return json.loads(self.offerings or '[]')


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    joined = db.Column(db.String(10), nullable=False, default=MIRROR_TS)


class Wishlist(db.Model):
    __tablename__ = 'wishlists'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False,
                        index=True)
    name = db.Column(db.String(128), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.String(10), nullable=False, default=MIRROR_TS)


class WishlistItem(db.Model):
    __tablename__ = 'wishlist_items'
    id = db.Column(db.Integer, primary_key=True)
    wishlist_id = db.Column(db.Integer, db.ForeignKey('wishlists.id'),
                            nullable=False, index=True)
    listing_id = db.Column(db.String(32), db.ForeignKey('listings.id'))
    experience_id = db.Column(db.String(16), db.ForeignKey('experiences.id'))
    added_at = db.Column(db.String(10), nullable=False, default=MIRROR_TS)


class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(12), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False,
                        index=True)
    kind = db.Column(db.String(16), nullable=False)   # 'stay' or 'experience'
    listing_id = db.Column(db.String(32), db.ForeignKey('listings.id'))
    experience_id = db.Column(db.String(16), db.ForeignKey('experiences.id'))
    experience_date = db.Column(db.String(10))
    checkin = db.Column(db.String(10))
    checkout = db.Column(db.String(10))
    adults = db.Column(db.Integer, default=1)
    children = db.Column(db.Integer, default=0)
    infants = db.Column(db.Integer, default=0)
    pets = db.Column(db.Integer, default=0)
    guests = db.Column(db.Integer, default=1)
    nights = db.Column(db.Integer)
    nightly_price = db.Column(db.Float)
    subtotal = db.Column(db.Float)
    total = db.Column(db.Float)
    status = db.Column(db.String(16), nullable=False, default='confirmed')
    created_at = db.Column(db.String(10), nullable=False, default=MIRROR_TS)


@login_manager.user_loader
def load_user(uid):
    return db.session.get(User, int(uid))


# ------------------------------------------------------------ search config --

# The upstream SERP filter taxonomy, frozen exactly as the filter panel
# renders it (captured 2026-09-30, destinations.json filter_panel).
ROOM_CATEGORIES = ['entire', 'private', 'shared']
ROOM_LABELS = {'entire': 'Entire home', 'private': 'Private room',
               'shared': 'Shared room'}
PROPERTY_TYPES = ['House', 'Apartment', 'Guesthouse', 'Hotel',
                  'Cabin', 'Home', 'Condo', 'Townhouse', 'Villa',
                  'Loft', 'Cottage', 'Farm stay', 'Bungalow', 'Boutique hotel']
AMENITY_FILTERS = [
    'Wifi', 'Kitchen', 'Free parking', 'Air conditioning', 'Heating',
    'TV', 'Washer', 'Dryer', 'Dedicated workspace', 'Hot tub', 'Pool',
    'Freezer', 'Microwave', 'BBQ grill', 'Fireplace', 'Gym', 'Sauna',
    'Lake access', 'Mountain view', 'Sea view', 'Beach access',
    'Ski-in/Ski-out', 'Patio or balcony', 'EV charger', 'Crib',
]
SORTS = {
    'recommended': 'Recommended',
    'price_asc': 'Price: low to high',
    'price_desc': 'Price: high to low',
    'rating_desc': 'Top rated',
}
PER_PAGE = 12


def normalize_amenity(name):
    return ' '.join(name.lower().replace(':', ' ').split())


def money(v):
    if v is None:
        return None
    return f"${v:,.2f}"


def money0(v):
    if v is None:
        return None
    return f"${v:,.0f}"


def nights_between(checkin, checkout):
    try:
        a = date.fromisoformat(checkin)
        b = date.fromisoformat(checkout)
        return (b - a).days
    except (ValueError, TypeError):
        return None


def trip_price(nightly, nights):
    """The upstream quote model the captures carry: nights x captured
    nightly rate, total includes all fees (the SERP price panel states
    'Trip price, includes all fees'). Deterministic derivation declared
    in provenance.json."""
    subtotal = round(nightly * nights, 2)
    return subtotal, subtotal


# ------------------------------------------------------------------ helpers --

def all_destinations():
    return Destination.query.order_by(Destination.slug).all()


def get_listing_or_404(lid):
    lst = db.session.get(Listing, str(lid))
    if not lst:
        abort(404)
    return lst


def serialize_listing_card(lst):
    return {
        'id': lst.id,
        'name': lst.name,
        'title': lst.title,
        'city': lst.city,
        'rating': lst.rating,
        'reviews_count': lst.reviews_count,
        'is_new': lst.is_new,
        'is_superhost': lst.is_superhost,
        'is_guest_favorite': lst.is_guest_favorite,
        'instant_book': lst.instant_book,
        'nightly_price': lst.nightly_price,
        'photos': lst.photo_list(),
    }


def stay_query(dest_slug, filters):
    """Deterministic filtering over the captured corpus (the pages state
    that visible counts are computed over the captured listings)."""
    q = Listing.query.filter_by(destination_slug=dest_slug)
    cats = filters.get('room_category')
    if cats:
        q = q.filter(Listing.room_category.in_(cats))
    ptypes = filters.get('property_type')
    if ptypes:
        q = q.filter(Listing.property_type.in_(ptypes))
    if filters.get('guest_favorite'):
        q = q.filter_by(is_guest_favorite=True)
    if filters.get('superhost'):
        q = q.filter_by(is_superhost=True)
    if filters.get('instant_book'):
        q = q.filter_by(instant_book=True)
    if filters.get('pets'):
        q = q.filter_by(pets_allowed=True)
    if filters.get('price_min') is not None:
        q = q.filter(Listing.quote_total >= filters['price_min'])
    if filters.get('price_max') is not None:
        q = q.filter(Listing.quote_total <= filters['price_max'])
    if filters.get('bedrooms'):
        q = q.filter(Listing.bedrooms >= filters['bedrooms'])
    if filters.get('beds'):
        q = q.filter(Listing.beds >= filters['beds'])
    if filters.get('baths'):
        q = q.filter(Listing.baths >= filters['baths'])
    for amen in filters.get('amenities', []):
        q = q.filter(Listing.amenity_flags.like(
            f'%"{amen.lower()}"%'))
    order = {
        'recommended': (Listing.serp_position.asc(),),
        'price_asc': (Listing.quote_total.is_(None), Listing.quote_total.asc(),
                      Listing.serp_position.asc()),
        'price_desc': (Listing.quote_total.is_(None), Listing.quote_total.desc(),
                       Listing.serp_position.asc()),
        'rating_desc': (Listing.rating.desc().nullslast(),
                        Listing.serp_position.asc()),
    }[filters.get('sort', 'recommended')]
    return q.order_by(*order)


def parse_stay_filters(args):
    def _float(name):
        v = args.get(name, '').strip()
        try:
            return float(v) if v and math.isfinite(float(v)) and float(v) >= 0 else None
        except ValueError:
            return None

    def _int(name):
        v = args.get(name, '').strip()
        try:
            return int(v) if v else None
        except ValueError:
            return None
    return {
        'room_category': [c for c in args.getlist('room_category') if c],
        'property_type': [p for p in args.getlist('property_type') if p],
        'guest_favorite': args.get('guest_favorite') == '1',
        'superhost': args.get('superhost') == '1',
        'instant_book': args.get('instant_book') == '1',
        'pets': args.get('pets') == '1',
        'price_min': _float('price_min'),
        'price_max': _float('price_max'),
        'bedrooms': _int('bedrooms'),
        'beds': _int('beds'),
        'baths': _int('baths'),
        'amenities': [a for a in args.getlist('amenities') if a],
        'sort': args.get('sort') if args.get('sort') in SORTS else 'recommended',
    }


def corpus_facets(dest_slug, base_q):
    """Facet counts computed over the captured corpus for the filter
    panel (upstream panel shape; counts are corpus counts, and the
    search page states that)."""
    all_q = Listing.query.filter_by(destination_slug=dest_slug)
    total = all_q.count()

    def count(q):
        return q.count()
    return {
        'total': total,
        'guest_favorite': count(base_q.filter(Listing.is_guest_favorite.is_(True))) if total else 0,
        'superhost': count(base_q.filter(Listing.is_superhost.is_(True))) if total else 0,
        'instant_book': count(base_q.filter(Listing.instant_book.is_(True))) if total else 0,
        'pets': count(base_q.filter(Listing.pets_allowed.is_(True))) if total else 0,
    }


def property_types_in_corpus(dest_slug):
    rows = (db.session.query(Listing.property_type, db.func.count(Listing.id))
            .filter(Listing.destination_slug == dest_slug,
                    Listing.property_type.isnot(None),
                    Listing.property_type != '')
            .group_by(Listing.property_type)
            .order_by(db.func.count(Listing.id).desc()).all())
    return [(r[0], r[1]) for r in rows]


def amenity_flags_in_corpus(dest_slug):
    counts = {}
    rows = Listing.query.filter_by(destination_slug=dest_slug).all()
    for lst in rows:
        for a in lst.amenity_flag_set():
            counts[a] = counts.get(a, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def canonical_amenities_in_corpus(dest_slug):
    """The upstream amenity-filter taxonomy (AMENITY_FILTERS, frozen from
    the captured filter panel) restricted to the captured corpus, with
    corpus counts — the same canonical amenity set the upstream SERP
    filter panel renders (review B2: the panel must carry the canonical
    names, so 'Hot tub' and 'Pool' are always checkable whenever the
    corpus carries them, instead of a corpus-count top-14 slice that
    dropped them)."""
    counts = dict(amenity_flags_in_corpus(dest_slug))
    return [(name, name.lower(), counts[name.lower()])
            for name in AMENITY_FILTERS if counts.get(name.lower())]


def dates_available_window(lst, checkin, checkout):
    """Both endpoints must be present in the captured availability
    calendar for the window to be bookable on the mirror."""
    cal = lst.calendar_map()
    if not cal or not checkin or not checkout:
        return False
    if not nights_between(checkin, checkout) or not 0 < nights_between(checkin, checkout) <= 366:
        return False
    d = date.fromisoformat(checkin)
    end = date.fromisoformat(checkout)
    while d < end:
        if not cal.get(d.isoformat()):
            return False
        d += timedelta(days=1)
    return True


def booking_code():
    import string
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = 'HM' + ''.join(secrets.choice(alphabet) for _ in range(8))
        if not Booking.query.filter_by(code=code).first():
            return code


# -------------------------------------------------------------------- routes --

@app.route('/_health')
def health():
    return jsonify(ok=True,
                   listings=Listing.query.count(),
                   experiences=Experience.query.count(),
                   reviews=Review.query.count(),
                   destinations=Destination.query.count(),
                   users=User.query.count(),
                   bookings=Booking.query.count(),
                   wishlists=Wishlist.query.count())


@app.route('/')
def home():
    dests = all_destinations()
    focus = dests[:8]
    carousels = []
    for d in focus[:4]:
        items = Listing.query.filter_by(destination_slug=d.slug) \
            .order_by(Listing.serp_position).limit(6).all()
        if items:
            carousels.append((d, items))
    exp_items = Experience.query.order_by(Experience.city_slug,
                                          Experience.rating.desc()).limit(8).all()
    return render_template('home.html', dests=dests, carousels=carousels,
                           exp_items=exp_items)


@app.route('/s/homes')
def search_redirect():
    slug = request.args.get('query', '').strip()
    for d in all_destinations():
        if slug and (d.city.lower() in slug.lower() or d.label.lower() in slug.lower()):
            return redirect(url_for('stays_search', slug=d.slug, **{k: request.args[k] for k in ['checkin', 'checkout', 'adults'] if request.args.get(k)}))
    if slug:
        abort(404, description='No captured destination matches this search.')
    return redirect(url_for('home'))


@app.route('/s/<slug>/homes')
def stays_search(slug):
    dest = db.session.get(Destination, slug)
    if not dest:
        abort(404)
    filters = parse_stay_filters(request.args)
    q = stay_query(slug, filters)
    listings = q.all()
    panel = json.loads(dest.filter_panel or '{}')
    facets = corpus_facets(slug, Listing.query.filter_by(destination_slug=slug))
    ptypes = property_types_in_corpus(slug)
    amenities = canonical_amenities_in_corpus(slug)
    return render_template(
        'stays_search.html', dest=dest, listings=listings, filters=filters,
        panel=panel, facets=facets, ptypes=ptypes, amenities=amenities,
        sort_options=SORTS, room_labels=ROOM_LABELS,
        checkin=request.args.get('checkin', ''),
        checkout=request.args.get('checkout', ''),
        adults=request.args.get('adults', ''))


def calendar_months(lst, limit=3):
    """Up to `limit` captured months as render-ready grids."""
    cal = lst.calendar_map()
    months = {}
    for dstr in sorted(cal):
        y, m, dd = dstr.split('-')
        months.setdefault((int(y), int(m)), []).append((int(dd), cal[dstr]))
    names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
             'July', 'August', 'September', 'October', 'November', 'December']
    out = []
    for (y, m), days in sorted(months.items())[:limit]:
        import calendar as _cal
        lead = _cal.monthrange(y, m)[1]  # placeholder, replaced below
        first_wd = date(y, m, 1).weekday()  # Mon=0
        lead = (first_wd + 1) % 7          # Sunday-first grid
        out.append({'name': names[m], 'year': y, 'lead': lead,
                    'days': [{'label': dd, 'available': ok} for dd, ok in days]})
    return out


@app.route('/rooms/<lid>')
def listing_detail(lid):
    lst = get_listing_or_404(lid)
    reviews = (Review.query.filter_by(listing_id=lst.id)
               .order_by(Review.id).all())
    tags = (ReviewTag.query.filter_by(listing_id=lst.id)
            .order_by(ReviewTag.count.desc()).all())
    quality = json.loads(lst.quality or '{}')
    # Review r2 (B4 residual, same root cause): highlight bodies are captured
    # as LocalizedContent envelopes and every title is null — render the
    # unpacked text, never ``<strong>None</strong> — {…}`` dict repr. The
    # house-rules/safety item descriptions use the same envelope family.
    rules = unpack_rule_groups(json.loads(lst.house_rules or '{}'))
    safety = unpack_rule_groups(json.loads(lst.safety or '{}'))
    highlights = []
    for h in json.loads(lst.highlights or '[]'):
        entry = {'title': localized_text(h.get('title')),
                 'body': localized_text(h.get('body'))}
        if entry['title'] or entry['body']:
            highlights.append(entry)
    # Sleeping arrangements capture null bed labels (items: [null]) — skip
    # them instead of rendering a literal "None" placeholder.
    sleeping = [{'name': s.get('name'),
                 'items': [i for i in (s.get('items') or [])
                           if isinstance(i, str)]}
                for s in json.loads(lst.sleeping or '[]')]
    ttk = json.loads(lst.things_to_know or '[]')
    similar_ids = [s.get('id') for s in json.loads(lst.similar or '[]') if s.get('id')]
    similar = [db.session.get(Listing, sid) for sid in similar_ids
               if db.session.get(Listing, sid)]
    explore = json.loads(lst.explore or '[]')
    saved_ids = set()
    user_wishlists = []
    if current_user.is_authenticated:
        rows = (WishlistItem.query
                .join(Wishlist).filter(Wishlist.user_id == current_user.id,
                                       WishlistItem.listing_id == lst.id).all())
        saved_ids = {w.wishlist_id for w in rows}
        user_wishlists = (Wishlist.query.filter_by(user_id=current_user.id)
                          .order_by(Wishlist.id).all())
    checkin = request.args.get('checkin', lst.quote_checkin)
    checkout = request.args.get('checkout', lst.quote_checkout)
    adults = request.args.get('adults', '2')
    nights = nights_between(checkin, checkout)
    price_total = None
    if nights and nights > 0:
        price_total = round((lst.nightly_price or 0) * nights, 2)
    return render_template(
        'listing_detail.html', lst=lst, reviews=reviews, tags=tags,
        quality=quality, rules=rules, safety=safety, sleeping=sleeping,
        ttk=ttk, highlights=highlights, similar=similar, explore=explore,
        dests_all=all_destinations(),
        saved_ids=saved_ids, checkin=checkin, checkout=checkout,
        adults=adults, nights=nights, price_total=price_total,
        cal_months=calendar_months(lst, limit=12), user_wishlists=user_wishlists,
        available=dates_available_window(lst, checkin, checkout),
        money=money, money0=money0)


@app.route('/rooms/<lid>/reviews')
def listing_reviews(lid):
    lst = get_listing_or_404(lid)
    reviews = (Review.query.filter_by(listing_id=lst.id)
               .order_by(Review.id).all())
    tags = (ReviewTag.query.filter_by(listing_id=lst.id)
            .order_by(ReviewTag.count.desc()).all())
    quality = json.loads(lst.quality or '{}')
    return render_template('listing_reviews.html', lst=lst, reviews=reviews,
                           tags=tags, quality=quality)


@app.route('/rooms/<lid>/book', methods=['GET', 'POST'])
def book_stay(lid):
    lst = get_listing_or_404(lid)
    checkin = request.values.get('checkin', '').strip()
    checkout = request.values.get('checkout', '').strip()
    adults = request.values.get('adults', '1').strip() or '1'
    if request.method == 'GET':
        nights = nights_between(checkin, checkout)
        if not nights or nights <= 0:
            return redirect(url_for('listing_detail', lid=lid))
        return render_template('book_stay.html', lst=lst, checkin=checkin,
                               checkout=checkout, adults=adults, nights=nights,
                               money=money)
    # POST — confirm and book
    if not current_user.is_authenticated:
        # relative next: the login guard only accepts paths starting with
        # '/', so an absolute request.url broke the round trip (review M1)
        return redirect(url_for('login', next=url_for('book_stay', lid=lid, checkin=checkin, checkout=checkout, adults=adults)))
    nights = nights_between(checkin, checkout)
    if not nights or nights <= 0:
        abort(400)
    if not dates_available_window(lst, checkin, checkout):
        return render_template('book_stay.html', lst=lst, checkin=checkin, checkout=checkout, adults=adults, nights=nights, error='These dates are not available in the captured calendar.', money=money), 400
    capacity = lst.max_guest_capacity or lst.person_capacity or 16
    try:
        n_adults = int(adults)
    except ValueError:
        n_adults = 0
    if n_adults < 1 or n_adults > capacity:
        return render_template('book_stay.html', lst=lst, checkin=checkin,
                               checkout=checkout, adults=adults, nights=nights,
                               error=f'This place allows up to {capacity} guests.',
                               money=money)
    existing = Booking.query.filter_by(user_id=current_user.id, kind='stay', listing_id=lst.id, checkin=checkin, checkout=checkout, status='confirmed').first()
    if existing:
        return redirect(url_for('booking_detail', code=existing.code))
    subtotal, total = trip_price(lst.nightly_price or 0, nights)
    bk = Booking(code=booking_code(), user_id=current_user.id, kind='stay',
                 listing_id=lst.id, checkin=checkin, checkout=checkout,
                 adults=n_adults, guests=n_adults, nights=nights,
                 nightly_price=lst.nightly_price, subtotal=subtotal, total=total,
                 status='confirmed', created_at=MIRROR_TS)
    db.session.add(bk)
    db.session.commit()
    return redirect(url_for('booking_detail', code=bk.code))


@app.route('/bookings/<code>')
def booking_detail(code):
    bk = Booking.query.filter_by(code=code).first_or_404()
    if not current_user.is_authenticated or bk.user_id != current_user.id:
        return redirect(url_for('login'))
    lst = db.session.get(Listing, bk.listing_id) if bk.listing_id else None
    exp = db.session.get(Experience, bk.experience_id) if bk.experience_id else None
    return render_template('booking_detail.html', bk=bk, lst=lst, exp=exp,
                           money=money, nights=bk.nights)


@app.route('/trips')
@login_required
def trips():
    bookings = (Booking.query.filter_by(user_id=current_user.id)
                .order_by(Booking.id.desc()).all())
    items = []
    for bk in bookings:
        lst = db.session.get(Listing, bk.listing_id) if bk.listing_id else None
        exp = db.session.get(Experience, bk.experience_id) if bk.experience_id else None
        items.append((bk, lst, exp))
    return render_template('trips.html', items=items, money=money)


@app.route('/trips/<code>/cancel', methods=['POST'])
@login_required
def cancel_trip(code):
    bk = Booking.query.filter_by(code=code).first_or_404()
    if bk.user_id != current_user.id:
        abort(403)
    bk.status = 'cancelled'
    db.session.commit()
    return redirect(url_for('booking_detail', code=code))


# ----------------------------------------------------------------- wishlists --

def _default_wishlist(user):
    wl = (Wishlist.query.filter_by(user_id=user.id, is_default=True).first())
    if not wl:
        wl = Wishlist(user_id=user.id, name='Saved', is_default=True,
                      created_at=MIRROR_TS)
        db.session.add(wl)
        db.session.commit()
    return wl


@app.route('/wishlist')
@login_required
def wishlist_index():
    wls = (Wishlist.query.filter_by(user_id=current_user.id)
           .order_by(Wishlist.id).all())
    out = []
    item_listing = {}
    item_exp = {}
    item_market = {}
    dest_city = {d.slug: d.city for d in Destination.query.all()}
    for wl in wls:
        rows = (WishlistItem.query.filter_by(wishlist_id=wl.id)
                .order_by(WishlistItem.id.desc()).all())
        out.append((wl, rows))
        for item in rows:
            item_listing[item.id] = db.session.get(Listing, item.listing_id) \
                if item.listing_id else None
            item_exp[item.id] = db.session.get(Experience, item.experience_id) \
                if item.experience_id else None
            # the market the saved stay belongs to (review M5): the card
            # shows the destination city, so a suburb-localized listing
            # (e.g. 'Room in Paradise Valley' in the Scottsdale market)
            # is still identifiable from the wishlists page
            lst = item_listing[item.id]
            if lst:
                item_market[item.id] = dest_city.get(lst.destination_slug)
    return render_template('wishlist.html', wishlists=out,
                           item_listing=item_listing, item_exp=item_exp,
                           item_market=item_market)


@app.route('/wishlist/create', methods=['POST'])
@login_required
def wishlist_create():
    name = request.form.get('name', '').strip()
    if name:
        wl = Wishlist(user_id=current_user.id, name=name, is_default=False,
                      created_at=MIRROR_TS)
        db.session.add(wl)
        db.session.commit()
    return redirect(url_for('wishlist_index'))


@app.route('/wishlist/add', methods=['POST'])
def wishlist_add():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    lid = request.form.get('listing_id', '').strip()
    eid = request.form.get('experience_id', '').strip()
    new_name = request.form.get('new_name', '').strip()
    target = request.form.get('wishlist_id', '').strip()
    if new_name:
        wl = Wishlist(user_id=current_user.id, name=new_name,
                      is_default=False, created_at=MIRROR_TS)
        db.session.add(wl)
        db.session.commit()
    elif target:
        wl = db.session.get(Wishlist, int(target))
        if not wl or wl.user_id != current_user.id:
            abort(403)
    else:
        wl = _default_wishlist(current_user)
    existing = WishlistItem.query.filter_by(
        wishlist_id=wl.id,
        listing_id=lid or None,
        experience_id=eid or None).first()
    if not existing:
        item = WishlistItem(wishlist_id=wl.id,
                            listing_id=lid or None,
                            experience_id=eid or None,
                            added_at=MIRROR_TS)
        db.session.add(item)
        db.session.commit()
    return redirect(request.form.get('back') or url_for('wishlist_index'))


@app.route('/wishlist/<int:item_id>/remove', methods=['POST'])
@login_required
def wishlist_remove(item_id):
    item = db.session.get(WishlistItem, item_id)
    if not item:
        abort(404)
    wl = db.session.get(Wishlist, item.wishlist_id)
    if not wl or wl.user_id != current_user.id:
        abort(403)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('wishlist_index'))


# --------------------------------------------------------------- experiences --

@app.route('/s/experiences')
def experiences_search():
    city = request.args.get('city', 'austin').strip()
    category = request.args.get('category', '').strip()
    sort = request.args.get('sort', 'recommended')
    dest = db.session.get(Destination, city)
    if not dest:
        abort(404)
    q = Experience.query.filter_by(city_slug=city)
    if category:
        q = q.filter(Experience.theme == category)
    if sort == 'price_asc':
        q = q.order_by(Experience.price_per_guest.asc())
    elif sort == 'price_desc':
        q = q.order_by(Experience.price_per_guest.desc())
    elif sort == 'rating_desc':
        q = q.order_by(Experience.rating.desc())
    else:
        q = q.order_by(Experience.rating.desc())
    items = q.all()
    categories = sorted({e.theme for e in
                         Experience.query.filter_by(city_slug=city).all()
                         if e.theme})
    # destination selector (review B3): the cities that carry captured
    # experiences, so LA/NYC/Miami are reachable through the UI
    exp_cities = (Destination.query
                  .join(Experience, Experience.city_slug == Destination.slug)
                  .distinct().order_by(Destination.slug).all())
    return render_template('experiences_search.html', dest=dest, items=items,
                           categories=categories, category=category, sort=sort,
                           exp_cities=exp_cities)


@app.route('/experiences/<eid>')
def experience_detail(eid):
    exp = db.session.get(Experience, str(eid))
    if not exp:
        abort(404)
    saved_ids = set()
    user_wishlists = []
    if current_user.is_authenticated:
        rows = (WishlistItem.query
                .join(Wishlist).filter(Wishlist.user_id == current_user.id,
                                       WishlistItem.experience_id == exp.id).all())
        saved_ids = {w.wishlist_id for w in rows}
        user_wishlists = (Wishlist.query.filter_by(user_id=current_user.id)
                          .order_by(Wishlist.id).all())
    return render_template('experience_detail.html', exp=exp, saved_ids=saved_ids,
                           user_wishlists=user_wishlists, offerings=exp.offering_list())


@app.route('/experiences/<eid>/book', methods=['GET', 'POST'])
def book_experience(eid):
    exp = db.session.get(Experience, str(eid))
    if not exp:
        abort(404)
    offerings = exp.offering_list()
    if request.method == 'GET':
        when = request.values.get('date', '')
        guests = request.values.get('guests', '1')
        return render_template('book_experience.html', exp=exp,
                               offerings=offerings, when=when, guests=guests,
                               money=money)
    if not current_user.is_authenticated:
        # relative next (review M1): request.url is absolute and the login
        # guard rejects it, stranding the user on the home page
        return redirect(url_for('login', next=url_for('book_experience', eid=eid, date=request.form.get('date', ''), guests=request.form.get('guests', '1'))))
    when = request.form.get('date', '').strip()
    guests = request.form.get('guests', '1').strip() or '1'
    if not when:
        return render_template('book_experience.html', exp=exp,
                               offerings=offerings, when=when, guests=guests,
                               error='Pick a date from the upcoming availability.',
                               money=money)
    valid = any(o.get('iso') == when for o in offerings)
    if not valid:
        return render_template('book_experience.html', exp=exp,
                               offerings=offerings, when=when, guests=guests,
                               error='That date is not in the captured availability.',
                               money=money)
    try:
        n_guests = int(guests)
    except ValueError:
        n_guests = 0
    if not 1 <= n_guests <= 6:
        return render_template('book_experience.html', exp=exp, offerings=offerings, when=when, guests=guests, error='Choose between 1 and 6 guests.', money=money), 400
    total = round((exp.price_per_guest or 0) * n_guests, 2)
    bk = Booking(code=booking_code(), user_id=current_user.id,
                 kind='experience', experience_id=exp.id, experience_date=when,
                 adults=n_guests, guests=n_guests, subtotal=total, total=total,
                 status='confirmed', created_at=MIRROR_TS)
    db.session.add(bk)
    db.session.commit()
    return redirect(url_for('booking_detail', code=bk.code))


# ----------------------------------------------------------------- accounts --

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    user = User.query.filter_by(email=email).first()
    if user and bcrypt.check_password_hash(user.password_hash, password):
        login_user(user)
        target = request.args.get('next') or request.form.get('next')
        if target and target.startswith('/') and not target.startswith('//') and '\\' not in target and not any(ord(c) < 32 for c in target) and not urlsplit(target).netloc:
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
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    if not name or not email or '@' not in email or len(password) < 8:
        return render_template('signup.html',
                               error='Enter your full name, a valid email and a password of at least 8 characters.')
    if User.query.filter_by(email=email).first():
        return render_template('signup.html', error='An account with that email already exists.')
    user = User(email=email, name=name,
                password_hash=bcrypt.generate_password_hash(password).decode(),
                joined=MIRROR_TS)
    db.session.add(user)
    db.session.commit()
    _default_wishlist(user)
    login_user(user)
    return redirect(url_for('home'))


# -------------------------------------------------------------------- seeding --

def seed_database():
    if Destination.query.count() > 0:
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
    if os.environ.get('AIRBNB_AUTO_SEED', '1') == '1':
        seed_database()
        seed_benchmark_users()
