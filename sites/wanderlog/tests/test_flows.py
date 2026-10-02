"""Flow tests: the trip planner's itinerary, map, checklist, budget,
collaboration and sharing surfaces, exercised with CSRF on."""
import re

from conftest import with_csrf

import app as wl


def _csrf(client, path):
    r = client.get(path)
    assert r.status_code == 200
    return re.search(r'name="csrf_token"[^>]*value="([^"]+)"',
                     r.get_data(as_text=True)).group(1)


# ---------------------------------------------------------------- itinerary --

def test_planner_shows_seeded_days(alice):
    body = alice.get('/plan/parisinspring').get_data(as_text=True)
    assert 'Day 1 · Apr 10' in body
    assert 'Day 4 · Apr 13' in body
    assert "Musée d'Orsay" in body.replace('&#39;', "'")
    assert 'Invite by email' in body
    assert 'Bob Chen' in body


def test_add_place_to_itinerary(alice):
    body = alice.get('/plan/parisinspring/add?q=arc').get_data(as_text=True)
    assert 'Arc de Triomphe' in body
    pid = re.search(r'name="place_id" value="(\d+)"', body).group(1)
    sec = re.search(r'<select id="section-\d+" name="section_id"[^>]*>\s*'
                    r'<option value="(\d+)"', body).group(1)
    r = alice.post('/plan/parisinspring/entry', data={
        'csrf_token': _csrf(alice, '/plan/parisinspring/add?q=arc'),
        'place_id': pid, 'section_id': sec,
        'note': 'Rooftop view at sunset', 'start_time': '18:00',
        'duration': '60'})
    assert r.status_code == 302
    body = alice.get('/plan/parisinspring').get_data(as_text=True)
    assert 'Rooftop view at sunset' in body


def test_reorder_and_remove_stops(alice):
    body = alice.get('/plan/parisinspring').get_data(as_text=True)
    move = re.search(r'action="/plan/entry/(\d+)/move"', body).group(1)
    tok = _csrf(alice, '/plan/parisinspring')
    r = alice.post(f'/plan/entry/{move}/move', data={'csrf_token': tok,
                                                     'delta': '1'})
    assert r.status_code == 302
    r = alice.post(f'/plan/entry/{move}/remove',
                   data={'csrf_token': _csrf(alice, '/plan/parisinspring')})
    assert r.status_code == 302
    body = alice.get('/plan/parisinspring').get_data(as_text=True)
    assert 'Place removed from the itinerary.' in body


def test_map_view_shows_pins_and_distances(alice):
    body = alice.get('/plan/parisinspring/map').get_data(as_text=True)
    assert '<svg' in body
    assert 'Distances between stops' in body
    legs = re.findall(r'([\d.]+) km · ([\d.]+) mi', body)
    assert len(legs) >= 3


def test_create_trip_flow(alice):
    body = alice.get('/plan/new?q=kyoto').get_data(as_text=True)
    assert 'Kyoto' in body
    gid = re.search(r'href="/plan/new\?geo_id=(\d+)', body).group(1)
    tok = _csrf(alice, f'/plan/new?geo_id={gid}')
    r = alice.post('/plan/new', data={
        'csrf_token': tok, 'geo_id': gid, 'title': 'Kyoto Temples',
        'start_date': '2026-12-10', 'end_date': '2026-12-12',
        'travelers': '2'})
    assert r.status_code == 302
    body = alice.get('/plans').get_data(as_text=True)
    assert 'Kyoto Temples' in body
    with wl.app.app_context():
        trip = wl.Trip.query.filter_by(title='Kyoto Temples').first()
        assert trip is not None
        assert wl.TripSection.query.filter_by(trip_id=trip.id).count() == 3


# ---------------------------------------------------------------- checklist --

def test_checklist_add_toggle_delete(alice):
    tok = _csrf(alice, '/plan/parisinspring/checklist')
    r = alice.post('/plan/parisinspring/checklist', data={
        'csrf_token': tok, 'text': 'Download the metro map',
        'list_type': 'todo'})
    assert r.status_code == 302
    body = alice.get('/plan/parisinspring/checklist').get_data(as_text=True)
    assert 'Download the metro map' in body
    assert 'Passport valid for 6+ months' in body
    # the new item's own row (not the first seeded item)
    row = re.search(r'checklist-item[^>]*>.*?Download the metro map', body, re.S)
    start = body.rfind('checklist-item', 0, body.find('Download the metro map'))
    iid = re.search(r'action="/plan/checklist/(\d+)/toggle"',
                    body[start:]).group(1)
    r = alice.post(f'/plan/checklist/{iid}/toggle',
                   data={'csrf_token': _csrf(alice,
                                             '/plan/parisinspring/checklist')})
    assert r.status_code == 302
    r = alice.post(f'/plan/checklist/{iid}/delete',
                   data={'csrf_token': _csrf(alice,
                                             '/plan/parisinspring/checklist')})
    assert r.status_code == 302
    body = alice.get('/plan/parisinspring/checklist').get_data(as_text=True)
    assert 'Download the metro map' not in body


# ------------------------------------------------------------------- budget --

def test_budget_math_and_expense_flow(alice):
    body = alice.get('/plan/parisinspring/budget').get_data(as_text=True)
    # seeded totals: $1,936.70 across 5 expenses
    assert '$1,936.70' in body
    # settlement: Bob owes Alice $735.85
    flat = ' '.join(body.split())
    assert re.search(r'Bob Chen<[^>]+> owes', body)
    assert '$735.85' in body
    alice_id = re.search(r'<select id="paid_by" name="paid_by">\s*'
                         r'<option value="(\d+)"', body).group(1)
    r = alice.post('/plan/parisinspring/budget', data={
        'csrf_token': _csrf(alice, '/plan/parisinspring/budget'),
        'description': 'Seine river cruise', 'amount': '42.50',
        'category': 'Activities', 'paid_by': alice_id,
        'date': '2027-04-12', 'split_among': [alice_id]})
    assert r.status_code == 302
    body = alice.get('/plan/parisinspring/budget').get_data(as_text=True)
    assert 'Seine river cruise' in body
    assert '$1,979.20' in body  # 1936.70 + 42.50


def test_expense_delete(alice):
    body = alice.get('/plan/parisinspring/budget').get_data(as_text=True)
    eid = re.search(r'action="/plan/expense/(\d+)/delete"', body).group(1)
    r = alice.post(f'/plan/expense/{eid}/delete',
                   data={'csrf_token': _csrf(alice,
                                             '/plan/parisinspring/budget')})
    assert r.status_code == 302
    body = alice.get('/plan/parisinspring/budget').get_data(as_text=True)
    assert 'Expense deleted.' in body


def test_budget_rejects_bad_amount(alice):
    r = alice.post('/plan/parisinspring/budget', data={
        'csrf_token': _csrf(alice, '/plan/parisinspring/budget'),
        'description': 'Not a number', 'amount': 'abc',
        'category': 'Food', 'paid_by': '1'})
    assert r.status_code == 302
    body = alice.get('/plan/parisinspring/budget').get_data(as_text=True)
    assert 'Enter a valid amount with at most two decimal places, date, category and trip members.' in body


# ------------------------------------------------------------ collaboration --

def test_invite_accept_decline_flow(alice, carol):
    r = alice.post('/plan/parisinspring/collaborators', data={
        'csrf_token': _csrf(alice, '/plan/parisinspring'),
        'email': 'carol.d@test.com'})
    assert r.status_code == 302
    body = alice.get('/plan/parisinspring').get_data(as_text=True)
    assert 'Invitation sent to Carol Davis.' in body
    assert 'Pending' in body

    body = carol.get('/plans').get_data(as_text=True)
    assert 'Trip invitations' in body
    cid = re.search(r'action="/plan/invite/(\d+)"', body).group(1)
    r = carol.post(f'/plan/invite/{cid}', data={
        'csrf_token': _csrf(carol, '/plans'), 'action': 'accept'})
    assert r.status_code == 302
    body = carol.get('/plans').get_data(as_text=True)
    assert 'Shared with me' in body
    # carol can now open the planner
    r = carol.get('/plan/parisinspring')
    assert r.status_code == 200


def test_invite_unknown_email_rejected(alice):
    r = alice.post('/plan/parisinspring/collaborators', data={
        'csrf_token': _csrf(alice, '/plan/parisinspring'),
        'email': 'nobody@nowhere.example'})
    body = alice.get('/plan/parisinspring').get_data(as_text=True)
    assert 'No Wanderlog account found for that email.' in body


def test_owner_can_remove_collaborator(alice):
    body = alice.get('/plan/parisinspring').get_data(as_text=True)
    cid = re.search(r'action="/plan/collaborator/(\d+)/remove"', body)
    assert cid, 'no removable collaborator on the seeded trip'
    r = alice.post(f'/plan/collaborator/{cid.group(1)}/remove',
                   data={'csrf_token': _csrf(alice, '/plan/parisinspring')})
    assert r.status_code == 302
    body = alice.get('/plan/parisinspring').get_data(as_text=True)
    assert 'Collaborator removed.' in body


# ------------------------------------------------------------------ sharing --

def test_privacy_change_controls_anonymous_access(alice, client):
    # private trip is hidden
    r = client.get('/trip/nycfoodcrawlv')
    assert r.status_code == 302
    # carol switches her trip to link
    r = alice.get('/plan/tokyowkend/settings')
    tok = _csrf(alice, '/plan/tokyowkend/settings')
    r = alice.post('/plan/tokyowkend/settings', data={
        'csrf_token': tok, 'title': 'Tokyo Weekend',
        'start_date': '2026-10-17', 'end_date': '2026-10-18',
        'privacy': 'link', 'travelers': '1'})
    assert r.status_code == 302
    r = client.get('/trip/tokyowkendv')
    assert r.status_code == 200
    assert 'Tokyo Weekend' in r.get_data(as_text=True)


def test_public_trip_listed_on_profile(alice, client):
    body = client.get('/u/dana.k').get_data(as_text=True)
    assert 'Rome Essentials' in body
    assert 'Public trips' in body


def test_shared_view_shows_members_and_budget(client):
    body = client.get('/trip/romeessentv').get_data(as_text=True)
    assert 'Dana Kim' in body
    assert 'Alice Johnson' in body
    assert '$1,556.00' in body  # 1410 + 52 + 94


def test_settings_rename_and_dates(alice):
    tok = _csrf(alice, '/plan/parisinspring/settings')
    r = alice.post('/plan/parisinspring/settings', data={
        'csrf_token': tok, 'title': 'Paris in the Spring!',
        'start_date': '2027-04-10', 'end_date': '2027-04-14',
        'privacy': 'link', 'travelers': '2'})
    assert r.status_code == 302
    body = alice.get('/plan/parisinspring').get_data(as_text=True)
    assert 'Paris in the Spring!' in body
    with wl.app.app_context():
        trip = wl.Trip.query.filter_by(edit_key='parisinspring').first()
        assert trip.end_date == '2027-04-14'
        assert wl.TripSection.query.filter_by(trip_id=trip.id).count() == 5
