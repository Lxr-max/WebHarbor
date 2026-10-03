"""Per-site health probe for the cars_com mirror."""
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
        if data.get('listings', 0) < 500:
            failures.append(f"only {data.get('listings')} listings seeded")
        if data.get('details', 0) < 80:
            failures.append(f"only {data.get('details')} detail-rich listings seeded")
        if data.get('dealers', 0) < 100:
            failures.append(f"only {data.get('dealers')} dealers seeded")
        if data.get('models', 0) < 10:
            failures.append(f"expected 10+ research model pages, got {data.get('models')}")
        if data.get('compares', 0) < 6:
            failures.append(f"expected 6+ comparisons, got {data.get('compares')}")
        if data.get('valuations', 0) < 5:
            failures.append(f"expected 5+ valuation vehicles, got {data.get('valuations')}")
        if data.get('users', 0) != 4:
            failures.append(f"expected 4 benchmark users, got {data.get('users')}")
    except Exception as e:
        print(f'[health] /_health failed: {e}')
        return 1

    for path, marker in [
        ('/', 'Find your next car'),
        ('/shopping/results/?stock_type=used', 'Used Cars for Sale Near'),
        ('/shopping/results/?stock_type=used&makes[]=honda&models[]=honda-civic', 'Honda Civic'),
        ('/shopping/results/?stock_type=used&sort=list_price_asc', 'results'),
        ('/shopping/new/', 'Shop All New Cars'),
        ('/shopping/certified-preowned/', 'Certified Pre-Owned'),
        ('/shopping/electric/', 'Electric Cars for Sale'),
        ('/shopping/for-sale-by-owner/', 'Cars for Sale by Owner'),
        ('/dealers/', 'Car dealers near'),
        ('/research/', 'Research cars'),
        ('/research/compare/', 'Compare cars side by side'),
        ('/sell/instant-offer/', 'Get your Instant Offer'),
        ('/car-loan-calculator/', 'Estimate your monthly car loan payment'),
        ('/authn/login', 'Log in to Cars.com'),
        ('/authn/register', 'Create your Cars.com account'),
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
            print(f'[health] {f}')
        return 1
    print(f'[health] cars_com on :{port} — all probes green')
    return 0


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 40136
    sys.exit(probe(port))
