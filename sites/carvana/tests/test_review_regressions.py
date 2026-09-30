import pytest
import app as cv
from conftest import with_csrf


def test_monthly_filter_matches_displayed_estimates():
    with cv.app.app_context():
        expected = {v.id for v in cv.Vehicle.query if round(v.monthly_payment()) <= 500}
        actual = {v.id for v in cv._search({'payment_max': '500'})}
        assert actual == expected
        assert actual


@pytest.mark.parametrize('data', [
    {'down_payment': '-1'}, {'down_payment': 'oops'},
    {'down_payment': '999999999'}, {'term': '1'}, {'credit_tier': 'invalid'},
])
def test_estimator_rejects_invalid_configuration(client, data):
    r = client.post('/vehicle/4255570/payment-estimate', data=with_csrf(
        client, '/vehicle/4255570', data))
    assert r.status_code == 400


def test_trade_credit_reduces_saved_payment(alice, bob):
    with cv.app.app_context():
        occupied = {o.vehicle_id for o in cv.Order.query if o.status != 'Cancelled'}
        v = next(v for v in cv.Vehicle.query if v.id not in occupied and v.price > 10000)
        vid = v.vehicle_id
        expected = round(v.monthly_payment(down_payment=2500, trade_credit=5000,
                                           term=60, apr_percent=6.24))
    path = f'/vehicle/{vid}/checkout'
    data = {'payment_type': 'finance', 'down_payment': '2500', 'term': '60',
            'credit_tier': 'great', 'trade_in': 'yes', 'trade_credit': '5000',
            'delivery_date': '2026-09-30', 'delivery_slot': '8:00 AM - 10:00 AM',
            'street': '123 Test St', 'city': 'Seattle', 'state': 'WA', 'zip': '98101'}
    r = alice.post(path, data=with_csrf(alice, path, data))
    assert r.status_code == 302
    with cv.app.app_context():
        order = cv.Order.query.filter_by(vehicle_id=v.id).first()
        assert order.monthly_payment == expected
        assert order.trade_credit == 5000
    assert bob.post(path, data=with_csrf(bob, path, data)).status_code == 409


@pytest.mark.parametrize('vin', ['123456789AB', '1HGCM82633A004352X'])
def test_offer_requires_exact_vin_length(client, vin):
    r = client.post('/sell-my-car/offer', data=with_csrf(client, '/sell-my-car/offer',
        {'vin': vin, 'mileage': '10000', 'condition': 'good'}))
    assert b'Enter the full VIN' in r.data


def test_content_pages_do_not_read_source_json(client, monkeypatch):
    monkeypatch.setattr(cv, '_load', lambda _: pytest.fail('Runtime JSON read'))
    assert client.get('/financing').status_code == 200


def test_save_get_does_not_mutate(alice):
    with cv.app.app_context():
        before = cv.Favorite.query.count()
    assert alice.get('/vehicle/4255570/favorite').status_code == 302
    with cv.app.app_context():
        assert cv.Favorite.query.count() == before


def test_unavailable_vehicle_facts_are_not_invented(client):
    with cv.app.app_context():
        sparse = cv.Vehicle.query.filter_by(vehicle_id=4599463).one()
        assert sparse.city is None and sparse.state is None
        assert sparse.mpg_combined is None
    body = client.get('/vehicle/4599463').text
    assert 'Vehicle location not provided' in body
    assert 'Auburn' not in body
    leaf = client.get('/vehicle/4452259').text
    assert 'MPGe (combined)</span>—' in leaf
    assert 'MPGe (combined)</span>27' not in leaf


def test_estimate_configuration_survives_checkout(alice):
    body = alice.get('/vehicle/4255570/checkout?down_payment=5000&term=60&credit_tier=great').text
    assert 'value="5000"' in body
    assert '<option value="60" selected' in body
    assert '<option value="great" selected' in body
