"""Flow tests: auth, favorites, checkout with delivery scheduling,
sell-your-car offers, profile edits and the benchmark fixtures — all with
CSRF enabled, submitting real tokens like a browser."""
import json
import re

import app as cv
from conftest import with_csrf


def test_register_login_logout(client):
    r = client.post('/authn/register', data=with_csrf(
        client, '/authn/register',
        {'display_name': 'Test User', 'email': 'test@example.com',
         'password': 'Password123'}))
    assert r.status_code == 302
    r = client.get('/account/favorites')
    assert r.status_code == 200
    r = client.get('/authn/logout')
    assert r.status_code == 302
    r = client.post('/authn/login', data=with_csrf(
        client, '/authn/login',
        {'email': 'test@example.com', 'password': 'Password123'}))
    assert r.status_code == 302
    assert client.get('/account/favorites').status_code == 200


def test_register_rejects_bad_input(client):
    r = client.post('/authn/register', data=with_csrf(
        client, '/authn/register',
        {'display_name': 'X', 'email': 'not-an-email',
         'password': 'Password123'}))
    assert r.status_code == 200
    assert 'valid email' in r.get_data(as_text=True)
    r = client.post('/authn/register', data=with_csrf(
        client, '/authn/register',
        {'display_name': 'X', 'email': 'x@example.com', 'password': 'short'}))
    assert 'at least 8' in r.get_data(as_text=True)


def test_login_rejects_wrong_password(client):
    r = client.post('/authn/login', data=with_csrf(
        client, '/authn/login',
        {'email': 'alice.j@test.com', 'password': 'WrongPass'}))
    assert r.status_code == 200
    assert 'Invalid email or password' in r.get_data(as_text=True)


def test_login_required_redirects(client):
    r = client.get('/account/favorites')
    assert r.status_code == 302
    assert '/authn/login' in r.headers['Location']


def test_save_and_unsave(alice):
    body = alice.get('/vehicle/4466702').get_data(as_text=True)
    assert 'Save this car' in body
    r = alice.post('/vehicle/4466702/favorite',
                   data=with_csrf(alice, '/vehicle/4466702', {}))
    assert r.status_code == 302
    body = alice.get('/vehicle/4466702').get_data(as_text=True)
    assert 'Saved ♥' in body
    # it appears in the favorites page
    body = alice.get('/account/favorites').get_data(as_text=True)
    assert 'Nissan Altima' in body
    # remove it again
    r = alice.post('/vehicle/4466702/favorite',
                   data=with_csrf(alice, '/vehicle/4466702', {}))
    body = alice.get('/account/favorites').get_data(as_text=True)
    assert 'Nissan Altima' not in body


def test_alice_seed_fixture(alice):
    body = alice.get('/account/favorites').get_data(as_text=True)
    assert 'Honda Civic' in body
    assert 'Toyota RAV4' in body
    assert 'Tesla Model 3' in body
    body = alice.get('/account/orders').get_data(as_text=True)
    assert 'CV-100026' in body
    assert 'Delivery scheduled' in body
    assert '2026-10-02' in body


def test_bob_delivered_order_timeline(bob):
    body = bob.get('/account/orders').get_data(as_text=True)
    assert 'CV-100019' in body
    assert 'Delivered' in body
    assert 'Financing approved' in body
    assert 'Out for delivery' in body
    assert '7-Day Money-Back Guarantee started' in body


def test_dana_financing_review_order(dana):
    body = dana.get('/account/orders').get_data(as_text=True)
    assert 'CV-100033' in body
    assert 'Financing review' in body


def test_carol_fixture(carol):
    body = carol.get('/account/favorites').get_data(as_text=True)
    assert 'BMW 3 Series' in body
    assert carol.get('/account/orders').get_data(as_text=True).count(
        'order-card') == 0


def test_checkout_full_flow(alice):
    """Full purchase: finance terms, delivery date/slot, address, order
    confirmation with a real monthly payment."""
    # a car Alice has not ordered yet
    with cv.app.app_context():
        v = (cv.Vehicle.query.filter(cv.Vehicle.make == 'Toyota')
             .order_by(cv.Vehicle.vehicle_id).first())
        vid = v.vehicle_id
        price = v.price
        taxes = v.estimated_taxes_fees or 0
    r = alice.get(f'/vehicle/{vid}/checkout')
    assert r.status_code == 200
    assert 'Complete your purchase' in r.get_data(as_text=True)
    r = alice.post(f'/vehicle/{vid}/checkout', data=with_csrf(
        alice, f'/vehicle/{vid}/checkout',
        {'payment_type': 'finance', 'down_payment': '2000', 'term': '60',
         'credit_tier': 'great', 'trade_in': 'no', 'trade_credit': '0',
         'delivery_date': '2026-10-01', 'delivery_slot': '2:00 PM - 4:00 PM',
         'street': '2811 Maple Ave', 'city': 'Seattle', 'state': 'wa',
         'zip': '98103'}))
    assert r.status_code == 302
    loc = r.headers['Location']
    assert '/order/' in loc
    body = alice.get(loc).get_data(as_text=True)
    assert 'Your order is confirmed' in body
    # the payment on the confirmation is the amortization over 6.24%
    principal = price + taxes - 2000
    rate = 6.24 / 100 / 12
    expect = int(round(principal * rate / (1 - (1 + rate) ** -60)))
    assert f"${expect:,}/mo" in body
    # the confirmation shows the amount financed for financed orders
    assert 'Amount financed' in body
    assert f"${principal:,}" in body
    # and it shows in orders with a timeline
    body = alice.get('/account/orders').get_data(as_text=True)
    assert 'Order placed' in body
    assert '2026-10-01' in body


def test_checkout_rejects_bad_delivery(alice):
    with cv.app.app_context():
        v = (cv.Vehicle.query.filter(cv.Vehicle.make == 'Jeep')
             .order_by(cv.Vehicle.vehicle_id).first())
        vid = v.vehicle_id
    r = alice.post(f'/vehicle/{vid}/checkout', data=with_csrf(
        alice, f'/vehicle/{vid}/checkout',
        {'payment_type': 'cash', 'trade_in': 'no',
         'delivery_date': '2020-01-01', 'delivery_slot': '2:00 PM - 4:00 PM',
         'street': '1 Main St', 'city': 'Seattle', 'state': 'WA',
         'zip': '98103'}))
    assert r.status_code == 200
    assert 'Complete the delivery details' in r.get_data(as_text=True)


def test_order_cancel_flow(dana):
    dana.post('/account/orders/CV-100033/cancel', data=with_csrf(
        dana, '/account/orders', {}))
    body = dana.get('/account/orders').get_data(as_text=True)
    assert 'Cancelled' in body
    assert 'Order cancelled by customer' in body


def test_sell_my_car_offer_flow(client):
    body = client.get('/sell-my-car').get_data(as_text=True)
    assert 'Get my offer' in body
    r = client.get('/sell-my-car/offer')
    assert r.status_code == 200
    r = client.post('/sell-my-car/offer', data=with_csrf(
        client, '/sell-my-car/offer',
        {'vin': '1HGCM82633A004352', 'mileage': '45000',
         'condition': 'good'}))
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Your instant offer' in body
    m = re.search(r'\$([\d,]+)', body)
    assert m
    # deterministic: same VIN -> same offer
    r2 = client.post('/sell-my-car/offer', data=with_csrf(
        client, '/sell-my-car/offer',
        {'vin': '1HGCM82633A004352', 'mileage': '45000',
         'condition': 'good'}))
    assert re.search(r'\$([\d,]+)', r2.get_data(as_text=True)).group(1) \
        == m.group(1)


def test_sell_offer_validation(client):
    r = client.post('/sell-my-car/offer', data=with_csrf(
        client, '/sell-my-car/offer',
        {'vin': 'SHORT', 'mileage': '45000', 'condition': 'good'}))
    assert 'full VIN' in r.get_data(as_text=True)
    r = client.post('/sell-my-car/offer', data=with_csrf(
        client, '/sell-my-car/offer',
        {'vin': '1HGCM82633A004352', 'mileage': 'abc',
         'condition': 'good'}))
    assert 'mileage' in r.get_data(as_text=True).lower()


def test_profile_edit(alice):
    body = alice.get('/account/profile').get_data(as_text=True)
    assert 'Alice Johnson' in body
    assert '(206) 555-0142' in body
    r = alice.post('/account/profile', data=with_csrf(
        alice, '/account/profile',
        {'phone': '(206) 555-0999', 'street': '500 Pine St',
         'city': 'Seattle', 'state': 'wa', 'zip': '98101',
         'about': 'Updated for testing'}))
    assert r.status_code == 302
    body = alice.get('/account/profile').get_data(as_text=True)
    assert '(206) 555-0999' in body
    assert '500 Pine St' in body


def test_favorite_requires_login(client):
    r = client.post('/vehicle/4466702/favorite',
                    data=with_csrf(client, '/vehicle/4466702', {}))
    assert r.status_code == 302
    assert '/authn/login' in r.headers['Location']


def test_anonymous_save_login_next_completes(client):
    """The anonymous save flow must not dead-end: an anonymous 'Save this
    car' POST bounces to login with ?next=<favorite URL>, and logging in
    from there lands on the favorite URL with GET — which saves the car
    and returns to the vehicle page showing it saved (no 405)."""
    r = client.post('/vehicle/4466702/favorite',
                    data=with_csrf(client, '/vehicle/4466702', {}))
    assert r.status_code == 302
    loc = r.headers['Location']
    assert loc.startswith('/authn/login?next=')
    # log in from that URL exactly like the rendered form does
    r = client.post(loc, data=with_csrf(
        client, loc, {'email': 'carol.d@test.com',
                      'password': 'TestPass123!'}))
    assert r.status_code == 302
    # the redirect chain ends on the vehicle page, car saved, no 405
    follow = client.get(r.headers['Location'])
    while follow.status_code in (301, 302):
        follow = client.get(follow.headers['Location'])
    assert follow.status_code == 200, follow.status_code
    body = follow.get_data(as_text=True)
    assert 'Saved ♥' not in body
    client.post('/vehicle/4466702/favorite', data=with_csrf(client, '/vehicle/4466702', {}))
    favs = client.get('/account/favorites').get_data(as_text=True)
    assert 'Nissan Altima' in favs
    # GET is idempotent: hitting the favorite URL again never unsaves
    client.get('/vehicle/4466702/favorite')
    favs = client.get('/account/favorites').get_data(as_text=True)
    assert 'Nissan Altima' in favs
    with cv.app.app_context():
        pk = (cv.Vehicle.query.filter_by(vehicle_id=4466702)
              .with_entities(cv.Vehicle.id).scalar())
        dupes = (cv.Favorite.query.filter_by(user_id=3)
                 .filter_by(vehicle_id=pk).count())
    assert dupes == 1


def test_favorite_get_requires_login_too(client):
    """An anonymous GET of the favorite URL still bounces to login
    (the completion route is authenticated like the POST toggle)."""
    r = client.get('/vehicle/4466702/favorite')
    assert r.status_code == 302
    assert '/authn/login' in r.headers['Location']


def test_csrf_required_on_post(client):
    """A POST without the token is rejected — CSRF stays on everywhere."""
    r = client.post('/authn/login',
                    data={'email': 'alice.j@test.com',
                          'password': 'TestPass123!'})
    assert r.status_code == 400
