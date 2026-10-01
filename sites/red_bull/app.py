#!/usr/bin/env python3
"""red_bull — a WebHarbor mirror of https://www.redbull.com/ (us-en).

Flask + SQLite mirror of the Red Bull entertainment-media surface, built
from a frozen upstream capture (2026-09-30):

  - the Energy Drink catalog: 18 real products (the Original, Zero,
    Sugarfree and the Editions) with flavors, benefit blocks, ingredient
    cards (caffeine / taurine / B-group vitamins / sugars / water) and
    available can sizes, plus the product line pages
  - the Events calendar: 100 real events with discipline tags, statuses,
    dates, venues and countries; per-event Info / Schedule / FAQs tabs;
    the event-series hubs (Cliff Diving, King of the Air, Cerro Abajo,
    Hardline, Foam Wreckers) with their tour stops; and the registration
    flow for ticketed events (real upstream entry fees captured from
    participate.redbull.com)
  - Athletes: 60 real athlete profiles with facts panels (date of birth,
    birthplace, nationality, career start, disciplines) and bios
  - Films & Shows: the Red Bull TV catalog — 100 films and 100 shows
    (season/episode counts, per-episode listings for the shows that
    publish them)
  - Stories: 40 real editorial stories with full bodies
  - Shop: 200 real products from the Red Bull Shop US (Shopify) with
    vendors, categories, size variants, SKUs and prices, plus the
    cart -> checkout -> order flow

Benchmark accounts (Alice/Bob/Carol/Dana), their orders, registrations
and favorites are deterministic fixtures declared in provenance.json.
The SQLite seed is materialized deterministically at image build time
(PYTHONHASHSEED=0, frozen bcrypt benchmark password).
"""
import json
import os
import random
import re
import secrets
from datetime import date, datetime, timezone

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
app.config["SECRET_KEY"] = os.environ.get("RED_BULL_SECRET_KEY") or "webharbor-red-bull-dev-key"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'RED_BULL_DB_URI', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'red_bull.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'account_login'
login_manager.login_message = 'Please sign in to your Red Bull account.'
csrf = CSRFProtect(app)

# The mirror is a frozen snapshot of the upstream site taken 2026-09-30.
MIRROR_TODAY = date(2026, 9, 30)
SITE_NAME = "red_bull"
# bcrypt hash of 'TestPass123!' — frozen so the seed DB is byte-reproducible.
BENCHMARK_PASSWORD_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')

SOURCE = os.path.join(BASE_DIR, 'source_data')


def _load(name):
    with open(os.path.join(SOURCE, name), encoding='utf-8') as f:
        return json.load(f)


# ------------------------------------------------------------------ models --

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(160), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    display_name = db.Column(db.String(120), nullable=False)


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(160), nullable=False)
    line = db.Column(db.String(80), nullable=False)          # Original/Zero/Sugarfree/Editions
    flavor = db.Column(db.String(160))
    meta_description = db.Column(db.Text)
    flavor_text = db.Column(db.Text)
    benefits = db.Column(db.Text, nullable=False, default='[]')
    ingredients = db.Column(db.Text, nullable=False, default='[]')
    sizes = db.Column(db.Text, nullable=False, default='[]')
    can_image = db.Column(db.String(300))
    scene_image = db.Column(db.String(300))

    def benefits_list(self):
        return json.loads(self.benefits)

    def ingredients_list(self):
        return json.loads(self.ingredients)

    def sizes_list(self):
        return json.loads(self.sizes)

    def caffeine(self):
        m = re.search(r'contains (\d+) mg of caffeine', self.ingredients or '')
        return int(m.group(1)) if m else None

    def sugars(self):
        m = re.search(r'contains (\d+) g of sugars', self.ingredients or '')
        return int(m.group(1)) if m else None


class EventSeries(db.Model):
    __tablename__ = 'event_series'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(160), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    standfirst = db.Column(db.Text)
    description = db.Column(db.Text, nullable=False, default='[]')
    image = db.Column(db.String(300))

    def description_list(self):
        return json.loads(self.description)


class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    title = db.Column(db.String(250), nullable=False)
    standfirst = db.Column(db.Text)
    discipline = db.Column(db.String(80))
    status = db.Column(db.String(40), nullable=False, default='upcoming')
    start_date = db.Column(db.String(40))
    end_date = db.Column(db.String(40))
    venue = db.Column(db.String(250))
    city = db.Column(db.String(120))
    country = db.Column(db.String(120))
    country_code = db.Column(db.String(8))
    image = db.Column(db.String(300))
    hero_image = db.Column(db.String(300))
    description = db.Column(db.Text, nullable=False, default='[]')
    series_id = db.Column(db.Integer, db.ForeignKey('event_series.id'))
    is_tv_event = db.Column(db.Boolean, nullable=False, default=False)
    # registration / ticketing (captured from participate.redbull.com)
    reg_price = db.Column(db.Float)
    reg_currency = db.Column(db.String(8))
    reg_title = db.Column(db.String(250))
    reg_type_name = db.Column(db.String(250))

    series = db.relationship('EventSeries', backref='events')
    schedule_items = db.relationship('EventScheduleItem', backref='event',
                                     order_by='EventScheduleItem.position')
    faqs = db.relationship('EventFaq', backref='event',
                           order_by='EventFaq.position')

    def description_list(self):
        return json.loads(self.description)

    def start(self):
        try:
            return datetime.strptime(self.start_date[:10], '%Y-%m-%d').date()
        except (TypeError, ValueError):
            return None

    def end(self):
        try:
            return datetime.strptime(self.end_date[:10], '%Y-%m-%d').date()
        except (TypeError, ValueError):
            return None

    def date_range_text(self):
        s, e = self.start(), self.end()
        if not s:
            return ''
        if not e or s == e:
            return s.strftime('%B %-d, %Y')
        if s.year == e.year and s.month == e.month:
            return f"{s.strftime('%B %-d')} – {e.strftime('%-d, %Y')}"
        if s.year == e.year:
            return f"{s.strftime('%B %-d')} – {e.strftime('%B %-d, %Y')}"
        return f"{s.strftime('%B %-d, %Y')} – {e.strftime('%B %-d, %Y')}"

    def state(self):
        """Upcoming / past relative to the frozen mirror date."""
        s = self.end() or self.start()
        if s and s < MIRROR_TODAY:
            return 'past'
        return 'upcoming'

    def location_text(self):
        parts = [p for p in (self.venue, self.city, self.country) if p]
        return ', '.join(dict.fromkeys(parts))


class EventScheduleItem(db.Model):
    __tablename__ = 'event_schedule_items'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    text = db.Column(db.String(400), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)


class EventFaq(db.Model):
    __tablename__ = 'event_faqs'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)


class Athlete(db.Model):
    __tablename__ = 'athletes'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(160), unique=True, nullable=False)
    name = db.Column(db.String(160), nullable=False)
    standfirst = db.Column(db.Text)
    discipline = db.Column(db.String(200))
    dob = db.Column(db.String(80))
    birthplace = db.Column(db.String(160))
    age = db.Column(db.String(12))
    nationality = db.Column(db.String(120))
    career_start = db.Column(db.String(40))
    bio = db.Column(db.Text, nullable=False, default='[]')
    hero_image = db.Column(db.String(300))

    def bio_list(self):
        return json.loads(self.bio)


class Film(db.Model):
    __tablename__ = 'films'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    title = db.Column(db.String(250), nullable=False)
    subheading = db.Column(db.Text)
    standfirst = db.Column(db.Text)
    discipline = db.Column(db.String(80))
    published = db.Column(db.String(40))
    duration = db.Column(db.Integer)          # seconds
    image = db.Column(db.String(300))

    def duration_text(self):
        if not self.duration:
            return ''
        m, s = divmod(self.duration, 60)
        return f"{m} min"


class Show(db.Model):
    __tablename__ = 'shows'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    title = db.Column(db.String(250), nullable=False)
    subheading = db.Column(db.Text)
    standfirst = db.Column(db.Text)
    discipline = db.Column(db.String(80))
    nr_seasons = db.Column(db.Integer)
    nr_episodes = db.Column(db.Integer)
    image = db.Column(db.String(300))

    episodes = db.relationship('Episode', backref='show',
                               order_by='Episode.season, Episode.episode')


class Episode(db.Model):
    __tablename__ = 'episodes'
    id = db.Column(db.Integer, primary_key=True)
    show_id = db.Column(db.Integer, db.ForeignKey('shows.id'), nullable=False)
    title = db.Column(db.String(250), nullable=False)
    season = db.Column(db.Integer)
    episode = db.Column(db.Integer)
    standfirst = db.Column(db.Text)
    duration = db.Column(db.Integer)
    published = db.Column(db.String(40))

    def duration_text(self):
        if not self.duration:
            return ''
        m, s = divmod(self.duration, 60)
        return f"{m} min"


class Story(db.Model):
    __tablename__ = 'stories'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(220), unique=True, nullable=False)
    title = db.Column(db.String(300), nullable=False)
    standfirst = db.Column(db.Text)
    discipline = db.Column(db.String(80))
    published = db.Column(db.String(40))
    body = db.Column(db.Text, nullable=False, default='[]')
    hero_image = db.Column(db.String(300))

    def body_list(self):
        return json.loads(self.body)

    def published_date(self):
        try:
            return datetime.strptime(self.published[:10], '%Y-%m-%d').date()
        except (TypeError, ValueError):
            return None


class ShopProduct(db.Model):
    __tablename__ = 'shop_products'
    id = db.Column(db.Integer, primary_key=True)
    handle = db.Column(db.String(200), unique=True, nullable=False)
    title = db.Column(db.String(250), nullable=False)
    vendor = db.Column(db.String(160))
    product_type = db.Column(db.String(120))
    category = db.Column(db.String(80), nullable=False)
    tags = db.Column(db.Text, nullable=False, default='[]')
    description = db.Column(db.Text)
    image = db.Column(db.String(400))

    variants = db.relationship('ShopVariant', backref='product',
                               order_by='ShopVariant.id')

    def tags_list(self):
        return json.loads(self.tags)

    def price_range(self):
        prices = [v.price for v in self.variants if v.price is not None]
        if not prices:
            return None, None
        return min(prices), max(prices)


class ShopVariant(db.Model):
    __tablename__ = 'shop_variants'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('shop_products.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    option1 = db.Column(db.String(120))
    option2 = db.Column(db.String(120))
    price = db.Column(db.Float)
    sku = db.Column(db.String(80))
    available = db.Column(db.Boolean, nullable=False, default=True)


class CartItem(db.Model):
    __tablename__ = 'cart_items'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), nullable=False, index=True)   # session cart token
    variant_id = db.Column(db.Integer, db.ForeignKey('shop_variants.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    added_at = db.Column(db.String(40), nullable=False, default='')

    variant = db.relationship('ShopVariant')


class ShopOrder(db.Model):
    __tablename__ = 'shop_orders'
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(40), nullable=False, default='confirmed')
    placed_at = db.Column(db.String(40), nullable=False)
    total = db.Column(db.Float, nullable=False, default=0)
    ship_name = db.Column(db.String(160), nullable=False)
    ship_email = db.Column(db.String(160), nullable=False)

    lines = db.relationship('ShopOrderLine', backref='order')
    user = db.relationship('User')


class ShopOrderLine(db.Model):
    __tablename__ = 'shop_order_lines'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('shop_orders.id'), nullable=False)
    variant_id = db.Column(db.Integer, nullable=False)
    product_title = db.Column(db.String(250), nullable=False)
    variant_title = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.String(80))
    unit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)


class EventRegistration(db.Model):
    __tablename__ = 'event_registrations'
    id = db.Column(db.Integer, primary_key=True)
    registration_code = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    ticket_type = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False)
    price = db.Column(db.Float)
    currency = db.Column(db.String(8))
    status = db.Column(db.String(40), nullable=False, default='confirmed')
    created_at = db.Column(db.String(40), nullable=False)

    event = db.relationship('Event')
    user = db.relationship('User')


class Favorite(db.Model):
    __tablename__ = 'favorites'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    kind = db.Column(db.String(20), nullable=False)      # event/film/show/story/athlete
    item_slug = db.Column(db.String(220), nullable=False)

    user = db.relationship('User')


# ------------------------------------------------------------------- login --

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def _cart_token():
    token = session.get('cart_token')
    if not token:
        token = secrets.token_hex(16)
        session['cart_token'] = token
    return token


def _now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


# ------------------------------------------------------------------- views --

@app.route('/_health')
def health():
    return {
        "ok": True, "site": SITE_NAME,
        "users": User.query.count(),
        "products": Product.query.count(),
        "events": Event.query.count(),
        "event_series": EventSeries.query.count(),
        "event_faqs": EventFaq.query.count(),
        "event_schedule_items": EventScheduleItem.query.count(),
        "athletes": Athlete.query.count(),
        "films": Film.query.count(),
        "shows": Show.query.count(),
        "episodes": Episode.query.count(),
        "stories": Story.query.count(),
        "shop_products": ShopProduct.query.count(),
        "shop_variants": ShopVariant.query.count(),
        "shop_orders": ShopOrder.query.count(),
        "event_registrations": EventRegistration.query.count(),
        "favorites": Favorite.query.count(),
    }


NAV = [
    ("Energy Drinks", 'energydrink'),
    ("Events", 'events'),
    ("Athletes", 'athletes'),
    ("Films", 'films'),
    ("Shows", 'shows'),
    ("Stories", 'stories'),
    ("Shop", 'shop'),
]


@app.route('/')
def home():
    hero_story = Story.query.order_by(Story.published.desc()).first()
    stories = (Story.query.order_by(Story.published.desc())
               .offset(1).limit(6).all())
    products = Product.query.order_by(Product.id).all()
    upcoming = (Event.query.filter(Event.start_date >= MIRROR_TODAY.isoformat())
               .order_by(Event.start_date).limit(6).all())
    films = Film.query.order_by(Film.published.desc()).limit(6).all()
    return render_template('home.html', nav=NAV, hero_story=hero_story,
                           stories=stories, products=products,
                           upcoming=upcoming, films=films)


@app.route('/energydrink')
def energydrink():
    line = request.args.get('line', '')
    q = Product.query
    if line:
        q = q.filter(Product.line == line)
    products = q.order_by(Product.id).all()
    lines = sorted({p.line for p in Product.query.all()})
    return render_template('products.html', nav=NAV, products=products,
                           lines=lines, active_line=line)


@app.route('/energydrink/<slug>')
def product_detail(slug):
    product = Product.query.filter_by(slug=slug).first_or_404()
    related = Product.query.filter(Product.id != product.id).order_by(Product.id).limit(6).all()
    return render_template('product_detail.html', nav=NAV, product=product,
                           related=related)


@app.route('/events')
def events():
    discipline = request.args.get('discipline', '')
    country = request.args.get('country', '')
    status = request.args.get('status', '')
    page = max(int(request.args.get('page', 1) or 1), 1)
    per_page = 12
    q = Event.query
    if discipline:
        q = q.filter(Event.discipline == discipline)
    if country:
        q = q.filter(Event.country_code == country)
    events_all = q.order_by(Event.start_date).all()
    # upcoming first (soonest first), then past (most recent first) — the
    # same ordering the upstream calendar uses for its default view
    upcoming = [e for e in events_all if e.state() == 'upcoming']
    past = sorted([e for e in events_all if e.state() == 'past'],
                  key=lambda e: e.start_date or '', reverse=True)
    if status == 'upcoming':
        events_all = upcoming
    elif status == 'past':
        events_all = past
    else:
        events_all = upcoming + past
    total = len(events_all)
    page_items = events_all[(page - 1) * per_page: page * per_page]
    disciplines = sorted({d for d in (e.discipline for e in Event.query.all()) if d})
    countries_q = Event.query.filter(Event.country_code.isnot(None))
    countries = sorted({(e.country_code, e.country) for e in countries_q.all()},
                        key=lambda x: (x[1] or ''))
    return render_template('events.html', nav=NAV, events=page_items,
                           disciplines=disciplines, countries=countries,
                           active_discipline=discipline, active_country=country,
                           active_status=status, page=page, total=total,
                           per_page=per_page)


@app.route('/events/<slug>')
def event_detail(slug):
    event = Event.query.filter_by(slug=slug).first_or_404()
    related = Event.query.filter(Event.id != event.id)
    if event.discipline:
        related = related.filter(Event.discipline == event.discipline)
    related = related.order_by(Event.start_date).limit(4).all()
    stories = Story.query.filter_by(discipline=event.discipline).limit(3).all() \
        if event.discipline else []
    return render_template('event_detail.html', nav=NAV, event=event,
                           related=related, stories=stories)


@app.route('/events/<slug>/schedule')
def event_schedule(slug):
    event = Event.query.filter_by(slug=slug).first_or_404()
    return render_template('event_tab.html', nav=NAV, event=event,
                           tab='Schedule', items=event.schedule_items,
                           faqs=event.faqs)


@app.route('/events/<slug>/faqs')
def event_faqs(slug):
    event = Event.query.filter_by(slug=slug).first_or_404()
    return render_template('event_tab.html', nav=NAV, event=event,
                           tab='FAQs', items=event.schedule_items,
                           faqs=event.faqs)


@app.route('/events/<slug>/register', methods=['GET', 'POST'])
def event_register(slug):
    event = Event.query.filter_by(slug=slug).first_or_404()
    if not (event.reg_price is not None or event.reg_title or event.reg_type_name):
        abort(404)
    form = {}
    errors = []
    if request.method == 'POST':
        form = {k: request.form.get(k, '').strip() for k in
                ('first_name', 'last_name', 'email', 'ticket_type', 'shirt_size')}
        if not form['first_name'] or not form['last_name']:
            errors.append('Please provide both a first and last name.')
        if not re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", form['email'] or ''):
            errors.append('Please provide a valid email address.')
        if not form['ticket_type']:
            errors.append('Please choose a ticket type.')
        if not errors:
            code = 'RB' + secrets.token_hex(4).upper()
            reg = EventRegistration(
                registration_code=code,
                user_id=current_user.id if current_user.is_authenticated else None,
                event_id=event.id,
                ticket_type=form['ticket_type'],
                first_name=form['first_name'], last_name=form['last_name'],
                email=form['email'], price=event.reg_price,
                currency=event.reg_currency, status='confirmed',
                created_at=_now_iso())
            db.session.add(reg)
            db.session.commit()
            return redirect(url_for('event_registration_confirmation',
                                    slug=slug, code=code))
    return render_template('event_register.html', nav=NAV, event=event,
                           form=form, errors=errors)


@app.route('/events/<slug>/register/confirmation/<code>')
def event_registration_confirmation(slug, code):
    event = Event.query.filter_by(slug=slug).first_or_404()
    reg = EventRegistration.query.filter_by(registration_code=code).first_or_404()
    return render_template('registration_confirmation.html', nav=NAV,
                           event=event, reg=reg)


@app.route('/event-series/<slug>')
def event_series(slug):
    series = EventSeries.query.filter_by(slug=slug).first_or_404()
    stops = (Event.query.filter_by(series_id=series.id)
             .order_by(Event.start_date).all())
    return render_template('event_series.html', nav=NAV, series=series,
                           stops=stops)


@app.route('/athletes')
def athletes():
    discipline = request.args.get('discipline', '')
    country = request.args.get('country', '')
    letter = request.args.get('letter', '')
    q = Athlete.query
    if discipline:
        q = q.filter(Athlete.discipline.ilike(f'%{discipline}%'))
    if country:
        q = q.filter(Athlete.nationality == country)
    if letter:
        q = q.filter(Athlete.name.ilike(f'{letter}%'))
    athletes_list = q.order_by(Athlete.name).all()
    disciplines = sorted({a.discipline for a in Athlete.query.all()
                          if a.discipline})
    countries = sorted({a.nationality for a in Athlete.query.all()
                        if a.nationality})
    letters = sorted({a.name[0].upper() for a in Athlete.query.all()})
    return render_template('athletes.html', nav=NAV, athletes=athletes_list,
                           disciplines=disciplines, countries=countries,
                           letters=letters, active_discipline=discipline,
                           active_country=country, active_letter=letter)


@app.route('/athletes/<slug>')
def athlete_detail(slug):
    athlete = Athlete.query.filter_by(slug=slug).first_or_404()
    stories = Story.query.filter_by(discipline='').limit(3).all()
    return render_template('athlete_detail.html', nav=NAV, athlete=athlete,
                           stories=stories)


@app.route('/films')
def films():
    discipline = request.args.get('discipline', '')
    page = max(int(request.args.get('page', 1) or 1), 1)
    per_page = 12
    q = Film.query
    if discipline:
        q = q.filter(Film.discipline == discipline)
    films_all = q.order_by(Film.published.desc().nullslast()).all()
    total = len(films_all)
    page_items = films_all[(page - 1) * per_page: page * per_page]
    disciplines = sorted({f.discipline for f in Film.query.all() if f.discipline})
    return render_template('films.html', nav=NAV, films=page_items,
                           disciplines=disciplines, active_discipline=discipline,
                           page=page, total=total, per_page=per_page)


@app.route('/films/<slug>')
def film_detail(slug):
    film = Film.query.filter_by(slug=slug).first_or_404()
    related = Film.query.filter(Film.id != film.id)
    if film.discipline:
        related = related.filter(Film.discipline == film.discipline)
    related = related.limit(4).all()
    return render_template('film_detail.html', nav=NAV, film=film,
                           related=related)


@app.route('/shows')
def shows():
    discipline = request.args.get('discipline', '')
    page = max(int(request.args.get('page', 1) or 1), 1)
    per_page = 12
    q = Show.query
    if discipline:
        q = q.filter(Show.discipline == discipline)
    shows_all = q.order_by(Show.nr_episodes.desc(), Show.title).all()
    total = len(shows_all)
    page_items = shows_all[(page - 1) * per_page: page * per_page]
    disciplines = sorted({s.discipline for s in Show.query.all() if s.discipline})
    return render_template('shows.html', nav=NAV, shows=page_items,
                           disciplines=disciplines, active_discipline=discipline,
                           page=page, total=total, per_page=per_page)


@app.route('/shows/<slug>')
def show_detail(slug):
    show = Show.query.filter_by(slug=slug).first_or_404()
    related = Show.query.filter(Show.id != show.id)
    if show.discipline:
        related = related.filter(Show.discipline == show.discipline)
    related = related.limit(4).all()
    return render_template('show_detail.html', nav=NAV, show=show,
                           related=related)


@app.route('/stories')
def stories():
    discipline = request.args.get('discipline', '')
    page = max(int(request.args.get('page', 1) or 1), 1)
    per_page = 10
    q = Story.query
    if discipline:
        q = q.filter(Story.discipline == discipline)
    stories_all = q.order_by(Story.published.desc().nullslast()).all()
    total = len(stories_all)
    page_items = stories_all[(page - 1) * per_page: page * per_page]
    disciplines = sorted({s.discipline for s in Story.query.all() if s.discipline})
    return render_template('stories.html', nav=NAV, stories=page_items,
                           disciplines=disciplines, active_discipline=discipline,
                           page=page, total=total, per_page=per_page)


@app.route('/stories/<slug>')
def story_detail(slug):
    story = Story.query.filter_by(slug=slug).first_or_404()
    related = Story.query.filter(Story.id != story.id)
    if story.discipline:
        related = related.filter(Story.discipline == story.discipline)
    related = related.order_by(Story.published.desc().nullslast()).limit(4).all()
    return render_template('story_detail.html', nav=NAV, story=story,
                           related=related)


@app.route('/shop')
def shop():
    category = request.args.get('category', '')
    vendor = request.args.get('vendor', '')
    sort = request.args.get('sort', '')
    page = max(int(request.args.get('page', 1) or 1), 1)
    per_page = 12
    q = ShopProduct.query
    if category:
        q = q.filter(ShopProduct.category == category)
    if vendor:
        q = q.filter(ShopProduct.vendor == vendor)
    products = q.order_by(ShopProduct.id).all()
    if sort == 'price_asc':
        products.sort(key=lambda p: p.price_range()[0] or 0)
    elif sort == 'price_desc':
        products.sort(key=lambda p: -(p.price_range()[0] or 0))
    total = len(products)
    page_items = products[(page - 1) * per_page: page * per_page]
    categories = sorted({p.category for p in ShopProduct.query.all()})
    vendors = sorted({p.vendor for p in ShopProduct.query.all() if p.vendor})
    return render_template('shop.html', nav=NAV, products=page_items,
                           categories=categories, vendors=vendors,
                           active_category=category, active_vendor=vendor,
                           active_sort=sort, page=page, total=total,
                           per_page=per_page)


@app.route('/shop/<handle>')
def shop_product(handle):
    product = ShopProduct.query.filter_by(handle=handle).first_or_404()
    related = (ShopProduct.query.filter(ShopProduct.category == product.category,
                                        ShopProduct.id != product.id)
               .limit(4).all())
    return render_template('shop_product.html', nav=NAV, product=product,
                           related=related)


@app.route('/cart')
def cart():
    items = CartItem.query.filter_by(token=_cart_token()).all()
    subtotal = sum(i.variant.price * i.quantity for i in items)
    return render_template('cart.html', nav=NAV, items=items,
                           subtotal=subtotal)


@app.route('/cart/add', methods=['POST'])
def cart_add():
    variant_id = request.form.get('variant_id', type=int)
    quantity = max(request.form.get('quantity', 1, type=int), 1)
    variant = ShopVariant.query.get(variant_id) if variant_id else None
    if not variant:
        abort(404)
    item = CartItem.query.filter_by(token=_cart_token(),
                                    variant_id=variant.id).first()
    if item:
        item.quantity += quantity
    else:
        db.session.add(CartItem(token=_cart_token(), variant_id=variant.id,
                                quantity=quantity, added_at=_now_iso()))
    db.session.commit()
    flash(f'Added {variant.product.title} ({variant.title}) to your cart.')
    return redirect(url_for('cart'))


@app.route('/cart/update', methods=['POST'])
def cart_update():
    item_id = request.form.get('item_id', type=int)
    quantity = request.form.get('quantity', type=int)
    item = CartItem.query.get(item_id) if item_id else None
    if not item or item.token != _cart_token():
        abort(404)
    if quantity is not None and quantity > 0:
        item.quantity = quantity
        db.session.commit()
    return redirect(url_for('cart'))


@app.route('/cart/remove', methods=['POST'])
def cart_remove():
    item_id = request.form.get('item_id', type=int)
    item = CartItem.query.get(item_id) if item_id else None
    if not item or item.token != _cart_token():
        abort(404)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('cart'))


@app.route('/shop/checkout', methods=['GET', 'POST'])
@login_required
def shop_checkout():
    items = CartItem.query.filter_by(token=_cart_token()).all()
    if not items:
        return redirect(url_for('cart'))
    subtotal = sum(i.variant.price * i.quantity for i in items)
    errors = []
    form = {}
    if request.method == 'POST':
        form = {k: request.form.get(k, '').strip() for k in
                ('ship_name', 'ship_email', 'address', 'city', 'zip')}
        for field in ('ship_name', 'ship_email', 'address', 'city', 'zip'):
            if not form[field]:
                errors.append('Please complete every shipping field.')
                break
        if not errors and not re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", form['ship_email']):
            errors.append('Please provide a valid email address.')
        if not errors:
            order_number = 'RB-' + str(100000 + secrets.randbelow(900000))
            order = ShopOrder(order_number=order_number, user_id=current_user.id,
                              status='confirmed', placed_at=_now_iso(),
                              total=round(subtotal, 2),
                              ship_name=form['ship_name'], ship_email=form['ship_email'])
            db.session.add(order)
            db.session.flush()
            for i in items:
                db.session.add(ShopOrderLine(
                    order_id=order.id, variant_id=i.variant.id,
                    product_title=i.variant.product.title,
                    variant_title=i.variant.title, sku=i.variant.sku,
                    unit_price=i.variant.price, quantity=i.quantity))
                db.session.delete(i)
            db.session.commit()
            return redirect(url_for('shop_order_confirmation',
                                    order_number=order_number))
    return render_template('checkout.html', nav=NAV, items=items,
                           subtotal=subtotal, form=form, errors=errors)


@app.route('/shop/orders/<order_number>')
@login_required
def shop_order_confirmation(order_number):
    order = ShopOrder.query.filter_by(order_number=order_number,
                                       user_id=current_user.id).first_or_404()
    return render_template('order_confirmation.html', nav=NAV, order=order)


@app.route('/account/login', methods=['GET', 'POST'])
def account_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('account'))
        return render_template('login.html', nav=NAV,
                               error='Invalid email or password.',
                               email=email)
    return render_template('login.html', nav=NAV, error=None, email='')


@app.route('/account/logout', methods=['POST'])
@login_required
def account_logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/account')
@login_required
def account():
    orders = (ShopOrder.query.filter_by(user_id=current_user.id)
              .order_by(ShopOrder.placed_at.desc()).all())
    registrations = (EventRegistration.query.filter_by(user_id=current_user.id)
                    .order_by(EventRegistration.created_at.desc()).all())
    favorites = Favorite.query.filter_by(user_id=current_user.id).all()
    fav_events = [f.item_slug for f in favorites if f.kind == 'event']
    fav_films = [f.item_slug for f in favorites if f.kind == 'film']
    fav_shows = [f.item_slug for f in favorites if f.kind == 'show']
    fav_stories = [f.item_slug for f in favorites if f.kind == 'story']
    fav_athletes = [f.item_slug for f in favorites if f.kind == 'athlete']
    return render_template('account.html', nav=NAV, orders=orders,
                           registrations=registrations,
                           fav_events=fav_events, fav_films=fav_films,
                           fav_shows=fav_shows, fav_stories=fav_stories,
                           fav_athletes=fav_athletes)


@app.route('/favorites/toggle', methods=['POST'])
@login_required
def favorites_toggle():
    kind = request.form.get('kind', '')
    slug = request.form.get('slug', '')
    if kind not in ('event', 'film', 'show', 'story', 'athlete') or not slug:
        abort(400)
    existing = Favorite.query.filter_by(user_id=current_user.id, kind=kind,
                                        item_slug=slug).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash('Removed from your favorites.')
    else:
        db.session.add(Favorite(user_id=current_user.id, kind=kind, item_slug=slug))
        db.session.commit()
        flash('Added to your favorites.')
    return redirect(request.form.get('next') or url_for('account'))


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html', nav=NAV), 404


# -------------------------------------------------------------------- main --

def seed_database():
    """Idempotent: materialize the upstream snapshot into the DB."""
    import seed_lib
    seed_lib.seed_all(db=db, models=globals(), bcrypt=bcrypt,
                      base_dir=BASE_DIR, load=_load)


# Module-level seed: runs at every container boot and every /reset/red_bull
# respawn; each seed function is gated, so a populated DB is a no-op.
with app.app_context():
    db.create_all()
    seed_database()


def main():
    """Import-and-seed entry point (deterministic, idempotent)."""
    with app.app_context():
        db.create_all()
        seed_database()


if __name__ == '__main__':
    main()
