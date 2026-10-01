from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

SITE_DIR = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(tempfile.mkdtemp(prefix="yf-tests-"))
os.environ["YF_DB_URI"] = f"sqlite:///{TEST_ROOT / 'yahoo_finance.db'}"
os.environ["YF_AUTO_SEED"] = "1"
sys.path.insert(0, str(SITE_DIR))

import app as yf_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_root():
    yield
    with yf_app.app.app_context():
        yf_app.db.session.remove()
        yf_app.db.engine.dispose()
    shutil.rmtree(TEST_ROOT, ignore_errors=True)


def with_csrf(client, source, data):
    """Mimic a real browser: load the page that hosts the form, read the
    CSRF token out of the rendered HTML, and submit it with the form.

    CSRF protection stays ENABLED for the whole suite (the reviewer
    convention: tests must submit real tokens like a browser does)."""
    r = client.get(source)
    assert r.status_code == 200, f"token source {source} -> {r.status_code}"
    m = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', r.data)
    assert m, f"no csrf_token input rendered on {source}"
    out = dict(data)
    out["csrf_token"] = m.group(1).decode()
    return out


@pytest.fixture()
def client():
    # CSRF protection stays ON: tests submit real tokens like a browser.
    yf_app.app.config.update(TESTING=True)
    return yf_app.app.test_client()


def login(client, email, password='TestPass123!'):
    data = with_csrf(client, '/login',
                     {'email': email, 'password': password, 'next': '/'})
    r = client.post('/login', data=data, follow_redirects=True)
    assert r.status_code == 200
    assert b'Sign out' in r.data
    return r


# ---------------------------------------------------------------- models --

def test_seed_counts():
    with yf_app.app.app_context():
        from app import (ChartPoint, EarningsEvent, IncomeRow, NewsArticle,
                         PriceAlert, Quote, ScreenerPreset, TrendingItem, User,
                         WatchItem)
        assert Quote.query.count() >= 300
        assert NewsArticle.query.count() >= 350
        assert EarningsEvent.query.count() >= 800
        assert IncomeRow.query.count() >= 1000
        assert ChartPoint.query.count() >= 6000
        assert ScreenerPreset.query.count() == 6
        assert TrendingItem.query.count() >= 15
        assert User.query.count() == 4
        assert WatchItem.query.count() >= 10
        assert PriceAlert.query.count() >= 4


def test_benchmark_users_and_frozen_hash():
    with yf_app.app.app_context():
        from app import User, WatchItem
        emails = {u.email for u in User.query.all()}
        assert emails == {'alice.j@test.com', 'bob.c@test.com',
                          'carol.d@test.com', 'dana.k@test.com'}
        alice = User.query.filter_by(email='alice.j@test.com').one()
        assert yf_app.bcrypt.check_password_hash(
            alice.password_hash, 'TestPass123!')
        assert alice.joined == '2026-09-30'
        syms = {w.symbol for w in WatchItem.query.filter_by(user_id=alice.id)}
        assert syms == {'MSFT', 'NVDA', 'TSLA', 'SPY'}


def test_idempotent_seeding_keeps_db_clean():
    """Re-running the boot seed against a populated DB must not add rows or
    bump the file (the reset byte-identity invariant)."""
    with yf_app.app.app_context():
        from app import Quote, User
        before_q = Quote.query.count()
        before_u = User.query.count()
        yf_app.seed_database()
        yf_app.seed_benchmark_users()
        assert Quote.query.count() == before_q
        assert User.query.count() == before_u


# ------------------------------------------------------------------ pages --

ALL_PAGES = [
    '/', '/lookup?s=apple', '/quote/AAPL', '/quote/AAPL/statistics',
    '/quote/AAPL/financials', '/quote/AAPL/profile', '/quote/AAPL/history',
    '/quote/AAPL/news', '/quote/NVDA', '/quote/%5EGSPC', '/quote/BTC-USD',
    '/quote/GC%3DF', '/screener', '/screener?preset=day_gainers',
    '/screener?preset=most_actives', '/calendar/earnings',
    '/calendar/earnings?day=2026-09-20', '/calendar/earnings?day=2026-10-04',
    '/news', '/news?topic=economy', '/news?topic=earnings', '/news?q=Nvidia',
    '/sectors', '/sectors/technology', '/sectors/healthcare', '/trending',
    '/login', '/signup',
]


@pytest.mark.parametrize('path', ALL_PAGES)
def test_page_renders(client, path):
    r = client.get(path)
    assert r.status_code == 200, path
    assert b'Yahoo Finance' in r.data


def test_unknown_page_404(client):
    assert client.get('/no/such/page').status_code == 404
    assert client.get('/quote/NOPE').status_code == 404


def test_home_layout(client):
    r = client.get('/')
    html = r.data.decode()
    for needle in ('Trending Tickers', 'Market Movers', 'Latest News',
                   'S&amp;P Futures', 'Bitcoin USD', 'US Markets'):
        assert needle in html, needle


# ------------------------------------------------------------ quote pages --

def test_quote_summary_key_data(client):
    r = client.get('/quote/AAPL')
    html = r.data.decode()
    assert 'Apple Inc.' in html
    assert '333.02' in html
    assert 'Technology' in html          # Overview line + sector
    assert '52 Week Range' in html
    assert '243.42 - 345.34' in html
    assert 'At close: September 30 at 4:00:01 PM EDT' in html
    assert 'Next earnings: October 29, 2026' in html


def test_quote_statistics_values(client):
    r = client.get('/quote/NVDA/statistics')
    html = r.data.decode()
    assert 'Trailing P/E' in html and '28.87' in html
    assert 'Profit Margin' in html and '63.66%' in html
    assert '50-Day Average' in html and '216.98' in html
    assert '52 Week Range' in html


def test_quote_financials_table(client):
    r = client.get('/quote/AAPL/financials')
    html = r.data.decode()
    assert '2025-09-30' in html
    assert '416.16B' in html           # total revenue
    assert '112.01B' in html           # net income


def test_quote_profile_facts(client):
    r = client.get('/quote/KO/profile')
    html = r.data.decode()
    assert 'Consumer Defensive' in html
    assert 'Beverages - Non-Alcoholic' in html
    assert '65,900' in html
    assert 'coca-colacompany.com' in html


def test_quote_history_rows(client):
    r = client.get('/quote/MSFT/history')
    html = r.data.decode()
    assert 'September 30, 2026' in html and '512.90' in html
    assert 'September 1, 2026' in html and '501.02' in html


# ---------------------------------------------------------------- screener --

def test_screener_preset_day_gainers(client):
    r = client.get('/screener?preset=day_gainers')
    html = r.data.decode()
    assert 'Day Gainers' in html
    assert 'UTHR' in html and '12.55%' in html


def test_screener_custom_filter(client):
    r = client.get('/screener?custom=1&sector=Technology&pe_min=12'
                   '&pe_max=40&sort=pe&dir=asc')
    html = r.data.decode()
    assert 'SMCI' in html
    assert 'Computer Hardware' in html


def test_screener_utilities_yield_filter(client):
    r = client.get('/screener?custom=1&sector=Utilities&yield_min=4'
                   '&sort=yield&dir=desc')
    html = r.data.decode()
    assert 'DUK-PA' in html and 'KEN' in html and 'Dominion' in html


def test_screener_sector_mcap_change_filter(client):
    """T14 premise regression (r1 review MED finding): the Healthcare
    10-200B band filtered by % change descending must yield at least the
    three reported leaders, in a stable order."""
    r = client.get('/screener?custom=1&sector=Healthcare'
                   '&mcap_min=10000000000&mcap_max=200000000000'
                   '&sort=change&dir=desc')
    html = r.data.decode()
    assert '9 matches' in html
    first = html.find('results-table')
    syms = re.findall(r'<a href="/quote/([^"]+)"><strong>',
                      html[first:])
    assert syms[:3] == ['UTHR', 'IBRX', 'PFE']
    assert len(syms) >= 3


# ---------------------------------------------------------------- calendar --

def test_calendar_default_week(client):
    r = client.get('/calendar/earnings')
    html = r.data.decode()
    assert 'Week of September 27, 2026 – October 3, 2026' in html
    assert 'September 30, 2026' in html


def test_calendar_prev_week_and_amc_filter(client):
    r = client.get('/calendar/earnings?day=2026-09-20')
    assert r.status_code == 200
    r = client.get('/calendar/earnings?day=2026-09-20&time=AMC')
    html = r.data.decode()
    m = re.search(r'(\d+) events shown', html)
    assert m and int(m.group(1)) == 2


def test_calendar_cost_row(client):
    r = client.get('/calendar/earnings?day=2026-09-20&symbol=COST')
    html = r.data.decode()
    assert 'COST' in html and 'Costco' in html
    assert '6.53' in html


# -------------------------------------------------------------------- news --

def test_news_topics(client):
    r = client.get('/news?topic=earnings')
    html = r.data.decode()
    assert 'CBOE' in html


def test_news_search_counts(client):
    r = client.get('/news?q=Nvidia')
    html = r.data.decode()
    assert '10 articles match' in html
    r = client.get('/news?q=buyback')
    assert '2 articles match' in r.data.decode()
    # r1-fix anchors: the reworded T9/T15 news question points
    r = client.get('/news?q=Apple')
    assert '9 articles match' in r.data.decode()
    r = client.get('/news?q=stablecoin')
    assert '2 articles match' in r.data.decode()


def test_hosted_article_page(client):
    with yf_app.app.app_context():
        from app import NewsArticle
        art = yf_app.db.session.query(NewsArticle).filter_by(
            key='419adde41935').one()
    r = client.get(art.url_path)
    assert r.status_code == 200
    html = r.data.decode()
    assert 'Motley Fool' in html
    assert '150B' in html
    assert 'Related tickers' in html


def test_lookup_quotes_and_news(client):
    r = client.get('/lookup?s=apple')
    html = r.data.decode()
    assert 'AAPL' in html
    assert 'Apple Inc.' in html
    assert 'Bank of America warns Apple investors' in html


def test_lookup_gold_futures(client):
    r = client.get('/lookup?s=gold')
    html = r.data.decode()
    assert 'GC=F' in html and 'Gold Dec 26' in html


# ----------------------------------------------------------------- sectors --

def test_sectors_table(client):
    r = client.get('/sectors')
    html = r.data.decode()
    assert 'Technology' in html
    assert '0.38%' in html           # technology weighted day change
    assert 'JBL' in html             # technology top loser
    assert '26.69T' in html          # technology aggregate market cap


def test_sector_detail_industries(client):
    r = client.get('/sectors/healthcare')
    html = r.data.decode()
    assert '39 captured companies' in html
    assert 'Biotechnology' in html
    assert 'LLY' in html and 'JNJ' in html


def test_trending_top(client):
    r = client.get('/trending')
    html = r.data.decode()
    assert 'MU' in html and 'Micron' in html
    assert 'LQDA' in html


# ----------------------------------------------------------- auth + state --

def test_csrf_rejects_missing_token(client):
    r = client.post('/watchlist/toggle', data={'symbol': 'AAPL'})
    assert r.status_code == 400


def test_login_wrong_password(client):
    data = with_csrf(client, '/login', {'email': 'alice.j@test.com',
                                        'password': 'nope', 'next': '/'})
    r = client.post('/login', data=data)
    assert r.status_code == 401
    assert b'Invalid email or password' in r.data


def test_watchlist_toggle_flow(client):
    login(client, 'alice.j@test.com')
    data = with_csrf(client, '/quote/KO', {'symbol': 'KO',
                                           'back': '/quote/KO'})
    r = client.post('/watchlist/toggle', data=data, follow_redirects=True)
    assert r.status_code == 200
    assert b'Remove from Watchlist' in r.data
    r = client.get('/watchlist')
    assert b'KO' in r.data
    r2 = client.post('/watchlist/toggle', data=data, follow_redirects=True)
    assert b'Add to Watchlist' in r2.data


def test_alert_direction_default_is_above(client):
    """Anti-padding premise (r1 review caliber): the alert direction
    dropdown renders Above as its unselected default, so an honest
    'above N' walk must not re-operate the control."""
    login(client, 'dana.k@test.com')
    r = client.get('/quote/AAPL')
    html = r.data.decode()
    m = re.search(r'<select id="direction"[^>]*>(.*?)</select>', html,
                  re.S)
    assert m, 'direction select missing from quote page'
    first = re.search(r'<option value="(\w+)"', m.group(1))
    assert first.group(1) == 'above'
    assert 'selected' not in m.group(1)


def test_alert_create_and_status(client):
    login(client, 'dana.k@test.com')
    data = with_csrf(client, '/quote/AAPL', {
        'symbol': 'AAPL', 'direction': 'above', 'threshold': '400',
        'note': 'Earnings run', 'back': '/alerts'})
    r = client.post('/alerts/create', data=data, follow_redirects=True)
    assert r.status_code == 200
    html = r.data.decode()
    assert 'AAPL' in html and 'Earnings run' in html
    # 333.02 < 400 -> stays Active
    assert 'Active' in html
    assert 'META' in html          # seeded alert still present


def test_alert_invalid_threshold_rejected(client):
    login(client, 'alice.j@test.com')
    data = with_csrf(client, '/quote/AAPL', {
        'symbol': 'AAPL', 'direction': 'above', 'threshold': '-5',
        'back': '/alerts'})
    r = client.post('/alerts/create', data=data)
    assert r.status_code == 400
    assert b'positive' in r.data


def test_alert_delete_only_own(client):
    login(client, 'dana.k@test.com')
    data = with_csrf(client, '/alerts', {'id': '6'})     # dana's META alert
    r = client.post('/alerts/delete', data=data, follow_redirects=True)
    assert r.status_code == 200
    assert b'META' not in r.data
    # alice's alert (id 1) belongs to another user: no-op, no crash
    data = with_csrf(client, '/alerts', {'id': '1'})
    r = client.post('/alerts/delete', data=data, follow_redirects=True)
    assert r.status_code == 200


def test_signup_creates_account_and_watches(client):
    data = with_csrf(client, '/signup', {
        'name': 'Jordan Vale', 'email': 'jordan.vale@test.com',
        'password': 'TestPass123!'})
    r = client.post('/signup', data=data, follow_redirects=True)
    assert r.status_code == 200
    with yf_app.app.app_context():
        from app import User
        user = User.query.filter_by(email='jordan.vale@test.com').one()
        assert user.name == 'Jordan Vale'
        assert user.joined == '2026-09-30'
        assert yf_app.bcrypt.check_password_hash(
            user.password_hash, 'TestPass123!')
    data = with_csrf(client, '/quote/SMCI', {'symbol': 'SMCI',
                                             'back': '/quote/SMCI'})
    r = client.post('/watchlist/toggle', data=data, follow_redirects=True)
    assert b'Remove from Watchlist' in r.data


def test_signup_rejects_short_password(client):
    data = with_csrf(client, '/signup', {
        'name': 'X', 'email': 'x.y@test.com', 'password': 'short'})
    r = client.post('/signup', data=data)
    assert r.status_code == 400


def test_login_required_redirects(client):
    r = client.get('/watchlist')
    assert r.status_code == 302
    assert r.headers['Location'].startswith('/login')
    r = client.get('/alerts')
    assert r.status_code == 302


# ------------------------------------------------------------ determinism --

def test_seed_database_byte_identical(tmp_path):
    """Two fresh seed builds from the tracked source snapshots must be
    byte-identical (the /reset byte-identity invariant)."""
    import hashlib
    import subprocess
    env = dict(os.environ)
    env['PYTHONHASHSEED'] = '0'
    hashes = []
    for i in range(2):
        target = tmp_path / f'seed{i}.db'
        env['YF_DB_URI'] = f'sqlite:///{target}'
        env['YF_AUTO_SEED'] = '1'
        subprocess.run([sys.executable, '-c',
                        'import sys; sys.path.insert(0, %r)\n'
                        'from app import main\nmain()' % str(SITE_DIR)],
                       env=env, check=True, cwd=str(SITE_DIR),
                       stdout=subprocess.DEVNULL)
        hashes.append(hashlib.sha256(target.read_bytes()).hexdigest())
    assert hashes[0] == hashes[1]
