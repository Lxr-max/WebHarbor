#!/usr/bin/env python3
"""Student.com mirror — Flask application.

Mirrors www.student.com's new-era US system (TX/FL/GA/OH): the homepage with
state CTAs and carousels, state college finders, university search-result pages
with sort/filters/map and infinite scroll, city pages, property pages with the
enquiry flow, the profile domain (saved properties, recently viewed, my
inquiries), the budget calculator, per-city internship listings, search
autocomplete and the content pages. All catalog and content data is real,
captured from the upstream site (see source_data/ + provenance.json).
"""
import json
import os
import re
from datetime import datetime, timezone

from flask import (Flask, abort, jsonify, redirect, render_template, request,
                   session, url_for)
from flask_bcrypt import Bcrypt
from flask_login import (LoginManager, UserMixin, current_user, login_user,
                         logout_user)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = "webharbor-student-com-dev-key"
# Tests point the app at a scratch copy of the seed via STUDENT_COM_DB_PATH so
# stateful checks never touch the live worktree database.
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "STUDENT_COM_DB_PATH",
    f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'student_com.db')}")
if not str(app.config["SQLALCHEMY_DATABASE_URI"]).startswith("sqlite:///"):
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(app.config["SQLALCHEMY_DATABASE_URI"])
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# SQLite busy timeout: the threaded dev server serves concurrent reads while a
# write commits (its EXCLUSIVE phase can take seconds on slow overlayfs);
# readers otherwise 500 with 'database is locked' instead of waiting it out.
# 30s is ample: the wait ends the moment the commit's exclusive lock releases.
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"connect_args": {"timeout": 30}}

os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)

csrf = CSRFProtect(app)
app.config["WTF_CSRF_TIME_LIMIT"] = None
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "index"

app.jinja_env.filters["from_json"] = json.loads

# Deterministic reference date: upstream data was captured 2026-09-26 and all
# seeded dates (views, enquiries, bookmarks) are pinned relative to it.
MIRROR_REFERENCE_DATE = datetime(2026, 9, 26)

STATE_NAMES = {"tx": "Texas", "fl": "Florida", "ga": "Georgia", "oh": "Ohio"}
PROPERTY_TYPES = ["Apartment", "Student Community", "Dorm", "House"]
LABEL_TO_TYPE = {"Apartment": "Apartment", "Student Community": "PBSA",
                 "Dorm": "Dorm", "House": "House"}
TYPE_TO_LABEL = {v: k for k, v in LABEL_TO_TYPE.items()}

VIBE_LABELS = {
    "coffee-food": ("Coffee & food", "\u2615"),
    "artsy-cultural": ("Artsy & cultural", "\U0001f5bc"),
    "parks-greenery": ("Parks & greenery", "\U0001f333"),
    "outdoorsy-active": ("Outdoorsy & active", "\U0001f3c3"),
    "music-nightlife": ("Music & nightlife", "\U0001f3b8"),
    "hangouts-study-spots": ("Hangouts & study spots", "\U0001f4da"),
    "fun-entertainment": ("Fun & entertainment", "\U0001f3ae"),
}
NEIGHBOURHOOD_LABELS = {
    "quiet": ("Quiet area", "Peaceful streets, ideal for focused study"),
    "urban": ("Urban", "Downtown, walkable, lively all hours"),
    "great-shopping-essentials": ("Good shopping & grocery",
                                  "Supermarkets, shops, caf\u00e9s all nearby"),
    "social": ("Social", "Busy, friendly, student-heavy blocks"),
    "suburban": ("Suburban", "Quieter residential streets, more space"),
}

STOP_WORDS = {"the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or",
              "is", "it", "by", "with", "near", "me"}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(80), default="")
    last_name = db.Column(db.String(80), default="")
    phone = db.Column(db.String(40), default="")
    created_at = db.Column(db.DateTime, default=MIRROR_REFERENCE_DATE)

    @property
    def display_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


class University(db.Model):
    __tablename__ = "universities"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(180), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    state = db.Column(db.String(4), nullable=False, index=True)
    city_slug = db.Column(db.String(80), nullable=False, index=True)
    has_properties = db.Column(db.Boolean, default=False)
    total_properties = db.Column(db.Integer, default=0)
    aliases = db.Column(db.JSON)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)


class City(db.Model):
    __tablename__ = "cities"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    state = db.Column(db.String(4), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    headline = db.Column(db.Text)
    summary = db.Column(db.Text)
    hero = db.Column(db.String(300))
    meta_description = db.Column(db.Text)
    content = db.Column(db.JSON)


class Property(db.Model):
    __tablename__ = "properties"
    id = db.Column(db.Integer, primary_key=True)
    upstream_id = db.Column(db.String(64), unique=True, nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    city_slug = db.Column(db.String(80), nullable=False, index=True)
    state_slug = db.Column(db.String(4), nullable=False, index=True)
    address = db.Column(db.String(300))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    min_price = db.Column(db.Integer)
    max_price = db.Column(db.Integer)
    property_type = db.Column(db.String(40), default="Apartment", index=True)
    rating = db.Column(db.Float)
    user_rating_count = db.Column(db.Integer, default=0)
    wheelchair_accessible = db.Column(db.Boolean, default=False)
    contact_email = db.Column(db.String(255))
    phone_number = db.Column(db.String(60))
    website = db.Column(db.String(400))
    google_maps_url = db.Column(db.String(600))
    property_summary = db.Column(db.Text)
    reviews_summary = db.Column(db.Text)
    room_types = db.Column(db.JSON)
    room_details = db.Column(db.JSON)
    amenities = db.Column(db.JSON)
    vibes = db.Column(db.JSON)
    neighbourhood_tags = db.Column(db.JSON)
    office_hours = db.Column(db.JSON)
    is_featured = db.Column(db.Boolean, default=False)
    hide_contact = db.Column(db.Boolean, default=False)
    images = db.Column(db.JSON)
    reviews = db.Column(db.JSON)
    university_name = db.Column(db.String(200))
    university_slug = db.Column(db.String(180), index=True)

    @property
    def type_label(self):
        return TYPE_TO_LABEL.get(self.property_type, self.property_type)

    @property
    def primary_image(self):
        return (self.images or [{}])[0].get("path")

    def distance_to(self, uni_slug):
        row = (PropertyUniversity.query
               .filter_by(property_slug=self.slug, university_slug=uni_slug).first())
        return row.distance_miles if row else None

    def vibe_labels(self):
        return [VIBE_LABELS[v] for v in (self.vibes or []) if v in VIBE_LABELS]

    def neighbourhood_labels(self):
        return [NEIGHBOURHOOD_LABELS[t] for t in (self.neighbourhood_tags or [])
                if t in NEIGHBOURHOOD_LABELS]


class PropertyUniversity(db.Model):
    __tablename__ = "property_universities"
    id = db.Column(db.Integer, primary_key=True)
    property_slug = db.Column(db.String(200), nullable=False, index=True)
    university_slug = db.Column(db.String(180), nullable=False, index=True)
    distance_miles = db.Column(db.Float)
    property_index = db.Column(db.Integer)


class Job(db.Model):
    __tablename__ = "jobs"
    id = db.Column(db.Integer, primary_key=True)
    upstream_id = db.Column(db.String(64), unique=True, nullable=False)
    city_slug = db.Column(db.String(80), nullable=False, index=True)
    title = db.Column(db.String(300), nullable=False)
    company = db.Column(db.String(200))
    location = db.Column(db.String(300))
    type = db.Column(db.String(80))
    raw_type = db.Column(db.String(120))
    url = db.Column(db.String(600))
    posted_at = db.Column(db.String(20))


class Bookmark(db.Model):
    __tablename__ = "bookmarks"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    property_slug = db.Column(db.String(200), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=MIRROR_REFERENCE_DATE)


class Enquiry(db.Model):
    __tablename__ = "enquiries"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    property_slug = db.Column(db.String(200), nullable=False, index=True)
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    phone = db.Column(db.String(40))
    email = db.Column(db.String(255))
    message = db.Column(db.Text)
    marketing_consent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=MIRROR_REFERENCE_DATE)

    @property
    def reference(self):
        return f"INQ-{self.id:06d}"


class PropertyView(db.Model):
    __tablename__ = "property_views"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    session_key = db.Column(db.String(64), index=True)
    property_slug = db.Column(db.String(200), nullable=False, index=True)
    viewed_at = db.Column(db.DateTime, default=MIRROR_REFERENCE_DATE)


class NewsletterSignup(db.Model):
    __tablename__ = "newsletter_signups"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=MIRROR_REFERENCE_DATE)


class ContactMessage(db.Model):
    __tablename__ = "contact_messages"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160))
    email = db.Column(db.String(255))
    topic = db.Column(db.String(200))
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=MIRROR_REFERENCE_DATE)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def tokenize(query):
    return [t.lower() for t in re.split(r"[^a-z0-9']+", query.lower())
            if t and t not in STOP_WORDS and len(t) > 1]


def scored_search(query, items, fields):
    tokens = tokenize(query)
    if not tokens:
        return items
    results = []
    for item in items:
        text = " ".join(str(getattr(item, f) or "") for f in fields).lower()
        score = sum(1 for t in tokens if t in text)
        if score:
            results.append((item, score))
    results.sort(key=lambda pair: (-pair[1], getattr(pair[0], "name", "").lower()))
    return [r[0] for r in results]


def session_key():
    if "view_key" not in session:
        session["view_key"] = os.urandom(16).hex()
    return session["view_key"]


def record_view(prop):
    key = session_key()
    uid = current_user.id if current_user.is_authenticated else None
    recent = (PropertyView.query
              .filter(PropertyView.session_key == key)
              .order_by(PropertyView.viewed_at.desc(), PropertyView.id.desc())
              .limit(12).all())
    if recent and recent[0].property_slug == prop.slug:
        return
    db.session.add(PropertyView(user_id=uid, session_key=key, property_slug=prop.slug,
                                viewed_at=datetime.now(timezone.utc)))
    if uid is None:
        old = (PropertyView.query.filter(PropertyView.session_key == key)
               .order_by(PropertyView.viewed_at.desc(), PropertyView.id.desc())
               .offset(24).all())
        for row in old:
            db.session.delete(row)
    db.session.commit()


def recently_viewed(limit=8):
    key = session_key()
    uid = current_user.id if current_user.is_authenticated else None
    if uid is not None:
        rows = (PropertyView.query
                .filter((PropertyView.session_key == key) | (PropertyView.user_id == uid))
                .order_by(PropertyView.viewed_at.desc(), PropertyView.id.desc())
                .limit(60).all())
    else:
        rows = (PropertyView.query.filter_by(session_key=key)
                .order_by(PropertyView.viewed_at.desc(), PropertyView.id.desc())
                .limit(60).all())
    seen, out = set(), []
    for row in rows:
        if row.property_slug in seen:
            continue
        seen.add(row.property_slug)
        prop = Property.query.filter_by(slug=row.property_slug).first()
        if prop:
            out.append((prop, row.viewed_at))
        if len(out) >= limit:
            break
    return out


def city_by_slug(state, city):
    c = City.query.filter_by(slug=city, state=state).first()
    if c is None:
        abort(404)
    return c


def property_or_404(state, city, slug):
    prop = Property.query.filter_by(slug=slug).first()
    if prop is None or prop.state_slug != state or prop.city_slug != city:
        abort(404)
    return prop


def uni_or_404(state, city, slug):
    uni = University.query.filter_by(slug=slug).first()
    if uni is None or uni.state != state or uni.city_slug != city:
        abort(404)
    return uni


@app.context_processor
def inject_globals():
    return {
        "STATE_NAMES": STATE_NAMES,
        "states": sorted(STATE_NAMES.items()),
        "recently_viewed_props": recently_viewed(6),
        "is_bookmarked": lambda slug: (
            current_user.is_authenticated and
            Bookmark.query.filter_by(user_id=current_user.id, property_slug=slug).first()
            is not None),
    }


# ---------------------------------------------------------------------------
# Routes — homepage
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    carousel_cities = []
    for cs in ["houston", "atlanta"]:
        city = City.query.filter_by(slug=cs).first()
        if not city:
            continue
        props = (Property.query.filter_by(city_slug=cs)
                 .filter(Property.rating.isnot(None))
                 .order_by(Property.rating.desc()).limit(6).all())
        if props:
            carousel_cities.append({"city": city, "properties": props})
    cities = City.query.all()
    cities.sort(key=lambda c: -Property.query.filter_by(city_slug=c.slug).count())
    top_unis = (University.query.filter_by(has_properties=True)
                .order_by(University.total_properties.desc()).limit(12).all())
    stats = {
        "properties": Property.query.count(),
        "universities": University.query.count(),
        "cities": City.query.count(),
    }
    return render_template("index.html", carousel_cities=carousel_cities,
                           popular_cities=cities[:10], top_unis=top_unis, stats=stats)


# ---------------------------------------------------------------------------
# State college finder
# ---------------------------------------------------------------------------
@app.route("/us/<state>/u")
def state_finder(state):
    if state not in STATE_NAMES:
        abort(404)
    q = request.args.get("q", "").strip()
    unis = University.query.filter_by(state=state).order_by(University.name).all()
    if q:
        unis = scored_search(q, unis, ["name", "city_slug", "slug"])
        if len(unis) < 8:
            extra = [u for u in University.query.filter_by(state=state).all()
                     if u not in unis and any(q.lower() in (a or "").lower() for a in (u.aliases or []))]
            unis = unis + extra
    popular = [u for u in unis if u.has_properties][:8]
    return render_template("state_finder.html", state=state,
                           state_name=STATE_NAMES[state], unis=unis,
                           popular=popular, q=q)


# ---------------------------------------------------------------------------
# City page
# ---------------------------------------------------------------------------
@app.route("/us/<state>/<city>")
def city_page(state, city):
    c = city_by_slug(state, city)
    props = Property.query.filter_by(city_slug=city).all()
    featured = [p for p in props if p.is_featured or (p.rating or 0) >= 4.5]
    featured = sorted(featured, key=lambda p: -(p.rating or 0))[:6] or \
        sorted(props, key=lambda p: -(p.rating or 0))[:6]
    unis = University.query.filter_by(city_slug=city).order_by(University.name).all()
    jobs_count = Job.query.filter_by(city_slug=city).count()
    return render_template("city.html", city=c, properties=props, featured=featured,
                           unis=unis, jobs_count=jobs_count)


# ---------------------------------------------------------------------------
# University SRP
# ---------------------------------------------------------------------------
def srp_query(uni, sort, min_price, max_price, types):
    links = (PropertyUniversity.query.filter_by(university_slug=uni.slug)
             .order_by(PropertyUniversity.distance_miles).all())
    props = []
    for link in links:
        p = Property.query.filter_by(slug=link.property_slug).first()
        if p is None:
            continue
        if min_price and (p.min_price or 0) < min_price:
            continue
        if max_price and (p.min_price or 10**9) > max_price:
            continue
        if types and p.property_type not in types:
            continue
        props.append((p, link.distance_miles))
    keys = {"distance": lambda pair: pair[1],
            "rating": lambda pair: -(pair[0].rating or 0),
            "price_asc": lambda pair: pair[0].min_price or 10**9,
            "price_desc": lambda pair: -(pair[0].min_price or 0)}
    props.sort(key=keys.get(sort, keys["distance"]))
    return props


def serialize_card(prop, distance):
    return {"slug": prop.slug, "name": prop.name, "type": prop.type_label,
            "min_price": prop.min_price, "rating": prop.rating,
            "distance": round(distance, 2) if distance is not None else None,
            "image": prop.primary_image,
            "url": url_for("property_page", state=prop.state_slug,
                           city=prop.city_slug, slug=prop.slug)}


@app.route("/us/<state>/<city>/u/<uni>")
def university_srp(state, city, uni):
    u = uni_or_404(state, city, uni)
    sort = request.args.get("sort", "distance")
    if sort not in ("distance", "rating", "price_asc", "price_desc"):
        sort = "distance"
    min_price = request.args.get("min_price", type=int)
    max_price = request.args.get("max_price", type=int)
    ptype = request.args.get("type", "")
    selected = request.args.get("selectedProperty", "")
    types = [LABEL_TO_TYPE[t] for t in ptype.split(",") if t in LABEL_TO_TYPE] if ptype else []

    props = srp_query(u, sort, min_price, max_price, types)
    total_upstream = len(props)

    offset = request.args.get("offset", type=int)
    if offset is not None and request.args.get("format") == "json":
        page = props[offset:offset + 20]
        return jsonify({"count": len(props), "total": total_upstream,
                        "properties": [serialize_card(p, d) for p, d in page]})

    return render_template("university_srp.html", uni=u,
                           city=City.query.filter_by(slug=city).first(),
                           props=props[:20], total_upstream=total_upstream, sort=sort,
                           min_price=min_price, max_price=max_price,
                           type_filter=ptype, selected=selected,
                           property_types=PROPERTY_TYPES, total_matching=len(props))


# ---------------------------------------------------------------------------
# Property page
# ---------------------------------------------------------------------------
@app.route("/us/<state>/<city>/p/<slug>")
def property_page(state, city, slug):
    prop = property_or_404(state, city, slug)
    record_view(prop)
    uni = (University.query.filter_by(slug=prop.university_slug).first()
           if prop.university_slug else None)
    distances = (PropertyUniversity.query.filter_by(property_slug=prop.slug)
                 .order_by(PropertyUniversity.distance_miles).all())
    near_unis = []
    for d in distances:
        u2 = University.query.filter_by(slug=d.university_slug).first()
        if u2:
            near_unis.append({"uni": u2, "distance": d.distance_miles})
    similar = (Property.query.filter(Property.city_slug == city, Property.slug != prop.slug)
               .order_by(Property.rating.desc()).limit(4).all())
    jobs = Job.query.filter_by(city_slug=city).limit(3).all()
    jobs_count = Job.query.filter_by(city_slug=city).count()
    return render_template("property.html", prop=prop, uni=uni, near_unis=near_unis,
                           similar=similar, jobs=jobs, jobs_count=jobs_count)


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------
@app.route("/us/<state>/<city>/internships")
def city_jobs(state, city):
    c = city_by_slug(state, city)
    jtype = request.args.get("type", "")
    jobs = Job.query.filter_by(city_slug=city).order_by(Job.posted_at.desc()).all()
    if jtype:
        jobs = [j for j in jobs if (j.type or "").lower() == jtype.lower()]
    type_counts = {}
    for j in Job.query.filter_by(city_slug=city).all():
        label = j.type or "Other"
        type_counts[label] = type_counts.get(label, 0) + 1
    return render_template("jobs.html", city=c, jobs=jobs, jtype=jtype,
                           type_counts=type_counts)


@app.route("/jobs")
def jobs_home():
    groups = {}
    for j in Job.query.order_by(Job.posted_at.desc()).all():
        groups.setdefault(j.city_slug, []).append(j)
    cities = {c.slug: c for c in City.query.all()}
    return render_template("jobs_home.html", groups=groups, cities=cities)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
@app.route("/search/suggest")
def search_suggest():
    q = request.args.get("q", "").strip()
    tokens = tokenize(q)
    if not tokens:
        return jsonify({"results": []})
    ql = q.lower()

    def word_match(token, text):
        return any(w.startswith(token) for w in re.findall(r"[a-z0-9']+", text))

    results = []
    for c in City.query.all():
        text = f"{c.name} {c.slug}".lower()
        score = sum(1 for t in tokens if word_match(t, text))
        if score:
            tier = 0 if ql == c.name.lower() else (1 if ql in c.name.lower() else 2)
            results.append({"type": "city", "name": c.name, "slug": c.slug,
                            "state": c.state, "city": c.slug, "score": score, "tier": tier,
                            "label": f"{c.name}, {STATE_NAMES.get(c.state, c.state.title())}"})
    for u in University.query.all():
        names = [u.name.lower()] + [a.lower() for a in (u.aliases or [])]
        text = f"{u.name} {u.city_slug} {' '.join(u.aliases or [])}".lower()
        score = sum(1 for t in tokens if word_match(t, text))
        if score:
            tier = 0 if any(ql == n for n in names) else (1 if any(ql in n for n in names) else 2)
            results.append({"type": "university", "name": u.name, "slug": u.slug,
                            "state": u.state, "city": u.city_slug, "score": score, "tier": tier,
                            "label": f"{u.name}, {STATE_NAMES.get(u.state, u.state.title())}"})
    for p in Property.query.all():
        text = f"{p.name} {p.city_slug}".lower()
        score = sum(1 for t in tokens if word_match(t, text))
        if score:
            tier = 0 if ql == p.name.lower() else (1 if ql in p.name.lower() else 2)
            results.append({"type": "property", "name": p.name, "slug": p.slug,
                            "state": p.state_slug, "city": p.city_slug, "score": score, "tier": tier,
                            "label": f"{p.name}, {p.city_slug.replace('-', ' ').title()}"})

    def rank(r):
        return (r["tier"], -r["score"],
                0 if r["type"] == "city" else 1 if r["type"] == "university" else 2,
                len(r["name"]))
    results.sort(key=rank)
    seen, out = set(), []
    for r in results:
        if r["name"].lower() in seen:
            continue
        seen.add(r["name"].lower())
        out.append(r)
        if len(out) >= 10:
            break
    return jsonify({"results": out})


@app.route("/search")
def search_results():
    q = request.args.get("q", "").strip()
    cities = scored_search(q, City.query.all(), ["name", "slug"]) if q else []
    unis = scored_search(q, University.query.all(), ["name", "city_slug"]) if q else []
    if q and len(unis) < 8:
        alias_hits = [u for u in University.query.all()
                      if u not in unis and any(q.lower() in (a or "").lower() for a in (u.aliases or []))]
        unis = unis + alias_hits
    props = (scored_search(q, Property.query.all(), ["name", "address", "city_slug"])
             if q else [])
    return render_template("search_results.html", q=q, cities=cities[:6],
                           unis=unis[:8], properties=props[:12])


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
@app.route("/profile/bookmarks")
def profile_bookmarks():
    if not current_user.is_authenticated:
        return render_template("profile_login_required.html", page="Saved Properties")
    marks = (Bookmark.query.filter_by(user_id=current_user.id)
             .order_by(Bookmark.created_at.desc()).all())
    props = [Property.query.filter_by(slug=m.property_slug).first() for m in marks]
    return render_template("profile_bookmarks.html",
                           props=[p for p in props if p])


@app.route("/profile/history")
def profile_history():
    if not current_user.is_authenticated:
        return render_template("profile_login_required.html",
                               page="Recently Viewed Properties")
    uid = current_user.id
    rows = (PropertyView.query
            .filter((PropertyView.user_id == uid) | (PropertyView.session_key == session_key()))
            .order_by(PropertyView.viewed_at.desc(), PropertyView.id.desc()).limit(60).all())
    seen, props = set(), []
    for row in rows:
        if row.property_slug in seen:
            continue
        seen.add(row.property_slug)
        p = Property.query.filter_by(slug=row.property_slug).first()
        if p:
            props.append((p, row.viewed_at))
    return render_template("profile_history.html", props=props)


@app.route("/profile/inquiries")
def profile_inquiries():
    if not current_user.is_authenticated:
        return render_template("profile_login_required.html", page="My Inquiries")
    enquiries = (Enquiry.query.filter_by(user_id=current_user.id)
                 .order_by(Enquiry.created_at.desc(), Enquiry.id.desc()).all())
    rows = []
    for e in enquiries:
        rows.append({"enquiry": e,
                     "prop": Property.query.filter_by(slug=e.property_slug).first()})
    return render_template("profile_inquiries.html", rows=rows)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
@app.route("/auth/login", methods=["POST"])
def auth_login():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        return jsonify({"ok": False, "error": "Invalid email or password"}), 401
    login_user(user, remember=True)
    return jsonify({"ok": True, "name": user.display_name})


@app.route("/auth/register", methods=["POST"])
def auth_register():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    first = request.form.get("first_name", "").strip()
    last = request.form.get("last_name", "").strip()
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"ok": False, "error": "Invalid email address"}), 400
    if len(password) < 8:
        return jsonify({"ok": False,
                        "error": "Password must be at least 8 characters"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"ok": False,
                        "error": "An account with this email already exists"}), 400
    user = User(email=email,
                password_hash=bcrypt.generate_password_hash(password).decode(),
                first_name=first, last_name=last)
    db.session.add(user)
    db.session.commit()
    login_user(user, remember=True)
    return jsonify({"ok": True, "name": user.display_name})


@app.route("/auth/logout", methods=["POST"])
def auth_logout():
    logout_user()
    return jsonify({"ok": True})


@app.route("/auth/status")
def auth_status():
    if current_user.is_authenticated:
        return jsonify({"authenticated": True, "name": current_user.display_name,
                        "email": current_user.email})
    return jsonify({"authenticated": False})


# ---------------------------------------------------------------------------
# Interactions
# ---------------------------------------------------------------------------
@app.route("/property/<slug>/bookmark", methods=["POST"])
def toggle_bookmark(slug):
    if not current_user.is_authenticated:
        return jsonify({"ok": False, "error": "auth"}), 401
    prop = Property.query.filter_by(slug=slug).first()
    if prop is None:
        abort(404)
    mark = Bookmark.query.filter_by(user_id=current_user.id, property_slug=slug).first()
    if mark:
        db.session.delete(mark)
        db.session.commit()
        return jsonify({"ok": True, "bookmarked": False,
                        "count": Bookmark.query.filter_by(user_id=current_user.id).count()})
    db.session.add(Bookmark(user_id=current_user.id, property_slug=slug))
    db.session.commit()
    return jsonify({"ok": True, "bookmarked": True,
                    "count": Bookmark.query.filter_by(user_id=current_user.id).count()})


@app.route("/property/<slug>/enquiry", methods=["POST"])
def submit_enquiry(slug):
    if not current_user.is_authenticated:
        return jsonify({"ok": False, "error": "auth"}), 401
    prop = Property.query.filter_by(slug=slug).first()
    if prop is None:
        abort(404)
    first = request.form.get("first_name", "").strip()
    last = request.form.get("last_name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip().lower()
    message = request.form.get("message", "").strip()
    consent = request.form.get("marketing_consent") == "on"
    errors = {}
    if not first:
        errors["first_name"] = "First name is required"
    if not last:
        errors["last_name"] = "Last name is required"
    if not re.match(r"^\+?[\d\s().-]{7,}$", phone.replace("+", "")):
        errors["phone"] = "Phone number is required"
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        errors["email"] = "Invalid email address"
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    enquiry = Enquiry(user_id=current_user.id, property_slug=slug, first_name=first,
                      last_name=last, phone=phone, email=email, message=message,
                      marketing_consent=consent)
    db.session.add(enquiry)
    db.session.commit()
    return jsonify({"ok": True, "reference": enquiry.reference})


@app.route("/newsletter", methods=["POST"])
def newsletter():
    email = request.form.get("email", "").strip().lower()
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"ok": False, "error": "Invalid email address"}), 400
    db.session.add(NewsletterSignup(email=email))
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/contact", methods=["POST"])
def contact_submit():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    topic = request.form.get("topic", "").strip()
    message = request.form.get("message", "").strip()
    if not name or not re.match(r"[^@]+@[^@]+\.[^@]+", email) or not message:
        return jsonify({"ok": False,
                        "error": "Please fill in your name, a valid email and a message"}), 400
    db.session.add(ContactMessage(name=name, email=email, topic=topic, message=message))
    db.session.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Content pages
# ---------------------------------------------------------------------------
@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/how-it-works")
def how_it_works():
    return render_template("how_it_works.html")


@app.route("/contact")
def contact_page():
    return render_template("contact.html")


@app.route("/help")
def help_page():
    return render_template("help.html")


@app.route("/guides/avoid-scams-and-fraud")
def guide_scams():
    return render_template("guide_scams.html")


@app.route("/scholarships")
def scholarships():
    return render_template("scholarships.html")


@app.route("/list-your-property")
def list_your_property():
    return render_template("list_your_property.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/terms/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/budget-calculator")
def budget_calculator():
    unis = (University.query.filter_by(has_properties=True)
            .order_by(University.name).all())
    return render_template("budget_calculator.html", unis=unis)


# ---------------------------------------------------------------------------
# Legacy redirect + health + errors
# ---------------------------------------------------------------------------
@app.route("/us/<city>")
def legacy_city(city):
    state = db.session.scalar(db.select(City.state).where(City.slug == city))
    if state is None:
        abort(404)
    return redirect(f"/us/{state}/{city}", code=308)


@app.route("/sitemap.xml")
def sitemap():
    """XML sitemap of the public browseable pages (upstream serves one too;
    the footer links to it)."""
    urls = ["/"]
    for st in STATE_NAMES:
        urls.append(f"/us/{st}/u")
    for c in City.query.order_by(City.slug).all():
        urls.append(f"/us/{c.state}/{c.slug}")
        urls.append(f"/us/{c.state}/{c.slug}/internships")
    for u in University.query.filter_by(has_properties=True).order_by(University.slug).all():
        urls.append(f"/us/{u.state}/{u.city_slug}/u/{u.slug}")
    for p in Property.query.order_by(Property.slug).all():
        urls.append(f"/us/{p.state_slug}/{p.city_slug}/p/{p.slug}")
    for path in ("/jobs", "/about", "/how-it-works", "/contact", "/help",
                 "/guides/avoid-scams-and-fraud", "/scholarships",
                 "/list-your-property", "/terms", "/terms/privacy",
                 "/budget-calculator"):
        urls.append(path)
    body = "\n".join(f"<url><loc>{request.host_url.rstrip('/')}{x}</loc></url>"
                     for x in urls)
    xml = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           f'{body}\n</urlset>\n')
    return app.response_class(xml, mimetype="application/xml")


@app.route("/_health")
def health():
    counts = {
        "users": User.query.count(),
        "universities": University.query.count(),
        "cities": City.query.count(),
        "properties": Property.query.count(),
        "jobs": Job.query.count(),
        "bookmarks": Bookmark.query.count(),
        "enquiries": Enquiry.query.count(),
    }
    ok = (counts["properties"] > 400 and counts["universities"] > 250
          and counts["users"] >= 4)
    return jsonify({"ok": ok, "counts": counts}), 200 if ok else 503


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
def seed_database():
    if Property.query.count() > 0:
        return
    from seed_data import run_seed
    run_seed(db, University, City, Property, PropertyUniversity, Job)


def seed_benchmark_users():
    if User.query.filter_by(email="alice.j@test.com").first():
        return
    from seed_data import run_seed_users
    run_seed_users(db, User, Property, Bookmark, Enquiry, PropertyView)


with app.app_context():
    db.create_all()
    seed_database()
    seed_benchmark_users()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 40094))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)
