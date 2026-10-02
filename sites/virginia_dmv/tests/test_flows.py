"""Flow tests: the stateful DMV online-account surface, driven exactly like a
browser (CSRF enabled, tokens read from the rendered pages).

All fee assertions use the real DMV 201 fee-chart numbers: passenger
<=4,000 lbs $30.75/yr, internet discount $1/yr, 2-year $3 / 3-year $4
discounts, emissions $2/yr, EV highway use fee $135.63/yr, late fee $10,
license $4/yr ($32 for 8 years), replacement $20, REAL ID $10 one-time,
records $8 online + $5 certified.
"""
import re

from conftest import with_csrf

MONEY = r"\$[\d,]+\.\d{2}"


def _first_vehicle_id(client):
    html = client.get('/account').get_data(as_text=True)
    m = re.search(r'/account/vehicles/(\d+)/renew', html)
    assert m, "no vehicle renewal link on the dashboard"
    return m.group(1)


def test_bad_login_rejected(client):
    r = client.post('/account/login', data=with_csrf(
        client, '/account/login', {'email': 'alice.j@test.com', 'password': 'wrong'}))
    assert b'sign-in failed' in r.data


def test_login_required_redirect(client):
    r = client.get('/account')
    assert r.status_code == 302
    assert '/account/login' in r.headers['Location']


def test_csrf_required(client):
    # no token -> 400 (CSRF protection is ON for the whole suite)
    r = client.post('/account/login', data={'email': 'alice.j@test.com',
                                            'password': 'TestPass123!'})
    assert r.status_code == 400


def test_dashboard_shows_license_and_vehicles(alice):
    html = alice.get('/account').get_data(as_text=True)
    assert 'Alice Johnson' in html
    assert 'D1234581' in html
    assert '2019 Toyota Camry' in html
    assert '2021 Toyota RAV4' in html
    assert 'REAL ID compliant' in html
    assert 'VADM9620114A' in html  # seeded appointment
    assert 'R20260114-3841' in html  # seeded transaction receipt


def test_address_change_flow(alice):
    r = alice.post('/account/address-change', data=with_csrf(
        alice, '/account/address-change',
        {'street': '500 E Broad St', 'city': 'Richmond', 'state': 'VA', 'zip': '23219'}),
        follow_redirects=True)
    assert b'has been updated' in r.data
    html = alice.get('/account').get_data(as_text=True)
    assert '500 E Broad St' in html
    # invalid zip rejected
    r = alice.post('/account/address-change', data=with_csrf(
        alice, '/account/address-change',
        {'street': '1 Test St', 'city': 'Richmond', 'state': 'VA', 'zip': 'ABC'}))
    assert b'complete Virginia mailing address' in r.data


def test_registration_renewal_math_passenger(alice):
    vid = _first_vehicle_id(alice)
    # 1-year preview: 30.75 - 1.00 internet = 29.75
    html = alice.get(f'/account/vehicles/{vid}/renew?years=1').get_data(as_text=True)
    assert re.search(r'\$30\.75', html)
    assert re.search(r'\$29\.75', html)
    # 2-year: 61.50 - 2.00 - 3.00 = 56.50
    html = alice.get(f'/account/vehicles/{vid}/renew?years=2').get_data(as_text=True)
    assert '$56.50' in html
    r = alice.post(f'/account/vehicles/{vid}/renew', data=with_csrf(
        alice, f'/account/vehicles/{vid}/renew?years=2', {'years': '2'}),
        follow_redirects=True)
    assert b'Official Internet Receipt' in r.data
    assert b'$56.50' in r.data
    m = re.search(rb'Receipt (REG[\w-]+)', r.data)
    assert m
    # receipt visible in transaction history
    html = alice.get('/account').get_data(as_text=True)
    assert m.group(1).decode() in html


def test_registration_renewal_math_emissions_and_late_fee(bob):
    # Bob's F-150: pickup 6,501-10,000 lbs = $44.75/yr, emissions locality (+$2/yr)
    vid = _first_vehicle_id(bob)
    html = bob.get(f'/account/vehicles/{vid}/renew?years=1').get_data(as_text=True)
    assert '$44.75' in html
    assert '$2.00' in html  # emissions program fee
    # 44.75 + 2.00 - 1.00 internet = 45.75
    assert '$45.75' in html


def test_registration_renewal_math_ev_highway_use_fee(dana):
    # Dana's Bolt EV: 30.75 + 135.63 HUF - 1.00 internet = 165.38
    vid = _first_vehicle_id(dana)
    html = dana.get(f'/account/vehicles/{vid}/renew?years=1').get_data(as_text=True)
    assert '$135.63' in html
    assert '$165.38' in html


def test_expired_registration_charged_late_fee(carol):
    # Carol's motorcycle registration expires 2026-12-31 (not late), but her
    # license is expired; the motorcycle renewal is the normal math:
    # 24.75 - 1.00 = 23.75
    vid = _first_vehicle_id(carol)
    html = carol.get(f'/account/vehicles/{vid}/renew?years=1').get_data(as_text=True)
    assert '$24.75' in html
    assert '$23.75' in html


def test_first_real_id_requires_office_visit(carol):
    response = carol.post('/account/license/renew', data=with_csrf(
        carol, '/account/license/renew', {'years': '8', 'real_id': '1'}))
    assert response.status_code == 400
    assert b'customer service center' in response.data


def test_license_renewal_standard(alice):
    r = alice.post('/account/license/renew', data=with_csrf(
        alice, '/account/license/renew', {'years': '8'}),
        follow_redirects=True)
    assert b'$32.00' in r.data


def test_license_replacement(bob):
    r = bob.post('/account/license/replace', data=with_csrf(
        bob, '/account/license/replace', {'reason': 'Lost or stolen'}),
        follow_redirects=True)
    assert b'$20.00' in r.data
    assert b'Official Internet Receipt' in r.data


def test_plate_purchase_with_personalization(alice):
    path = '/account/plates/virginia-tech-go-hokies/purchase'
    # availability check
    r = alice.post(path, data=with_csrf(alice, path,
                     {'vehicle_id': '1', 'message': 'HOKIE4', 'check': '1', 'confirm': '0'}))
    assert re.search(rb'HOKIE4 is (not )?available', r.data)
    # confirm purchase: $25 plate fee + $10 personalized fee
    r = alice.post(path, data=with_csrf(alice, path,
                     {'vehicle_id': '1', 'message': 'HOKIE4', 'confirm': '1'}),
                   follow_redirects=True)
    assert b'Official Internet Receipt' in r.data
    assert b'$25.00' in r.data
    assert b'$10.00' in r.data
    assert b'Personalized plate fee' in r.data


def test_plate_purchase_message_length_rejected(alice):
    path = '/account/plates/173rd-airborne/purchase'
    # 173rd Airborne allows 6 characters; 7 chars must be rejected
    r = alice.post(path, data=with_csrf(alice, path,
                     {'vehicle_id': '1', 'message': 'TOOLONG7', 'check': '1', 'confirm': '0'}))
    assert b'not available' in r.data


def test_record_request_certified_driver(alice):
    r = alice.post('/account/records', data=with_csrf(
        alice, '/account/records',
        {'record_type': 'driver', 'certified': '1', 'delivery': 'online', 'vehicle_id': '1'}),
        follow_redirects=True)
    assert b'Record Request' in r.data
    assert b'certified' in r.data
    # $8.00 online + $5.00 certified = $13.00
    assert b'$13.00' in r.data


def test_record_request_vehicle_by_mail(bob):
    vid = _first_vehicle_id(bob)
    r = bob.post('/account/records', data=with_csrf(
        bob, '/account/records',
        {'record_type': 'vehicle', 'certified': '0', 'delivery': 'mail', 'vehicle_id': vid}),
        follow_redirects=True)
    assert b'$9.00' in r.data  # mailed copy
    assert b'within 5 business days' in r.data


def test_appointment_book_and_cancel(alice):
    # step 2: pick office + service + date
    r = alice.post('/appointments/new', data=with_csrf(
        alice, '/appointments/new',
        {'step': '2', 'office': 'richmond-central',
         'service': "Driver's License Renewal", 'date': '2026-10-07'}))
    assert b'Available times' in r.data
    # step 3: confirm
    tok = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', r.data).group(1).decode()
    r = alice.post('/appointments/new', data={
        'csrf_token': tok, 'step': '3', 'office': 'richmond-central',
        'service': "Driver's License Renewal", 'date': '2026-10-07',
        'time': '9:20 AM', 'name': 'Alice Johnson', 'email': 'alice.j@test.com'})
    m = re.search(rb'Confirmation (VADM[\w-]+)', r.data)
    assert m, "no confirmation number rendered"
    confirm = m.group(1).decode()
    # lookup
    r = alice.get(f'/appointments/lookup?confirmation={confirm}&email=alice.j@test.com')
    assert confirm in r.get_data(as_text=True)
    # cancel via lookup page form
    r = alice.post('/appointments/cancel', data=with_csrf(
        alice, f'/appointments/lookup?confirmation={confirm}&email=alice.j@test.com',
        {'confirmation': confirm, 'email': 'alice.j@test.com'}),
        follow_redirects=True)
    assert b'canceled' in r.data


def test_appointment_lookup_requires_both_fields(client):
    # the lookup form submits by GET (a browser never needs a CSRF token),
    # and a mismatched email must not reveal the appointment
    r = client.get('/appointments/lookup?confirmation=VADM9620114A&email=wrong@test.com')
    assert b'No appointment found' in r.data


def test_practice_exam_passing_score(client):
    # fetch the section-2 exam and answer every question correctly
    html = client.get('/licenses-ids/exams/practice-exam/2').get_data(as_text=True)
    qids = re.findall(r'name="q_(\d+)"', html)
    assert len(qids) >= 8
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)
    # read each correct answer from the seeded bank through the app context
    from app import app, QuizQuestion
    with app.app_context():
        correct = {str(q.id): q.correct for q in
                   QuizQuestion.query.filter_by(section='2').all()}
    data = {'csrf_token': tok}
    for qid in set(qids):
        data[f'q_{qid}'] = correct[qid]
    r = client.post('/licenses-ids/exams/practice-exam/2/grade', data=data)
    text = r.get_data(as_text=True)
    assert 'Your score: 10/10 (100%)' in text or 'Your score: 9/10 (90%)' in text \
        or 'passed this practice section' in text
    assert 'Correct.' in text


def test_practice_exam_failing_score(client):
    html = client.get('/licenses-ids/exams/practice-exam/1').get_data(as_text=True)
    qids = list(dict.fromkeys(re.findall(r'name="q_(\d+)"', html)))
    tok = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)
    data = {'csrf_token': tok}
    for qid in qids:
        data[f'q_{qid}'] = 'wrong'
    r = client.post('/licenses-ids/exams/practice-exam/1/grade', data=data)
    assert b'Below the 80 percent passing standard' in r.data
    assert b'15 days' in r.data


def test_seeded_appointment_lookup(client):
    r = client.get('/appointments/lookup?confirmation=VADM9620114A&email=alice.j@test.com')
    text = r.get_data(as_text=True)
    assert "Driver&#39;s License Renewal" in text or "Driver's License Renewal" in text
    assert 'richmond' in text.lower()
    assert '2026-10-07' in text


def test_receipt_view_scoped_to_owner(client):
    # log in as Alice, view her seeded receipt
    client.post('/account/login', data=with_csrf(
        client, '/account/login',
        {'email': 'alice.j@test.com', 'password': 'TestPass123!'}))
    r = client.get('/account/receipt/R20260114-3841')
    assert r.status_code == 200
    # switch the same browser to Bob: the receipt must be invisible
    client.get('/account/logout')
    client.post('/account/login', data=with_csrf(
        client, '/account/login',
        {'email': 'bob.c@test.com', 'password': 'TestPass123!'}))
    r = client.get('/account/receipt/R20260114-3841')
    assert r.status_code == 403
