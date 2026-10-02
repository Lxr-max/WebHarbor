"""End-to-end flow tests with CSRF enabled: auth, buy -> cart -> checkout
-> order history, wishlist, and the support ticket flow."""
import re

from conftest import csrf, login


def test_signup_login_logout(client):
    A, c = client
    token = csrf(c, '/account/signup/')
    r = c.post('/account/signup/', data={
        'name': 'Eve Tester', 'email': 'eve.t@test.com',
        'password': 'Sup3rSecret!', 'csrf_token': token,
    }, follow_redirects=True)
    assert r.status_code == 200
    assert b'My Account' in r.data
    r = c.get('/account/logout', follow_redirects=True)
    assert b'Sign In' in r.data
    r = login(c, 'eve.t@test.com', 'Sup3rSecret!')
    assert b'Eve Tester' in r.data


def test_login_wrong_password(client):
    A, c = client
    r = login(c, 'alice.j@test.com', 'WrongPass999')
    assert b'Invalid email or password' in r.data


def test_buy_add_to_cart_checkout_order(client):
    A, c = client
    r = login(c, 'alice.j@test.com')
    assert r.status_code == 200
    buy_url = '/smartphones/galaxy-s26-ultra/buy/?Storage=512GB'
    html = c.get(buy_url).data.decode()
    m = re.search(r'name="model_code" value="(SM-[A-Z0-9]+)"', html)
    assert m
    token = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"',
                      c.get(buy_url).data).group(1).decode()
    r = c.post(buy_url, data={
        'model_code': m.group(1), 'qty': '2', 'csrf_token': token,
    }, follow_redirects=True)
    assert b'added to your cart' in r.data.lower() or b'Added' in r.data
    html = c.get('/cart/').data.decode()
    assert 'Galaxy S26 Ultra' in html
    assert '$' in html

    token = csrf(c, '/checkout/')
    r = c.post('/checkout/', data={
        'full_name': 'Alice Johnson', 'email': 'alice.j@test.com',
        'address1': '42 Galaxy Way', 'city': 'Ridgefield Park',
        'state': 'NJ', 'zipcode': '07660', 'payment_method': 'Card',
        'csrf_token': token,
    }, follow_redirects=True)
    assert r.status_code == 200
    assert b'Order SS-' in r.data
    # the placed order shows its items on the order detail page
    order_no = re.search(r'Order (SS-[0-9]+)', r.data.decode()).group(1)
    html = c.get(f'/orders/{order_no}/').data.decode()
    assert 'Galaxy S26 Ultra' in html
    # the order also appears in the history list
    html = c.get('/orders/').data.decode()
    assert order_no in html
    # cart is now empty
    html = c.get('/cart/').data.decode()
    assert 'Your cart is empty' in html


def test_cart_qty_update_and_remove(client):
    A, c = client
    login(c, 'bob.c@test.com')
    html = c.get('/smartphones/galaxy-z-fold8-ultra/buy/').data.decode()
    model = re.search(r'name="model_code" value="(SM-[A-Z0-9]+)"', html).group(1)
    token = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"',
                      c.get('/smartphones/galaxy-z-fold8-ultra/buy/').data
                      ).group(1).decode()
    c.post('/smartphones/galaxy-z-fold8-ultra/buy/', data={
        'model_code': model, 'qty': '1', 'csrf_token': token})
    html = c.get('/cart/').data.decode()
    item_id = re.search(r'name="item_id" value="(\d+)"', html).group(1)
    token = csrf(c, '/cart/')
    c.post('/cart/update', data={'item_id': item_id, 'qty': '3',
                                 'csrf_token': token})
    html = c.get('/cart/').data.decode()
    assert '3' in html
    c.post('/cart/remove', data={'item_id': item_id, 'csrf_token': token})
    html = c.get('/cart/').data.decode()
    assert 'Your cart is empty' in html


def test_wishlist_toggle_flow(client):
    A, c = client
    login(c, 'carol.d@test.com')
    html = c.get('/smartphones/galaxy-z-flip8/').data.decode()
    token = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"',
                      c.get('/smartphones/galaxy-z-flip8/').data).group(1).decode()
    r = c.post('/wishlist/toggle', data={
        'product_slug': 'galaxy-z-flip8', 'csrf_token': token},
        follow_redirects=True)
    assert b'Added Galaxy Z Flip8' in r.data
    html = c.get('/account/wishlist/').data.decode()
    assert 'Galaxy Z Flip8' in html
    r = c.post('/wishlist/toggle', data={
        'product_slug': 'galaxy-z-flip8', 'csrf_token': token},
        follow_redirects=True)
    assert b'Removed Galaxy Z Flip8' in r.data


def test_contact_ticket_flow(client):
    A, c = client
    login(c, 'dana.k@test.com')
    token = csrf(c, '/support/contact/')
    r = c.post('/support/contact/', data={
        'category': 'Phones, Tablets & Wearables', 'topic': 'Warranty',
        'email': 'dana.k@test.com', 'subject': 'Buds pairing',
        'message': 'My Galaxy Buds4 Pro will not pair with my phone.',
        'csrf_token': token,
    }, follow_redirects=True)
    assert b'ST-' in r.data
    html = c.get('/account/').data.decode()
    assert 'Buds pairing' in html


def test_guest_cannot_add_to_cart_or_checkout(client):
    A, c = client
    html = c.get('/smartphones/galaxy-s26-ultra/buy/').data.decode()
    model = re.search(r'name="model_code" value="(SM-[A-Z0-9]+)"', html).group(1)
    token = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"',
                      c.get('/smartphones/galaxy-s26-ultra/buy/').data
                      ).group(1).decode()
    r = c.post('/smartphones/galaxy-s26-ultra/buy/', data={
        'model_code': model, 'qty': '1', 'csrf_token': token},
        follow_redirects=True)
    assert b'Sign In' in r.data          # bounced to login
    r = c.get('/checkout/', follow_redirects=True)
    assert b'Sign In' in r.data


def test_search_finds_products(client):
    A, c = client
    html = c.get('/search/?q=fold').data.decode()
    assert 'Galaxy Z Fold' in html
    html = c.get('/search/?q=zzzznotfound').data.decode()
    assert 'No products matched' in html
