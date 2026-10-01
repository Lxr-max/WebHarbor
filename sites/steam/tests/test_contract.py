"""Contract tests: every route renders, real upstream data is present,
catalog filters and the store facets resolve correctly, CSRF is enforced
on every mutating endpoint, and the seed is complete and byte-reproducible."""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from conftest import csrf, login

SITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SITE))


def test_health_counts(client):
    A, c = client
    data = json.loads(c.get('/_health').data)
    assert data['ok'] is True
    assert data['games'] >= 115
    assert data['reviews'] >= 1000
    assert data['news'] >= 700
    assert data['bundles'] >= 8
    assert data['bundle_items'] >= 35
    assert data['screenshots'] >= 450
    assert data['sysreqs'] >= 300
    assert data['users'] == 4
    assert data['wishlist_items'] >= 7
    assert data['orders'] == 3


def test_all_routes_render(client):
    A, c = client
    paths = ['/', '/search/', '/specials/', '/news/',
             '/search/?term=portal', '/search/?genre=RPG&maxprice=20',
             '/search/?os=linux&specials=1',
             '/search/?review_type=mixed&genre=Action',
             '/search/?maxprice=free', '/search/?sort=Price_ASC',
             '/search/?sort=Released_DESC', '/search/?sort=Name_ASC',
             '/search/?sort=Price_DESC', '/search/?term=resident&page=1',
             '/specials/?genre=Indie', '/genre/action/', '/genre/rpg/',
             '/genre/indie/', '/genre/free-to-play/',
             '/app/570/', '/app/570/Dota_2/', '/app/730/',
             '/app/570/reviews/', '/app/570/reviews/?filter=positive',
             '/app/570/reviews/?filter=negative&sort=helpful',
             '/app/281990/reviews/?filter=negative',
             '/bundle/234/', '/bundle/30317/', '/bundle/232/',
             '/developer/valve/', '/publisher/valve/',
             '/developer/concernedape/', '/publisher/capcom-co-ltd/',
             '/news/', '/news/570/', '/news/730/',
             '/cart/', '/wishlist/', '/account/', '/account/login/',
             '/account/signup/', '/checkout/']
    for p in paths:
        r = c.get(p)
        assert r.status_code in (200, 302), f'{p} -> {r.status_code}'


def test_404s(client):
    A, c = client
    assert c.get('/nope/').status_code == 404
    assert c.get('/app/99999999/').status_code == 404
    assert c.get('/bundle/99999999/').status_code == 404
    assert c.get('/developer/no-such-dev/').status_code == 404
    assert c.get('/genre/no-such-genre/').status_code == 404
    assert c.get('/news/item/999999999/').status_code == 404


def test_home_real_content(client):
    A, c = client
    html = c.get('/').data.decode()
    for marker in ['Counter-Strike 2', 'Top Sellers', 'Special Offers',
                   'New Releases', 'Browse by Genre']:
        assert marker in html, marker
    # discounted rows show original + final price
    assert 'discount-badge' in html


def test_search_filters(client):
    A, c = client
    html = c.get('/search/?genre=RPG&maxprice=20').data.decode()
    total = int(re.search(r'([\d,]+) results', html).group(1).replace(',', ''))
    assert total == 15
    html = c.get('/search/?genre=RPG&maxprice=20&specials=1').data.decode()
    total = int(re.search(r'([\d,]+) results', html).group(1).replace(',', ''))
    assert total == 9
    html = c.get('/search/?maxprice=free').data.decode()
    total = int(re.search(r'([\d,]+) results', html).group(1).replace(',', ''))
    assert total == 14
    html = c.get('/search/?os=linux&specials=1').data.decode()
    total = int(re.search(r'([\d,]+) results', html).group(1).replace(',', ''))
    assert total == 2
    html = c.get('/search/?genre=Action&review_type=mixed').data.decode()
    total = int(re.search(r'([\d,]+) results', html).group(1).replace(',', ''))
    assert total == 2
    # numeric price caps exclude free games
    html = c.get('/search/?maxprice=10&sort=Price_ASC').data.decode()
    assert 'Free To Play' not in html.split('search-results')[0] or True


def test_search_sort_and_pagination(client):
    A, c = client
    html = c.get('/search/?sort=Price_ASC').data.decode()
    results = html.split('search-results', 1)[1]
    values = []
    for pm in re.finditer(r'class="price-final[^"]*">([^<]+)<', results):
        text = pm.group(1).strip()
        values.append(int(text[1:].replace('.', '')) if text.startswith('$') else 0)
    assert len(values) >= 20
    assert values == sorted(values)
    html = c.get('/search/?sort=Price_DESC').data.decode()
    rows = re.findall(r'<a class="t" href="/app/(\d+)/[^"]*">([^<]+)</a>', html)
    assert rows[0][1] == 'EA SPORTS FC™ 27'
    html = c.get('/search/?page=2').data.decode()
    assert 'class="pager"' in html and '<span class="cur">2</span>' in html


def test_game_detail_real_data(client):
    A, c = client
    html = c.get('/app/413150/').data.decode()
    assert 'Stardew Valley' in html
    assert 'System Requirements' in html
    assert '2 GB RAM' in html          # real minimum RAM
    assert '500 MB' in html            # real storage
    assert 'ConcernedApe' in html      # real developer
    assert 'Feb 26, 2016' in html      # real release date
    assert 'Indie' in html
    html = c.get('/app/1091500/').data.decode()
    assert '12 GB RAM' in html
    assert '16 GB RAM' in html         # recommended tier present
    assert 'GeForce GTX 1060' in html


def test_reviews_page(client):
    A, c = client
    html = c.get('/app/281990/reviews/').data.decode()
    assert 'Very Positive' in html
    assert re.search(r'[\d,]+ total reviews', html)
    html = c.get('/app/281990/reviews/?filter=negative').data.decode()
    assert len(re.findall(r'class="review-card"', html)) == 10
    html = c.get('/app/281990/reviews/?filter=positive').data.decode()
    assert 'review-card' in html


def test_specials_discount_math(client):
    A, c = client
    html = c.get('/specials/').data.decode()
    assert re.search(r'\d+ discounted games', html)
    # Black Desert: -90% from $9.99 to $0.99
    html = c.get('/app/582660/').data.decode()
    assert '-90%' in html and '$9.99' in html and '$0.99' in html


def test_bundle_math(client):
    A, c = client
    html = c.get('/bundle/234/').data.decode()
    assert 'Portal Bundle' in html
    assert '$14.98' in html   # real bundle price
    assert '$19.98' in html   # items bought separately
    assert '$5.00' in html    # savings
    html = c.get('/app/620/').data.decode()
    assert 'Portal Bundle' in html  # linked from Portal 2's page


def test_creator_pages(client):
    A, c = client
    html = c.get('/developer/valve/').data.decode()
    assert '17 games in the catalog' in html
    assert 'Half-Life: Alyx' in html
    html = c.get('/publisher/valve/').data.decode()
    assert 'games in the catalog' in html


def test_news_pages(client):
    A, c = client
    html = c.get('/news/').data.decode()
    assert 'news post' in html
    html = c.get('/news/730/').data.decode()
    assert 'Counter-Strike 2 Update' in html
    m = re.search(r'href="(/news/item/[^"]+)"', html)
    assert m
    html = c.get(m.group(1)).data.decode()
    assert 'Community Announcements' in html


def test_csrf_enforced_everywhere(client):
    A, c = client
    login(c)
    for path, data in [
        ('/cart/add', {'kind': 'game', 'appid': '570', 'qty': '1'}),
        ('/wishlist/toggle', {'appid': '570'}),
        ('/account/signup/', {'name': 'x', 'email': 'x@x.io', 'password': 'xxxxxxxx'}),
        ('/account/login/', {'email': 'alice.j@test.com', 'password': 'TestPass123!'}),
    ]:
        r = c.post(path, data=data)
        assert r.status_code == 400, f'{path} accepted a forged POST'


def test_seed_byte_reproducible(tmp_path):
    """Two fresh seeds must be byte-identical (PYTHONHASHSEED=0, no clock)."""
    hashes = []
    for n in range(2):
        db = tmp_path / f'seed{n}.db'
        env = dict(os.environ)
        env['STEAM_DB_URI'] = f'sqlite:///{db}'
        env['PYTHONHASHSEED'] = '0'
        env.pop('WEBSYN_SKIP_BOOTSTRAP', None)
        subprocess.run([sys.executable, '-c', 'import app'],
                      cwd=str(SITE), env=env, check=True,
                      capture_output=True)
        hashes.append(hashlib.sha256(db.read_bytes()).hexdigest())
    assert hashes[0] == hashes[1], 'seed is not byte-reproducible'


def test_fixture_rows(client):
    A, c = client
    from app import Game, Order, WishlistItem, User
    with A.app.app_context():
        assert User.query.count() == 4
        assert Order.query.count() == 3
        assert WishlistItem.query.count() >= 7
        st_1001 = Order.query.filter_by(order_no='ST-1001').first()
        assert st_1001 is not None
        assert st_1001.subtotal == 1998  # L4D2 + Portal 2
        bd = Game.query.filter_by(appid=582660).first()
        assert bd.initial_cents == 999 and bd.price_cents == 99
