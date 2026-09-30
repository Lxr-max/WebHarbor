"""Per-site health probe for the airbnb mirror."""
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
        if data.get('listings', 0) < 80:
            failures.append(f"only {data.get('listings')} listings seeded")
        if data.get('experiences', 0) < 40:
            failures.append(f"only {data.get('experiences')} experiences seeded")
        if data.get('reviews', 0) < 200:
            failures.append(f"only {data.get('reviews')} reviews seeded")
        if data.get('destinations', 0) != 8:
            failures.append(f"expected 8 destinations, got {data.get('destinations')}")
        if data.get('users', 0) != 4:
            failures.append(f"expected 4 benchmark users, got {data.get('users')}")
    except Exception as e:
        print(f'[health] /_health failed: {e}')
        return 1

    for path, marker in [
        ('/', 'Find your next stay'),
        ('/s/asheville/homes', 'Stays in Asheville'),
        ('/s/lake-tahoe/homes', 'Stays in Lake Tahoe'),
        ('/s/experiences?city=austin', 'Experiences in Austin'),
        ('/login', 'Log in'),
        ('/signup', 'Sign up'),
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
    print('[health] airbnb all green')
    return 0


if __name__ == '__main__':
    sys.exit(probe(int(sys.argv[1]) if len(sys.argv) > 1 else 40116))
