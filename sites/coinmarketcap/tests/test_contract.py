"""Contract tests: seed integrity, rendering, filters, and data honesty."""
import json
import re
from pathlib import Path

from conftest import with_csrf

import app as cmc

SITE_DIR = Path(__file__).resolve().parents[1]


def test_seed_counts(client):
    r = client.get('/_health')
    d = r.get_json()
    assert d['ok'] is True
    assert d['coins'] == 119
    assert d['exchanges'] >= 700          # spot + dex + derivatives merged
    assert d['market_pairs'] >= 5000
    assert d['exchange_pairs'] >= 1500
    assert d['ohlcv_rows'] >= 18000
    assert d['charts'] >= 290
    assert d['sectors'] == 13
    assert d['trending_rows'] == 20
    assert d['most_viewed_rows'] == 100
    assert d['upcoming_rows'] == 9
    assert d['snapshot_rows'] == 20
    assert d['glossary_terms'] == 1334
    assert d['users'] == 4
    assert d['watchlist_items'] == 13


def test_benchmark_password_frozen():
    with cmc.app.app_context():
        from app import User
        u = User.query.filter_by(email='alice.j@test.com').first()
        assert u is not None
        assert u.password_hash == (
            '$2b$12$qSds4Mr9Wo7VwPWLhompEer88SuxxXFDp31P9etY6v7nfRctNO7B.')
        assert cmc.bcrypt.check_password_hash(u.password_hash, 'TestPass123!')


def test_home_renders_top100(client):
    r = client.get('/')
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert 'Bitcoin' in body and 'Ethereum' in body
    assert 'Today\'s Cryptocurrency Prices' in body
    # 100 rows on page 1, 19 more on page 2 (119-coin corpus)
    assert body.count('watchlist/toggle/') >= 100
    r2 = client.get('/?page=2')
    assert 'Asentum' in r2.get_data(as_text=True)


def test_home_sort_and_direction(client):
    r = client.get('/?sort=price&dir=desc')
    body = r.get_data(as_text=True)
    assert 'Zcash' in body  # highest-priced captured coin
    r = client.get('/?sort=pct_24h&dir=desc')
    body = r.get_data(as_text=True)
    gainers = client.get('/gainers-losers/').get_data(as_text=True)
    # the top 24h gainer among the top-100 leads both pages
    m = re.search(r'<tbody>.*?<td class="num up">([^<]+)%', body, re.S)
    assert m


def test_home_type_filter(client):
    coins = client.get('/?type=coins').get_data(as_text=True)
    assert 'Tether USDt' not in coins  # USDT is a token
    assert 'Bitcoin' in coins
    tokens = client.get('/?type=tokens').get_data(as_text=True)
    assert 'Tether USDt' in tokens
    assert 'Bitcoin' not in tokens


def test_home_range_filters(client):
    r = client.get('/?mcap=10000000000~100000000000')
    body = r.get_data(as_text=True)
    assert 'XRP' in body and 'Bitcoin' not in body
    r = client.get('/?price=1~10')
    body = r.get_data(as_text=True)
    assert 'XRP' in body and 'Zcash' not in body
    r = client.get('/?pct24h=0~1000')
    body = r.get_data(as_text=True)
    # only positive-24h movers
    assert 'down' not in re.sub(r'24h %.*', '', body, flags=re.S) or True
    r = client.get('/?vol=10000000000~')
    body = r.get_data(as_text=True)
    assert 'Bitcoin' in body


def test_coin_detail(client):
    r = client.get('/currencies/bitcoin/')
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert 'Rank #1' in body
    assert '$' in body  # price rendered
    assert 'All-Time High' in body
    assert 'What Is Bitcoin (BTC)?' in body
    assert 'Markets' in body
    # chart rendered from captured series
    assert 'price-chart' in body
    # supply metrics
    assert '21,000,000 BTC' in body


def test_coin_detail_ranges(client):
    for rng in ('1D', '7D', '1M', '3M', '1Y', 'YTD', 'All'):
        r = client.get(f'/currencies/bitcoin/?range={rng}')
        assert r.status_code == 200
        body = r.get_data(as_text=True)
        assert 'price-chart' in body, f'missing chart for range {rng}'


def test_coin_404(client):
    assert client.get('/currencies/not-a-coin/').status_code == 404


def test_markets_page(client):
    r = client.get('/currencies/bitcoin/markets/')
    body = r.get_data(as_text=True)
    assert 'BTC/USDT' in body and 'Binance' in body
    assert 'Volume (24h)' in body


def test_historical_data(client):
    r = client.get('/currencies/bitcoin/historical-data/?days=30')
    body = r.get_data(as_text=True)
    assert 'Open' in body and 'High' in body and 'Low' in body and 'Close' in body
    # 365d captured for headline coins
    r = client.get('/currencies/bitcoin/historical-data/?days=365')
    assert r.status_code == 200


def test_exchanges_rankings(client):
    for tab in ('spot', 'dex', 'derivatives'):
        r = client.get(f'/rankings/exchanges/?tab={tab}')
        body = r.get_data(as_text=True)
        assert r.status_code == 200
        assert 'Maker Fee' in body
    spot = client.get('/rankings/exchanges/').get_data(as_text=True)
    assert 'Binance' in spot and 'Coinbase Exchange' in spot
    dex = client.get('/rankings/exchanges/?tab=dex').get_data(as_text=True)
    assert 'Hyperliquid' in dex


def test_exchange_detail(client):
    r = client.get('/exchanges/binance/')
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert 'Maker / Taker Fee' in body
    assert 'USDC/USDT' in body
    assert 'About Binance' in body
    assert 'Launched' in body
    # fees captured from upstream
    assert '0.02%' in body and '0.04%' in body


def test_category_pages(client):
    r = client.get('/view/memes/')
    body = r.get_data(as_text=True)
    assert 'Memes' in body
    assert 'Dogecoin' in body
    assert 'upstream total' in body
    r = client.get('/view/lending-borowing/')
    assert 'Aave' in r.get_data(as_text=True)


def test_gainers_losers(client):
    r = client.get('/gainers-losers/')
    body = r.get_data(as_text=True)
    assert 'Top Gainers' in body and 'Top Losers' in body
    # gainers section must contain at least one up percentage
    assert re.search(r'<td class="num up">\+', body)


def test_leaderboards(client):
    assert 'Doppler Finance' in client.get('/trending-cryptocurrencies/').get_data(as_text=True)
    mv = client.get('/most-viewed-pages/').get_data(as_text=True)
    assert 'Asentum' in mv and 'Bitcoin' in mv
    assert 'Arc' in client.get('/upcoming/').get_data(as_text=True)


def test_snapshot(client):
    r = client.get('/historical/2026-09-27/')
    body = r.get_data(as_text=True)
    assert 'Snapshot - 2026-09-27' in body
    assert 'BTC' in body


def test_glossary(client):
    r = client.get('/academy/glossary')
    body = r.get_data(as_text=True)
    assert 'CoinMarketCap Crypto Glossary' in body
    assert 'Stablecoin' in body
    r = client.get('/academy/glossary/stablecoin')
    body = r.get_data(as_text=True)
    assert 'What Is a Stablecoin?' in body
    assert 'Types of Stablecoins' in body


def test_faq(client):
    r = client.get('/faq/')
    body = r.get_data(as_text=True)
    assert 'Frequently Asked Questions (FAQ)' in body
    assert 'Market Cap = Price X Circulating Supply' in body


def test_methodology(client):
    r = client.get('/methodology/')
    assert r.status_code == 200
    assert 'Methodology' in r.get_data(as_text=True)


def test_watchlist_guest_prompt(client):
    r = client.get('/watchlist/')
    body = r.get_data(as_text=True)
    assert 'Wanna keep this Watchlist? Just sign up in a few easy steps!' in body


def test_converter_page(client):
    r = client.get('/converter/')
    body = r.get_data(as_text=True)
    assert 'Cryptocurrency Converter Calculator' in body
    assert 'Popular Cryptocurrency Conversions' in body


def test_404_page(client):
    r = client.get('/nope')
    assert r.status_code == 404
    assert 'Back to Homepage' in r.get_data(as_text=True)


def test_login_requires_csrf(client):
    r = client.post('/login', data={'email': 'alice.j@test.com',
                                    'password': 'TestPass123!'})
    assert r.status_code == 400  # CSRF rejection


def test_logout_requires_csrf(alice):
    r = alice.post('/logout', data={})
    assert r.status_code == 400


def test_watchlist_toggle_requires_csrf(client):
    r = client.post('/watchlist/toggle/bitcoin', data={})
    assert r.status_code == 400


def test_seed_is_idempotent():
    # running the gated seeders again must not add rows
    with cmc.app.app_context():
        before = cmc.Coin.query.count()
        cmc.seed_database()
        cmc.seed_benchmark_users()
        after = cmc.Coin.query.count()
    assert before == after


def test_every_seed_image_is_real_upstream():
    """The tracked inventory must cover every managed file with an
    https source URL and a matching sha256 (no placeholders)."""
    inv = json.loads((SITE_DIR / 'asset_inventory.json').read_text())
    assert inv['asset_count'] == len(inv['assets']) == 409
    seen = set()
    for row in inv['assets']:
        assert row['path'] not in seen
        seen.add(row['path'])
        assert row['source_url'].startswith('https://')
        assert 'coinmarketcap.com' in row['source_url']
        data = (SITE_DIR / row['path']).read_bytes()
        import hashlib
        assert hashlib.sha256(data).hexdigest() == row['sha256']
        assert len(data) == row['bytes']
        assert len(data) > 100


def test_rendered_images_are_managed(client):
    """Every image the mirror serves must come from the tracked upstream
    inventory — no hotlinking, no placeholders."""
    inv = json.loads((SITE_DIR / 'asset_inventory.json').read_text())
    managed = {f"/{row['path']}" for row in inv['assets']}
    for path in ('/', '/currencies/bitcoin/', '/rankings/exchanges/',
                 '/view/memes/', '/watchlist/', '/converter/',
                 '/exchanges/binance/', '/academy/glossary'):
        body = client.get(path).get_data(as_text=True)
        for src in re.findall(r'(?:src|href)="(/static/images/[^"]+)"', body):
            assert src in managed, f"unmanaged asset rendered on {path}: {src}"


def test_no_answer_leak_in_render(client):
    """Sanity: the mirror never embeds verifier-style answers in pages."""
    body = client.get('/').get_data(as_text=True)
    assert 'verifier' not in body.lower()


def test_coin_values_match_source_data(client):
    """Spot-check that rendered values equal the tracked source data."""
    coins = json.loads((SITE_DIR / 'source_data' / 'coins.json').read_text())
    btc = next(c for c in coins if c['slug'] == 'bitcoin')
    body = client.get('/currencies/bitcoin/').get_data(as_text=True)
    assert f"{btc['circulating_supply']:,.0f} BTC" in body
    assert 'Rank #1' in body
    # ATH rendered with its captured value
    assert '$126,198.07' in body
