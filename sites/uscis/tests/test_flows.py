"""Flow tests: drive the interactive tools the way an agent would."""
import json
import re


def _csrf(client, path):
    html = client.get(path).get_data(as_text=True)
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    return m.group(1) if m else None


def test_case_status_lookup(client):
    tok = _csrf(client, '/casestatus')
    resp = client.post('/casestatus', data={'csrf_token': tok,
                                            'receipt': 'SRC2210123456'})
    html = resp.get_data(as_text=True)
    assert 'Case Is Being Actively Reviewed' in html
    assert 'I-485' in html
    assert 'Case Was Received' in html  # history timeline renders
    assert '08/30/2026' in html


def test_case_status_rejects_unknown_receipt(client):
    tok = _csrf(client, '/casestatus')
    resp = client.post('/casestatus', data={'csrf_token': tok,
                                            'receipt': 'SRC0000000001'})
    html = resp.get_data(as_text=True)
    assert 'Validation Error' in html
    assert 'National Customer Service Center' in html


def test_login_and_my_progress(auth_alice):
    html = auth_alice.get('/account').get_data(as_text=True)
    assert 'Alice Johnson' in html
    assert 'SRC2210123456' in html and 'SRC2210567890' in html
    assert 'USCWAS2610081030' in html  # seeded ADIT stamp appointment


def test_login_rejects_bad_password(client):
    client.post('/account/login', data={'email': 'alice.j@test.com',
                                        'password': 'WrongPass99!'})
    resp = client.get('/account')
    assert resp.status_code == 302


def test_wizard_full_civilian_path(client):
    path = '/citizenship-resource-center/learn-about-citizenship/naturalization-eligibility-tool-0'
    html = client.get(path).get_data(as_text=True)
    for opt in ['No', '18 or older', 'No', 'Yes', 'No',
                'Before December 27, 2021', 'No', 'No']:
        tok = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)
        key = re.search(r'name="state_key" value="([^"]+)"', html).group(1)
        ans = re.search(r'name="answers" value="(\[.*?\])"', html)
        html = client.post(path, data={'csrf_token': tok, 'state_key': key,
                                       'option': opt,
                                       'answers': ans.group(1) if ans else '[]'},
                           follow_redirects=True).get_data(as_text=True)
    assert 'lawful permanent resident for more than 5 years' in html
    assert 'Start over' in html


def test_wizard_parents_citizen_shortcut(client):
    path = '/citizenship-resource-center/learn-about-citizenship/naturalization-eligibility-tool-0'
    html = client.get(path).get_data(as_text=True)
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)
    key = re.search(r'name="state_key" value="([^"]+)"', html).group(1)
    html = client.post(path, data={'csrf_token': tok, 'state_key': key,
                                   'option': 'Yes', 'answers': '[]'},
                       follow_redirects=True).get_data(as_text=True)
    assert 'You may already be a U.S. citizen.' in html
    assert 'N-600' in html


def test_civil_surgeon_filters(client):
    base = client.get('/tools/find-a-civil-surgeon?zip=22202').get_data(as_text=True)
    assert 'VAN DORN PEDIATRICS' in base
    arabic = client.get('/tools/find-a-civil-surgeon?zip=22202&language=Arabic').get_data(as_text=True)
    assert 'Arabic' in arabic
    assert arabic.count('class="surgeon"') == 5  # five Arabic-speaking rows in the frozen set
    female = client.get('/tools/find-a-civil-surgeon?zip=60601&gender=Female').get_data(as_text=True)
    assert female.count('class="surgeon"') == 5


def test_fee_calculator_n400(client):
    html = client.get('/feecalculator').get_data(as_text=True)
    m = re.search(r'<option value="(\d+)"[^>]*>N-400, Application for Naturalization', html)
    assert m
    html = client.get(f"/feecalculator?form={m.group(1)}").get_data(as_text=True)
    assert '$760' in html and '$710' in html
    assert '$380' in html  # reduced fee for <=400% FPL


def test_processing_times_inquiry_guidance(client):
    html = client.get('/processing-times?form=I-485&office=CHI').get_data(as_text=True)
    assert '13.5 Months to 35.5 Months' in html
    assert 'January 10, 2017' in html
    assert 'submit an inquiry' in html


def test_appointment_book_and_view(auth_dana):
    # book a fresh ADIT stamp appointment in Houston
    html = auth_dana.get('/appointment/new').get_data(as_text=True)
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)
    html = auth_dana.post('/appointment/new', data={
        'csrf_token': tok, 'action': 'pick_reason', 'reason': 'ADIT Stamp',
        'reason_detail': 'flow test'}, follow_redirects=True).get_data(as_text=True)
    assert 'Enter your ZIP code' in html
    html = auth_dana.post('/appointment/new', data={
        'csrf_token': tok, 'action': 'find_office', 'reason': 'ADIT Stamp',
        'reason_detail': '', 'zip': '77002'}, follow_redirects=True).get_data(as_text=True)
    assert 'Houston' in html
    slot = re.search(r'name="slot" value="([^"]+)"', html).group(1)
    html = auth_dana.post('/appointment/new', data={
        'csrf_token': tok, 'action': 'pick_slot', 'reason': 'ADIT Stamp',
        'reason_detail': '', 'zip': '77002', 'office': 'HOU',
        'slot': slot}, follow_redirects=True).get_data(as_text=True)
    assert 'Your Appointment Is Scheduled' in html
    conf = re.search(r'Confirmation: ([A-Z0-9]+)', html).group(1)
    assert conf.startswith('USCHOU')
    # view it through the public lookup flow
    html = auth_dana.get('/appointment/view').get_data(as_text=True)
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)
    html = auth_dana.post('/appointment/view', data={
        'csrf_token': tok, 'confirmation': conf, 'zip': '77002'}).get_data(as_text=True)
    assert conf in html and 'Scheduled' in html


def test_appointment_cancel_flow(auth_dana):
    dash = auth_dana.get('/account').get_data(as_text=True)
    assert 'USCHOU2610060945' in dash  # seeded EAP appointment
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', dash).group(1)
    html = auth_dana.post('/appointment/cancel', data={
        'csrf_token': tok, 'confirmation': 'USCHOU2610060945'},
        follow_redirects=True).get_data(as_text=True)
    assert 'canceled' in html.lower()
    view = auth_dana.get('/appointment/view').get_data(as_text=True)
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', view).group(1)
    html = auth_dana.post('/appointment/view', data={
        'csrf_token': tok, 'confirmation': 'USCHOU2610060945',
        'zip': '77002'}).get_data(as_text=True)
    assert 'Canceled' in html


def test_change_of_address(auth_dana):
    html = auth_dana.get('/account/address').get_data(as_text=True)
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)
    html = auth_dana.post('/account/address', data={
        'csrf_token': tok, 'street': '42 Treaty Rd', 'city': 'Houston',
        'state': 'TX', 'zip': '77002'}, follow_redirects=True).get_data(as_text=True)
    assert 'Your address has been updated' in html
    assert '42 Treaty Rd' in html


def test_registration_creates_account(client):
    html = client.get('/account/register').get_data(as_text=True)
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)
    resp = client.post('/account/register', data={
        'csrf_token': tok, 'display_name': 'Test User',
        'email': 'test.user@example.org', 'password': 'Passw0rd!'},
        follow_redirects=True)
    html = resp.get_data(as_text=True)
    assert 'Test User' in html
    assert 'USC' in html  # an account number was assigned


def test_field_office_lookup_chain(client):
    for zip_code, office in [('60601', 'Chicago'), ('77002', 'Houston'),
                             ('10001', 'New York'), ('94105', 'San Francisco')]:
        html = client.get(f'/about-us/find-a-uscis-office/field-offices/search?zip={zip_code}').get_data(as_text=True)
        assert office in html, f"{zip_code} did not resolve to {office}"


def test_case_status_requires_valid_format(client):
    tok = _csrf(client, '/casestatus')
    html = client.post('/casestatus', data={'csrf_token': tok,
                                            'receipt': 'SHORT'}).get_data(as_text=True)
    assert 'does not recognize the receipt number' in html
