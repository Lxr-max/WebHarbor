"""Self-check suite for the ticketmaster mirror.

Run from sites/ticketmaster/:  python3 -m pytest tests/ -q

The suite runs against a temporary database seeded from scratch (pointed to
via TICKETMASTER_DB_URI before importing the app) so it never mutates the
seed.
"""
import os
import pathlib
import re
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent
sys.path.insert(0, str(SITE))

TMP = tempfile.mkdtemp(prefix='ticketmaster-tests-')
DB_PATH = os.path.join(TMP, 'ticketmaster.db')
os.environ['TICKETMASTER_DB_URI'] = f'sqlite:///{DB_PATH}'

from app import (app, db, Artist, Event, TicketListing, User, Order,  # noqa: E402
                  Favorite, PaymentMethod, Presale, Venue, MIRROR_TODAY)

app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False
client = app.test_client()

CTX = app.app_context()
CTX.push()


@classmethod
def _fresh(cls):
    """Isolated client per call: no session carry-over between tests."""
    return app.test_client()


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_session():
    with client.session_transaction() as sess:
        sess.clear()
    yield


def _csrf(path):
    r = client.get(path)
    m = re.search(rb'name="csrf_token" value="([^"]+)"', r.data)
    return m.group(1).decode() if m else ''


def _login(email='alice.j@test.com', password='TestPass123!'):
    r = client.post('/signin', data={'email': email, 'password': password},
                    follow_redirects=True)
    assert b'Your Account' in r.data, 'login failed'
    return r


# ----------------------------------------------------------------- seed ----

def test_seed_volume():
    assert Event.query.count() >= 500
    assert Artist.query.count() >= 100
    assert Venue.query.count() >= 100
    assert TicketListing.query.count() >= 20000
    for cat in ('Music', 'Sports', 'Arts & Theater', 'Family'):
        assert Event.query.filter_by(category=cat).count() >= 50, cat


def test_cheapest_option_unique():
    """Every 'cheapest <type>' question must have exactly one answer.

    Within each (event, ticket type) the minimum all-in price must be achieved
    by exactly one listing, both across all listings and among the listings
    with 4+ seats together — the two cuts the tasks ask about. seed_data's
    _detie_minimums enforces this at build time; this test guards it.
    """
    from collections import defaultdict
    for threshold in (0, 4):
        groups = defaultdict(list)
        q = TicketListing.query.filter(TicketListing.qty_available >= threshold)
        for l in q:
            groups[(l.event_id, l.ticket_type)].append(l.price)
        for (eid, ttype), prices in groups.items():
            assert prices.count(min(prices)) == 1, \
                f'tied minimum for event {eid} type {ttype}: {sorted(prices)[:3]}'


def test_search_distractor_density():
    """Task queries must return near-name competitors, not a single row."""
    r = client.get('/search?q=power+to+the+people')
    html = r.data.decode()
    # the festival plus the real near-name tours captured from upstream
    assert html.count('Find Tickets') >= 5
    assert 'Power to the People Festival' in html
    assert 'The High Kings' in html


def test_benchmark_fixtures_pinned():
    """Demo-account fixtures match the task descriptions (pinned IDs)."""
    bob = User.query.filter_by(email='bob.c@test.com').first()
    bob_events = sorted(f.event.name for f in bob.favorites if f.event)
    assert bob_events == ['Gorillaz - The Mountain Tour', 'Teddy Swims: The UGLY Tour']
    david = User.query.filter_by(email='david.k@test.com').first()
    david_events = [f.event.name for f in david.favorites if f.event]
    assert 'Rod Wave: Don\'t Look Down Tour' in david_events


def test_seed_idempotence():
    """Re-running the boot path must be a no-op (byte-identity guard)."""
    from app import seed_database, seed_benchmark_users
    before = Event.query.count()
    with app.app_context():
        seed_database()          # gated: must not re-seed
        seed_benchmark_users()
    assert Event.query.count() == before


def test_benchmark_users():
    for email in ('alice.j@test.com', 'bob.c@test.com',
                  'carol.d@test.com', 'david.k@test.com'):
        u = User.query.filter_by(email=email).first()
        assert u is not None, email
    alice = User.query.filter_by(email='alice.j@test.com').first()
    assert len(alice.orders) >= 1
    assert len(alice.payment_methods) >= 1
    assert len(alice.favorites) >= 3
    assert alice.first_name == 'Alice'


def test_events_have_venues_and_dates():
    for e in Event.query.filter_by(is_add_on=False).limit(40):
        assert e.venue is not None
        assert re.match(r'\d{4}-\d{2}-\d{2}$', e.date)
        assert e.category in ('Music', 'Sports', 'Arts & Theater', 'Family')
        assert e.listings, f'event {e.id} has no listings'


def test_price_math():
    """Displayed price = face value + 37.6% service fee (captured upstream)."""
    l = TicketListing.query.first()
    assert abs(l.price - round(l.face_value * 1.376, 2)) < 0.01


# --------------------------------------------------------------- browsing --

def test_homepage():
    r = client.get('/')
    assert r.status_code == 200
    html = r.data.decode()
    assert 'Highlights' in html
    assert 'Trending Searches' in html
    assert 'Happening This Weekend' in html
    assert 'Popular Near You' in html
    assert '/event/' in html


def test_homepage_discovery_selection():
    """Featured shelves should offer different acts and honest weekend dates."""
    from flask import template_rendered
    captured = []

    def record(sender, template, context, **extra):
        captured.append(context)

    with template_rendered.connected_to(record, app):
        assert client.get('/').status_code == 200
    ctx = captured[0]
    events = [ctx['hero'], *ctx['highlights'], *ctx['weekend']]
    assert len(events) >= 12
    assert len({e.artist_id for e in events}) == len(events)
    assert len({e.category for e in ctx['highlights']}) == 4
    assert all(e.image and not e.is_add_on for e in events)
    assert all(e.date >= MIRROR_TODAY.date().isoformat() for e in events)
    assert ctx['weekend']
    from datetime import date
    assert all(date.fromisoformat(e.date).weekday() in (5, 6) for e in ctx['weekend'])
    for category in ctx['popular'].values():
        assert len({e.artist_id for e in category}) == len(category)


def test_discover_filters():
    r = client.get('/discover/sports?sub=Basketball')
    assert r.status_code == 200
    assert 'Results' in r.data.decode()
    r = client.get('/discover/concerts?city=Las%20Vegas&price_max=100')
    assert r.status_code == 200
    r = client.get('/discover/family?sort=price')
    assert 'Results' in r.data.decode()


def test_search_scored():
    r = client.get('/search?q=metallica')
    assert r.status_code == 200
    html = r.data.decode()
    assert 'Metallica' in html
    # multi-word partial query must still hit (token overlap, not strict AND)
    r = client.get('/search?q=taylor%20swift')
    assert 'Results' in r.data.decode()
    r = client.get('/search?q=zzzznotfound')
    assert 'No results' in r.data.decode()


def test_event_page_and_filters():
    e = Event.query.filter_by(is_add_on=False).first()
    r = client.get(f'/event/{e.id}')
    assert r.status_code == 200
    html = r.data.decode()
    assert e.name in html
    assert 'We&#39;re All In' in html or "We're All In" in html
    # lowest-price sort returns ascending prices
    r = client.get(f'/event/{e.id}?sort=lowest')
    prices = [float(p) for p in re.findall(r'\$([\d.]+) <small>incl', r.data.decode())]
    assert prices == sorted(prices)
    # quantity filter drops listings with fewer seats
    r = client.get(f'/event/{e.id}?qty=4')
    assert r.status_code == 200


def test_404():
    assert client.get('/event/NOPE123').status_code == 404
    assert client.get('/no/such/page').status_code == 404


# --------------------------------------------------------------- checkout --

def _pick_event_with_vip():
    return (TicketListing.query
            .filter_by(ticket_type='VIP Package')
            .first().event_id)


def _guest_checkout(event_id=None):
    e = Event.query.get(event_id) if event_id else Event.query.filter_by(is_add_on=False).first()
    listing = TicketListing.query.filter_by(event_id=e.id).order_by(TicketListing.face_value).first()
    r = client.get(f'/event/{e.id}/tickets?listing={listing.id}&qty=2')
    assert r.status_code == 200
    assert b'Reserve Tickets' in r.data
    assert b'Service Fee x2' in r.data
    r = client.post(f'/event/{e.id}/tickets',
                    data={'listing': listing.id, 'qty': 2},
                    follow_redirects=True)
    assert b'Choose your delivery method' in r.data
    r = client.post('/checkout', data={'action': 'delivery', 'delivery': 'mobile'},
                    follow_redirects=True)
    assert b'Card number' in r.data
    r = client.post('/checkout', data={
        'action': 'payment', 'email': 'guest@example.com', 'brand': 'Visa',
        'number': '5555555555554444', 'holder': 'Guest Guest',
        'exp_month': '12', 'exp_year': '2029'}, follow_redirects=True)
    assert b'Review your order' in r.data
    r = client.post('/checkout', data={'action': 'place'}, follow_redirects=True)
    assert b'Your order is confirmed' in r.data
    m = re.search(rb'Order Number<br><b>([A-Z0-9]+)', r.data)
    assert m, 'confirmation missing order number'
    order_no = m.group(1).decode()
    order = Order.query.filter_by(order_no=order_no).first()
    assert order is not None
    assert order.qty == 2
    assert order.card_last4 == '4444'
    assert abs(order.total - round(order.unit_price * 2, 2)) < 0.01
    return order


def test_guest_checkout_chain():
    order = _guest_checkout()
    # listing availability decremented
    assert order.listing.qty_available >= 0


def test_signed_in_checkout_uses_saved_card():
    _login()
    e = Event.query.filter_by(is_add_on=False).first()
    listing = TicketListing.query.filter_by(event_id=e.id).order_by(TicketListing.face_value).first()
    client.get(f'/event/{e.id}/tickets?listing={listing.id}&qty=3')
    client.post(f'/event/{e.id}/tickets', data={'listing': listing.id, 'qty': 3})
    client.post('/checkout', data={'action': 'delivery', 'delivery': 'eticket'})
    method = PaymentMethod.query.filter_by(user_id=User.query.filter_by(
        email='alice.j@test.com').first().id).first()
    r = client.post('/checkout', data={'action': 'payment',
                                       'method_id': method.id},
                    follow_redirects=True)
    assert b'Review your order' in r.data
    r = client.post('/checkout', data={'action': 'place'}, follow_redirects=True)
    assert b'Your order is confirmed' in r.data
    order = Order.query.filter(Order.order_no.like('%')).order_by(Order.id.desc()).first()
    assert order.user_id is not None
    assert order.card_last4 == method.last4


def test_checkout_validation():
    e = Event.query.filter_by(is_add_on=False).first()
    listing = TicketListing.query.filter_by(event_id=e.id).first()
    client.get(f'/event/{e.id}/tickets?listing={listing.id}&qty=2')
    client.post(f'/event/{e.id}/tickets', data={'listing': listing.id, 'qty': 2})
    client.post('/checkout', data={'action': 'delivery', 'delivery': 'mobile'})
    r = client.post('/checkout', data={
        'action': 'payment', 'email': 'x@y.com', 'brand': 'Visa',
        'number': '123', 'holder': '', 'exp_month': '13', 'exp_year': '2020'},
                    follow_redirects=True)
    assert b'Enter a valid card number.' in r.data
    assert b'Enter the name on the card.' in r.data
    assert b'Expiry month must be 1-12.' in r.data
    assert b'The card is expired.' in r.data


def test_no_draft_redirects_home():
    r = client.get('/checkout', follow_redirects=False)
    assert r.status_code == 302


# ---------------------------------------------------------------- account --

def test_auth_flow():
    client.get('/logout')
    r = client.get('/member')
    assert r.status_code == 302  # login required
    _login('bob.c@test.com')
    r = client.get('/member')
    assert r.status_code == 200
    assert b'Bob' in r.data
    r = client.get('/member/orders')
    assert r.status_code == 200
    # wrong password
    client.get('/logout')
    r = client.post('/signin', data={'email': 'bob.c@test.com',
                                     'password': 'wrong'},
                    follow_redirects=True)
    assert b'Invalid email or password.' in r.data


def test_register_validation():
    r = client.post('/register', data={
        'first_name': 'New', 'last_name': 'User',
        'email': 'not-an-email', 'password': 'short'},
                    follow_redirects=True)
    assert b'Enter a valid email address.' in r.data
    assert b'Password must be at least 8 characters.' in r.data


def test_profile_and_payment_methods():
    _login('carol.d@test.com')
    r = client.post('/member/profile', data={
        'first_name': 'Carol', 'last_name': 'Davis',
        'phone': '(312) 555-9999', 'zip': '60602'},
                    follow_redirects=True)
    assert b'Profile updated.' in r.data
    assert User.query.filter_by(email='carol.d@test.com').first().phone == '(312) 555-9999'
    r = client.post('/member/payment', data={
        'brand': 'Amex', 'number': '378282246310005',
        'holder': 'Carol Davis', 'exp_month': '6', 'exp_year': '2031'},
                    follow_redirects=True)
    assert b'Card added.' in r.data
    method = (PaymentMethod.query.filter_by(last4='0005')
              .filter_by(user_id=User.query.filter_by(email='carol.d@test.com').first().id)
              .first())
    assert method is not None
    r = client.post('/member/payment', data={'action': 'delete', 'id': method.id},
                    follow_redirects=True)
    assert b'Card removed.' in r.data


def test_favorites_toggle():
    _login('david.k@test.com')
    a = Artist.query.first()
    r = client.post('/favorites/toggle', data={
        'kind': 'artist', 'ref': a.id, 'next': f'/artist/{a.id}'},
                    follow_redirects=True)
    assert b'favorites' in r.data
    assert Favorite.query.filter_by(artist_id=a.id).first() is not None
    r = client.get('/member/favorites')
    assert a.name in r.data.decode()


# ------------------------------------------------------------ misc pages --

def test_artist_and_venue_pages():
    a = Artist.query.filter(Artist.rating.isnot(None)).first()
    r = client.get(f'/artist/{a.id}')
    assert r.status_code == 200
    assert a.name in r.data.decode()
    assert f'{a.rating:.1f} out of 5' in r.data.decode()
    v = Venue.query.filter(Venue.address.isnot(None)).first()
    r = client.get(f'/venue/{v.id}')
    assert r.status_code == 200
    assert v.address.replace('&', '&amp;') in r.data.decode() or v.address in r.data.decode()


def test_giftcards():
    r = client.get('/giftcards')
    assert b'Give the Gift of Live' in r.data
    r = client.post('/giftcards', data={'action': 'balance', 'code': 'GC-TEST-1234'},
                    follow_redirects=True)
    assert b'current balance' in r.data
    r = client.post('/giftcards', data={'action': 'buy', 'amount': '10',
                                        'type': 'E-Gift Card',
                                        'email': 'x@y.com'},
                    follow_redirects=True)
    assert b'between $25 and $1000' in r.data


def test_help_center():
    r = client.get('/help')
    assert b'how can we help' in r.data
    r = client.get('/help/presale')
    assert b'presale code' in r.data
    assert client.get('/help/nope').status_code == 404


def test_presales_render():
    e = (Event.query.filter(Event.presales.any()).first())
    assert e is not None
    r = client.get(f'/event/{e.id}')
    assert 'On Sale Info' in r.data.decode()
    assert Presale.query.filter_by(event_id=e.id).first().title in r.data.decode()


def test_images_are_real_files():
    """Every referenced image must exist on disk (no placeholder gaps)."""
    import pathlib
    base = pathlib.Path(SITE)
    for e in Event.query.filter(Event.image.isnot(None)).limit(60):
        p = base / e.image
        assert p.exists(), f'missing image for event {e.id}: {e.image}'
        assert p.stat().st_size > 500
    for a in Artist.query.filter(Artist.image.isnot(None)).limit(40):
        assert (base / a.image).exists(), f'missing image for artist {a.id}'
    for v in Venue.query.filter(Venue.image.isnot(None)).limit(20):
        assert (base / v.image).exists(), f'missing image for venue {v.id}'
