import pytest
from html import unescape
from conftest import ds_app, with_csrf

@pytest.mark.parametrize('url',['/movies','/shows','/shop/toys','/parks/attractions','/live-shows/disney-on-ice'])
def test_invalid_pagination(client,url):
    assert client.get(url+'?page=abc').status_code == 400
    assert client.get(url+'?page=99999').status_code == 200

@pytest.mark.parametrize('target',['//example.org','https://example.org','/\\example.org'])
def test_local_return(target):
    assert ds_app.local_return(target) == '/'

@pytest.mark.parametrize('quantity',['abc','-1','100'])
def test_bad_bag_quantity(client,quantity):
    assert client.post('/bag/add',data=with_csrf(client,'/login',{'pid':'none','qty':quantity})).status_code == 400

def test_guest_bag_survives_login(client):
    product=ds_app.Product.query.first()
    client.post('/bag/add',data=with_csrf(client,'/login',{'pid':product.pid,'qty':2}))
    client.post('/login',data=with_csrf(client,'/login',{'email':'alice.j@test.com','password':'TestPass123!'}))
    assert product.name in unescape(client.get('/bag').get_data(as_text=True))

def test_favorite_label_reflects_state(alice_client):
    row=ds_app.Favorite.query.filter_by(user_id=1,item_type='movie').first()
    assert b'Remove from Favorites' in alice_client.get('/movies/'+row.item_key).data
