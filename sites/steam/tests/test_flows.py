"""End-to-end flow tests with CSRF enabled: auth, wishlist, cart ->
checkout -> order history, and the account surface."""
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
    assert b'Eve Tester' in r.data
    r = c.get('/account/logout', follow_redirects=True)
    assert b'Sign in' in r.data
    r = login(c, 'eve.t@test.com', 'Sup3rSecret!')
    assert b'Eve Tester' in r.data


def test_login_wrong_password(client):
    A, c = client
    r = login(c, 'alice.j@test.com', 'WrongPass999')
    assert b'Invalid email or password' in r.data


def test_wishlist_add_remove(client):
    A, c = client
    login(c, 'alice.j@test.com')
    html = c.get('/wishlist/').data.decode()
    assert 'Counter-Strike 2' in html and 'Dota 2' in html
    token = csrf(c, '/app/413150/')
    c.post('/wishlist/toggle', data={
        'appid': '413150', 'next': '/wishlist/', 'csrf_token': token})
    html = c.get('/wishlist/').data.decode()
    before = len(re.findall(r'class="capsule"', html))
    assert before == 3
    token = csrf(c, '/wishlist/')
    c.post('/wishlist/toggle', data={
        'appid': '413150', 'next': '/wishlist/', 'csrf_token': token})
    html = c.get('/wishlist/').data.decode()
    after = len(re.findall(r'class="capsule"', html))
    assert after == 2


def test_wishlist_requires_login(client):
    A, c = client
    r = c.get('/wishlist/')
    assert r.status_code == 302
    assert '/account/login/' in r.headers['Location']


def test_cart_add_qty_remove_checkout(client):
    A, c = client
    token = csrf(c, '/app/1245620/')
    r = c.post('/cart/add', data={
        'kind': 'game', 'appid': '1245620', 'qty': '1', 'csrf_token': token,
    }, follow_redirects=True)
    assert b'ELDEN RING' in r.data
    token = csrf(c, '/bundle/234/')
    r = c.post('/cart/add', data={
        'kind': 'bundle', 'bundle_id': '234', 'qty': '1',
        'csrf_token': token}, follow_redirects=True)
    assert b'Portal Bundle' in r.data
    html = c.get('/cart/').data.decode()
    assert '$74.97' in html  # 59.99 + 14.98
    item_id = re.search(r'name="item_id" value="(\d+)"', html).group(1)
    token = csrf(c, '/cart/')
    r = c.post('/cart/update', data={
        'item_id': item_id, 'qty': '2', 'csrf_token': token},
        follow_redirects=True)
    assert '$134.96' in html or '$134.96' in r.data.decode()
    login(c, 'alice.j@test.com')
    token = csrf(c, '/checkout/')
    r = c.post('/checkout/', data={
        'full_name': 'Alice Johnson', 'email': 'alice.j@test.com',
        'address1': '42 Pipeline Way', 'city': 'Bellevue', 'state': 'WA',
        'zipcode': '98004', 'payment_method': 'Visa', 'csrf_token': token,
    }, follow_redirects=True)
    assert r.status_code == 200
    m = re.search(rb'your order (ST-\d+) is confirmed', r.data, re.I)
    assert m
    order_no = m.group(1).decode()
    html = c.get(f'/order/{order_no}/').data.decode()
    assert 'ELDEN RING' in html and 'Portal Bundle' in html
    html = c.get('/account/').data.decode()
    assert order_no in html and 'ST-1001' in html
    html = c.get('/cart/').data.decode()
    assert 'Your cart is empty' in html


def test_cart_remove(client):
    A, c = client
    token = csrf(c, '/app/550/')
    c.post('/cart/add', data={
        'kind': 'game', 'appid': '550', 'qty': '1', 'csrf_token': token})
    html = c.get('/cart/').data.decode()
    item_id = re.search(r'name="item_id" value="(\d+)"', html).group(1)
    token = csrf(c, '/cart/')
    r = c.post('/cart/remove', data={
        'item_id': item_id, 'csrf_token': token}, follow_redirects=True)
    assert 'Your cart is empty' in r.data.decode()


def test_checkout_requires_login_and_cart(client):
    A, c = client
    r = c.get('/checkout/')
    assert r.status_code == 302  # not signed in
    login(c, 'bob.s@test.com')
    r = c.get('/checkout/', follow_redirects=True)
    assert 'Your cart is empty' in r.data.decode()


def test_checkout_validation(client):
    A, c = client
    token = csrf(c, '/app/550/')
    c.post('/cart/add', data={
        'kind': 'game', 'appid': '550', 'qty': '1', 'csrf_token': token})
    login(c, 'bob.s@test.com')
    token = csrf(c, '/checkout/')
    r = c.post('/checkout/', data={
        'full_name': '', 'email': 'not-an-email', 'address1': '',
        'city': '', 'state': '', 'zipcode': '', 'payment_method': 'Visa',
        'csrf_token': token}, follow_redirects=True)
    assert b'fill in every field' in r.data or b'valid email' in r.data
    # cart must survive the failed checkout
    html = c.get('/cart/').data.decode()
    assert 'Left 4 Dead 2' in html


def test_order_number_sequence(client):
    A, c = client
    token = csrf(c, '/app/550/')
    c.post('/cart/add', data={
        'kind': 'game', 'appid': '550', 'qty': '1', 'csrf_token': token})
    login(c, 'carol.m@test.com')
    token = csrf(c, '/checkout/')
    r = c.post('/checkout/', data={
        'full_name': 'Carol Martinez', 'email': 'carol.m@test.com',
        'address1': '12 Farm Lane', 'city': 'Portland', 'state': 'OR',
        'zipcode': '97201', 'payment_method': 'Visa', 'csrf_token': token,
    }, follow_redirects=True)
    m = re.search(rb'your order (ST-\d+) is confirmed', r.data, re.I)
    assert m and m.group(1).decode() == 'ST-1004'
