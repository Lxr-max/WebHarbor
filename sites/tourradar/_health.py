"""Per-site health probe for the tourradar mirror.

Run standalone (`python3 _health.py [port]`) or import `health()` from the
control plane. Verifies the seed DB is populated and the key route families
render with real content.
"""
import json
import sys
import urllib.request


def health():
    return {"ok": True, "site": "tourradar"}


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
        if data.get('tours', 0) < 50:
            failures.append(f"only {data.get('tours')} tours seeded")
        if data.get('departures', 0) < 100:
            failures.append(f"only {data.get('departures')} departures seeded")
    except Exception as e:
        print(f'[health] /_health failed: {e}')
        return 1

    for path, marker in [
        ('/', 'Top deals'),
        ('/srp/d-japan', 'tours found'),
        ('/t/255', 'Itinerary'),
        ('/book-now/255', 'Select accommodation'),
        ('/login', 'Log in'),
        ('/search?q=japan', 'Tours'),
        ('/o/macbackpackers', 'Reviews'),
        ('/moments', 'Traveler Moments'),
        ('/d/japan', 'Japan Tours'),
    ]:
        try:
            status, body = get(path)
            if status != 200:
                failures.append(f'{path} -> {status}')
            elif marker not in body:
                failures.append(f'{path} missing marker {marker!r}')
        except Exception as e:
            failures.append(f'{path} failed: {e}')

    if failures:
        for f in failures:
            print(f'[health] FAIL {f}')
        return 1
    print(f'[health] tourradar healthy: {data}')
    return 0


if __name__ == '__main__':
    sys.exit(probe(int(sys.argv[1]) if len(sys.argv) > 1 else 43102))
