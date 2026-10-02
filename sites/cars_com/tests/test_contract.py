"""Contract tests: every route renders 200 with its key content, and the
seeded corpus supports the upstream filter taxonomy."""
import re

from conftest import with_csrf


def text_of(response):
    import html as html_mod
    return " ".join(html_mod.unescape(
        re.sub(r"<[^>]+>", " ", response.get_data(as_text=True))).split())


def test_health(client):
    r = client.get('/_health')
    assert r.status_code == 200
    data = r.get_json()
    assert data['ok'] is True
    assert data['listings'] >= 250
    assert data['dealers'] >= 10
    assert data['models'] >= 5
    assert data['compares'] >= 3
    assert data['valuations'] >= 5
    assert data['users'] == 4


def test_home(client):
    r = client.get('/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Find your next car' in body
    assert 'Certified Pre-Owned Cars' in body
    assert 'What&#39;s My Car Worth?' in body or "What's My Car Worth" in body
    # the search widget exposes the upstream stock taxonomy
    for label in ('New, used &amp; CPO', 'Certified Pre-Owned', 'Search'):
        assert label in body


def test_srp_used_all(client):
    r = client.get('/shopping/results/?stock_type=used')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Used Cars for Sale Near' in body
    assert 'results' in body
    assert 'vehicle-card-' in body


def test_srp_filters(client):
    r = client.get('/shopping/results/?stock_type=used&body_style_slugs=suv'
                   '&list_price_max=40000&maximum_distance=50')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    m = re.search(r'class="result-count-pill">([^<]+)', body)
    assert m
    assert 'vehicle-card-' in body


def test_srp_make_model(client):
    r = client.get('/shopping/results/?stock_type=used&makes[]=honda&models[]=honda-civic')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Honda Civic' in body


def test_srp_sort_price(client):
    r = client.get('/shopping/results/?stock_type=used&sort=list_price_asc')
    assert r.status_code == 200
    prices = [int(p.replace(',', '')) for p in
              re.findall(r'class="price">\$([\d,]+)', r.get_data(as_text=True))]
    assert prices == sorted(prices)


def test_srp_pagination(client):
    r1 = client.get('/shopping/results/?stock_type=used')
    assert r1.status_code == 200
    body = r1.get_data(as_text=True)
    m = re.search(r'Page 1 of (\d+)', body)
    if m and int(m.group(1)) > 1:
        r2 = client.get('/shopping/results/?stock_type=used&page=2')
        assert r2.status_code == 200
        assert 'vehicle-card-' in r2.get_data(as_text=True)


def test_srp_deal_rating_filter(client):
    r = client.get('/shopping/results/?stock_type=used&deal_ratings=fair')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    m = re.search(r'class="result-count-pill">(\d+) results', body)
    assert m and int(m.group(1)) > 0


def test_srp_keyword(client):
    r = client.get('/shopping/results/?keyword=Tesla')
    assert r.status_code == 200
    assert 'Tesla' in r.get_data(as_text=True)


def test_srp_csrf_required(client):
    r = client.post('/searches/save/', data={'query_string': '/shopping/results/?stock_type=used'})
    # CSRF missing -> Flask-WTF rejects with 400 before login_required redirect
    assert r.status_code in (302, 400)


def test_detail_page(client):
    from app import Listing
    with client.application.app_context():
        l = Listing.query.filter_by(has_detail=True).first()
    r = client.get(f'/vehicledetail/{l.id}/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert l.title in body
    assert 'Features &amp; specs' in body
    assert 'csrf_token' in body


def test_detail_404(client):
    r = client.get('/vehicledetail/00000000-0000-0000-0000-000000000000/')
    assert r.status_code == 404


def test_browse_pages(client):
    for path, marker in [('/shopping/new/', 'Shop All New Cars'),
                         ('/shopping/used/', 'Used Cars'),
                         ('/shopping/certified-preowned/', 'Certified Pre-Owned'),
                         ('/shopping/suv/', 'SUVs for Sale'),
                         ('/shopping/electric/', 'Electric Cars for Sale'),
                         ('/shopping/cheap/', 'Cheap Cars for Sale'),
                         ('/shopping/for-sale-by-owner/', 'Cars for Sale by Owner')]:
        r = client.get(path)
        assert r.status_code == 200, path
        assert marker in r.get_data(as_text=True), path


def test_dealers_index(client):
    r = client.get('/dealers/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Car dealers near' in body
    assert 'dealer-row' in body


def test_dealers_filters(client):
    r = client.get('/dealers/?rating=4&sort=rating')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'matches' in body


def test_dealer_page(client):
    from app import Dealer
    with client.application.app_context():
        d = Dealer.query.filter(Dealer.about.isnot(None)).first()
        if not d:
            d = Dealer.query.first()
    r = client.get(f'/dealers/{d.id}/{d.slug}/')
    assert r.status_code == 200
    assert d.name in r.get_data(as_text=True)


def test_dealer_inventory(client):
    from app import Dealer, Listing
    with client.application.app_context():
        d = Dealer.query.first()
        count = Listing.query.filter_by(dealer_id=d.id).count()
    r = client.get(f'/dealers/{d.id}/{d.slug}/inventory/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'cars listed at this dealership' in body
    if count:
        assert 'vehicle-card-' in body


def test_research_home(client):
    r = client.get('/research/')
    assert r.status_code == 200
    assert 'Research cars' in r.get_data(as_text=True)


def test_model_page(client):
    from app import ModelPage
    with client.application.app_context():
        p = ModelPage.query.filter(ModelPage.trims.isnot(None)).first()
    r = client.get(f'/research/{p.slug}/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Available trims' in body
    assert 'Consumer reviews' in body


def test_compare_pages(client):
    from app import ComparePair
    with client.application.app_context():
        pair = ComparePair.query.first()
    r = client.get(f'/research/compare/{pair.slug}/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Starting MSRP' in body
    r2 = client.get('/research/compare/')
    assert r2.status_code == 200


def test_offer_start(client):
    r = client.get('/sell/instant-offer/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Get your Instant Offer' in body
    assert 'Select year' in body
    assert 'csrf_token' in body


def test_offer_api(client):
    r = client.get('/sell/instant-offer/api/models?make=HONDA')
    assert r.status_code == 200
    models = r.get_json()
    assert 'CIVIC' in models


def test_calculator_get(client):
    r = client.get('/car-loan-calculator/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Estimate your monthly car loan payment' in body


def test_calculator_post(client):
    data = with_csrf(client, '/car-loan-calculator/', {
        'vehicle_price': '30000', 'credit_rating': 'good', 'term': '72',
        'zip': '98101', 'down_payment': '0', 'trade_in': '0',
        'cash_incentives': '', 'fees': '', 'custom_apr': ''})
    r = client.post('/car-loan-calculator/', data=data)
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    m = re.search(r'Estimated monthly payment: \$([\d,]+)', body)
    assert m
    # price+tax at 7% over 72 months ≈ $485/mo — sanity window
    assert 380 <= int(m.group(1).replace(',', '')) <= 620


def test_auth_pages(client):
    r = client.get('/authn/login')
    assert r.status_code == 200 and 'Log in to Cars.com' in r.get_data(as_text=True)
    r = client.get('/authn/register')
    assert r.status_code == 200 and 'Create your Cars.com account' in r.get_data(as_text=True)


def test_404(client):
    r = client.get('/shopping/this-does-not-exist/')
    assert r.status_code == 404
    assert "can't find that page" in r.get_data(as_text=True)
