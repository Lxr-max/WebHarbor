"""Per-site health probe for the microsoft_azure mirror."""
import json
import sys
import urllib.request


def health():
    return {"ok": True, "site": "microsoft_azure"}


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
        for key, floor in [('products', 200), ('product_categories', 20),
                           ('product_pages', 20), ('pricing_cards', 40),
                           ('calc_services', 4), ('regions', 55),
                           ('free_services', 80), ('stories', 140),
                           ('story_industries', 10), ('blog_posts', 20),
                           ('dict_articles', 80), ('support_plans', 4),
                           ('users', 4), ('vm_prices', 500)]:
            if data.get(key, 0) < floor:
                failures.append(f"only {data.get(key)} {key} seeded")
    except Exception as e:
        print(f'[health] /_health failed: {e}')
        return 1

    for path, marker in [
        ('/', 'Microsoft Azure'),
        ('/products/', 'Azure products'),
        ('/products/kubernetes-service/', 'Azure Kubernetes Service'),
        ('/pricing/', 'Pricing'),
        ('/pricing/calculator/', 'Pricing calculator'),
        ('/pricing/details/kubernetes-service/', 'Azure Kubernetes Service'),
        ('/pricing/free-services/', 'free'),
        ('/explore/global-infrastructure/geographies/', 'geographies'),
        ('/customer-stories/', 'customer'),
        ('/blog/', 'Azure Blog'),
        ('/resources/cloud-computing-dictionary/', 'Cloud computing terminology'),
        ('/support/', 'Azure support'),
        ('/search/', 'Search'),
        ('/account/login', 'Sign in'),
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
            print(f'[health] FAIL {f}')
        return 1
    print(f'[health] microsoft_azure healthy: products={data.get("products")} stories={data.get("stories")}')
    return 0


if __name__ == '__main__':
    sys.exit(probe(int(sys.argv[1]) if len(sys.argv) > 1 else 40212))
