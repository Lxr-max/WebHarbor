import json
import pytest
import app as z
from conftest import with_csrf

@pytest.fixture(autouse=True)
def fresh_seed():
    with z.app.app_context():
        z.db.drop_all()
    z.main()


def test_anonymous_cannot_edit_account_bag(client):
    with z.app.app_context():
        row = z.CartItem.query.filter_by(user_id=1).first()
        ident, quantity = row.id, row.quantity
    for action in ('update', 'remove'):
        response = client.post('/us/en/shop/update', data=with_csrf(client, '/', {'item':ident,'action':action,'quantity':3}))
        assert response.status_code == 403
    with z.app.app_context():
        assert z.db.session.get(z.CartItem, ident).quantity == quantity

@pytest.mark.parametrize('value', ['bad','0','-1','1.5','100'])
def test_invalid_quantity_does_not_write(client, value):
    data={'product':'08100038','color':1,'size':1,'quantity':value}
    assert client.post('/us/en/shop/add',data=with_csrf(client,'/',data)).status_code==400
    with z.app.app_context():
        assert z.CartItem.query.filter_by(user_id=None).count()==0

@pytest.mark.parametrize('availability,expected',[('coming_soon',400),('low_on_stock',302)])
def test_stock_availability(client,availability,expected):
    with z.app.app_context():
        size=z.Size.query.filter_by(availability=availability).first()
        data=dict(product=size.color.product.seo_id,color=size.color.id,size=size.id)
    assert client.post('/us/en/shop/add',data=with_csrf(client,'/',data)).status_code==expected


def test_guest_bag_survives_login(client):
    client.post('/us/en/shop/add',data=with_csrf(client,'/',dict(product='08100038',color=1,size=1)))
    client.post('/us/en/logon',data=with_csrf(client,'/',dict(email='alice.j@test.com',password='TestPass123!')))
    with z.app.app_context():
        assert z.CartItem.query.filter_by(user_id=None).count()==0
        assert z.CartItem.query.filter_by(user_id=1,product_id=578162617).one().quantity==2


def test_unavailable_combination_excluded(client):
    # Black printed jeans have no purchasable sizes; blue sizes must not satisfy the black filter.
    page=client.get('/us/en/man-jeans-l659.html?color=Black&size=30+(US+30)').text
    assert 'PRINTED LOOSE FIT JEANS' not in page


def test_selected_color_has_own_gallery(client):
    red=client.get('/us/en/elongated-shoulder-bag-p16821710.html?v1=600').text
    assert 'p16821710-c600-gal0.jpg' in red
    assert 'p16821710-gal0.jpg' not in red.split('<div class="pdp-colors">')[0]


def test_checkout_defaults_and_address_radio_group(alice):
    alice.post('/us/en/account/addresses/2/default',data=with_csrf(alice,'/',{}))
    page=alice.get('/us/en/shop/checkout').text
    assert 'name="address_id" value="2"' in page
    assert 'name="new_address"' not in page
    assert page.index('value="2"') < page.index('value="1"')
