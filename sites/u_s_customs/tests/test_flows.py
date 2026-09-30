"""Flow tests: the interactive traveler tools end-to-end."""
import re


def _wizard(client, data_overrides=None):
    base = {
        'family_name': 'Muller', 'first_name': 'Anna',
        'birth_date': '1992-09-09', 'gender': 'Female',
        'citizenship': 'Germany',
        'passport_number': 'DE11223344',
        'passport_issue_country': 'Germany',
        'passport_expiry': '2030-04-04',
        'email': 'anna.muller@example.com',
        'phone': '+49 30 555 0100',
        'address_city': 'Berlin', 'address_country': 'Germany',
        'travel_purpose': 'Business',
        'destination_address': '350 Fifth Ave, New York, NY',
        'q_a': 'No', 'q_b': 'No', 'q_c': 'No', 'q_d': 'No', 'q_e': 'No',
        'card_name': 'Anna Muller', 'card_number': '4242 4242 4242 4242',
        'card_exp': '09/29', 'card_cvv': '123', 'disclaimer_agree': 'Yes',
    }
    if data_overrides:
        base.update(data_overrides)
    steps = ['disclaimers', 'applicant', 'personal', 'travel',
             'eligibility', 'review', 'pay']
    application_number = None
    for i, step in enumerate(steps):
        form = {k: v for k, v in base.items()
                if k in ('disclaimer_agree',) and step == 'disclaimers'}
        if step == 'applicant':
            form = {k: base[k] for k in ('family_name', 'first_name',
                                        'birth_date', 'gender', 'citizenship')}
        if step == 'personal':
            form = {k: base[k] for k in ('passport_number',
                                        'passport_issue_country',
                                        'passport_expiry', 'email', 'phone',
                                        'address_city', 'address_country')}
        if step == 'travel':
            form = {k: base[k] for k in ('travel_purpose',
                                        'destination_address')}
        if step == 'eligibility':
            form = {k: base[k] for k in ('q_a', 'q_b', 'q_c', 'q_d', 'q_e')}
        if step == 'pay':
            form = {k: base[k] for k in ('card_name', 'card_number',
                                        'card_exp', 'card_cvv')}
        form['step'] = step
        form['next'] = 'submit' if step == 'pay' else 'next'
        r = client.post('/esta/apply', data=form, follow_redirects=False)
        assert r.status_code == 302, f"wizard step {step} -> {r.status_code}"
        if step == 'pay':
            application_number = re.search(
                r'ESTA-\w+', r.headers['Location']).group(0)
    return application_number


def test_esta_wizard_approval(client):
    num = _wizard(client)
    assert num
    html = client.get(f'/esta/confirmation/{num}').get_data(as_text=True)
    assert 'Authorization Approved' in html
    assert '2028-09-28' in html
    assert '40.27' in html


def test_esta_wizard_non_vwp_not_authorized(client):
    num = _wizard(client, {'citizenship': 'Brazil',
                           'passport_issue_country': 'Brazil',
                           'address_country': 'Brazil',
                           'passport_number': 'BR5566778'})
    assert num
    html = client.get(f'/esta/confirmation/{num}').get_data(as_text=True)
    assert 'Travel Not Authorized' in html


def test_esta_check_by_passport(client):
    r = client.get('/esta/check?passport_number=DE29384756')
    html = r.get_data(as_text=True)
    assert 'ESTA-88291045' in html
    assert 'Authorization Approved' in html
    assert '2028-08-20' in html


def test_i94_lookup_success_and_failure(client):
    r = client.post('/i94/request', data={
        'family_name': 'Johnson', 'first_name': 'Alice',
        'birth_date': '1990-04-12', 'passport_number': 'DE29384756'})
    html = r.get_data(as_text=True)
    assert '269745632011' in html
    assert 'VWP B-1' in html
    assert 'Washington Dulles International Airport' in html
    r = client.post('/i94/request', data={
        'family_name': 'Johnson', 'first_name': 'Alice',
        'birth_date': '1990-04-13', 'passport_number': 'DE29384756'})
    assert 'No I-94 record found' in r.get_data(as_text=True)


def test_login_and_account(client):
    r = client.post('/login', data={'email': 'alice.j@test.com',
                                    'password': 'TestPass123!'})
    assert r.status_code == 302
    html = client.get('/account').get_data(as_text=True)
    assert 'Alice Johnson' in html
    assert 'ESTA-88291045' in html
    assert 'Blaine' in html  # her saved crossing
    # the saved-crossings table renders the live max delay, not a placeholder
    assert 'see crossing page' not in html
    assert re.search(r'\d+ min', html), 'no numeric max delay rendered'
    r = client.get('/logout')
    assert r.status_code == 302


def test_login_wrong_password(client):
    r = client.post('/login', data={'email': 'alice.j@test.com',
                                     'password': 'nope'})
    assert b'Invalid email or password' in r.data


def test_bob_conditional_approval_flow(client):
    client.post('/login', data={'email': 'bob.c@test.com',
                                'password': 'TestPass123!'})
    html = client.get('/account').get_data(as_text=True)
    assert 'GE-77031188' in html
    html = client.get('/ttp/schedule/GE-77031188').get_data(as_text=True)
    assert 'Austin-Bergstrom International Airport' in html
    m = re.search(r'<option value="(\d+)">Austin-Bergstrom', html)
    assert m
    r = client.post('/ttp/schedule/GE-77031188',
                    data={'center': m.group(1), 'date': '2026-10-15',
                          'slot': '9:00 a.m.'}, follow_redirects=True)
    assert 'Interview Scheduled' in r.get_data(as_text=True)


def test_ttp_status_lookup(client):
    r = client.get('/ttp/status?application_number=GE-77554402',
                   follow_redirects=True)
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'GE-77554402' in html
    assert 'Interview Scheduled' in html
    assert 'Los Angeles International Airport' in html


def test_ttp_apply(client):
    r = client.post('/ttp/apply/nexus', data={
        'family_name': 'Taylor', 'first_name': 'Sam',
        'birth_date': '1991-01-01', 'citizenship': 'Canada',
        'email': 'sam@example.com', 'phone': '+1 555 0100',
        'passport_number': 'CA998877'}, follow_redirects=False)
    assert r.status_code == 302
    num = r.headers['Location'].split('/')[-1]
    html = client.get(f'/ttp/status/{num}').get_data(as_text=True)
    assert 'Pending Review' in html
    assert '$50' in html


def test_save_crossing_requires_login(client):
    r = client.post('/account/saved/crossing/1', follow_redirects=False)
    assert r.status_code == 302
    assert '/login' in r.headers['Location']


def test_save_and_list_crossing(auth_client):
    r = auth_client.post('/account/saved/crossing/1', follow_redirects=True)
    assert r.status_code == 200
    html = auth_client.get('/account').get_data(as_text=True)
    assert 'Saved Border Crossings' in html


def test_job_save_flow(client):
    client.post('/login', data={'email': 'dana.k@test.com',
                                'password': 'TestPass123!'})
    r = client.post('/careers/job/882166800/save', follow_redirects=True)
    assert r.status_code == 200
    html = client.get('/account').get_data(as_text=True)
    assert 'CBP Officer' in html or 'Customs and Border Protection Officer' in html


def test_form_download_sha(client):
    from app import CbpForm
    from app import app
    with app.app_context():
        form = CbpForm.query.filter_by(form_number='19').first()
    r = client.get(f'/forms/download/{form.catalog_key}')
    assert r.status_code == 200
    import hashlib
    data = r.get_data()
    assert hashlib.sha256(data).hexdigest() == form.sha256


def test_invalid_pagination_does_not_crash(client):
    for path in ['/bwt', '/newsroom/media-releases/all']:
        response = client.get(path + '?page=not-a-number')
        assert response.status_code == 200
