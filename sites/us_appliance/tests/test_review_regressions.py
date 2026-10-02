import re
from bs4 import BeautifulSoup
import app as m


def test_sale_filter_survives_pagination(client):
    page = BeautifulSoup(client.get('/gas-ranges.html?on_sale=1').data, 'html.parser')
    links = page.select('.pagination a')
    assert links and all('on_sale=1' in x['href'] for x in links)


def test_subcategories_are_reachable(client):
    for parent, child in [('cooking', 'ranges'), ('ranges', 'gas-ranges')]:
        page = BeautifulSoup(client.get('/'+parent+'.html').data, 'html.parser')
        assert page.select_one('.category-children a[href="/'+child+'.html"]')


def test_full_brand_catalog_paginates_and_sorts(client):
    first = BeautifulSoup(client.get('/brand/cafe?sort=priceasc').data, 'html.parser')
    prices = [float(x.text.strip().replace('$','').replace(',','')) for x in first.select('.card .price--now')]
    assert prices == sorted(prices)
    next_link = first.select_one('.pagination a')
    assert next_link and 'sort=priceasc' in next_link['href']
    assert client.get('/brand/cafe'+next_link['href']).status_code == 200


def test_invalid_cart_quantity_does_not_mutate(client):
    with m.app.app_context():
        count = m.CartItem.query.count()
        pid = m.Product.query.filter_by(slug='jgbs66rekss').one().id
    for quantity in ['bad', '-1', '0', '21', '1000000']:
        assert client.post('/cart.php?action=add', data={'product_id':pid, 'qty':quantity}).status_code == 400
    with m.app.app_context():
        assert m.CartItem.query.count() == count


def test_availability_excludes_non_contiguous_destinations(client):
    with m.app.app_context():
        pid = m.Product.query.filter_by(slug='jgbs66rekss').one().id
    for zip_code in ['99501','96762','00901']:
        assert client.post('/availability',data={'product_id':pid,'zip':zip_code}).json['ok'] is False
    assert client.post('/availability',data={'product_id':pid,'zip':'90210'}).json['ok'] is True


def test_order_confirmation_requires_owner(client, alice):
    assert client.get('/order-confirmation/10003').status_code == 404
    assert alice.get('/order-confirmation/10001').status_code == 200


def test_product_shipping_matches_cart_rules(client):
    page = BeautifulSoup(client.get('/jgbs66rekss.html').data,'html.parser')
    assert '$99' in page.select_one('#modal-freeshipp').text
