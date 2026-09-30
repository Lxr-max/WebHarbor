"""Per-site health probe for the carvana mirror."""
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
        if data.get('vehicles', 0) < 1000:
            failures.append(f"only {data.get('vehicles')} vehicles seeded")
        if data.get('details', 0) < 40:
            failures.append(f"only {data.get('details')} vehicle details seeded")
        if data.get('users', 0) != 4:
            failures.append(f"expected 4 benchmark users, got {data.get('users')}")
        if data.get('reviews', 0) < 100:
            failures.append(f"only {data.get('reviews')} reviews seeded")
        if data.get('snapshots', 0) < 80:
            failures.append(f"only {data.get('snapshots')} search snapshots seeded")
    except Exception as e:
        print(f'[health] /_health failed: {e}')
        return 1

    for path, marker in [
        ('/', 'Buy a car online'),
        ('/cars', 'cars match your search'),
        ('/cars?make=Honda', 'Honda'),
        ('/cars?body=SUV', 'SUV'),
        ('/cars?fuel=Electric', 'Electric'),
        ('/vehicle/4466702', '2025 Nissan Altima'),
        ('/vehicle/4120245', '2025 Ram 2500 Crew Cab'),
        ('/how-it-works', 'How It Works'),
        ('/financing', 'Finance Your Next Vehicle Purchase'),
        ('/faq', 'What do you need help with?'),
        ('/certified-program', 'Carvana Certified'),
        ('/sell-my-car', 'Sell or trade in your car'),
        ('/authn/login', 'Welcome back'),
        ('/authn/register', 'Create your account'),
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
    print('[health] carvana all green')
    return 0


if __name__ == '__main__':
    sys.exit(probe(int(sys.argv[1]) if len(sys.argv) > 1 else 40193))
