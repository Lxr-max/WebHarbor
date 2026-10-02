import pytest
import app as u
from conftest import with_csrf

@pytest.mark.parametrize('path,data',[
    ('/postcalc/international',{'country':'Japan','weight':'-2'}),
    ('/postcalc/international',{'country':'Japan','weight':'nan'}),
    ('/postcalc/packages',{'zone':'bad','weight':'2'}),
    ('/postcalc/packages',{'zone':'4','weight':'inf'}),
    ('/postcalc/letters',{'shape':'invalid','ounces':'1'}),
    ('/store/cart/add',{'sku':'555304','qty':'abc'}),
])
def test_invalid_numeric_forms(client,path,data):
    assert client.post(path,data=with_csrf(client,'/login',data)).status_code==400


def test_label_requires_completed_wizard(alice):
    with u.app.app_context():before=u.Shipment.query.count()
    assert alice.post('/clicknship/label',data=with_csrf(alice,'/login',{'service':'invalid'})).status_code==400
    with u.app.app_context():assert u.Shipment.query.count()==before


def test_flat_rate_packaging_changes_quotes():
    with u.app.app_context():
        data={'weight_lbs':'30','zone':'8','box_type':'fr-large'}
        assert u._cns_options(data)==[('pm','Priority Mail',34.0)]
        data['box_type']='fr-medium'
        assert u._cns_options(data)==[('pm','Priority Mail',24.8)]


def test_claim_details_private():
    with u.app.app_context():
        claim=u.Claim.query.filter_by(user_id=2).first();number=claim.claim_number
    client=u.app.test_client()
    assert client.get('/claims/'+number).status_code==302
    for email,expected in [('alice.j@test.com',404),('bob.c@test.com',200)]:
        client=u.app.test_client()
        client.post('/login',data=with_csrf(client,'/login',dict(email=email,password='TestPass123!')))
        assert client.get('/claims/'+number).status_code==expected

@pytest.mark.parametrize('end',['2026-10-01','2026-10-02','2026-10-31'])
def test_hold_calendar_limits(carol,end):
    data={'start_date':'2026-10-01','end_date':end,'option':'Hold all mail, deliver on end date'}
    with u.app.app_context():before=u.HoldMailRequest.query.count()
    result=carol.post('/manage/hold-mail/request',data=with_csrf(carol,'/login',data))
    assert 'at most 30 days' in result.text
    with u.app.app_context():assert u.HoldMailRequest.query.count()==before


def test_invalid_claim_shows_error(bob):
    result=bob.post('/claims/file',data=with_csrf(bob,'/login',{'tracking':'unknown','note':'damage'}))
    assert 'Pick one of your insured shipments' in result.text


def test_three_month_reservation_expiry(client):
    payload={'size':'2','period':'3 months'}
    response=client.post('/po-boxes/reserve/boston-ma-02205',data=with_csrf(client,'/login',payload))
    assert 'PO Box Reserved' in response.text
    with u.app.app_context():
        rental=u.PoBoxRental.query.order_by(u.PoBoxRental.id.desc()).first()
        assert rental.expires_on=='2026-12-29'
