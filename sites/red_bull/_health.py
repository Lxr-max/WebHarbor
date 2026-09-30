"""Per-site health probe for the red_bull mirror."""
import json
import sys
import urllib.request


def health():
    return {"ok": True, "site": "red_bull"}


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
        for key, floor in [('products', 18), ('events', 90), ('event_series', 5),
                           ('event_faqs', 20), ('event_schedule_items', 20),
                           ('athletes', 50), ('films', 90), ('shows', 90),
                           ('episodes', 20), ('stories', 35), ('shop_products', 150),
                           ('shop_variants', 300), ('users', 4), ('shop_orders', 1),
                           ('event_registrations', 2), ('favorites', 8)]:
            if data.get(key, 0) < floor:
                failures.append(f"only {data.get(key)} {key} seeded")
    except Exception as e:                                      # noqa: BLE001
        print(f'[health] /_health failed: {e}')
        return 1

    for path, marker in [
        ('/', 'Energy Drinks'),
        ('/energydrink', 'Red Bull Editions'),
        ('/energydrink/red-bull-summer-edition', 'Sudachi Lime'),
        ('/events', 'Red Bull Events'),
        ('/events/red-bull-foam-wreckers-virginia-beach', 'Foam Wreckers'),
        ('/events/red-bull-foam-wreckers-virginia-beach/faqs', 'soft-boards'),
        ('/athletes', 'Red Bull Athletes'),
        ('/athletes/sky-brown', 'Miyazaki'),
        ('/films', 'Red Bull Films'),
        ('/shows', 'Red Bull TV Shows'),
        ('/stories', 'Red Bull Stories'),
        ('/shop', 'Red Bull Shop'),
        ('/cart', 'Your cart'),
    ]:
        try:
            status, body = get(path)
            if status != 200:
                failures.append(f"{path} -> {status}")
            elif marker not in body:
                failures.append(f"{path} missing marker {marker!r}")
        except Exception as e:                                  # noqa: BLE001
            failures.append(f"{path} failed: {e}")

    if failures:
        for f in failures:
            print(f'[health] {f}')
        return 1
    print('[health] red_bull OK')
    return 0


if __name__ == '__main__':
    sys.exit(probe(int(sys.argv[1]) if len(sys.argv) > 1 else 40210))
