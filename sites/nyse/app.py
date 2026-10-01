#!/usr/bin/env python3
"""nyse — a WebHarbor mirror of https://www.nyse.com/

Flask + SQLite mirror of the New York Stock Exchange portal: the home
page with its market movers ticker and Today's Stock Market article, the
Listings Directory (stock / ETF / index / REIT tabs with the upstream
search, sort and pagination), per-symbol quote pages carrying the captured
quote header, company facts, board of directors, total returns, key data,
options chains and the five-year price history chart, the IPO Center
(priced deals, largest recent IPOs, monthly execution, pricing stats,
backlog), the Bell calendar with its event imagery, the markets hub and
the history of the NYSE — plus authenticated watchlists and price alerts
seeded for four benchmark users.

Content comes from the tracked source_data/*.json snapshots captured from
www.nyse.com on 2026-09-29/30 (see provenance.json); the SQLite seed is
materialized deterministically at image build time (PYTHONHASHSEED=0).
"""
import html
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
app.config["SECRET_KEY"] = os.environ.get("NYSE_SECRET_KEY") or "webharbor-nyse-dev-key"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'NYSE_DB_URI', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'nyse.db')}")
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
    'CREATE INDEX IF NOT EXISTS ix_bell_events_etype'
    ' ON bell_events (etype)',
    'CREATE INDEX IF NOT EXISTS ix_bell_events_start_ms'
    ' ON bell_events (start_ms)',
    'CREATE INDEX IF NOT EXISTS ix_board_members_symbol'
    ' ON board_members (symbol)',
    'CREATE INDEX IF NOT EXISTS ix_cms_blocks_page'
    ' ON cms_blocks (page)',
    'CREATE INDEX IF NOT EXISTS ix_directory_rows_tab'
    ' ON directory_rows (tab)',
    'CREATE INDEX IF NOT EXISTS ix_home_meta_section'
    ' ON home_meta (section)',
    'CREATE INDEX IF NOT EXISTS ix_ipo_deals_status'
    ' ON ipo_deals (status)',
    'CREATE INDEX IF NOT EXISTS ix_market_movers_category'
    ' ON market_movers (category)',
    'CREATE INDEX IF NOT EXISTS ix_option_contracts_exp_label'
    ' ON option_contracts (exp_label)',
    'CREATE INDEX IF NOT EXISTS ix_option_contracts_symbol'
    ' ON option_contracts (symbol)',
    'CREATE INDEX IF NOT EXISTS ix_option_expiries_symbol'
    ' ON option_expiries (symbol)',
    'CREATE INDEX IF NOT EXISTS ix_price_alerts_user_id'
    ' ON price_alerts (user_id)',
    'CREATE INDEX IF NOT EXISTS ix_price_bars_symbol'
    ' ON price_bars (symbol)',
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

MIRROR_DATE = date(2026, 9, 29)
MIRROR_TS = '2026-09-29'
SITE_NAME = 'nyse'
UPSTREAM = 'https://www.nyse.com/'
# bcrypt hash of 'TestPass123!' — frozen so the seed DB is byte-reproducible.
BENCHMARK_PASSWORD_HASH = (
    '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')


def _load(name):
    with open(os.path.join(BASE_DIR, 'source_data', name),
              encoding='utf-8') as f:
        return json.load(f)


# ------------------------------------------------------------- inventory --

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
                    # Also key by the exact upstream source URL: a few
                    # upstream files carry the wrong extension, so the
                    # local name is re-keyed to the real byte format.
                    _INVENTORY[row['source_url']] = row['path']
                    for alias in row.get('also_served_at', []):
                        _INVENTORY[alias] = row['path']
    return _INVENTORY


def _img_name(url):
    """Local image for an upstream URL, when the bytes are inventoried."""
    if not url:
        return None
    if url in _inventory():
        return _inventory()[url].split('static/')[-1]
    name = url.split('/')[-1].split('?')[0]
    if name in _inventory():
        return _inventory()[name].split('static/')[-1]
    return None


def img(url):
    """Template helper: full static path or None."""
    local = _img_name(url)
    return url_for('static', filename=local) if local else None


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
    added_at = db.Column(db.String(10))


class PriceAlert(db.Model):
    __tablename__ = 'price_alerts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    symbol = db.Column(db.String(24), nullable=False)
    direction = db.Column(db.String(8), nullable=False)   # above / below
    threshold = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(200))
    created_at = db.Column(db.String(10), nullable=False)


class DirectoryRow(db.Model):
    __tablename__ = 'directory_rows'
    id = db.Column(db.Integer, primary_key=True)
    tab = db.Column(db.String(8), nullable=False)  # equity/etf/reit/index
    symbol = db.Column(db.String(24), nullable=False)
    name = db.Column(db.Text, nullable=False)
    mic = db.Column(db.String(8), nullable=False)
    quote_url = db.Column(db.String(255), nullable=False)


class Quote(db.Model):
    __tablename__ = 'quotes'
    symbol = db.Column(db.String(24), primary_key=True)
    exchg = db.Column(db.String(8))
    dispname = db.Column(db.String(32))
    name = db.Column(db.Text)
    last = db.Column(db.Float)
    change = db.Column(db.Float)
    pctchg = db.Column(db.Float)
    volume = db.Column(db.Integer)
    quote_time = db.Column(db.Text)
    low = db.Column(db.Float)
    high = db.Column(db.Float)
    open = db.Column(db.Float)
    ave_vol = db.Column(db.Integer)
    ann_low = db.Column(db.Float)
    ann_high = db.Column(db.Float)
    prev = db.Column(db.Float)
    bid = db.Column(db.Float)
    ask = db.Column(db.Float)
    bid_size = db.Column(db.Integer)
    ask_size = db.Column(db.Integer)
    cusip = db.Column(db.String(16))
    last_update_time = db.Column(db.String(16))
    wl52date = db.Column(db.String(48))
    wh52date = db.Column(db.String(48))
    dividend = db.Column(db.Float)
    div_date = db.Column(db.String(48))
    div_yield = db.Column(db.Float)
    div_int = db.Column(db.Integer)
    beta = db.Column(db.Float)
    eps = db.Column(db.Float)
    trade_size = db.Column(db.Integer)
    # company facts (null for indices)
    ceo = db.Column(db.Text)
    country = db.Column(db.String(4))
    sector = db.Column(db.String(64))
    market_cap = db.Column(db.Float)
    shares_outstanding = db.Column(db.Float)
    website = db.Column(db.String(128))
    incorporated_year = db.Column(db.String(16))
    # total returns panel
    ret_1m = db.Column(db.Float)
    ret_3m = db.Column(db.Float)
    ret_6m = db.Column(db.Float)
    ret_52w = db.Column(db.Float)
    ret_3y = db.Column(db.Float)
    volatility = db.Column(db.Float)
    rsi = db.Column(db.Float)
    symbol_type = db.Column(db.String(24))
    future_ex_date = db.Column(db.String(16))
    # rich data present?
    is_rich = db.Column(db.Integer, nullable=False, default=0)
    history_bars = db.Column(db.Integer, nullable=False, default=0)
    opt_expiries = db.Column(db.Integer, nullable=False, default=0)


class BoardMember(db.Model):
    __tablename__ = 'board_members'
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(24), db.ForeignKey('quotes.symbol'),
                       nullable=False)
    name = db.Column(db.Text, nullable=False)
    term_in_years = db.Column(db.Integer)


class PriceBar(db.Model):
    __tablename__ = 'price_bars'
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(24), db.ForeignKey('quotes.symbol'),
                       nullable=False)
    date = db.Column(db.String(10), nullable=False)
    open = db.Column(db.Float)
    high = db.Column(db.Float)
    low = db.Column(db.Float)
    close = db.Column(db.Float)
    volume = db.Column(db.Integer)


class OptionExpiry(db.Model):
    __tablename__ = 'option_expiries'
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(24), db.ForeignKey('quotes.symbol'),
                       nullable=False)
    position = db.Column(db.Integer, nullable=False)
    label = db.Column(db.String(48), nullable=False)


class OptionContract(db.Model):
    __tablename__ = 'option_contracts'
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(24), db.ForeignKey('quotes.symbol'),
                       nullable=False)
    exp_label = db.Column(db.String(48), nullable=False)
    exp_pos = db.Column(db.Integer, nullable=False, default=1)
    kind = db.Column(db.String(4), nullable=False)    # call / put
    strike = db.Column(db.Float, nullable=False)
    recent = db.Column(db.Float)
    bid = db.Column(db.Float)
    ask = db.Column(db.Float)
    volume = db.Column(db.Integer)
    open_int = db.Column(db.Float)


class BellEvent(db.Model):
    __tablename__ = 'bell_events'
    id = db.Column(db.String(32), primary_key=True)
    title = db.Column(db.Text, nullable=False)
    etype = db.Column(db.String(24), nullable=False)
    start_ms = db.Column(db.Integer, nullable=False)
    end_ms = db.Column(db.Integer, nullable=False)
    date_label = db.Column(db.String(64), nullable=False)
    time_label = db.Column(db.String(64))
    description = db.Column(db.Text)
    image = db.Column(db.String(255))
    media_json = db.Column(db.Text)

    def media_list(self):
        try:
            return json.loads(self.media_json or '[]')
        except json.JSONDecodeError:
            return []

    def plain_title(self):
        # Upstream renders the bell titles with the numeric HTML entities
        # decoded (® í é ™ …); the raw capture keeps the entity form, so
        # decode at render time to match what the live page shows.
        return html.unescape(self.title or '')

    def plain_description(self):
        text = re.sub(r'<[^>]+>', ' ', self.description or '')
        # Decode the full entity vocabulary the upstream feed uses
        # (&#0174; &#0237; &#8217; &#8482; &#0233; &amp; &quot; …) — the
        # live pages show the decoded characters, not the literal entities.
        text = html.unescape(text)
        return re.sub(r'\s+', ' ', text).strip()


class MarketMover(db.Model):
    __tablename__ = 'market_movers'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(16), nullable=False)
    symbol = db.Column(db.String(24), nullable=False)
    name = db.Column(db.Text, nullable=False)
    volume = db.Column(db.Integer)
    last_price = db.Column(db.Float)
    change = db.Column(db.Float)
    pctchg = db.Column(db.Float)


class IpoDeal(db.Model):
    __tablename__ = 'ipo_deals'
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(24))
    issuer = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(24), nullable=False)
    exchange = db.Column(db.String(64))
    industry = db.Column(db.String(64))
    price_date_ms = db.Column(db.Integer)
    price_date = db.Column(db.String(16))
    filed_date_ms = db.Column(db.Integer)
    filed_date = db.Column(db.String(16))
    amended_date_ms = db.Column(db.Integer)
    amended_date = db.Column(db.String(16))
    offer_price = db.Column(db.Float)
    price_range = db.Column(db.String(32))
    range_vs_offer = db.Column(db.String(16))
    proceeds = db.Column(db.Float)
    filed_proceeds = db.Column(db.Float)
    shares_filed = db.Column(db.Integer)
    offer_shares = db.Column(db.Integer)
    bookrunners = db.Column(db.Text)
    expected_date = db.Column(db.String(16))
    withdrawn_txt = db.Column(db.String(64))


class IpoLargest(db.Model):
    __tablename__ = 'ipo_largest'
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(24))
    issuer = db.Column(db.Text, nullable=False)
    exchange = db.Column(db.String(64))
    industry = db.Column(db.String(64))
    price_date_ms = db.Column(db.Integer)
    price_date = db.Column(db.String(16))
    filed_date_ms = db.Column(db.Integer)
    filed_date = db.Column(db.String(16))
    offer_1day = db.Column(db.Float)
    offer_current = db.Column(db.Float)
    range_vs_offer = db.Column(db.String(16))
    proceeds = db.Column(db.Float)
    bookrunners = db.Column(db.Text)
    issue_type = db.Column(db.String(16))


class IpoMonthly(db.Model):
    __tablename__ = 'ipo_monthly'
    id = db.Column(db.Integer, primary_key=True)
    month_ms = db.Column(db.Integer, nullable=False)
    month_label = db.Column(db.String(16), nullable=False)
    deals = db.Column(db.Integer, nullable=False)
    proceeds = db.Column(db.Float, nullable=False)


class IpoSectorStat(db.Model):
    __tablename__ = 'ipo_sector_stats'
    id = db.Column(db.Integer, primary_key=True)
    sector = db.Column(db.String(64), nullable=False)
    deals = db.Column(db.Integer, nullable=False)
    priced_above = db.Column(db.Integer, nullable=False)
    priced_within = db.Column(db.Integer, nullable=False)
    priced_below = db.Column(db.Integer, nullable=False)
    pct_above = db.Column(db.Integer)
    pct_within = db.Column(db.Integer)
    pct_below = db.Column(db.Integer)
    avg_1day = db.Column(db.Float)
    avg_30day = db.Column(db.Float)
    proceeds = db.Column(db.Float)


class IpoBacklog(db.Model):
    __tablename__ = 'ipo_backlog'
    id = db.Column(db.Integer, primary_key=True)
    industry = db.Column(db.String(64), nullable=False)
    current_deals = db.Column(db.Integer, nullable=False)
    current_proceeds = db.Column(db.Float, nullable=False)
    historical_deals = db.Column(db.Integer, nullable=False)
    historical_proceeds = db.Column(db.Float, nullable=False)


class CmsBlock(db.Model):
    __tablename__ = 'cms_blocks'
    id = db.Column(db.Integer, primary_key=True)
    page = db.Column(db.String(24), nullable=False)
    slot = db.Column(db.Integer, nullable=False)
    heading = db.Column(db.Text)
    body_json = db.Column(db.Text, nullable=False)

    def body(self):
        try:
            return json.loads(self.body_json or '[]')
        except json.JSONDecodeError:
            return []


class HomeMeta(db.Model):
    __tablename__ = 'home_meta'
    id = db.Column(db.Integer, primary_key=True)
    section = db.Column(db.String(24), nullable=False)
    payload_json = db.Column(db.Text, nullable=False)

    def payload(self):
        try:
            return json.loads(self.payload_json or '{}')
        except json.JSONDecodeError:
            return {}


# -------------------------------------------------------------- login glue --

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ------------------------------------------------------------------ helpers --

@app.context_processor
def template_helpers():
    return {'img': img, 'fmt_price': fmt_price, 'fmt_volume': fmt_volume,
            'fmt_pct': fmt_pct, 'fmt_money': fmt_money}


TAB_LABELS = {
    'stock': ('equity', 'Stocks'),
    'etf': ('etf', 'ETFs'),
    'index': ('index', 'Indices'),
    'reit': ('reit', 'REITs'),
}

MIC_NAMES = {
    'XNYS': 'NYSE',
    'XNCM': 'NYSE',
    'XNMS': 'NYSE',
    'XASE': 'NYSE American',
    'ARCX': 'NYSE Arca',
    'BATS': 'Cboe BZX',
    'XNGS': 'NASDAQ',
    'XNAS': 'NASDAQ',
    'TXSE': 'TXSE',
    'GIF': 'Index',
    'IDX': 'Index',
}


def quote_href(mic, symbol):
    if mic in ('IDX', 'GIF'):
        return f'/quote/index/{symbol}'
    return f'/quote/{mic}:{symbol}'


def sym_href(symbol):
    """Quote URL for a symbol using one of its captured directory MICs."""
    row = DirectoryRow.query.filter_by(symbol=symbol).first()
    if row:
        return quote_href(row.mic, symbol)
    return f'/quote/XNYS:{symbol}'


def _num(value):
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value):
    n = _num(value)
    return int(n) if n is not None else None


def fmt_money(value):
    if value is None:
        return '--'
    if abs(value) >= 1e12:
        return f'{value/1e12:,.2f}T'
    if abs(value) >= 1e9:
        return f'{value/1e9:,.2f}B'
    if abs(value) >= 1e6:
        return f'{value/1e6:,.2f}M'
    return f'{value:,.0f}'


def fmt_volume(value):
    if value is None:
        return '--'
    return f'{value:,}'


def fmt_price(value):
    if value is None:
        return '--'
    return f'{value:,.2f}' if abs(value) < 10000 else f'{value:,.2f}'


def fmt_pct(value):
    if value is None:
        return '--'
    return f'{value:.2f}'


def alert_state(alert):
    """Deterministic alert status against the frozen snapshot price."""
    quote = db.session.get(Quote, alert.symbol)
    if not quote or quote.last is None:
        return 'pending'
    if alert.direction == 'above' and quote.last >= alert.threshold:
        return 'triggered'
    if alert.direction == 'below' and quote.last <= alert.threshold:
        return 'triggered'
    return 'pending'


def parse_page(value, default=1):
    try:
        return max(1, int(value or default))
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------- svg chart --

def price_chart(bars, width=860, height=260):
    """Server-side SVG close-price chart for the zoom window."""
    if not bars:
        return None
    closes = [b['close'] for b in bars]
    lo, hi = min(closes), max(closes)
    span = (hi - lo) or 1.0
    step = width / max(1, len(bars) - 1)
    points = []
    for i, c in enumerate(closes):
        x = i * step
        y = height - ((c - lo) / span) * (height - 30) - 10
        points.append(f'{x:.1f},{y:.1f}')
    path = 'M ' + ' L '.join(points)
    area = path + f' L {width},{height} L 0,{height} Z'
    return {'path': path, 'area': area, 'lo': lo, 'hi': hi,
            'first_date': bars[0]['date'], 'last_date': bars[-1]['date'],
            'width': width, 'height': height}


ZOOM_DAYS = {'1W': 7, '1M': 30, '3M': 91, '1Y': 365, '5Y': 1300}


# -------------------------------------------------------------------- routes --

@app.route('/')
def home():
    movers = MarketMover.query.filter_by(category='nyse') \
        .order_by(MarketMover.id).all()
    ticker_note = 'Market data delayed minimum of 15 minutes'
    hero = HomeMeta.query.filter_by(section='hero').first()
    hero = hero.payload() if hero else {}
    article = HomeMeta.query.filter_by(section='article').first()
    article = article.payload() if article else {}
    cards = HomeMeta.query.filter_by(section='cards').first()
    cards = cards.payload() if cards else []
    shows = HomeMeta.query.filter_by(section='shows').first()
    shows = shows.payload() if shows else []
    whats = HomeMeta.query.filter_by(section='whats_next').first()
    whats = whats.payload() if whats else []
    bells = BellEvent.query.order_by(BellEvent.start_ms.desc()).limit(4).all()
    priced = IpoDeal.query.filter_by(status='Priced') \
        .order_by(IpoDeal.price_date_ms.desc()).limit(4).all()
    for d in priced:
        d.href = sym_href(d.symbol) if d.symbol else None
    for item in whats:
        item['img'] = img(item.get('image'))
    collage_meta = HomeMeta.query.filter_by(section='collage').first()
    collage = collage_meta.payload() if collage_meta else []
    collage_images = [u for u in collage if img(u)]
    return render_template('home.html', movers=movers, hero=hero,
                           article=article, cards=cards, shows=shows,
                           whats_next=whats, bells=bells, priced=priced,
                           collage_images=collage_images,
                           ticker_note=ticker_note)


@app.route('/market-update')
def market_update():
    article = HomeMeta.query.filter_by(section='article').first()
    article = article.payload() if article else {}
    return render_template('market_update.html', article=article)


@app.route('/listings')
def listings():
    blocks = CmsBlock.query.filter_by(page='listings') \
        .order_by(CmsBlock.slot).all()
    meta = HomeMeta.query.filter_by(section='listings_meta').first()
    return render_template('listings.html', blocks=blocks,
                           meta=meta.payload() if meta else {}, img=img)


@app.route('/history-of-nyse')
def history():
    blocks = CmsBlock.query.filter_by(page='history') \
        .order_by(CmsBlock.slot).all()
    images = HomeMeta.query.filter_by(section='history_images').first()
    images = images.payload() if images else []
    for image in images:
        image['img'] = img(image.get('src'))
    return render_template('history.html', blocks=blocks, images=images)


@app.route('/markets')
def markets():
    nyse = MarketMover.query.filter_by(category='nyse') \
        .order_by(MarketMover.id).all()
    american = MarketMover.query.filter_by(category='nyse_american') \
        .order_by(MarketMover.id).all()
    note = 'Market data delayed minimum of 15 minutes'
    symbols = {m.symbol for m in nyse} | {m.symbol for m in american}
    quote_exists = {s: db.session.get(Quote, s) is not None
                     for s in symbols}
    return render_template('markets.html', movers_nyse=nyse,
                           movers_american=american, note=note,
                           quote_exists=quote_exists,
                           fmt_price=fmt_price, fmt_volume=fmt_volume)


@app.route('/listings_directory/<tab>')
def listings_directory(tab):
    if tab not in TAB_LABELS:
        abort(404)
    data_tab, label = TAB_LABELS[tab]
    q = (request.args.get('q') or '').strip()
    sort = request.args.get('sort') or 'symbol'
    order = request.args.get('order') or 'asc'
    page = parse_page(request.args.get('page'))
    query = DirectoryRow.query.filter_by(tab=data_tab)
    if q:
        like = f'%{q}%'
        query = query.filter(db.or_(DirectoryRow.symbol.ilike(like),
                                   DirectoryRow.name.ilike(like)))
    if sort == 'name':
        col = DirectoryRow.name
    else:
        col, sort = DirectoryRow.symbol, 'symbol'
    query = query.order_by(col.asc() if order != 'desc' else col.desc(),
                           DirectoryRow.symbol)
    total = query.count()
    per_page = 20
    pages = max(1, -(-total // per_page))
    page = min(page, pages)
    rows = query.offset((page - 1) * per_page).limit(per_page).all()
    # Which of the page's symbols resolve to a captured quote payload?
    quotes_present = {}
    for r in rows:
        quotes_present[r.symbol] = db.session.get(Quote, r.symbol) is not None
    counts = {}
    for tab_key, _label in TAB_LABELS.values():
        counts[tab_key] = DirectoryRow.query.filter_by(tab=tab_key).count()
    return render_template('directory.html', tab=tab, label=label, rows=rows,
                           total=total, q=q, sort=sort, order=order,
                           page=page, pages=pages, counts=counts,
                           quotes_present=quotes_present,
                           mic_names=MIC_NAMES, quote_href=quote_href)


@app.route('/quote/<path:spec>')
def quote(spec=None):
    if ':' not in spec:
        abort(404)
    mic, symbol = spec.split(':', 1)
    return quote_page(mic, symbol, index=False)


@app.route('/quote/index/<symbol>')
def quote_index(symbol):
    return quote_page('IDX', symbol)


def quote_page(mic, symbol, index=False):
    row = Quote.query.get(symbol)
    if not row:
        abort(404)
    if not index and mic not in ('IDX', 'GIF'):
        # The exchange in the URL must match one of the captured listings.
        mics = {m for (m,) in db.session.query(DirectoryRow.mic)
                .filter_by(symbol=symbol).all()}
        if mics and mic not in mics:
            abort(404)
    board = BoardMember.query.filter_by(symbol=symbol) \
        .order_by(BoardMember.id).all()
    zoom = request.args.get('zoom') or '6M'
    bars = []
    chart = None
    exp_tab = parse_page(request.args.get('exp'), 1)
    expiries = []
    option_rows = []
    put_call_ratio = None
    if row.is_rich:
        all_bars = PriceBar.query.filter_by(symbol=symbol) \
            .order_by(PriceBar.date).all()
        days = ZOOM_DAYS.get(zoom, 183)
        window = all_bars[-days:]
        bars = [{'date': b.date, 'close': b.close} for b in window]
        chart = price_chart(bars)
        expiries = [e.label for e in OptionExpiry.query.filter_by(
            symbol=symbol).order_by(OptionExpiry.position).all()]
        exp_tab = min(max(1, exp_tab), max(1, len(expiries)))
        if expiries:
            current = expiries[exp_tab - 1]
            option_rows = OptionContract.query.filter_by(
                symbol=symbol, exp_label=current) \
                .order_by(OptionContract.strike).all()
        calls = db.session.query(db.func.sum(OptionContract.open_int)) \
            .filter_by(symbol=symbol, kind='call').scalar() or 0
        puts = db.session.query(db.func.sum(OptionContract.open_int)) \
            .filter_by(symbol=symbol, kind='put').scalar() or 0
        put_call_ratio = round(puts / calls, 2) if calls else None
    in_watch = False
    alert_rows = []
    if current_user.is_authenticated:
        in_watch = WatchItem.query.filter_by(
            user_id=current_user.id, symbol=symbol).first() is not None
        alert_rows = PriceAlert.query.filter_by(
            user_id=current_user.id, symbol=symbol) \
            .order_by(PriceAlert.id).all()
    strikes = {}
    for opt in option_rows:
        strikes.setdefault(opt.strike, {})[opt.kind] = opt
    spec = f'index/{symbol}' if index else f'{mic}:{symbol}'
    return render_template(
        'quote.html', q=row, board=board, chart=chart, zoom=zoom,
        expiries=expiries, exp_tab=exp_tab, strikes=sorted(strikes),
        strike_rows=strikes, put_call_ratio=put_call_ratio,
        in_watch=in_watch, alerts=alert_rows, spec=spec,
        mic_name=MIC_NAMES.get(mic, mic), quote_href=quote_href,
        alert_state=alert_state)


@app.route('/ipo-center/recent-ipo')
def ipo_recent():
    # The upstream "Priced Deals" table lists only deals that actually
    # priced (status Priced); filed / expected / withdrawn / postponed
    # rows live on the Filings page, exactly as on the live site.
    deals = IpoDeal.query.filter_by(status='Priced') \
        .order_by(IpoDeal.price_date_ms.desc()).all()
    window = request.args.get('window') or '30'
    if window not in ('30', '90', '180'):
        window = '30'
    days = int(window)
    largest = IpoLargest.query.all()
    horizon_ms = days * 86400 * 1000
    newest = max((d.price_date_ms or 0) for d in largest) if largest else 0
    shown = sorted((d for d in largest
                    if d.price_date_ms and newest - d.price_date_ms <= horizon_ms),
                   key=lambda d: -(d.proceeds or 0))[:10]
    monthly = IpoMonthly.query.order_by(IpoMonthly.month_ms).all()
    updated = 'September 30, 2026 5:49 AM EDT'
    source = 'S&P Global'
    return render_template('ipo_recent.html', deals=deals, largest=shown,
                           monthly=monthly, window=window,
                           updated=updated, source=source,
                           fmt_money=fmt_money, fmt_price=fmt_price)


@app.route('/ipo-center/ipo-pricing-stats')
def ipo_pricing_stats():
    rows = IpoSectorStat.query.order_by(IpoSectorStat.sector).all()
    updated = 'September 30, 2026 5:49 AM EDT'
    source = 'S&P Global'
    return render_template('ipo_pricing_stats.html', rows=rows,
                           updated=updated, source=source, fmt_money=fmt_money)


@app.route('/ipo-center/filings')
def ipo_filings():
    status = request.args.get('status') or ''
    exchange = request.args.get('exchange') or ''
    query = IpoDeal.query
    if status:
        query = query.filter_by(status=status)
    if exchange:
        query = query.filter(IpoDeal.exchange.ilike(f'%{exchange}%'))
    rows = query.order_by(IpoDeal.price_date_ms.desc()).all()
    statuses = sorted({d.status for d in IpoDeal.query.all()})
    exchanges = sorted({(d.exchange or '') for d in IpoDeal.query.all()
                        if d.exchange})
    return render_template('ipo_filings.html', rows=rows, statuses=statuses,
                           exchanges=exchanges, status=status,
                           exchange=exchange, fmt_money=fmt_money,
                           fmt_price=fmt_price)


@app.route('/ipo-center/backlog')
def ipo_backlog():
    rows = IpoBacklog.query.order_by(IpoBacklog.industry).all()
    total_current = sum(r.current_deals for r in rows)
    total_proceeds = sum(r.current_proceeds for r in rows)
    return render_template('ipo_backlog.html', rows=rows,
                           total_current=total_current,
                           total_proceeds=total_proceeds,
                           fmt_money=fmt_money)


@app.route('/bell')
def bell():
    intro = HomeMeta.query.filter_by(section='bell_intro').first()
    recent = BellEvent.query.order_by(BellEvent.start_ms.desc()).limit(6).all()
    return render_template('bell.html', intro=intro.payload() if intro else {},
                          recent=recent, img=img)


@app.route('/bell/calendar')
def bell_calendar():
    etype = request.args.get('type') or ''
    q = (request.args.get('q') or '').strip()
    start = (request.args.get('from') or '').strip()
    end = (request.args.get('to') or '').strip()
    page = parse_page(request.args.get('page'))
    query = BellEvent.query
    if etype:
        query = query.filter_by(etype=etype)
    if q:
        like = f'%{q}%'
        query = query.filter(BellEvent.title.ilike(like))
    if start:
        try:
            ms = int(datetime.strptime(start, '%Y-%m-%d')
                     .replace(tzinfo=timezone.utc).timestamp() * 1000)
            query = query.filter(BellEvent.start_ms >= ms)
        except ValueError:
            pass
    if end:
        try:
            ms = int((datetime.strptime(end, '%Y-%m-%d')
                      .replace(tzinfo=timezone.utc).timestamp()) * 1000
                     + 86399999)
            query = query.filter(BellEvent.start_ms <= ms)
        except ValueError:
            pass
    total = query.count()
    per_page = 15
    pages = max(1, -(-total // per_page))
    page = min(page, pages)
    rows = query.order_by(BellEvent.start_ms.desc()) \
        .offset((page - 1) * per_page).limit(per_page).all()
    types = sorted({e.etype for e in BellEvent.query.all()})
    return render_template('bell_calendar.html', rows=rows, total=total,
                           etype=etype, q=q, start=start, end=end,
                           page=page, pages=pages, types=types, img=img)


@app.route('/search')
def search():
    q = (request.args.get('q') or '').strip()
    symbol_rows, events, ipos = [], [], []
    if q:
        like = f'%{q}%'
        matches = Quote.query.filter(db.or_(
            Quote.symbol.ilike(like), Quote.name.ilike(like))) \
            .order_by(Quote.symbol).limit(30).all()
        for s in matches:
            d = DirectoryRow.query.filter_by(symbol=s.symbol).first()
            href = quote_href(d.mic, s.symbol) if d else None
            symbol_rows.append({'quote': s, 'href': href})
        events = BellEvent.query.filter(BellEvent.title.ilike(like)) \
            .order_by(BellEvent.start_ms.desc()).limit(12).all()
        ipos = IpoDeal.query.filter(IpoDeal.issuer.ilike(like)) \
            .order_by(IpoDeal.price_date_ms.desc()).limit(12).all()
    return render_template('search.html', q=q, symbol_rows=symbol_rows,
                           events=events, ipos=ipos, img=img)


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


@app.route('/watchlist')
@login_required
def watchlist():
    rows = WatchItem.query.filter_by(user_id=current_user.id) \
        .order_by(WatchItem.id).all()
    items = []
    for row in rows:
        quote = db.session.get(Quote, row.symbol)
        if quote:
            items.append({'row': row, 'quote': quote,
                          'href': sym_href(row.symbol)})
    return render_template('watchlist.html', items=items,
                           fmt_price=fmt_price, fmt_pct=fmt_pct,
                           fmt_volume=fmt_volume, quote_href=quote_href)


@app.route('/watchlist/toggle', methods=['POST'])
@login_required
def watchlist_toggle():
    symbol = (request.form.get('symbol') or '').strip()
    if not symbol or not db.session.get(Quote, symbol):
        abort(400)
    row = WatchItem.query.filter_by(user_id=current_user.id,
                                    symbol=symbol).first()
    if row:
        db.session.delete(row)
        db.session.commit()
        return redirect(request.form.get('back') or url_for('watchlist'))
    db.session.add(WatchItem(user_id=current_user.id, symbol=symbol,
                             added_at=MIRROR_TS))
    db.session.commit()
    return redirect(request.form.get('back') or url_for('watchlist'))


@app.route('/alerts')
@login_required
def alerts():
    rows = PriceAlert.query.filter_by(user_id=current_user.id) \
        .order_by(PriceAlert.id).all()
    items = [{'row': r, 'quote': db.session.get(Quote, r.symbol),
              'state': alert_state(r), 'href': sym_href(r.symbol)}
             for r in rows]
    return render_template('alerts.html', items=items,
                           fmt_price=fmt_price, quote_href=quote_href)


@app.route('/alerts/create', methods=['POST'])
@login_required
def alerts_create():
    symbol = (request.form.get('symbol') or '').strip()
    direction = request.form.get('direction') or ''
    threshold_raw = (request.form.get('threshold') or '').strip()
    note = (request.form.get('note') or '').strip()
    quote = db.session.get(Quote, symbol) if symbol else None
    if not quote:
        abort(400)
    try:
        threshold = float(threshold_raw)
    except ValueError:
        threshold = None
    if direction not in ('above', 'below') or threshold is None \
            or threshold <= 0:
        return render_template('alerts_error.html', quote=quote,
                               href=sym_href(symbol),
                               message='Choose a direction and a positive '
                                       'target price.'), 400
    db.session.add(PriceAlert(user_id=current_user.id, symbol=symbol,
                              direction=direction, threshold=threshold,
                              note=note or None, created_at=MIRROR_TS))
    db.session.commit()
    return redirect(url_for('alerts'))


@app.route('/alerts/delete', methods=['POST'])
@login_required
def alerts_delete():
    alert_id = request.form.get('id') or ''
    row = db.session.get(PriceAlert, int(alert_id)) if alert_id.isdigit() else None
    if row and row.user_id == current_user.id:
        db.session.delete(row)
        db.session.commit()
    return redirect(url_for('alerts'))


# -------------------------------------------------------------- error pages --

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


# -------------------------------------------------------------------- seeds --

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
    if os.environ.get('NYSE_AUTO_SEED', '1') == '1':
        seed_database()
        seed_benchmark_users()
