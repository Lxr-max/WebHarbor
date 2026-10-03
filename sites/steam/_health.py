"""Per-site health probe for the steam mirror."""
import json
import sys
import urllib.request


def health():
    return {"ok": True, "site": "steam"}


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
        for key, floor in [('games', 100), ('reviews', 400), ('news', 200),
                           ('bundles', 6), ('bundle_items', 10),
                           ('screenshots', 300), ('sysreqs', 150),
                           ('users', 4), ('wishlist_items', 5), ('orders', 3)]:
            if data.get(key, 0) < floor:
                failures.append(f"only {data.get(key)} {key} seeded")
    except Exception as e:
        print(f'[health] /_health failed: {e}')
        return 1

    for path, marker in [
        ('/', 'Welcome to Steam'),
        ('/search/', 'Steam Store Search'),
        ('/specials/', 'Special Offers'),
        ('/news/', 'Steam News'),
        ('/app/570/', 'Dota 2'),
        ('/app/570/reviews/', 'User Reviews'),
        ('/wishlist/', 'Sign in'),
        ('/cart/', 'Your Shopping Cart'),
    ]:
        try:
            status, body = get(path)
            if status != 200 or marker not in body:
                failures.append(f"{path} -> {status}, marker {marker!r} missing")
        except Exception as e:
            failures.append(f"{path} failed: {e}")

    if failures:
        for f in failures:
            print(f'[health] {f}')
        return 1
    print(f'[health] steam OK on :{port}')
    return 0


if __name__ == '__main__':
    sys.exit(probe(int(sys.argv[1]) if len(sys.argv) > 1 else 40140))
