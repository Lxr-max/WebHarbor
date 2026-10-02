#!/usr/bin/env python3
"""The Weather Network mirror — Flask application.

Mirrors theweathernetwork.com: location forecasts (current / hourly / 7-day /
14-day / weekend / monthly) for 580 real locations (112 city pages plus school,
airport, ski, golf, beach, camping, cottage, marine, attraction and park
channels); weather news (638 real articles across 5 categories / 13
subcategories); the video hub (782 real jwplayer videos, upstream MUST WATCH /
Animals and Weather / Featured playlists); active Environment Canada alerts
(51 real bulletins with regions, severities, messages and recommended actions);
the radar map page; the vacation hub with per-country indexes; four explore
hubs; scored location search; author pages; accounts with saved locations and
a metric/imperial unit preference.

All data is real, captured from the upstream site and its public Pelmorex APIs
on 2026-09-26/27 — see provenance.json. The site clock is pinned to the capture
moment so every relative display ("Updated 2 minutes ago") is stable.
"""
import json
import os
import re
from datetime import date, datetime

from flask import (Flask, abort, flash, redirect, render_template, request,
                   session)
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy import func

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, instance_path=os.path.join(BASE_DIR, 'instance'))
app.config['SECRET_KEY'] = 'webharbor-the-weather-network-dev-key'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("WEBHARBOR_DATABASE_URI") or \
    f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'the_weather_network.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

csrf = CSRFProtect(app)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Deterministic site clock, pinned to the upstream capture moment:
# 2026-09-27 01:30 UTC == 2026-09-26 9:30 PM EDT, right before the first
# hourly slot (10 PM local). LOCAL is used for "Updated X minutes ago" style
# math against local timestamps; DISPLAY carries the UTC date the upstream
# home page rendered ("It's Sunday, September 27th").
MIRROR_NOW_LOCAL = datetime(2026, 9, 26, 21, 30)
MIRROR_NOW_DISPLAY = datetime(2026, 9, 27)
MIRROR_REFERENCE_DATE = date(2026, 9, 26)

STOP_WORDS = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or',
              'is', 'it', 'by', 'with', 'my', 'your', 'our'}

# channel key -> URL segment on the upstream site
CHANNEL_URL = {
    'city': 'city', 'school': 'school', 'airport': 'airport', 'ski': 'ski',
    'golf': 'golf', 'beach': 'beach', 'campground': 'camping', 'cottage': 'cottage',
    'marine': 'marine', 'attraction': 'attraction', 'park': 'park',
}
CHANNEL_LABEL = {
    'city': 'Weather', 'school': 'Schools', 'airport': 'Airport Forecast', 'ski': 'Ski Report',
    'golf': 'Golf Report', 'beach': 'Beaches', 'campground': 'Camping', 'cottage': 'Cottage',
    'marine': 'Marine', 'attraction': 'Attractions', 'park': 'Parks',
}

NEWS_CATEGORIES = [
    ('weather', 'Weather', [('forecasts', 'Forecasts'), ('severe', 'Severe'), ('seasonal', 'Seasonal')]),
    ('science', 'Science', [('space', 'Space'), ('explainers', 'Explainers')]),
    ('climate', 'Climate', [('causes', 'Causes'), ('impacts', 'Impacts'), ('solutions', 'Solutions')]),
    ('nature', 'Nature', [('animals', 'Animals'), ('habitats', 'Habitats'), ('outdoors', 'Outdoors')]),
    ('lifestyle', 'Lifestyle', [('health', 'Health'), ('travel', 'Travel'), ('community', 'Community')]),
]
CATEGORY_COLOURS = {
    'weather': '#BE9207', 'science': '#4F8EDB', 'climate': '#56AB4A',
    'nature': '#0E9F7E', 'lifestyle': '#E86830',
}
REGION_CODES = {
    'AB': 'Alberta', 'BC': 'British Columbia', 'MB': 'Manitoba', 'NB': 'New Brunswick',
    'NL': 'Newfoundland and Labrador', 'NS': 'Nova Scotia', 'NT': 'Northwest Territories',
    'NU': 'Nunavut', 'ON': 'Ontario', 'PE': 'Prince Edward Island', 'QC': 'Quebec',
    'SK': 'Saskatchewan', 'YT': 'Yukon',
}
RADAR_CITIES = ('toronto', 'montreal', 'vancouver', 'calgary', 'halifax', 'ottawa', 'victoria')


def day_periods(daily):
    """Upstream 7/14-day period breakdown, derived from the captured day/night
    values exactly the way the upstream page computes it:
      Morning   = previous day's night period
      Afternoon = the day period
      Evening   = midpoint of the day and night values (display interpolation)
      Overnight = the night period
    All values trace back to the frozen API snapshot; nothing is invented."""
    out = []
    for i, d in enumerate(daily):
        prev = daily[i - 1] if i > 0 else d

        def night_fields(src):
            return {'temp': src.night_temp, 'feels': src.night_feels, 'icon': src.night_icon,
                    'text': src.night_text, 'wind_dir': src.night_wind_dir,
                    'wind_speed': src.night_wind_speed, 'wind_gust': src.night_wind_gust,
                    'rh': src.night_rh, 'pop': src.night_pop, 'rain': src.night_rain,
                    'rain_range': src.night_rain_range, 'snow': src.night_snow,
                    'snow_range': src.night_snow_range}

        def day_fields(src):
            return {'temp': src.day_temp, 'feels': src.day_feels, 'icon': src.day_icon,
                    'text': src.day_text, 'wind_dir': src.day_wind_dir,
                    'wind_speed': src.day_wind_speed, 'wind_gust': src.day_wind_gust,
                    'rh': src.day_rh, 'pop': src.day_pop, 'rain': src.day_rain,
                    'rain_range': src.day_rain_range, 'snow': src.day_snow,
                    'snow_range': src.day_snow_range}

        morning = night_fields(prev)
        afternoon = day_fields(d)
        evening = day_fields(d)
        if d.day_temp is not None and d.night_temp is not None:
            evening['temp'] = round((d.day_temp + d.night_temp) / 2)
            evening['feels'] = round((d.day_feels + d.night_feels) / 2) if d.day_feels is not None and d.night_feels is not None else d.day_feels
        overnight = night_fields(d)
        out.append({'morning': morning, 'afternoon': afternoon,
                    'evening': evening, 'overnight': overnight})
    return out


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(120), default='')
    unit = db.Column(db.String(10), default='metric')
    created_at = db.Column(db.DateTime, default=datetime(2026, 1, 15))

    def set_password(self, raw):
        self.password_hash = bcrypt.generate_password_hash(raw).decode('utf-8')

    def check_password(self, raw):
        return bcrypt.check_password_hash(self.password_hash, raw)


class Location(db.Model):
    __tablename__ = 'locations'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    channel = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(160), nullable=False)
    prov = db.Column(db.String(80), default='')
    prov_code = db.Column(db.String(4), default='')
    country = db.Column(db.String(80), default='')
    country_code = db.Column(db.String(4), default='')
    friendly_url = db.Column(db.String(240), nullable=False)
    url_path = db.Column(db.String(240), nullable=False)  # e.g. ca/ontario/toronto
    lat = db.Column(db.Float, default=0.0)
    lng = db.Column(db.Float, default=0.0)
    is_popular = db.Column(db.Boolean, default=False)
    __table_args__ = (db.UniqueConstraint('channel', 'url_path', name='uq_loc_channel_path'),)

    @property
    def url_prefix(self):
        return CHANNEL_URL.get(self.channel, 'city')

    def url(self, tab='current'):
        return f"/en/{self.url_prefix}/{self.url_path}/{tab}"

    @property
    def display_sub(self):
        if self.channel == 'city':
            bits = [b for b in (self.prov_code, self.country) if b]
            return ', '.join(bits)
        bits = [b for b in (self.prov, self.country) if b]
        return ', '.join(bits)


class Observation(db.Model):
    __tablename__ = 'observations'
    id = db.Column(db.Integer, primary_key=True)
    loc_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    time_local = db.Column(db.String(20), default='')
    code = db.Column(db.String(12), default='')
    icon = db.Column(db.Integer, default=1)
    text = db.Column(db.String(60), default='')
    temp = db.Column(db.Float)
    feels = db.Column(db.Float)
    dew = db.Column(db.Float)
    wind_dir = db.Column(db.String(4), default='')
    wind_speed = db.Column(db.Float)
    wind_gust = db.Column(db.Float)
    wind_deg = db.Column(db.Integer)
    rh = db.Column(db.Integer)
    pressure = db.Column(db.Float)
    pressure_trend = db.Column(db.Integer)
    visibility = db.Column(db.Float)
    ceiling = db.Column(db.Integer)


class HourlyForecast(db.Model):
    __tablename__ = 'hourly_forecasts'
    id = db.Column(db.Integer, primary_key=True)
    loc_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    time_local = db.Column(db.String(20), nullable=False)
    icon = db.Column(db.Integer, default=1)
    text = db.Column(db.String(60), default='')
    temp = db.Column(db.Float)
    feels = db.Column(db.Float)
    wind_dir = db.Column(db.String(4), default='')
    wind_speed = db.Column(db.Float)
    wind_gust = db.Column(db.Float)
    rh = db.Column(db.Integer)
    pop = db.Column(db.Integer)
    rain = db.Column(db.Float)
    rain_range = db.Column(db.String(12), default='')
    snow = db.Column(db.Float)
    snow_range = db.Column(db.String(12), default='')
    cloud = db.Column(db.Integer)

    @property
    def hour_label(self):
        try:
            t = datetime.fromisoformat(self.time_local)
            return t.strftime('%-I%p').lower()
        except Exception:
            return self.time_local

    @property
    def day_label(self):
        try:
            t = datetime.fromisoformat(self.time_local)
            return f"{t.strftime('%a')} {t.strftime('%b')} {t.day}"
        except Exception:
            return ''


class DailyForecast(db.Model):
    __tablename__ = 'daily_forecasts'
    id = db.Column(db.Integer, primary_key=True)
    loc_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    date_local = db.Column(db.String(12), nullable=False)
    day_icon = db.Column(db.Integer, default=1)
    day_text = db.Column(db.String(60), default='')
    day_temp = db.Column(db.Float)
    day_feels = db.Column(db.Float)
    day_wind_dir = db.Column(db.String(4), default='')
    day_wind_speed = db.Column(db.Float)
    day_wind_gust = db.Column(db.Float)
    day_rh = db.Column(db.Integer)
    day_pop = db.Column(db.Integer)
    day_rain = db.Column(db.Float)
    day_rain_range = db.Column(db.String(12), default='')
    day_snow = db.Column(db.Float)
    day_snow_range = db.Column(db.String(12), default='')
    night_icon = db.Column(db.Integer, default=1)
    night_text = db.Column(db.String(60), default='')
    night_temp = db.Column(db.Float)
    night_feels = db.Column(db.Float)
    night_wind_dir = db.Column(db.String(4), default='')
    night_wind_speed = db.Column(db.Float)
    night_wind_gust = db.Column(db.Float)
    night_rh = db.Column(db.Integer)
    night_pop = db.Column(db.Integer)
    night_rain = db.Column(db.Float)
    night_rain_range = db.Column(db.String(12), default='')
    night_snow = db.Column(db.Float)
    night_snow_range = db.Column(db.String(12), default='')
    pop = db.Column(db.Integer)
    rain = db.Column(db.Float)
    rain_range = db.Column(db.String(12), default='')
    snow = db.Column(db.Float)
    snow_range = db.Column(db.String(12), default='')
    sun_hours = db.Column(db.Float)
    day_type = db.Column(db.String(20), default='')

    @property
    def day_name(self):
        try:
            return datetime.fromisoformat(self.date_local).strftime('%a')
        except Exception:
            return ''

    @property
    def date_label(self):
        try:
            return datetime.fromisoformat(self.date_local).strftime('%b %-d')
        except Exception:
            return ''

    @property
    def full_date_label(self):
        try:
            return datetime.fromisoformat(self.date_local).strftime('%B %-d, %Y')
        except Exception:
            return ''


class MonthlyAverage(db.Model):
    __tablename__ = 'monthly_averages'
    id = db.Column(db.Integer, primary_key=True)
    loc_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    month_key = db.Column(db.String(10), nullable=False)
    day = db.Column(db.String(12), nullable=False)
    tmax = db.Column(db.Float)
    tmin = db.Column(db.Float)
    precip_freq = db.Column(db.Integer)

    @property
    def day_num(self):
        try:
            return datetime.fromisoformat(self.day).day
        except Exception:
            return 0


class WellBeing(db.Model):
    __tablename__ = 'wellbeing'
    id = db.Column(db.Integer, primary_key=True)
    loc_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    kind = db.Column(db.String(20), nullable=False)   # airquality/uv/pollen/health/bugs
    value = db.Column(db.Float)
    label = db.Column(db.String(40), default='')


class Author(db.Model):
    __tablename__ = 'authors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(120), default='')
    slug = db.Column(db.String(120), unique=True)
    avatar = db.Column(db.String(200), default='')


class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(240), unique=True, nullable=False)
    slug = db.Column(db.String(200), nullable=False)
    headline = db.Column(db.String(300), nullable=False)
    summary = db.Column(db.Text, default='')
    body = db.Column(db.Text, nullable=False)
    category_key = db.Column(db.String(40), nullable=False)
    subcategory_key = db.Column(db.String(40), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('authors.id'))
    thumb = db.Column(db.String(200), default='')
    effective_date = db.Column(db.String(40), default='')
    created_at = db.Column(db.String(40), default='')
    updated_at = db.Column(db.String(40), default='')
    keywords = db.Column(db.Text, default='[]')
    embedded_videos = db.Column(db.Text, default='[]')

    @property
    def kw(self):
        try:
            return json.loads(self.keywords)
        except Exception:
            return []

    @property
    def vids(self):
        try:
            return json.loads(self.embedded_videos)
        except Exception:
            return []

    @property
    def published_label(self):
        try:
            t = datetime.fromisoformat(self.effective_date)
            return t.strftime('%b. %-d, %Y, %-I:%M %p')
        except Exception:
            return ''

    @property
    def date_label(self):
        try:
            return datetime.fromisoformat(self.effective_date).strftime('%B %-d, %Y')
        except Exception:
            return ''


class Video(db.Model):
    __tablename__ = 'videos'
    id = db.Column(db.Integer, primary_key=True)
    mediaid = db.Column(db.String(12), unique=True, nullable=False)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default='')
    duration = db.Column(db.Integer, default=0)
    pubdate = db.Column(db.Integer, default=0)
    playlists = db.Column(db.Text, default='[]')

    @property
    def pls(self):
        try:
            return json.loads(self.playlists)
        except Exception:
            return []

    @property
    def duration_label(self):
        m, s = divmod(int(self.duration or 0), 60)
        return f"{m}:{s:02d}"


class Alert(db.Model):
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True)
    placecode = db.Column(db.String(20), unique=True, nullable=False)
    location_name = db.Column(db.String(200), nullable=False)
    region = db.Column(db.String(60), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    condition = db.Column(db.String(40), default='')
    type = db.Column(db.String(30), default='')
    priority = db.Column(db.String(20), default='')
    status = db.Column(db.String(20), default='active')
    treatment = db.Column(db.Integer, default=1)
    source_text = db.Column(db.String(160), default='')
    issued = db.Column(db.String(20), default='')
    expires = db.Column(db.String(20), default='')
    updated = db.Column(db.String(20), default='')
    message = db.Column(db.Text, default='')
    recommended = db.Column(db.Text, default='')
    related = db.Column(db.Text, default='[]')

    @property
    def rel(self):
        try:
            return json.loads(self.related)
        except Exception:
            return []

    @property
    def issued_label(self):
        try:
            return datetime.fromisoformat(self.issued).strftime('%a %-I:%M %p %b. %-d')
        except Exception:
            return ''

    @property
    def expires_label(self):
        try:
            return datetime.fromisoformat(self.expires).strftime('%a %-I:%M %p %b. %-d')
        except Exception:
            return ''

    @property
    def region_code(self):
        for code, name in REGION_CODES.items():
            if name.lower() == self.region.lower():
                return code
        return ''


class SavedLocation(db.Model):
    __tablename__ = 'saved_locations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    loc_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime(2026, 9, 20))
    __table_args__ = (db.UniqueConstraint('user_id', 'loc_id', name='uq_saved_user_loc'),)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Indexes are created in this fixed order (never via Column(index=True), whose
# CREATE INDEX statements follow Table.indexes set iteration and flip the seed
# between byte layouts across builds). All statements are IF NOT EXISTS so a
# normal boot on an already-seeded database writes nothing.
INDEX_DDL = (
    'CREATE INDEX IF NOT EXISTS ix_locations_channel ON locations (channel)',
    'CREATE INDEX IF NOT EXISTS ix_observations_loc_id ON observations (loc_id)',
    'CREATE INDEX IF NOT EXISTS ix_hourly_forecasts_loc_id ON hourly_forecasts (loc_id)',
    'CREATE INDEX IF NOT EXISTS ix_daily_forecasts_loc_id ON daily_forecasts (loc_id)',
    'CREATE INDEX IF NOT EXISTS ix_monthly_averages_loc_id ON monthly_averages (loc_id)',
    'CREATE INDEX IF NOT EXISTS ix_wellbeing_loc_id ON wellbeing (loc_id)',
    'CREATE INDEX IF NOT EXISTS ix_articles_slug ON articles (slug)',
    'CREATE INDEX IF NOT EXISTS ix_articles_category_key ON articles (category_key)',
    'CREATE INDEX IF NOT EXISTS ix_articles_subcategory_key ON articles (subcategory_key)',
    'CREATE INDEX IF NOT EXISTS ix_alerts_region ON alerts (region)',
    'CREATE INDEX IF NOT EXISTS ix_saved_locations_user_id ON saved_locations (user_id)',
)


def create_indexes():
    with db.engine.begin() as conn:
        for ddl in INDEX_DDL:
            conn.execute(db.text(ddl))


class SiteContent(db.Model):
    __tablename__ = 'site_content'
    key = db.Column(db.String(80), primary_key=True)
    payload = db.Column(db.Text, nullable=False)


def seed_site_content():
    if SiteContent.query.count():
        return
    for key, filename in [('chrome', 'source_data_site.json'), ('inline_images', 'inline_images.json')]:
        with open(os.path.join(BASE_DIR, filename), encoding='utf-8') as handle:
            value = json.load(handle)
        db.session.add(SiteContent(key=key, payload=json.dumps(value, ensure_ascii=False, sort_keys=True)))
    db.session.commit()


def load_site_chrome():
    row = db.session.get(SiteContent, 'chrome')
    return json.loads(row.payload) if row else {}


SITE_CHROME = {}


def search_text(value):
    """Match Canadian place names with or without keyboard accents."""
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value or ''))
                   if not unicodedata.combining(c)).casefold()


def scored_search(query, items, fields=('name', 'prov', 'country', 'channel')):
    tokens = [t.lower() for t in re.split(r'\W+', search_text(query))
              if t.lower() not in STOP_WORDS and len(t) > 1]
    if not tokens:
        return items
    results = []
    for item in items:
        text = search_text(' '.join(str(getattr(item, f, '') or '') for f in fields))
        score = sum(1 for t in tokens if t in text)
        if score > 0:
            results.append((item, score))
    results.sort(key=lambda x: (-x[1], x[0].name.lower(), x[0].code))
    return [r[0] for r in results]


def get_unit():
    if session.get('user_id'):
        user = db.session.get(User, session['user_id'])
        if user:
            return user.unit or 'metric'
    return session.get('unit', 'metric')


def c_to_f(c):
    return None if c is None else round(c * 9 / 5 + 32)


def kmh_to_mph(v):
    return None if v is None else round(v * 0.621371)


def mm_to_in(v):
    return None if v is None else round(v / 25.4, 2)


def cm_to_in(v):
    return None if v is None else round(v / 2.54, 1)


def fmt_temp(value, unit):
    if value is None:
        return '--'
    if unit == 'imperial':
        return f"{c_to_f(value)}°"
    return f"{round(value)}°"


def fmt_speed(value, unit):
    if value is None:
        return '--'
    if unit == 'imperial':
        return f"{kmh_to_mph(value)} mph"
    return f"{round(value)} km/h"


def precip_label(rain, rain_range, snow, snow_range, unit):
    """Upstream-style precipitation summary: '<1mm', '~1mm', '5-10mm'..."""
    if snow:
        if unit == 'imperial':
            return f"{cm_to_in(snow)} in snow"
        return f"{round(snow)} cm snow" if snow >= 1 else '<1 cm snow'
    if rain:
        if unit == 'imperial':
            return f"{mm_to_in(rain)} in rain"
        if rain_range:
            return f"{rain_range} mm"
        return f"{round(rain)} mm"
    return 'None expected'


def minutes_ago(time_local, ref_time=None):
    """Relative 'Updated X minutes ago' label.

    The site clock is pinned to the capture window: the reference instant is
    the top of the hour before the first hourly forecast slot for this
    location (all observations were captured 0-60 min before their first
    slot), so the label is deterministic and honest per location.
    """
    try:
        t = datetime.fromisoformat(time_local)
    except Exception:
        return 'Updated recently'
    if ref_time:
        try:
            ref = datetime.fromisoformat(ref_time)
            delta = (ref - t).total_seconds() / 60
        except Exception:
            delta = 30
    else:
        delta = 30
    if delta < 1:
        delta = 1
    if delta < 60:
        return f"Updated {int(delta)} minutes ago"
    if delta < 60 * 24:
        return f"Updated {int(delta // 60)} hours ago"
    return 'Updated recently'


def _ordinal(n):
    if 10 <= n % 100 <= 20:
        return 'th'
    return {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')


def long_date_heading():
    return f"It's {MIRROR_NOW_DISPLAY.strftime('%A, %B')} {MIRROR_NOW_DISPLAY.day}{_ordinal(MIRROR_NOW_DISPLAY.day)}"


def wx_icon(icon):
    return f"/static/images/wx_icons/icon_{icon or 1}.svg"


def _locs_by_slugs(slugs):
    out = []
    for slug in slugs:
        loc = Location.query.filter(Location.url_path.like(f"%/{slug}"),
                                    Location.channel == 'city').first()
        if loc:
            out.append(loc)
    return out


def popular_locations():
    return _locs_by_slugs(SITE_CHROME.get('city_popular') or [])


def home_locations():
    return _locs_by_slugs(SITE_CHROME.get('home_popular') or [])


def nav_provinces():
    return SITE_CHROME.get('nav_provinces') or []


def lineup_items():
    items = []
    for entry in SITE_CHROME.get('home_lineup') or []:
        if entry.get('type') == 'article':
            art = Article.query.filter_by(path=entry.get('path')).first()
            if art:
                items.append({'kind': 'article', 'article': art, 'video': None,
                              'title': entry.get('title') or art.headline})
        else:
            vid = Video.query.filter_by(mediaid=entry.get('mediaid')).first()
            if vid:
                items.append({'kind': 'video', 'article': None, 'video': vid,
                               'title': entry.get('title') or vid.title})
    return items


def feed_items():
    """Bottom-of-home content feed: the upstream endless mixed feed, frozen at
    the capture order (lead articles interleaved with the Featured playlist
    videos), then the remaining lineup entries."""
    items = []
    for entry in SITE_CHROME.get('home_feed') or []:
        if entry.get('type') == 'article':
            art = Article.query.filter_by(path=entry.get('path')).first()
            if art:
                items.append({'kind': 'article', 'article': art, 'video': None,
                              'title': entry.get('title') or art.headline})
        else:
            vid = Video.query.filter_by(mediaid=entry.get('mediaid')).first()
            if vid:
                items.append({'kind': 'video', 'article': None, 'video': vid,
                              'title': entry.get('title') or vid.title})
    return items


def hourly_summary(hourly):
    """Upstream hero line, e.g. 'A few clouds for the next 6 hours, then clear.'
    Derived from the captured hourly rows exactly like the upstream page: the
    leading run of identical conditions, then what follows."""
    if not hourly:
        return ''
    texts = [h.text for h in hourly[:12]]
    first = texts[0]
    run = 1
    while run < len(texts) and texts[run] == first:
        run += 1
    if run >= len(texts) or run >= 12:
        return f'{first} for the next {len(texts)} hours.'
    nxt = texts[run]
    if nxt == first:
        return f'{first} for the next {run} hours.'
    return f'{first} for the next {run} hours, then {nxt.lower()}.'


def context(**kw):
    ctx = {
        'unit': get_unit(),
        'nav_provinces': nav_provinces(),
        'chrome': SITE_CHROME,
        'region_codes': REGION_CODES,
        'now_heading': long_date_heading(),
    }
    ctx.update(kw)
    return ctx


# --- article body rendering -------------------------------------------------


def _load_inline_map():
    row = db.session.get(SiteContent, 'inline_images')
    return json.loads(row.payload) if row else {}


INLINE_IMAGES = {}


def _inline_base(url):
    url = (url or '').strip().replace('&amp;', '&')
    if url.startswith('//'):
        url = 'https:' + url
    return url.split('?')[0]


# tracking pixels embedded as markdown images in The Conversation-sourced
# articles; upstream renders them as invisible 1x1 beacons — never content
TRACKING_MARKERS = ('counter.theconversation.com', 'engagefront', '/pxl')

# Captured article paths + author slugs, loaded once for body-link rewriting:
# upstream bodies link to ~800 sibling articles that exist on the live site
# but were outside the 638-article capture window. Those links are rewritten
# to their (sub)category listing so the mirror never serves a dead link.
def _load_link_sets():
    paths, slugs, locs, byslug = set(), set(), set(), {}
    try:
        for (p,) in db.session.execute(db.text('SELECT path FROM articles')):
            paths.add(p)
        for (p, s) in db.session.execute(db.text('SELECT path, slug FROM articles')):
            if s and s not in byslug:
                byslug[s] = p
        for (s,) in db.session.execute(db.text('SELECT slug FROM authors')):
            if s:
                slugs.add(s)
        for (c, p) in db.session.execute(db.text('SELECT channel, url_path FROM locations')):
            locs.add(f'{c}:{p}')
    except Exception:
        pass
    return paths, slugs, locs, byslug


ARTICLE_PATHS, AUTHOR_SLUGS, LOC_PATHS, ARTICLE_BY_SLUG = set(), set(), set(), {}   # filled by the bootstrap below
NEWS_CATEGORIES_BY_KEY = {key: (label, dict(subs)) for key, label, subs in NEWS_CATEGORIES}
NEWS_SUBCATEGORY_HOME = {sub: key for key, label, subs in NEWS_CATEGORIES for sub in dict(subs)}

CHANNEL_URL_TO_KEY = {v: k for k, v in CHANNEL_URL.items()}

# Upstream capture quirk: a browser extension on the capture machine rewrote
# some source URLs as chrome-extension://<id>/https://... — the real target
# follows the prefix.
_CHROME_EXT_RE = re.compile(r'^chrome-extension://[^/]+/(https?://.+)$', re.I)
# Upstream capture quirk: bare host links in the captured markdown
# ('www.carfreebanff.ca', 'google.com/url?q=...', 'news.google.com/read/...').
_SCHEMELESS_HOST_RE = re.compile(r'^(?:www\.)?[a-z0-9][a-z0-9.-]*\.[a-z]{2,}(?:[/?#:]|\.$|$)', re.I)


def _normalize_body_href(url):
    """Normalize upstream capture quirks in body-link URLs so every rendered
    body link is either a live internal path or a well-formed external URL.

    Handles: leading/trailing whitespace (browsers trim it; keep crawlers and
    browsers seeing the same thing), a doubled opening paren before http(s)
    ('[x]((url))' captions), the chrome-extension:// capture prefix, the
    'ttps://' typo, scheme-less upstream-host links (rewritten like any other
    upstream path) and scheme-less external-host links (given a scheme).
    """
    url = url.strip()
    if url.startswith('(') and url[1:5].lower() == 'http':
        url = url[1:].lstrip()
    m = _CHROME_EXT_RE.match(url)
    if m:
        url = m.group(1)
    if url[:7].lower() == 'ttps://':
        url = 'h' + url
    low = url.lower()
    for host in ('www.theweathernetwork.com/', 'theweathernetwork.com/'):
        if low.startswith(host):
            # scheme-less upstream-host link: strip the host and let the
            # caller rewrite the resulting path (no recursion here — the
            # outer pass must stay the single rewriting pass)
            return '/' + url[len(host):].lstrip('/')
    if _SCHEMELESS_HOST_RE.match(url):
        return 'https://' + url
    return url

# Upstream articles linked with the bare /ca/news/article/<slug> scheme (no
# category in the URL) that fell outside the 638-article capture window.
# Each maps to the (sub)category listing that holds its closest captured
# siblings on the mirror, so the link still lands on a live listing page.
SLUG_SECTION_FALLBACK = {
    '4-friendly-pollinators-you-can-find-in-canada-bats-bees-moths-hummingbirds-butterflies': '/en/news/nature/animals',
    'buzzing-with-ideas-to-keep-pollinators-and-plants-thriving-bees-butterflies-birds-moths-flies': '/en/news/nature/animals',
    'covid19-outbreak-prompts-airline-companies-in-europe-to-fly-ghost-flights-coronavirus': '/en/news/climate/causes',
    'earwigs-are-flourishing-on-p-e-i-this-season-heres-why': '/en/news/nature/animals',
    'five-ways-life-would-be-better-if-it-were-always-daylight-saving': '/en/news/weather/seasonal',
    'flight-shaming-a-growing-trend-climate-change': '/en/news/climate/causes',
    'fracking-to-blame-for-earthquakes-seismic-clusters-in-central-alberta': '/en/news/climate/causes',
    'have-you-found-a-meteorite-heres-how-to-know-for-sure': '/en/news/science/space',
    'honeybees-can-pose-a-threat-to-wild-bees-heres-how': '/en/news/nature/animals',
    'how-hot-water-fuels-the-worlds-most-powerful-hurricanes': '/en/news/science/explainers',
    'how-the-tropics-help-produce-big-springtime-snows-on-the-prairies': '/en/news/science/explainers',
    'microbursts-can-turn-a-gentle-thunderstorm-into-a-harrowing-ordeal': '/en/news/weather/severe',
    'mikmaq-first-nation-artist-captures-life-and-the-changing-coastlines-on-p-e-i': '/en/news/nature/outdoors',
    'nasa-axion-first-private-astronaut-mission-to-the-international-space-stationh-on-historic-all-civilian-mission': '/en/news/science/space',
    'nova-scotia-breaks-22-year-tornado-drought-with-strongest-twister-41-years': '/en/news/weather/severe',
    'shop-the-weather-home-emergency-kit': '/en/news/weather/seasonal',
    'the-biggest-threat-to-canadian-turtles': '/en/news/nature/animals',
    'the-future-of-food-waste-disposal': '/en/news/climate/solutions',
    'this-day-in-weather-history-february-3-black-history-month-feature': '/en/news/weather/severe',
    'top-3-pests-to-be-on-the-lookout-for-this-fall-in-canada': '/en/news/nature/animals',
    'understanding-cape-the-fuel-that-powers-a-thunderstorm': '/en/news/science/explainers',
    'why-does-your-long-range-forecast-change-so-often': '/en/news/science/explainers',
    'why-that-wild-weather-model-map-you-saw-on-social-media-is-probably-bogus': '/en/news/science/explainers',
    'william-shatner-to-fly-to-space-with-bezos-blue-origin': '/en/news/science/space',
}


def _rewrite_news_link(url):
    """Point body links at a page the mirror actually serves.

    Upstream article bodies link to sibling articles, author pages, city
    forecast pages, explore hubs, vacation pages and map pages. The capture
    window covers 638 of them; everything outside it is redirected to the
    closest page the mirror really has, so no body link ever dead-ends.

    Besides the /en/... scheme, upstream bodies also carry the Canadian
    locale scheme (/ca/news/article/<slug>, /ca/news/category/<name>) and a
    handful of bare section paths (/explore/<hub>, /weatherhistory,
    /weather-apps, /photos/..., bare /ca). Those are normalized here to the
    same closest-live-page rule so they never dead-end either.
    """
    url = _normalize_body_href(url.split('#')[0])
    parts = [p for p in url.strip('/').split('/') if p]
    if not parts:
        return url
    if parts[0] != 'en':
        return _rewrite_non_en_link(url, parts)
    if len(parts) == 1:
        return '/en'
    head = parts[1]
    if head == 'news':
        if len(parts) >= 4 and parts[2] == 'author':
            if parts[3] in AUTHOR_SLUGS:
                return '/en/news/author/' + parts[3]
            return '/en/news'
        if len(parts) >= 5:
            cat, sub, slug = parts[2], parts[3], parts[4]
            if f'/en/news/{cat}/{sub}/{slug}' in ARTICLE_PATHS:
                return f'/en/news/{cat}/{sub}/{slug}'
            meta = NEWS_CATEGORIES_BY_KEY.get(cat)
            if meta and sub in meta[1]:
                return f'/en/news/{cat}/{sub}'
            if meta:
                return f'/en/news/{cat}'
            return '/en/news'
        if len(parts) == 4:                      # /en/news/<cat>/<page-ish>
            meta = NEWS_CATEGORIES_BY_KEY.get(parts[2])
            if meta:
                return f'/en/news/{parts[2]}'
            return '/en/news'
        return url
    if head == 'city' and len(parts) == 2:
        return '/en/search'                      # upstream: find-your-city page
    if head in CHANNEL_URL_TO_KEY:
        channel = CHANNEL_URL_TO_KEY[head]
        if len(parts) >= 5:
            path = '/'.join(parts[2:5])
            if f'{channel}:{path}' in LOC_PATHS:
                tab = parts[5] if len(parts) > 5 else 'current'
                if tab not in ('current', 'hourly', '7-days', '14-days', 'weekend', 'monthly'):
                    tab = 'current'   # upstream-only tabs (pollen/bugs/uv) land on current
                return f'/en/{head}/{path}/{tab}'
        return '/en/search'
    if head == 'vacation':
        if len(parts) >= 5 and f'city:{"/".join(parts[2:5])}' in LOC_PATHS:
            return url
        return '/en/vacation'
    if head == 'explore':
        if len(parts) >= 3 and parts[2] in HUB_META:
            return '/en/explore/' + parts[2]
        return '/en'
    if head == 'maps':
        return '/en/maps/radar'
    if head == 'alerts' or head == 'video' or head == 'account' or head == 'info':
        return url
    return url


def _rewrite_non_en_link(url, parts):
    """Normalize upstream locale/bare-section body links to a live mirror page.

    /ca/...            -> the same path under /en/... (mirror scheme), or the
                         closest live section when the target wasn't captured
    /explore/<hub>     -> the hub page when captured, else the home page
    /weatherhistory    -> severe weather news (home of the This Day in
                         Weather History series on the mirror)
    /weather-apps      -> the About Our Mobile Apps info page
    /photos/...        -> home (the mirror has no photo galleries)
    """
    head = parts[0]
    if head == 'ca':
        if len(parts) == 1:
            return '/en'
        if parts[1] == 'news':
            # /ca/news/article/<slug>: upstream's locale article scheme carries
            # no category — link the captured article, else its section listing.
            if len(parts) >= 4 and parts[2] == 'article':
                slug = parts[3]
                if slug in ARTICLE_BY_SLUG:
                    return ARTICLE_BY_SLUG[slug]
                if slug in SLUG_SECTION_FALLBACK:
                    return SLUG_SECTION_FALLBACK[slug]
                return '/en/news'
            # /ca/news/category/<name>: upstream category page — the mirror
            # serves that name as a subcategory listing (seasonal, space, ...).
            if len(parts) >= 4 and parts[2] == 'category':
                name = parts[3]
                if name in NEWS_CATEGORIES_BY_KEY:
                    return f'/en/news/{name}'
                if name in NEWS_SUBCATEGORY_HOME:
                    return f'/en/news/{NEWS_SUBCATEGORY_HOME[name]}/{name}'
                return '/en/news'
            # /ca/news/<cat>/<sub>/<slug> (and deeper): same shape as the mirror
            return _rewrite_news_link('/' + '/'.join(['en'] + parts[1:]))
        return '/en'
    if head == 'explore':
        if len(parts) >= 2 and parts[1] in HUB_META:
            return '/en/explore/' + parts[1]
        return '/en'
    if head == 'weatherhistory':
        return '/en/news/weather/severe'
    if head == 'weather-apps':
        return '/en/info/about-our-mobile-apps'
    if head == 'photos':
        return '/en'
    return url


def _inline_local(url):
    """Local static path for an upstream inline image URL, or None."""
    if any(m in url for m in TRACKING_MARKERS):
        return None
    entry = INLINE_IMAGES.get(_inline_base(url))
    return entry and entry.get('path')


def _rewrite_md_image(m):
    alt, url = m.group(1), m.group(2)
    local = _inline_local(url)
    if not local:
        return ''          # tracking pixel or upstream-gone image: render nothing
    alt_attr = (alt or '').replace('"', '&quot;')
    return (f'<span class="sc-c94751ec-1 ddellb"><img alt="{alt_attr}" '
            f'loading="lazy" src="/static/images/{local}"></span>')


def _rewrite_img_tag(m):
    tag = m.group(0)
    src = re.search(r'src="([^"]+)"', tag)
    if not src:
        return tag
    local = _inline_local(src.group(1))
    if not local:
        return tag
    tag = re.sub(r'srcset="[^"]*"\s*', '', tag)
    tag = re.sub(r'sizes="[^"]*"\s*', '', tag)
    tag = tag.replace(src.group(1), f'/static/images/{local}')
    return tag


def _rewrite_zoom_link(m):
    """Inside <figure> blocks the <a href> wraps the <img> as a zoom link to
    the full-size upstream asset; point it at the same local file. Only
    image hrefs are touched — caption attribution links pass through."""
    href, inner = m.group(1), m.group(2)
    local = _inline_local(href)
    if not local:
        return inner          # unwrap: drop the dead upstream zoom link
    return f'<a href="/static/images/{local}">{inner}</a>'


_ZOOM_RE = re.compile(r'<a href="([^"]*\.(?:jpe?g|png|webp|gif)[^"]*)">(.*?)</a>', re.S)


def _rewrite_bare_img(m):
    """Bare <img> tags in raw captured HTML fragments (embed widgets, counter
    beacons): keep already-local srcs, localize known upstream srcs, and drop
    unknown ones — the same upstream-gone / tracking-pixel convention the
    markdown and figure paths already apply. E.g. the live cwfis fire-danger
    map the upstream fire-bans explainer hotlinked now 404s upstream and was
    never captured: it must not render as a broken external <img> that makes
    the mirror emit an off-site request."""
    tag = m.group(0)
    src = re.search(r'src="([^"]+)"', tag)
    if not src:
        return tag
    url = src.group(1)
    if url.startswith('/static/images/') or url.startswith('static/images/'):
        return tag
    local = _inline_local(url)
    if not local:
        return ''           # tracking pixel or upstream-gone image: render nothing
    tag = re.sub(r'srcset="[^"]*"\s*', '', tag)
    tag = re.sub(r'sizes="[^"]*"\s*', '', tag)
    return tag.replace(url, f'/static/images/{local}')


def _rewrite_figure(m):
    frag = m.group(0)
    src = re.search(r'<img[^>]+src="([^"]+)"', frag)
    if not src:
        return frag
    local = _inline_local(src.group(1))
    if not local:
        return ''            # upstream image is gone: drop the whole figure
    frag = _ZOOM_RE.sub(_rewrite_zoom_link, frag)
    frag = re.sub(r'<img[^>]+>', _rewrite_img_tag, frag)
    return frag


def render_body(body):
    """Render the captured upstream markdown to HTML.

    Handles: paragraphs, ### headings, [text](url) links (rewritten to the
    mirror), __bold__, *italic*, ![alt](url) inline images (rewritten to the
    locally captured upstream files, rendered exactly like the upstream DOM:
    a <span><img></span> followed by an italic caption paragraph),
    <script src jwplayer> embeds (rendered as video cards via the media id),
    and captured <figure> blocks (img src / zoom href rewritten to the local
    copies, srcset/sizes dropped).
    """
    text = body or ''
    # Some captured bodies end with a raw upstream flight/RSC payload that
    # leaked into the scrape (e.g. '3e:["$","$L42",null,{...}]'). It is
    # transport JSON, never article content: strip everything from the first
    # '<hexid>:["$' marker onward so the payload neither renders as visible
    # garbage text nor emits its escaped-href anchors (which resolved to
    # dead /%22https://... 404s). Render-time only: the seed data is frozen.
    m = re.search(r'[0-9a-f]{1,3}:\["\$"', text)
    if m:
        text = text[:m.start()]
    # rewrite upstream links to local paths (both https/http and www/non-www
    # upstream host forms occur verbatim in the captured bodies)
    text = re.sub(r'https?://(?:www\.)?theweathernetwork\.com', '', text)
    # jwplayer embeds -> video card placeholders resolved by the template
    def embed(m):
        mid = m.group(1)
        return f'@@VIDEO:{mid}@@'
    text = re.sub(r'<script src="https://cdn\.jwplayer\.com/players/([A-Za-z0-9]{8})-[^"]+\.js"></script>', embed, text)
    # inline markdown images -> local <span><img></span> (upstream DOM shape)
    text = re.sub(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)', _rewrite_md_image, text)
    # captured <figure> blocks: rewrite or drop
    text = re.sub(r'<figure.*?</figure>', _rewrite_figure, text, flags=re.S)
    # bare <img> tags in raw HTML fragments: localize or drop, never emit an
    # external src (the markdown/figure passes above already handle their own)
    text = re.sub(r'<img[^>]+>', _rewrite_bare_img, text)
    # escape nothing else: figures/figcaption are trusted captured HTML
    blocks = re.split(r'\n\s*\n', text)
    out = []
    for block in blocks:
        b = block.strip()
        if not b:
            continue
        if b.startswith('@@VIDEO:'):
            out.append(b)
        elif b.startswith('<span class="sc-c94751ec-1'):
            out.append(b)
        elif b.startswith('<figure') or b.startswith('<img'):
            out.append(b)
        elif b.startswith('###'):
            heading = re.sub(r'^#+\s*', '', b)
            heading = re.sub(r'__(.+?)__', r'<strong>\1</strong>', heading)
            out.append(f'<h3>{heading}</h3>')
        else:
            # paragraphs: markdown links + bold + italic
            def _md_link(m):
                href = _rewrite_news_link(m.group(2))
                return f'<a href="{href}">{m.group(1)}</a>'
            b = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', _md_link, b)
            b = re.sub(r'__(.+?)__', r'<strong>\1</strong>', b)
            b = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', b)
            b = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<i>\1</i>', b)
            out.append(f'<p>{b}</p>')
    html = '\n'.join(out)
    return html


def body_videos(rendered):
    return re.findall(r'@@VIDEO:([A-Za-z0-9]{8})@@', rendered or '')


def replace_embeds(rendered):
    """Swap @@VIDEO:id@@ placeholders for inline video cards (jwplayer embeds)."""
    def repl(m):
        vid = Video.query.filter_by(mediaid=m.group(1)).first()
        if not vid:
            return ''
        title = vid.title.replace('"', '&quot;')
        return (f'<div class="article-embed"><a href="/en/video/{vid.mediaid}" style="display:block">'
                f'<img src="/static/images/videos/{vid.mediaid}.jpg" alt="{title}"></a>'
                f'<div class="ae-title">{vid.title} '
                f'<span class="muted" style="font-weight:400">{vid.duration_label}</span></div></div>')
    return re.sub(r'@@VIDEO:([A-Za-z0-9]{8})@@', repl, rendered or '')


app.jinja_env.filters['temp'] = fmt_temp
app.jinja_env.filters['speed'] = fmt_speed
app.jinja_env.filters['wxicon'] = wx_icon
app.jinja_env.filters['render_body'] = render_body
app.jinja_env.filters['replace_embeds'] = replace_embeds
app.jinja_env.filters['minutes_ago'] = minutes_ago
app.jinja_env.filters['category_colour'] = lambda k: CATEGORY_COLOURS.get(k, '#1E417C')
app.jinja_env.globals['c_to_f'] = c_to_f
app.jinja_env.globals['kmh_to_mph'] = kmh_to_mph
app.jinja_env.globals['precip_label'] = precip_label
app.jinja_env.globals['minutes_ago'] = minutes_ago
app.jinja_env.globals['body_videos'] = body_videos


# ---------------------------------------------------------------------------
# Routes — home & search
# ---------------------------------------------------------------------------

@app.route('/')
def root():
    return redirect('/en')


@app.route('/en')
def home():
    province_cards = []
    for prov in nav_provinces():
        locs = (Location.query.filter(Location.channel == 'city',
                                      Location.url_path.like(f"%/{prov['slug']}/%"))
                .order_by(Location.name).all())
        province_cards.append({'slug': prov['slug'], 'name': prov.get('name') or prov['slug'].replace('-', ' ').title(), 'cities': locs})
    hero = []
    for loc in home_locations():
        hero.append({'loc': loc, 'obs': Observation.query.filter_by(loc_id=loc.id).first()})
    return render_template('home.html', **context(
        hero_locs=hero,
        rail=lineup_items(),
        feed=feed_items(),
        alerts_total=Alert.query.count(),
        province_cards=province_cards,
        articles=Article.query.order_by(Article.created_at.desc()).limit(12).all(),
    ))


@app.route('/en/search')
def search():
    # the header form submits ?search=, direct links use ?q=
    q = (request.args.get('q') or request.args.get('search') or '').strip()
    results = []
    if q:
        results = scored_search(q, Location.query.all())
    return render_template('search.html', **context(q=q, results=results[:40]))


@app.route('/en/search/suggest')
def search_suggest():
    """JSON typeahead for the header search box (mirrors the upstream widget)."""
    q = (request.args.get('q') or '').strip()
    out = []
    if q:
        for loc in scored_search(q, Location.query.all())[:8]:
            out.append({'name': loc.name, 'sub': loc.display_sub, 'url': loc.url()})
    from flask import jsonify
    return jsonify({'results': out})


# ---------------------------------------------------------------------------
# Routes — location forecasts
# ---------------------------------------------------------------------------

@app.route('/en/<any("city","school","airport","ski","golf","beach","camping","cottage","marine","attraction","park"):channel_url>/<cc>/<prov>/<slug>')
@app.route('/en/<any("city","school","airport","ski","golf","beach","camping","cottage","marine","attraction","park"):channel_url>/<cc>/<prov>/<slug>/<any("current","hourly","7-days","14-days","weekend","monthly"):tab>')
def location_page(channel_url, cc, prov, slug, tab='current'):
    channel = next((k for k, v in CHANNEL_URL.items() if v == channel_url), None)
    if channel is None:
        abort(404)
    loc = Location.query.filter_by(channel=channel,
                                    url_path=f"{cc}/{prov}/{slug}").first()
    if not loc:
        abort(404)
    obs = Observation.query.filter_by(loc_id=loc.id).first()
    hourly = HourlyForecast.query.filter_by(loc_id=loc.id).order_by(HourlyForecast.time_local).all()
    daily = DailyForecast.query.filter_by(loc_id=loc.id).order_by(DailyForecast.date_local).all()

    updated = minutes_ago(obs.time_local, hourly[0].time_local if hourly else None) if obs else ''
    if tab in ('7-days', '14-days'):
        days = daily[:7] if tab == '7-days' else daily
        periods = day_periods(daily)
        return render_template('location_days.html', **context(
            loc=loc, obs=obs, updated=updated, hourly=hourly[:14], daily=daily, days=days,
            periods=periods, tab=tab))
    if tab == 'hourly':
        return render_template('location_hourly.html', **context(
            loc=loc, obs=obs, updated=updated, hourly=hourly, daily=daily, tab=tab))
    if tab == 'weekend':
        weekend = [d for d in daily if d.day_type == 'weekend'][:2] or daily[:2]
        return render_template('location_weekend.html', **context(
            loc=loc, obs=obs, updated=updated, hourly=hourly, daily=daily, weekend=weekend, tab=tab))
    if tab == 'monthly':
        month_keys = sorted({m.month_key for m in MonthlyAverage.query.filter_by(loc_id=loc.id)})
        month = request.args.get('m')
        active_month = month if month in month_keys else (month_keys[0] if month_keys else '')
        rows = (MonthlyAverage.query.filter_by(loc_id=loc.id, month_key=active_month)
                .order_by(MonthlyAverage.day).all())
        return render_template('location_monthly.html', **context(
            loc=loc, obs=obs, updated=updated, month_keys=month_keys, active_month=active_month,
            rows=rows, tab=tab))

    # current tab
    wellbeing = {w.kind: w for w in WellBeing.query.filter_by(loc_id=loc.id).all()}
    today = daily[0] if daily else None
    periods = day_periods(daily)
    faq = build_faq(loc, obs, today, wellbeing)
    saved = False
    if session.get('user_id'):
        saved = bool(SavedLocation.query.filter_by(user_id=session['user_id'], loc_id=loc.id).first())
    radar_slug = 'toronto'
    for cand in RADAR_CITIES:
        if loc.url_path.endswith(f"/{cand}"):
            radar_slug = cand
            break
    featured_vids = [v for v in Video.query.all() if 'HtPmBhvM' in v.pls]
    featured_vids.sort(key=lambda v: (-(v.pubdate or 0), v.mediaid))
    return render_template('location_current.html', **context(
        loc=loc, obs=obs, updated=updated, hourly=hourly[:14], daily=daily, today=today,
        periods=periods, wellbeing=wellbeing, faq=faq, tab=tab, saved=saved,
        hero_summary=hourly_summary(hourly), featured_vids=featured_vids,
        month_keys=sorted({m.month_key for m in MonthlyAverage.query.filter_by(loc_id=loc.id)}),
        month_rows=(MonthlyAverage.query.filter_by(loc_id=loc.id, month_key=sorted(
                        {m.month_key for m in MonthlyAverage.query.filter_by(loc_id=loc.id)})[0])
                    .order_by(MonthlyAverage.day).all()
                    if MonthlyAverage.query.filter_by(loc_id=loc.id).count() else []),
        radar_slug=radar_slug,
        alerts=Alert.query.filter(Alert.region == loc.prov).all() if loc.prov else [],
        popular=[{'loc': p, 'obs': Observation.query.filter_by(loc_id=p.id).first()}
                 for p in popular_locations()],
        related_news=Article.query.order_by(Article.created_at.desc()).limit(6).all(),
    ))


def build_faq(loc, obs, today, wellbeing):
    faq = []
    if obs is None:
        return faq
    unit = get_unit()
    faq.append((f"What is the current temperature in {loc.name}?", fmt_temp(obs.temp, unit)))
    faq.append((f"What is the “feels like” temperature in {loc.name}?", fmt_temp(obs.feels, unit)))
    if today:
        faq.append((f"What is the high and low temperature today in {loc.name}?",
                    f"{fmt_temp(today.day_temp, unit)} / {fmt_temp(today.night_temp, unit)}"))
        faq.append((f"What is the probability of rain or snow today in {loc.name}?", f"{today.pop}% P.O.P."))
        faq.append((f"How much will it rain or snow today in {loc.name}?",
                    precip_label(today.rain, today.rain_range, today.snow, today.snow_range, unit)))
    faq.append((f"What is the current wind speed and direction in {loc.name}?",
                f"{fmt_speed(obs.wind_speed, unit)} {obs.wind_dir}"))
    faq.append((f"What is the current humidity level in {loc.name}?", f"{obs.rh}%"))
    region_alerts = Alert.query.filter(Alert.region == loc.prov).count() if loc.prov else 0
    faq.append((f"Are there any active weather alerts in {loc.name}?",
                f"{region_alerts} in {loc.prov}" if region_alerts else "No"))
    uv = wellbeing.get('uv')
    faq.append((f"What is the UV index right now in {loc.name}?", uv.label if uv else 'Low'))
    faq.append((f"What time is sunrise and sunset today in {loc.name}?", "See Today’s Conditions"))
    return faq


# ---------------------------------------------------------------------------
# Routes — news
# ---------------------------------------------------------------------------

@app.route('/en/news')
def news_index():
    cats = []
    for key, label, subs in NEWS_CATEGORIES:
        latest = (Article.query.filter_by(category_key=key)
                  .order_by(Article.created_at.desc()).limit(4).all())
        cats.append({'key': key, 'label': label, 'subs': subs, 'latest': latest})
    return render_template('news_index.html', **context(cats=cats))


def _resolve_category(cat, sub=None):
    for key, label, subs in NEWS_CATEGORIES:
        if key == cat:
            if sub is None:
                return key, label, subs, None, None
            for sk, sl in subs:
                if sk == sub:
                    return key, label, subs, sk, sl
    return None


@app.route('/en/news/<cat>')
def news_category(cat):
    resolved = _resolve_category(cat)
    if not resolved:
        abort(404)
    key, label, subs, _, _ = resolved
    articles = (Article.query.filter_by(category_key=key)
                .order_by(Article.created_at.desc()).all())
    return render_template('news_category.html', **context(
        cat_key=key, cat_label=label, subs=subs, sub_key=None, sub_label=None,
        articles=articles))


@app.route('/en/news/<cat>/<sub>')
def news_subcategory(cat, sub):
    resolved = _resolve_category(cat, sub)
    if not resolved:
        abort(404)
    key, label, subs, sk, sl = resolved
    articles = (Article.query.filter_by(category_key=key, subcategory_key=sk)
                .order_by(Article.created_at.desc()).all())
    return render_template('news_category.html', **context(
        cat_key=key, cat_label=label, subs=subs, sub_key=sk, sub_label=sl,
        articles=articles))


@app.route('/en/news/author/<slug>')
def author_page(slug):
    author = Author.query.filter_by(slug=slug).first()
    if not author:
        abort(404)
    arts = (Article.query.filter_by(author_id=author.id)
            .order_by(Article.created_at.desc()).all())
    return render_template('author.html', **context(author=author, arts=arts))


@app.route('/en/news/<cat>/<sub>/<slug>')
def article(cat, sub, slug):
    resolved = _resolve_category(cat, sub)
    if not resolved:
        abort(404)
    art = Article.query.filter_by(slug=slug).first()
    if not art or art.category_key != cat or art.subcategory_key != sub:
        abort(404)
    author = db.session.get(Author, art.author_id) if art.author_id else None
    related = []
    for kw in art.kw[:1]:
        related = (Article.query.filter(Article.slug != art.slug,
                                        Article.keywords.like(f'%"{kw}"%'))
                   .order_by(Article.created_at.desc()).limit(4).all())
    if not related:
        related = (Article.query.filter(Article.slug != art.slug,
                                         Article.category_key == art.category_key)
                   .order_by(Article.created_at.desc()).limit(4).all())
    embeds = [v for v in (Video.query.filter_by(mediaid=m).first() for m in art.vids) if v]
    more = (Article.query.filter(Article.slug != art.slug)
            .order_by(Article.created_at.desc()).limit(8).all())
    return render_template('article.html', **context(
        art=art, author=author, related=related, embeds=embeds, more=more,
        cat_key=cat, sub_key=sub))


# ---------------------------------------------------------------------------
# Routes — video
# ---------------------------------------------------------------------------

@app.route('/en/video')
def video_index():
    playlists = {}
    for pid, name in [('oLRZ3mum', 'MUST WATCH'), ('p71u5XZn', 'Animals and Weather')]:
        vids = [v for v in Video.query.all() if pid in v.pls]
        vids.sort(key=lambda v: (-(v.pubdate or 0), v.mediaid))
        playlists[pid] = {'id': pid, 'name': name, 'videos': vids}
    featured = [v for v in Video.query.all() if 'HtPmBhvM' in v.pls]
    featured.sort(key=lambda v: (-(v.pubdate or 0), v.mediaid))
    must_watch = playlists['oLRZ3mum']['videos']
    top = must_watch[0] if must_watch else None
    return render_template('video_index.html', **context(
        playlists=playlists, featured=featured, top=top, feed=feed_items()))


@app.route('/en/video/<mediaid>')
def video_detail(mediaid):
    vid = Video.query.filter_by(mediaid=mediaid).first()
    if not vid:
        abort(404)
    same_pl = None
    for pid in vid.pls:
        if pid in ('oLRZ3mum', 'p71u5XZn'):
            same_pl = [v for v in Video.query.all() if pid in v.pls and v.mediaid != mediaid]
            same_pl.sort(key=lambda v: (-(v.pubdate or 0), v.mediaid))
            same_pl = same_pl[:8]
            break
    return render_template('video_detail.html', **context(vid=vid, same_pl=same_pl))


# ---------------------------------------------------------------------------
# Routes — alerts
# ---------------------------------------------------------------------------

@app.route('/en/alerts/ca')
def alerts_index():
    region = request.args.get('region', 'ALL')
    q = Alert.query
    if region and region != 'ALL':
        prov = REGION_CODES.get(region)
        if not prov:
            abort(404)
        q = q.filter(Alert.region == prov)
    alerts = q.order_by(Alert.region, Alert.location_name).all()
    counts = dict(db.session.query(Alert.region, func.count(Alert.id)).group_by(Alert.region).all())
    return render_template('alerts_index.html', **context(
        alerts=alerts, region=region, counts=counts, total=Alert.query.count(),
        feed=feed_items()))


@app.route('/en/alerts/ca/<placecode>')
def alert_detail(placecode):
    alert = Alert.query.filter_by(placecode=placecode).first()
    if not alert:
        abort(404)
    related = [Article.query.filter_by(slug=r.get('slug')).first() for r in alert.rel]
    related = [a for a in related if a]
    more = (Alert.query.filter(Alert.region == alert.region,
                               Alert.placecode != placecode).all())[:8]
    return render_template('alert_detail.html', **context(alert=alert, related=related, more=more))


# ---------------------------------------------------------------------------
# Routes — maps & channels & hubs
# ---------------------------------------------------------------------------

@app.route('/en/maps/radar')
def maps_radar():
    maps = []
    for slug in RADAR_CITIES:
        loc = Location.query.filter(Location.url_path.endswith(f'/{slug}'),
                                    Location.channel == 'city').first()
        if loc:
            maps.append({'slug': slug, 'loc': loc})
    return render_template('maps.html', **context(maps=maps))


@app.route('/en/vacation')
def vacation():
    """Vacation weather hub: destination cities, grouped by country."""
    countries = [(r[0].lower(), r[1]) for r in (db.session.query(Location.country_code, Location.country)
                   .filter(Location.channel == 'city')
                   .filter(Location.country_code.notin_(['CA']))
                   .distinct().order_by(Location.country).all())]
    entries = []
    for l in (Location.query.filter(Location.channel == 'city')
              .filter(Location.country_code.notin_(['CA']))
              .order_by(Location.country, Location.name).all()):
        entries.append({'loc': l, 'obs': Observation.query.filter_by(loc_id=l.id).first()})
    return render_template('channel_index.html', **context(
        channel='vacation', channel_url='vacation', channel_label='Vacation',
        entries=entries, vacation_copy=SITE_CHROME.get('vacation_copy', ''),
        vacation_countries=countries))


@app.route('/en/vacation/<cc>')
def vacation_country(cc):
    """Per-country vacation index (mirrors the upstream /en/vacation/<cc> pages)."""
    cc = cc.lower()
    country = (db.session.query(Location.country_code, Location.country)
               .filter(Location.channel == 'city',
                       func.lower(Location.country_code) == cc).first())
    if not country:
        abort(404)
    entries = []
    for l in (Location.query.filter(Location.channel == 'city',
                                     func.lower(Location.country_code) == cc)
              .order_by(Location.name).all()):
        entries.append({'loc': l, 'obs': Observation.query.filter_by(loc_id=l.id).first()})
    return render_template('channel_index.html', **context(
        channel='vacation', channel_url='vacation', channel_label='Vacation',
        entries=entries, vacation_copy='', country_page=country[1],
        vacation_countries=[(cc, country[1])]))


@app.route('/en/<any("school","airport","ski","golf","beach","camping","cottage","marine","attraction","park"):channel_url>')
def channel_index(channel_url):
    channel = next((k for k, v in CHANNEL_URL.items() if v == channel_url), None)
    if channel is None:
        abort(404)
    entries = []
    for l in Location.query.filter_by(channel=channel).order_by(Location.name).all():
        entries.append({'loc': l, 'obs': Observation.query.filter_by(loc_id=l.id).first()})
    return render_template('channel_index.html', **context(
        channel=channel, channel_url=channel_url,
        channel_label=CHANNEL_LABEL.get(channel, channel),
        entries=entries, vacation_copy=SITE_CHROME.get('vacation_copy', '')))


HUB_META = {
    'discover-and-learn': {'title': 'Discover & Learn', 'image': 'hub_DiscoverPortugal_386x126.jpg'},
    'indigenous': {'title': 'Indigenous News', 'image': 'hub_Indigenous.png'},
    'el-nino-la-nina': {'title': 'El Niño and La Niña', 'image': 'hub_ElNino.png'},
    'experiencing-canada': {'title': 'Experiencing Canada', 'image': 'hub_ExperienceCanada.jpg'},
}


INFO_PAGES = {
    'help-centre': ('Help Centre', 'Browse forecasts, alerts, maps and news. Sign in to save your favourite locations and switch between metric and imperial units from any page header.'),
    'privacy-policy-global': ('Privacy Policy', 'This offline mirror stores only your session and your saved locations. No data leaves the container.'),
    'terms-of-use': ('Terms Of Use', 'The Weather Network mirror content is captured from the upstream site for offline benchmark use.'),
    'ai-code-of-ethics': ('AI Code of Ethics', 'Our AI Code of Ethics describes how we apply AI responsibly across forecasting and newsroom products.'),
    'accessibility-and-accommodation': ('Accessibility and Accommodation', 'We are committed to accessible experiences across our web and app products.'),
    'about-us': ('About Us', 'The Weather Network is Canada\u2019s most trusted weather brand and news source, delivering forecasts, radar, alerts and weather news across the country.'),
    'weather-apis': ('Weather APIs', 'Pelmorex weather APIs power our forecasts, observations and indices.'),
    'about-our-mobile-apps': ('About Our Mobile Apps', 'The Weather Network apps deliver forecasts, radar and alerts on iOS, Android and TV platforms.'),
    'fast-channels': ('FAST Channels', 'Watch The Weather Network\u2019s free ad-supported streaming channels for live local weather and national coverage.'),
}


@app.route('/en/info/<slug>')
def info_page(slug):
    meta = INFO_PAGES.get(slug)
    if not meta:
        abort(404)
    return render_template('info.html', **context(title=meta[0], body=meta[1]))


@app.route('/en/explore/<hub>')
def explore(hub):
    meta = HUB_META.get(hub)
    if not meta:
        abort(404)
    if hub == 'el-nino-la-nina':
        arts = (Article.query.filter(db.or_(Article.headline.like('%Niño%'),
                                           Article.headline.like('%Nino%'),
                                           Article.headline.like('%La Niña%'),
                                           Article.headline.like('%La Nina%'),
                                           Article.summary.like('%El Niño%'),
                                           Article.summary.like('%La Niña%')))
                .order_by(Article.created_at.desc()).limit(8).all())
    elif hub == 'indigenous':
        arts = (Article.query.filter(Article.keywords.like('%"indigenous"%'))
                .order_by(Article.created_at.desc()).limit(8).all())
    elif hub == 'experiencing-canada':
        arts = (Article.query.filter(Article.subcategory_key == 'travel')
                .order_by(Article.created_at.desc()).limit(8).all())
    else:
        arts = Article.query.order_by(Article.created_at.desc()).limit(8).all()
    return render_template('hub.html', **context(hub=hub, meta=meta, arts=arts))


# ---------------------------------------------------------------------------
# Routes — account
# ---------------------------------------------------------------------------

@app.route('/en/account/sign-in', methods=['GET', 'POST'])
def sign_in():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return render_template('sign_in.html', **context(
                error="We couldn't find an account with those credentials.",
                email=email)), 401
        session['user_id'] = user.id
        session['unit'] = user.unit
        flash(f"Welcome back, {user.display_name or user.username}!")
        return redirect('/en/account')
    return render_template('sign_in.html', **context(error=None, email=''))


@app.route('/en/account/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        display = (request.form.get('display_name') or '').strip() or username
        error = None
        if not re.fullmatch(r'[A-Za-z0-9_]{3,30}', username or ''):
            error = 'Pick a username with 3-30 letters, numbers or underscores.'
        elif '@' not in email or len(email) < 5:
            error = 'Enter a valid email address.'
        elif len(password) < 8:
            error = 'Password must be at least 8 characters.'
        elif User.query.filter_by(email=email).first():
            error = 'An account with that email already exists.'
        elif User.query.filter_by(username=username).first():
            error = 'That username is taken.'
        if error:
            return render_template('register.html', **context(
                error=error, form=request.form)), 400
        user = User(username=username, email=email, display_name=display,
                    unit='metric', created_at=MIRROR_NOW_LOCAL)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        flash(f"Welcome to The Weather Network, {display}!")
        return redirect('/en/account')
    return render_template('register.html', **context(error=None, form={}))


@app.route('/en/account/sign-out', methods=['POST'])
def sign_out():
    session.pop('user_id', None)
    flash('You are signed out.')
    return redirect('/en')


@app.route('/en/account')
def account():
    if not session.get('user_id'):
        return redirect('/en/account/sign-in')
    user = db.session.get(User, session['user_id'])
    if not user:
        session.pop('user_id', None)
        return redirect('/en/account/sign-in')
    rows = []
    for s in (SavedLocation.query.filter_by(user_id=user.id)
              .order_by(SavedLocation.created_at, SavedLocation.id).all()):
        loc = db.session.get(Location, s.loc_id)
        if loc:
            rows.append({'saved': s, 'loc': loc,
                         'obs': Observation.query.filter_by(loc_id=loc.id).first()})
    return render_template('account.html', **context(user=user, rows=rows))


@app.route('/en/account/saved/add', methods=['POST'])
def saved_add():
    if not session.get('user_id'):
        return redirect('/en/account/sign-in')
    code = request.form.get('code') or ''
    loc = Location.query.filter_by(code=code).first()
    if not loc:
        abort(404)
    user_id = session['user_id']
    if not SavedLocation.query.filter_by(user_id=user_id, loc_id=loc.id).first():
        db.session.add(SavedLocation(user_id=user_id, loc_id=loc.id, created_at=MIRROR_NOW_LOCAL))
        db.session.commit()
        flash(f"{loc.name} added to your saved locations.")
    else:
        flash(f"{loc.name} is already in your saved locations.")
    return redirect(request.form.get('next') or '/en/account')


@app.route('/en/account/saved/<int:saved_id>/remove', methods=['POST'])
def saved_remove(saved_id):
    if not session.get('user_id'):
        return redirect('/en/account/sign-in')
    s = db.session.get(SavedLocation, saved_id)
    if not s or s.user_id != session['user_id']:
        abort(404)
    loc = db.session.get(Location, s.loc_id)
    db.session.delete(s)
    db.session.commit()
    if loc:
        flash(f"{loc.name} removed from your saved locations.")
    return redirect(request.form.get('next') or '/en/account')


@app.route('/en/account/preferences', methods=['GET', 'POST'])
def preferences():
    unit = request.values.get('unit')
    if unit not in ('metric', 'imperial'):
        # bare link (no toggle): just bounce back — nothing to change
        return redirect(request.referrer or '/en')
    session['unit'] = unit
    if session.get('user_id'):
        user = db.session.get(User, session['user_id'])
        if user:
            user.unit = unit
            db.session.commit()
    return redirect(request.values.get('next') or request.referrer or '/en')


# ---------------------------------------------------------------------------
# Health & errors
# ---------------------------------------------------------------------------

@app.route('/_health')
def health():
    try:
        import sqlite3
        from pathlib import Path
        uri = app.config['SQLALCHEMY_DATABASE_URI']
        db_path = Path(uri.replace('sqlite:///', '', 1))
        conn = sqlite3.connect(db_path)
        try:
            counts = {}
            for table in ['users', 'locations', 'observations', 'hourly_forecasts',
                          'daily_forecasts', 'monthly_averages', 'wellbeing', 'authors',
                          'articles', 'videos', 'alerts', 'saved_locations']:
                counts[table] = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
            ok = (counts['locations'] >= 500 and counts['articles'] >= 400
                  and counts['videos'] >= 500 and counts['alerts'] >= 40
                  and counts['hourly_forecasts'] >= 20000 and counts['users'] >= 4)
            return {'ok': bool(ok), 'site': 'the_weather_network', 'counts': counts}
        finally:
            conn.close()
    except Exception as exc:  # pragma: no cover
        return {'ok': False, 'site': 'the_weather_network', 'error': str(exc)}, 500


@app.errorhandler(404)
def not_found(_e):
    return render_template('404.html', **context()), 404


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def seed_database():
    """Idempotent content seed — the whole function is gated."""
    import seed_data
    seed_data.db = db
    seed_data.MODELS = {m.__name__: m for m in (
        User, Location, Observation, HourlyForecast, DailyForecast,
        MonthlyAverage, WellBeing, Author, Article, Video, Alert,
        SavedLocation)}
    seed_data.run_seed()


def seed_benchmark_users():
    """Idempotent benchmark users — gated as a whole."""
    import seed_data
    seed_data.db = db
    seed_data.MODELS = {m.__name__: m for m in (
        User, Location, Observation, HourlyForecast, DailyForecast,
        MonthlyAverage, WellBeing, Author, Article, Video, Alert,
        SavedLocation)}
    seed_data.run_user_seed()


if os.environ.get('WEBSYN_SKIP_BOOTSTRAP') != '1':
    with app.app_context():
        db.create_all()
        create_indexes()
        seed_database()
        seed_benchmark_users()
        seed_site_content()
        SITE_CHROME.update(load_site_chrome())
        INLINE_IMAGES.update(_load_inline_map())
        _paths, _slugs, _locs, _byslug = _load_link_sets()
        ARTICLE_PATHS.update(_paths)
        AUTHOR_SLUGS.update(_slugs)
        LOC_PATHS.update(_locs)
        ARTICLE_BY_SLUG.update(_byslug)


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
