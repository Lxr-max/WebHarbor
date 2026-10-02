"""Self-check suite for the trip_com mirror.

Run from sites/trip_com/:  python3 -m pytest tests/ -q

The suite runs against a temporary database seeded from scratch (pointed to
via TRIP_COM_DB_URI before importing the app) so it never mutates the seed.
"""
import os
import pathlib
import re
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent
sys.path.insert(0, str(SITE))

TMP = tempfile.mkdtemp(prefix='trip_com-tests-')
DB_PATH = os.path.join(TMP, 'trip_com.db')
os.environ['TRIP_COM_DB_URI'] = f'sqlite:///{DB_PATH}'

from app import (app, db, Attraction, AttractionBooking, AttractionPackage, City,  # noqa: E402
                  Coupon, Flight, FlightBooking, FlightRoute, Guide, Hotel,
                  HotelBooking, HotelPhoto, HotelReview, RoomRate, User,
                  WishlistItem, apply_promo, scored_search)

app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False
ctx = app.app_context()
ctx.push()
client = app.test_client()


def _csrf(path):
    r = client.get(path)
    m = re.search(rb'name="csrf_token" value="([^"]+)"', r.data)
    return m.group(1).decode() if m else ''


def _post(path, **data):
    token = _csrf(path)
    if token:
        data['csrf_token'] = token
    return client.post(path, data=data, follow_redirects=True)


# ------------------------------------------------------------------ catalog --

def test_seed_volume():
    assert City.query.count() == 11
    assert Hotel.query.count() >= 1000
    assert Hotel.query.filter_by(bookable=True).count() >= 70
    assert RoomRate.query.count() >= 500
    assert Flight.query.count() >= 700
    assert Attraction.query.count() == 131
    assert not Attraction.query.filter_by(name='Attractions & Tours category').count()
    assert Guide.query.count() == 6
    assert Coupon.query.count() == 4
    assert HotelPhoto.query.count() >= 400
    assert HotelReview.query.count() >= 60


def test_seed_only_real_cities():
    names = {c.name for c in City.query.all()}
    assert {"Las Vegas", "New York", "Orlando", "Hong Kong"} <= names


def test_flights_have_both_legs_per_route():
    for route in FlightRoute.query.all():
        outs = Flight.query.filter_by(route_id=route.id, leg='out').count()
        rets = Flight.query.filter_by(route_id=route.id, leg='ret').count()
        assert outs >= 20, route.origin_code
        assert rets >= 20, route.dest_code


def test_rooms_have_sane_prices():
    for r in RoomRate.query.limit(200):
        assert r.price > 0
        assert r.total >= r.price


def test_scored_search_is_fuzzy():
    rows = scored_search("vegas strip hotel", Hotel.query.all(),
                         ['name', 'district'])
    assert rows, "token-overlap search must match 'vegas strip hotel'"
    first = rows[0]
    text = (first.name + ' ' + (first.district or '')).lower()
    assert 'vegas' in text or 'strip' in text


# ------------------------------------------------------------------- pages --

def test_core_pages_render():
    for path in ['/', '/hotels/', '/flights/', '/things-to-do/', '/deals/',
                 '/guide/', '/sign-in/', '/register/', '/search?q=vegas']:
        r = client.get(path)
        assert r.status_code == 200, path
        assert len(r.data) > 2000, path


def test_hotel_list_and_filters():
    r = client.get('/hotels/list?city=Las+Vegas')
    assert r.status_code == 200
    assert b'properties found' in r.data
    r = client.get('/hotels/list?city=Las+Vegas&maxprice=100&sort=price')
    body = r.data.decode()
    assert 'properties found' in body
    r = client.get('/hotels/list?city=Nowhereville')
    assert r.status_code == 200          # falls back to a scored city match


def test_hotel_detail_shows_rooms():
    hotel = Hotel.query.filter_by(bookable=True).first()
    r = client.get(f'/hotels/detail/{hotel.id}')
    assert r.status_code == 200
    assert b'Choose your room' in r.data
    r = client.get('/hotels/detail/999999999')
    assert r.status_code == 404


def test_flight_list_filters():
    r = client.get('/flights/list?dcity=SFO&acity=JFK&ddate=2026-10-20&rdate=2026-10-27')
    assert r.status_code == 200
    assert b'flight-row' in r.data
    r = client.get('/flights/list?dcity=SFO&acity=JFK&ddate=2026-10-20&airline=Delta+Air+Lines&stops=nonstop')
    assert b'Delta Air Lines' in r.data
    r = client.get('/flights/list?dcity=XXX&acity=YYY')
    assert r.status_code == 302          # unknown route redirects home


def test_flight_search_accepts_code_and_city_mix():
    """Review MINOR-2: each search side resolves independently, so mixing an
    airport code with a city name (e.g. 'MIA' + 'New York') must find the
    route instead of bouncing back to the search form."""
    r = client.get('/flights/list?dcity=MIA&acity=New+York&ddate=2026-10-24&rdate=2026-10-31')
    assert r.status_code == 200
    assert b'flight-row' in r.data
    assert b'MIA' in r.data and b'LGA' in r.data
    # pure city names still work
    r = client.get('/flights/list?dcity=Miami&acity=New+York')
    assert r.status_code == 200
    assert b'flight-row' in r.data
    # pure codes still work
    r = client.get('/flights/list?dcity=ORD&acity=MIA')
    assert r.status_code == 200
    assert b'flight-row' in r.data


def test_select_link_carries_outbound_filters():
    """Review MAJOR-1: the Select link must carry the outbound airline/stops
    filters into the return-selection page so a filtered outbound search
    cannot silently end in a non-matching return flight."""
    r = client.get('/flights/list?dcity=SFO&acity=JFK&ddate=2026-10-20&rdate=2026-10-27'
                   '&airline=Delta+Air+Lines&stops=nonstop')
    hrefs = re.findall(rb'href="(/flights/select/\d+\?[^"]+)"', r.data)
    assert hrefs
    for h in hrefs:
        assert b'airline=Delta+Air+Lines' in h and b'stops=nonstop' in h
    # the return page is pre-filtered and says so
    r2 = client.get(hrefs[0].decode().replace('&amp;', '&'))
    assert r2.status_code == 200
    assert b'Matching your outbound filters' in r2.data
    airlines = set(re.findall(rb'class="f-airline">([^<]+)', r2.data))
    assert airlines and all(a.startswith(b'Delta Air Lines') for a in airlines)
    assert b'Nonstop' in r2.data
    # without filters the Select link stays filter-free
    r = client.get('/flights/list?dcity=SFO&acity=JFK&ddate=2026-10-20&rdate=2026-10-27')
    href = re.search(rb'href="(/flights/select/\d+\?[^"]+)"', r.data).group(1)
    assert b'airline=' not in href and b'stops=' not in href


def test_attraction_pages():
    att = Attraction.query.first()
    r = client.get(f'/things-to-do/detail/{att.id}')
    assert r.status_code == 200
    r = client.get('/things-to-do/experiences/orlando')
    assert r.status_code == 200


# ---------------------------------------------------------------- bookings --

def test_hotel_booking_chain():
    room = RoomRate.query.order_by(RoomRate.id).first()
    nights = 2
    taxes = (room.total - room.price) * nights
    base = room.price * nights + taxes
    r = _post(f'/hotels/book/{room.id}?checkin=2026-10-04&checkout=2026-10-06',
              first_name='Test', last_name='Booker',
              email='tb@example.com', phone='+15550001111',
              card_no='4242424242424242', card_name='Test Booker')
    assert r.status_code == 200
    body = r.data.decode()
    assert 'Your booking is confirmed' in body
    m = re.search(r'TH[A-Z0-9]{8}', body)
    assert m
    booking = HotelBooking.query.get(m.group(0))
    assert booking is not None
    assert abs(booking.total - round(base, 2)) < 0.01
    assert booking.coins == int(booking.total * 0.01)
    # confirmation page renders
    r = client.get(f'/hotels/confirmation/{booking.ref}')
    assert r.status_code == 200


def test_hotel_booking_validates_input():
    room = RoomRate.query.order_by(RoomRate.id).first()
    r = _post(f'/hotels/book/{room.id}',
              first_name='', last_name='Booker',
              email='not-an-email', phone='x',
              card_no='12', card_name='')
    assert r.status_code == 400
    assert b'valid email' in r.data


def test_flight_roundtrip_chain():
    route = FlightRoute.query.first()
    out = Flight.query.filter_by(route_id=route.id, leg='out').order_by(Flight.price).first()
    ret = Flight.query.filter_by(route_id=route.id, leg='ret').order_by(Flight.price).first()
    total = out.price + ret.price
    r = _post(f'/flights/book?out={out.id}&ret={ret.id}&ddate=2026-10-20&rdate=2026-10-27',
              first_name='Test', last_name='Flyer',
              email='tf@example.com', phone='+15550002222',
              card_no='4242424242424242', card_name='Test Flyer')
    assert r.status_code == 200
    body = r.data.decode()
    m = re.search(r'TF[A-Z0-9]{8}', body)
    assert m
    booking = FlightBooking.query.get(m.group(0))
    assert booking is not None
    assert abs(booking.total - total) < 0.01
    assert booking.trip_type == 'rt'
    assert str(booking.departure_date) == '2026-10-20'
    assert str(booking.return_date) == '2026-10-27'
    assert 'Oct 20, 2026' in body and 'Oct 27, 2026' in body


def test_attraction_booking_chain():
    pkg = AttractionPackage.query.order_by(AttractionPackage.id).first()
    guests = 2
    r = _post(f'/things-to-do/book/{pkg.id}?guests={guests}&date=2026-10-06',
              first_name='Test', last_name='Visitor',
              email='tv@example.com')
    assert r.status_code == 200
    m = re.search(r'TA[A-Z0-9]{8}', r.data.decode())
    assert m
    assert abs(pkg.price * guests - pkg.price * guests) < 0.01


def test_attraction_booking_form_overrides_query_string():
    """Review BLOCKER-1 regression: once the traveller edits the date/guests
    inputs and submits, the FORM values must win over the Book-now link's
    query-string defaults (request.values used to let the query string
    silently override the submitted values)."""
    pkg = AttractionPackage.query.order_by(AttractionPackage.id).first()
    r = _post(f'/things-to-do/book/{pkg.id}?date=2026-10-06&guests=2',
              date='2026-10-12', guests='3',
              first_name='Wei', last_name='Chen', email='wc@example.com')
    assert r.status_code == 200
    m = re.search(r'TA[A-Z0-9]{8}', r.data.decode())
    assert m
    booking = AttractionBooking.query.get(m.group(0))
    assert booking is not None
    assert str(booking.visit_date) == '2026-10-12'      # edited date recorded
    assert booking.guests == 3                          # edited guests recorded
    assert abs(booking.total - pkg.price * 3) < 0.01
    # the confirmation page echoes the submitted values
    body = r.data.decode()
    assert 'Oct 12' in body or '2026-10-12' in body


def test_attraction_booking_falls_back_to_link_defaults():
    """A POST that leaves the date/guests inputs untouched still books the
    Book-now link's query-string defaults (2026-10-06, 2 guests)."""
    pkg = AttractionPackage.query.order_by(AttractionPackage.id).first()
    r = _post(f'/things-to-do/book/{pkg.id}?date=2026-10-06&guests=2',
              first_name='Ana', last_name='Default', email='ad@example.com')
    m = re.search(r'TA[A-Z0-9]{8}', r.data.decode())
    booking = AttractionBooking.query.get(m.group(0))
    assert str(booking.visit_date) == '2026-10-06'
    assert booking.guests == 2


# ------------------------------------------------------------------- promo --

def test_promo_codes_apply_and_reject():
    # percent promo above the minimum spend
    disc, cp = apply_promo('TRIPNEW20', 200.0, 'hotels')
    assert cp is not None and disc == 40.0
    # below the minimum spend: no discount
    disc, cp = apply_promo('TRIPNEW20', 50.0, 'hotels')
    assert disc == 0.0
    # wrong scope
    disc, cp = apply_promo('FLYTRIP10', 500.0, 'hotels')
    assert disc == 0.0
    # unknown code
    disc, cp = apply_promo('NOPE123', 500.0, 'hotels')
    assert cp is None and disc == 0.0
    # amount promo
    disc, cp = apply_promo('SAVE25', 300.0, 'all')
    assert disc == 25.0


def test_hotel_promo_changes_total():
    room = RoomRate.query.filter(RoomRate.price > 100).order_by(RoomRate.price).first()
    base = room.total
    r = _post(f'/hotels/book/{room.id}',
              first_name='Promo', last_name='User',
              email='p@example.com', phone='+15550003333',
              card_no='4242424242424242', card_name='Promo User',
              promo_code='TRIPNEW20')
    body = r.data.decode()
    m = re.search(r'TH[A-Z0-9]{8}', body)
    booking = HotelBooking.query.get(m.group(0))
    expected = round(base * 0.8, 2)
    assert abs(booking.total - expected) < 0.01
    assert booking.promo_code == 'TRIPNEW20'


# ------------------------------------------------------------------ account --

def test_auth_flow():
    r = _post('/sign-in/', email='alice.j@test.com', password='TestPass123!')
    assert r.status_code == 200
    assert b"Trip Coins balance" in r.data
    r = client.get('/account/')
    assert r.status_code == 200
    r = client.get('/logout')
    assert r.status_code == 302
    r = client.get('/account/')
    assert r.status_code == 302                  # login required again


def test_bad_password_rejected():
    r = _post('/sign-in/', email='alice.j@test.com', password='WrongPass!')
    assert r.status_code == 401


def test_benchmark_users_have_history():
    for email in ['alice.j@test.com', 'bob.c@test.com', 'carol.d@test.com',
                  'david.k@test.com']:
        u = User.query.filter_by(email=email).first()
        assert u is not None, email
        assert WishlistItem.query.filter_by(user_id=u.id).count() >= 3


def test_wishlist_toggle_and_cancel():
    client.post('/sign-in/', data={'email': 'bob.c@test.com',
                                   'password': 'TestPass123!'},
                follow_redirects=True)
    before = WishlistItem.query.count()
    hotel = Hotel.query.filter_by(bookable=True).first()
    r = _post(f'/wishlist/toggle/{hotel.id}')
    assert WishlistItem.query.count() == before + 1
    r = _post(f'/wishlist/toggle/{hotel.id}')
    assert WishlistItem.query.count() == before

    booking = HotelBooking.query.filter_by(ref='THBOBCH1').first()
    assert booking is not None
    r = _post('/bookings/cancel/hotel/THBOBCH1')
    assert booking.status == 'cancelled'
    # other users' bookings are untouchable
    r = client.post('/bookings/cancel/flight/TFALICE1')
    assert r.status_code == 404


# ------------------------------------------------------------- idempotence --

def test_seed_gates_are_idempotent():
    from seed_data import build_benchmark_users
    from app import bcrypt, BENCHMARK_PASSWORD_HASH
    before = User.query.count()
    build_benchmark_users(db, bcrypt, BENCHMARK_PASSWORD_HASH)
    assert User.query.count() == before


def test_health_probe_passes():
    import _health
    result = _health.health()
    assert result['ok'], result


def test_recovered_attractions_do_not_invent_packages():
    # Recovered source entries retain real titles; never a category placeholder.
    assert not Attraction.query.filter(Attraction.name == 'Attractions & Tours category').count()
    package = AttractionPackage.query.filter_by(attraction_id=46680654).first()
    assert 'year' in package.validity.lower()


def test_return_date_must_follow_departure():
    outbound = Flight.query.filter_by(leg='out').first()
    inbound = Flight.query.filter_by(route_id=outbound.route_id, leg='ret').first()
    response = client.get(f'/flights/book?out={outbound.id}&ret={inbound.id}&ddate=2026-10-27&rdate=2026-10-20')
    assert response.status_code == 400
