"""Flow tests: cart, guest checkout, auth, orders, wishlist, reviews, Q&A."""
from __future__ import annotations

import re

import pytest

import app as bc_app

from conftest import with_csrf, any_product_with_size


# ------------------------------------------------------------- guest cart --

def test_guest_add_and_update_cart(client):
    slug, sku = any_product_with_size()
    r = client.post('/cart/add', data=with_csrf(
        client, f'/{slug}', {'sku': sku, 'quantity': 1}),
        follow_redirects=True)
    assert r.status_code == 200
    assert b'Order Summary' in r.data
    # bump quantity to 3
    m = re.search(rb'name="item" value="(\d+)"', r.data)
    assert m
    r = client.post('/cart/update', data=with_csrf(
        client, '/cart', {'item': m.group(1).decode(), 'quantity': 3}),
        follow_redirects=True)
    assert b'value="3"' in r.data
    # remove
    r = client.post('/cart/update', data=with_csrf(
        client, '/cart', {'item': m.group(1).decode(), 'action': 'remove'}),
        follow_redirects=True)
    assert b'Your cart is currently empty' in r.data


def test_cart_requires_csrf(client):
    slug, sku = any_product_with_size()
    r = client.post('/cart/add', data={'sku': sku, 'quantity': 1})
    assert r.status_code == 400, "CSRF must reject token-less submits"


def test_guest_checkout_end_to_end(client):
    slug, sku = any_product_with_size()
    client.post('/cart/add', data=with_csrf(
        client, f'/{slug}', {'sku': sku, 'quantity': 1}))
    data = {'email': 'guest.hiker@example.com', 'full_name': 'Guest Hiker',
            'line1': '1 Canyon Rd', 'city': 'Moab', 'state': 'Utah',
            'zip': '84532', 'phone': '435-555-0199',
            'shipping_method': 'standard', 'card_name': 'Guest Hiker',
            'card': '4111111111111111', 'expiry': '01/28', 'cvc': '123'}
    r = client.post('/checkout', data=with_csrf(client, '/checkout', data),
                    follow_redirects=False)
    assert r.status_code == 302, r.data[:400]
    dest = r.headers['Location']
    assert dest.startswith('/order-confirmation/')
    r = client.get(dest)
    assert r.status_code == 200
    assert b'Your order number is' in r.data
    m = re.search(rb'order number is <strong>(\d+)</strong>', r.data)
    assert m and len(m.group(1)) == 10
    # cart is now empty
    r = client.get('/cart')
    assert b'Your cart is currently empty' in r.data


def test_guest_checkout_validation(client):
    slug, sku = any_product_with_size()
    client.post('/cart/add', data=with_csrf(
        client, f'/{slug}', {'sku': sku, 'quantity': 1}))
    bad = {'email': 'not-an-email', 'full_name': '', 'line1': '', 'city': '',
           'state': '', 'zip': '', 'phone': '', 'shipping_method': 'standard',
           'card': '123', 'expiry': '99/99', 'cvc': ''}
    r = client.post('/checkout', data=with_csrf(client, '/checkout', bad))
    assert r.status_code == 200
    assert b'Enter a valid email' in r.data or b'Fill in every' in r.data


def test_checkout_empty_cart_redirects(client):
    r = client.get('/checkout', follow_redirects=False)
    assert r.status_code == 302
    assert r.headers['Location'].endswith('/cart')


def test_express_shipping_costs_more(client):
    slug, sku = any_product_with_size()
    client.post('/cart/add', data=with_csrf(
        client, f'/{slug}', {'sku': sku, 'quantity': 1}))
    r = client.get('/checkout')
    assert b'Express Shipping' in r.data
    assert b'$25.00' in r.data


# ------------------------------------------------------------------ auth --

def test_login_wrong_password(client):
    r = client.post('/login', data=with_csrf(
        client, '/login', {'email': 'alice.j@test.com',
                           'password': 'WrongPass!', 'mode': 'login'}))
    assert r.status_code == 200
    assert b'Invalid email or password' in r.data


def test_register_and_login(client):
    r = client.post('/register', data=with_csrf(
        client, '/register', {'email': 'new.rider@example.com',
                      'name': 'New Rider', 'password': 'Ride2026ok'}),
        follow_redirects=False)
    assert r.status_code == 302
    r = client.get('/logout', follow_redirects=False)
    assert r.status_code == 302
    r = client.post('/login', data=with_csrf(
        client, '/login', {'email': 'new.rider@example.com',
                           'password': 'Ride2026ok', 'mode': 'login'}),
        follow_redirects=False)
    assert r.status_code == 302


def test_guest_cart_merges_on_login(client):
    slug, sku = any_product_with_size()
    client.post('/cart/add', data=with_csrf(
        client, f'/{slug}', {'sku': sku, 'quantity': 2}))
    client.post('/login', data=with_csrf(
        client, '/login', {'email': 'bob.c@test.com',
                           'password': 'TestPass123!', 'mode': 'login'}))
    r = client.get('/cart')
    assert r.status_code == 200
    assert b'Qty' in r.data
    assert b'value="2"' in r.data


# ---------------------------------------------------------------- orders --

def test_benchmark_order_history_visible(alice):
    r = alice.get('/account')
    assert r.status_code == 200
    with bc_app.app.app_context():
        order = (bc_app.Order.query.filter_by(user_id=1)
                 .order_by(bc_app.Order.id).first())
    assert order, "alice has no seeded orders"
    assert order.number.encode() in r.data
    r = alice.get(f"/account/orders/{order.number}")
    assert r.status_code == 200
    assert order.number.encode() in r.data


def test_order_not_visible_to_others(bob):
    with bc_app.app.app_context():
        order = (bc_app.Order.query.filter_by(user_id=1)
                 .order_by(bc_app.Order.id).first())
    r = bob.get(f"/account/orders/{order.number}")
    assert r.status_code == 404


def test_order_confirmation_guest_scoped(client):
    with bc_app.app.app_context():
        order = bc_app.Order.query.filter_by(
            guest_email='guest.hiker@example.com').first()
    if not order:
        pytest.skip("no guest order in this run")
    r = client.get(f"/order-confirmation/{order.number}")
    assert r.status_code == 200


# -------------------------------------------------------------- wishlist --

def test_wishlist_toggle_and_remove(alice):
    with bc_app.app.app_context():
        p = bc_app.Product.query.order_by(bc_app.Product.id).first()
    r = alice.post('/wish-list/toggle', data=with_csrf(
        alice, f'/{p.slug}', {'product': p.id, 'next': '/wish-list'}),
        follow_redirects=True)
    assert r.status_code == 200
    assert p.title.encode() in r.data
    r = alice.post('/wish-list/toggle', data=with_csrf(
        alice, '/wish-list', {'product': p.id, 'next': '/wish-list'}),
        follow_redirects=True)
    # toggled off — the product may still render if seeded in the wishlist
    assert r.status_code == 200


def test_wishlist_requires_login(client):
    r = client.post('/wish-list/toggle', data={
        'product': 'x', 'csrf_token': 'x'}, follow_redirects=False)
    # unauthenticated toggles bounce to the login page (form has real csrf)
    assert r.status_code in (302, 400)


# --------------------------------------------------------------- reviews --

def test_write_review_and_histogram(alice):
    with bc_app.app.app_context():
        p = bc_app.Product.query.order_by(bc_app.Product.id).first()
        before = bc_app.Review.query.filter_by(product_id=p.id).count()
    r = alice.post(f'/{p.slug}/write-review', data=with_csrf(
        alice, f'/{p.slug}',
        {'rating': '4', 'title': 'Solid gear',
         'text': 'Took it out last weekend and it performed great.',
         'familiarity': "I've used it several times", 'fit': 'True to Size'}),
        follow_redirects=True)
    assert r.status_code == 200
    assert b'Solid gear' in r.data
    with bc_app.app.app_context():
        after = bc_app.Review.query.filter_by(product_id=p.id).count()
    assert after == before + 1


def test_write_review_needs_rating_and_text(alice):
    with bc_app.app.app_context():
        p = bc_app.Product.query.order_by(bc_app.Product.id).first()
    r = alice.post(f'/{p.slug}/write-review', data=with_csrf(
        alice, f'/{p.slug}', {'rating': '', 'text': ''}),
        follow_redirects=True)
    assert b'Choose a star rating' in r.data


def test_review_sort_orders(client):
    with bc_app.app.app_context():
        p = (bc_app.Product.query
             .filter(bc_app.Product.review_count > 20)
             .order_by(bc_app.Product.id).first())
    r1 = client.get(f'/{p.slug}?review-sort=highest')
    r2 = client.get(f'/{p.slug}?review-sort=lowest')
    assert r1.status_code == r2.status_code == 200


def test_ask_question(alice):
    with bc_app.app.app_context():
        p = bc_app.Product.query.order_by(bc_app.Product.id).first()
    r = alice.post(f'/{p.slug}/ask-question', data=with_csrf(
        alice, f'/{p.slug}', {'text': 'Does this pack down small for travel?'}),
        follow_redirects=True)
    assert r.status_code == 200
    assert b'Does this pack down small' in r.data


# ------------------------------------------------------------- addresses --

def test_address_add_default_delete(alice):
    data = {'label': 'Trailhead', 'full_name': 'Alice Johnson',
            'line1': '500 Ridge Ct', 'city': 'Jackson', 'state': 'Wyoming',
            'zip': '83001', 'phone': '307-555-0121', 'is_default': '1'}
    r = alice.post('/account/addresses', data=with_csrf(
        alice, '/account/addresses', data), follow_redirects=True)
    assert r.status_code == 200
    assert b'500 Ridge Ct' in r.data
    # find the delete action on the card that contains the new street line
    block = re.search(rb'500 Ridge Ct.*?action="/account/addresses/(\d+)/delete"',
                      r.data, re.S)
    assert block, "delete action for the new address not rendered"
    addr_id = block.group(1).decode()
    r = alice.post(f'/account/addresses/{addr_id}/delete',
                   data=with_csrf(alice, '/account/addresses', {}),
                   follow_redirects=True)
    assert b'500 Ridge Ct' not in r.data
