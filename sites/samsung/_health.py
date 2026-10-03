"""Per-site health probe for the samsung mirror."""
import json
import sys
import urllib.request


def health():
    return {"ok": True, "site": "samsung"}


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
        for key, floor in [('products', 400), ('config_products', 150),
                           ('spec_rows', 1000), ('spec_models', 20),
                           ('heroes', 3), ('warranty_faqs', 5),
                           ('warranty_categories', 3), ('users', 4),
                           ('orders', 3), ('wishlist_items', 5),
                           ('tickets', 1)]:
            if data.get(key, 0) < floor:
                failures.append(f"only {data.get(key)} {key} seeded")
    except Exception as e:
        print(f'[health] /_health failed: {e}')
        return 1

    for path, marker in [
        ('/', 'Samsung'),
        ('/shop/all/', 'Shop All Products'),
        ('/smartphones/', 'Smartphones'),
        ('/tablets/', 'Tablets'),
        ('/watches/', 'Watches'),
        ('/tvs/', 'TVs'),
        ('/refrigerators/', 'Refrigerators'),
        ('/laundry/', 'Laundry'),
        ('/mobile-accessories/', 'Mobile Accessories'),
        ('/smartphones/galaxy-s26-ultra/', 'Galaxy S26 Ultra'),
        ('/smartphones/galaxy-s26-ultra/buy/', 'Buy'),
        ('/compare/', 'Galaxy Compare'),
        ('/support/', 'Samsung Support'),
        ('/support/warranty/', 'Warranty Center'),
        ('/support/contact/', 'Contact Us'),
        ('/search/?q=galaxy', 'Search results'),
        ('/account/login/', 'Sign In'),
        ('/cart/', 'Cart'),
    ]:
        try:
            status, body = get(path)
            if status != 200:
                failures.append(f'{path} -> {status}')
            elif marker.lower() not in body.lower():
                failures.append(f'{path} missing marker {marker!r}')
        except Exception as e:
            failures.append(f'{path} failed: {e}')

    if failures:
        for f in failures:
            print(f'[health] {f}')
        return 1
    print('[health] samsung all green')
    return 0


if __name__ == '__main__':
    sys.exit(probe(int(sys.argv[1]) if len(sys.argv) > 1 else 40219))
