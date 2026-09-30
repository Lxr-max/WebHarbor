"""Flow tests: auth, wishlist management, the stay booking flow with the
captured price quote, cancellation, and the experience booking flow.
All POSTs submit real CSRF tokens (CSRF protection stays enabled)."""
import re

import app as ab
from conftest import with_csrf


def _login(client, email='alice.j@test.com'):
    r = client.post('/login', data=with_csrf(client, '/login', {
        'email': email, 'password': 'TestPass123!'}))
    assert r.status_code in (302, 303)


def _logout(client):
    client.get('/logout')


def test_login_logout(client):
    _login(client)
    body = client.get('/').get_data(as_text=True)
    assert 'Alice' in body
    _logout(client)
    body = client.get('/').get_data(as_text=True)
    assert 'Log in' in body


def test_bad_login(client):
    r = client.post('/login', data=with_csrf(client, '/login', {
        'email': 'alice.j@test.com', 'password': 'wrong'}))
    assert r.status_code == 200
    assert 'Invalid email or password' in r.get_data(as_text=True)


def test_signup_flow(client):
    r = client.post('/signup', data=with_csrf(client, '/signup', {
        'name': 'Test Runner', 'email': 'runner@test.com',
        'password': 'SuperSecret9!'}))
    assert r.status_code in (302, 303)
    body = client.get('/').get_data(as_text=True)
    assert 'Test' in body
    # the new account gets a default wishlist
    with ab.app.app_context():
        u = ab.User.query.filter_by(email='runner@test.com').first()
        assert u is not None
        assert ab.Wishlist.query.filter_by(user_id=u.id, is_default=True).count() == 1


def test_wishlist_save_and_remove(auth_client):
    with ab.app.app_context():
        lst = ab.Listing.query.filter_by(destination_slug='miami').first()
    r = auth_client.post('/wishlist/add', data=with_csrf(
        auth_client, f'/rooms/{lst.id}',
        {'listing_id': lst.id, 'back': f'/rooms/{lst.id}'}))
    assert r.status_code in (302, 303)
    body = auth_client.get('/wishlist').get_data(as_text=True)
    assert lst.name in body
    with ab.app.app_context():
        item = ab.WishlistItem.query.filter_by(listing_id=lst.id).first()
        assert item is not None
        r = auth_client.post(f"/wishlist/{item.id}/remove")
        assert r.status_code == 400  # no token
        token = with_csrf(auth_client, '/wishlist', {})['csrf_token']
        r = auth_client.post(f"/wishlist/{item.id}/remove",
                             data={'csrf_token': token})
        assert r.status_code in (302, 303)
        assert ab.WishlistItem.query.filter_by(listing_id=lst.id).count() == 0


def test_wishlist_create(auth_client):
    r = auth_client.post('/wishlist/create', data=with_csrf(
        auth_client, '/wishlist', {'name': 'Mountain escapes'}))
    assert r.status_code in (302, 303)
    body = auth_client.get('/wishlist').get_data(as_text=True)
    assert 'Mountain escapes' in body


def test_booking_requires_login(client):
    with ab.app.app_context():
        lst = ab.Listing.query.filter_by(destination_slug='asheville').first()
    r = client.get(f'/rooms/{lst.id}/book?checkin=2026-12-06'
                   f'&checkout=2026-12-11&adults=2')
    assert r.status_code == 200  # page renders
    r = client.post(f'/rooms/{lst.id}/book?checkin=2026-12-06'
                    f'&checkout=2026-12-11&adults=2',
                    data=with_csrf(client,
                                   f'/rooms/{lst.id}/book?checkin=2026-12-06&checkout=2026-12-11&adults=2',
                                   {'checkin': '2026-12-06',
                                    'checkout': '2026-12-11',
                                    'adults': '2'}))
    assert r.status_code in (302, 303)
    assert '/login' in r.headers.get('Location', '')


def test_book_stay_full_flow(auth_client):
    with ab.app.app_context():
        lst = ab.Listing.query.filter_by(destination_slug='asheville').first()
        n0 = ab.Booking.query.count()
    r = auth_client.get(f'/rooms/{lst.id}/book?checkin=2026-12-06'
                        f'&checkout=2026-12-11&adults=2')
    assert r.status_code == 200
    assert 'Confirm and pay' in r.get_data(as_text=True)
    r = auth_client.post(f'/rooms/{lst.id}/book?checkin=2026-12-06'
                         f'&checkout=2026-12-11&adults=2',
                         data=with_csrf(
                             auth_client,
                             f'/rooms/{lst.id}/book?checkin=2026-12-06&checkout=2026-12-11&adults=2',
                             {'checkin': '2026-12-06',
                              'checkout': '2026-12-11',
                              'adults': '2'}))
    assert r.status_code in (302, 303)
    code = r.headers['Location'].rsplit('/', 1)[-1]
    r = auth_client.get(f'/bookings/{code}')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Your trip is booked' in body
    assert code in body
    with ab.app.app_context():
        assert ab.Booking.query.count() == n0 + 1
        bk = ab.Booking.query.filter_by(code=code).first()
        assert bk.kind == 'stay'
        assert bk.nights == 5
        assert bk.total == round(lst.nightly_price * 5, 2)
    # trips page lists it
    body = auth_client.get('/trips').get_data(as_text=True)
    assert code in body


def test_cancel_trip(auth_client):
    with ab.app.app_context():
        bk = ab.Booking.query.filter_by(user_id=2).filter_by(
            status='confirmed').first()  # alice id may differ; use login below
        alice = ab.User.query.filter_by(email='alice.j@test.com').first()
        bk = ab.Booking.query.filter_by(user_id=alice.id,
                                        status='confirmed').first()
        code = bk.code
    r = auth_client.post(f'/trips/{code}/cancel', data=with_csrf(
        auth_client, '/trips', {}))
    assert r.status_code in (302, 303)
    with ab.app.app_context():
        bk = ab.Booking.query.filter_by(code=code).first()
        assert bk.status == 'cancelled'
    body = auth_client.get(f'/bookings/{code}').get_data(as_text=True)
    assert 'cancelled' in body.lower()


def test_book_experience_flow(auth_client):
    with ab.app.app_context():
        exp = ab.Experience.query.filter_by(city_slug='austin').first()
        n0 = ab.Booking.query.count()
    date = exp.offering_list()[0]['iso']
    r = auth_client.get(f'/experiences/{exp.id}/book?date={date}&guests=2')
    assert r.status_code == 200
    r = auth_client.post(f'/experiences/{exp.id}/book', data=with_csrf(
        auth_client, f'/experiences/{exp.id}/book',
        {'date': date, 'guests': '2'}))
    assert r.status_code in (302, 303)
    code = r.headers['Location'].rsplit('/', 1)[-1]
    with ab.app.app_context():
        bk = ab.Booking.query.filter_by(code=code).first()
        assert bk.kind == 'experience'
        assert bk.total == round(exp.price_per_guest * 2, 2)
    body = auth_client.get(f'/bookings/{code}').get_data(as_text=True)
    assert exp.name.replace("'", "&#39;") in body


def test_benchmark_fixture_states():
    """The four benchmark users carry their seeded states."""
    with ab.app.app_context():
        alice = ab.User.query.filter_by(email='alice.j@test.com').first()
        bob = ab.User.query.filter_by(email='bob.c@test.com').first()
        carol = ab.User.query.filter_by(email='carol.d@test.com').first()
        dana = ab.User.query.filter_by(email='dana.k@test.com').first()
        assert ab.Booking.query.filter_by(user_id=alice.id).count() >= 2
        assert ab.Booking.query.filter_by(user_id=alice.id,
                                          status='cancelled').count() >= 1
        assert ab.Booking.query.filter_by(user_id=bob.id,
                                          kind='experience').count() >= 1
        assert ab.Booking.query.filter_by(user_id=carol.id).count() >= 1
        assert ab.Booking.query.filter_by(user_id=dana.id).count() == 0
        assert ab.Wishlist.query.filter_by(user_id=dana.id).count() == 2
