import pytest
from conftest import wanderlog_app as m, with_csrf

@pytest.mark.parametrize('amount',['inf','NaN','-1','0.001'])
def test_expense_invalid_amount(alice,amount):
    with m.app.app_context():before=m.Expense.query.count()
    alice.post('/plan/parisinspring/budget',data=with_csrf(alice,'/plan/parisinspring/budget',dict(description='Bad',amount=amount,paid_by='17',category='Food')))
    with m.app.app_context():assert m.Expense.query.count()==before

def test_expense_split_rejects_outsider(alice):
    with m.app.app_context():before=m.Expense.query.count()
    alice.post('/plan/parisinspring/budget',data=with_csrf(alice,'/plan/parisinspring/budget',dict(description='Bad',amount='10',paid_by='17',category='Food',split_among=['999'])))
    with m.app.app_context():assert m.Expense.query.count()==before

def test_invalid_settings_atomic(alice):
    with m.app.app_context():
        t=m.Trip.query.filter_by(edit_key='parisinspring').one();before=(t.title,t.privacy,t.start_date,t.end_date)
    alice.post('/plan/parisinspring/settings',data=with_csrf(alice,'/plan/parisinspring/settings',dict(title='Changed',privacy='private',start_date='2026-11-02',end_date='2026-10-01')))
    with m.app.app_context():
        t=m.Trip.query.filter_by(edit_key='parisinspring').one();assert (t.title,t.privacy,t.start_date,t.end_date)==before


def test_duplicate_trip_names_allowed(alice):
    with m.app.app_context():geo=m.Geo.query.first().id
    data=dict(title='Weekend away',geo_id=str(geo),start_date='2026-11-01',end_date='2026-11-02',travelers='2')
    for _ in range(2):
        response=alice.post('/plan/new',data=with_csrf(alice,'/plan/new',data))
        assert response.status_code==302
    with m.app.app_context():assert m.Trip.query.filter_by(title='Weekend away').count()==2
