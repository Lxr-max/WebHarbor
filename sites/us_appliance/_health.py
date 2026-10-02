"""Per-site health probe for the us_appliance mirror.

Run standalone (`python3 _health.py [port]`) or import `health()` from the
control plane. Verifies the seed DB is populated and the key route families
render with real captured content.
"""
import json
import sys
import urllib.request


def health():
    return {"ok": True, "site": "us_appliance"}


def probe(port: int) -> int:
    failures = []

    def get(path):
        with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',
                                    timeout=20) as r:
            return r.status, r.read().decode('utf-8', 'replace')

    try:
        status, body = get('/_health')
        data = json.loads(body)
        if not data.get('ok'):
            failures.append(f"/_health not ok: {data}")
        if data.get('products', 0) < 12000:
            failures.append(f"only {data.get('products')} products seeded")
        if data.get('categories', 0) < 400:
            failures.append(f"only {data.get('categories')} categories seeded")
        if data.get('reviews', 0) < 200:
            failures.append(f"only {data.get('reviews')} reviews seeded")
        if data.get('orders', 0) < 8:
            failures.append(f"only {data.get('orders')} seeded orders")
    except Exception as e:  # noqa: BLE001
        print(f'[health] /_health failed: {e}')
        return 1

    for path, marker in [
        ('/', 'Shop by Appliance Category'),
        ('/ranges.html', 'Shop by Range Fuel Type'),
        ('/frdore.html?query=c232', 'French Door'),
        ('/search.php?search_query=ranges&section=product', 'Products ('),
        ('/jgbs66rekss.html', 'GE JGBS66REKSS'),
        ('/cart.php', 'Your Cart'),
        ('/ordertracking.html', 'R+L Carriers'),
        ('/testimonials.html', 'merchant reviews'),
        ('/faq.html', 'Frequently Asked Questions'),
        ('/rebates.html', 'Appliance Rebates'),
        ('/freedelivery.html', 'Nationwide Delivery'),
        ('/financeoffers.html', '0% Interest If Paid In Full In 15 Months'),
        ('/hugepricecuts.html', 'Appliance Deals Today'),
        ('/login.php', 'Sign in'),
        ('/shopbybrand.html', 'Shop By Brand'),
    ]:
        try:
            status, body = get(path)
            if status != 200:
                failures.append(f'{path} -> {status}')
            elif marker not in body:
                failures.append(f'{path} missing marker {marker!r}')
        except Exception as e:  # noqa: BLE001
            failures.append(f'{path} failed: {e}')

    if failures:
        for f in failures:
            print(f'[health] FAIL {f}')
        return 1
    print(f'[health] us_appliance healthy: {data}')
    return 0


if __name__ == '__main__':
    sys.exit(probe(int(sys.argv[1]) if len(sys.argv) > 1 else 40099))
