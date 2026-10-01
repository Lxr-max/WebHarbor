"""Reviewer regressions; no external evidence directory required."""
import re
from urllib.parse import urlsplit, parse_qs
import pytest
import app as site

@pytest.mark.parametrize('target', ['https://example.org/', '//example.org/', '/\\example.org/', '/%2fexample.org/', '/%5cexample.org/', '/%0d%0aLocation:https://example.org/'])
def test_external_continuations_stay_local(target):
    with site.app.test_request_context('/'):
        assert site.local_redirect(target, '/').location == '/'

@pytest.mark.parametrize('target', ['/papers?q=hello', '/account', '/search/publ?year=2026&type=article'])
def test_internal_continuations_survive(target):
    with site.app.test_request_context('/'):
        assert site.local_redirect(target, '/').location == target

def test_unknown_favorite_rejected(alice, csrf):
    html = alice.get('/account').get_data(as_text=True)
    response = alice.post('/favorites/toggle', data={'csrf_token':csrf(html), 'kind':'film', 'slug':'not-a-real-film'})
    assert response.status_code == 404


def test_cart_update_form_has_valid_owner(alice, csrf):
    from bs4 import BeautifulSoup
    with site.app.app_context():
        variant = site.ShopVariant.query.filter_by(available=True).first()
        variant_id = variant.id
    html = alice.get('/account').get_data(as_text=True)
    alice.post('/cart/add', data={'csrf_token':csrf(html), 'variant_id':variant_id,'quantity':1})
    soup = BeautifulSoup(alice.get('/cart').get_data(as_text=True), 'html.parser')
    update = next(b for b in soup.select('button') if b.get_text(strip=True)=='Update')
    form = soup.find('form', id=update['form'])
    assert form['action']=='/cart/update'
    assert form.select_one('input[name=quantity]') and form.select_one('input[name=item_id]')


def test_checkout_persists_shipping_address(alice, csrf):
    with site.app.app_context():
        variant_id = site.ShopVariant.query.filter_by(available=True).first().id
    html = alice.get('/account').get_data(as_text=True)
    alice.post('/cart/add', data={'csrf_token':csrf(html), 'variant_id':variant_id, 'quantity':2})
    html = alice.get('/shop/checkout').get_data(as_text=True)
    response = alice.post('/shop/checkout', data={'csrf_token':csrf(html), 'ship_name':'Alice Johnson', 'ship_email':'alice.j@test.com', 'address':'1 Main St', 'city':'Seattle', 'zip':'98101'}, follow_redirects=True)
    assert response.status_code == 200 and '1 Main St' in response.get_data(as_text=True)
    with site.app.app_context():
        order = site.ShopOrder.query.order_by(site.ShopOrder.id.desc()).first()
        assert (order.ship_address, order.ship_city, order.ship_zip) == ('1 Main St', 'Seattle', '98101')
        assert len(order.lines) == 1 and order.lines[0].quantity == 2


def test_sugarfree_missing_quantity_is_explicit(alice):
    with site.app.app_context():
        product = site.Product.query.filter(site.Product.name.like('%Summer%Sugarfree%')).first()
        slug = product.slug
    # Use the site's actual detail endpoint independently of spelling changes.
    with site.app.test_request_context('/'):
        from flask import url_for
        path = url_for('product_detail', slug=slug)
    html = alice.get(path).get_data(as_text=True)
    assert 'Sugarfree; exact quantity not listed' in html
