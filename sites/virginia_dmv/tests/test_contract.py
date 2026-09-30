"""Contract tests: every route family renders real upstream-sourced content."""
import json


def _get(client, path):
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"
    return resp.get_data(as_text=True)


def test_health(client):
    data = json.loads(client.get('/_health').get_data())
    assert data['ok'] is True
    assert data['site'] == 'virginia_dmv'
    assert data['pages'] >= 30
    assert data['offices'] >= 130
    assert data['plates'] >= 340
    assert data['forms'] >= 410
    assert data['news'] >= 65
    assert data['quiz_questions'] >= 260
    assert data['manual_subsections'] >= 20
    assert data['fee_rows'] >= 70
    assert data['online_services'] >= 60
    assert data['users'] == 4
    assert data['vehicles'] == 5


def test_homepage(client):
    html = _get(client, '/')
    # the homepage renders the captured upstream home page data
    for marker in ['Virginia Department of Motor Vehicles', 'Reserve Your Spot',
                   'Browse license plates', 'Practice Exams', 'Scam Alert!',
                   'Get a REAL ID', 'Change my address',
                   'What can we help you find today?', 'Explore your online options',
                   'Popular Services']:
        assert marker in html, f"homepage missing {marker!r}"


def test_content_pages(client):
    probes = [
        ('/licenses-ids', 'Learner'),
        ('/licenses-ids', 'REAL ID'),
        ('/licenses-ids/license', 'Apply for a Driver'),
        ('/licenses-ids/license', 'Renew Your Driver'),
        ('/licenses-ids/license', 'Practice Exams'),
        ('/licenses-ids/learners', 'Learner'),
        ('/licenses-ids/learners', 'Permit'),
        ('/licenses-ids/real-id', 'REAL ID'),
        ('/licenses-ids/real-id', 'REAL ID compliant'),
        ('/licenses-ids/cdl', 'Commercial Driver'),
        ('/licenses-ids/id-cards', 'ID Cards'),
        ('/licenses-ids/motorcycle', 'Motorcycle License'),
        ('/vehicles', 'Review Vehicle Requirements'),
        ('/vehicles', 'Taxes'),
        ('/vehicles/registration', 'Requirements Before Registering'),
        ('/vehicles/registration', 'Renewal Fees and Multi-Year Discounts'),
        ('/vehicles/title', 'Title'),
        ('/vehicles/title', 'Vehicle'),
        ('/vehicles/buy-sell', 'Selling/Donating a Virginia-titled Vehicle'),
        ('/vehicles/buy-sell', 'Notify DMV you have sold, traded or donated'),
        ('/vehicles/taxes-fees', 'DMV Fees'),
        ('/moving', 'Moving'),
        ('/moving/new-virginia', 'New to Virginia'),
        ('/moving/new-virginia', 'Get a Virginia Driver'),
        ('/moving/new-virginia', 'Title Your Vehicle in Virginia'),
        ('/records/request-driver-vehicle-record', 'Request a Copy of Your'),
        ('/about', 'About DMV'),
        ('/contact-us', 'Contact Us'),
        ('/online-services/address-change', 'Change Address'),
    ]
    for path, marker in probes:
        html = _get(client, path)
        assert marker in html, f"{path} missing {marker!r}"


def test_plates_catalog(client):
    html = _get(client, '/vehicles/license-plates/search')
    assert 'Search/View Specialized License Plates' in html
    assert '173rd Airborne' in html
    html = _get(client, '/vehicles/license-plates/search?category=College')
    assert 'Displaying' in html and '(342)' not in html
    html = _get(client, '/vehicles/license-plates/search?q=virginia+tech')
    assert 'Virginia Tech - Go Hokies' in html
    html = _get(client, '/vehicles/license-plates/search/virginia-tech-go-hokies')
    assert '$25' in html and 'Revenue Sharing Plates' in html
    assert 'HOKIE' in html
    # the plate image is a real upstream file served from static
    assert '/static/images/plates/' in html


def test_office_locator(client):
    html = _get(client, '/all-locations')
    assert 'Customer Service Center' in html
    assert 'DMV Select' in html
    assert 'Alexandria' in html
    html = _get(client, '/all-locations?type=dmv_select')
    assert 'AAA Alexandria' in html
    html = _get(client, '/locations/alexandria')
    assert '2681 Mill Road' in html
    assert '804-497-7100' in html
    assert 'Road Skills Testing' in html
    assert 'Nearby Alternatives' in html


def test_forms_catalog(client):
    html = _get(client, '/forms')
    assert 'Plate/Decal Transfer' in html
    assert 'ASA 42' in html
    html = _get(client, '/forms?category=Driver')
    assert 'Displaying' in html
    html = _get(client, '/forms?q=crd+93')
    assert 'Information Request' in html
    # PDF download serves the real upstream form file
    resp = client.get('/download/forms/asa42.pdf')
    assert resp.status_code == 200
    assert resp.mimetype == 'application/pdf'
    assert resp.data[:4] == b'%PDF'


def test_fee_chart(client):
    html = _get(client, '/vehicles/taxes-fees')
    for marker in ['$30.75', '$35.75', '$44.75', '$24.75', '$15.00', '$32.00',
                   '$10.00', '4.15% of sales price', '$600']:
        assert marker in html, f"fee chart missing {marker!r}"
    resp = client.get('/download/dmv201.pdf')
    assert resp.status_code == 200
    assert resp.data[:4] == b'%PDF'


def test_newsroom(client):
    html = _get(client, '/news')
    assert 'DMV News' in html
    html = _get(client, '/news/virginia-issued-drivers-licenses-and-ids-now-available-apple-wallet')
    assert 'Apple Wallet' in html


def test_manual_and_practice_exam(client):
    html = _get(client, '/drivers-manual')
    assert 'About DMV Testing' in html
    assert 'Signals, Signs and Pavement Markings' in html
    html = _get(client, '/drivers-manual/1/1')
    assert 'Two-Part Knowledge Exam Test' in html
    assert 'must correctly answer all ten traffic sign questions' in html
    assert '80 percent' in html
    html = _get(client, '/drivers-manual/1/3')
    assert 'Vision Screening' in html
    assert '20/40' in html
    html = _get(client, '/licenses-ids/exams/practice-exam/2')
    assert 'Traffic Signals' in html
    assert 'Sample questions' in html


def test_online_services_catalog(client):
    html = _get(client, '/online-services-all')
    text = _get(client, '/online-services-all')
    for marker in ['Vehicle Registration Renewal', 'Driver', 'CDL Renewal',
                   'DMV Online Account', 'Plate Purchase', 'Record Request',
                   'Trucking Services', 'Payments and Refunds']:
        assert marker in text, f"online services missing {marker!r}"


def test_404(client):
    assert client.get('/nonexistent-page').status_code == 404
