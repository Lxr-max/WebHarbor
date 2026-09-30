"""StubHub (stubhub.com) mirror — Flask application.

Mirrors https://www.stubhub.com/ as served on 2026-09-26: the home page with
its popular-events carousel and location-filtered event grid, the
category/grouping/performer browse pages, the search with performer
suggestions, the event pages with the real seat-map SVG, filtered ticket
listings (quantity / price / sort / features / zones) and the per-listing
seat-view photos, the purchase pipeline (listing -> quantity -> review ->
delivery -> payment -> confirmation with the fee breakdown), the seller
pipeline (sell landing -> find event -> create listing -> manage listings ->
sales), the account domain (orders, payments, favorites), and the gift-card
store.

All runtime data lives in instance/stubhub.db (built deterministically by
seed_data.py from the tracked source_data/ snapshots); heavy imagery lives
under static/images/ (HF-managed).
"""
from __future__ import annotations

import json
import os
import random
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_bcrypt import Bcrypt
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from markupsafe import escape
from sqlalchemy import Index, text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "STUBHUB_DB_PATH", f"sqlite:///{BASE_DIR}/instance/stubhub.db")
app.config["SECRET_KEY"] = "webharbor-stubhub-dev-key"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = ""

# The mirror pins "now" to the snapshot date so every relative statement
# ("today", "this weekend") stays deterministic.
MIRROR_NOW = datetime(2026, 9, 26, 12, 0)

# StubHub shows all-in prices ("incl. fees"). The checkout breakdown splits a
# ticket price into base fare + service fee at a fixed rate, plus a per-order
# processing fee. Deterministic so order math is verifiable.
SERVICE_FEE_RATE = 0.22
ORDER_PROCESSING_FEE = 2.95
DELIVERY_FEES = {"instant": 0.0, "mobile": 0.0, "ups": 14.95}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(128), unique=True, nullable=False)
    display_name = db.Column(db.String(96), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    metro_id = db.Column(db.Integer, db.ForeignKey("metros.id"), default=1)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def check_password(self, pw):
        return bcrypt.check_password_hash(self.password_hash, pw)


class Metro(db.Model):
    """Location-picker entries (the 'Redmond' chip in the header)."""
    __tablename__ = "metros"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    slug = db.Column(db.String(64), unique=True, nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    is_default = db.Column(db.Boolean, default=False)


class CategoryNode(db.Model):
    """Taxonomy node: top categories (Sports/Concerts/Theater/Festivals),
    genre categories, and league groupings all share one tree."""
    __tablename__ = "category_nodes"
    id = db.Column(db.Integer, primary_key=True)
    upstream_id = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String(96), nullable=False)
    slug = db.Column(db.String(96), nullable=False)
    kind = db.Column(db.String(16), nullable=False)  # top|category|grouping
    parent_id = db.Column(db.Integer, db.ForeignKey("category_nodes.id"))
    sort = db.Column(db.Integer, default=0)
    children = db.relationship("CategoryNode", backref=db.backref("parent", remote_side=[id]))


class Performer(db.Model):
    __tablename__ = "performers"
    id = db.Column(db.Integer, primary_key=True)
    upstream_id = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(160), nullable=False)
    node_id = db.Column(db.Integer, db.ForeignKey("category_nodes.id"))
    image_file = db.Column(db.String(200))
    hero_file = db.Column(db.String(200))
    bio = db.Column(db.Text)
    followers = db.Column(db.Integer, default=0)
    hourly_views = db.Column(db.Integer, default=0)
    is_team = db.Column(db.Boolean, default=False)

    @property
    def event_count(self):
        return Event.query.filter_by(performer_id=self.id).count()

    @property
    def next_events(self):
        return (Event.query.filter_by(performer_id=self.id)
                .order_by(Event.starts_at).limit(2).all())

    @property
    def next_range(self):
        evs = self.next_events
        if not evs:
            return ""
        if len(evs) == 1:
            ev = evs[0]
            return "TBA" if ev.is_time_tbd else \
                f"{ev.local_starts_at.strftime('%a, %b %-d')} • {fmt_time(ev.local_starts_at)}"
        a, b = evs
        ya = "" if a.local_starts_at.year == MIRROR_NOW.year else f" {a.local_starts_at.year}"
        yb = "" if b.local_starts_at.year == MIRROR_NOW.year else f" {b.local_starts_at.year}"
        return f"{a.local_starts_at.strftime('%b %-d')}{ya} - {b.local_starts_at.strftime('%b %-d')}{yb}"

    @property
    def next_label(self):
        evs = self.next_events
        if not evs:
            return "No upcoming events"
        ev = evs[0]
        return "TBA" if ev.is_time_tbd else \
            f"{ev.local_starts_at.strftime('%a, %b %-d')} • {fmt_time(ev.local_starts_at)}"


class Venue(db.Model):
    __tablename__ = "venues"
    id = db.Column(db.Integer, primary_key=True)
    upstream_id = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String(160), nullable=False)
    city = db.Column(db.String(96), nullable=False)
    state = db.Column(db.String(16))
    country = db.Column(db.String(48))
    seatmap_file = db.Column(db.String(200))
    sections = db.Column(db.Text)  # JSON list of section labels


class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True)
    upstream_id = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), nullable=False)
    performer_id = db.Column(db.Integer, db.ForeignKey("performers.id"))
    venue_id = db.Column(db.Integer, db.ForeignKey("venues.id"))
    node_id = db.Column(db.Integer, db.ForeignKey("category_nodes.id"))
    starts_at = db.Column(db.DateTime, nullable=False)
    is_time_tbd = db.Column(db.Boolean, default=False)
    holiday_badge = db.Column(db.String(64))
    listing_count = db.Column(db.Integer, default=0)
    min_price = db.Column(db.Integer)
    max_price = db.Column(db.Integer)
    is_parking = db.Column(db.Boolean, default=False)
    is_popular = db.Column(db.Boolean, default=False)
    is_recommended = db.Column(db.Boolean, default=False)
    availability_note = db.Column(db.String(64))
    on_sale_at = db.Column(db.DateTime)

    performer = db.relationship("Performer", backref="events")
    venue = db.relationship("Venue", backref="events")

    @property
    def url_path(self):
        return f"/{self.slug}/event/{self.upstream_id}"

    @property
    def local_starts_at(self):
        """The start instant rendered in the venue's local timezone."""
        return to_venue_local(self.starts_at, self.venue.state if self.venue else None)

    @property
    def date_label(self):
        if self.is_time_tbd:
            return "TBA"
        return self.local_starts_at.strftime("%b %-d") if self.local_starts_at.year == MIRROR_NOW.year \
            else self.local_starts_at.strftime("%b %-d '%y")

    @property
    def date_full(self):
        if self.is_time_tbd:
            return "TBA"
        return self.local_starts_at.strftime("%a, %b %-d • %-I:%M %p").replace("AM", "AM").replace("PM", "PM")


class Listing(db.Model):
    __tablename__ = "listings"
    id = db.Column(db.Integer, primary_key=True)
    upstream_id = db.Column(db.BigInteger, unique=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    section = db.Column(db.String(64), nullable=False)
    zone = db.Column(db.String(64))
    row = db.Column(db.String(32))
    seats = db.Column(db.String(64))
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)  # per ticket, incl. fees
    original_price = db.Column(db.Integer)  # pre-discount, if discounted
    features = db.Column(db.Text)  # JSON list
    badges = db.Column(db.Text)  # JSON list
    deal_rating = db.Column(db.Float)
    seat_view_file = db.Column(db.String(200))
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"))  # set => user listing
    is_sold = db.Column(db.Boolean, default=False)
    is_sponsored = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime)

    event = db.relationship("Event", backref="listings")

    @property
    def feature_list(self):
        return json.loads(self.features or "[]")

    @property
    def badge_list(self):
        return json.loads(self.badges or "[]")

    @property
    def price_display(self):
        return f"${self.price:,}"

    def base_fare(self):
        return round(self.price / (1 + SERVICE_FEE_RATE))

    def service_fee(self):
        return self.price - self.base_fare()


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(24), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"))
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Integer, nullable=False)
    delivery_method = db.Column(db.String(16), nullable=False)
    delivery_fee = db.Column(db.Float, nullable=False)
    processing_fee = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(24), nullable=False, default="Confirmed")
    placed_at = db.Column(db.DateTime, nullable=False)
    card_last4 = db.Column(db.String(8))

    user = db.relationship("User", backref="orders")
    event = db.relationship("Event", backref="orders")
    listing = db.relationship("Listing", backref="order", uselist=False)

    def subtotal(self):
        return self.quantity * self.unit_price

    def fees_total(self):
        return self.total - self.subtotal()


class Sale(db.Model):
    """Completed seller-side transactions for the benchmark users."""
    __tablename__ = "sales"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"))
    section = db.Column(db.String(64))
    row = db.Column(db.String(32))
    quantity = db.Column(db.Integer)
    payout = db.Column(db.Float)
    status = db.Column(db.String(24), default="Paid")
    sold_at = db.Column(db.DateTime)
    order_number = db.Column(db.String(24))

    user = db.relationship("User", backref="sales")
    event = db.relationship("Event", backref="sales")


class PaymentCard(db.Model):
    __tablename__ = "payment_cards"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    brand = db.Column(db.String(24), nullable=False)
    last4 = db.Column(db.String(8), nullable=False)
    holder = db.Column(db.String(96))
    exp_month = db.Column(db.Integer, nullable=False)
    exp_year = db.Column(db.Integer, nullable=False)
    is_default = db.Column(db.Boolean, default=False)

    user = db.relationship("User", backref="cards")


class Favorite(db.Model):
    __tablename__ = "favorites"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    performer_id = db.Column(db.Integer, db.ForeignKey("performers.id"))
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"))
    created_at = db.Column(db.DateTime)

    performer = db.relationship("Performer")
    event = db.relationship("Event")


class GiftCardOrder(db.Model):
    __tablename__ = "gift_card_orders"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    amount = db.Column(db.Integer, nullable=False)
    recipient_name = db.Column(db.String(96))
    recipient_email = db.Column(db.String(128))
    message = db.Column(db.Text)
    design = db.Column(db.String(32), default="classic")
    code = db.Column(db.String(24), nullable=False)
    status = db.Column(db.String(24), default="Delivered")
    created_at = db.Column(db.DateTime)


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    body = db.Column(db.String(200))
    kind = db.Column(db.String(24), default="info")
    created_at = db.Column(db.DateTime)


# ---------------------------------------------------------------------------
# Asset / formatting helpers
# ---------------------------------------------------------------------------

def _build_asset_url_map():
    mapping = {}
    try:
        with open(os.path.join(BASE_DIR, "asset_inventory.json"), encoding="utf-8") as fh:
            for asset in json.load(fh).get("assets", []):
                source_url = asset.get("source_url") or ""
                local = asset.get("path") or ""
                if source_url and local:
                    mapping[source_url] = local
    except (OSError, ValueError):
        pass
    return mapping


ASSET_URL_MAP = _build_asset_url_map()


def resolve_asset(url_or_path):
    """Map an upstream image URL to its static/images path (or None)."""
    if not url_or_path:
        return None
    if url_or_path.startswith("/static/"):
        return url_or_path
    local = ASSET_URL_MAP.get(url_or_path)
    if local:
        return "/" + local
    return None


# ---------------------------------------------------------------------------
# Venue-local time rendering (#F5)
#
# Event start instants are stored as the upstream UTC epoch — the true
# kickoff instant. Upstream renders them in the venue's local timezone (the
# local date is what the event URL slug encodes), so every user-facing
# date/time is converted with the venue's US timezone before formatting.
# The US DST rule (2nd Sunday of March .. 1st Sunday of November) is applied
# arithmetically: deterministic, no tzdata dependency.

TZ_BASE_OFFSET = {"P": -8, "E": -5, "M": -7}      # standard-time UTC hours
TZ_BY_STATE = {"WA": "P", "CA": "P", "NV": "P",
               "NY": "E", "NJ": "E", "CT": "E", "MA": "E", "MD": "E",
               "NC": "E", "PA": "E", "CO": "M"}


def _nth_sunday(year, month, n):
    first = date(year, month, 1)
    first_sunday = 1 + (6 - first.weekday()) % 7
    return date(year, month, first_sunday + 7 * (n - 1))


def _us_dst_active(day):
    return _nth_sunday(day.year, 3, 2) <= day < _nth_sunday(day.year, 11, 1)


def to_venue_local(utc_dt, state):
    """Convert a stored UTC instant to the venue's local (naive) datetime."""
    zone = TZ_BY_STATE.get((state or "").upper(), "P")
    offset = TZ_BASE_OFFSET[zone] + (1 if _us_dst_active(utc_dt.date()) else 0)
    return utc_dt + timedelta(hours=offset)


def fmt_money(value):
    if value is None:
        return "—"
    if isinstance(value, float) and not value.is_integer():
        return f"${value:,.2f}"
    return f"${int(value):,}"


def fmt_date_short(dt):
    return dt.strftime("%b %-d")


def fmt_date_full(dt):
    return dt.strftime("%a, %b %-d")


def fmt_time(dt):
    return dt.strftime("%-I:%M %p")


def rel_days(dt):
    days = (dt.date() - MIRROR_NOW.date()).days
    if days == 0:
        return "Today"
    if days == 1:
        return "Tomorrow"
    return None


def slugify(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def parse_price(text):
    if not text:
        return None
    m = re.search(r"\$?([\d,]+)", str(text))
    return int(m.group(1).replace(",", "")) if m else None


STOP_WORDS = {"the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or",
              "is", "it", "by", "with", "vs", "vs.", "at"}


def tokenize(query):
    return [t.lower() for t in re.split(r"\W+", query)
            if t.lower() not in STOP_WORDS and len(t) > 1]


def scored_search(query, items, fields=("name",)):
    tokens = tokenize(query)
    if not tokens:
        return items
    scored = []
    for item in items:
        text = " ".join(getattr(item, f, "") or "" for f in fields).lower()
        score = sum(1 for t in tokens if t in text)
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda pair: (-pair[0], pair[1].name.lower() if hasattr(pair[1], "name") else 0))
    return [item for _, item in scored]


def zone_for_section(section):
    """Group a section label into the zone buckets the filters use."""
    s = (section or "").strip().upper()
    m = re.match(r"^(\d)", s)
    if m and re.match(r"^\d{3}", s):
        return f"{m.group(1)}00 Level"
    if s.startswith("SUITE"):
        return "Suites"
    if s in ("FLOOR", "PIT", "SNAKE", "MIX"):
        return "Floor"
    if s.startswith("LOGE") or s.startswith("BOX"):
        return "Boxes"
    if s.startswith("BALC"):
        return "Balcony"
    if s.startswith("MAIN") or s.startswith("ORCH"):
        return "Main Floor"
    if s.startswith("MEZZ"):
        return "Mezzanine"
    return "Other"


# ---------------------------------------------------------------------------
# Template context
# ---------------------------------------------------------------------------

@app.context_processor
def base_context():
    top_nodes = CategoryNode.query.filter_by(kind="top").order_by(CategoryNode.sort).all()
    metro = None
    if current_user.is_authenticated:
        metro = Metro.query.get(current_user.metro_id)
    return {
        "top_nodes": top_nodes,
        "current_metro": metro,
        "default_metro": Metro.query.filter_by(is_default=True).first(),
        "MIRROR_NOW": MIRROR_NOW,
    }


def event_card(evt, metro=None):
    local = evt.local_starts_at
    return {
        "id": evt.upstream_id,
        "name": evt.name,
        "slug": evt.slug,
        "url": evt.url_path,
        "date_label": evt.date_label,
        "date_full": fmt_date_full(local),
        "time": "TBA" if evt.is_time_tbd else fmt_time(local),
        "venue": evt.venue.name if evt.venue else "",
        "city": f"{evt.venue.city}, {evt.venue.state}" if evt.venue else "",
        "badge": evt.holiday_badge or rel_days(local),
        "min_price": evt.min_price,
        "listing_count": evt.listing_count,
    }


# ---------------------------------------------------------------------------
# Browse: home, category, grouping, performer
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    popular_ids = [p.id for p in Performer.query.order_by(Performer.followers.desc()).limit(12).all()]
    popular = Performer.query.filter(Performer.id.in_(popular_ids)).all()
    popular.sort(key=lambda p: -p.followers)
    recommended = Performer.query.filter(Performer.hourly_views > 0) \
        .order_by(Performer.hourly_views.desc()).limit(20).all()
    grid = Event.query.filter(Event.listing_count > 0).order_by(Event.starts_at).limit(30).all()
    return render_template("index.html", popular=popular, recommended=recommended,
                           grid=grid, event_card=event_card)


def _grid_for_node(node, page, per_page=20):
    """All events under a taxonomy node (including children)."""
    node_ids = [node.id]
    frontier = [node]
    while frontier:
        nxt = []
        for n in frontier:
            kids = CategoryNode.query.filter_by(parent_id=n.id).all()
            for k in kids:
                node_ids.append(k.id)
                nxt.append(k)
        frontier = nxt
    q = Event.query.filter(Event.node_id.in_(node_ids))
    if Event.query.filter(Event.node_id.in_(node_ids)).filter(Event.listing_count > 0).count() > 20:
        q = q.filter(Event.listing_count > 0)
    total = q.count()
    items = (q.order_by(Event.starts_at)
             .offset((page - 1) * per_page).limit(per_page).all())
    return items, total


def _node_page(node, page):
    if node.kind == "grouping":
        # league grouping: member performers (teams), then their events
        members = Performer.query.filter_by(node_id=node.id).order_by(Performer.name).all()
        events, total = _grid_for_node(node, page)
        return render_template("grouping.html", node=node, members=members,
                               events=events, total=total, page=page,
                               event_card=event_card)
    top = Performer.query.filter_by(node_id=node.id).order_by(Performer.followers.desc()).limit(12).all()
    events, total = _grid_for_node(node, page)
    parent = node.parent
    return render_template("category.html", node=node, parent=parent,
                           top_performers=top, events=events, total=total,
                           page=page, event_card=event_card)


@app.route("/<path:slug>/category/<int:upstream_id>")
def category_page(slug, upstream_id):
    node = CategoryNode.query.filter_by(upstream_id=upstream_id).first_or_404()
    canonical = f"{node.slug}-tickets" if node.slug else None
    if canonical and slug != canonical:
        return redirect(f"/{canonical}/category/{node.upstream_id}")
    page = max(1, request.args.get("page", 1, type=int))
    return _node_page(node, page)


@app.route("/<path:slug>/grouping/<int:upstream_id>")
def grouping_page(slug, upstream_id):
    node = CategoryNode.query.filter_by(upstream_id=upstream_id).first_or_404()
    canonical = f"{node.slug}-tickets" if node.slug else None
    if canonical and slug != canonical:
        return redirect(f"/{canonical}/grouping/{node.upstream_id}")
    page = max(1, request.args.get("page", 1, type=int))
    return _node_page(node, page)


@app.route("/<path:slug>/performer/<int:upstream_id>")
def performer_page(slug, upstream_id):
    performer = Performer.query.filter_by(upstream_id=upstream_id).first_or_404()
    canonical = f"{performer.slug}-tickets"
    if slug != canonical:
        return redirect(f"/{canonical}/performer/{performer.upstream_id}")
    page = max(1, request.args.get("page", 1, type=int))
    per_page = 20
    events = (Event.query.filter_by(performer_id=performer.id)
              .order_by(Event.starts_at)
              .offset((page - 1) * per_page).limit(per_page).all())
    total = Event.query.filter_by(performer_id=performer.id).count()
    similar = []
    if performer.node_id:
        similar = (Performer.query
                   .filter(Performer.node_id == performer.node_id,
                           Performer.id != performer.id)
                   .order_by(Performer.followers.desc()).limit(8).all())
    is_fav = False
    if current_user.is_authenticated:
        is_fav = Favorite.query.filter_by(user_id=current_user.id,
                                           performer_id=performer.id).first() is not None
    return render_template("performer.html", performer=performer, events=events,
                           total=total, page=page, similar=similar,
                           is_fav=is_fav, event_card=event_card)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

@app.route("/search")
def search():
    q = (request.args.get("q") or "").strip()
    performers, events = [], []
    if q:
        performers = scored_search(q, Performer.query.all(),
                                    ("name", "slug"))[:8]
        evs = Event.query.filter(Event.listing_count > 0).all()
        events = scored_search(q, evs, ("name",))[:40]
        # also events by matched performer
        matched_ids = {p.id for p in performers}
        extra = Event.query.filter(Event.performer_id.in_(matched_ids)) \
            .order_by(Event.starts_at).limit(40).all()
        seen = {e.id for e in events}
        events += [e for e in extra if e.id not in seen]
    return render_template("search.html", q=q, performers=performers,
                           events=events, event_card=event_card)


@app.route("/secure/search/getSuggestedSearches", methods=["GET", "POST"])
def search_suggestions():
    q = (request.args.get("q") or request.form.get("q") or "").strip()
    out = []
    if q:
        performers = scored_search(q, Performer.query.all(), ("name", "slug"))[:6]
        for p in performers:
            out.append({"type": "performer", "name": p.name,
                        "url": f"/{p.slug}-tickets/performer/{p.upstream_id}"})
    return jsonify(out)


# ---------------------------------------------------------------------------
# Event page (listings + seat map)
# ---------------------------------------------------------------------------

SORTS = {"recommended": "Recommended", "price": "Price", "best_deal": "Best deal",
         "best_view": "Best view"}
FEATURE_OPTIONS = ["Instant download", "Clear view", "Aisle seat", "Club access",
                   "Parking included", "Wheelchair accessible"]

_SEATMAP_CACHE = {}


def _seatmap_svg(venue):
    """Inline-renderable seat-map markup for a venue, or None.

    The captured upstream seat maps are JS-driven sprite sheets: the root
    <svg> is a 0x0 <defs> wrapper and the paintable geometry lives in the
    <g id="map-def" viewBox="..."> group. Extract that group and re-wrap it
    in a properly sized <svg> so the event page renders the real venue map
    (the previous template assumed inline-ready markup and printed the file
    path as literal text)."""
    if not venue or not venue.seatmap_file:
        return None
    cached = _SEATMAP_CACHE.get(venue.id)
    if cached is not None:
        return cached
    path = resolve_asset(f"/static/images/seatmaps/{venue.upstream_id}.svg")
    if not path:
        return None
    try:
        data = Path(BASE_DIR, path.lstrip("/")).read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r'<g\s+id="map-def"\s+viewBox="([^"]+)"', data)
    if not m:
        return None
    depth = 0
    inner = None
    for t in re.finditer(r"<g\b|</g>", data[m.start():]):
        depth += 1 if t.group(0).startswith("<g") else -1
        if depth == 0:
            inner = data[m.end():m.start() + t.start()]
            break
    if inner is None:
        return None
    markup = (f'<svg class="seatmap-svg" xmlns="http://www.w3.org/2000/svg" '
              f'viewBox="{m.group(1)}" role="img" '
              f'aria-label="{escape(venue.name)} seat map">{inner}</svg>')
    _SEATMAP_CACHE[venue.id] = markup
    return markup


def _sort_listings(items, sort):
    if sort == "price":
        return sorted(items, key=lambda l: (l.price, l.section))
    if sort == "best_deal":
        def deal(l):
            return (l.original_price - l.price) if l.original_price else 0
        return sorted(items, key=lambda l: (-deal(l), l.price))
    if sort == "best_view":
        return sorted(items, key=lambda l: (-(l.deal_rating or 0), l.price))
    # recommended: sponsored first, then rating, then price
    return sorted(items, key=lambda l: (not l.is_sponsored, -(l.deal_rating or 0), l.price))


@app.route("/<path:slug>/event/<int:upstream_id>")
def event_page(slug, upstream_id):
    evt = Event.query.filter_by(upstream_id=upstream_id).first_or_404()
    if slug != evt.slug:
        return redirect(evt.url_path)

    quantity = request.args.get("quantity", type=int)
    price_min = parse_price(request.args.get("price_min"))
    price_max = parse_price(request.args.get("price_max"))
    sort = request.args.get("sort") if request.args.get("sort") in SORTS else "recommended"
    features = request.args.getlist("features")
    zone = request.args.get("zone")
    section = request.args.get("section")

    listings = [l for l in Listing.query.filter_by(event_id=evt.id, is_sold=False).all()
                if not l.seller_id or True]
    # quantity filter: listings that can satisfy the requested party size
    if quantity:
        listings = [l for l in listings if l.quantity >= quantity]
    if price_min is not None:
        listings = [l for l in listings if l.price >= price_min]
    if price_max is not None:
        listings = [l for l in listings if l.price <= price_max]
    if features:
        listings = [l for l in listings
                    if all(any(f == feat or f in feat for feat in l.feature_list)
                           for f in features)]
    if zone:
        listings = [l for l in listings if (l.zone or zone_for_section(l.section)) == zone]
    if section:
        listings = [l for l in listings if l.section.upper() == section.upper()]

    total_count = Listing.query.filter_by(event_id=evt.id, is_sold=False).count()
    listings = _sort_listings(listings, sort)
    shown = listings[:10]

    zones = sorted({(l.zone or zone_for_section(l.section)) for l in evt.listings
                    if not l.is_sold})
    seatmap = _seatmap_svg(evt.venue)
    is_fav = False
    if current_user.is_authenticated:
        is_fav = Favorite.query.filter_by(user_id=current_user.id,
                                           event_id=evt.id).first() is not None
    nearby = (Event.query.filter(Event.performer_id == evt.performer_id,
                                 Event.id != evt.id)
              .order_by(Event.starts_at).limit(4).all())
    return render_template(
        "event.html", evt=evt, listings=shown, total_count=total_count,
        shown_count=len(listings), quantity=quantity, price_min=price_min,
        price_max=price_max, sort=sort, sort_label=SORTS[sort], features=features,
        zone=zone, section=section, zones=zones, seatmap=seatmap,
        feature_options=FEATURE_OPTIONS, is_fav=is_fav, nearby=nearby,
        event_card=event_card)


@app.route("/<path:slug>/event/<int:upstream_id>/listing/<int:listing_id>")
def listing_detail(slug, upstream_id, listing_id):
    evt = Event.query.filter_by(upstream_id=upstream_id).first_or_404()
    if slug != evt.slug:
        return redirect(f"{evt.url_path}/listing/{listing_id}")
    listing = Listing.query.filter_by(id=listing_id, event_id=evt.id).first_or_404()
    if listing.is_sold:
        return redirect(evt.url_path)
    quantity = request.args.get("quantity", type=int) or min(listing.quantity, 2)
    return render_template("listing_detail.html", evt=evt, listing=listing,
                           quantity=quantity)


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------

def _checkout_fee_breakdown(listing, quantity, delivery):
    subtotal = listing.price * quantity
    delivery_fee = DELIVERY_FEES.get(delivery, 0.0)
    total = subtotal + delivery_fee + ORDER_PROCESSING_FEE
    return {"subtotal": subtotal, "delivery_fee": delivery_fee,
            "processing_fee": ORDER_PROCESSING_FEE, "total": round(total, 2)}


@app.route("/secure/checkout/start", methods=["POST"])
@login_required
def checkout_start():
    listing_id = request.form.get("listing_id", type=int)
    quantity = request.form.get("quantity", type=int)
    listing = Listing.query.get_or_404(listing_id)
    if listing.is_sold:
        flash("Those tickets are no longer available.", "error")
        return redirect(listing.event.url_path)
    quantity = max(1, min(quantity or 1, listing.quantity))
    session["checkout"] = {"listing_id": listing.id, "quantity": quantity}
    return redirect(url_for("checkout_review"))


@app.route("/secure/checkout/review", methods=["GET", "POST"])
@login_required
def checkout_review():
    co = session.get("checkout")
    if not co:
        return redirect(url_for("home"))
    listing = Listing.query.get_or_404(co["listing_id"])
    evt = listing.event
    if request.method == "POST":
        delivery = request.form.get("delivery")
        if delivery not in DELIVERY_FEES:
            flash("Choose a delivery method.", "error")
        else:
            co["delivery"] = delivery
            session["checkout"] = co
            return redirect(url_for("checkout_payment"))
    delivery = co.get("delivery", "instant")
    fees = _checkout_fee_breakdown(listing, co["quantity"], delivery)
    return render_template("checkout_review.html", evt=evt, listing=listing,
                           quantity=co["quantity"], fees=fees,
                           delivery=delivery, delivery_fees=DELIVERY_FEES)


@app.route("/secure/checkout/payment", methods=["GET", "POST"])
@login_required
def checkout_payment():
    co = session.get("checkout")
    if not co or "delivery" not in co:
        return redirect(url_for("home"))
    listing = Listing.query.get_or_404(co["listing_id"])
    evt = listing.event
    cards = PaymentCard.query.filter_by(user_id=current_user.id).all()
    if request.method == "POST":
        number = re.sub(r"\D", "", request.form.get("number") or "")
        card_id = request.form.get("card_id", type=int)
        if number:
            # The buyer filled the "Use a new card" form: the new card takes
            # precedence over any selected saved-card radio (upstream treats
            # the expanded form as the explicit choice). The first card a
            # buyer ever uses is kept on file; further cards are used for
            # this order only — wallet cards are managed on the payments
            # page.
            brand = (request.form.get("brand") or "Card").strip()
            holder = request.form.get("holder", "").strip()
            exp_month = request.form.get("exp_month", type=int)
            exp_year = request.form.get("exp_year", type=int)
            cvv = request.form.get("cvv", "").strip()
            if len(number) < 13 or len(number) > 19 or not number.isdigit():
                flash("Enter a valid card number.", "error")
            elif not exp_month or not 1 <= exp_month <= 12:
                flash("Enter a valid expiry month.", "error")
            elif not exp_year or (exp_year, exp_month) < (MIRROR_NOW.year, MIRROR_NOW.month):
                flash("Enter a valid expiry year.", "error")
            elif not re.fullmatch(r"\d{3}", cvv):
                flash("Enter a valid 3-digit security code.", "error")
            elif not holder:
                flash("Enter the name on the card.", "error")
            else:
                if not cards:
                    card = PaymentCard(user_id=current_user.id, brand=brand.title(),
                                       last4=number[-4:], holder=holder,
                                       exp_month=exp_month, exp_year=exp_year,
                                       is_default=True)
                    db.session.add(card)
                    db.session.flush()
                    co["card_id"] = card.id
                    co.pop("new_card", None)
                    db.session.commit()
                else:
                    co["new_card"] = {"brand": brand.title(),
                                      "last4": number[-4:], "holder": holder}
                    co.pop("card_id", None)
                session["checkout"] = co
                return redirect(url_for("checkout_confirm"))
        elif card_id:
            card = PaymentCard.query.filter_by(id=card_id,
                                               user_id=current_user.id).first()
            if not card:
                flash("Choose a valid card.", "error")
            else:
                co["card_id"] = card.id
                co.pop("new_card", None)
                session["checkout"] = co
                return redirect(url_for("checkout_confirm"))
        else:
            flash("Choose a payment method.", "error")
    fees = _checkout_fee_breakdown(listing, co["quantity"], co["delivery"])
    return render_template("checkout_payment.html", evt=evt, listing=listing,
                           quantity=co["quantity"], fees=fees, cards=cards)


def _checkout_card_label(co):
    """The payment label actually chosen for this checkout session."""
    card_id = co.get("card_id")
    if card_id:
        card = PaymentCard.query.get(card_id)
        if card:
            return f"{card.brand} ••••{card.last4}"
    new_card = co.get("new_card") or {}
    return f"{new_card.get('brand', 'Card')} ••••{new_card.get('last4', '')}"


@app.route("/secure/checkout/confirm", methods=["GET", "POST"])
@login_required
def checkout_confirm():
    co = session.get("checkout")
    if not co or ("card_id" not in co and "new_card" not in co):
        return redirect(url_for("home"))
    listing = Listing.query.get_or_404(co["listing_id"])
    evt = listing.event
    card_label = _checkout_card_label(co)
    fees = _checkout_fee_breakdown(listing, co["quantity"], co["delivery"])
    if request.method == "POST":
        if listing.is_sold:
            flash("Those tickets are no longer available.", "error")
            return redirect(evt.url_path)
        order = Order(order_number=_next_order_number(), user_id=current_user.id,
                      event_id=evt.id, listing_id=listing.id,
                      quantity=co["quantity"], unit_price=listing.price,
                      delivery_method=co["delivery"],
                      delivery_fee=fees["delivery_fee"],
                      processing_fee=fees["processing_fee"], total=fees["total"],
                      status="Confirmed", placed_at=MIRROR_NOW,
                      card_last4=card_label)
        listing.quantity -= co["quantity"]
        listing.is_sold = listing.quantity == 0
        db.session.add(order)
        db.session.add(Notification(user_id=current_user.id,
                                    body=f"Order confirmed: {evt.name} on {fmt_date_full(evt.local_starts_at)}.",
                                    created_at=MIRROR_NOW))
        db.session.commit()
        session.pop("checkout", None)
        return redirect(url_for("checkout_confirmation", order_number=order.order_number))
    return render_template("checkout_confirm.html", evt=evt, listing=listing,
                           quantity=co["quantity"], fees=fees, card_label=card_label,
                           delivery=co["delivery"])


def _next_order_number():
    # Deterministic-ish order numbers: mirror the upstream 8-9 digit style.
    last = Order.query.order_by(Order.id.desc()).first()
    base = 41800000 + (last.id if last else 0) * 7 + 1234
    return str(base + 13)


@app.route("/secure/checkout/confirmation/<order_number>")
@login_required
def checkout_confirmation(order_number):
    order = Order.query.filter_by(order_number=order_number,
                                  user_id=current_user.id).first_or_404()
    return render_template("checkout_confirmation.html", order=order)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/secure/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            target = request.args.get("next") or request.form.get("next")
            if target and target.startswith("/"):
                return redirect(target)
            return redirect(url_for("home"))
        flash("That email and password combination is incorrect.", "error")
    return render_template("login.html")


@app.route("/secure/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        display = request.form.get("display_name", "").strip() or email.split("@")[0]
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("Enter a valid email address.", "error")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        elif User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
        else:
            user = User(username=slugify(display) or f"user{int(datetime.now().timestamp())}",
                        email=email, display_name=display,
                        password_hash=bcrypt.generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("home"))
    return render_template("register.html")


@app.route("/secure/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))


@app.route("/explore")
def explore():
    """The all-events browse page (upstream /explore)."""
    page = max(1, request.args.get("page", 1, type=int))
    per_page = 30
    q = Event.query.filter(Event.listing_count > 0)
    total = q.count()
    events = q.order_by(Event.starts_at) \
        .offset((page - 1) * per_page).limit(per_page).all()
    return render_template("explore.html", events=events, total=total,
                           page=page, event_card=event_card)


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------

@app.route("/secure/myaccount")
@login_required
def account_home():
    orders = Order.query.filter_by(user_id=current_user.id) \
        .order_by(Order.placed_at.desc()).limit(5).all()
    listings = Listing.query.filter_by(seller_id=current_user.id, is_sold=False).count()
    sales = Sale.query.filter_by(user_id=current_user.id).count()
    return render_template("account_home.html", orders=orders, listings=listings,
                           sales=sales)


@app.route("/secure/myaccount/purchases")
@login_required
def account_purchases():
    orders = Order.query.filter_by(user_id=current_user.id) \
        .order_by(Order.placed_at.desc()).all()
    # Upstream lists gift-card purchases on the Orders page alongside ticket
    # orders, so "order history" covers both.
    gift_cards = GiftCardOrder.query.filter_by(user_id=current_user.id) \
        .order_by(GiftCardOrder.created_at.desc()).all()
    return render_template("purchases.html", orders=orders,
                           gift_cards=gift_cards)


@app.route("/secure/myaccount/purchases/<order_number>")
@login_required
def account_order_detail(order_number):
    order = Order.query.filter_by(order_number=order_number,
                                  user_id=current_user.id).first_or_404()
    return render_template("order_detail.html", order=order)


@app.route("/secure/myaccount/sales")
@login_required
def account_sales():
    sales = Sale.query.filter_by(user_id=current_user.id) \
        .order_by(Sale.sold_at.desc()).all()
    total = sum(s.payout or 0 for s in sales)
    return render_template("sales.html", sales=sales, total=total)


@app.route("/secure/myaccount/listings")
@login_required
def account_listings():
    mine = Listing.query.filter_by(seller_id=current_user.id, is_sold=False) \
        .order_by(Listing.created_at.desc()).all()
    return render_template("my_listings.html", listings=mine)


def _refresh_event_stats(evt):
    """Recompute listing_count / min_price / max_price from unsold rows."""
    rows = [l for l in Listing.query.filter_by(event_id=evt.id).all()
            if not l.is_sold]
    evt.listing_count = len(rows)
    if rows:
        evt.min_price = min(l.price for l in rows)
        evt.max_price = max(l.price for l in rows)
    else:
        evt.min_price = None
        evt.max_price = None


@app.route("/secure/myaccount/listings/<int:listing_id>/update", methods=["POST"])
@login_required
def account_listing_update(listing_id):
    listing = Listing.query.filter_by(id=listing_id, seller_id=current_user.id).first_or_404()
    action = request.form.get("action")
    if action == "delete":
        evt = listing.event
        db.session.delete(listing)
        db.session.flush()
        _refresh_event_stats(evt)
        db.session.commit()
        flash("Listing removed.", "success")
    elif action == "reprice":
        new_price = parse_price(request.form.get("price"))
        if not new_price or new_price <= 0:
            flash("Enter a valid price.", "error")
        else:
            listing.price = new_price
            _refresh_event_stats(listing.event)
            db.session.commit()
            flash(f"Price updated to {fmt_money(new_price)}.", "success")
    return redirect(url_for("account_listings"))


@app.route("/secure/myaccount/payments", methods=["GET", "POST"])
@login_required
def account_payments():
    if request.method == "POST":
        brand = (request.form.get("brand") or "Card").strip()
        number = re.sub(r"\D", "", request.form.get("number") or "")
        holder = request.form.get("holder", "").strip()
        exp_month = request.form.get("exp_month", type=int)
        exp_year = request.form.get("exp_year", type=int)
        cvv = request.form.get("cvv", "").strip()
        if len(number) < 13 or len(number) > 19 or not number.isdigit():
            flash("Enter a valid card number.", "error")
        elif not exp_month or not 1 <= exp_month <= 12 or not exp_year or (exp_year, exp_month) < (MIRROR_NOW.year, MIRROR_NOW.month):
            flash("Enter a valid expiry date.", "error")
        elif not re.fullmatch(r"\d{3}", cvv):
            flash("Enter a valid 3-digit security code.", "error")
        elif not holder:
            flash("Enter the name on the card.", "error")
        else:
            if PaymentCard.query.filter_by(user_id=current_user.id).count() == 0:
                is_default = True
            else:
                is_default = False
            db.session.add(PaymentCard(user_id=current_user.id, brand=brand.title(),
                                       last4=number[-4:], holder=holder,
                                       exp_month=exp_month, exp_year=exp_year,
                                       is_default=is_default))
            db.session.commit()
            flash(f"{brand.title()} ending in {number[-4:]} added.", "success")
        return redirect(url_for("account_payments"))
    cards = PaymentCard.query.filter_by(user_id=current_user.id).all()
    return render_template("payments.html", cards=cards)


@app.route("/secure/myaccount/payments/<int:card_id>/default", methods=["POST"])
@login_required
def account_card_default(card_id):
    card = PaymentCard.query.filter_by(id=card_id, user_id=current_user.id).first_or_404()
    for c in PaymentCard.query.filter_by(user_id=current_user.id).all():
        c.is_default = (c.id == card_id)
    db.session.commit()
    flash(f"{card.brand} ending in {card.last4} is now your default card.", "success")
    return redirect(url_for("account_payments"))


@app.route("/secure/myaccount/payments/<int:card_id>/remove", methods=["POST"])
@login_required
def account_card_remove(card_id):
    card = PaymentCard.query.filter_by(id=card_id, user_id=current_user.id).first_or_404()
    was_default = card.is_default
    db.session.delete(card)
    db.session.commit()
    if was_default:
        first = PaymentCard.query.filter_by(user_id=current_user.id).first()
        if first:
            first.is_default = True
            db.session.commit()
    flash("Card removed.", "success")
    return redirect(url_for("account_payments"))


# ---------------------------------------------------------------------------
# Selling
# ---------------------------------------------------------------------------

@app.route("/selltickets")
def sell_landing():
    q = (request.args.get("q") or "").strip()
    results = []
    if q:
        results = scored_search(q, Event.query.order_by(Event.starts_at).all(), ("name",))[:20]
    return render_template("sell_landing.html", q=q, results=results,
                           event_card=event_card)


@app.route("/selltickets/event/<int:upstream_id>", methods=["GET", "POST"])
@login_required
def sell_create(upstream_id):
    evt = Event.query.filter_by(upstream_id=upstream_id).first_or_404()
    if request.method == "POST":
        section = request.form.get("section", "").strip()
        row = request.form.get("row", "").strip()
        seats = request.form.get("seats", "").strip()
        quantity = request.form.get("quantity", type=int)
        price = parse_price(request.form.get("price"))
        if not section:
            flash("Enter the section.", "error")
        elif not quantity or not 1 <= quantity <= 20:
            flash("Enter a quantity between 1 and 20.", "error")
        elif not price or price < 5:
            flash("Enter a price per ticket of at least $5.", "error")
        else:
            listing = Listing(upstream_id=None, event_id=evt.id, section=section,
                              zone=zone_for_section(section), row=row or None,
                              seats=seats or None, quantity=quantity, price=price,
                              features=json.dumps(["2 tickets together"] if quantity > 1 else []),
                              badges="[]", seller_id=current_user.id,
                              created_at=MIRROR_NOW)
            db.session.add(listing)
            # autoflush already includes the new row in the count below —
            # no +1 (that double-counted every new listing)
            _refresh_event_stats(evt)
            db.session.commit()
            flash(f"Listing created: {quantity} tickets in {section} for {fmt_money(price)} each.", "success")
            return redirect(url_for("account_listings"))
    sections = json.loads(evt.venue.sections) if evt.venue and evt.venue.sections else []
    return render_template("sell_create.html", evt=evt, sections=sections)


# ---------------------------------------------------------------------------
# Favorites
# ---------------------------------------------------------------------------

@app.route("/favorites")
@login_required
def favorites():
    favs = Favorite.query.filter_by(user_id=current_user.id) \
        .order_by(Favorite.created_at.desc()).all()
    return render_template("favorites.html", favorites=favs)


@app.route("/favorite/performer/<int:upstream_id>", methods=["POST"])
@login_required
def favorite_performer(upstream_id):
    performer = Performer.query.filter_by(upstream_id=upstream_id).first_or_404()
    fav = Favorite.query.filter_by(user_id=current_user.id,
                                    performer_id=performer.id).first()
    if fav:
        db.session.delete(fav)
        db.session.commit()
        flash(f"Unfollowed {performer.name}.", "success")
    else:
        db.session.add(Favorite(user_id=current_user.id, performer_id=performer.id,
                                created_at=MIRROR_NOW))
        performer.followers += 1
        db.session.commit()
        flash(f"Following {performer.name}.", "success")
    return redirect(request.form.get("next") or f"/{performer.slug}-tickets/performer/{performer.upstream_id}")


@app.route("/favorite/event/<int:upstream_id>", methods=["POST"])
@login_required
def favorite_event(upstream_id):
    evt = Event.query.filter_by(upstream_id=upstream_id).first_or_404()
    fav = Favorite.query.filter_by(user_id=current_user.id, event_id=evt.id).first()
    if fav:
        db.session.delete(fav)
        db.session.commit()
        flash("Removed from favorites.", "success")
    else:
        db.session.add(Favorite(user_id=current_user.id, event_id=evt.id,
                                created_at=MIRROR_NOW))
        db.session.commit()
        flash("Added to favorites.", "success")
    return redirect(request.form.get("next") or evt.url_path)


# ---------------------------------------------------------------------------
# Gift cards
# ---------------------------------------------------------------------------

GIFT_AMOUNTS = [25, 50, 75, 100, 150, 200, 250, 500]
GIFT_DESIGNS = ["classic", "birthday", "holiday", "sports", "concert"]


@app.route("/gift-cards")
def gift_cards():
    orders = []
    if current_user.is_authenticated:
        orders = GiftCardOrder.query.filter_by(user_id=current_user.id) \
            .order_by(GiftCardOrder.created_at.desc()).all()
    return render_template("gift_cards.html", amounts=GIFT_AMOUNTS,
                           designs=GIFT_DESIGNS, orders=orders)


@app.route("/gift-cards/purchase", methods=["POST"])
@login_required
def gift_card_purchase():
    try:
        amount = int(request.form.get("amount"))
    except (TypeError, ValueError):
        amount = 0
    recipient_name = request.form.get("recipient_name", "").strip()
    recipient_email = request.form.get("recipient_email", "").strip()
    message = request.form.get("message", "").strip()
    design = request.form.get("design") or "classic"
    if amount not in GIFT_AMOUNTS:
        flash("Choose a gift card amount.", "error")
    elif not recipient_name or not recipient_email:
        flash("Enter the recipient's name and email.", "error")
    elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", recipient_email):
        flash("Enter a valid recipient email.", "error")
    else:
        code = _gift_code()
        db.session.add(GiftCardOrder(user_id=current_user.id, amount=amount,
                                     recipient_name=recipient_name,
                                     recipient_email=recipient_email,
                                     message=message or None, design=design,
                                     code=code, created_at=MIRROR_NOW))
        db.session.commit()
        flash(f"Your ${amount} gift card for {recipient_name} is on its way to {recipient_email}.", "success")
    return redirect(url_for("gift_cards"))


def _gift_code():
    rng = random.Random(os.urandom(8))
    return "SH" + "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(10))


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Footer destination pages (audit fix: the footer's Our Company / Have
# Questions links previously 404'd; each now serves a real page).
# ---------------------------------------------------------------------------

STATIC_PAGES = {
    "about": {
        "title": "About StubHub",
        "paragraphs": [
            "StubHub is the world's top destination for ticket buyers and resellers. "
            "Fans come to StubHub to buy and sell sports, concert and theater tickets, "
            "with customer service all the way to their seat and every order 100% "
            "guaranteed.",
            "Prices are set by sellers and may be above face value. You are buying "
            "tickets from a third party; StubHub is not the ticket seller.",
        ],
    },
    "opendistribution": {
        "title": "Open Distribution",
        "paragraphs": [
            "StubHub's open distribution program lets ticketing partners list their "
            "inventory on the StubHub marketplace, connecting their events with the "
            "fans searching for them every day.",
            "Partners keep control of their inventory and pricing while reaching one "
            "of the largest audiences of live-event buyers on the web.",
        ],
    },
    "affiliates": {
        "title": "Affiliate Program",
        "paragraphs": [
            "The StubHub affiliate program rewards publishers and content creators "
            "for sending fans to the events they cover.",
            "Affiliates earn a commission on qualifying ticket orders that start "
            "from their links, with access to banners, feeds and reporting for the "
            "events their audiences care about.",
        ],
    },
    "careers": {
        "title": "Careers at StubHub",
        "paragraphs": [
            "StubHub teams build the marketplace that connects fans with the live "
            "events they love, from engineering and data science to customer "
            "operations and trust & safety.",
            "We're hiring across technology, operations and partner-facing teams. "
            "Explore the current openings to find your seat.",
        ],
    },
    "helpCenter": {
        "title": "Help Center",
        "paragraphs": [
            "StubHub's FanProtect guarantee covers every order: valid tickets, on "
            "time, or we'll make it right.",
            "Browse the help topics below for the fastest answers, or head straight "
            "to your account to track an order, manage listings or update payment "
            "cards.",
        ],
        "bullets": [
            "Track an order or view your receipts under My Tickets, then Orders.",
            "Manage or reprice the tickets you're selling under My Listings.",
            "Add, remove or change your default payment card under Payments.",
            "Buy a gift card for friends and family from the Gift Cards page.",
        ],
    },
}


@app.route("/<string:page_key>")
def static_page(page_key):
    page = STATIC_PAGES.get(page_key)
    if page is None:
        from flask import abort
        abort(404)
    return render_template("static_page.html", page=page)


@app.route("/_health")
def health():
    try:
        events = Event.query.count()
        listings = Listing.query.count()
        performers = Performer.query.count()
        venues = Venue.query.count()
        users = User.query.count()
        return {"ok": events > 0 and listings > 0 and performers > 0
                and venues > 0 and users >= 4,
                "site": "stubhub", "events": events,
                "listings": listings, "performers": performers,
                "venues": venues, "users": users}
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "error": str(exc)}, 500


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

with app.app_context():
    db.create_all()
    from seed_data import seed_database, seed_benchmark_users
    seed_database()
    seed_benchmark_users()
