"""Reviewer regressions: payments, order ownership, configuration and plan caps."""
from decimal import Decimal
import pytest
from conftest import verizon_app as m, csrf_from


def post(client, path, data):
    token = csrf_from(client.get(path).get_data(as_text=True))
    return client.post(path, data=dict(data, csrf_token=token), follow_redirects=True)


@pytest.mark.parametrize('amount', ['-1', '0', 'nan', 'inf', 'nonsense', '0.001', '99999999'])
def test_invalid_payments_do_not_change_bill(alice, amount):
    with m.app.app_context():
        before = m.Payment.query.count()
        bill = m.Bill.query.filter_by(user_id=1, status='unpaid').first()
        bid = bill.id if bill else m.Bill.query.filter_by(user_id=1).order_by(m.Bill.id.desc()).first().id
        old = m.db.session.get(m.Bill, bid).status
    post(alice, '/account/pay/', {'amount': amount, 'method': 'Bank account (ACH ending 8891)'})
    with m.app.app_context():
        assert m.Payment.query.count() == before
        assert m.db.session.get(m.Bill, bid).status == old


def test_partial_payment_and_remaining_balance(alice):
    with m.app.app_context():
        bill = m.Bill.query.filter_by(user_id=1).filter(m.Bill.status != 'paid').order_by(m.Bill.id.desc()).first()
        bid, total = bill.id, Decimal(bill.total)
    post(alice, '/account/pay/', {'amount': '50', 'method': 'Bank account (ACH ending 8891)'})
    with m.app.app_context(): assert m.db.session.get(m.Bill, bid).status == 'partial'
    assert f'{total - 50:.2f}' in alice.get('/account/pay/').get_data(as_text=True)
    post(alice, '/account/pay/', {'amount': str(total - 50), 'method': 'Bank account (ACH ending 8891)'})
    with m.app.app_context(): assert m.db.session.get(m.Bill, bid).status == 'paid'


def test_private_order_not_public(client, alice):
    with m.app.app_context():
        order = m.Order.query.filter_by(user_id=2).first()
        path = '/order/' + order.confirmation + '/'
    assert client.get(path).status_code == 403
    assert alice.get(path).status_code == 403


@pytest.mark.parametrize('field,value', [('color','invented'),('storage','999 TB'),('term','-1'),('plan','bad'),('protection','free')])
def test_configure_rejects_unknown_options(client, field, value):
    with m.app.app_context():
        d=m.Device.query.first(); slug=d.slug
        data=dict(color=d.colors_list()[0],storage=d.storage_list()[0],term='36')
    data[field]=value
    post(client,f'/smartphones/{slug}/configure',data)
    with m.app.app_context(): assert m.Cart.query.count() == 0


def test_upfront_order_price_and_session_owner(client):
    with m.app.app_context():
        d=m.Device.query.first(); slug=d.slug; price=d.full_price
    post(client,f'/smartphones/{slug}/configure',{'term':'full'})
    response=post(client,'/checkout/',dict(name='Test Buyer',email='buyer@example.com',street='1 Main St',city='Seattle',state='WA',zip='98101'))
    with m.app.app_context():
        order=m.Order.query.order_by(m.Order.id.desc()).first()
        assert Decimal(order.total_today)==Decimal(price.replace(',',''))
        path=f'/order/{order.confirmation}/'
    assert response.status_code==200
    assert m.app.test_client().get(path).status_code==403


def test_plan_allowances_match_plan(dana):
    with m.app.app_context():
        line=m.Line.query.filter_by(user_id=4).first(); lid=line.id
        unlimited=m.Plan.query.filter_by(name='Unlimited').one(); pid=unlimited.id
    post(dana,f'/account/lines/{lid}/change-plan',{'plan':str(pid)})
    with m.app.app_context():
        usage=m.Usage.query.filter_by(line_id=lid).one()
        assert usage.data_cap_gb is None
        assert usage.hotspot_cap_gb=='5'
