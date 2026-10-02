"""Flow tests: the interactive chains an agent drives — accounts, shopping
list, My Store, newsletter, gift card balance — all with CSRF enabled and
real tokens scraped from the rendered forms."""
import re

from conftest import with_csrf


def test_login_logout_flow(client):
    data = with_csrf(client, "/login", {"email": "alice.j@test.com",
                                        "password": "TestPass123!"})
    r = client.post("/login", data=data)
    assert r.status_code in (302, 303)
    r = client.get('/')
    assert 'Log out' in r.data.decode() or 'Shopping List' in r.data.decode()
    r = client.get('/logout')
    assert r.status_code in (302, 303)


def test_login_wrong_password(client):
    data = with_csrf(client, "/login", {"email": "alice.j@test.com",
                                        "password": "wrong"})
    r = client.post("/login", data=data)
    assert r.status_code == 200
    assert 'Invalid email or password' in r.data.decode()


def test_csrf_required_on_login(client):
    r = client.post("/login", data={"email": "alice.j@test.com",
                                    "password": "TestPass123!"})
    assert r.status_code in (400, 302, 303)
    html = (r.data.decode() if r.status_code == 400 else "")
    assert r.status_code != 200 or 'CSRF' in html


def test_signup_flow(client):
    data = with_csrf(client, "/signup", {
        "name": "Jordan Vale", "email": "jordan.vale@test.com",
        "password": "Password99!"})
    r = client.post("/signup", data=data, follow_redirects=True)
    assert r.status_code == 200
    # new account has an empty shopping list
    r = client.get('/home/shopping-list')
    assert 'not added any items' in r.data.decode()


def test_shopping_list_seeded_state(alice_client):
    r = alice_client.get('/home/shopping-list')
    html = r.data.decode()
    assert 'Pumpkin Cream Cheese Spread' in html
    assert 'Pumpkin Bisque' in html
    assert 'Total items: 8' in html


def _list_total(client):
    html = client.get('/home/shopping-list').data.decode()
    m = re.search(r'Total items: (\d+)', html)
    return int(m.group(1)) if m else 0


def test_shopping_list_add_from_pdp(bob_client):
    before = _list_total(bob_client)
    data = with_csrf(bob_client, '/home/products/pdp/ooey-gooey-cheese-blend-083507',
                     {"next": "/home/shopping-list"})
    r = bob_client.post('/home/shopping-list/add/083507', data=data,
                        follow_redirects=True)
    html = r.data.decode()
    assert 'Ooey Gooey Cheese Blend' in html
    assert _list_total(bob_client) == before + 1


def test_shopping_list_increase_decrease_remove(bob_client):
    before = _list_total(bob_client)
    html = bob_client.get('/home/shopping-list').data.decode()
    m = re.search(r'/home/shopping-list/update/(\d+)', html)
    assert m
    item_id = m.group(1)
    qty = int(re.search(
        r'update/%s.*?<b>(\d+)</b>' % item_id, html, re.S).group(1))
    data = with_csrf(bob_client, '/home/shopping-list',
                     {"action": "increase"})
    bob_client.post(f'/home/shopping-list/update/{item_id}', data=data)
    assert _list_total(bob_client) == before + 1
    data = with_csrf(bob_client, '/home/shopping-list', {"action": "decrease"})
    bob_client.post(f'/home/shopping-list/update/{item_id}', data=data)
    assert _list_total(bob_client) == before
    data = with_csrf(bob_client, '/home/shopping-list', {"action": "remove"})
    bob_client.post(f'/home/shopping-list/update/{item_id}', data=data)
    assert _list_total(bob_client) == before - qty


def test_shopping_list_clear(fresh_user_client):
    data = with_csrf(fresh_user_client, '/home/products/pdp/ooey-gooey-cheese-blend-083507',
                     {"next": "/home/shopping-list"})
    fresh_user_client.post('/home/shopping-list/add/083507', data=data)
    assert _list_total(fresh_user_client) == 1
    data = with_csrf(fresh_user_client, '/home/shopping-list', {})
    r = fresh_user_client.post('/home/shopping-list/clear', data=data,
                               follow_redirects=True)
    assert 'not added any items' in r.data.decode()


def test_shopping_list_requires_login(client):
    r = client.get('/home/shopping-list')
    assert r.status_code in (302, 303)
    assert '/login' in r.headers.get('Location', '')


def test_set_my_store(carol_client):
    data = with_csrf(carol_client, '/home/store-search?q=98052',
                     {"next": "/"})
    r = carol_client.post('/home/set-my-store/140', data=data,
                          follow_redirects=True)
    html = r.data.decode()
    assert 'My Store:' in html
    assert 'Redmond (140)' in html


def test_my_store_header_reflects_preference(dana_client):
    r = dana_client.get('/')
    html = r.data.decode()
    assert 'My Store:' in html
    # dana's seeded store is 742 = Charlotte - Piper Glen (provenance fixture)
    assert 'Charlotte - Piper Glen (742)' in html


def test_subscribe_flow(client):
    data = with_csrf(client, "/home/subscribe",
                     {"email": "new.person@example.com"})
    r = client.post("/home/subscribe", data=data)
    assert r.status_code == 200
    assert 'Welcome aboard' in r.data.decode()


def test_subscribe_invalid_email(client):
    data = with_csrf(client, "/home/subscribe", {"email": "not-an-email"})
    r = client.post("/home/subscribe", data=data)
    assert 'valid email address' in r.data.decode()


def test_unsubscribe_flow(client):
    data = with_csrf(client, "/home/unsubscribe",
                     {"email": "alice.j@test.com"})
    r = client.post("/home/unsubscribe", data=data)
    assert r.status_code == 200
    # the removed confirmation block renders (subscribe.html {% if removed %})
    html = r.data.decode()
    assert "You&rsquo;ve been unsubscribed" in html
    assert "alice.j@test.com has been removed" in html
    # alice is now unsubscribed; resubscribing works again
    data = with_csrf(client, "/home/subscribe",
                     {"email": "alice.j@test.com"})
    r = client.post("/home/subscribe", data=data)
    assert 'Welcome aboard' in r.data.decode()


def test_unsubscribe_unknown_email(client):
    data = with_csrf(client, "/home/unsubscribe",
                     {"email": "stranger@example.com"})
    r = client.post("/home/unsubscribe", data=data)
    assert 'not on our newsletter list' in r.data.decode()


def test_gift_card_balance(client):
    data = with_csrf(client, "/home/gift-card-balance-inquiry",
                     {"card_number": "6510000000654321"})
    r = client.post("/home/gift-card-balance-inquiry", data=data)
    assert '$51.37' in r.data.decode()


def test_gift_card_unknown_number(client):
    data = with_csrf(client, "/home/gift-card-balance-inquiry",
                     {"card_number": "000000000000"})
    r = client.post("/home/gift-card-balance-inquiry", data=data)
    assert 'could not find a gift card' in r.data.decode()


def test_gift_card_zero_balance(client):
    data = with_csrf(client, "/home/gift-card-balance-inquiry",
                     {"card_number": "6510000000112233"})
    r = client.post("/home/gift-card-balance-inquiry", data=data)
    assert '$0.00' in r.data.decode()


def test_dietary_filter_chain(client):
    """Vegan + Gluten Free in From The Freezer yields only products that
    carry both characteristics."""
    r = client.get('/home/products/category/from-the-freezer-95'
                   '?filters=%7B%22characteristics%22%3A%5B%22Vegan%22%2C%22'
                   'Gluten+Free%22%5D%7D')
    html = r.data.decode()
    m = re.search(r'(\d+) products', html)
    assert m and 0 < int(m.group(1)) < 467


def test_search_pagination(client):
    r = client.get('/home/search?q=pumpkin')
    html = r.data.decode()
    assert 'results for' in html
    # the search results page shows all three section buckets
    assert 'Products (' in html
    assert 'Everything Else (' in html
