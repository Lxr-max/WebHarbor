"""Contract tests: every route renders, real data is present, filters work,
CSRF is enforced on every mutating endpoint, and the seed is complete."""
import json
import re

from conftest import csrf


def test_health_counts(client):
    A, c = client
    data = json.loads(c.get('/_health').data)
    assert data['ok'] is True
    assert data['products'] >= 130
    assert data['product_pages'] >= 20
    assert data['pricing_cards'] == 50
    assert data['regions'] >= 55
    assert data['free_services'] >= 80
    assert data['stories'] >= 140
    assert data['dict_articles'] >= 80
    assert data['blog_posts'] >= 20
    assert data['support_plans'] == 4
    assert data['users'] == 4
    assert data['vm_prices'] >= 2500


def test_all_routes_render(client):
    A, c = client
    paths = ['/', '/products/', '/products/kubernetes-service/',
             '/products/cosmos-db/', '/products/nope/'[:0] or '/products/functions/',
             '/pricing/', '/pricing/calculator/',
             '/pricing/calculator/?service=kubernetes-service',
             '/pricing/calculator/?service=storage',
             '/pricing/calculator/?service=cosmos-db',
             '/pricing/details/kubernetes-service/',
             '/pricing/details/virtual-machines-linux/',
             '/pricing/details/cosmos-db/', '/pricing/details/managed-disks/',
             '/pricing/free-services/',
             '/explore/global-infrastructure/geographies/',
             '/explore/global-infrastructure/geographies/sweden/',
             '/explore/global-infrastructure/products-by-region/',
             '/customer-stories/',
             '/customer-stories/27388-canlak-coatings-microsoft-fabric/',
             '/blog/', '/blog/gpt-6-astra-sol-and-luna-for-production-agents-in-microsoft-foundry/',
             '/resources/cloud-computing-dictionary/',
             '/resources/cloud-computing-dictionary/what-is-a-container/',
             '/support/', '/search/?q=kubernetes', '/account/login',
             '/account/signup']
    for p in paths:
        r = c.get(p)
        assert r.status_code == 200, f'{p} -> {r.status_code}'


def test_404(client):
    A, c = client
    assert c.get('/products/does-not-exist/').status_code == 404
    assert c.get('/pricing/details/nope/').status_code == 404


def test_products_category_filter_and_search(client):
    A, c = client
    page = c.get('/products/?category=Compute').data.decode()
    n_all = len(re.findall(r'product-card"', page))
    assert n_all == 17
    page = c.get('/products/?q=kubernetes').data.decode()
    assert 'Azure Kubernetes Service (AKS)' in page
    page = c.get('/products/?q=zzzznotfound').data.decode()
    assert 'No products match' in page


def test_free_services_filters(client):
    A, c = client
    page = c.get('/pricing/free-services/?category=databases&period=12+months+free').data.decode()
    assert 'Azure Cosmos DB' in page
    assert '400 request units' in page
    page = c.get('/pricing/free-services/?period=Always+free').data.decode()
    assert 'Azure Kubernetes Service (AKS)' in page


def test_stories_filters(client):
    A, c = client
    page = c.get('/customer-stories/?industry=Healthcare').data.decode()
    assert len(re.findall(r'story-card"', page)) == 20
    page = c.get('/customer-stories/?industry=Healthcare&product=Azure+Kubernetes+Service').data.decode()
    assert len(re.findall(r'story-card"', page)) == 2
    page = c.get('/customer-stories/?q=canlak').data.decode()
    assert 'Canlak' in page


def test_dictionary_search(client):
    A, c = client
    page = c.get('/resources/cloud-computing-dictionary/?q=vector').data.decode()
    assert 'vector database' in page.lower()
    page = c.get('/resources/cloud-computing-dictionary/?q=zzznope').data.decode()
    assert 'No articles match' in page


def test_blog_category_filter(client):
    A, c = client
    page = c.get('/blog/?category=announcements').data.decode()
    assert len(re.findall(r'story-card"', page)) == 7


def test_site_search_sections(client):
    A, c = client
    page = c.get('/search/?q=kubernetes').data.decode()
    assert 'Products' in page and 'Documentation' in page
    assert re.search(r'\d+ results? for', page)


def test_geographies_and_availability(client):
    A, c = client
    page = c.get('/explore/global-infrastructure/geographies/').data.decode()
    assert 'Sweden' in page
    page = c.get('/explore/global-infrastructure/geographies/sweden/').data.decode()
    assert 'Sweden Central' in page
    assert 'Available' in page
    page = c.get('/explore/global-infrastructure/products-by-region/'
                 '?service=virtual-machines&region=us-east&region=europe-west').data.decode()
    assert 'D4SV5 (Linux)' in page
    assert '0.1920' in page


def test_csrf_enforced(client):
    A, c = client
    # login without token fails
    r = c.post('/account/login', data={'email': 'alice.chen@test.com',
                                        'password': 'TestPass123!'})
    assert r.status_code == 400
    # favorite without token fails
    r = c.post('/favorites/toggle', data={'product_slug': 'cosmos-db'})
    assert r.status_code == 400
    # calculator submit without token fails
    r = c.post('/pricing/calculator/', data={'service': 'virtual-machines',
                                              'size': 'linux-d4sv5-standard'})
    assert r.status_code == 400
    # signup without token fails
    r = c.post('/account/signup', data={'name': 'X', 'email': 'x@x.com',
                                          'password': 'password1'})
    assert r.status_code == 400


def test_benchmark_accounts_login(client):
    A, c = client
    for email in ('alice.chen@test.com', 'bob.alvarez@test.com',
                  'carol.ito@test.com', 'dana.osei@test.com'):
        tok = csrf(c, '/account/login')
        r = c.post('/account/login', data={'csrf_token': tok, 'email': email,
                                            'password': 'TestPass123!'},
                   follow_redirects=True)
        assert r.status_code == 200
        assert 'Signed in as' in r.data.decode()
        c.get('/account/logout')


def test_saved_state_isolation(client):
    A, c = client
    tok = csrf(c, '/account/login')
    c.post('/account/login', data={'csrf_token': tok, 'email': 'alice.chen@test.com',
                                    'password': 'TestPass123!'}, follow_redirects=True)
    # alice sees no estimates or favorites on a fresh seed
    page = c.get('/account/').data.decode()
    assert 'No saved estimates yet' in page
    assert 'No favorites yet' in page


def test_free_services_category_filter_ui(client):
    """F-2 regression: the category dropdown submits real category values,
    not tuple reprs, so every category filter matches through the UI."""
    A, c = client
    page = c.get('/pricing/free-services/').data.decode()
    sel = re.search(r'<select name="category"[^>]*>(.*?)</select>', page, re.S).group(1)
    options = re.findall(r'<option value="([^"]*)"[^>]*>([^<]*)</option>', sel)
    assert options and options[0] == ('', 'All categories')
    for value, label in options[1:]:
        # a tuple repr like ('storage',) must never appear as an option value
        assert value and not value.startswith('(') and not value.endswith(')')
        assert "'," not in value and '"' not in value
    values = {v for v, _ in options}
    assert 'storage' in values and 'compute' in values and 'databases' in values
    # submitting the rendered storage option through the UI matches services
    page = c.get('/pricing/free-services/?category=storage').data.decode()
    assert len(re.findall(r'free-card"', page)) == 4
    assert 'Azure Blob Storage' in page
    assert '12 months free' in page
    # a category with always-free services still filters through the UI
    page = c.get('/pricing/free-services/?category=compute&period=Always+free').data.decode()
    assert len(re.findall(r'free-card"', page)) == 6


def test_linux_vm_pricing_details_reachable(client):
    """F-1 regression: the Linux Virtual Machines pricing details page is
    reachable through visible elements — the pricing hub card and the VM
    product page pricing button — and the canonical upstream VM pricing
    URL redirects to it instead of 404."""
    A, c = client
    # the pricing hub card links to the captured Linux VMs details page
    page = c.get('/pricing/').data.decode()
    m = re.search(r'<a class="pricing-card" href="([^"]*)">\s*'
                  r'<img[^>]*>\s*<span>Azure Virtual Machines</span>', page)
    assert m, 'Azure Virtual Machines card missing from the pricing hub'
    assert m.group(1) == '/pricing/details/virtual-machines-linux/'
    # the details page itself renders with the captured tables
    page = c.get(m.group(1)).data.decode()
    assert 'Linux Virtual Machines' in page
    assert 'Deleted (Deallocated)' in page
    # the VM product page pricing button points at the same details page
    page = c.get('/products/virtual-machines/').data.decode()
    m = re.search(r'href="([^"]*)">Explore Virtual Machines pricing</a>', page)
    assert m, 'VM product page pricing button missing'
    assert m.group(1) == '/pricing/details/virtual-machines-linux/'
    # the upstream-shaped canonical URL no longer 404s: it redirects
    r = c.get('/pricing/details/virtual-machines/')
    assert r.status_code == 301
    assert r.headers['Location'].endswith('/pricing/details/virtual-machines-linux/')
    r = c.get('/pricing/details/virtual-machines/', follow_redirects=True)
    assert r.status_code == 200
    assert 'Deleted (Deallocated)' in r.data.decode()
