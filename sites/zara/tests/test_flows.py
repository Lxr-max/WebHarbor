"""Flow tests: auth, bag, checkout, orders, wishlist, addresses — every
form submitted with a real CSRF token, like a browser."""
import re

from conftest import with_csrf

import app as zara


def _first_size(client, pdp):
    body = client.get(pdp).get_data(as_text=True)
    prod = re.search(r'name="product" value="([^"]+)"', body).group(1)
    color = re.search(r'name="color" value="(\d+)"', body).group(1)
    size = re.search(r'name="size" value="(\d+)"', body).group(1)
    return prod, color, size


# ------------------------------------------------------------------ auth ----

def test_register_login_logout(client):
    r = client.post('/us/en/logon?mode=register',
                    data=with_csrf(client, '/us/en/logon?mode=register',
                                   {'name': 'Zoe Tester',
                                    'email': 'zoe@example.com',
                                    'password': 'Passw0rd!',
                                    'mode': 'register'}))
    assert r.status_code == 302
    body = client.get('/us/en/account').get_data(as_text=True)
    assert 'HI, ZOE' in body.upper()

    client.get('/us/en/logon/logout')
    r = client.get('/us/en/account')
    assert r.status_code == 302

    r = client.post('/us/en/logon?mode=login',
                    data=with_csrf(client, '/us/en/logon',
                                   {'email': 'zoe@example.com',
                                    'password': 'Passw0rd!',
                                    'mode': 'login'}))
    assert r.status_code == 302


def test_login_rejects_bad_password(client):
    r = client.post('/us/en/logon?mode=login',
                    data=with_csrf(client, '/us/en/logon',
                                   {'email': 'alice.j@test.com',
                                    'password': 'wrong-pass',
                                    'mode': 'login'}))
    assert r.status_code == 401
    assert 'Incorrect email or password' in r.get_data(as_text=True)


def test_register_rejects_existing_email(client):
    r = client.post('/us/en/logon?mode=register',
                    data=with_csrf(client, '/us/en/logon?mode=register',
                                   {'name': 'Alice Again',
                                    'email': 'alice.j@test.com',
                                    'password': 'Passw0rd!',
                                    'mode': 'register'}))
    assert r.status_code == 400
    assert 'already exists' in r.get_data(as_text=True)


# ------------------------------------------------------------------- bag ----

def test_alice_sees_seeded_bag(alice):
    body = alice.get('/us/en/shop').get_data(as_text=True)
    assert 'MIDI SCARF DRESS' in body
    assert 'LEATHER WIDE HEEL BOOTS' in body
    assert 'SUMMARY' in body
    assert 'CHECKOUT' in body


def test_add_update_remove_bag(alice):
    prod, color, size = _first_size(
        alice, '/us/en/elongated-shoulder-bag-p16821710.html')
    r = alice.post('/us/en/shop/add',
                   data=with_csrf(alice,
                                  '/us/en/elongated-shoulder-bag-p16821710.html',
                                  {'product': prod, 'color': color,
                                   'size': size, 'quantity': '1'}))
    assert r.status_code == 302
    body = alice.get('/us/en/shop').get_data(as_text=True)
    assert 'ELONGATED SHOULDER BAG' in body

    m = re.search(r'ELONGATED SHOULDER BAG.*?name="item" value="(\d+)"',
                  body, re.S)
    item = m.group(1)
    r = alice.post('/us/en/shop/update',
                   data=with_csrf(alice, '/us/en/shop',
                                  {'item': item, 'quantity': '3',
                                   'action': 'update'}))
    assert r.status_code == 302
    body = alice.get('/us/en/shop').get_data(as_text=True)
    assert re.search(r'ELONGATED SHOULDER BAG.*?QTY', body, re.S)

    r = alice.post('/us/en/shop/update',
                   data=with_csrf(alice, '/us/en/shop',
                                  {'item': item, 'action': 'remove'}))
    assert r.status_code == 302
    assert 'ELONGATED SHOULDER BAG' not in \
        alice.get('/us/en/shop').get_data(as_text=True)


def test_guest_bag_isolation(client, alice):
    prod, color, size = _first_size(
        client, '/us/en/elongated-shoulder-bag-p16821710.html')
    client.post('/us/en/shop/add',
                data=with_csrf(client,
                               '/us/en/elongated-shoulder-bag-p16821710.html',
                               {'product': prod, 'color': color,
                                'size': size, 'quantity': '1'}))
    # Alice's bag is unaffected by the guest bag
    body = alice.get('/us/en/shop').get_data(as_text=True)
    assert 'MIDI SCARF DRESS' in body


def test_cannot_add_other_users_rows(bob, alice):
    body = alice.get('/us/en/shop').get_data(as_text=True)
    m = re.search(r'name="item" value="(\d+)"', body)
    r = bob.post('/us/en/shop/update',
                 data=with_csrf(bob, '/us/en/shop',
                                 {'item': m.group(1), 'action': 'remove'}))
    assert r.status_code == 403


# --------------------------------------------------------------- checkout ----

def test_checkout_flow_with_saved_address(alice):
    # seeded bag has 2 items
    body = alice.get('/us/en/shop/checkout').get_data(as_text=True)
    m = re.search(r'name="address_id" value="(\d+)"', body)
    r = alice.post('/us/en/shop/checkout',
                   data=with_csrf(alice, '/us/en/shop/checkout',
                                  {'address_id': m.group(1),
                                   'card': '4111111111111111',
                                   'expiry': '12/28'}))
    assert r.status_code == 302
    loc = r.headers['Location']
    assert '/us/en/shop/confirm/' in loc
    body = alice.get(loc).get_data(as_text=True)
    assert 'THANK YOU' in body.upper()
    # bag is now empty; order appears in the account
    assert 'Your bag is empty' in alice.get('/us/en/shop').get_data(as_text=True)
    body = alice.get('/us/en/account/orders').get_data(as_text=True)
    assert re.search(r'80\d{9}', body)


def test_checkout_rejects_bad_card(alice):
    prod, color, size = _first_size(alice,
                                    '/us/en/elongated-shoulder-bag-p16821710.html')
    alice.post('/us/en/shop/add',
               data=with_csrf(alice,
                              '/us/en/elongated-shoulder-bag-p16821710.html',
                              {'product': prod, 'color': color,
                               'size': size, 'quantity': '1'}))
    r = alice.post('/us/en/shop/checkout',
                   data=with_csrf(alice, '/us/en/shop/checkout',
                                  {'address_id': '1',
                                   'card': '123',
                                   'expiry': '12/28'}))
    assert r.status_code == 200  # re-render with error
    assert 'valid 16-digit card' in r.get_data(as_text=True)


def test_new_user_full_purchase(client):
    client.post('/us/en/logon?mode=register',
                data=with_csrf(client, '/us/en/logon?mode=register',
                               {'name': 'Nina Buyer',
                                'email': 'nina@example.com',
                                'password': 'Passw0rd!',
                                'mode': 'register'}))
    prod, color, size = _first_size(client,
                                    '/us/en/midi-scarf-dress-p08100038.html')
    client.post('/us/en/shop/add',
                data=with_csrf(client,
                               '/us/en/midi-scarf-dress-p08100038.html',
                               {'product': prod, 'color': color,
                                'size': size, 'quantity': '2'}))
    r = client.post('/us/en/shop/checkout',
                    data=with_csrf(client, '/us/en/shop/checkout',
                                   {'new_address': '1',
                                    'full_name': 'Nina Buyer',
                                    'line1': '12 Market St',
                                    'city': 'Austin',
                                    'state': 'TX',
                                    'zip': '78701',
                                    'phone': '512-555-0100',
                                    'card': '5555666677778888',
                                    'expiry': '09/27'}))
    assert r.status_code == 302
    body = client.get(r.headers['Location']).get_data(as_text=True)
    assert 'MIDI SCARF DRESS' in body
    assert 'ending in 8888' in body


# ---------------------------------------------------------------- orders ----

def test_order_history_and_detail(alice):
    body = alice.get('/us/en/account/orders').get_data(as_text=True)
    assert '8004128041' in body and '8004193147' in body
    assert 'Delivered' in body and 'Shipped' in body

    body = alice.get('/us/en/account/orders/8004128041').get_data(as_text=True)
    assert 'SHOULDER PAD ZIP JACKET' in body
    assert '100% LEATHER PUFFED-BODY DRESS' in body
    assert '4417' in body


def test_order_item_prices_match_catalog(alice):
    """Fixture order prices must equal the products' real captured prices."""
    body = alice.get('/us/en/account/orders/8004128041').get_data(as_text=True)
    with zara.app.app_context():
        p = zara.Product.query.filter_by(seo_id='05479900').first()
        assert f"USD {p.price / 100:,.2f}" in body


# --------------------------------------------------------------- wishlist ----

def test_wishlist_toggle(alice):
    body = alice.get('/us/en/wishlist').get_data(as_text=True)
    assert 'DRAPED SEQUIN MIDI DRESS' in body  # seeded

    alice.post('/us/en/wishlist/toggle',
               data=with_csrf(alice, '/us/en/midi-scarf-dress-p08100038.html',
                              {'product': '08100038', 'color': '712',
                               'back': '/us/en/wishlist'}))
    body = alice.get('/us/en/wishlist').get_data(as_text=True)
    assert 'MIDI SCARF DRESS' in body

    alice.post('/us/en/wishlist/toggle',
               data=with_csrf(alice, '/us/en/wishlist',
                              {'product': '08100038', 'color': '712',
                               'back': '/us/en/wishlist'}))
    body = alice.get('/us/en/wishlist').get_data(as_text=True)
    assert 'MIDI SCARF DRESS' not in body
    assert 'DRAPED SEQUIN MIDI DRESS' in body  # seeded items intact


# -------------------------------------------------------------- addresses ----

def test_address_add_default_delete(alice):
    r = alice.post('/us/en/account/addresses/add',
                   data=with_csrf(alice, '/us/en/account/addresses',
                                  {'label': 'BEACH',
                                   'full_name': 'Alice Johnson',
                                   'line1': '1 Pier Ave',
                                   'city': 'Santa Monica',
                                   'state': 'CA',
                                   'zip': '90401',
                                   'phone': '310-555-0199'}))
    assert r.status_code == 302
    body = alice.get('/us/en/account/addresses').get_data(as_text=True)
    assert 'BEACH' in body

    m = re.findall(r'action="/us/en/account/addresses/(\d+)/default"', body)
    r = alice.post(f'/us/en/account/addresses/{m[-1]}/default',
                   data=with_csrf(alice, '/us/en/account/addresses', {}))
    assert r.status_code == 302
    body = alice.get('/us/en/account/addresses').get_data(as_text=True)

    m = re.findall(r'action="/us/en/account/addresses/(\d+)/delete"', body)
    r = alice.post(f'/us/en/account/addresses/{m[-1]}/delete',
                   data=with_csrf(alice, '/us/en/account/addresses', {}))
    assert r.status_code == 302
    assert 'BEACH' not in alice.get(
        '/us/en/account/addresses').get_data(as_text=True)


def test_address_validation(alice):
    r = alice.post('/us/en/account/addresses/add',
                   data=with_csrf(alice, '/us/en/account/addresses',
                                  {'label': 'X', 'full_name': '',
                                   'line1': '1 St', 'city': 'NY',
                                   'state': 'NY', 'zip': '10001',
                                   'phone': '212-555-0100'}))
    assert r.status_code == 400
    assert 'Fill in every address field' in r.get_data(as_text=True)


# ------------------------------------------------------------- newsletter ----

def test_newsletter_signup(client):
    r = client.post('/newsletter',
                    data=with_csrf(client, '/',
                                   {'email': 'shopper@example.com',
                                    'section': 'WOMAN'}))
    assert r.status_code == 200
    assert 'subscribed' in r.get_data(as_text=True)
    with zara.app.app_context():
        row = zara.NewsletterSignup.query.filter_by(
            email='shopper@example.com').first()
        assert row is not None and row.section == 'WOMAN'


# --------------------------------------------------------------- category ----

def test_category_filter_and_sort(client):
    r = client.get('/us/en/woman-dresses-l1066.html?color=Black')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'products' in body

    r = client.get('/us/en/woman-dresses-l1066.html?sort=price-asc')
    body = r.get_data(as_text=True)
    prices = [float(x) for x in
              re.findall(r'USD ([\d,]+\.\d{2})', body)]
    assert prices == sorted(prices)
