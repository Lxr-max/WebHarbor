import re
from conftest import login,csrf

def test_tab_buy_defaults_to_requested_device(client):
    A,c=client
    html=c.get('/tablets/galaxy-tab-s11/buy/').get_data(as_text=True)
    assert 'Buy Galaxy Tab S11 (11' in html
    assert 'Model code: SM-X730NZAAXAR' in html

def test_cart_rejects_model_outside_selection(client):
    A,c=client;login(c,'alice.j@test.com')
    path='/smartphones/galaxy-s26-ultra/buy/'
    token=csrf(c,path)
    r=c.post(path,data={'csrf_token':token,'model_code':'SM-X730NZAAXAR','qty':'1'})
    assert r.status_code==400
    with A.app.app_context():assert A.CartItem.query.count()==0

def test_invalid_quantity_is_client_error(client):
    A,c=client;login(c,'alice.j@test.com');path='/smartphones/galaxy-s26-ultra/buy/'
    r=c.post(path,data={'csrf_token':csrf(c,path),'model_code':'SM-S948UZSAXAA','qty':'bad'})
    assert r.status_code==400

def test_warranty_does_not_certify_device(client):
    A,c=client
    html=c.get('/support/warranty/?category=phones-tablets-wearables&model=SM-S948UZVEXAA').get_data(as_text=True)
    assert 'Individual device coverage is not verified' in html
    assert 'Coverage status: Active' not in html

def test_warranty_rejects_wrong_category_model(client):
    A,c=client
    html=c.get('/support/warranty/?category=home-appliances&model=SM-S948UZVEXAA').get_data(as_text=True)
    assert 'class="coverage-card"' not in html
