"""Per-site health probe for the coinmarketcap mirror."""
import json
import sys
import urllib.request


def probe(port: int) -> int:
    failures = []

    def get(path):
        with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}', timeout=10) as r:
            return r.status, r.read().decode('utf-8', 'replace')

    try:
        status, body = get('/_health')
        data = json.loads(body)
        if not data.get('ok'):
            failures.append(f"/_health not ok: {data}")
        if data.get('coins', 0) != 119:
            failures.append(f"expected 119 coins, got {data.get('coins')}")
        if data.get('exchanges', 0) < 700:
            failures.append(f"expected 700+ exchanges, got {data.get('exchanges')}")
        if data.get('market_pairs', 0) < 5000:
            failures.append(f"expected 5000+ market pairs, got {data.get('market_pairs')}")
        if data.get('ohlcv_rows', 0) < 18000:
            failures.append(f"expected 18000+ OHLCV rows, got {data.get('ohlcv_rows')}")
        if data.get('charts', 0) < 290:
            failures.append(f"expected 290+ chart series, got {data.get('charts')}")
        if data.get('sectors', 0) != 13:
            failures.append(f"expected 13 sector pages, got {data.get('sectors')}")
        if data.get('glossary_terms', 0) != 1334:
            failures.append(f"expected 1334 glossary terms, got {data.get('glossary_terms')}")
        if data.get('users', 0) != 4:
            failures.append(f"expected 4 benchmark users, got {data.get('users')}")
    except Exception as e:
        print(f'[health] /_health failed: {e}')
        return 1

    for path, marker in [
        ('/', "Today's Cryptocurrency Prices"),
        ('/?sort=price&dir=desc', 'Zcash'),
        ('/?type=tokens', 'Tether USDt'),
        ('/?mcap=10000000000~100000000000', 'XRP'),
        ('/currencies/bitcoin/', 'What Is Bitcoin (BTC)?'),
        ('/currencies/bitcoin/?range=All', 'price-chart'),
        ('/currencies/bitcoin/historical-data/?days=30', 'Open'),
        ('/currencies/bitcoin/markets/', 'BTC/USDT'),
        ('/currencies/dogecoin/', 'Dogecoin'),
        ('/rankings/exchanges/', 'Binance'),
        ('/rankings/exchanges/?tab=dex', 'Hyperliquid'),
        ('/exchanges/binance/', 'About Binance'),
        ('/view/memes/', 'Dogecoin'),
        ('/view/lending-borowing/', 'Aave'),
        ('/gainers-losers/', 'Top Gainers'),
        ('/trending-cryptocurrencies/', 'Trending Cryptocurrencies'),
        ('/most-viewed-pages/', 'Most Viewed Cryptocurrencies'),
        ('/upcoming/', 'Upcoming Cryptocurrencies'),
        ('/watchlist/', 'Wanna keep this Watchlist?'),
        ('/converter/', 'Cryptocurrency Converter Calculator'),
        ('/academy/glossary', 'CoinMarketCap Crypto Glossary'),
        ('/academy/glossary/stablecoin', 'Types of Stablecoins'),
        ('/faq/', 'Frequently Asked Questions (FAQ)'),
        ('/methodology/', 'Methodology'),
        ('/historical/', 'Historical Snapshots'),
        ('/historical/2026-09-27/', 'Snapshot - 2026-09-27'),
        ('/login', 'Email Address'),
        ('/signup', 'Create an account'),
        ('/cryptocurrency-category/', 'Cryptocurrency Categories'),
    ]:
        try:
            status, body = get(path)
            if status != 200:
                failures.append(f'{path} -> {status}')
            elif marker not in body:
                failures.append(f'{path} missing marker {marker!r}')
        except Exception as e:
            failures.append(f'{path} raised {e}')

    if failures:
        for f in failures:
            print(f'[health] FAIL {f}')
        return 1
    print('[health] coinmarketcap all green')
    return 0


if __name__ == '__main__':
    sys.exit(probe(int(sys.argv[1]) if len(sys.argv) > 1 else 40116))
