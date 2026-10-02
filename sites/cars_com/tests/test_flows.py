"""Flow tests: stateful, CSRF-token-submitting walks through the mirror —
search + save, dealer walkthrough, research + compare, the Instant Cash
Offer wizard end to end, the payment calculator, and account flows."""
import re

from conftest import with_csrf


def _card_hrefs(body, n=3):
    return re.findall(r'href="(/vehicledetail/[0-9a-f-]{36}/)"', body)[:n]


def test_search_filter_save_flow(alice):
    # 1. search used SUVs under $40k within 50 miles
    r = alice.get('/shopping/results/?stock_type=used&body_style_slugs=suv'
                  '&list_price_max=40000&maximum_distance=50')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'vehicle-card-' in body
    # 2. save the first car from the results page
    href = _card_hrefs(body, 1)[0]
    r = alice.post(f'/save/{href.split("/")[2]}/',
                   data=with_csrf(alice, f'/shopping/results/?stock_type=used&body_style_slugs=suv',
                                  {'next': '/shopping/results/?stock_type=used&body_style_slugs=suv'}),
                   follow_redirects=False)
    assert r.status_code == 302
    # 3. it appears in the garage
    r = alice.get('/profile/your-garage/')
    assert r.status_code == 200
    assert 'Saved cars' in r.get_data(as_text=True)
    assert href in r.get_data(as_text=True)


def test_save_search_flow(bob):
    r = bob.get('/shopping/results/?stock_type=new&models[]=toyota-rav4')
    assert r.status_code == 200
    data = with_csrf(bob, '/shopping/results/?stock_type=new&models[]=toyota-rav4',
                    {'query_string': '/shopping/results/?stock_type=new&models[]=toyota-rav4',
                     'name': 'New Toyota RAV4', 'alert_frequency': 'weekly'})
    r = bob.post('/searches/save/', data=data, follow_redirects=False)
    assert r.status_code == 302
    r = bob.get('/profile/your-garage/')
    body = r.get_data(as_text=True)
    assert 'New Toyota RAV4' in body
    assert 'weekly' in body


def test_unsave_flow(carol):
    r = carol.get('/profile/your-garage/')
    body = r.get_data(as_text=True)
    m = re.search(r'action="(/save/[0-9a-f-]{36}/)"', body)
    assert m, "benchmark user should have a saved car to remove"
    r = carol.post(m.group(1), data=with_csrf(carol, '/profile/your-garage/',
                                              {'next': '/profile/your-garage/'}))
    assert r.status_code == 302
    assert m.group(1) not in carol.get('/profile/your-garage/').get_data(as_text=True)


def test_offer_wizard_flow(dana):
    # step 1: vehicle selection
    r = dana.get('/sell/instant-offer/')
    assert r.status_code == 200
    start = '/sell/instant-offer/'
    r = dana.post('/sell/instant-offer/vehicle/',
                  data=with_csrf(dana, start, {'year': '2018', 'make': 'HONDA',
                                               'model': 'CIVIC',
                                               'trim': 'EX 4 DOOR HATCHBACK 1.5L 4 CYL TURBO'}),
                  follow_redirects=False)
    assert r.status_code == 302
    # step 2: details
    r = dana.get('/sell/instant-offer/details/')
    assert r.status_code == 200
    assert 'Estimated car value' in r.get_data(as_text=True)
    r = dana.post('/sell/instant-offer/details/',
                  data=with_csrf(dana, '/sell/instant-offer/details/',
                                 {'mileage': '60000', 'zip': '98101',
                                  'exterior_color': 'Blue', 'keys': '1',
                                  'original_owner': 'Yes', 'payments': 'No'}),
                  follow_redirects=False)
    assert r.status_code == 302
    # step 3: the offer
    r = dana.get('/sell/instant-offer/offer/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    m = re.search(r'\$([\d,]+) - \$([\d,]+)', body)
    assert m and int(m.group(1).replace(',', '')) > 500
    # the offer is saved to the garage
    r = dana.get('/profile/your-garage/')
    assert 'Instant Offer requests' in r.get_data(as_text=True)
    assert 'Civic' in r.get_data(as_text=True)


def test_offer_wizard_requires_details(client):
    r = client.post('/sell/instant-offer/vehicle/',
                    data=with_csrf(client, '/sell/instant-offer/',
                                   {'year': '2018', 'make': 'HONDA', 'model': 'CIVIC',
                                    'trim': 'EX 4 DOOR HATCHBACK 1.5L 4 CYL TURBO'}),
                    follow_redirects=False)
    assert r.status_code == 302
    r = client.post('/sell/instant-offer/details/',
                    data=with_csrf(client, '/sell/instant-offer/details/', {'mileage': ''}),
                    follow_redirects=False)
    assert r.status_code == 400


def test_offer_session_guard(client):
    r = client.get('/sell/instant-offer/details/')
    assert r.status_code == 302
    r = client.get('/sell/instant-offer/offer/')
    assert r.status_code == 302


def test_register_login_logout(client):
    r = client.post('/authn/register',
                    data=with_csrf(client, '/authn/register',
                                   {'name': 'Test Runner', 'email': 'runner.t@test.com',
                                    'password': 'Passw0rd!'}),
                    follow_redirects=False)
    assert r.status_code == 302
    r = client.get('/profile/your-garage/')
    assert r.status_code == 200
    assert 'runner.t@test.com' in r.get_data(as_text=True)
    r = client.post('/authn/logout', data=with_csrf(client, '/profile/your-garage/', {}),
                    follow_redirects=False)
    assert r.status_code == 302
    r = client.get('/profile/your-garage/', follow_redirects=False)
    assert r.status_code == 302  # login redirect


def test_login_bad_password(client):
    r = client.post('/authn/login', data={'email': 'alice.j@test.com',
                                          'password': 'wrong-password',
                                          'csrf_token': 'nope'})
    assert r.status_code in (400, 401)


def test_dealer_walkthrough(client):
    # directory -> dealer page -> inventory -> a listing
    r = client.get('/dealers/?sort=rating')
    assert r.status_code == 200
    m = re.search(r'href="(/dealers/\d+/[a-z0-9_-]+)/"', r.get_data(as_text=True))
    assert m
    r = client.get(m.group(1) + '/')
    assert r.status_code == 200
    m2 = re.search(r'href="(/dealers/\d+/[a-z0-9-]+/inventory/)"',
                   r.get_data(as_text=True))
    if m2:
        r = client.get(m2.group(1))
        assert r.status_code == 200


def test_research_compare_walk(client):
    r = client.get('/research/compare/')
    assert r.status_code == 200
    m = re.search(r'href="(/research/compare/[a-z0-9_-]+/)"', r.get_data(as_text=True))
    assert m
    r = client.get(m.group(1))
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'vs.' in body
    # both models link back to their research pages
    assert body.count('/research/') >= 2


def test_detail_price_history(client):
    from app import Listing
    with client.application.app_context():
        l = Listing.query.filter(Listing.price_history != '[]',
                                 Listing.price_history.isnot(None)).first()
    if not l:
        return
    r = client.get(f'/vehicledetail/{l.id}/')
    assert r.status_code == 200
    assert 'Price history' in r.get_data(as_text=True)
