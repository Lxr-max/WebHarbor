"""Per-site health probe for the usps mirror."""
import json
import sys
import urllib.request


def health():
    return {"ok": True, "site": "usps"}


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
        if data.get('rates', 0) < 3000:
            failures.append(f"only {data.get('rates')} rates seeded")
        if data.get('post_offices', 0) < 4000:
            failures.append(f"only {data.get('post_offices')} post offices seeded")
        if data.get('countries', 0) < 40:
            failures.append(f"only {data.get('countries')} countries seeded")
        if data.get('products', 0) < 40:
            failures.append(f"only {data.get('products')} products seeded")
        if data.get('pages', 0) < 40:
            failures.append(f"only {data.get('pages')} pages seeded")
    except Exception as e:
        print(f'[health] /_health failed: {e}')
        return 1

    for path, marker in [
        ('/', 'Quick Tools'),
        ('/ship/priority-mail.htm', 'Priority Mail'),
        ('/postcalc/', 'Calculate a Price'),
        ('/postcalc/letters', 'First-Class Mail'),
        ('/postcalc/packages', 'Ground Advantage'),
        ('/postcalc/international', 'Priority Mail International'),
        ('/postcalc/extra-services', 'Certified Mail'),
        ('/tracking/', 'Track a Package'),
        ('/tracking/9405500000000000000003', 'In Transit'),
        ('/tracking/9405500000000000000001', 'Delivered'),
        ('/clicknship/', 'Click-N-Ship'),
        ('/pickup/', 'Schedule a Pickup'),
        ('/locations/', 'Find USPS Locations'),
        ('/locations/?q=90210', 'Beverly Hills'),
        ('/po-boxes/', 'PO Box'),
        ('/store/stamps', 'Stamps'),
        ('/store/product/breast-cancer-research-stamps-S_555304',
         'Breast Cancer Research'),
        ('/manage/hold-mail.htm', 'Hold Mail'),
        ('/manage/hold-mail/request', None),  # login-gated: 302 to sign-in
        ('/manage/forward.htm', 'Change My Address'),
        ('/manage/change-address/request', 'Forwarding'),
        ('/international/countries', 'Japan'),
        ('/international/countries/japan', 'Prohibitions'),
        ('/help/claims.htm', 'Claim'),
        ('/claims/status', 'Claim Status'),
        ('/newsroom/', 'Newsroom'),
        ('/login', 'Sign In'),
        ('/search/?q=stamps', 'Search Results'),
    ]:
        try:
            status, body = get(path)
            if marker is None:
                # login-gated tool pages must redirect to sign-in
                if status not in (200, 302):
                    failures.append(f'{path} -> {status}')
            elif status != 200:
                failures.append(f'{path} -> {status}')
            elif marker not in body:
                failures.append(f'{path} missing marker {marker!r}')
        except Exception as e:
            failures.append(f'{path} failed: {e}')

    if failures:
        for f in failures:
            print(f'[health] FAIL {f}')
        return 1
    print(f'[health] usps healthy: {data}')
    return 0


if __name__ == '__main__':
    sys.exit(probe(int(sys.argv[1]) if len(sys.argv) > 1 else 43110))
