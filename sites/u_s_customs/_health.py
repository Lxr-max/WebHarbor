"""Per-site health probe for the u_s_customs mirror."""
import json
import sys
import urllib.request


def health():
    return {"ok": True, "site": "u_s_customs"}


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
        if data.get('crossings', 0) < 80:
            failures.append(f"only {data.get('crossings')} crossings seeded")
        if data.get('ports', 0) < 300:
            failures.append(f"only {data.get('ports')} ports seeded")
        if data.get('releases', 0) < 40:
            failures.append(f"only {data.get('releases')} releases seeded")
    except Exception as e:
        print(f'[health] /_health failed: {e}')
        return 1

    for path, marker in [
        ('/', 'U.S. Customs and Border Protection'),
        ('/travel/advisories-wait-times', 'Border Wait Times'),
        ('/bwt', 'Border Wait Times'),
        ('/bwt/crossing/250401', 'San Ysidro'),
        ('/contact/ports', 'Locate a Port of Entry'),
        ('/travel/international-visitors/esta', 'Electronic System for Travel Authorization'),
        ('/esta/apply', 'Official ESTA Application'),
        ('/i94/request', 'Get Most Recent I-94'),
        ('/travel/trusted-traveler-programs/global-entry', 'Global Entry'),
        ('/newsroom/media-releases/all', 'Media Releases'),
        ('/newsroom/publications/forms', 'CBP Forms'),
        ('/trade/basic-import-export', 'Basic Import and Export'),
        ('/careers/search', 'Search Jobs'),
        ('/login', 'Log in'),
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
    print(f'[health] u_s_customs healthy: {data}')
    return 0


if __name__ == '__main__':
    sys.exit(probe(int(sys.argv[1]) if len(sys.argv) > 1 else 43105))
