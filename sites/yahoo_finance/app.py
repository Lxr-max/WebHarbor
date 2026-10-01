#!/usr/bin/env python3
"""yahoo_finance — a WebHarbor mirror of https://finance.yahoo.com/

Flask + SQLite mirror of Yahoo Finance: the home page with its market
strip, index cards, trending tickers, movers and news rail; symbol search
(lookup) across quotes and news; quote pages with the Summary / Statistics /
Financials / Profile / History / News tabs, watchlist toggles and price
alerts; the stock screener with the six captured predefined screens plus
sector / industry / valuation / dividend / price filters; the earnings
calendar with week + day + symbol filtering; the news hub with its three
captured topics, keyword search and article pages; and the sector &
industry comparison pages computed from the captured universe — plus
authenticated watchlists and price alerts seeded for four benchmark users.

Market data comes from the tracked source_data/*.json snapshots captured
from finance.yahoo.com on 2026-10-01 UTC (the public quote, quoteSummary,
chart, screener, trending, earnings-visualization and news-stream APIs,
see provenance.json); the SQLite seed is materialized deterministically at
image build time (PYTHONHASHSEED=0).
"""
import math
import json
import os
import re
from datetime import date, datetime, timezone

from flask import (Flask, abort, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_bcrypt import Bcrypt
from flask_login import (LoginManager, UserMixin, current_user,
                         login_required, login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from markupsafe import Markup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, instance_path=os.path.join(BASE_DIR, 'instance'))
app.config["SECRET_KEY"] = os.environ.get("YF_SECRET_KEY") or "webharbor-yahoo-finance-dev-key"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'YF_DB_URI', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'yahoo_finance.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

db = SQLAlchemy(app)

# ---- deterministic schema creation -------------------------------------
# SQLAlchemy's create_all() emits CREATE INDEX statements in Table.indexes
# set order; that set is keyed by object identity, so the DDL order varies
# between processes and two seed builds would not be byte-identical. We
# therefore declare no index=True columns and create the indexes here in
# sorted order, with tables created in sorted-name order as well.
SCHEMA_INDEX_DDL = (
    'CREATE INDEX IF NOT EXISTS ix_chart_points_symbol'
    ' ON chart_points (symbol)',
    'CREATE INDEX IF NOT EXISTS ix_earnings_events_start_dt'
    ' ON earnings_events (start_dt)',
    'CREATE INDEX IF NOT EXISTS ix_earnings_events_ticker'
    ' ON earnings_events (ticker)',
    'CREATE INDEX IF NOT EXISTS ix_income_rows_symbol'
    ' ON income_rows (symbol)',
    'CREATE INDEX IF NOT EXISTS ix_news_articles_hosted'
    ' ON news_articles (hosted)',
    'CREATE INDEX IF NOT EXISTS ix_news_articles_pub_time'
    ' ON news_articles (pub_time)',
    'CREATE INDEX IF NOT EXISTS ix_price_alerts_user_id'
    ' ON price_alerts (user_id)',
    'CREATE INDEX IF NOT EXISTS ix_screener_presets_preset_id'
    ' ON screener_presets (preset_id)',
    'CREATE INDEX IF NOT EXISTS ix_trending_items_rank'
    ' ON trending_items (rank)',
    'CREATE INDEX IF NOT EXISTS ix_watch_items_user_id'
    ' ON watch_items (user_id)',
)


def create_schema():
    """Create all tables and indexes in a deterministic order."""
    tables = [db.metadata.tables[name]
              for name in sorted(db.metadata.tables)]
    db.metadata.create_all(db.engine, tables=tables)
    from sqlalchemy import text as _sa_text
    with db.engine.begin() as conn:
        for stmt in SCHEMA_INDEX_DDL:
            conn.execute(_sa_text(stmt))


bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to continue.'
csrf = CSRFProtect(app)

# The mirror's frozen market date: quotes, calendar and news were captured
# after the 2026-09-30 close (2026-10-01 UTC); every wall-clock the app
# renders is anchored here so the snapshot is self-consistent.
MIRROR_DATE = date(2026, 9, 30)
MIRROR_TS = '2026-09-30'
SITE_NAME = 'yahoo_finance'
UPSTREAM = 'https://finance.yahoo.com/'

# bcrypt hash of 'TestPass123!' — frozen so the seed DB is byte-reproducible.
BENCHMARK_PASSWORD_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')

DEFAULT_WEEK = ('2026-09-27', '2026-10-03')


# ------------------------------------------------------------- inventory --

_QUOTE_SYMBOLS = None


@app.context_processor
def _inject_quote_symbols():
    """Captured quote symbols, for templates that link ticker mentions.

    The upstream capture references far more tickers than the 318-quote
    snapshot the mirror ships; links to uncaptured symbols would dead-end
    on the 404 page, so templates hyperlink a ticker only when the mirror
    can actually serve its quote (the same captured-only idiom the home
    page's trending table already uses).
    """
    global _QUOTE_SYMBOLS
    if _QUOTE_SYMBOLS is None:
        _QUOTE_SYMBOLS = {sym for (sym,) in db.session.query(Quote.symbol)}
    return {'quote_symbols': _QUOTE_SYMBOLS}


_INVENTORY = None


def _inventory():
    global _INVENTORY
    if _INVENTORY is None:
        _INVENTORY = {}
        path = os.path.join(BASE_DIR, 'asset_inventory.json')
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                for row in json.load(f).get('assets', []):
                    _INVENTORY[row['source_url']] = row['path']
    return _INVENTORY


def img(url):
    """Template helper: local static path for an upstream image URL, or None."""
    if not url:
        return None
    local = _inventory().get(url)
    return url_for('static', filename=local.split('static/')[-1]) if local else None


def img_name(url):
    if not url:
        return None
    local = _inventory().get(url)
    return local.split('static/')[-1] if local else None


# ----------------------------------------------------------------- models --

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    joined = db.Column(db.String(10))


class WatchItem(db.Model):
    __tablename__ = 'watch_items'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    symbol = db.Column(db.String(24), nullable=False)
    added_at = db.Column(db.String(10), nullable=False)


class PriceAlert(db.Model):
    __tablename__ = 'price_alerts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    symbol = db.Column(db.String(24), nullable=False)
    direction = db.Column(db.String(8), nullable=False)   # above / below
    threshold = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(200))
    created_at = db.Column(db.String(10), nullable=False)


class Quote(db.Model):
    __tablename__ = 'quotes'
    symbol = db.Column(db.String(24), primary_key=True)
    short_name = db.Column(db.Text)
    long_name = db.Column(db.Text)
    quote_type = db.Column(db.String(12), nullable=False, default='EQUITY')
    exchange = db.Column(db.String(12))
    full_exchange = db.Column(db.String(48))
    currency = db.Column(db.String(8))
    market_state = db.Column(db.String(16))
    quote_time = db.Column(db.String(64))
    price = db.Column(db.Float)
    change = db.Column(db.Float)
    change_pct = db.Column(db.Float)
    prev_close = db.Column(db.Float)
    open = db.Column(db.Float)
    bid = db.Column(db.Float)
    ask = db.Column(db.Float)
    bid_size = db.Column(db.Integer)
    ask_size = db.Column(db.Integer)
    day_low = db.Column(db.Float)
    day_high = db.Column(db.Float)
    volume = db.Column(db.BigInteger)
    avg_vol_3m = db.Column(db.BigInteger)
    market_cap = db.Column(db.Float)
    pe_ttm = db.Column(db.Float)
    pe_forward = db.Column(db.Float)
    peg_ratio = db.Column(db.Float)
    eps_ttm = db.Column(db.Float)
    eps_forward = db.Column(db.Float)
    price_book = db.Column(db.Float)
    book_value = db.Column(db.Float)
    div_rate = db.Column(db.Float)
    div_yield = db.Column(db.Float)          # percent, e.g. 0.33
    payout_ratio = db.Column(db.Float)
    div_date = db.Column(db.String(24))
    exdiv_date = db.Column(db.String(24))
    beta = db.Column(db.Float)
    wk52_low = db.Column(db.Float)
    wk52_high = db.Column(db.Float)
    wk52_change_pct = db.Column(db.Float)
    day50_avg = db.Column(db.Float)
    day200_avg = db.Column(db.Float)
    profit_margin = db.Column(db.Float)
    operating_margin = db.Column(db.Float)
    roe = db.Column(db.Float)
    roa = db.Column(db.Float)
    revenue = db.Column(db.Float)
    revenue_growth = db.Column(db.Float)
    gross_profit = db.Column(db.Float)
    ebitda = db.Column(db.Float)
    total_cash = db.Column(db.Float)
    total_debt = db.Column(db.Float)
    debt_equity = db.Column(db.Float)
    current_ratio = db.Column(db.Float)
    shares_outstanding = db.Column(db.Float)
    held_insiders = db.Column(db.Float)
    held_institutions = db.Column(db.Float)
    target_mean = db.Column(db.Float)
    recommendation = db.Column(db.String(24))
    rec_mean = db.Column(db.Float)
    num_analysts = db.Column(db.Integer)
    earnings_date = db.Column(db.String(24))
    fiscal_year_end = db.Column(db.String(24))
    sector = db.Column(db.String(64))
    industry = db.Column(db.String(96))
    website = db.Column(db.String(160))
    country = db.Column(db.String(48))
    employees = db.Column(db.Integer)
    city = db.Column(db.String(48))
    state = db.Column(db.String(48))
    phone = db.Column(db.String(48))
    description = db.Column(db.Text)
    logo_url = db.Column(db.String(255))


class IncomeRow(db.Model):
    __tablename__ = 'income_rows'
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(24), nullable=False)
    year_end = db.Column(db.String(24), nullable=False)
    revenue = db.Column(db.Float)
    cost_revenue = db.Column(db.Float)
    gross_profit = db.Column(db.Float)
    operating_income = db.Column(db.Float)
    net_income = db.Column(db.Float)
    ebitda = db.Column(db.Float)
    diluted_eps = db.Column(db.Float)
    rd_expense = db.Column(db.Float)


class EarningsEvent(db.Model):
    __tablename__ = 'earnings_events'
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(24), nullable=False)
    company = db.Column(db.Text)
    event_name = db.Column(db.Text)
    start_dt = db.Column(db.String(32), nullable=False)   # ISO datetime
    day = db.Column(db.String(10), nullable=False)        # YYYY-MM-DD
    time_type = db.Column(db.String(8))                   # BMO/AMC/TAS/...
    date_is_estimate = db.Column(db.Integer, nullable=False, default=0)
    eps_estimate = db.Column(db.Float)
    eps_actual = db.Column(db.Float)
    surprise_pct = db.Column(db.Float)
    market_cap = db.Column(db.Float)
    tz = db.Column(db.String(16))


class NewsArticle(db.Model):
    __tablename__ = 'news_articles'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(16), nullable=False)
    title = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text)
    provider = db.Column(db.String(96))
    provider_id = db.Column(db.String(96))
    hosted = db.Column(db.Integer, nullable=False, default=0)
    live_blog = db.Column(db.Integer, nullable=False, default=0)
    pub_time = db.Column(db.String(32), nullable=False)  # ISO datetime
    url_path = db.Column(db.String(255), nullable=False)
    upstream_url = db.Column(db.String(500), nullable=False)
    thumb_url = db.Column(db.String(255))
    thumb_name = db.Column(db.String(120))
    tickers = db.Column(db.Text, nullable=False, default='')
    topics = db.Column(db.Text, nullable=False, default='')
    body = db.Column(db.Text, nullable=False, default='')
    author = db.Column(db.String(96))


class ScreenerPreset(db.Model):
    __tablename__ = 'screener_presets'
    id = db.Column(db.Integer, primary_key=True)
    preset_id = db.Column(db.String(32), nullable=False)
    title = db.Column(db.String(96), nullable=False)
    description = db.Column(db.Text)
    total = db.Column(db.Integer)
    rows = db.Column(db.Text, nullable=False, default='[]')


class TrendingItem(db.Model):
    __tablename__ = 'trending_items'
    id = db.Column(db.Integer, primary_key=True)
    rank = db.Column(db.Integer, nullable=False)
    symbol = db.Column(db.String(24), nullable=False)


class ChartPoint(db.Model):
    __tablename__ = 'chart_points'
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(24), nullable=False)
    bar_date = db.Column(db.String(10), nullable=False)
    close = db.Column(db.Float, nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ------------------------------------------------------------- formatting --

def fmt_num(value, decimals=2):
    if value is None:
        return 'N/A'
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 'N/A'
    if value == int(value) and abs(value) < 1e15:
        return f'{int(value):,}'
    return f'{value:,.{decimals}f}'


def fmt_price(value, decimals=2):
    if value is None:
        return 'N/A'
    try:
        return f'{float(value):,.{decimals}f}'
    except (TypeError, ValueError):
        return 'N/A'


def fmt_big(value):
    """Compact big-number rendering: 4.86T / 112.21B / 190.42M / 53.52K."""
    if value is None:
        return 'N/A'
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 'N/A'
    sign = '-' if v < 0 else ''
    v = abs(v)
    for div, suffix in ((1e12, 'T'), (1e9, 'B'), (1e6, 'M'), (1e3, 'K')):
        if v >= div:
            s = f'{v / div:,.2f}'.rstrip('0').rstrip('.')
            return f'{sign}{s}{suffix}'
    return f'{sign}{int(v):,}'


def fmt_pct(value, decimals=2, sign=False):
    if value is None:
        return 'N/A'
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 'N/A'
    s = '+' if (sign and v > 0) else ''
    return f'{s}{v:,.{decimals}f}%'


def fmt_signed(value, decimals=2):
    if value is None:
        return 'N/A'
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 'N/A'
    s = '+' if v > 0 else ''
    return f'{s}{v:,.{decimals}f}'


def fmt_int(value):
    if value is None:
        return 'N/A'
    try:
        return f'{int(value):,}'
    except (TypeError, ValueError):
        return 'N/A'


def month_day_year(iso_date):
    """2026-09-30 -> September 30, 2026 (upstream's calendar rendering)."""
    try:
        d = date.fromisoformat(str(iso_date)[:10])
    except (ValueError, TypeError):
        return iso_date
    return f'{d.strftime("%B")} {d.day}, {d.year}'


def rel_time(iso_ts):
    """Upstream's relative-time rendering against the mirror date."""
    try:
        dt = datetime.fromisoformat(str(iso_ts).replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return iso_ts
    anchor = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
    delta = (anchor - dt).total_seconds()
    if delta < 0:
        return month_day_year(iso_ts[:10])
    hours = int(delta // 3600)
    if hours < 1:
        return f'{max(int(delta // 60), 1)} minutes ago'
    if hours < 24:
        return f'{hours} hours ago'
    days = hours // 24
    if days == 1:
        return '1 day ago'
    return f'{days} days ago'


def from_json(value):
    try:
        return json.loads(value) if value else []
    except (ValueError, TypeError):
        return []


app.jinja_env.filters['from_json'] = from_json
app.jinja_env.globals.update(
    fmt_num=fmt_num, fmt_price=fmt_price, fmt_big=fmt_big,
    fmt_pct=fmt_pct, fmt_signed=fmt_signed, fmt_int=fmt_int,
    month_day_year=month_day_year, rel_time=rel_time)


# ------------------------------------------------------------------ data ----

STRIP_ORDER = ['ES=F', 'NQ=F', 'YM=F', 'RTY=F', '^TNX', '^VIX', 'GC=F',
               'BTC-USD', 'CL=F']
STRIP_LABELS = {
    'ES=F': 'S&P Futures', 'NQ=F': 'Nasdaq Futures', 'YM=F': 'Dow Futures',
    'RTY=F': 'Russell 2000 Futures', '^TNX': '10-Yr Bond', '^VIX': 'VIX',
    'GC=F': 'Gold', 'BTC-USD': 'Bitcoin USD', 'CL=F': 'Crude Oil',
}
INDEX_CARDS = ['^GSPC', '^DJI', '^IXIC', '^RUT']
SECTOR_ORDER = [
    'Technology', 'Communication Services', 'Consumer Cyclical',
    'Consumer Defensive', 'Healthcare', 'Financial Services',
    'Basic Materials', 'Industrials', 'Energy', 'Utilities', 'Real Estate',
]
PRESET_ORDER = [
    ('day_gainers', 'Day Gainers'),
    ('day_losers', 'Day Losers'),
    ('most_actives', 'Most Actives'),
    ('small_cap_gainers', 'Small Cap Gainers'),
    ('aggressive_small_caps', 'Aggressive Small Caps'),
    ('growth_technology_stocks', 'Growth Technology Stocks'),
]


def quote_or_404(symbol):
    q = db.session.get(Quote, symbol)
    if not q:
        abort(404)
    return q


def symbol_href(symbol):
    from urllib.parse import quote
    return '/quote/' + quote(str(symbol))


def parse_tickers(blob):
    try:
        return json.loads(blob) if blob else []
    except ValueError:
        return []


def _preset_rows(preset):
    try:
        return json.loads(preset.rows)
    except ValueError:
        return []


def _preset_view(row):
    """Screener preset rows use Yahoo's {'raw','fmt'} cells; keep both."""
    def cell(v):
        if isinstance(v, dict):
            return v.get('raw')
        return v
    return {
        'symbol': row.get('ticker') or row.get('symbol'),
        'name': row.get('companyName') or row.get('shortName'),
        'price': cell(row.get('regularMarketPrice')),
        'change_pct': cell(row.get('regularMarketChangePercent')),
        'change': cell(row.get('regularMarketChange')),
        'volume': cell(row.get('regularMarketVolume')),
        'mcap': cell(row.get('marketCap')),
        'pe': cell(row.get('peRatioLtm')),
        'avg_rating': row.get('averageRating'),
        'sector': row.get('sector'),
        'industry': row.get('industry'),
        'wk52_high': cell(row.get('fiftyTwoWeekHigh')),
        'wk52_low': cell(row.get('fiftyTwoWeekLow')),
        'wk52_change': cell(row.get('fiftyTwoWeekChangePercent')),
    }


# ------------------------------------------------------------------ routes --

@app.route('/')
def home():
    strip = [db.session.get(Quote, s) for s in STRIP_ORDER]
    strip = [s for s in strip if s]
    cards = [db.session.get(Quote, s) for s in INDEX_CARDS]
    cards = [c for c in cards if c]
    trending = (db.session.query(TrendingItem).order_by(TrendingItem.rank)
                .limit(10).all())
    trending_quotes = [(t.rank, db.session.get(Quote, t.symbol))
                       for t in trending]
    trending_quotes = [(r, q) for r, q in trending_quotes if q]
    movers = {}
    for pid, _title in PRESET_ORDER[:3]:
        preset = db.session.query(ScreenerPreset).filter_by(
            preset_id=pid).first()
        if preset:
            rows = [_preset_view(r) for r in _preset_rows(preset)][:5]
            movers[pid] = {'title': preset.title, 'rows': rows}
    news = (db.session.query(NewsArticle)
            .order_by(NewsArticle.pub_time.desc()).limit(6).all())
    return render_template('home.html', strip=strip, cards=cards,
                           trending=trending_quotes, movers=movers,
                           news=news, strip_labels=STRIP_LABELS,
                           lead_news=NewsArticle.query.filter(NewsArticle.thumb_name.isnot(None), NewsArticle.thumb_name != "").order_by(NewsArticle.pub_time.desc()).first())


@app.route('/lookup')
def lookup():
    q = (request.args.get('s') or request.args.get('q') or '').strip()
    quotes = []
    news = []
    if q:
        like = f'%{q}%'
        quotes = (db.session.query(Quote)
                  .filter(db.or_(Quote.symbol.ilike(like),
                                 Quote.short_name.ilike(like),
                                 Quote.long_name.ilike(like)))
                  .order_by(Quote.market_cap.desc().nullslast()).limit(12).all())
        news = (db.session.query(NewsArticle)
                .filter(db.or_(NewsArticle.title.ilike(like),
                               NewsArticle.summary.ilike(like)))
                .order_by(NewsArticle.pub_time.desc()).limit(10).all())
    return render_template('lookup.html', q=q, quotes=quotes, news=news)


@app.route('/search')
def search():
    return redirect('/lookup?' + request.query_string.decode() if
                    request.query_string else '/lookup')


def _quote_news(q):
    like = f'%{q.symbol}%'
    return (db.session.query(NewsArticle)
            .filter(NewsArticle.tickers.ilike(like))
            .order_by(NewsArticle.pub_time.desc()).limit(8).all())


def _chart_points(symbol):
    return (db.session.query(ChartPoint)
            .filter(ChartPoint.symbol == symbol)
            .order_by(ChartPoint.bar_date).all())


def _chart_svg(points, width=640, height=220):
    """Inline sparkline rendered from the captured daily closes."""
    closes = [p.close for p in points]
    if len(closes) < 2:
        return None
    lo, hi = min(closes), max(closes)
    span = (hi - lo) or 1.0
    pad = 8
    n = len(closes) - 1
    coords = []
    for i, c in enumerate(closes):
        x = pad + (width - 2 * pad) * (i / n)
        y = pad + (height - 2 * pad) * (1 - (c - lo) / span)
        coords.append((round(x, 1), round(y, 1)))
    up = closes[-1] >= closes[0]
    stroke = '#1a9e5c' if up else '#c31d1d'
    d_line = 'M' + ' L'.join(f'{x} {y}' for x, y in coords)
    area = (f'M{coords[0][0]} {height - 2} L' +
            ' L'.join(f'{x} {y}' for x, y in coords) +
            f' L{coords[-1][0]} {height - 2} Z')
    fill = '#1a9e5c14' if up else '#c31d1d14'
    return Markup(f'<svg viewBox="0 0 {width} {height}" class="quote-chart" '
                  f'role="img" aria-label="Daily close chart"><path d="{area}" '
                  f'fill="{fill}"/><path d="{d_line}" fill="none" '
                  f'stroke="{stroke}" stroke-width="2"/></svg>')


@app.route('/quote/<symbol>')
def quote_summary(symbol):
    q = quote_or_404(symbol)
    points = _chart_points(symbol)
    svg = _chart_svg(points)
    news = _quote_news(q)
    income = (db.session.query(IncomeRow)
              .filter(IncomeRow.symbol == q.symbol)
              .order_by(IncomeRow.year_end).all())
    watching = False
    if current_user.is_authenticated:
        watching = db.session.query(WatchItem).filter_by(
            user_id=current_user.id, symbol=q.symbol).first() is not None
    alerts = []
    if current_user.is_authenticated:
        alerts = (db.session.query(PriceAlert)
                  .filter_by(user_id=current_user.id, symbol=q.symbol)
                  .order_by(PriceAlert.id).all())
    return render_template('quote_summary.html', q=q, svg=svg, news=news,
                           income=income, watching=watching, alerts=alerts)


@app.route('/quote/<symbol>/statistics')
def quote_statistics(symbol):
    q = quote_or_404(symbol)
    return render_template('quote_statistics.html', q=q)


@app.route('/quote/<symbol>/financials')
def quote_financials(symbol):
    q = quote_or_404(symbol)
    income = (db.session.query(IncomeRow)
              .filter(IncomeRow.symbol == q.symbol)
              .order_by(IncomeRow.year_end).all())
    return render_template('quote_financials.html', q=q, income=income)


@app.route('/quote/<symbol>/profile')
def quote_profile(symbol):
    q = quote_or_404(symbol)
    return render_template('quote_profile.html', q=q)


@app.route('/quote/<symbol>/history')
def quote_history(symbol):
    q = quote_or_404(symbol)
    points = _chart_points(symbol)
    return render_template('quote_history.html', q=q, points=points)


@app.route('/quote/<symbol>/news')
def quote_news(symbol):
    q = quote_or_404(symbol)
    news = _quote_news(q)
    return render_template('quote_news.html', q=q, news=news)


# --------------------------------------------------------------- screener --

MCAP_BANDS = [
    ('nano', 'Nano Cap', 0, 5e8),
    ('micro', 'Micro Cap', 5e8, 2e9),
    ('small', 'Small Cap', 2e9, 1e10),
    ('mid', 'Mid Cap', 1e10, 1e11),
    ('large', 'Large Cap', 1e11, 2e11),
    ('mega', 'Mega Cap', 2e11, None),
]

SORT_COLUMNS = {
    'mcap': ('market_cap', 'Market Cap'),
    'pe': ('pe_ttm', 'P/E (TTM)'),
    'price': ('price', 'Price'),
    'change': ('change_pct', '% Change'),
    'volume': ('volume', 'Volume'),
    'yield': ('div_yield', 'Div Yield %'),
    'symbol': ('symbol', 'Symbol'),
}


def _fnum(name, default=None):
    raw = request.args.get(name)
    if raw is None or str(raw).strip() == '':
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@app.route('/screener')
def screener():
    preset_id = request.args.get('preset') or 'day_gainers'
    sectors = [s for s in SECTOR_ORDER
               if db.session.query(Quote).filter_by(sector=s).count()]
    industries = sorted({r[0] for r in db.session.query(Quote.industry)
                         .filter(Quote.industry.isnot(None)).distinct()
                         if r[0]})

    preset = db.session.query(ScreenerPreset).filter_by(
        preset_id=preset_id).first()

    # custom filter view
    flt = {
        'sector': request.args.get('sector') or '',
        'industry': request.args.get('industry') or '',
        'mcap_min': _fnum('mcap_min'),
        'mcap_max': _fnum('mcap_max'),
        'pe_min': _fnum('pe_min'),
        'pe_max': _fnum('pe_max'),
        'price_min': _fnum('price_min'),
        'price_max': _fnum('price_max'),
        'yield_min': _fnum('yield_min'),
        'change_min': _fnum('change_min'),
    }
    sort_key = request.args.get('sort') or 'mcap'
    sort_col = SORT_COLUMNS.get(sort_key, SORT_COLUMNS['mcap'])[0]
    sort_dir = request.args.get('dir') or 'desc'

    query = db.session.query(Quote).filter(
        Quote.quote_type.in_(['EQUITY', 'ETF']))
    if flt['sector']:
        query = query.filter(Quote.sector == flt['sector'])
    if flt['industry']:
        query = query.filter(Quote.industry == flt['industry'])
    if flt['mcap_min'] is not None:
        query = query.filter(Quote.market_cap >= flt['mcap_min'])
    if flt['mcap_max'] is not None:
        query = query.filter(Quote.market_cap <= flt['mcap_max'])
    if flt['pe_min'] is not None:
        query = query.filter(Quote.pe_ttm >= flt['pe_min'])
    if flt['pe_max'] is not None:
        query = query.filter(Quote.pe_ttm <= flt['pe_max'])
    if flt['price_min'] is not None:
        query = query.filter(Quote.price >= flt['price_min'])
    if flt['price_max'] is not None:
        query = query.filter(Quote.price <= flt['price_max'])
    if flt['yield_min'] is not None:
        query = query.filter(Quote.div_yield >= flt['yield_min'])
    if flt['change_min'] is not None:
        query = query.filter(Quote.change_pct >= flt['change_min'])
    col = getattr(Quote, sort_col)
    order = col.desc() if sort_dir == 'desc' else col.asc()
    query = query.order_by(order.nullslast(), Quote.symbol)
    matches = query.count()
    rows = query.limit(50).all()

    preset_view = None
    if preset:
        preset_view = {
            'preset_id': preset.preset_id,
            'title': preset.title,
            'description': preset.description,
            'total': preset.total,
            'rows': [_preset_view(r) for r in _preset_rows(preset)],
        }
    return render_template('screener.html', presets=PRESET_ORDER,
                           preset=preset_view, rows=rows, flt=flt,
                           sectors=sectors, industries=industries,
                           mcap_bands=MCAP_BANDS, sort_key=sort_key,
                           sort_dir=sort_dir, matches=matches,
                           sort_columns=SORT_COLUMNS)


# ----------------------------------------------------- earnings calendar --

def _week_bounds(anchor_day):
    """Sunday..Saturday week containing anchor_day (YYYY-MM-DD) — the
    upstream calendar's own week convention."""
    d = date.fromisoformat(anchor_day)
    sunday = d.toordinal() - ((d.weekday() + 1) % 7)
    from datetime import timedelta
    start = date.fromordinal(sunday)
    return start.isoformat(), (start + timedelta(days=6)).isoformat()


def _week_days(start_iso):
    from datetime import timedelta
    start = date.fromisoformat(start_iso)
    return [(start + timedelta(days=i)).isoformat() for i in range(7)]


@app.route('/calendar/earnings')
def calendar_earnings():
    from datetime import timedelta
    anchor = request.args.get('day') or '2026-09-30'
    try:
        date.fromisoformat(anchor)
    except ValueError:
        anchor = '2026-09-30'
    start, end = _week_bounds(anchor)
    days = _week_days(start)
    prev_week = (date.fromisoformat(start) - timedelta(days=7)).isoformat()
    next_week = (date.fromisoformat(start) + timedelta(days=7)).isoformat()
    this_week = DEFAULT_WEEK[0]
    all_events = (db.session.query(EarningsEvent)
                  .filter(EarningsEvent.day >= start,
                          EarningsEvent.day <= end)
                  .order_by(EarningsEvent.start_dt,
                            EarningsEvent.ticker).all())
    symbol_q = (request.args.get('symbol') or '').strip().upper()
    time_filter = request.args.get('time') or ''
    events = all_events
    if symbol_q:
        events = [e for e in events if symbol_q in e.ticker.upper()]
    if time_filter in ('BMO', 'AMC'):
        events = [e for e in events if e.time_type == time_filter]
    counts = {}
    for e in all_events:
        counts[e.day] = counts.get(e.day, 0) + 1
    return render_template('calendar_earnings.html', anchor=anchor,
                           start=start, end=end, days=days, events=events,
                           counts=counts, symbol_q=symbol_q,
                           time_filter=time_filter, prev_week=prev_week,
                           next_week=next_week, this_week=this_week)


# ------------------------------------------------------------------ news --

NEWS_TOPICS = [
    ('stock-market-news', 'Latest Stock Market News'),
    ('economy', 'Economy'),
    ('earnings', 'Earnings'),
]


@app.route('/news')
def news_home():
    topic = request.args.get('topic') or 'latest'
    q = (request.args.get('q') or '').strip()
    page = max(int(request.args.get('page') or 1), 1)
    query = db.session.query(NewsArticle)
    if topic != 'latest':
        query = query.filter(NewsArticle.topics.ilike(f'%{topic}%'))
    if q:
        like = f'%{q}%'
        query = query.filter(db.or_(NewsArticle.title.ilike(like),
                                    NewsArticle.summary.ilike(like)))
    total = query.count()
    articles = (query.order_by(NewsArticle.pub_time.desc())
                .offset((page - 1) * 15).limit(15).all())
    return render_template('news.html', topics=NEWS_TOPICS, topic=topic,
                           q=q, articles=articles, page=page, total=total,
                           pages=max((total + 14) // 15, 1))


@app.route('/news/<key>')
def news_article_by_key(key):
    art = db.session.query(NewsArticle).filter_by(key=key).first()
    if not art:
        abort(404)
    return redirect(art.url_path)


def _serve_article(url_path):
    art = db.session.query(NewsArticle).filter_by(url_path=url_path).first()
    if not art:
        # A few captured upstream paths are stored percent-encoded (%, :, ',
        # unicode punctuation); the router hands us the decoded form, so
        # retry with the canonical re-encoding before giving up.
        from urllib.parse import quote
        art = db.session.query(NewsArticle).filter_by(
            url_path=quote(url_path, safe='/')).first()
    if not art:
        return None
    related = []
    tickers = parse_tickers(art.tickers)
    if tickers:
        like = f'%{tickers[0]}%'
        related = (db.session.query(NewsArticle)
                   .filter(NewsArticle.id != art.id,
                           NewsArticle.tickers.ilike(like))
                   .order_by(NewsArticle.pub_time.desc()).limit(4).all())
    return render_template('article.html', art=art, related=related,
                           tickers=tickers)


# --------------------------------------------------------------- sectors --

@app.route('/sectors')
def sectors():
    rows = []
    for sector in SECTOR_ORDER:
        quotes = (db.session.query(Quote)
                  .filter(Quote.sector == sector,
                          Quote.quote_type == 'EQUITY').all())
        if not quotes:
            continue
        caps = [q.market_cap or 0 for q in quotes]
        chg = [q.change_pct or 0 for q in quotes]
        wsum = sum(abs(c) for c in caps) or 1.0
        day_chg = sum(c * abs(w) for c, w in zip(chg, caps)) / wsum
        by_chg = sorted([q for q in quotes if q.change_pct is not None],
                        key=lambda q: q.change_pct)
        top_gainer = by_chg[-1]
        top_loser = by_chg[0]
        industries = sorted({q.industry for q in quotes if q.industry})
        rows.append({
            'sector': sector,
            'slug': sector.lower().replace(' ', '-'),
            'count': len(quotes),
            'mcap': sum(caps),
            'day_chg': day_chg,
            'top_gainer': top_gainer,
            'top_loser': top_loser,
            'industries': industries,
        })
    rows.sort(key=lambda r: r['mcap'], reverse=True)
    return render_template('sectors.html', rows=rows)


@app.route('/sectors/<slug>')
def sector_detail(slug):
    name = slug.replace('-', ' ').title()
    sector = next((s for s in SECTOR_ORDER if s.lower().replace(' ', '-') == slug), None)
    if not sector:
        abort(404)
    quotes = (db.session.query(Quote)
              .filter(Quote.sector == sector)
              .order_by(Quote.market_cap.desc().nullslast()).all())
    equities = [q for q in quotes if q.quote_type == 'EQUITY']
    by_industry = {}
    for q in equities:
        by_industry.setdefault(q.industry or 'Other', []).append(q)
    industries = []
    for ind in sorted(by_industry):
        members = sorted(by_industry[ind],
                         key=lambda q: -(q.market_cap or 0))
        avg_chg = (sum(q.change_pct or 0 for q in members) / len(members)
                   if members else None)
        industries.append({'name': ind, 'members': members, 'avg_chg': avg_chg})
    return render_template('sector_detail.html', sector=sector, slug=slug,
                           quotes=equities, industries=industries)


@app.route('/trending')
def trending():
    items = (db.session.query(TrendingItem)
             .order_by(TrendingItem.rank).all())
    rows = [(i.rank, db.session.get(Quote, i.symbol)) for i in items]
    rows = [(r, q) for r, q in rows if q]
    return render_template('trending.html', rows=rows)


# ------------------------------------------------------------ watch/alert --

@app.route('/watchlist')
@login_required
def watchlist():
    items = (db.session.query(WatchItem)
             .filter_by(user_id=current_user.id)
             .order_by(WatchItem.id).all())
    rows = [(item, db.session.get(Quote, item.symbol)) for item in items]
    rows = [(i, q) for i, q in rows if q]
    return render_template('watchlist.html', rows=rows)


@app.route('/watchlist/toggle', methods=['POST'])
@login_required
def watchlist_toggle():
    symbol = (request.form.get('symbol') or '').strip()
    back = request.form.get('back') or '/watchlist'
    q = db.session.get(Quote, symbol)
    if not q:
        abort(404)
    row = db.session.query(WatchItem).filter_by(
        user_id=current_user.id, symbol=symbol).first()
    if row:
        db.session.delete(row)
    else:
        db.session.add(WatchItem(user_id=current_user.id, symbol=symbol,
                                 added_at=MIRROR_TS))
    db.session.commit()
    if not back.startswith('/'):
        back = '/watchlist'
    return redirect(back)


@app.route('/alerts')
@login_required
def alerts():
    rows = (db.session.query(PriceAlert)
            .filter_by(user_id=current_user.id)
            .order_by(PriceAlert.id).all())
    pairs = []
    for row in rows:
        q = db.session.get(Quote, row.symbol)
        status = 'Active'
        if q and q.price is not None and row.threshold is not None:
            if row.direction == 'above' and q.price >= row.threshold:
                status = 'Triggered'
            elif row.direction == 'below' and q.price <= row.threshold:
                status = 'Triggered'
        pairs.append((row, q, status))
    return render_template('alerts.html', rows=pairs)


@app.route('/alerts/create', methods=['POST'])
@login_required
def alerts_create():
    symbol = (request.form.get('symbol') or '').strip()
    direction = request.form.get('direction') or ''
    note = (request.form.get('note') or '').strip()
    back = request.form.get('back') or '/alerts'
    q = db.session.get(Quote, symbol)
    if not q:
        abort(404)
    try:
        threshold = float(request.form.get('threshold'))
    except (TypeError, ValueError):
        threshold = None
    if direction not in ('above', 'below') or threshold is None \
            or not math.isfinite(threshold) or threshold <= 0:
        return render_template('alerts_error.html', quote=q,
                               href=symbol_href(symbol),
                               message='Choose a direction and a positive '
                                       'target price.'), 400
    db.session.add(PriceAlert(user_id=current_user.id, symbol=symbol,
                              direction=direction, threshold=threshold,
                              note=note or None, created_at=MIRROR_TS))
    db.session.commit()
    if not back.startswith('/'):
        back = '/alerts'
    return redirect(back)


@app.route('/alerts/delete', methods=['POST'])
@login_required
def alerts_delete():
    alert_id = request.form.get('id') or ''
    row = db.session.get(PriceAlert, int(alert_id)) if alert_id.isdigit() else None
    if row and row.user_id == current_user.id:
        db.session.delete(row)
        db.session.commit()
    return redirect(url_for('alerts'))


# ------------------------------------------------------------------- auth --

@app.route('/login', methods=['GET', 'POST'])
def login():
    nxt = request.args.get('next') or request.form.get('next') or ''
    if not nxt.startswith('/'):
        nxt = '/'
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        user = db.session.query(User).filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash,
                                               request.form.get('password')):
            login_user(user)
            return redirect(nxt)
        return render_template('login.html', error='Invalid email or '
                               'password.', next=nxt), 401
    return render_template('login.html', error=None, next=nxt)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        if not name or '@' not in email or len(password) < 8:
            return render_template('signup.html', error='Enter a name, a '
                                   'valid email and a password of at least 8 '
                                   'characters.'), 400
        if db.session.query(User).filter_by(email=email).first():
            return render_template('signup.html', error='An account with '
                                   'that email already exists.'), 400
        user = User(email=email, name=name,
                   password_hash=bcrypt.generate_password_hash(password).decode(),
                   joined=MIRROR_TS)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect('/')
    return render_template('signup.html', error=None)


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    logout_user()
    return redirect('/')


# -------------------------------------------------------------- fallbacks --

@app.route('/<path:page>')
def catchall(page):
    """Serve article pages at their upstream paths (e.g.
    /markets/live/stock-market-today-...html) before the 404."""
    rendered = _serve_article('/' + page)
    if rendered is not None:
        return rendered
    abort(404)


@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


# ------------------------------------------------------------------ seeds --

def seed_database():
    if Quote.query.count() > 0:
        return
    from seed_lib import seed_all
    seed_all(db)


def seed_benchmark_users():
    from seed_lib import seed_benchmark_users as _s
    _s(db)


def main():
    with app.app_context():
        create_schema()
        seed_database()
        seed_benchmark_users()


with app.app_context():
    create_schema()
    if os.environ.get('YF_AUTO_SEED', '1') == '1':
        seed_database()
        seed_benchmark_users()
