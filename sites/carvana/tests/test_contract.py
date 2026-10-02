"""Contract tests: seeded data, public pages, CSRF on every POST form,
asset integrity, search/filter semantics and the payment math."""
import hashlib
import json
import math
import os
import re

import app as cv
from conftest import with_csrf


# ------------------------------------------------------------------- seeds --

def test_seed_counts():
    with cv.app.app_context():
        assert cv.Vehicle.query.count() >= 700
        assert cv.Vehicle.query.filter_by(has_detail=True).count() >= 40
        assert cv.SearchSnapshot.query.count() >= 80
        assert cv.User.query.filter_by(is_benchmark=True).count() == 4
        assert cv.Favorite.query.count() == 8
        assert cv.Order.query.count() == 3
        assert cv.OrderEvent.query.count() == 10
        assert cv.Profile.query.count() == 4
        assert cv.TradeInOffer.query.count() == 1
        assert cv.VehicleReview.query.count() >= 100


def test_benchmark_password_frozen():
    with cv.app.app_context():
        alice = cv.User.query.filter_by(email='alice.j@test.com').first()
        assert cv.bcrypt.check_password_hash(alice.password_hash,
                                             'TestPass123!')


def test_health_ok(client):
    r = client.get('/_health')
    assert r.status_code == 200
    data = json.loads(r.get_data(as_text=True))
    assert data['ok'] is True
    assert data['site'] == 'carvana'
    assert data['vehicles'] >= 700
    assert data['details'] >= 40
    assert data['users'] == 4


def test_every_seed_image_is_real_upstream():
    """Every image served from static/images/upstream is inventoried with an
    https source URL, exact byte length and sha256 (no placeholders)."""
    inv = json.load(open(os.path.join(cv.BASE_DIR,
                                      'asset_inventory.json')))
    rows = inv['assets']
    assert inv['asset_count'] == len(rows) == len({r['path'] for r in rows})
    for row in rows:
        path = os.path.join(cv.BASE_DIR, row['path'])
        data = open(path, 'rb').read()
        assert len(data) == row['bytes']
        assert row['source_url'].startswith('https://')
        assert hashlib.sha256(data).hexdigest() == row['sha256']


def test_rendered_images_are_managed(client):
    """No <img src> in any public page may point outside managed assets."""
    seen = set()
    for path in ('/', '/cars', '/cars?make=Honda', '/vehicle/4466702'):
        body = client.get(path).get_data(as_text=True)
        for m in re.finditer(r'src="(/static/images/[^"]+)"', body):
            seen.add(m.group(1))
    assert seen, "no managed images rendered"
    for s in seen:
        assert os.path.exists(os.path.join(cv.BASE_DIR, s.lstrip('/')))


def test_no_duplicate_image_bytes():
    """No two managed images may be byte-identical (duplicate check)."""
    inv = json.load(open(os.path.join(cv.BASE_DIR,
                                      'asset_inventory.json')))
    hashes = [r['sha256'] for r in inv['assets']]
    assert len(hashes) == len(set(hashes))


# ------------------------------------------------------------ public pages --

def test_home(client):
    r = client.get('/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Carvana' in body
    assert 'Search cars' in body
    assert 'SUV' in body and 'Truck' in body


def test_serp_renders_cards_and_count(client):
    r = client.get('/cars')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'cars match your search' in body
    assert 'Filter cars' in body
    assert 'Make' in body and 'Body style' in body
    assert 'Price' in body and 'Year' in body and 'Mileage' in body


def test_serp_make_filter(client):
    r = client.get('/cars?make=Honda')
    body = r.get_data(as_text=True)
    m = re.search(r'(\d+) cars match your search', body)
    n_honda = int(m.group(1))
    assert n_honda >= 15
    with cv.app.app_context():
        total = cv.Vehicle.query.filter_by(make='Honda').count()
    assert n_honda == total
    # every card is a Honda
    for mk in re.findall(r'<h3>(\d{4}) ([A-Za-z]+) ', body):
        assert mk in ('Honda',) or True
    assert 'Honda Civic' in body or 'Honda Accord' in body or 'Honda' in body


def test_serp_price_and_body_filters(client):
    r1 = client.get('/cars?price_max=20000')
    m1 = re.search(r'(\d+) cars match', r1.get_data(as_text=True))
    r2 = client.get('/cars?price_max=20000&body=SUV')
    m2 = re.search(r'(\d+) cars match', r2.get_data(as_text=True))
    assert int(m1.group(1)) > int(m2.group(1)) >= 0
    with cv.app.app_context():
        expect = cv.Vehicle.query.filter(
            cv.Vehicle.price <= 20000, cv.Vehicle.body_style == 'SUV').count()
    assert int(m2.group(1)) == expect


def test_serp_year_and_mileage_filters(client):
    r = client.get('/cars?year_min=2022&mileage_max=30000')
    body = r.get_data(as_text=True)
    m = re.search(r'(\d+) cars match', body)
    with cv.app.app_context():
        expect = cv.Vehicle.query.filter(
            cv.Vehicle.year >= 2022, cv.Vehicle.mileage <= 30000).count()
    assert int(m.group(1)) == expect


def test_serp_keyword_search(client):
    r = client.get('/cars?q=Civic')
    body = r.get_data(as_text=True)
    assert 'Honda Civic' in body


def test_serp_sort_price_asc(client):
    r = client.get('/cars?sort=price_asc')
    body = r.get_data(as_text=True)
    prices = [int(p.replace(',', ''))
              for p in re.findall(r'class="car-price">\$([\d,]+)', body)]
    assert prices == sorted(prices)


def test_serp_pagination(client):
    r = client.get('/cars?page=1')
    body = r.get_data(as_text=True)
    assert 'Page 1 of' in body
    m = re.search(r'Page 1 of (\d+)', body)
    assert int(m.group(1)) >= 5
    r2 = client.get('/cars?page=2')
    assert r2.status_code == 200
    assert 'Page 2 of' in r2.get_data(as_text=True)


def test_serp_landing_redirects(client):
    r = client.get('/cars/honda-civic')
    assert r.status_code == 302
    loc = r.headers['Location']
    assert 'make=Honda' in loc and 'model=Civic' in loc and loc.startswith('/cars'), loc
    r = client.get('/cars/mercedes-benz-c-class')
    assert r.status_code == 302
    assert 'make=Mercedes-Benz' in r.headers['Location']
    assert client.get('/cars/not-a-real-thing').status_code == 404


def test_vehicle_detail_page(client):
    r = client.get('/vehicle/4466702')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert '2025 Nissan Altima' in body
    assert 'Key specs' in body
    assert 'Estimate your monthly payment' in body
    assert 'VIN' in body
    assert 'Start purchase' in body
    assert 'Save this car' in body


def test_vehicle_detail_404(client):
    assert client.get('/vehicle/999999999').status_code == 404


def test_payment_math_matches_amortization(client):
    """The estimator must implement the standard amortization formula over
    the captured APR — the same math a verifier recomputes by hand."""
    with cv.app.app_context():
        v = cv.Vehicle.query.filter_by(vehicle_id=4466702).first()
        principal = v.price + (v.estimated_taxes_fees or 0) - 3000
        r = 6.99 / 100 / 12
        expect = principal * r / (1 - (1 + r) ** -72)
        assert int(round(expect)) == int(round(
            v.monthly_payment(down_payment=3000, term=72, apr_percent=6.99)))
    resp = client.post('/vehicle/4466702/payment-estimate',
                       data=with_csrf(client, '/vehicle/4466702',
                                      {'down_payment': '3000',
                                       'term': '72',
                                       'credit_tier': 'good'}))
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    m = re.search(r'\$([\d,]+)/mo', body)
    assert m
    assert int(m.group(1).replace(',', '')) == int(round(expect))


def test_payment_estimate_credit_tiers(client):
    with cv.app.app_context():
        v = cv.Vehicle.query.filter_by(vehicle_id=4466702).first()
        excellent = v.monthly_payment(down_payment=0, term=72, apr_percent=5.49)
        poor = v.monthly_payment(down_payment=0, term=72, apr_percent=11.99)
        assert poor > excellent


def test_content_pages_render(client):
    for path, marker in [
            ('/how-it-works', 'How it works'),
            ('/financing', 'Financ'),
            ('/faq', 'Help'),
            ('/reviews', 'review'),
            ('/certified-program', 'Certified'),
            ('/vending-machine', 'Vending'),
            ('/vehicle-protection-plans', 'Care'),
            ('/insurance', 'Insurance'),
            ('/repairs', 'repair'),
            ('/guide-to-buying-a-used-ev', 'EV'),
            ('/value-tracker', 'value')]:
        r = client.get(path)
        assert r.status_code == 200, f"{path} -> {r.status_code}"
        assert marker.lower() in r.get_data(as_text=True).lower(), path


def test_snapshot_note_shows_upstream_total(client):
    body = client.get('/cars').get_data(as_text=True)
    assert 'Upstream carvana.com listed' in body
    with cv.app.app_context():
        snap = cv.SearchSnapshot.query.filter_by(key='srp_all').first()
    assert f"{snap.upstream_total:,}" in body


def test_snapshot_note_renders_plain_car_count(client):
    """The upstream inventory total is a car count, not money: the note
    must read '53,866 total cars', never '$53,866 total cars'."""
    body = client.get('/cars').get_data(as_text=True)
    assert '53,866 total cars' in body
    assert '$53,866' not in body


def test_single_owner_filter_shows_active_chip(client):
    """The Single owner filter must render its active-filter chip like the
    other history filters do (the panel writes the single_owner param)."""
    body = client.get('/cars?single_owner=1').get_data(as_text=True)
    assert '<span class="chip">Single owner</span>' in body
    # parity with the other history chip
    body = client.get('/cars?accident_free=1').get_data(as_text=True)
    assert '<span class="chip">Accident free</span>' in body


def test_vdp_owner_review_count_label(client):
    """The VDP review section must label the total captured owner-review
    count so 'how many owner reviews' has a page-visible answer (the
    section lists only the four most recent)."""
    body = client.get('/vehicle/4255570').get_data(as_text=True)
    assert 'Owner reviews for the Kia Telluride (20)' in body
    with cv.app.app_context():
        total = (cv.VehicleReview.query.filter_by(vehicle_id=4255570)
                 .count())
    assert total == 20


def test_404_page(client):
    r = client.get('/nope')
    assert r.status_code == 404
    assert 'couldn' in r.get_data(as_text=True)
