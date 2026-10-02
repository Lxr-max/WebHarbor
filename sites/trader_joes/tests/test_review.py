from conftest import tj_app, login

def test_home_uses_seeded_content(client, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Runtime must not read source_data home content')
    monkeypatch.setattr(tj_app, '_load', forbidden)
    r = client.get('/')
    assert r.status_code == 200
    assert b'One Seasoning Wonder' in r.data
    assert b'WATCH THE VIDEO' not in r.data

def test_list_cost_matches_captured_prices(client):
    login(client, 'alice.j@test.com')
    with tj_app.app.app_context():
        user = tj_app.User.query.filter_by(email='alice.j@test.com').one()
        items = tj_app.ShoppingItem.query.filter_by(user_id=user.id).all()
        cents = sum(round(tj_app.db.session.get(tj_app.Product, i.sku).retail_price*100)*i.quantity for i in items)
    text = client.get('/home/shopping-list').get_data(as_text=True)
    assert f'Estimated product total: ${cents/100:.2f}' in text
    assert 'This list is not an order' in text

def test_recipe_capture_escapes_decoded(client):
    text = client.get('/home/recipes/pumpkin-bars').get_data(as_text=True)
    assert r'\u2019' not in text
    assert r'\u00be' not in text
    assert '¾' in text


def test_nutrition_fraction_is_rendered_as_daily_value_percentage(client):
    with tj_app.app.test_request_context():
        product = tj_app.db.session.get(tj_app.Product, '051533')
        url = tj_app.product_link(product)
    text = client.get(url).get_data(as_text=True)
    assert '(10% DV)' in text and '(25% DV)' in text
    assert '(.1% DV)' not in text
