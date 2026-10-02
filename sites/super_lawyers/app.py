"""Super Lawyers (superlawyers.com) mirror — Flask application.

Mirrors https://superlawyers.com/ as served on 2026-09-26: the consumer
homepage (hero lawyer search, Why Super Lawyers, legal-issue cards,
resources + Ask a Lawyer promos), the attorney directory
(attorneys.superlawyers.com: national practice pages, state pages, city
pages, and the practice-area x city SERP with lawyer cards, court
locations, nearby cities, related practice areas, FAQ accordions),
lawyer + firm profile pages (profiles.superlawyers.com: About /
Practice areas with percentage breakdown + pie chart / Achievements /
Map / Selections / contact form), the Top Lists section, the legal
article resources hub with topic overviews and articles, the Ask a
Lawyer Q&A, attorney feature articles, the about/selection-process
pages, and the Lawyer-login account area (favorites, saved searches,
contact inquiries).

All runtime data lives in instance/super_lawyers.db (see seed_data.py,
which loads the tracked source_data/ snapshots captured from the live
site). Heavy imagery lives under static/images/ (HF-managed bundle).
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime

from flask import (Flask, abort, flash, redirect, render_template, request,
                   url_for)
from flask_bcrypt import Bcrypt
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from markupsafe import Markup
from sqlalchemy import Index

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "SUPER_LAWYERS_DB_PATH",
    f"sqlite:///{BASE_DIR}/instance/super_lawyers.db")
app.config["SECRET_KEY"] = "webharbor-super-lawyers-dev-key"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = ""

# The mirror pins "now" to the capture date so relative statements stay
# deterministic across resets.
MIRROR_NOW = datetime(2026, 9, 26, 12, 0)

STOP_WORDS = {
    "the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or",
    "is", "it", "by", "with", "from", "as", "that", "this", "are", "be",
    "was", "were", "how", "what", "which", "who", "when", "where", "why",
    "do", "does", "did", "can", "could", "should", "would", "will", "has",
    "have", "had", "my", "me", "i", "you", "your", "lawyer", "lawyers",
    "attorney", "attorneys", "law", "find",
}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=MIRROR_NOW)

    favorites = db.relationship("Favorite", backref="user",
                                cascade="all, delete-orphan",
                                order_by="Favorite.created_at.desc()")
    saved_searches = db.relationship("SavedSearch", backref="user",
                                     cascade="all, delete-orphan",
                                     order_by="SavedSearch.created_at.desc()")
    inquiries = db.relationship("Inquiry", backref="user",
                               cascade="all, delete-orphan",
                               order_by="Inquiry.created_at.desc()")

    def check_password(self, raw: str) -> bool:
        try:
            return bcrypt.check_password_hash(self.password_hash, raw)
        except Exception:  # noqa: BLE001
            return False

    # flask-login protocol
    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


class Favorite(db.Model):
    __tablename__ = "favorites"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    lawyer_uuid = db.Column(db.String(40), nullable=False)
    created_at = db.Column(db.DateTime, default=MIRROR_NOW)


class SavedSearch(db.Model):
    __tablename__ = "saved_searches"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    practice_slug = db.Column(db.String(120), nullable=False)
    city_slug = db.Column(db.String(120), nullable=False)
    state_slug = db.Column(db.String(120), nullable=False)
    label = db.Column(db.String(200), nullable=False)
    alerts = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=MIRROR_NOW)


class Inquiry(db.Model):
    __tablename__ = "inquiries"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    lawyer_uuid = db.Column(db.String(40), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=MIRROR_NOW)


class State(db.Model):
    __tablename__ = "states"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)


class City(db.Model):
    __tablename__ = "cities"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    state_slug = db.Column(db.String(80), nullable=False)
    __table_args__ = (Index("ix_cities_state_slug", "state_slug"),)


class PracticeArea(db.Model):
    __tablename__ = "practice_areas"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(160), unique=True, nullable=False)
    name = db.Column(db.String(160), nullable=False)


class Firm(db.Model):
    __tablename__ = "firms"
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(40), unique=True, nullable=False)
    slug = db.Column(db.String(240), nullable=False)
    name = db.Column(db.String(240), nullable=False)
    state_slug = db.Column(db.String(80), nullable=False)
    city_slug = db.Column(db.String(120), nullable=False)
    office_json = db.Column(db.Text, nullable=False, default="[]")
    phone = db.Column(db.String(60))
    map_path = db.Column(db.String(200))

    @property
    def office(self):
        return json.loads(self.office_json or "[]")


class Lawyer(db.Model):
    __tablename__ = "lawyers"
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(40), unique=True, nullable=False)
    slug = db.Column(db.String(240), nullable=False)
    name = db.Column(db.String(240), nullable=False)
    tagline = db.Column(db.String(400))
    photo_path = db.Column(db.String(200))
    card_photo_path = db.Column(db.String(200))
    top_photo_path = db.Column(db.String(200))
    phone = db.Column(db.String(60))
    state_slug = db.Column(db.String(80), nullable=False)
    city_slug = db.Column(db.String(120), nullable=False)
    firm_uuid = db.Column(db.String(40))
    side_practice_areas = db.Column(db.String(400))
    licensed_since = db.Column(db.String(20))
    education = db.Column(db.String(240))
    sl_years = db.Column(db.String(200))
    rs_years = db.Column(db.String(200))
    sl_years_count = db.Column(db.Integer, default=0)
    rs_years_count = db.Column(db.Integer, default=0)
    first_admitted = db.Column(db.String(120))
    professional_webpage = db.Column(db.String(400))
    languages_json = db.Column(db.Text, default="[]")
    about_json = db.Column(db.Text, default="[]")
    practice_areas_json = db.Column(db.Text, default="[]")
    focus_areas_json = db.Column(db.Text, default="[]")
    pa_breakdown_json = db.Column(db.Text, default="[]")
    honors_json = db.Column(db.Text, default="[]")
    office_json = db.Column(db.Text, default="[]")
    findlaw = db.Column(db.Boolean, default=False)
    lawinfo = db.Column(db.Boolean, default=False)
    online_links_json = db.Column(db.Text, default="[]")

    __table_args__ = (
        Index("ix_lawyers_state_city", "state_slug", "city_slug"),
        Index("ix_lawyers_name", "name"),
    )

    # ---- json field accessors -------------------------------------------
    def _j(self, field):
        try:
            value = json.loads(getattr(self, field) or "[]")
        except (ValueError, TypeError):
            return []
        return value if isinstance(value, list) else []

    @property
    def about(self):
        return self._j("about_json")

    @property
    def practice_areas(self):
        return self._j("practice_areas_json")

    @property
    def focus_areas(self):
        return self._j("focus_areas_json")

    @property
    def pa_breakdown(self):
        return self._j("pa_breakdown_json")

    @property
    def honors(self):
        return self._j("honors_json")

    @property
    def languages(self):
        return self._j("languages_json")

    @property
    def office(self):
        return self._j("office_json")

    @property
    def online_links(self):
        return self._j("online_links_json")

    @property
    def firm(self):
        return Firm.query.filter_by(uuid=self.firm_uuid).first() if self.firm_uuid else None

    @property
    def city(self):
        return City.query.filter_by(slug=self.city_slug,
                                    state_slug=self.state_slug).first()

    @property
    def state(self):
        return State.query.filter_by(slug=self.state_slug).first()

    def photo(self, variant="full"):
        attr = {"full": "photo_path", "card": "card_photo_path",
                "top": "top_photo_path"}[variant]
        return getattr(self, attr) or self.photo_path or PLACEHOLDER_HEADSHOT


class ListingEntry(db.Model):
    """A lawyer card on a (practice, state, city) SERP, upstream order."""
    __tablename__ = "listing_entries"
    id = db.Column(db.Integer, primary_key=True)
    practice_slug = db.Column(db.String(160), nullable=False)
    state_slug = db.Column(db.String(80), nullable=False)
    city_slug = db.Column(db.String(120), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    lawyer_uuid = db.Column(db.String(40), nullable=False)
    name = db.Column(db.String(240))
    city_line = db.Column(db.String(240))
    tagline = db.Column(db.String(400))
    phone = db.Column(db.String(60))
    firm_name = db.Column(db.String(240))
    sponsored = db.Column(db.Boolean, default=False)

    __table_args__ = (
        Index("ix_listing_combo", "practice_slug", "state_slug", "city_slug"),
    )


class Court(db.Model):
    __tablename__ = "courts"
    id = db.Column(db.Integer, primary_key=True)
    state_slug = db.Column(db.String(80), nullable=False)
    city_slug = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(240), nullable=False)
    line1 = db.Column(db.String(240), nullable=False)
    line2 = db.Column(db.String(240))
    phone = db.Column(db.String(60), nullable=False)
    website = db.Column(db.String(400))


class ListingMeta(db.Model):
    """Per-(practice, state, city) rails captured from the SERP."""
    __tablename__ = "listing_meta"
    id = db.Column(db.Integer, primary_key=True)
    practice_slug = db.Column(db.String(160), nullable=False)
    state_slug = db.Column(db.String(80), nullable=False)
    city_slug = db.Column(db.String(120), nullable=False)
    h1 = db.Column(db.String(300), nullable=False)
    intro_json = db.Column(db.Text, default="[]")
    faq_json = db.Column(db.Text, default="[]")
    nearby_json = db.Column(db.Text, default="[]")
    related_json = db.Column(db.Text, default="[]")

    __table_args__ = (
        Index("ix_listing_meta_combo", "practice_slug", "state_slug", "city_slug"),
    )

    def _j(self, field):
        try:
            value = json.loads(getattr(self, field) or "[]")
        except (ValueError, TypeError):
            return []
        return value if isinstance(value, list) else []

    @property
    def intro(self):
        return self._j("intro_json")

    @property
    def faq(self):
        return self._j("faq_json")

    @property
    def nearby(self):
        return self._j("nearby_json")

    @property
    def related(self):
        return self._j("related_json")


class TopList(db.Model):
    __tablename__ = "top_lists"
    id = db.Column(db.Integer, primary_key=True)
    state_slug = db.Column(db.String(80), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    slug = db.Column(db.String(300), nullable=False)
    year = db.Column(db.Integer, nullable=False)

    entries = db.relationship("TopListEntry", backref="top_list",
                              cascade="all, delete-orphan",
                              order_by="TopListEntry.position")


class TopListEntry(db.Model):
    __tablename__ = "top_list_entries"
    id = db.Column(db.Integer, primary_key=True)
    list_id = db.Column(db.Integer, db.ForeignKey("top_lists.id"), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    lawyer_uuid = db.Column(db.String(40), nullable=False)
    firm_name = db.Column(db.String(240))


class ResourceTopic(db.Model):
    __tablename__ = "resource_topics"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(160), unique=True, nullable=False)
    title = db.Column(db.String(300), nullable=False)
    blocks_json = db.Column(db.Text, default="[]")
    links_json = db.Column(db.Text, default="[]")

    @property
    def blocks(self):
        try:
            return json.loads(self.blocks_json or "[]")
        except (ValueError, TypeError):
            return []

    @property
    def links(self):
        try:
            return json.loads(self.links_json or "[]")
        except (ValueError, TypeError):
            return []


class ResourceArticle(db.Model):
    __tablename__ = "resource_articles"
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(400), unique=True, nullable=False)
    title = db.Column(db.String(400), nullable=False)
    topic_slug = db.Column(db.String(160), nullable=False)
    blocks_json = db.Column(db.Text, default="[]")

    @property
    def blocks(self):
        try:
            return json.loads(self.blocks_json or "[]")
        except (ValueError, TypeError):
            return []


class Answer(db.Model):
    __tablename__ = "answers"
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(40), unique=True, nullable=False)
    topic_slug = db.Column(db.String(160), nullable=False)
    state_slug = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(400), nullable=False)
    question = db.Column(db.String(600), nullable=False)
    asked_in = db.Column(db.String(160))
    asked_on = db.Column(db.String(80))
    last_answered_on = db.Column(db.String(80))
    answer_count = db.Column(db.Integer, default=1)
    answerer_name = db.Column(db.String(240))
    answerer_city = db.Column(db.String(160))
    answerer_firm = db.Column(db.String(240))
    answerer_phone = db.Column(db.String(60))
    answerer_profile_uuid = db.Column(db.String(40))
    answerer_photo_path = db.Column(db.String(200))
    body_json = db.Column(db.Text, default="[]")

    @property
    def body(self):
        try:
            return json.loads(self.body_json or "[]")
        except (ValueError, TypeError):
            return []

    @property
    def answerer(self):
        return Lawyer.query.filter_by(
            uuid=self.answerer_profile_uuid).first() if self.answerer_profile_uuid else None


class FeatureArticle(db.Model):
    __tablename__ = "feature_articles"
    id = db.Column(db.Integer, primary_key=True)
    state_slug = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(240), nullable=False)
    title = db.Column(db.String(400), nullable=False)
    subtitle = db.Column(db.String(400))
    blocks_json = db.Column(db.Text, default="[]")
    featured_json = db.Column(db.Text, default="[]")
    related_json = db.Column(db.Text, default="[]")

    __table_args__ = (Index("ix_feature_state_slug", "state_slug"),)

    @property
    def blocks(self):
        try:
            return json.loads(self.blocks_json or "[]")
        except (ValueError, TypeError):
            return []

    @property
    def featured_lawyers(self):
        try:
            return json.loads(self.featured_json or "[]")
        except (ValueError, TypeError):
            return []

    @property
    def related(self):
        try:
            return json.loads(self.related_json or "[]")
        except (ValueError, TypeError):
            return []


class StaticPage(db.Model):
    __tablename__ = "static_pages"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    title = db.Column(db.String(300), nullable=False)
    blocks_json = db.Column(db.Text, default="[]")

    @property
    def blocks(self):
        try:
            return json.loads(self.blocks_json or "[]")
        except (ValueError, TypeError):
            return []


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def tokenize(query: str) -> list[str]:
    tokens = [t.lower() for t in re.split(r"\W+", query or "")
              if t.lower() not in STOP_WORDS and len(t) > 1]
    return tokens


def scored_search(query: str, rows, fields):
    """Token-overlap scored search (never strict AND)."""
    tokens = tokenize(query)
    if not tokens:
        return rows[:60]
    scored = []
    for row in rows:
        text = " ".join(getattr(row, f, "") or "" for f in fields).lower()
        score = sum(1 for t in tokens if t in text)
        if score > 0:
            scored.append((score, row))
    scored.sort(key=lambda pair: (-pair[0], pair[1].id))
    return [row for _, row in scored[:60]]


def resolve_geo(slug: str):
    """A single directory segment is either a state or a practice area."""
    state = State.query.filter_by(slug=slug).first()
    if state:
        return ("state", state)
    practice = PracticeArea.query.filter_by(slug=slug).first()
    if practice:
        return ("practice", practice)
    return (None, None)


# Upstream serves this circled-headshot icon in the photo slot of any lawyer
# without a real headshot (verified in the captured upstream profile/list HTML:
# e.g. the 2026 WA Top 10 list and photo-less profiles.superlawyers.com pages).
PLACEHOLDER_HEADSHOT = "images/icon-headshot-circled.png"


def lawyer_by_uuid(uuid: str):
    return Lawyer.query.filter_by(uuid=uuid).first()


def city_display(city_slug: str, state_slug: str):
    city = City.query.filter_by(slug=city_slug, state_slug=state_slug).first()
    state = State.query.filter_by(slug=state_slug).first()
    if city and state:
        return f"{city.name}, {state.name}"
    return city_slug.replace("-", " ").title()


def state_abbr(state_slug: str) -> str:
    mapping = {
        "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
        "california": "CA", "colorado": "CO", "connecticut": "CT",
        "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI",
        "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
        "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
        "maryland": "MD", "massachusetts": "MA", "michigan": "MI",
        "minnesota": "MN", "mississippi": "MS", "missouri": "MO",
        "montana": "MT", "nebraska": "NE", "nevada": "NV",
        "new-hampshire": "NH", "new-jersey": "NJ", "new-mexico": "NM",
        "new-york": "NY", "north-carolina": "NC", "north-dakota": "ND",
        "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
        "pennsylvania": "PA", "rhode-island": "RI", "south-carolina": "SC",
        "south-dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
        "vermont": "VT", "virginia": "VA", "washington": "WA",
        "washington-dc": "DC", "west-virginia": "WV", "wisconsin": "WI",
        "wyoming": "WY",
    }
    return mapping.get(state_slug, "")


def prettify_city_slug(city_slug: str) -> str:
    """Human-readable city name from a slug ("ft-lauderdale" -> "Ft. Lauderdale")."""
    words = []
    for w in city_slug.replace("_", "-").split("-"):
        if not w:
            continue
        w = w.capitalize()
        if w.lower() in {"ft", "st"}:
            w += "."
        words.append(w)
    return " ".join(words)


def featured_city_line(city_slug: str, state_slug: str) -> str:
    """Office city line for an article's featured lawyer ("Greenwood Village, CO"),
    matching the upstream featured-lawyer card format."""
    city = City.query.filter_by(slug=city_slug, state_slug=state_slug).first()
    name = city.name if city else prettify_city_slug(city_slug)
    abbr = state_abbr(state_slug)
    return f"{name}, {abbr}" if abbr else name


def resolve_lawyer_img(uuid: str, suffix: str = "") -> str | None:
    """Resolve a lawyer's on-disk image variant (ext follows bytes)."""
    import glob
    for cand in sorted(glob.glob(os.path.join(
            BASE_DIR, "static", "images", "lawyers",
            f"{uuid}{suffix}.*"))):
        return os.path.relpath(cand, os.path.join(BASE_DIR, "static"))
    return None


app.add_template_global(resolve_lawyer_img, name="lawyer_img")
app.add_template_global(featured_city_line)


def all_states():
    return State.query.order_by(State.name).all()


app.add_template_global(lawyer_by_uuid)
app.add_template_global(state_abbr)
app.add_template_global(city_display)
app.add_template_global(all_states)


# ---------------------------------------------------------------------------
# Consumer site (www.superlawyers.com)
# ---------------------------------------------------------------------------

def _load_source_json(name):
    path = os.path.join(BASE_DIR, "source_data", name)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return []


def practice_categories():
    """The 19 upstream top-level practice categories with sub-practices."""
    return _load_source_json("practice_categories.json")


def toplist_regions():
    """The 40 upstream Top Lists regions (name + slug)."""
    return _load_source_json("toplist_regions.json")


def resource_categories():
    """The 37 upstream resource topic categories (name + slug)."""
    return _load_source_json("resource_categories.json")


app.add_template_global(practice_categories)
app.add_template_global(toplist_regions)
app.add_template_global(resource_categories)


@app.route("/")
def home():
    topics = ResourceTopic.query.order_by(ResourceTopic.title).all()
    # the two spotlight answers upstream features on both the consumer home
    # and the Ask a Lawyer hub (answering attorney headshots included)
    spotlight = Answer.query.filter(Answer.uuid.in_(
        ["5ab26a62-9cb6-11f0-a8f5-127149c488c1",
         "5a8bdfd7-9cb6-11f0-a8f5-127149c488c1"])) \
        .order_by(Answer.id).all()
    return render_template("index.html", topics=topics, spotlight=spotlight)


@app.route("/attorneys/")
def attorneys_home():
    top_cities = db.session.query(ListingEntry.city_slug, ListingEntry.state_slug) \
        .distinct().all()
    city_entries = []
    for city_slug, state_slug in top_cities:
        city_entries.append({
            "city": City.query.filter_by(slug=city_slug, state_slug=state_slug).first(),
            "city_slug": city_slug, "state_slug": state_slug,
            "count": ListingEntry.query.filter_by(city_slug=city_slug,
                                                  state_slug=state_slug).count(),
        })
    city_entries.sort(key=lambda e: (e["state_slug"], e["city_slug"]))
    states = State.query.order_by(State.name).all()
    return render_template("attorneys_home.html", city_entries=city_entries,
                           states=states,
                           categories=practice_categories())


@app.route("/attorneys/search/")
def attorney_search():
    q = request.args.get("q", "").strip()
    where = request.args.get("where", "").strip()
    # resolve the location
    state_slug = city_slug = None
    if where:
        for city in City.query.all():
            state = State.query.filter_by(slug=city.state_slug).first()
            hay = f"{city.name} {state.name if state else ''} {state_abbr(city.state_slug)}".lower()
            if where.lower().replace(",", " ").strip() in hay or \
                    all(t in hay for t in tokenize(where)):
                state_slug, city_slug = city.state_slug, city.slug
                break
    # resolve the practice area
    practice_slug = None
    if q:
        tokens = tokenize(q)
        best = None
        for pa in PracticeArea.query.all():
            text = f"{pa.name} {pa.slug.replace('-', ' ')}".lower()
            score = sum(1 for t in tokens if t in text)
            if score and (best is None or score > best[0]):
                best = (score, pa)
        if best:
            practice_slug = best[1].slug
    # upstream redirects recognized combos to the canonical SERP
    if practice_slug and state_slug and city_slug:
        return redirect(url_for("serp", practice_slug=practice_slug,
                                state_slug=state_slug, city_slug=city_slug))
    if practice_slug and not where:
        return redirect(url_for("directory_segment", slug=practice_slug))
    if practice_slug and state_slug and not city_slug:
        return redirect(url_for("directory_segment", slug=state_slug))
    # otherwise: scored lawyer search across the directory
    rows = Lawyer.query.order_by(Lawyer.id).all()
    results = scored_search(q or where, rows,
                            ["name", "side_practice_areas", "tagline"])
    return render_template("lawyer_search.html", q=q, where=where,
                           results=results)


@app.route("/attorneys/<slug>/")
def directory_segment(slug):
    kind, obj = resolve_geo(slug)
    if kind == "state":
        return state_page(obj)
    if kind == "practice":
        return practice_area(obj)
    abort(404)


def state_page(state):
    city_rows = City.query.filter_by(state_slug=state.slug) \
        .order_by(City.name).all()
    listed = {r[0] for r in db.session.query(ListingEntry.city_slug)
              .filter_by(state_slug=state.slug).distinct()}
    return render_template("state.html", state=state, city_rows=city_rows,
                           listed=listed)


def practice_area(practice):
    combos = db.session.query(
        ListingEntry.state_slug, ListingEntry.city_slug) \
        .filter_by(practice_slug=practice.slug).distinct().all()
    city_rows = []
    for state_slug, city_slug in combos:
        city = City.query.filter_by(slug=city_slug, state_slug=state_slug).first()
        if not city:
            continue
        city_rows.append({"city": city, "state_slug": state_slug})
    city_rows.sort(key=lambda r: (r["city"].name))
    states = State.query.order_by(State.name).all()
    return render_template("practice.html", practice=practice,
                           city_rows=city_rows, states=states)


@app.route("/attorneys/<state_slug>/<city_slug>/")
def city_page(state_slug, city_slug):
    city = City.query.filter_by(slug=city_slug, state_slug=state_slug).first()
    state = State.query.filter_by(slug=state_slug).first()
    if not city or not state:
        abort(404)
    practices = PracticeArea.query.order_by(PracticeArea.name).all()
    populated = {r[0] for r in db.session.query(ListingEntry.practice_slug)
                 .filter_by(state_slug=state_slug, city_slug=city_slug).distinct()}
    other_cities = City.query.filter(
        City.state_slug == state_slug, City.slug != city_slug) \
        .order_by(City.name).all()
    return render_template("city.html", city=city, state=state,
                           practices=practices, populated=populated,
                           other_cities=other_cities)


@app.route("/attorneys/<practice_slug>/<state_slug>/<city_slug>/")
def serp(practice_slug, state_slug, city_slug):
    practice = PracticeArea.query.filter_by(slug=practice_slug).first()
    state = State.query.filter_by(slug=state_slug).first()
    city = City.query.filter_by(slug=city_slug, state_slug=state_slug).first()
    if not practice or not state or not city:
        abort(404)
    meta = ListingMeta.query.filter_by(practice_slug=practice_slug,
                                       state_slug=state_slug,
                                       city_slug=city_slug).first()
    entries = ListingEntry.query.filter_by(
        practice_slug=practice_slug, state_slug=state_slug,
        city_slug=city_slug).order_by(ListingEntry.position).all()
    cards = []
    for entry in entries:
        lawyer = lawyer_by_uuid(entry.lawyer_uuid)
        if lawyer:
            cards.append({"entry": entry, "lawyer": lawyer})
    courts = Court.query.filter_by(state_slug=state_slug, city_slug=city_slug).all()
    return render_template("serp.html", practice=practice, state=state,
                           city=city, meta=meta, cards=cards, courts=courts)


# ---------------------------------------------------------------------------
# Profiles (profiles.superlawyers.com)
# ---------------------------------------------------------------------------

@app.route("/profiles/<state_slug>/<city_slug>/lawyer/<slug>/<uuid>.html")
def lawyer_profile(state_slug, city_slug, slug, uuid):
    lawyer = Lawyer.query.filter_by(uuid=uuid).first()
    if not lawyer or lawyer.slug != slug:
        abort(404)
    state = State.query.filter_by(slug=lawyer.state_slug).first()
    city = City.query.filter_by(slug=lawyer.city_slug,
                                state_slug=lawyer.state_slug).first()
    return render_template("lawyer_profile.html", lawyer=lawyer,
                           state=state, city=city)


@app.route("/profiles/<state_slug>/<city_slug>/lawfirm/<slug>/<uuid>.html")
def firm_profile(state_slug, city_slug, slug, uuid):
    firm = Firm.query.filter_by(uuid=uuid).first()
    if not firm or firm.slug != slug:
        abort(404)
    attorneys = [l for l in Lawyer.query.filter_by(firm_uuid=uuid)
                 .order_by(Lawyer.id).all()]
    return render_template("firm_profile.html", firm=firm, attorneys=attorneys)


@app.route("/profiles/contact/lawyer/<uuid>.html")
def contact_lawyer_page(uuid):
    lawyer = lawyer_by_uuid(uuid)
    if not lawyer:
        abort(404)
    return render_template("contact_lawyer.html", lawyer=lawyer)


@app.route("/profiles/contact/lawyer/<uuid>.html", methods=["POST"])
def contact_lawyer_submit(uuid):
    lawyer = lawyer_by_uuid(uuid)
    if not lawyer:
        abort(404)
    form = {k: request.form.get(k, "").strip() for k in
            ("first_name", "last_name", "email", "phone", "city",
             "state", "message")}
    errors = []
    for field in ("first_name", "last_name", "email", "phone", "city",
                  "state", "message"):
        if not form[field]:
            errors.append(field.replace("_", " "))
    if form["email"] and "@" not in form["email"]:
        errors.append("email")
    if errors:
        flash("Please fill in all required fields correctly.", "error")
        return render_template("contact_lawyer.html", lawyer=lawyer,
                               form=form, errors=errors), 400
    if current_user.is_authenticated:
        inquiry = Inquiry(user_id=current_user.id, lawyer_uuid=uuid,
                          first_name=form["first_name"],
                          last_name=form["last_name"], email=form["email"],
                          phone=form["phone"], city=form["city"],
                          state=form["state"], message=form["message"])
        db.session.add(inquiry)
        db.session.commit()
        flash("Your inquiry has been sent. Track it under My inquiries.",
              "success")
        return redirect(url_for("account_inquiries"))
    flash("Your inquiry has been sent to the attorney.", "success")
    return redirect(url_for("lawyer_profile",
                            state_slug=lawyer.state_slug,
                            city_slug=lawyer.city_slug,
                            slug=lawyer.slug, uuid=lawyer.uuid))


# ---------------------------------------------------------------------------
# Top Lists (www.superlawyers.com/top-lists/)
# ---------------------------------------------------------------------------

@app.route("/top-lists/")
def top_lists_hub():
    states = db.session.query(TopList.state_slug).distinct().all()
    state_rows = []
    for (slug,) in states:
        state = State.query.filter_by(slug=slug).first()
        if state:
            state_rows.append({"state": state,
                               "count": TopList.query.filter_by(state_slug=slug).count()})
    state_rows.sort(key=lambda r: r["state"].name)
    populated_slugs = {r["state"].slug for r in state_rows}
    top5 = TopList.query.filter(TopList.title.like("Top 5:%")) \
        .order_by(TopList.id).all()
    top10 = TopList.query.filter(TopList.title.like("Top 10:%")) \
        .order_by(TopList.id).all()
    women = TopList.query.filter(TopList.title.like("%Women%")) \
        .order_by(TopList.id).all()
    return render_template("top_lists_hub.html", states=state_rows,
                           top5=top5, top10=top10, women=women,
                           regions=toplist_regions(),
                           populated_slugs=populated_slugs)


@app.route("/top-lists/<state_slug>/")
def top_list_state(state_slug):
    state = State.query.filter_by(slug=state_slug).first()
    if not state:
        abort(404)
    lists = TopList.query.filter_by(state_slug=state_slug) \
        .order_by(TopList.id).all()
    return render_template("top_list_state.html", state=state, lists=lists)


@app.route("/top-lists/<state_slug>/<slug>/<hash_>/")
def top_list_detail(state_slug, slug, hash_):
    lst = TopList.query.filter_by(state_slug=state_slug, slug=slug).first()
    if not lst:
        abort(404)
    cards = []
    for entry in lst.entries:
        lawyer = lawyer_by_uuid(entry.lawyer_uuid)
        if lawyer:
            cards.append({"entry": entry, "lawyer": lawyer})
    state = State.query.filter_by(slug=state_slug).first()
    return render_template("top_list_detail.html", lst=lst, state=state,
                           cards=cards)


# ---------------------------------------------------------------------------
# Resources (www.superlawyers.com/resources/)
# ---------------------------------------------------------------------------

@app.route("/resources/")
def resources_hub():
    topics = ResourceTopic.query.order_by(ResourceTopic.title).all()
    topic_slugs = {t.slug for t in topics}
    return render_template("resources_hub.html", topics=topics,
                           topic_slugs=topic_slugs)


@app.route("/resources/search/")
def resources_search():
    q = request.args.get("q", "").strip()
    articles = ResourceArticle.query.order_by(ResourceArticle.id).all()
    results = scored_search(q, articles, ["title"]) if q else []
    return render_template("resources_search.html", q=q, results=results,
                           total=ResourceArticle.query.count())


@app.route("/resources/<path:article_path>/")
def resource_page(article_path):
    topic = ResourceTopic.query.filter_by(slug=article_path.rstrip("/")).first()
    if topic:
        related = ResourceArticle.query.filter_by(topic_slug=topic.slug) \
            .order_by(ResourceArticle.id).limit(6).all()
        return render_template("resource_topic.html", topic=topic,
                               related=related)
    article = ResourceArticle.query.filter_by(
        path=article_path.rstrip("/")).first()
    if not article:
        abort(404)
    siblings = ResourceArticle.query.filter_by(topic_slug=article.topic_slug) \
        .order_by(ResourceArticle.id).limit(6).all()
    topic = ResourceTopic.query.filter_by(slug=article.topic_slug).first()
    return render_template("resource_article.html", article=article,
                           topic=topic, siblings=siblings)


# ---------------------------------------------------------------------------
# Ask a Lawyer (answers.superlawyers.com)
# ---------------------------------------------------------------------------

@app.route("/answers/")
def answers_home():
    recent = Answer.query.order_by(Answer.id).limit(8).all()
    topics = PracticeArea.query.order_by(PracticeArea.name).all()
    answered_topics = {r[0] for r in db.session.query(Answer.topic_slug).distinct()}
    answered_states = {r[0] for r in db.session.query(Answer.state_slug).distinct()}
    spotlight = Answer.query.filter(Answer.uuid.in_(
        ["5ab26a62-9cb6-11f0-a8f5-127149c488c1",
         "5a8bdfd7-9cb6-11f0-a8f5-127149c488c1"])) \
        .order_by(Answer.id).all()
    return render_template("answers_home.html", recent=recent,
                           topics=topics, spotlight=spotlight,
                           answered_topics=answered_topics,
                           answered_states=answered_states)


@app.route("/answers/search/")
def answers_search():
    q = request.args.get("q", "").strip()
    rows = Answer.query.order_by(Answer.id).all()
    results = scored_search(q, rows, ["question"]) if q else []
    return render_template("answers_search.html", q=q, results=results)


@app.route("/answers/ask-a-question/")
def ask_question():
    return render_template("ask_question.html")


@app.route("/answers/<topic_slug>/")
def answers_topic(topic_slug):
    practice = PracticeArea.query.filter_by(slug=topic_slug).first()
    state = None if practice else State.query.filter_by(slug=topic_slug).first()
    if practice:
        rows = Answer.query.filter_by(topic_slug=topic_slug) \
            .order_by(Answer.id).all()
    elif state:
        rows = Answer.query.filter_by(state_slug=state.slug) \
            .order_by(Answer.id).all()
    else:
        rows = []
    return render_template("answers_topic.html", practice=practice,
                           state=state, topic_slug=topic_slug, answers=rows)


@app.route("/answers/<topic_slug>/<state_slug>/<slug>/<uuid>.html")
def answer_detail(topic_slug, state_slug, slug, uuid):
    answer = Answer.query.filter_by(uuid=uuid).first()
    if not answer or answer.slug != slug:
        abort(404)
    return render_template("answer_detail.html", answer=answer)


# ---------------------------------------------------------------------------
# Feature articles (www.superlawyers.com/articles/)
# ---------------------------------------------------------------------------

@app.route("/articles/")
def articles_hub():
    articles = FeatureArticle.query.filter(
        FeatureArticle.state_slug != "online-features") \
        .order_by(FeatureArticle.id).all()
    # the upstream hub rail shows four online exclusives; the remaining
    # online features stay reachable via related rails and search
    rail_slugs = ["without-remedy-is-it-a-right", "signed-sealed-expunged",
                  "dont-forget-digital-assets", "uneasy-rider"]
    online = FeatureArticle.query.filter(
        FeatureArticle.state_slug == "online-features",
        FeatureArticle.slug.in_(rail_slugs)).order_by(FeatureArticle.id).all()
    states = db.session.query(FeatureArticle.state_slug).distinct().all()
    state_rows = []
    for (slug,) in states:
        state = State.query.filter_by(slug=slug).first()
        if state:
            state_rows.append(state)
    state_rows.sort(key=lambda s: s.name)
    return render_template("articles_hub.html", articles=articles,
                           online=online, states=state_rows)


@app.route("/articles/<state_slug>/<slug>/")
def article_detail(state_slug, slug):
    article = FeatureArticle.query.filter_by(slug=slug,
                                             state_slug=state_slug).first()
    if not article:
        abort(404)
    others = FeatureArticle.query.filter(FeatureArticle.id != article.id) \
        .order_by(FeatureArticle.id).limit(4).all()
    # only link to articles actually mirrored in the DB; the harvested
    # related rails reference many pieces that were not captured
    existing = {(a.state_slug, a.slug)
                for a in FeatureArticle.query.with_entities(
                    FeatureArticle.state_slug, FeatureArticle.slug).all()}
    related = [r for r in article.related
               if (r.get('state'), r.get('slug')) in existing]
    return render_template("article_detail.html", article=article,
                           others=others, related=related)


@app.route("/articles/award-winning-editorial/")
def award_editorial():
    page = StaticPage.query.filter_by(key="for_lawyers").first()
    articles = FeatureArticle.query.order_by(FeatureArticle.id).all()
    return render_template("award_editorial.html", page=page,
                           articles=articles)


# ---------------------------------------------------------------------------
# Static pages
# ---------------------------------------------------------------------------

STATIC_ROUTES = {
    "about": "/about/",
    "selection_process": "/about/selection-process/",
    "attorney_faq": "/about/attorney-faq/",
    "for_lawyers": "/for-lawyers/",
    "digital_magazines": "/for-lawyers/digital-magazines/",
    "marketing_solutions": "/marketing-solutions/",
    "contact": "/contact.html",
}


@app.route("/about/")
@app.route("/about/selection-process/")
@app.route("/about/attorney-faq/")
@app.route("/for-lawyers/")
@app.route("/for-lawyers/digital-magazines/")
@app.route("/marketing-solutions/")
@app.route("/contact.html")
def static_site_page():
    key = {v: k for k, v in STATIC_ROUTES.items()}.get(request.path)
    page = StaticPage.query.filter_by(key=key).first()
    if not page:
        abort(404)
    return render_template("static_page.html", page=page)


# ---------------------------------------------------------------------------
# Account (my.superlawyers.com)
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("account"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip()
        display = request.form.get("display_name", "").strip()
        password = request.form.get("password", "")
        if not email or "@" not in email or not username or len(password) < 8:
            flash("Enter a valid email, username, and a password of at least "
                  "8 characters.", "error")
            return render_template("register.html"), 400
        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
            return render_template("register.html"), 400
        user = User(email=email, username=username,
                    display_name=display or username,
                    password_hash=bcrypt.generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("account"))
    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))


@app.route("/account")
@login_required
def account():
    favorites = Favorite.query.filter_by(user_id=current_user.id).all()
    searches = SavedSearch.query.filter_by(user_id=current_user.id).all()
    inquiries = Inquiry.query.filter_by(user_id=current_user.id).all()
    return render_template("account.html", favorites=favorites,
                           searches=searches, inquiries=inquiries)


@app.route("/account/favorites")
@login_required
def account_favorites():
    favorites = Favorite.query.filter_by(user_id=current_user.id) \
        .order_by(Favorite.created_at.desc()).all()
    rows = []
    for fav in favorites:
        lawyer = lawyer_by_uuid(fav.lawyer_uuid)
        if lawyer:
            rows.append({"fav": fav, "lawyer": lawyer})
    return render_template("account_favorites.html", rows=rows)


@app.route("/account/favorites/toggle/<uuid>", methods=["POST"])
@login_required
def toggle_favorite(uuid):
    lawyer = lawyer_by_uuid(uuid)
    if not lawyer:
        abort(404)
    existing = Favorite.query.filter_by(user_id=current_user.id,
                                         lawyer_uuid=uuid).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash("Removed from your saved attorneys.", "success")
    else:
        db.session.add(Favorite(user_id=current_user.id, lawyer_uuid=uuid))
        db.session.commit()
        flash("Attorney saved to your list.", "success")
    return redirect(request.form.get("next") or url_for("account_favorites"))


@app.route("/account/saved-searches")
@login_required
def account_saved_searches():
    searches = SavedSearch.query.filter_by(user_id=current_user.id) \
        .order_by(SavedSearch.created_at.desc()).all()
    return render_template("account_saved_searches.html", searches=searches)


@app.route("/account/saved-searches/create", methods=["POST"])
@login_required
def create_saved_search():
    practice_slug = request.form.get("practice_slug", "").strip()
    state_slug = request.form.get("state_slug", "").strip()
    city_slug = request.form.get("city_slug", "").strip()
    practice = PracticeArea.query.filter_by(slug=practice_slug).first()
    city = City.query.filter_by(slug=city_slug, state_slug=state_slug).first()
    if not practice or not city:
        flash("Choose a practice area and location first.", "error")
        return redirect(url_for("account_saved_searches"))
    label = f"{practice.name} in {city_display(city_slug, state_slug)}"
    db.session.add(SavedSearch(user_id=current_user.id,
                               practice_slug=practice_slug,
                               state_slug=state_slug, city_slug=city_slug,
                               label=label))
    db.session.commit()
    flash(f"Saved search created: {label}.", "success")
    return redirect(url_for("account_saved_searches"))


@app.route("/account/saved-searches/<int:sid>/delete", methods=["POST"])
@login_required
def delete_saved_search(sid):
    row = SavedSearch.query.filter_by(id=sid, user_id=current_user.id).first()
    if row:
        db.session.delete(row)
        db.session.commit()
        flash("Saved search removed.", "success")
    return redirect(url_for("account_saved_searches"))


@app.route("/account/inquiries")
@login_required
def account_inquiries():
    inquiries = Inquiry.query.filter_by(user_id=current_user.id) \
        .order_by(Inquiry.created_at.desc()).all()
    rows = []
    for inquiry in inquiries:
        lawyer = lawyer_by_uuid(inquiry.lawyer_uuid)
        if lawyer:
            rows.append({"inquiry": inquiry, "lawyer": lawyer})
    return render_template("account_inquiries.html", rows=rows)


@app.route("/account/profile", methods=["GET", "POST"])
@login_required
def account_profile():
    if request.method == "POST":
        display = request.form.get("display_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        if not display or not email or "@" not in email:
            flash("Enter a display name and a valid email.", "error")
            return redirect(url_for("account_profile"))
        current_user.display_name = display
        current_user.email = email
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("account_profile"))
    return render_template("account_profile.html")


# ---------------------------------------------------------------------------
# Health + errors
# ---------------------------------------------------------------------------

@app.route("/_health")
def health():
    try:
        return {"ok": True, "site": "super_lawyers",
                "counts": {
                    "lawyers": Lawyer.query.count(),
                    "firms": Firm.query.count(),
                    "listings": ListingEntry.query.count(),
                    "top_lists": TopList.query.count(),
                    "resource_topics": ResourceTopic.query.count(),
                    "resource_articles": ResourceArticle.query.count(),
                    "answers": Answer.query.count(),
                    "feature_articles": FeatureArticle.query.count(),
                    "users": User.query.count(),
                }}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}, 500


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

with app.app_context():
    db.create_all()
    import seed_data  # noqa: E402
    seed_data.db = db
    seed_data.seed_database()
    seed_data.seed_benchmark_users()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
