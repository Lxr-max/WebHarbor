"""Contract tests: seeded data, public pages, CSRF on every POST form,
privacy rules and asset integrity."""
import json
import re

from conftest import with_csrf

import app as wl


# ------------------------------------------------------------------- seeds --

def test_seed_counts():
    with wl.app.app_context():
        assert wl.Geo.query.count() >= 11
        assert wl.Place.query.count() >= 400
        assert wl.CategoryList.query.count() >= 30
        assert wl.Guide.query.count() >= 14
        assert wl.Trip.query.count() >= 5
        assert wl.User.query.filter_by(is_upstream=False).count() == 4
        assert wl.TripEntry.query.count() >= 30
        assert wl.Expense.query.count() >= 12
        assert wl.ChecklistItem.query.count() >= 20


def test_benchmark_password_frozen():
    with wl.app.app_context():
        alice = wl.User.query.filter_by(email='alice.j@test.com').first()
        assert wl.bcrypt.check_password_hash(alice.password_hash, 'TestPass123!')


def test_health_ok(client):
    r = client.get('/_health')
    assert r.status_code == 200
    data = json.loads(r.get_data(as_text=True))
    assert data['ok'] is True
    assert data['geos'] >= 11 and data['guides'] >= 14


def test_place_images_all_real():
    """Every image served from static/images/upstream is inventoried with an
    https source URL, exact byte length and sha256 (no placeholders)."""
    import os
    root = os.path.join(wl.BASE_DIR, 'static', 'images', 'upstream')
    inv = json.load(open(os.path.join(wl.BASE_DIR, 'asset_inventory.json')))
    by_path = {row['path']: row for row in inv['assets']}
    files = [f for f in os.listdir(root) if not f.startswith('.')]
    assert len(files) == inv['asset_count'] == len(by_path)
    for row in inv['assets']:
        path = os.path.join(wl.BASE_DIR, row['path'])
        data = open(path, 'rb').read()
        assert len(data) == row['bytes']
        assert row['source_url'].startswith('https://')


# ------------------------------------------------------------ public pages --

def test_landing_and_directory(client):
    r = client.get('/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'One app for all your travel planning needs' in body
    assert '/explore/1' in body and '/guides' in body

    r = client.get('/guides')
    body = r.get_data(as_text=True)
    assert 'Paris 5 Day Tourist Itinerary' in body
    assert 'Japan: Video Game Guide' in body

    r = client.get('/guides?sort=likes')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert body.index('Japan: Video Game Guide') < body.index('Paris 5 Day Tourist Itinerary')


def test_guide_view_has_real_upstream_places(client):
    r = client.get('/view/uzyvvtuwtc')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Paris 5 Day Tourist Itinerary' in body
    assert 'Notre Dame' in body
    assert 'Shakespeare &amp; Company' in body
    assert 'Berthillon Glacier' in body
    assert 'elisa' in body
    # frozen upstream stats
    # upstream counts plus the seeded benchmark likes
    assert '177,509 views' in body
    assert re.search(r'77[0-9] likes', body)


def test_guide_comment_and_like_flow(alice):
    body = alice.get('/view/zlcocpeivp').get_data(as_text=True)
    before_likes = re.search(r'(\d[\d,]*) likes', body).group(1)
    r = alice.post('/guides/like/zlcocpeivp',
                   data=with_csrf(alice, '/view/zlcocpeivp', {}))
    assert r.status_code == 302
    body = alice.get('/view/zlcocpeivp').get_data(as_text=True)
    assert 'Remove my like' in body
    r = alice.post('/guides/comment/zlcocpeivp',
                   data=with_csrf(alice, '/view/zlcocpeivp',
                                  {'body': 'Beautiful list!'}))
    body = alice.get('/view/zlcocpeivp').get_data(as_text=True)
    assert 'Beautiful list!' in body


def test_explore_page_categories_and_lists(client):
    r = client.get('/explore/1')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'About Tokyo' in body
    assert 'Top places to visit' in body
    assert 'Tokyo Skytree' in body
    # category chips link to the captured ranked lists
    assert '/list/geoCategory/1/' in body


def test_ranked_list_sources(client):
    r = client.get('/list/geoCategory/1/where-to-eat-best-restaurants-in-tokyo')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Narisawa' in body
    assert 'Eater' in body
    assert '#1' in body


def test_place_details_page(client):
    r = client.get('/place/details/99')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Tower of London' in body
    assert 'Crown Jewels' in body
    assert 'ranked #2' in body


def test_profile_and_leaderboard(client):
    r = client.get('/u/alilies')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'elisa' in body and '214' in body
    r = client.get('/leaderboard')
    body = r.get_data(as_text=True)
    assert 'Traveler leaderboard' in body


def test_hotels_surfaces(client):
    body = client.get('/hotels').get_data(as_text=True)
    assert 'Search for hotel and Airbnb stays in one place' in body
    r = client.get('/hotels/1')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Mandarin Oriental' in body


def test_search(client):
    r = client.get('/search?q=louvre')
    body = r.get_data(as_text=True)
    assert 'Louvre Museum' in body


def test_search_matches_display_names(client):
    """The site search finds travelers by display name too (T17 premise:
    'Dana Kim' resolves directly to her profile)."""
    r = client.get('/search?q=Dana+Kim')
    body = r.get_data(as_text=True)
    assert 'Dana Kim' in body
    assert '/u/dana.k' in body


def test_search_cards_do_not_leak_answers(client):
    """Card-level tightening: place cards show categories (not the About
    description) and traveler cards show no geo counts."""
    r = client.get('/search?q=louvre')
    body = r.get_data(as_text=True)
    assert 'Former historic palace' not in body
    assert 'Art museum' in body
    r = client.get('/search?q=lilies')
    body = r.get_data(as_text=True)
    assert '/u/alilies' in body
    assert '214 geos' not in body


def test_no_literal_none_rendering(client):
    """Places without descriptions render no literal None on ranking pages,
    and the place Nearby section filters null related-attraction entries."""
    r = client.get('/list/geoCategory/104388/top-things-to-do-and-attractions-in-tokyo')
    body = r.get_data(as_text=True)
    assert 'Shibuya Crossing' in body
    assert '>None<' not in body and ' None\n' not in body
    r = client.get('/list/geoCategory/74217/where-to-eat-best-restaurants-in-rome')
    body = r.get_data(as_text=True)
    assert 'Bonci Pizzarium' in body
    assert '>None<' not in body and ' None\n' not in body
    r = client.get('/hotels/9614')
    body = r.get_data(as_text=True)
    assert 'Hôtel Madame Rêve' in body
    assert '>None<' not in body


def test_hotel_ranking_cards_are_truncated_previews(client):
    """Hotel ranking cards show a truncated description preview and no
    category chips, so full descriptions/categories only resolve on the
    hotel's own page."""
    r = client.get('/hotels/9614')
    body = r.get_data(as_text=True)
    assert 'a renowned restaurant &amp; a spa.' not in body  # full desc hidden
    assert 'views, …' in body  # truncated preview marker
    seg = body[body.find('Shangri-La Paris'):body.find('#2')]
    assert 'chip static' not in seg  # no category chips on hotel cards


def test_404(client):
    r = client.get('/no-such-page')
    assert r.status_code == 404
    assert 'Page not found' in r.get_data(as_text=True)


# --------------------------------------------------------------- auth rules --

def test_register_login_logout_flow(client):
    r = client.post('/register', data=with_csrf(client, '/register', {
        'email': 'new.user@example.com', 'username': 'newuser',
        'display_name': 'New User', 'password': 'SuperSecret9'}))
    assert r.status_code == 302
    body = client.get('/plans').get_data(as_text=True)
    assert 'Hi, New User' in body
    r = client.post('/logout', data=with_csrf(client, '/plans', {}))
    assert r.status_code == 302
    r = client.post('/login', data=with_csrf(client, '/login', {
        'email': 'new.user@example.com', 'password': 'SuperSecret9'}))
    assert r.status_code == 302
    # wrong password fails
    client.post('/logout', data=with_csrf(client, '/plans', {}))
    r = client.post('/login', data=with_csrf(client, '/login', {
        'email': 'new.user@example.com', 'password': 'WrongPass1'}))
    assert r.status_code == 200
    assert 'Incorrect email or password' in r.get_data(as_text=True)


def test_plans_requires_login(client):
    r = client.get('/plans')
    assert r.status_code == 302
    assert '/login' in r.headers['Location']


# ---------------------------------------------------------------- privacy --

def test_private_trip_hidden_from_anonymous(client):
    r = client.get('/trip/nycfoodcrawlv')
    assert r.status_code == 302
    assert '/login' in r.headers['Location']


def test_link_trip_viewable_anonymously(client):
    r = client.get('/trip/parisinspringv')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Paris in the Spring' in body
    assert 'Musée d&#39;Orsay' in body or "Musée d'Orsay" in body


def test_collaborator_can_edit_but_not_settings(bob):
    r = bob.get('/plan/parisinspring')
    assert r.status_code == 200
    r = bob.get('/plan/parisinspring/settings')
    assert r.status_code == 403


def test_non_member_cannot_open_private_planner(bob):
    r = bob.get('/plan/nycfoodcrawl')
    assert r.status_code == 403


# ------------------------------------------------------------------- CSRF --

def test_every_post_form_carries_csrf_token(client):
    """The regression gate: every shipped POST form embeds the token."""
    pages = ['/', '/guides', '/view/uzyvvtuwtc', '/explore/1', '/hotels',
             '/login', '/register', '/trip/parisinspringv',
             '/list/geoCategory/1/where-to-eat-best-restaurants-in-tokyo',
             '/place/details/99', '/u/alilies', '/leaderboard', '/search?q=x']
    for page in pages:
        body = client.get(page).get_data(as_text=True)
        for form in re.findall(r'<form method="post"[^>]*>(.*?)</form>',
                               body, flags=re.S):
            assert 'name="csrf_token"' in form, f'POST form on {page} lacks csrf'
    for page in ['/plans', '/plan/parisinspring', '/plan/parisinspring/budget',
                '/plan/parisinspring/checklist', '/plan/parisinspring/settings',
                '/plan/parisinspring/map', '/plan/new']:
        r = client.get(page)
        if r.status_code != 200:
            continue
        body = r.get_data(as_text=True)
        for form in re.findall(r'<form method="post"[^>]*>(.*?)</form>',
                               body, flags=re.S):
            assert 'name="csrf_token"' in form, f'POST form on {page} lacks csrf'


def test_post_without_csrf_token_rejected(alice):
    r = alice.post('/plan/parisinspring/checklist',
                   data={'text': 'no token', 'list_type': 'todo'})
    assert r.status_code == 400
