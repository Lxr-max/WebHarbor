"""Per-site health probe for the wanderlog mirror."""
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
        if data.get('geos', 0) < 11:
            failures.append(f"only {data.get('geos')} geos seeded")
        if data.get('places', 0) < 400:
            failures.append(f"only {data.get('places')} places seeded")
        if data.get('guides', 0) < 14:
            failures.append(f"only {data.get('guides')} guides seeded")
        if data.get('trips', 0) < 5:
            failures.append(f"only {data.get('trips')} trips seeded")
    except Exception as e:
        print(f'[health] /_health failed: {e}')
        return 1

    for path, marker in [
        ('/', 'One app for all your travel planning needs'),
        ('/guides', 'Travel guides'),
        ('/view/uzyvvtuwtc', 'Paris 5 Day Tourist Itinerary'),
        ('/explore/1', 'Tokyo'),
        ('/explore/9614', 'Paris'),
        ('/list/geoCategory/1/where-to-eat-best-restaurants-in-tokyo', 'restaurants in Tokyo'),
        ('/place/details/99', 'Tower of London'),
        ('/hotels', 'Search for hotel'),
        ('/leaderboard', 'Traveler leaderboard'),
        ('/search?q=paris', 'Paris'),
        ('/login', 'Log in to Wanderlog'),
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
    print('[health] wanderlog all green')
    return 0


if __name__ == '__main__':
    sys.exit(probe(int(sys.argv[1]) if len(sys.argv) > 1 else 40113))
