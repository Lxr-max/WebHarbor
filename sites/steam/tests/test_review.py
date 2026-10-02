import pytest
from conftest import csrf, login

@pytest.mark.parametrize('quantity', ['abc', '0', '-2', '11', '1.5', ''])
def test_invalid_quantity_rejected_without_cart_change(client, quantity):
    app, c = client
    r = c.post('/cart/add', data={'csrf_token': csrf(c, '/app/620/'), 'kind':'game', 'appid':'620', 'qty':quantity})
    assert r.status_code == 400
    with app.app.app_context():
        assert app.CartItem.query.count() == 0

@pytest.mark.parametrize('route', ['/cart/update', '/cart/remove'])
def test_invalid_cart_identifier_returns_client_error(client, route):
    _, c = client
    r = c.post(route, data={'csrf_token':csrf(c, '/app/620/'),'item_id':'bad','qty':'2'})
    assert r.status_code == 400

def test_checkout_rejects_unlisted_payment_method(client):
    app, c = client
    login(c)
    c.post('/cart/add', data={'csrf_token':csrf(c,'/app/620/'),'appid':'620','kind':'game','qty':'1'})
    with app.app.app_context():
        before = app.Order.query.count()
    r = c.post('/checkout/', data={'csrf_token':csrf(c,'/checkout/'), 'full_name':'Alice Jones','email':'alice.j@test.com','address1':'42 Pipeline Way','city':'Bellevue','state':'WA','zipcode':'98004','payment_method':'invalid'})
    assert b'Choose a supported payment method' in r.data
    with app.app.app_context():
        assert app.Order.query.count() == before
        assert app.CartItem.query.count() == 1


def test_news_format_escapes_markup_and_renders_captured_tags(client):
    app, _ = client
    value = str(app._news_format('[p]Update[/p][list][*]Fixed clipping[/*][/list]<script>alert(1)</script>'))
    assert '<p>Update</p>' in value and '<li>Fixed clipping</li>' in value
    assert '<script>' not in value and '&lt;script&gt;' in value
