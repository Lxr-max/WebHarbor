"""Per-site health probe for the zara mirror."""
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
        if data.get('products', 0) < 100:
            failures.append(f"only {data.get('products')} products seeded")
        if data.get('colors', 0) < 150:
            failures.append(f"only {data.get('colors')} colors seeded")
        if data.get('sizes', 0) < 600:
            failures.append(f"only {data.get('sizes')} sizes seeded")
        if data.get('categories', 0) != 13:
            failures.append(f"expected 13 categories, got {data.get('categories')}")
        if data.get('stores', 0) != 25:
            failures.append(f"expected 25 stores, got {data.get('stores')}")
        if data.get('searches', 0) != 9:
            failures.append(f"expected 9 search snapshots, got {data.get('searches')}")
        if data.get('users', 0) != 4:
            failures.append(f"expected 4 benchmark users, got {data.get('users')}")
        if data.get('orders', 0) != 4:
            failures.append(f"expected 4 seeded orders, got {data.get('orders')}")
    except Exception as e:
        print(f'[health] /_health failed: {e}')
        return 1

    for path, marker in [
        ('/', 'ZARA'),
        ('/us/en/woman-dresses-l1066.html', 'MIDI SCARF DRESS'),
        ('/us/en/man-jackets-l640.html', 'JACKETS'),
        ('/us/en/kids-girl-dresses-jumpsuits-l360.html', 'GIRL DRESSES'),
        ('/us/en/beauty-perfumes-l1415.html', 'PERFUMES'),
        ('/us/en/midi-scarf-dress-p08100038.html', 'Ecru'),
        ('/us/en/search?searchTerm=jeans', 'results'),
        ('/us/en/search?searchTerm=coat', 'Blue'),
        ('/us/en/z-stores-st1404.html', 'SANTA MONICA PROMENADE'),
        ('/us/en/z-stores-st1404.html?state=HAWAII', 'ALA MOANA'),
        ('/us/en/logon', 'LOG IN'),
        ('/us/en/logon?mode=register', 'CREATE ACCOUNT'),
        ('/us/en/shop', 'BAG'),
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
    print('[health] zara all green')
    return 0


if __name__ == '__main__':
    sys.exit(probe(int(sys.argv[1]) if len(sys.argv) > 1 else 40114))
