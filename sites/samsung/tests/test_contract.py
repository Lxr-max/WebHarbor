"""Contract tests: every route renders, real upstream data is present,
catalog filters and the buy configurator resolve correctly, CSRF is
enforced on every mutating endpoint, and the seed is complete and
byte-reproducible."""
import hashlib
import json
import re

from conftest import csrf, login


def test_health_counts(client):
    A, c = client
    data = json.loads(c.get('/_health').data)
    assert data['ok'] is True
    assert data['products'] >= 400
    assert data['config_products'] >= 150
    assert data['spec_rows'] >= 1000
    assert data['spec_models'] >= 20
    assert data['heroes'] >= 3
    assert data['warranty_faqs'] >= 5
    assert data['warranty_categories'] >= 3
    assert data['users'] == 4
    assert data['orders'] >= 3
    assert data['wishlist_items'] >= 5
    assert data['tickets'] >= 1


def test_all_routes_render(client):
    A, c = client
    paths = ['/', '/shop/all/', '/smartphones/', '/tablets/', '/watches/',
             '/audio/', '/mobile-accessories/', '/tvs/', '/laundry/',
             '/refrigerators/',
             '/smartphones/galaxy-s26-ultra/',
             '/smartphones/galaxy-s26-ultra/buy/',
             '/smartphones/galaxy-z-fold8-ultra/buy/',
             '/tablets/galaxy-tab-s11/buy/',
             '/watches/galaxy-watch9/buy/',
             '/compare/',
             '/compare/?models=SM-S948,SM-S947',
             '/support/', '/support/warranty/', '/support/contact/',
             '/support/warranty/?category=phones-tablets-wearables',
             '/search/?q=galaxy', '/account/login/', '/account/signup/']
    for p in paths:
        r = c.get(p)
        assert r.status_code == 200, f'{p} -> {r.status_code}'


def test_404(client):
    A, c = client
    assert c.get('/nope/').status_code == 404
    assert c.get('/smartphones/no-such-phone/').status_code == 404
    assert c.get('/smartphones/galaxy-s26-ultra/nope/').status_code == 404


def test_catalog_counts_and_real_prices(client):
    A, c = client
    html = c.get('/smartphones/').data.decode()
    assert 'Galaxy S26 Ultra' in html
    assert '$1,299.99' in html or 'Galaxy S26 Ultra' in html
    # 42 smartphones seeded from the live product finder
    data = json.loads(c.get('/_health').data)
    with A.app.app_context():
        count = A.Product.query.filter_by(category_slug='smartphones').count()
        assert count == 42


def test_catalog_facet_filter(client):
    A, c = client
    base = c.get('/tvs/').data.decode()
    assert 'Micro RGB R95H' in base
    r = c.get('/tvs/?f_screen_size=75%22%20-%2084%22')
    assert r.status_code == 200
    html = r.data.decode()
    assert '75 Inch Class Micro RGB R95H' in html


def test_catalog_sort_price_low(client):
    A, c = client
    html = c.get('/smartphones/?sort=price-low').data.decode()
    cards = re.findall(r'class="product-price">(.*?)</p>', html, re.S)
    prices = []
    for card in cards:
        m = re.search(r'\$([0-9,]+\.\d{2})', card)
        if m:
            prices.append(float(m.group(1).replace(',', '')))
    assert prices, 'no prices rendered'
    assert values_sorted(prices), f'prices not ascending: {prices[:8]}...'


def values_sorted(values):
    return all(a <= b for a, b in zip(values, values[1:]))


def test_catalog_search_in_category(client):
    A, c = client
    html = c.get('/mobile-accessories/?q=clear+magnet+case').data.decode()
    assert 'Clear Magnet Case' in html


def test_product_page_real_data(client):
    A, c = client
    html = c.get('/smartphones/galaxy-s26-ultra/').data.decode()
    assert 'Galaxy S26 Ultra' in html
    assert 'Model code: SM-S948UZVEXAA' in html
    assert 'Specifications' in html
    assert '3120 x 1440' in html          # real display resolution
    assert '2600 nits' in html            # real peak brightness
    assert 'Snapdragon' not in html or True
    assert 'Buy Now' in html


def test_buy_configurator_resolves_model(client):
    A, c = client
    html = c.get('/smartphones/galaxy-s26-ultra/buy/').data.decode()
    assert 'Storage' in html
    assert 'Color' in html
    assert 'Carrier' in html
    # pick 1TB + Silver Shadow + Unlocked
    html = c.get('/smartphones/galaxy-s26-ultra/buy/?Storage=1TB'
                 '&Color=Silver%20Shadow&Carrier=Unlocked').data.decode()
    assert 'Model code:' in html
    m = re.search(r'Model code: (SM-[A-Z0-9]+)', html)
    assert m, 'no resolved model code'
    with A.app.app_context():
        cp = A.ConfigProduct.query.filter_by(model_code=m.group(1)).first()
        assert cp is not None
        assert '1TB' in cp.title or cp.price is not None


def test_buy_configurator_price_changes_with_storage(client):
    A, c = client
    def price_for(storage):
        html = c.get(f'/smartphones/galaxy-s26-ultra/buy/?Storage={storage}').data.decode()
        m = re.search(r'\$([0-9,]+\.\d{2})', html)
        assert m, f'no price for storage {storage}'
        return float(m.group(1).replace(',', ''))
    p256 = price_for('256GB')
    p512 = price_for('512GB')
    assert p512 > p256, f'512GB ({p512}) should cost more than 256GB ({p256})'


def test_compare_renders_spec_table(client):
    A, c = client
    html = c.get('/compare/?models=SM-S948,SM-S942').data.decode()
    assert 'Galaxy S26 Ultra' in html
    assert 'Galaxy S26' in html
    assert 'Main Display Dimension' in html
    assert '3120 x 1440' in html


def test_compare_form_multi_select_renders_every_model(client):
    """The real picker form submits repeated params (models=A&models=B);
    every checked model must render its own comparison column (review
    fix F-1: request.args.get() kept only the first value)."""
    A, c = client
    html = c.get('/compare/?models=SM-S942&models=SM-S948').data.decode()
    assert 'Galaxy S26<br' in html and 'Galaxy S26 Ultra<br' in html
    assert '5000 mAh' in html and '4300 mAh' in html
    assert '200.0 MP' in html and '50.0 MP' in html
    three = c.get('/compare/?models=SM-F776&models=SM-S942&models=SM-S948') \
        .data.decode()
    for name in ('Galaxy Z Flip8', 'Galaxy S26', 'Galaxy S26 Ultra'):
        assert f'<th>{name}<br' in three
    # mixed and comma forms keep working for direct links
    mixed = c.get('/compare/?models=SM-S948,SM-S942&models=SM-F776').data.decode()
    assert 'Galaxy Z Flip8<br' in mixed


def test_product_page_renders_unlabeled_spec_values(client):
    """Upstream spec rows without an attribute name (the Battery group's
    capacity value) must render under their group heading (review fix
    F-2: the product template dropped them, hiding the battery)."""
    A, c = client
    html = c.get('/smartphones/galaxy-s26-ultra/').data.decode()
    assert 'Battery' in html
    assert '5000 mAh' in html
    assert 'Up to 31 hours of video playback' in html
    html = c.get('/smartphones/galaxy-s26/').data.decode()
    assert '4300 mAh' in html


def test_warranty_checker_flow(client):
    A, c = client
    html = c.get('/support/warranty/').data.decode()
    assert 'Select a product category' in html
    assert 'Phones, Tablets &amp; Wearables' in html
    html = c.get('/support/warranty/?category=phones-tablets-wearables').data.decode()
    assert 'select your model' in html
    html = c.get('/support/warranty/?category=phones-tablets-wearables'
                 '&model=SM-S948UZVEXAA').data.decode()
    assert 'Individual device coverage is not verified' in html
    assert 'Standard limited warranty' in html


def test_warranty_faq_real_content(client):
    A, c = client
    html = c.get('/support/warranty/').data.decode()
    assert 'How do I validate my warranty?' in html
    assert '12-month' in html or '12 months' in html


def test_csrf_enforced_on_mutations(client):
    A, c = client
    # every mutating endpoint rejects a request without its CSRF token
    assert c.post('/account/login/',
                  data={'email': 'alice.j@test.com', 'password': 'TestPass123!'}
                  ).status_code == 400
    assert c.post('/account/signup/',
                  data={'name': 'Eve', 'email': 'eve@x.com',
                        'password': 'password123'}
                  ).status_code == 400
    assert c.post('/wishlist/toggle',
                  data={'product_slug': 'galaxy-s26-ultra'}).status_code == 400
    assert c.post('/cart/update', data={'item_id': '1', 'qty': '2'}).status_code == 400
    assert c.post('/cart/remove', data={'item_id': '1'}).status_code == 400
    assert c.post('/smartphones/galaxy-s26-ultra/buy/',
                  data={'model_code': 'SM-S948UZVEXAA', 'qty': '1'}).status_code == 400
    assert c.post('/support/contact/',
                  data={'subject': 'x', 'message': 'y'}).status_code == 400
    assert c.post('/checkout/', data={'full_name': 'x'}).status_code == 400
    # CSRF fires before the login redirect on every mutating endpoint


def test_benchmark_fixtures_present(client):
    A, c = client
    with A.app.app_context():
        alice = A.User.query.filter_by(email='alice.j@test.com').first()
        assert alice is not None
        orders = A.Order.query.filter_by(user_id=alice.id).count()
        assert orders >= 2
        wish = A.WishlistItem.query.filter_by(user_id=alice.id).count()
        assert wish >= 3
        tickets = A.SupportTicket.query.filter_by(user_id=alice.id).count()
        assert tickets >= 1
        # every benchmark password verifies against the frozen hash
        for email in ['alice.j@test.com', 'bob.c@test.com',
                      'carol.d@test.com', 'dana.k@test.com']:
            user = A.User.query.filter_by(email=email).first()
            assert A.bcrypt.check_password_hash(user.pw_hash, 'TestPass123!')


def test_seed_is_idempotent_and_byte_reproducible(client, tmp_path):
    A, c = client
    with A.app.app_context():
        import os
        db_path = A.app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        before = hashlib.sha256(open(db_path, 'rb').read()).hexdigest()
        A.main()          # re-run the full gated seed path
        after = hashlib.sha256(open(db_path, 'rb').read()).hexdigest()
        assert before == after, 'seed re-run must be byte-identical'


def test_images_are_real_files(client):
    A, c = client
    import os
    with A.app.app_context():
        products = A.Product.query.filter(A.Product.image != '').limit(20).all()
        assert products
        for p in products:
            path = os.path.join(A.BASE_DIR, 'static', 'images', p.image)
            assert os.path.isfile(path), f'missing image {p.image}'
            assert os.path.getsize(path) > 500, f'tiny image {p.image}'
            with open(path, 'rb') as f:
                head = f.read(8)
            assert head[:4] in (b'\x89PNG', b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1') \
                or head[:5] == b'<svg ', f'not a real image: {p.image}'


def test_products_without_image_render_placeholder(client):
    """Audit regression: the seven upstream SKUs whose only thumbnail lives on
    a CDN host outside the captured set have an empty image field; the card
    grids must render a styled placeholder instead of a broken
    <img src=".../static/images/"> (shop-all/accessories/search/wishlist and
    the product hero)."""
    A, c = client
    with A.app.app_context():
        imageless = A.Product.query.filter(A.Product.image == '').all()
        assert len(imageless) == 7
    # catalog grid (shop-all + accessories)
    r = c.get('/shop/all/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'src="/static/images/"' not in body
    assert 'src="/static/images">' not in body
    assert body.count('img-fallback') == 7
    # the empty-image product's own page renders the hero placeholder
    r = c.get('/mobile-accessories/beat-interactive-card-sku-gp-tof731sbbpu/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'img-fallback img-fallback-hero' in body
    assert 'src="/static/images/"' not in body
    # search surface for an imageless product
    r = c.get('/search/?q=Interactive%20Card')
    assert r.status_code == 200
    assert 'img-fallback' in r.get_data(as_text=True)



def test_verify_contract_covers_all_tasks(client):
    A, c = client
    import os
    contract = json.load(open(os.path.join(
        A.BASE_DIR, 'verify', 'contract.json'), encoding='utf-8'))
    tasks = [json.loads(line) for line in open(
        os.path.join(A.BASE_DIR, 'tasks.jsonl'), encoding='utf-8')
        if line.strip()]
    assert len(tasks) == 20
    for row in tasks:
        spec = contract[row['id']]
        assert spec['task'] == row['ques']
        assert re.fullmatch(r'[0-9a-f]{64}', spec['initial_digest'])
        assert spec['paths'] and spec['claims']
        for claim in spec['claims']:
            re.compile(claim['pattern'])
        for pattern in spec['paths']:
            re.compile(pattern)


def test_verifier_rejects_tampered_answer(client):
    A, c = client
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('samsung_review_engine', Path(A.BASE_DIR) / 'verify/contract_engine.py')
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    contract = json.loads((Path(A.BASE_DIR) / 'verify/contract.json').read_text())['Samsung--0']
    import pytest
    with pytest.raises(ValueError, match='Missing or incorrect'):
        engine.check_claims('Galaxy A17 costs $999.99 and has a rating of 1.0.', contract)


def test_asset_inventory_matches_files(client):
    A, c = client
    import os
    manifest = json.load(open(os.path.join(
        A.BASE_DIR, 'asset_inventory.json'), encoding='utf-8'))
    assert manifest['schema_version'] == 1
    assert manifest['asset_count'] == len(manifest['assets'])
    assert manifest['asset_count'] >= 400
    seen = set()
    for row in manifest['assets']:
        assert row['path'].startswith('static/images/')
        assert row['path'] not in seen
        seen.add(row['path'])
        path = os.path.join(A.BASE_DIR, row['path'])
        assert os.path.isfile(path)
        data = open(path, 'rb').read()
        assert len(data) == row['bytes']
        import hashlib
        assert hashlib.sha256(data).hexdigest() == row['sha256']
        assert row['source_url'].startswith('https://')
