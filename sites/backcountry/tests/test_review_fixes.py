import pytest
from conftest import bc_app, with_csrf

@pytest.mark.parametrize('url',['/cat/ski?price-min=nan','/cat/ski?price-max=inf','/cat/ski?price-min=-1'])
def test_bad_prices_fail_cleanly(client,url):
    assert client.get(url).status_code == 400

def test_anonymous_cannot_change_account_cart(client):
    response=client.post('/cart/update',data=with_csrf(client,'/login',{'item':1,'quantity':3}))
    assert response.status_code == 403

@pytest.mark.parametrize('quantity',['abc','-1','0','999999999'])
def test_invalid_cart_quantity(client,quantity):
    response=client.post('/cart/add',data=with_csrf(client,'/login',{'sku':'BAGZ2GN-TAN-ONESIZ','quantity':quantity}))
    assert response.status_code == 400

@pytest.mark.parametrize('target',['//example.org','https://example.org','/\\example.org'])
def test_local_return(target):
    assert bc_app.local_return(target) == '/'

def test_search_sort_keeps_query(client):
    response=client.get('/search?q=tent')
    assert b'name="q" value="tent"' in response.data

def test_filter_switch_preserves_price(client):
    response=client.get('/cat/ski?price-min=100&price-max=200')
    assert b'price-min=100&amp;price-max=200&amp;color=black' in response.data


def test_womens_gender_does_not_match_mens_substring():
    from types import SimpleNamespace
    assert bc_app.product_gender(SimpleNamespace(title="Jacket - Women's")) == 'female'
    assert bc_app.product_gender(SimpleNamespace(title="Jacket - Men's")) == 'male'
