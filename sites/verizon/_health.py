"""Per-site health probe for the verizon mirror."""
import json
import sys
import urllib.request


def health():
    return {"ok": True, "site": "verizon"}


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
        for key, floor in [('devices', 20), ('plans', 5), ('stores', 800),
                           ('content_pages', 8), ('protection_plans', 3),
                           ('trade_in_quotes', 20), ('troubleshoot_flows', 8),
                           ('users', 4), ('lines', 7), ('bills', 12),
                           ('usage', 7), ('orders', 1)]:
            if data.get(key, 0) < floor:
                failures.append(f"only {data.get(key)} {key} seeded")
    except Exception as e:
        print(f'[health] /_health failed: {e}')
        return 1

    for path, marker in [
        ('/', 'Simplicity Plan'),
        ('/plans/', 'Start by choosing the number of lines'),
        ('/prepaid/', 'Verizon Prepaid plans'),
        ('/smartphones/', 'Apple iPhone 18 Pro'),
        ('/smartphones/apple-iphone-18-pro/', 'Burgundy'),
        ('/smartphones/samsung-galaxy-s26/', 'Samsung Galaxy S26'),
        ('/smartphones/apple-iphone-18-pro/configure', 'Customize your Apple iPhone 18 Pro'),
        ('/cart/', 'Your cart'),
        ('/smartphones/motorola-moto-g-2026/', 'Motorola moto g - 2026'),
        ('/smartphones/motorola-moto-g-2026/configure', 'Customize your Motorola moto g - 2026'),
        ('/trade-in/', 'Trade in your device'),
        ('/trade-in/estimate/', 'which device are you trading in'),
        ('/stores/', 'Find a Verizon store'),
        ('/stores/washington/', 'Washington Verizon store locations'),
        ('/stores/washington/seattle/', 'Seattle Washington Verizon store locations'),
        ('/store/r00000151174/', 'Seattle Northgate'),
        ('/store/r00000151174/appointment/', 'Schedule an appointment at Seattle Northgate'),
        ('/support/', 'Verizon Support'),
        ('/support/return-policy/', 'Return policy'),
        ('/support/contact-us/', 'Contact us'),
        ('/support/troubleshoot/', "we're here to help you"),
        ('/account/login', 'Sign in to My Verizon'),
        ('/account/register', 'Register for My Verizon'),
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
    print(f'[health] verizon healthy: devices={data["devices"]} stores={data["stores"]}')
    return 0


if __name__ == '__main__':
    sys.exit(probe(int(sys.argv[1]) if len(sys.argv) > 1 else 43111))
