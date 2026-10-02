"""Flow tests: real form submissions with CSRF enabled — signup, login,
favorites, calculator estimates across all four services, saved estimates,
currency conversion, and logout."""
import re

from conftest import csrf


def _vm_post(c, **over):
    data = {'service': 'virtual-machines', 'size': 'linux-d4sv5-standard',
            'quantity': '1', 'hours': '730', 'region': 'us-east',
            'currency': 'usd'}
    data.update(over)
    data['csrf_token'] = csrf(c, f"/pricing/calculator/?service={data['service']}")
    return c.post(f"/pricing/calculator/?service={data['service']}",
                 data=data, follow_redirects=True)


def _total(page):
    m = re.search(r'Estimated monthly cost \(\w+\)</th>\s*<th></th>\s*<th>([^<]+)</th>',
                  page)
    assert m, 'no total rendered'
    return m.group(1)


def test_signup_login_logout_flow(client):
    A, c = client
    tok = csrf(c, '/account/signup')
    r = c.post('/account/signup', data={'csrf_token': tok, 'name': 'Zoe Test',
                                         'email': 'zoe@test.com',
                                         'password': 'TestPass123!'},
               follow_redirects=True)
    assert 'Welcome to Azure, Zoe Test!' in r.data.decode()
    c.get('/account/logout')
    tok = csrf(c, '/account/login')
    r = c.post('/account/login', data={'csrf_token': tok, 'email': 'zoe@test.com',
                                        'password': 'TestPass123!'},
               follow_redirects=True)
    assert 'Signed in as Zoe Test' in r.data.decode()
    tok = csrf(c, '/account/login')
    r = c.post('/account/login', data={'csrf_token': tok, 'email': 'zoe@test.com',
                                        'password': 'wrong'}, follow_redirects=True)
    assert 'Invalid email or password' in r.data.decode()


def test_duplicate_signup_rejected(client):
    A, c = client
    tok = csrf(c, '/account/signup')
    r = c.post('/account/signup', data={'csrf_token': tok, 'name': 'Zoe',
                                         'email': 'alice.chen@test.com',
                                         'password': 'TestPass123!'},
               follow_redirects=True)
    assert 'already exists' in r.data.decode()


def test_short_password_rejected(client):
    A, c = client
    tok = csrf(c, '/account/signup')
    r = c.post('/account/signup', data={'csrf_token': tok, 'name': 'Zoe',
                                         'email': 'zoe2@test.com',
                                         'password': 'short'}, follow_redirects=True)
    assert 'at least 8 characters' in r.data.decode()


def test_vm_estimate_math(client):
    A, c = client
    page = _vm_post(c, quantity='3').data.decode()
    assert _total(page) == '$420.48'  # 0.192 * 730 * 3


def test_vm_estimate_currency_conversion(client):
    A, c = client
    page = _vm_post(c, currency='eur').data.decode()
    assert _total(page).startswith('€')


def test_vm_estimate_region_prices_differ(client):
    A, c = client
    east = _total(_vm_post(c).data.decode())
    west = _total(_vm_post(c, region='europe-west').data.decode())
    assert east != west


def test_aks_estimate_control_plane(client):
    A, c = client
    data = {'service': 'kubernetes-service', 'tier': 'SLA',
            'size': 'linux-d4sv5-standard', 'nodes': '3', 'hours': '730',
            'region': 'us-east', 'currency': 'usd'}
    data['csrf_token'] = csrf(c, '/pricing/calculator/?service=kubernetes-service')
    page = c.post('/pricing/calculator/?service=kubernetes-service', data=data,
                  follow_redirects=True).data.decode()
    assert _total(page) == '$493.48'  # 0.10*730 + 0.192*730*3
    data['tier'] = 'SLA and Long Term Support'
    data['csrf_token'] = csrf(c, '/pricing/calculator/?service=kubernetes-service')
    page = c.post('/pricing/calculator/?service=kubernetes-service', data=data,
                  follow_redirects=True).data.decode()
    assert _total(page) == '$858.48'  # 0.60*730 + 420.48


def test_storage_graduated_tiers(client):
    A, c = client
    data = {'service': 'storage', 'capacity_gb': '60000', 'write_10k': '100',
            'read_10k': '1000', 'region': 'us-east', 'currency': 'usd'}
    data['csrf_token'] = csrf(c, '/pricing/calculator/?service=storage')
    page = c.post('/pricing/calculator/?service=storage', data=data,
                  follow_redirects=True).data.decode()
    # 51200*0.021 + 8800*0.02 + 100*0.065 + 1000*0.005
    assert _total(page) == '$1,262.70'


def test_cosmos_estimate_modes(client):
    A, c = client
    data = {'service': 'cosmos-db', 'mode': 'single', 'ru_s': '400',
            'storage_gb': '100', 'gateway': 'no', 'region': 'us-east',
            'currency': 'usd'}
    data['csrf_token'] = csrf(c, '/pricing/calculator/?service=cosmos-db')
    page = c.post('/pricing/calculator/?service=cosmos-db', data=data,
                  follow_redirects=True).data.decode()
    # 0.008*4*730 + 0.25*100
    assert _total(page) == '$48.36'
    data['mode'] = 'multiple'
    data['csrf_token'] = csrf(c, '/pricing/calculator/?service=cosmos-db')
    page = c.post('/pricing/calculator/?service=cosmos-db', data=data,
                  follow_redirects=True).data.decode()
    # 0.016*4*730 + 25
    assert _total(page) == '$71.72'


def test_unavailable_combination_shows_error(client):
    A, c = client
    # a size that is not priced in the picked region
    page = _vm_post(c, size='linux-e96sv5-standard', region='brazil-south')
    body = page.data.decode()
    assert 'not available in the selected region' in body


def test_save_estimate_requires_login(client):
    A, c = client
    tok = csrf(c, '/pricing/calculator/')
    r = c.post('/pricing/calculator/save',
               data={'csrf_token': tok, 'service': 'virtual-machines'},
               follow_redirects=False)
    assert r.status_code == 302
    assert '/account/login' in r.headers['Location']


def test_save_and_delete_estimate(client):
    A, c = client
    tok = csrf(c, '/account/login')
    c.post('/account/login', data={'csrf_token': tok, 'email': 'alice.chen@test.com',
                                    'password': 'TestPass123!'}, follow_redirects=True)
    data = {'service': 'virtual-machines', 'size': 'linux-d4sv5-standard',
            'quantity': '3', 'hours': '730', 'region': 'us-east',
            'currency': 'usd', 'name': 'Test estimate'}
    data['csrf_token'] = csrf(c, '/pricing/calculator/')
    r = c.post('/pricing/calculator/save', data=data, follow_redirects=True)
    assert 'Test estimate' in r.data.decode()
    assert '$420.48' in r.data.decode()
    page = c.get('/account/').data.decode()
    est_id = re.search(r'/account/estimates/(\d+)/delete', page).group(1)
    tok = csrf(c, '/account/')
    r = c.post(f'/account/estimates/{est_id}/delete', data={'csrf_token': tok},
               follow_redirects=True)
    assert 'Estimate deleted' in r.data.decode()
    assert 'No saved estimates yet' in r.data.decode()


def test_save_estimate_cannot_touch_other_users(client):
    A, c = client
    tok = csrf(c, '/account/login')
    c.post('/account/login', data={'csrf_token': tok, 'email': 'bob.alvarez@test.com',
                                    'password': 'TestPass123!'}, follow_redirects=True)
    # bob has no estimates; deleting a nonexistent id must 404
    tok = csrf(c, '/account/login')
    r = c.post('/account/estimates/1/delete', data={'csrf_token': tok},
               follow_redirects=False)
    assert r.status_code == 404


def test_favorite_toggle_flow(client):
    A, c = client
    tok = csrf(c, '/account/login')
    c.post('/account/login', data={'csrf_token': tok, 'email': 'carol.ito@test.com',
                                    'password': 'TestPass123!'}, follow_redirects=True)
    tok = csrf(c, '/products/cosmos-db/')
    r = c.post('/favorites/toggle', data={'csrf_token': tok,
                                           'product_slug': 'cosmos-db',
                                           'next': '/products/cosmos-db/'},
               follow_redirects=True)
    assert 'Added Azure Cosmos DB to your favorites' in r.data.decode()
    tok = csrf(c, '/products/cosmos-db/')
    r = c.post('/favorites/toggle', data={'csrf_token': tok,
                                           'product_slug': 'cosmos-db',
                                           'next': '/products/cosmos-db/'},
               follow_redirects=True)
    assert 'Removed Azure Cosmos DB' in r.data.decode()


def test_favorite_requires_login(client):
    A, c = client
    tok = csrf(c, '/account/login')
    r = c.post('/favorites/toggle',
               data={'csrf_token': tok, 'product_slug': 'cosmos-db'},
               follow_redirects=False)
    assert r.status_code == 302
