"""Flow tests: auth, wishlist, booking, cancellation, Q&A, reviews."""
import re

import pytest

from app import app, Booking, Tour, TourQA, User, WishlistItem, db


@pytest.fixture(autouse=True)
def _ctx():
    with app.app_context():
        yield


def _login(client, email='alice.j@test.com', password='TestPass123!'):
    resp = client.post('/login', data={'email': email, 'password': password},
                       follow_redirects=True)
    assert resp.status_code == 200
    return resp


def test_login_logout(client):
    resp = _login(client)
    assert b'Alice Johnson' in resp.data
    resp = client.get('/account')
    assert resp.status_code == 200
    assert b'Tour Management' in resp.data
    resp = client.get('/logout', follow_redirects=True)
    assert b'logged out' in resp.data


def test_login_wrong_password(client):
    resp = client.post('/login', data={'email': 'alice.j@test.com',
                                       'password': 'wrong'},
                       follow_redirects=True)
    assert b'Incorrect email or password' in resp.data


def test_signup_flow(client):
    resp = client.post('/signup', data={
        'email': 'new@example.com', 'password': 'Passw0rd!',
        'display_name': 'New Traveler'}, follow_redirects=True)
    assert b'Welcome to TourRadar' in resp.data
    with db.session.no_autoflush:
        assert User.query.filter_by(email='new@example.com').first()


def test_wishlist_toggle(auth_client):
    with db.session.no_autoflush:
        tour = Tour.query.filter(
            ~Tour.id.in_([w.tour_id for w in
                          WishlistItem.query.filter_by(user_id=1)])).first()
    resp = auth_client.post(f'/wishlist/toggle/{tour.id}',
                            follow_redirects=True)
    assert b'Saved' in resp.data
    with db.session.no_autoflush:
        assert WishlistItem.query.filter_by(user_id=1,
                                            tour_id=tour.id).first()
    resp = auth_client.post(f'/wishlist/toggle/{tour.id}',
                             follow_redirects=True)
    assert b'Removed' in resp.data
    with db.session.no_autoflush:
        assert not WishlistItem.query.filter_by(user_id=1,
                                                tour_id=tour.id).first()


def _booking_payload(tour_id, date, email='guest@example.com'):
    return {
        'action': 'book', 'date': date, 'travelers': '2',
        'room_type': 'double', 'insurance': 'none', 'promo_code': '',
        'payment_schedule': 'deposit',
        'title_0': 'Mr.', 'first_0': 'John', 'last_0': 'Smith',
        'dob_0': '1990-05-10', 'gender_0': 'Male', 'nationality_0': 'USA',
        'title_1': 'Ms.', 'first_1': 'Jane', 'last_1': 'Smith',
        'dob_1': '1992-02-02', 'gender_1': 'Female', 'nationality_1': 'USA',
        'email': email, 'phone': '+1 555 0100',
        'card_name': 'John Smith', 'card_number': '4242 4242 4242 4242',
        'expiry': '09/29', 'cvv': '123', 'billing_country': 'USA',
        'zip': '12345', 'accept_terms': '1',
    }


def test_booking_full_chain(client):
    with db.session.no_autoflush:
        tour = Tour.query.get(255)
        dep = tour.next_departure
    payload = _booking_payload(255, dep.start_date)
    resp = client.post('/book-now/255', data=payload,
                       follow_redirects=False)
    assert resp.status_code == 302
    ref = resp.headers['Location'].rsplit('/', 1)[-1]
    with db.session.no_autoflush:
        booking = Booking.query.filter_by(ref=ref).first()
        assert booking is not None
        assert booking.status == 'confirmed'
        assert booking.tour_id == 255
        assert booking.room_type == 'Double Room'
        assert len(booking.travelers_list) == 2
        expected = round(dep.price * 2, 2)
        assert abs(booking.total - expected) < 0.01
        assert abs(booking.due_today - round(expected * 0.10, 2)) < 0.01
    html = client.get(f'/booking/{ref}').get_data(as_text=True)
    assert 'Booking Confirmed' in html
    assert ref in html


def test_booking_validation_rejects_bad_card(client):
    with db.session.no_autoflush:
        dep = Tour.query.get(255).next_departure
    payload = _booking_payload(255, dep.start_date, email='badcard@example.com')
    payload['card_number'] = '12'
    resp = client.post('/book-now/255', data=payload)
    assert resp.status_code == 400
    assert b'valid card number' in resp.data
    with db.session.no_autoflush:
        assert not Booking.query.filter_by(lead_email='badcard@example.com').all()


def test_booking_promo_code(client):
    with db.session.no_autoflush:
        tour = Tour.query.get(255)
        dep = tour.next_departure
    payload = _booking_payload(255, dep.start_date, email='promo@example.com')
    payload['promo_code'] = 'TRAVEL50'
    resp = client.post('/book-now/255', data=payload,
                       follow_redirects=False)
    assert resp.status_code == 302
    ref = resp.headers['Location'].rsplit('/', 1)[-1]
    with db.session.no_autoflush:
        booking = Booking.query.filter_by(ref=ref).first()
        expected = round(dep.price * 2 - 50, 2)
        assert abs(booking.total - expected) < 0.01


def test_booking_bad_promo_rejected(client):
    with db.session.no_autoflush:
        dep = Tour.query.get(255).next_departure
    payload = _booking_payload(255, dep.start_date, email='badpromo@example.com')
    payload['promo_code'] = 'NOT_A_CODE'
    resp = client.post('/book-now/255', data=payload)
    assert resp.status_code == 400
    assert b'not valid' in resp.data


def test_booking_cancellation(auth_client):
    with db.session.no_autoflush:
        booking = Booking.query.filter_by(user_id=1, status='confirmed').first()
        assert booking is not None, 'alice must have a confirmed booking'
    resp = auth_client.post(f'/booking/{booking.ref}/cancel',
                            follow_redirects=True)
    assert b'cancelled' in resp.data
    with db.session.no_autoflush:
        assert Booking.query.filter_by(ref=booking.ref).first().status == 'cancelled'


def test_ask_question(client):
    before = 0
    with db.session.no_autoflush:
        before = TourQA.query.filter_by(tour_id=255).count()
    resp = client.post('/t/255/ask', data={
        'question': 'Is airport pickup included on arrival day?',
        'asker': 'Curious Traveler'}, follow_redirects=True)
    assert b'sent to the operator' in resp.data
    with db.session.no_autoflush:
        assert TourQA.query.filter_by(tour_id=255).count() == before + 1


def test_ask_requires_real_question(client):
    resp = client.post('/t/255/ask', data={'question': 'hi'},
                       follow_redirects=True)
    assert b'at least 10 characters' in resp.data


def test_review_writing_requires_completed_booking(auth_client):
    with db.session.no_autoflush:
        completed = Booking.query.filter_by(user_id=1,
                                            status='completed').first()
        assert completed, 'alice must have a completed booking'
    resp = auth_client.post(f'/t/{completed.tour_id}/review', data={
        'rating': '5', 'title': 'Trip of a lifetime',
        'body': 'The guide made every day special and the group was fun.'},
        follow_redirects=True)
    assert b'published' in resp.data


def test_profile_update(auth_client):
    resp = auth_client.post('/account/profile', data={
        'display_name': 'Alice Johnson', 'phone': '+1 555 0199',
        'nationality': 'USA'}, follow_redirects=True)
    assert b'Profile updated' in resp.data
    with db.session.no_autoflush:
        assert User.query.get(1).phone == '+1 555 0199'
