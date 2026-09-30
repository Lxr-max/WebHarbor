import re
import pytest
from conftest import cars_app as m, with_csrf

@pytest.mark.parametrize('data',[{'term':'0'},{'term':'-1'},{'vehicle_price':'inf'},{'vehicle_price':'nan'},{'down_payment':'-1'},{'custom_apr':'-1'},{'custom_apr':'21'}])
def test_invalid_financing(client,data):
 r=client.post('/car-loan-calculator/',data=with_csrf(client,'/car-loan-calculator/',{'vehicle_price':'30000','term':'60'}|data))
 assert r.status_code==400 and b'Enter nonnegative' in r.data

def test_zero_apr(client):
 r=client.post('/car-loan-calculator/',data=with_csrf(client,'/car-loan-calculator/',dict(vehicle_price='30000',term='60',custom_apr='0')))
 assert r.status_code==200 and b'0.0%' in r.data and b'$551/mo' in r.data

@pytest.mark.parametrize('target',['//example.org','https://example.org','/\\example.org'])
def test_login_local_redirect(client,target):
 r=client.post('/authn/login',query_string={'next_url':target},data=with_csrf(client,'/authn/login',dict(email='alice.j@test.com',password='TestPass123!')))
 assert r.location=='/profile/your-garage/'

def test_dealer_unknown_sort(client):
 assert client.get('/dealers/?sort=unknown').status_code==200

def test_offer_saved_once_on_submission(bob):
 r=bob.post('/sell/instant-offer/vehicle/',data=with_csrf(bob,'/sell/instant-offer/',dict(year='2021',make='TESLA',model='MODEL 3',trim='LONG RANGE AWD SEDAN ELECTRIC')))
 assert r.status_code==302
 with m.app.app_context():before=m.OfferRequest.query.count()
 r=bob.post('/sell/instant-offer/details/',data=with_csrf(bob,'/sell/instant-offer/details/',dict(mileage='38000',zip='98101',exterior_color='White',keys='1',original_owner='Yes',payments='No')))
 assert r.status_code==302
 for _ in range(3):assert bob.get(r.location).status_code==200
 with m.app.app_context():assert m.OfferRequest.query.count()==before+1

@pytest.mark.parametrize('year',['abc','-1','999999999999999999999999'])
def test_invalid_offer_year(client,year):
 r=client.post('/sell/instant-offer/vehicle/',data=with_csrf(client,'/sell/instant-offer/',dict(year=year,make='TESLA',model='MODEL 3',trim='LONG RANGE AWD SEDAN ELECTRIC')))
 assert r.status_code==400

@pytest.mark.parametrize('query',['list_price_min=oops&mileage_max=100','mileage_max=-1','maximum_distance=9999999999999999999999'])
def test_invalid_search_filters(client,query):
 assert client.get('/shopping/results/?'+query).status_code==400
