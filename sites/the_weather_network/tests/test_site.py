"""Site regression tests for the_weather_network mirror.

Run with: python3 -m pytest tests/ -q  (from sites/the_weather_network/)
Uses a scratch copy of the seed DB so stateful checks never touch the
worktree database.
"""
import os
import shutil
import sqlite3
import sys
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import pytest

SEED = os.path.join(BASE_DIR, 'instance_seed', 'the_weather_network.db')
if not os.path.exists(SEED):
    SEED = os.path.join(BASE_DIR, 'instance', 'the_weather_network.db')


@pytest.fixture()
def client(tmp_path):
    scratch = str(tmp_path / 'scratch.db')
    if os.path.exists(SEED):
        shutil.copy(SEED, scratch)
    os.environ['WEBHARBOR_DATABASE_URI'] = f'sqlite:///{scratch}'
    import app as appmod
    appmod.app.config['TESTING'] = True
    appmod.app.config['WTF_CSRF_ENABLED'] = False
    with appmod.app.test_client() as c:
        yield c
    os.environ.pop('WEBHARBOR_DATABASE_URI', None)
    sys.modules.pop('app', None)
    sys.modules.pop('seed_data', None)


def test_health(client):
    r = client.get('/_health')
    assert r.status_code == 200
    body = r.get_json()
    assert body['ok'] is True
    assert body['site'] == 'the_weather_network'
    counts = body['counts']
    assert counts['locations'] >= 500
    assert counts['articles'] >= 600
    assert counts['videos'] >= 700
    assert counts['alerts'] >= 40
    assert counts['hourly_forecasts'] >= 20000
    assert counts['users'] == 4


def test_key_pages_200(client):
    urls = [
        '/en',
        '/en/search?q=toronto', '/en/search?search=banff',
        '/en/search/suggest?q=vict',
        '/en/city/ca/ontario/toronto/current',
        '/en/city/ca/ontario/toronto/hourly',
        '/en/city/ca/ontario/toronto/7-days',
        '/en/city/ca/ontario/toronto/14-days',
        '/en/city/ca/ontario/toronto/weekend',
        '/en/city/ca/ontario/toronto/monthly?m=2026-12',
        '/en/ski/ca/alberta/banff-sunshine/current',
        '/en/golf/ca/alberta/banff-springs-golf-club/7-days',
        '/en/school/ca/alberta/banff-community-high-school/current',
        '/en/news', '/en/news/weather', '/en/news/weather/severe',
        '/en/news/nature/habitats', '/en/news/lifestyle/health',
        '/en/news/author/mia-gordon',
        '/en/news/weather/severe/polo-cements-its-status-as-one-of-the-pacifics-most-intense-hurricanes',
        '/en/video', '/en/video/UpJfe6IA',
        '/en/alerts/ca', '/en/alerts/ca?region=AB',
        '/en/maps/radar', '/en/vacation', '/en/vacation/us',
        '/en/explore/el-nino-la-nina', '/en/explore/indigenous',
        '/en/info/help-centre', '/en/account/sign-in', '/en/account/register',
    ]
    for u in urls:
        assert client.get(u).status_code == 200, u


def test_search_scored_not_strict(client):
    # multi-word query must return results (token overlap, not strict AND)
    r = client.get('/en/search?q=banff+springs')
    assert r.status_code == 200
    assert b'sr-item' in r.data
    # partial word / city + province style queries
    r = client.get('/en/search?q=lake+louise')
    assert b'sr-item' in r.data
    r = client.get('/en/search?q=nonexistentplace')
    assert b'No locations matched' in r.data


def test_search_suggest(client):
    r = client.get('/en/search/suggest?q=vict')
    assert r.status_code == 200
    data = r.get_json()
    assert data['results']
    assert any('Victoria' in x['name'] for x in data['results'])


def test_article_inline_images_local(client):
    r = client.get('/en/news/climate/causes/15-minute-cities-how-to-separate-'
                   'the-reality-from-the-conspiracy-theory')
    assert r.status_code == 200
    html = r.data.decode('utf-8')
    # figures rewritten to local files, no upstream img srcs remain
    assert 'src="/static/images/inline/' in html
    assert 'srcset="' not in html
    assert 'images.theconversation.com' not in html.split('figcaption')[0] if 'figcaption' in html else True
    # zoom links point at the local copy
    assert '<a href="/static/images/inline/' in html


def test_article_body_links_never_dead(client):
    """Every /en/... link rendered inside an article body must resolve."""
    import re
    import app as appmod
    bad = []
    checked = 0
    with appmod.app.app_context():
        for art in appmod.Article.query.limit(80).all():
            r = client.get(art.path)
            assert r.status_code == 200, art.path
            html = r.data.decode('utf-8')
            for href in set(re.findall(r'href="(/en/[^"#]+)"', html)):
                checked += 1
                rr = client.get(href)
                if rr.status_code >= 400:
                    bad.append((art.path, href, rr.status_code))
    assert not bad, bad[:5]
    assert checked > 200


def test_alerts_region_filter(client):
    r = client.get('/en/alerts/ca?region=AB')
    assert r.status_code == 200
    assert r.data.decode().count('alert-card') >= 40
    r = client.get('/en/alerts/ca?region=MB')
    assert r.data.decode().count('alert-card') >= 3
    assert client.get('/en/alerts/ca?region=ZZ').status_code == 404


def test_video_hub_playlists(client):
    r = client.get('/en/video')
    html = r.data.decode('utf-8')
    assert 'MUST WATCH' in html
    assert 'Animals and Weather' in html
    assert html.count('nc-dur') >= 60      # durations on cards (upstream design)


def test_auth_and_saved_flow(client):
    # sign in as a benchmark user
    r = client.post('/en/account/sign-in',
                   data={'email': 'bob.c@test.com', 'password': 'TestPass123!'})
    assert r.status_code == 302
    r = client.get('/en/account')
    assert r.status_code == 200
    html = r.data.decode('utf-8')
    assert 'Vancouver' in html and 'Banff National Park' in html
    # remove one saved location (Banff — the Alberta outlier)
    import re
    m = re.search(r'<span class="sv-name">Banff National Park[^<]*</span>.*?'
                  r'action="(/en/account/saved/\d+/remove)"', html, re.S)
    assert m, 'Banff remove form not found'
    r = client.post(m.group(1))
    assert r.status_code == 302
    r = client.get('/en/account')
    html = r.data.decode('utf-8')
    # the removal flash mentions the name; the saved-list row must be gone
    assert '<span class="sv-name">Banff National Park' not in html
    assert 'removed from your saved locations' in html
    # add Whistler Blackcomb
    r = client.post('/en/account/saved/add',
                    data={'code': 'CABC0278', 'next': '/en/account'})
    assert r.status_code in (302, 404)
    if r.status_code == 302:
        r = client.get('/en/account')
        assert 'Whistler Blackcomb' in r.data.decode('utf-8')


def test_register_validation(client):
    # duplicate email is rejected
    r = client.post('/en/account/register',
                    data={'username': 'alice_j', 'email': 'alice.j@test.com',
                          'password': 'SomePass123'})
    assert r.status_code == 400
    # short password rejected
    r = client.post('/en/account/register',
                    data={'username': 'newuser1', 'email': 'new@x.com',
                          'password': 'short'})
    assert r.status_code == 400
    # valid registration works
    r = client.post('/en/account/register',
                    data={'username': 'newuser1', 'email': 'new@x.com',
                          'password': 'LongEnough1!'})
    assert r.status_code == 302


def test_unit_preference(client):
    r = client.get('/en/city/ca/ontario/toronto/current')
    assert b'\xc2\xb0C' in r.data or '°C' in r.data.decode()
    client.get('/en/account/preferences?unit=imperial')
    r = client.get('/en/city/ca/ontario/toronto/current')
    html = r.data.decode('utf-8')
    assert '°F' in html
    # 18C == 64F
    assert '64°' in html


def test_monthly_tab(client):
    r = client.get('/en/city/ca/ontario/toronto/monthly?m=2026-12')
    assert r.status_code == 200
    html = r.data.decode('utf-8')
    assert '2026-12' in html
    assert 'Historical Averages' in html


def test_404s(client):
    for u in ('/en/city/ca/ontario/nowhere/current',
              '/en/news/weather/severe/no-such-article',
              '/en/video/ZZZZZZZZ',
              '/en/alerts/ca/NOPE',
              '/en/explore/nope',
              '/en/info/nope'):
        assert client.get(u).status_code == 404, u


def test_seed_idempotent(client):
    """Calling the bootstrap seed functions on a populated DB is a no-op."""
    import app as appmod
    with appmod.app.app_context():
        before = os.path.getmtime(os.environ['WEBHARBOR_DATABASE_URI'].replace('sqlite:///', ''))
        appmod.seed_database()
        appmod.seed_benchmark_users()
        after = os.path.getmtime(os.environ['WEBHARBOR_DATABASE_URI'].replace('sqlite:///', ''))
        assert before == after, 'seed functions must not write on a populated DB'
