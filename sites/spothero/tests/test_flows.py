"""Stateful flows: auth, reservations (extend/cancel), payment methods,
favorites, profile persistence, and guest checkout."""
import re

from conftest import login


def _auth_flow(client, app):
    return login(app, 'alice.j@test.com')


def test_login_logout(client, app):
    authed = login(app, 'alice.j@test.com')
    body = authed.get('/account').get_data(as_text=True)
    assert 'Hi, Alice!' in body
    authed.get('/auth/logout')
    response = authed.get('/account')
    assert response.status_code == 302, 'account must re-gate after logout'


def test_guest_booking_persists(client):
    response = client.post('/purchase/hourly?facility=2348'
                           '&starts=2026-10-03T12:00&ends=2026-10-03T18:00',
                           data={'email': 'guest.check@example.com',
                                 'creditCardName': 'Guest Check'})
    assert response.status_code in (302, 303)
    confirm = client.get(response.headers['Location'])
    body = confirm.get_data(as_text=True)
    code = re.search(r'SH-[A-Z0-9]{6}', body).group(0)
    assert code
    text = re.sub(r'<[^>]+>', ' ', body)
    assert re.search(r'Total paid\s*\$[\d.]+', text)


def test_extend_reservation(app):
    authed = login(app, 'alice.j@test.com')
    body = authed.get('/account').get_data(as_text=True)
    code = re.search(r'SH-[A-Z0-9]{6}', body).group(0)
    detail = authed.get(f'/account/reservations/{code}').get_data(as_text=True)
    old_total = float(re.search(
        r'Total paid\s*\$([\d.]+)', re.sub(r'<[^>]+>', ' ', detail)).group(1))
    response = authed.post(f'/account/reservations/{code}/extend', data={'hours': 2})
    assert response.status_code in (302, 303)
    after = authed.get(f'/account/reservations/{code}').get_data(as_text=True)
    new_total = float(re.search(
        r'Total paid\s*\$([\d.]+)', re.sub(r'<[^>]+>', ' ', after)).group(1))
    assert new_total > old_total, 'extending must increase the total'
    assert 'extended by 2' in after


def test_cancel_reservation(app):
    authed = login(app, 'david.k@test.com')
    body = authed.get('/account').get_data(as_text=True)
    code = re.search(r'SH-[A-Z0-9]{6}', body).group(0)
    response = authed.post(f'/account/reservations/{code}/cancel')
    assert response.status_code in (302, 303)
    after = authed.get(f'/account/reservations/{code}').get_data(as_text=True)
    assert 'canceled' in after.lower()
    assert 'Refunds are issued to the original payment method' in after


def test_payment_method_default_flow(app):
    authed = login(app, 'carol.d@test.com')
    # add a card: not her first, so it must NOT auto-become the default
    authed.post('/account/payment-methods',
                data={'action': 'add', 'brand': 'Visa',
                      'number': '4242424242424242',
                      'exp_month': 9, 'exp_year': 2029})
    body = authed.get('/account/payment-methods').get_data(as_text=True)
    rows = re.findall(r'<tr>(.*?)</tr>', body, re.S)
    row4242 = [r for r in rows if '4242' in r][0]
    assert 'Default' not in row4242, 'later cards must wait for an explicit default'
    # "Make default" buttons carry an accessible name that identifies the card
    assert re.search(r'aria-label="Make Visa ending in 4242 the default', row4242)
    pm_id = re.search(r'name="id" value="(\d+)"', row4242).group(1)
    authed.post('/account/payment-methods',
                data={'action': 'default', 'id': pm_id})
    body = authed.get('/account/payment-methods').get_data(as_text=True)
    rows = re.findall(r'<tr>(.*?)</tr>', body, re.S)
    row4242 = [r for r in rows if '4242' in r][0]
    assert 'Default' in row4242, 'the new card must now be the default'
    assert 'Make default' not in row4242, 'default card has no default button'


def test_remove_payment_method(app):
    authed = login(app, 'carol.d@test.com')
    body = authed.get('/account/payment-methods').get_data(as_text=True)
    rows = re.findall(r'<tr>(.*?)</tr>', body, re.S)
    row6742 = [r for r in rows if '6742' in r][0]
    assert re.search(r'aria-label="Remove Mastercard ending in 6742', row6742)
    pm_id = re.search(r'name="id" value="(\d+)"', row6742).group(1)
    authed.post('/account/payment-methods',
                data={'action': 'delete', 'id': pm_id})
    after = authed.get('/account/payment-methods').get_data(as_text=True)
    assert '6742' not in re.sub(r'<[^>]+>', ' ', after), \
        'removed card must disappear'


def test_profile_persistence(app):
    authed = login(app, 'bob.c@test.com')
    authed.post('/account/profile',
                data={'license_plate': 'WI-BO1180',
                      'vehicle': 'Honda CR-V Hybrid',
                      'phone': '312-555-0121'})
    authed.get('/auth/logout')
    relogged = login(app, 'bob.c@test.com')
    body = relogged.get('/account/profile').get_data(as_text=True)
    assert 'WI-BO1180' in body and 'Honda CR-V Hybrid' in body


def test_favorites_add_remove(app):
    authed = login(app, 'alice.j@test.com')
    # 129876 (the Wrigley lot) is not among Alice's seeded favorites
    body = authed.get('/account/favorites').get_data(as_text=True)
    assert '1075 W Addison' not in body
    authed.post('/account/favorites', data={'facility_id': 129876})
    body = authed.get('/account/favorites').get_data(as_text=True)
    assert '1075 W Addison' in body
    # remove it again
    authed.post('/account/favorites', data={'facility_id': 129876})
    body = authed.get('/account/favorites').get_data(as_text=True)
    assert '1075 W Addison' not in body


def test_facility_page_height_note(client):
    """The clearance note must render in the upstream format (H' I\")."""
    body = client.get('/facility/16130').get_data(as_text=True)
    text = re.sub(r'<[^>]+>', ' ', body)
    assert re.search(r"Height Restriction: 7' 1\"", text), \
        'the 85-inch clearance must render as 7\' 1"'


def test_static_pages_from_db(client):
    """Static pages must render from the seeded DB, not request-time JSON."""
    body = client.get('/about/parking-guarantee').get_data(as_text=True)
    assert 'Parking Guarantee' in body
    assert '&amp;nbsp;' not in body, 'HTML entities must be decoded'
