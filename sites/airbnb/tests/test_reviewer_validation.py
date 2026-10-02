import pytest
from conftest import ab_app as m,with_csrf

@pytest.mark.parametrize('guests',['-2','0','7','abc','1.5'])
def test_invalid_experience_guests(auth_client,guests):
 with m.app.app_context():
  exp=m.Experience.query.first();eid=exp.id;date=exp.offering_list()[0]['iso'];count=m.Booking.query.count()
 r=auth_client.post(f'/experiences/{eid}/book',data=with_csrf(auth_client,f'/experiences/{eid}/book',dict(date=date,guests=guests)))
 assert r.status_code==400
 with m.app.app_context():assert m.Booking.query.count()==count

def test_uncaptured_stay_dates(auth_client):
 with m.app.app_context():lid=m.Listing.query.first().id;count=m.Booking.query.count()
 r=auth_client.post(f'/rooms/{lid}/book',data=with_csrf(auth_client,f'/rooms/{lid}',dict(checkin='2030-01-01',checkout='2030-01-03',adults='2')))
 assert r.status_code==400 and b'not available' in r.data
 with m.app.app_context():assert m.Booking.query.count()==count

@pytest.mark.parametrize('target',['//example.org','https://example.org','/\\example.org'])
def test_login_local_redirect(client,target):
 r=client.post('/login',query_string={'next':target},data=with_csrf(client,'/login',dict(email='alice.j@test.com',password='TestPass123!')))
 assert r.location=='/'

def test_search_keeps_dates(client):
 r=client.get('/s/homes?query=Miami&checkin=2026-12-06&checkout=2026-12-13&adults=3',follow_redirects=True)
 assert b'checkin=2026-12-06' in r.data and b'checkout=2026-12-13' in r.data and b'adults=3' in r.data

def test_experience_dates_visible(client):
 with m.app.app_context():exp=m.Experience.query.first();eid=exp.id;date=exp.offering_list()[0]['iso']
 assert date.encode() in client.get(f'/experiences/{eid}').data

def test_unknown_destination(client):
 assert client.get('/s/homes?query=unknown-town').status_code==404

@pytest.mark.parametrize('price',['nan','inf','-20'])
def test_bad_price_does_not_crash(client,price):
 assert client.get('/s/miami/homes?price_max='+price).status_code==200


def test_repeat_booking_is_idempotent(auth_client):
 with m.app.app_context():
  lst=m.Listing.query.filter_by(destination_slug='asheville').first();lid=lst.id;data=dict(checkin=lst.quote_checkin,checkout=lst.quote_checkout,adults='2')
 first=auth_client.post(f'/rooms/{lid}/book',data=with_csrf(auth_client,f'/rooms/{lid}',data))
 second=auth_client.post(f'/rooms/{lid}/book',data=with_csrf(auth_client,f'/rooms/{lid}',data))
 assert first.status_code==second.status_code==302 and first.location==second.location
