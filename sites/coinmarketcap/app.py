#!/usr/bin/env python3
"""coinmarketcap — a WebHarbor mirror of https://coinmarketcap.com/

Flask + SQLite mirror of CoinMarketCap (crypto market-data vertical):
the top-100 ranking table with the upstream filter taxonomy (type,
category, market cap / price / 24h% / volume ranges, sortable columns,
pagination), coin detail pages with the full captured metrics, supply
details, ATH/ATL, contract addresses, About text, similar coins and
server-rendered historical charts (1D/7D/1M/3M/1Y/YTD/All) plus a
historical OHLCV table, per-coin spot markets, exchange rankings
(spot/DEX/derivatives) with exchange detail pages and market-pair
tables, category (/view/<tag>/) pages, leaderboards (gainers & losers,
trending, most viewed, upcoming), historical snapshots, the converter
calculator, the glossary, the FAQ, and the watchlist feature (guest
session watchlist + logged-in saved watchlists) seeded for four
benchmark users.

Content comes from the tracked source_data/*.json snapshots captured
from coinmarketcap.com and api.coinmarketcap.com on 2026-09-29/30 UTC
with plain HTTP + headless Chromium for the client-rendered islands
(see provenance.json); the SQLite seed is materialized deterministically
at image build time (PYTHONHASHSEED=0).
"""
import json
import math
import os
from datetime import datetime, timedelta, timezone

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
app.config["SECRET_KEY"] = os.environ.get("COINMARKETCAP_SECRET_KEY") or "webharbor-coinmarketcap-dev-key"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'COINMARKETCAP_DB_URI', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'coinmarketcap.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to continue.'
csrf = CSRFProtect(app)

# The mirror is a frozen snapshot of the upstream site taken 2026-09-29/30 UTC.
MIRROR_DATE = "2026-09-29"
SITE_NAME = "coinmarketcap"
UPSTREAM = "https://coinmarketcap.com/"
SOURCE = os.path.join(BASE_DIR, 'source_data')

PER_PAGE = 100
CHART_RANGES = ['1D', '7D', '1M', '3M', '1Y', 'YTD', 'All']

# The upstream filter panel's exact range buckets (captured 2026-09-29).
MCAP_BUCKETS = [
    ('', 'All'), ('0~1000000', '<$1M'), ('1000000~10000000', '$1M - $10M'),
    ('10000000~100000000', '$10M - $100M'), ('100000000~1000000000', '$100M - $1B'),
    ('1000000000~10000000000', '$1B - $10B'), ('10000000000~100000000000', '$10B - $100B'),
    ('100000000000~1000000000000', '$100B - $1T'), ('1000000000000~', '>$1T'),
]
PRICE_BUCKETS = [
    ('', 'All'), ('0~1', '<$1'), ('1~10', '$1 - $10'), ('10~100', '$10 - $100'),
    ('100~1000', '$100 - $1k'), ('1000~10000', '$1k - $10k'),
    ('10000~100000', '$10k - $100k'), ('100000~', '>$100k'),
]
PCT24H_BUCKETS = [
    ('', 'All'), ('-1000~0', 'Negative'), ('0~1000', 'Positive'),
    ('0~5', '0% - 5%'), ('5~10', '5% - 10%'), ('10~25', '10% - 25%'),
    ('25~50', '25% - 50%'), ('50~1000', '>50%'),
]
VOLUME_BUCKETS = [
    ('', 'All'), ('0~10000000', '<$10M'), ('10000000~50000000', '$10M - $50M'),
    ('50000000~100000000', '$50M - $100M'), ('100000000~500000000', '$100M - $500M'),
    ('500000000~1000000000', '$500M - $1B'), ('1000000000~5000000000', '$1B - $5B'),
    ('5000000000~10000000000', '$5B - $10B'), ('10000000000~', '>$10B'),
]

SORTS = {
    'rank': ('rank', 'asc'), 'price': ('price', 'desc'),
    'pct_1h': ('pct_1h', 'desc'), 'pct_24h': ('pct_24h', 'desc'),
    'pct_7d': ('pct_7d', 'desc'), 'market_cap': ('market_cap', 'desc'),
    'volume_24h': ('volume_24h', 'desc'),
    'circulating_supply': ('circulating_supply', 'desc'),
}


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
                    stem = fname.rsplit('.', 1)[0]
                    _INVENTORY[f"{os.path.dirname(row['path'])}/{stem}"] = row['path']
    return _INVENTORY


def asset(kind: str, key) -> str | None:
    """URL for a managed upstream asset (None if absent)."""
    inv = _inventory()
    rel = inv.get(f"static/images/upstream/{kind}/{key}")
    return '/' + rel if rel else None


def coin_logo(coin) -> str | None:
    return asset('coins/64x64', coin.id)


def coin_logo_large(coin) -> str | None:
    return asset('coins/200x200', coin.id) or coin_logo(coin)


def coin_sparkline(coin) -> str | None:
    return asset('sparklines/7d', coin.id)


def exchange_logo(exch) -> str | None:
    return asset('exchanges/64x64', exch.id)


def menu_icon(name: str) -> str | None:
    return asset('menu', name.rsplit('.', 1)[0])


# ------------------------------------------------------------ formatting ----

def fmt_price(v) -> str:
    if v is None:
        return '--'
    v = float(v)
    if v >= 1000:
        return f"${v:,.2f}"
    if v >= 1:
        return f"${v:,.2f}"
    if v == 0:
        return "$0.00"
    # CMC shows tiny prices with significant digits
    digits = max(0, 6 - math.floor(math.log10(v)) - 1) if v > 0 else 6
    digits = min(digits, 12)
    return f"${v:,.{digits}f}"


def fmt_usd_compact(v) -> str:
    if v is None:
        return '--'
    v = float(v)
    for div, suffix in ((1e12, 'T'), (1e9, 'B'), (1e6, 'M'), (1e3, 'K')):
        if abs(v) >= div:
            return f"${v / div:,.2f}{suffix}"
    return f"${v:,.2f}"


def fmt_usd_full(v) -> str:
    if v is None:
        return '--'
    return f"${float(v):,.2f}"


def fmt_pct(v) -> str:
    if v is None:
        return '--'
    v = float(v)
    sign = '+' if v > 0 else ''
    return f"{sign}{v:,.2f}%"


def fmt_supply(v, symbol) -> str:
    if v is None:
        return '--'
    v = float(v)
    if v >= 1e12:
        return f"{v / 1e12:,.3f}T {symbol}"
    return f"{v:,.0f} {symbol}"


def fmt_int(v) -> str:
    if v is None:
        return '--'
    return f"{float(v):,.0f}"


def fmt_fee(v) -> str:
    if v is None or v == '':
        return '--'
    return f"{float(v):.2f}%"


def fmt_date(ts) -> str:
    if not ts:
        return '--'
    try:
        d = datetime.fromisoformat(ts.replace('Z', '+00:00'))
    except ValueError:
        return ts[:10]
    return d.strftime('%b %d, %Y')


def pct_class(v) -> str:
    if v is None:
        return ''
    return 'up' if float(v) > 0 else ('down' if float(v) < 0 else '')


def ms_date(v) -> str:
    """Render an upstream millisecond timestamp (UTC, frozen snapshot)."""
    if not v:
        return '--'
    d = datetime.fromtimestamp(float(v) / 1000, timezone.utc)
    return d.strftime('%b %d, %Y')


@app.template_filter('rich_text')
def rich_text(s):
    """Render captured upstream markdown-ish description HTML.

    The upstream coin/exchange descriptions are markdown with inline
    links; the mirror renders them as simple block HTML with paragraphs,
    headings and link anchors preserved, exactly as coinmarketcap.com
    renders its About sections.
    """
    if not s:
        return Markup('')
    import html as html_mod
    import re as re_mod
    text = html_mod.escape(s)
    # markdown links [label](url) -> <a>
    text = re_mod.sub(r'\[([^\]]+)\]\((https?://[^)\s]+)\)',
                      r'<a href="\2" rel="nofollow">\1</a>', text)
    # headings
    text = re_mod.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re_mod.M)
    text = re_mod.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re_mod.M)
    # bold
    text = re_mod.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    # paragraphs: split on double newline, wrap single newlines
    blocks = [b.strip() for b in text.split('\n\n') if b.strip()]
    out = []
    for b in blocks:
        if b.startswith('<h2>') or b.startswith('<h3>'):
            out.append(b)
        else:
            out.append(f'<p>{b.replace(chr(10), "<br>")}</p>')
    return Markup(''.join(out))


def chart_svg(points, width=760, height=220):
    """Server-rendered SVG line chart from the captured series."""
    if not points:
        return None
    ps = [(p['t'], float(p['p'])) for p in points if p.get('p') is not None]
    if len(ps) < 2:
        return None
    lo, hi = min(p for _, p in ps), max(p for _, p in ps)
    if hi == lo:
        hi = lo + 1
    pad = (hi - lo) * 0.08
    lo_p, hi_p = lo - pad, hi + pad
    left, right, top, bottom = 70, 16, 14, 26
    w, h = width, height
    n = len(ps)
    xs = [left + (w - left - right) * i / (n - 1) for i in range(n)]
    ys = [top + (h - top - bottom) * (1 - (p - lo_p) / (hi_p - lo_p))
          for _, p in ps]
    path = ' '.join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}"
                    for i, (x, y) in enumerate(zip(xs, ys)))
    rising = ps[-1][1] >= ps[0][1]
    color = '#21BA72' if rising else '#F6465D'
    d0 = datetime.fromtimestamp(ps[0][0], timezone.utc).strftime('%b %d, %Y')
    d1 = datetime.fromtimestamp(ps[-1][0], timezone.utc).strftime('%b %d, %Y')
    # Mark the plotted maximum and label it with its date so the chart's
    # highest point is fully derivable from the page (the max label at the
    # top-left carries the price; this marker carries the date).
    mi = max(range(n), key=lambda i: ps[i][1])
    dmax = datetime.fromtimestamp(ps[mi][0], timezone.utc).strftime('%b %d, %Y')
    lx = min(max(xs[mi], left + 55), w - right - 55)
    grid = []
    for frac in (0, 0.25, 0.5, 0.75, 1):
        y = top + (h - top - bottom) * frac
        val = hi_p - (hi_p - lo_p) * frac
        grid.append(f'<line x1="{left}" y1="{y:.1f}" x2="{w - right}" y2="{y:.1f}" stroke="#EAEBEF"/>'
                    f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" class="axis">{fmt_price(val)}</text>')
    return Markup(
        f'<svg viewBox="0 0 {w} {h}" class="price-chart" role="img" aria-label="price chart">'
        f'{"".join(grid)}'
        f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2"/>'
        f'<line x1="{xs[mi]:.1f}" y1="{ys[mi]:.1f}" x2="{xs[mi]:.1f}" y2="{h - bottom:.1f}" stroke="{color}" stroke-width="1" stroke-dasharray="3,3" opacity="0.5"/>'
        f'<circle cx="{xs[mi]:.1f}" cy="{ys[mi]:.1f}" r="3" fill="{color}"/>'
        f'<text x="{lx:.1f}" y="{h - bottom - 8:.1f}" text-anchor="middle" class="axis axis-max">{dmax}</text>'
        f'<text x="{left}" y="{h - 8}" class="axis">{d0}</text>'
        f'<text x="{w - right}" y="{h - 8}" text-anchor="end" class="axis">{d1}</text>'
        f'<text x="{left}" y="{top - 2}" class="axis axis-hi">{fmt_price(hi)}</text>'
        f'<text x="{left}" y="{top + 12}" class="axis" opacity="0"></text>'
        f'</svg>')


app.jinja_env.filters['price'] = fmt_price
app.jinja_env.filters['usd'] = fmt_usd_compact
app.jinja_env.filters['usd_full'] = fmt_usd_full
app.jinja_env.filters['pct'] = fmt_pct
app.jinja_env.filters['supply'] = fmt_supply
app.jinja_env.filters['int'] = fmt_int
app.jinja_env.filters['fee'] = fmt_fee
app.jinja_env.filters['date'] = fmt_date
app.jinja_env.filters['pct_class'] = pct_class
app.jinja_env.filters['ms_date'] = ms_date


# ------------------------------------------------------------------- models --

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(160), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_benchmark = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.String(10), nullable=False, default='2026-09-01')


class Coin(db.Model):
    __tablename__ = 'coins'
    id = db.Column(db.Integer, primary_key=True)   # the upstream CMC id
    slug = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    symbol = db.Column(db.String(40), nullable=False)
    category = db.Column(db.String(20))
    status = db.Column(db.String(20))
    rank = db.Column(db.Integer)
    price = db.Column(db.Float)
    pct_1h = db.Column(db.Float)
    pct_24h = db.Column(db.Float)
    pct_7d = db.Column(db.Float)
    pct_30d = db.Column(db.Float)
    pct_60d = db.Column(db.Float)
    pct_90d = db.Column(db.Float)
    pct_1y = db.Column(db.Float)
    pct_ytd = db.Column(db.Float)
    pct_yesterday = db.Column(db.Float)
    volume_24h = db.Column(db.Float)
    volume_7d = db.Column(db.Float)
    volume_30d = db.Column(db.Float)
    volume_reported_24h = db.Column(db.Float)
    cex_volume = db.Column(db.Float)
    dex_volume = db.Column(db.Float)
    market_cap = db.Column(db.Float)
    fdv = db.Column(db.Float)
    dominance = db.Column(db.Float)
    turnover = db.Column(db.Float)
    roi = db.Column(db.Float)
    circulating_supply = db.Column(db.Float)
    self_reported_circulating = db.Column(db.Float)
    total_supply = db.Column(db.Float)
    max_supply = db.Column(db.Float)
    supply_source = db.Column(db.Text)
    market_pair_count = db.Column(db.Integer)
    date_added = db.Column(db.String(24))
    date_launched = db.Column(db.String(24))
    launch_price = db.Column(db.Float)
    ath = db.Column(db.Float)
    ath_pct = db.Column(db.Float)
    ath_ts = db.Column(db.String(24))
    atl = db.Column(db.Float)
    atl_pct = db.Column(db.Float)
    atl_ts = db.Column(db.String(24))
    high_24h = db.Column(db.Float)
    low_24h = db.Column(db.Float)
    high_7d = db.Column(db.Float)
    low_7d = db.Column(db.Float)
    high_30d = db.Column(db.Float)
    low_30d = db.Column(db.Float)
    high_52w = db.Column(db.Float)
    low_52w = db.Column(db.Float)
    open_yesterday = db.Column(db.Float)
    close_yesterday = db.Column(db.Float)
    volume_rank = db.Column(db.Integer)
    watch_count = db.Column(db.Integer)
    watch_ranking = db.Column(db.Integer)
    description = db.Column(db.Text)
    urls = db.Column(db.Text)
    tags = db.Column(db.Text)
    platforms = db.Column(db.Text)
    holders = db.Column(db.Text)
    similar = db.Column(db.Text)
    related = db.Column(db.Text)
    ratings = db.Column(db.Text)
    badges = db.Column(db.Text)
    is_active = db.Column(db.Boolean)
    last_updated = db.Column(db.String(24))

    def tags_list(self):
        return json.loads(self.tags or '[]')

    def urls_map(self):
        return json.loads(self.urls or '{}')

    def platforms_list(self):
        return json.loads(self.platforms or '[]')

    def holders_map(self):
        return json.loads(self.holders or '{}') if self.holders else {}

    def similar_list(self):
        return json.loads(self.similar or '[]')

    def related_list(self):
        return json.loads(self.related or '[]')

    def ratings_list(self):
        return json.loads(self.ratings or '[]')

    def supply_source_map(self):
        return json.loads(self.supply_source or '{}')


class Tag(db.Model):
    __tablename__ = 'tags'
    slug = db.Column(db.String(120), primary_key=True)
    name = db.Column(db.String(140), nullable=False)
    group_name = db.Column(db.String(40))


class CoinTag(db.Model):
    __tablename__ = 'coin_tags'
    id = db.Column(db.Integer, primary_key=True)
    coin_id = db.Column(db.Integer, nullable=False, index=True)
    tag_slug = db.Column(db.String(120), nullable=False, index=True)


class Sector(db.Model):
    __tablename__ = 'sectors'
    tag_slug = db.Column(db.String(120), primary_key=True)
    sector_id = db.Column(db.String(40))
    name = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text)
    market_cap = db.Column(db.Float)
    market_change = db.Column(db.Float)
    market_volume = db.Column(db.Float)
    volume_change = db.Column(db.Float)
    tokens_num = db.Column(db.Integer)
    upstream_total = db.Column(db.Integer)
    stats = db.Column(db.Text)
    top_coins = db.Column(db.Text)

    def stats_list(self):
        return json.loads(self.stats or '[]')

    def top_coins_list(self):
        return json.loads(self.top_coins or '[]')


class Chart(db.Model):
    __tablename__ = 'coin_charts'
    id = db.Column(db.Integer, primary_key=True)
    coin_id = db.Column(db.Integer, nullable=False, index=True)
    range_name = db.Column(db.String(8), nullable=False)
    points = db.Column(db.Text, nullable=False)

    def points_list(self):
        return json.loads(self.points)


class Ohlcv(db.Model):
    __tablename__ = 'ohlcv'
    id = db.Column(db.Integer, primary_key=True)
    coin_id = db.Column(db.Integer, nullable=False, index=True)
    date = db.Column(db.String(10), nullable=False)
    open = db.Column(db.Float)
    high = db.Column(db.Float)
    low = db.Column(db.Float)
    close = db.Column(db.Float)
    volume = db.Column(db.Float)
    market_cap = db.Column(db.Float)
    supply = db.Column(db.Float)


class MarketPair(db.Model):
    __tablename__ = 'market_pairs'
    id = db.Column(db.Integer, primary_key=True)
    coin_id = db.Column(db.Integer, nullable=False, index=True)
    rank = db.Column(db.Integer)
    exchange_name = db.Column(db.String(140))
    exchange_slug = db.Column(db.String(140))
    pair = db.Column(db.String(60))
    category = db.Column(db.String(30))
    price = db.Column(db.Float)
    volume_usd = db.Column(db.Float)
    volume_pct = db.Column(db.Float)
    market_score = db.Column(db.String(16))
    market_reputation = db.Column(db.Integer)
    fee_type = db.Column(db.String(30))
    depth_neg_2 = db.Column(db.Float)
    depth_pos_2 = db.Column(db.Float)
    effective_liquidity = db.Column(db.Float)
    last_updated = db.Column(db.String(24))
    quote_symbol = db.Column(db.String(20))
    market_url = db.Column(db.String(300))


class Exchange(db.Model):
    __tablename__ = 'exchanges'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(140), unique=True, nullable=False)
    name = db.Column(db.String(140), nullable=False)
    dex_status = db.Column(db.Integer)
    spot_rank = db.Column(db.Integer)
    dex_rank = db.Column(db.Integer)
    derivatives_rank = db.Column(db.Integer)
    score = db.Column(db.Float)
    traffic_score = db.Column(db.Float)
    visits = db.Column(db.Integer)
    liquidity = db.Column(db.Float)
    maker_fee = db.Column(db.Float)
    taker_fee = db.Column(db.Float)
    spot_vol_24h = db.Column(db.Float)
    derivatives_vol_24h = db.Column(db.Float)
    derivatives_pairs = db.Column(db.Integer)
    derivatives_open_interest = db.Column(db.Float)
    filtered_vol_24h = db.Column(db.Float)
    total_vol_24h = db.Column(db.Float)
    total_vol_7d = db.Column(db.Float)
    total_vol_30d = db.Column(db.Float)
    vol_chg_24h = db.Column(db.Float)
    vol_chg_7d = db.Column(db.Float)
    vol_chg_30d = db.Column(db.Float)
    market_share_pct = db.Column(db.Float)
    num_coins = db.Column(db.Integer)
    num_markets = db.Column(db.Integer)
    date_launched = db.Column(db.String(24))
    fiats = db.Column(db.Text)
    countries = db.Column(db.Text)
    status = db.Column(db.String(20))
    por_audit = db.Column(db.Integer)
    reserves = db.Column(db.Integer)
    last_updated = db.Column(db.String(24))
    description = db.Column(db.Text)
    urls = db.Column(db.Text)
    tags = db.Column(db.Text)
    net_worth_usd = db.Column(db.Float)
    quote = db.Column(db.Text)

    def fiats_list(self):
        return json.loads(self.fiats or '[]')

    def countries_list(self):
        return json.loads(self.countries or '[]')

    def urls_map(self):
        return json.loads(self.urls or '{}')

    def tags_list(self):
        return json.loads(self.tags or '[]')


class ExchangePair(db.Model):
    __tablename__ = 'exchange_pairs'
    id = db.Column(db.Integer, primary_key=True)
    exchange_id = db.Column(db.Integer, nullable=False, index=True)
    rank = db.Column(db.Integer)
    pair = db.Column(db.String(60))
    base = db.Column(db.String(20))
    quote_sym = db.Column(db.String(20))
    price = db.Column(db.Float)
    volume_24h = db.Column(db.Float)
    volume_pct = db.Column(db.Float)
    liquidity_score = db.Column(db.Float)
    market_url = db.Column(db.String(300))
    category = db.Column(db.String(30))
    last_updated = db.Column(db.String(24))


class GlobalMetric(db.Model):
    __tablename__ = 'global_metrics'
    id = db.Column(db.Integer, primary_key=True)
    latest = db.Column(db.Text)
    historical = db.Column(db.Text)
    page_shared = db.Column(db.Text)
    trending_top5 = db.Column(db.Text)

    def latest_map(self):
        return json.loads(self.latest or '{}')

    def historical_list(self):
        return json.loads(self.historical or '[]')

    def page_shared_map(self):
        return json.loads(self.page_shared or '{}')

    def trending_list(self):
        return json.loads(self.trending_top5 or '[]')


class TrendingRow(db.Model):
    __tablename__ = 'trending_rows'
    id = db.Column(db.Integer, primary_key=True)
    rank = db.Column(db.Integer)
    symbol = db.Column(db.String(40))
    name = db.Column(db.String(140))
    slug = db.Column(db.String(140))
    platform = db.Column(db.String(80))
    price = db.Column(db.Float)
    pct_1h = db.Column(db.Float)
    pct_24h = db.Column(db.Float)
    pct_7d = db.Column(db.Float)
    pct_30d = db.Column(db.Float)
    volume_24h = db.Column(db.Float)
    market_cap = db.Column(db.Float)
    liquidity = db.Column(db.Float)
    txs_24h = db.Column(db.Float)
    age_ms = db.Column(db.Float)
    risk = db.Column(db.String(20))
    listing_rank = db.Column(db.Integer)


class MostViewedRow(db.Model):
    __tablename__ = 'most_viewed_rows'
    id = db.Column(db.Integer, primary_key=True)
    rank = db.Column(db.Integer)
    slug = db.Column(db.String(140))
    name = db.Column(db.String(140))
    price_text = db.Column(db.String(40))
    pct_24h_text = db.Column(db.String(40))
    pct_7d_text = db.Column(db.String(40))
    pct_30d_text = db.Column(db.String(40))
    market_cap_text = db.Column(db.String(40))
    volume_text = db.Column(db.String(40))


class UpcomingRow(db.Model):
    __tablename__ = 'upcoming_rows'
    id = db.Column(db.Integer, primary_key=True)
    rank = db.Column(db.Integer)
    coin_slug = db.Column(db.String(140))
    coin_name = db.Column(db.String(140))
    coin_symbol = db.Column(db.String(40))
    launch_time_ms = db.Column(db.Float)


class SnapshotRow(db.Model):
    __tablename__ = 'snapshot_rows'
    id = db.Column(db.Integer, primary_key=True)
    snapshot_date = db.Column(db.String(10), nullable=False, index=True)
    rank = db.Column(db.Integer)
    symbol = db.Column(db.String(40))
    name = db.Column(db.String(140))
    market_cap_text = db.Column(db.String(60))
    price_text = db.Column(db.String(40))
    supply_text = db.Column(db.String(60))
    volume_text = db.Column(db.String(60))
    pct_1h_text = db.Column(db.String(40))
    pct_24h_text = db.Column(db.String(40))
    pct_7d_text = db.Column(db.String(40))


class GlossaryTerm(db.Model):
    __tablename__ = 'glossary_terms'
    slug = db.Column(db.String(140), primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    excerpt = db.Column(db.Text)
    difficulty = db.Column(db.String(40))
    content = db.Column(db.Text)


class Conversion(db.Model):
    __tablename__ = 'conversions'
    key = db.Column(db.String(60), primary_key=True)
    from_symbol = db.Column(db.String(40))
    from_name = db.Column(db.String(140))
    amount = db.Column(db.Float)
    to_price = db.Column(db.Float)
    to_symbol = db.Column(db.String(40))


class Content(db.Model):
    __tablename__ = 'contents'
    key = db.Column(db.String(40), primary_key=True)
    text = db.Column(db.Text)

    def text_value(self):
        return self.text or ''


class WatchlistItem(db.Model):
    __tablename__ = 'watchlist_items'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    coin_id = db.Column(db.Integer, nullable=False)
    added_at = db.Column(db.String(10), nullable=False, default='2026-09-29')


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ------------------------------------------------------------------ helpers --

def _range_filter(query, column, spec):
    if not spec:
        return query
    lo, _, hi = spec.partition('~')
    if lo not in (None, '', '0'):
        query = query.filter(column >= float(lo))
    if hi not in (None, ''):
        query = query.filter(column <= float(hi))
    return query


def _global_metrics():
    return db.session.get(GlobalMetric, 1)


def _watched_ids() -> set[int]:
    if current_user.is_authenticated:
        return {w.coin_id for w in WatchlistItem.query.filter_by(user_id=current_user.id)}
    return set(session.get('watchlist', []))


def _base_ctx():
    gm = _global_metrics()
    raw = gm.latest_map() if gm else {}
    # The upstream exposes two shapes for the same numbers: the page's
    # __NEXT_DATA__ globalMetrics (marketCap / totalVol / totalCryptos)
    # and the data-api quotes/latest payload (quotes[0].totalMarketCap /
    # totalVolume24H / totalCryptoCurrencies). Normalize to the page's
    # shape, exactly the values the live header renders.
    quotes = raw.get('quotes') or [{}]
    latest = dict(raw)
    latest.setdefault('marketCap', quotes[0].get('totalMarketCap'))
    latest.setdefault('totalVol', quotes[0].get('totalVolume24H'))
    latest.setdefault('totalCryptos', raw.get('totalCryptoCurrencies'))
    if 'page_global_metrics' in raw:
        for k in ('totalCryptos', 'numCryptocurrencies', 'numMarkets'):
            if raw['page_global_metrics'].get(k) is not None:
                latest[k] = raw['page_global_metrics'][k]
    latest.setdefault('marketCapChange',
                      quotes[0].get('totalMarketCapYesterdayPercentageChange'))
    latest.setdefault('totalVolChange',
                      quotes[0].get('totalVolume24HYesterdayPercentageChange'))
    return {
        'global_metrics': latest,
        'page_shared': gm.page_shared_map() if gm else {},
        'trending_top5': gm.trending_list() if gm else [],
        'mirror_date': MIRROR_DATE,
        'watched': _watched_ids(),
        'menu_icon': menu_icon,
        'asset': asset,
        # Which internal targets actually have pages: tag chips and market
        # pair exchanges are only linkified when the mirror carries the
        # target page (audit fix: 272 tag chips pointed at sector pages that
        # do not exist in the mirror and 2 market exchanges had no page).
        'sector_slugs': {s.tag_slug for s in Sector.query.all()},
        'existing_exchange_slugs': {e.slug for e in
                                    db.session.query(Exchange.slug).all()},
    }


# ------------------------------------------------------------------- routes --

@app.route('/')
def home():
    args = request.args
    sort = args.get('sort', 'rank')
    column, default_dir = SORTS.get(sort, SORTS['rank'])
    direction = args.get('dir', default_dir)
    crypto_type = args.get('type', 'all')
    tag = args.get('tag', '')
    page = max(1, int(args.get('page', 1) or 1))

    query = Coin.query.filter(Coin.is_active == True)  # noqa: E712
    if crypto_type == 'coins':
        query = query.filter(Coin.category == 'coin')
    elif crypto_type == 'tokens':
        query = query.filter(Coin.category == 'token')
    if tag:
        query = query.filter(Coin.id.in_(
            db.session.query(CoinTag.coin_id).filter(CoinTag.tag_slug == tag)))
    query = _range_filter(query, Coin.market_cap, args.get('mcap', ''))
    query = _range_filter(query, Coin.price, args.get('price', ''))
    query = _range_filter(query, Coin.pct_24h, args.get('pct24h', ''))
    query = _range_filter(query, Coin.volume_24h, args.get('vol', ''))

    col = getattr(Coin, column)
    order = col.desc() if direction == 'desc' else col.asc()
    if column == 'rank':
        order = col.asc() if direction == 'asc' else col.desc()
    total = query.count()
    rows = (query.order_by(order)
            .offset((page - 1) * PER_PAGE).limit(PER_PAGE).all())

    sectors = Sector.query.order_by(Sector.name).all()
    ctx = _base_ctx()
    ctx.update({
        'rows': rows, 'total': total, 'page': page,
        'pages': max(1, math.ceil(total / PER_PAGE)),
        'sort': sort, 'direction': direction,
        'crypto_type': crypto_type, 'tag': tag,
        'mcap': args.get('mcap', ''), 'price_filter': args.get('price', ''),
        'pct24h': args.get('pct24h', ''), 'vol': args.get('vol', ''),
        'mcap_buckets': MCAP_BUCKETS, 'price_buckets': PRICE_BUCKETS,
        'pct_buckets': PCT24H_BUCKETS, 'vol_buckets': VOLUME_BUCKETS,
        'sectors': sectors,
        'coin_logo': coin_logo, 'coin_sparkline': coin_sparkline,
    })
    return render_template('home.html', **ctx)


@app.route('/currencies/<slug>/')
def coin_detail(slug):
    coin = Coin.query.filter_by(slug=slug).first_or_404()
    rng = request.args.get('range', '7D')
    if rng not in CHART_RANGES:
        rng = '7D'
    chart = Chart.query.filter_by(coin_id=coin.id, range_name=rng).first()
    available = [r for r, in db.session.query(Chart.range_name).filter_by(coin_id=coin.id)]
    pairs = MarketPair.query.filter_by(coin_id=coin.id).order_by(MarketPair.rank).limit(10).all()
    similar_ids = [s.get('id') for s in coin.similar_list() if s.get('id')]
    similar = Coin.query.filter(Coin.id.in_(similar_ids)).all() if similar_ids else []
    similar = sorted(similar, key=lambda c: similar_ids.index(c.id))
    related_slugs = [r.get('slug') for r in coin.related_list() if r.get('slug')]
    related = Coin.query.filter(Coin.slug.in_(related_slugs)).all() if related_slugs else []
    related = sorted(related, key=lambda c: related_slugs.index(c.slug))
    ctx = _base_ctx()
    ctx.update({
        'coin': coin, 'chart_range': rng,
        'chart': chart.chart_svg if False else (chart_svg(chart.points_list()) if chart else None),
        'available_ranges': [r for r in CHART_RANGES if r in available],
        'pairs': pairs, 'similar': similar, 'related': related,
        'coin_logo': coin_logo, 'coin_logo_large': coin_logo_large,
    })
    return render_template('coin.html', **ctx)


@app.route('/currencies/<slug>/markets/')
def coin_markets(slug):
    coin = Coin.query.filter_by(slug=slug).first_or_404()
    pairs = MarketPair.query.filter_by(coin_id=coin.id).order_by(MarketPair.rank).all()
    ctx = _base_ctx()
    ctx.update({'coin': coin, 'pairs': pairs, 'coin_logo': coin_logo})
    return render_template('markets.html', **ctx)


@app.route('/currencies/<slug>/historical-data/')
def coin_historical(slug):
    coin = Coin.query.filter_by(slug=slug).first_or_404()
    days = request.args.get('days', '30')
    if days not in ('7', '30', '90', '365'):
        days = '30'
    page = max(1, int(request.args.get('page', 1) or 1))
    span = int(days)
    query = Ohlcv.query.filter_by(coin_id=coin.id)
    # Upstream semantics: the days tabs window the table to the most
    # recent `span` daily rows (the capture is one row per UTC day).
    cutoff_row = query.order_by(Ohlcv.date.desc()).first()
    if cutoff_row is not None:
        latest = datetime.strptime(cutoff_row.date, '%Y-%m-%d').date()
        cutoff = (latest - timedelta(days=span - 1)).isoformat()
        window = query.filter(Ohlcv.date >= cutoff)
    else:
        window = query
    total = window.count()
    rows = (window.order_by(Ohlcv.date.desc())
            .offset((page - 1) * 50).limit(50).all())
    full_total = query.count()
    available_days = []
    for d in (7, 30, 90, 365):
        if full_total >= d:
            available_days.append(str(d))
    ctx = _base_ctx()
    ctx.update({
        'coin': coin, 'rows': rows, 'total': total, 'days': days,
        'page': page, 'pages': max(1, math.ceil(total / 50)),
        'available_days': available_days or [str(full_total)],
        'coin_logo': coin_logo,
    })
    return render_template('historical.html', **ctx)


@app.route('/rankings/exchanges/')
def exchanges():
    tab = request.args.get('tab', 'spot')
    if tab not in ('spot', 'dex', 'derivatives'):
        tab = 'spot'
    rank_col = {'spot': Exchange.spot_rank, 'dex': Exchange.dex_rank,
                'derivatives': Exchange.derivatives_rank}[tab]
    query = Exchange.query.filter(rank_col.isnot(None))
    total = query.count()
    rows = query.order_by(rank_col.asc()).all()
    ctx = _base_ctx()
    ctx.update({'rows': rows, 'total': total, 'tab': tab,
                'exchange_logo': exchange_logo})
    return render_template('exchanges.html', **ctx)


@app.route('/exchanges/<slug>/')
def exchange_detail(slug):
    exch = Exchange.query.filter_by(slug=slug).first_or_404()
    pairs = ExchangePair.query.filter_by(exchange_id=exch.id).order_by(ExchangePair.rank).all()
    ctx = _base_ctx()
    ctx.update({'exch': exch, 'pairs': pairs, 'exchange_logo': exchange_logo})
    return render_template('exchange.html', **ctx)


@app.route('/view/<tag>/')
def category(tag):
    sector = Sector.query.filter_by(tag_slug=tag).first_or_404()
    rows = (Coin.query.filter(Coin.id.in_(
                db.session.query(CoinTag.coin_id).filter(CoinTag.tag_slug == tag)))
            .order_by(Coin.rank.asc()).all())
    ctx = _base_ctx()
    ctx.update({
        'sector': sector, 'rows': rows,
        'coin_logo': coin_logo, 'coin_sparkline': coin_sparkline,
    })
    return render_template('category.html', **ctx)


@app.route('/cryptocurrency-category/')
def categories_index():
    sectors = Sector.query.order_by(Sector.name).all()
    content = Content.query.filter_by(key='categories_all').first()
    all_cats = json.loads(content.text_value()) if content else []
    ctx = _base_ctx()
    ctx.update({'sectors': sectors, 'all_cats': all_cats})
    return render_template('categories_index.html', **ctx)


@app.route('/gainers-losers/')
def gainers_losers():
    top100 = Coin.query.filter(Coin.is_active == True).filter(Coin.rank <= 100)  # noqa: E712
    gainers = top100.order_by(Coin.pct_24h.desc()).limit(10).all()
    losers = top100.order_by(Coin.pct_24h.asc()).limit(10).all()
    ctx = _base_ctx()
    ctx.update({'gainers': gainers, 'losers': losers,
                'coin_logo': coin_logo})
    return render_template('gainers_losers.html', **ctx)


@app.route('/trending-cryptocurrencies/')
def trending():
    rows = TrendingRow.query.order_by(TrendingRow.rank).all()
    slugs = {r.slug for r in rows}
    known = {c.slug: c for c in Coin.query.filter(Coin.slug.in_(slugs))} if slugs else {}
    ctx = _base_ctx()
    ctx.update({'rows': rows, 'known': known})
    return render_template('trending.html', **ctx)


@app.route('/most-viewed-pages/')
def most_viewed():
    rows = MostViewedRow.query.order_by(MostViewedRow.rank).all()
    slugs = {r.slug for r in rows}
    known = {c.slug: c for c in Coin.query.filter(Coin.slug.in_(slugs))} if slugs else {}
    ctx = _base_ctx()
    ctx.update({'rows': rows, 'known': known})
    return render_template('most_viewed.html', **ctx)


@app.route('/upcoming/')
def upcoming():
    rows = UpcomingRow.query.order_by(UpcomingRow.rank).all()
    ctx = _base_ctx()
    ctx.update({'rows': rows})
    return render_template('upcoming.html', **ctx)


@app.route('/watchlist/', methods=['GET', 'POST'])
def watchlist():
    if request.method == 'POST':
        slug = request.form.get('remove')
        if slug:
            coin = Coin.query.filter_by(slug=slug).first()
            if coin:
                if current_user.is_authenticated:
                    WatchlistItem.query.filter_by(user_id=current_user.id,
                                                  coin_id=coin.id).delete()
                    db.session.commit()
                else:
                    wl = session.get('watchlist', [])
                    if coin.id in wl:
                        wl.remove(coin.id)
                    session['watchlist'] = wl
        return redirect(url_for('watchlist'))

    ids = sorted(_watched_ids())
    rows = Coin.query.filter(Coin.id.in_(ids)).order_by(Coin.rank.asc()).all() if ids else []
    ctx = _base_ctx()
    ctx.update({'rows': rows, 'coin_logo': coin_logo,
                'coin_sparkline': coin_sparkline})
    return render_template('watchlist.html', **ctx)


@app.route('/watchlist/toggle/<slug>', methods=['POST'])
def watchlist_toggle(slug):
    coin = Coin.query.filter_by(slug=slug).first_or_404()
    if current_user.is_authenticated:
        item = WatchlistItem.query.filter_by(user_id=current_user.id,
                                             coin_id=coin.id).first()
        if item:
            db.session.delete(item)
        else:
            db.session.add(WatchlistItem(user_id=current_user.id,
                                        coin_id=coin.id, added_at=MIRROR_DATE))
        db.session.commit()
    else:
        wl = session.get('watchlist', [])
        if coin.id in wl:
            wl.remove(coin.id)
        else:
            wl.append(coin.id)
        session['watchlist'] = wl
    return redirect(request.form.get('next') or request.referrer or url_for('home'))


@app.route('/converter/', methods=['GET', 'POST'])
def converter():
    coins = Coin.query.filter(Coin.is_active == True).order_by(Coin.rank.asc()).all()  # noqa: E712
    popular = Conversion.query.order_by(Conversion.key).all()
    result = None
    amount = request.form.get('amount', '1') or '1'
    frm = request.form.get('from', 'bitcoin') or 'bitcoin'
    to = request.form.get('to', 'usd') or 'usd'
    if request.method == 'POST':
        try:
            amt = float(amount.replace(',', ''))
        except ValueError:
            amt = None
        price_from = 1.0 if frm == 'usd' else None
        price_to = 1.0 if to == 'usd' else None
        coin_from = Coin.query.filter_by(slug=frm).first()
        coin_to = Coin.query.filter_by(slug=to).first()
        if coin_from and coin_from.price:
            price_from = coin_from.price
        if coin_to and coin_to.price:
            price_to = coin_to.price
        if amt is not None and price_from and price_to:
            value = amt * price_from / price_to
            from_label = f"{coin_from.name} ({coin_from.symbol})" if coin_from else 'United States Dollar "$" (USD)'
            to_label = f"{coin_to.name} ({coin_to.symbol})" if coin_to else 'United States Dollar "$" (USD)'
            result = {
                'amount': amt, 'from_label': from_label,
                'to_label': to_label, 'value': value,
                'from_price': price_from, 'to_price': price_to,
            }
    ctx = _base_ctx()
    ctx.update({'coins': coins, 'popular': popular, 'result': result,
                'amount': amount, 'frm': frm, 'to': to,
                'coin_logo': coin_logo})
    return render_template('converter.html', **ctx)


@app.route('/academy/glossary')
def glossary_index():
    terms = GlossaryTerm.query.order_by(GlossaryTerm.title).all()
    ctx = _base_ctx()
    ctx.update({'terms': terms})
    return render_template('glossary_index.html', **ctx)


@app.route('/academy/glossary/<slug>')
def glossary_term(slug):
    term = GlossaryTerm.query.filter_by(slug=slug).first_or_404()
    others = GlossaryTerm.query.filter(GlossaryTerm.content.isnot(None)) \
        .filter(GlossaryTerm.slug != slug).order_by(GlossaryTerm.title).all()
    ctx = _base_ctx()
    ctx.update({'term': term, 'others': others})
    return render_template('glossary_term.html', **ctx)


@app.route('/faq/')
def faq():
    content = Content.query.filter_by(key='faq').first()
    text = content.text_value() if content else ''
    # split the rendered upstream FAQ into Q/A blocks
    blocks = []
    lines = [l.strip() for l in text.split('\n')]
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.endswith('?') and len(line) > 15:
            answer = []
            j = i + 1
            while j < len(lines) and not (lines[j].endswith('?') and len(lines[j]) > 15):
                if lines[j]:
                    answer.append(lines[j])
                j += 1
            blocks.append({'q': line, 'a': ' '.join(answer)})
            i = j
        else:
            i += 1
    ctx = _base_ctx()
    ctx.update({'blocks': blocks[:26]})
    return render_template('faq.html', **ctx)


@app.route('/methodology/')
def methodology():
    content = Content.query.filter_by(key='methodology').first()
    text = content.text_value() if content else ''
    ctx = _base_ctx()
    ctx.update({'text': text})
    return render_template('methodology.html', **ctx)


@app.route('/historical/')
def historical_index():
    rows = SnapshotRow.query.order_by(SnapshotRow.rank).all()
    dates = sorted({r.snapshot_date for r in rows}, reverse=True)
    ctx = _base_ctx()
    ctx.update({'dates': dates})
    return render_template('historical_index.html', **ctx)


@app.route('/historical/<date>/')
def historical_snapshot(date):
    rows = SnapshotRow.query.filter_by(snapshot_date=date) \
        .order_by(SnapshotRow.rank).all()
    if not rows:
        abort(404)
    ctx = _base_ctx()
    ctx.update({'rows': rows, 'date': date})
    return render_template('snapshot.html', **ctx)


# --------------------------------------------------------------------- auth --

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('home'))
        error = 'Your email and password does not match. Please try again.'
    ctx = _base_ctx()
    ctx.update({'error': error})
    return render_template('login.html', **ctx)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error = None
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        newsletter = request.form.get('newsletter') == 'on'
        if '@' not in email or '.' not in email.split('@')[-1] or len(email) < 6:
            error = 'The email you entered is not in the correct format. Please check.'
        elif len(password) < 8:
            error = 'Your password must be at least 8 characters long.'
        elif User.query.filter_by(email=email).first():
            error = 'The email you entered is already registered. Please log in.'
        else:
            user = User(email=email, display_name=email.split('@')[0],
                        password_hash=bcrypt.generate_password_hash(password).decode(),
                        is_benchmark=False, created_at=MIRROR_DATE)
            db.session.add(user)
            db.session.commit()
            # a guest watchlist carries over to the new account
            for cid in session.get('watchlist', []):
                coin = db.session.get(Coin, cid)
                if coin:
                    db.session.add(WatchlistItem(user_id=user.id, coin_id=cid,
                                                added_at=MIRROR_DATE))
            db.session.commit()
            session.pop('watchlist', None)
            login_user(user)
            return redirect(url_for('home'))
    ctx = _base_ctx()
    ctx.update({'error': error})
    return render_template('signup.html', **ctx)


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.errorhandler(404)
def not_found(e):
    ctx = _base_ctx()
    return render_template('404.html', **ctx), 404


# ------------------------------------------------------------------ health --

@app.route('/_health')
def health():
    return jsonify({
        'ok': True,
        'site': SITE_NAME,
        'coins': Coin.query.count(),
        'exchanges': Exchange.query.count(),
        'market_pairs': MarketPair.query.count(),
        'exchange_pairs': ExchangePair.query.count(),
        'ohlcv_rows': Ohlcv.query.count(),
        'charts': Chart.query.count(),
        'sectors': Sector.query.count(),
        'trending_rows': TrendingRow.query.count(),
        'most_viewed_rows': MostViewedRow.query.count(),
        'upcoming_rows': UpcomingRow.query.count(),
        'snapshot_rows': SnapshotRow.query.count(),
        'glossary_terms': GlossaryTerm.query.count(),
        'users': User.query.count(),
        'watchlist_items': WatchlistItem.query.count(),
    })


# -------------------------------------------------------------------- seeds --

def seed_database():
    if Coin.query.count() > 0:
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
    if os.environ.get('COINMARKETCAP_AUTO_SEED', '1') == '1':
        seed_database()
        seed_benchmark_users()


if __name__ == '__main__':
    main()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 40116)))
