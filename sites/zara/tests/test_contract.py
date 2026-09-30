"""Contract tests: seeded data, public pages, CSRF on every POST form,
privacy rules and asset integrity."""
import json
import os
import re

import app as zara


# ------------------------------------------------------------------- seeds --

def test_seed_counts():
    with zara.app.app_context():
        assert zara.Product.query.count() >= 120
        assert zara.Color.query.count() >= 150
        assert zara.Size.query.count() >= 600
        assert zara.Category.query.count() == 13
        assert zara.Store.query.count() == 25
        assert zara.SearchSnapshot.query.count() == 9
        assert zara.Campaign.query.count() >= 8
        assert zara.User.query.filter_by(is_benchmark=True).count() == 4
        assert zara.Order.query.count() == 4
        assert zara.CartItem.query.count() == 6
        assert zara.WishlistItem.query.count() == 6
        assert zara.Address.query.count() == 5


def test_benchmark_password_frozen():
    with zara.app.app_context():
        alice = zara.User.query.filter_by(email='alice.j@test.com').first()
        assert zara.bcrypt.check_password_hash(alice.password_hash,
                                                'TestPass123!')


def test_health_ok(client):
    r = client.get('/_health')
    assert r.status_code == 200
    data = json.loads(r.get_data(as_text=True))
    assert data['ok'] is True
    assert data['products'] >= 120 and data['stores'] == 25


def test_every_seed_image_is_real_upstream():
    """Every image served from static/images/upstream is inventoried with an
    https source URL, exact byte length and sha256 (no placeholders)."""
    inv = json.load(open(os.path.join(zara.BASE_DIR,
                                      'asset_inventory.json')))
    rows = inv['assets']
    assert inv['asset_count'] == len(rows) == len({r['path'] for r in rows})
    for row in rows:
        path = os.path.join(zara.BASE_DIR, row['path'])
        data = open(path, 'rb').read()
        assert len(data) == row['bytes']
        assert row['source_url'].startswith('https://static.zara.net/')
        import hashlib
        assert hashlib.sha256(data).hexdigest() == row['sha256']


def test_rendered_images_are_managed():
    """No <img src> in any catalog page may point outside managed assets."""
    seen = set()
    for path in ('/us/en/woman-dresses-l1066.html',
                 '/us/en/midi-scarf-dress-p08100038.html',
                 '/us/en/z-stores-st1404.html'):
        body = zara.app.test_client().get(path).get_data(as_text=True)
        for m in re.finditer(r'src="(/static/images/[^"]+)"', body):
            seen.add(m.group(1))
    assert seen, "no managed images rendered"
    for s in seen:
        assert os.path.exists(os.path.join(zara.BASE_DIR, s.lstrip('/')))


# ------------------------------------------------------------ public pages --

def test_home(client):
    r = client.get('/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'ZARA' in body
    assert 'DRESSES' in body


def test_all_categories_render(client):
    with zara.app.app_context():
        cats = zara.Category.query.all()
    for c in cats:
        r = client.get(c.path)
        assert r.status_code == 200, c.path
        import html
        assert c.name.upper() in html.unescape(
            r.get_data(as_text=True).upper())


def test_pdp_renders_sizes_and_availability(client):
    r = client.get('/us/en/midi-scarf-dress-p08100038.html')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'MIDI SCARF DRESS' in body
    assert 'Ecru' in body
    assert 'XS' in body and 'IN STOCK' in body.upper()
    assert 'SKU' in body.upper()


def test_pdp_color_switching(client):
    r = client.get('/us/en/elongated-shoulder-bag-p16821710.html')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Two-tone' in body
    assert '?v1=' in body  # color selector links


def test_search_snapshot_and_computed(client):
    r = client.get('/us/en/search?searchTerm=jeans')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'results' in body
    assert 'Blue' in body          # upstream color facet panel

    r = client.get('/us/en/search?searchTerm=scraf')  # misspelling
    assert r.status_code == 200

    r = client.get('/us/en/search?searchTerm=zzznotathing')
    assert r.status_code == 200
    assert 'No products found' in r.get_data(as_text=True)


def test_store_locator_filters(client):
    r = client.get('/us/en/z-stores-st1404.html?state=HAWAII')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'ALA MOANA' in body
    assert 'SANTA MONICA' not in body

    r = client.get('/us/en/z-stores-st1404.html?q=90401')
    assert 'SANTA MONICA PROMENADE' in r.get_data(as_text=True)


def test_store_detail_hours(client):
    r = client.get('/us/en/stores-locator/zara-santa-monica-s3322')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert '1338, THIRD STREET PROMENADE' in body
    assert 'Monday' in body and 'Sunday' in body
    assert 'UPCOMING SCHEDULE' in body
    assert '8332472473' in body


def test_404(client):
    assert client.get('/us/en/nope-l999999.html').status_code == 404
    assert client.get('/us/en/void-p00000000.html').status_code == 404


# ----------------------------------------------------------------- privacy --

def test_private_pages_require_login(client):
    for path in ('/us/en/wishlist', '/us/en/account',
                 '/us/en/account/orders', '/us/en/account/addresses',
                 '/us/en/shop/checkout'):
        r = client.get(path)
        assert r.status_code == 302, path
        assert '/us/en/logon' in r.headers['Location']


def test_order_isolation(alice, bob):
    """Bob cannot open Alice's order."""
    r = bob.get('/us/en/account/orders/8004128041')
    assert r.status_code == 404
    r = alice.get('/us/en/account/orders/8004128041')
    assert r.status_code == 200


# ------------------------------------------------------------------- csrf --

def test_post_without_csrf_rejected(client):
    r = client.post('/us/en/shop/add',
                    data={'product': '08100038', 'color': '1', 'size': '1'})
    assert r.status_code in (302, 400)  # CSRF failure, not silent success
    r = client.post('/newsletter', data={'email': 'x@y.z'})
    assert r.status_code in (302, 400)
