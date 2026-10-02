"""Contract tests: every route family renders real content from the seed."""
import json
import re


def _get(client, path):
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"
    return resp.get_data(as_text=True)


def test_health(client):
    resp = client.get('/_health')
    assert resp.status_code == 200
    data = json.loads(resp.get_data())
    assert data['ok'] is True
    assert data['site'] == 'tourradar'
    assert data['tours'] >= 50
    assert data['departures'] >= 100


def test_homepage(client):
    html = _get(client, '/')
    for marker in ['Top deals', 'Traveler Moments', 'Popular Destinations',
                   'Travel With The Best Tour Operators', 'Escape Sale']:
        assert marker in html, f"homepage missing {marker!r}"
    assert '/t/' in html


def test_destination_landing(client):
    html = _get(client, '/d/japan')
    assert 'Japan Tours &amp; Trips' in html or 'Japan Tours' in html
    assert 'View Tours' in html
    assert 'tour-card' in html


def test_serp_with_filters(client):
    html = _get(client, '/srp/d-japan')
    assert 'tours found' in html
    assert 'Duration' in html and 'Adventure styles' in html
    html = _get(client, '/srp/d-japan?price_max=3000&sort=price_asc')
    assert 'tours found' in html
    prices = [int(p.replace(',', '')) for p in
              re.findall(r'class="price-now">US\$([\d,]+)</span>', html)]
    assert prices == sorted(prices), "price_asc sort broken"
    for p in prices:
        assert p <= 3000


def test_style_region_place_serp(client):
    for path in ['/srp/f-safari', '/srp/b-south-america',
                 '/srp/v-islands-bali', '/srp/i-africa-safari']:
        html = _get(client, path)
        assert 'tours found' in html


def test_tour_detail(client):
    html = _get(client, '/t/255')
    for marker in ['Itinerary', "What's Included", 'Good to Know',
                   'Traveler Reviews', "Dates &amp; Prices", 'Operated by']:
        assert marker in html, f"tour detail missing {marker!r}"
    assert 'MacBackpackers' in html
    assert 'day-head' in html


def test_tour_reviews_page(client):
    html = _get(client, '/t/255/reviews')
    assert 'Overall rating based on' in html
    assert 'Traveled in' in html or 'reply' in html


def test_operator_page(client):
    html = _get(client, '/o/macbackpackers')
    assert 'MacBackpackers' in html
    assert 'Reviews' in html
    assert '/t/' in html


def test_search_scored(client):
    html = _get(client, '/search?q=japan%20safari')
    assert 'Results for' in html
    html = _get(client, '/search?q=nile%20cruise')
    assert '/t/' in html


def test_suggest_api(client):
    resp = client.get('/api/suggest?q=jap')
    assert resp.status_code == 200
    rows = json.loads(resp.get_data())
    assert rows and any('Japan' in r['label'] for r in rows)


def test_static_pages(client):
    for path, marker in [
        ('/about', 'About TourRadar'), ('/contact', '24/7 Customer Support'),
        ('/trust', 'Why should I use TourRadar'),
        ('/cancellation-policy', 'Cancellation Policy'),
        ('/terms-conditions', 'Terms &amp; Conditions'),
        ('/privacy', 'Privacy Policy'), ('/payments', 'Payments'),
        ('/operators-list', 'operators'),
        ('/reviews-of-tourradar', 'Customer Reviews'),
        ('/moments', 'Traveler Moments'), ('/s/solo', 'Solo'),
    ]:
        html = _get(client, path)
        assert marker in html, f"{path} missing {marker!r}"


def test_404_page(client):
    resp = client.get('/t/999999999')
    assert resp.status_code == 404
    assert "couldn't find that page" in resp.get_data(as_text=True)


def test_wishlist_requires_login(client):
    resp = client.get('/wishlists')
    assert resp.status_code == 200
    assert 'Log In' in resp.get_data(as_text=True)


def test_images_served(client):
    from app import Tour
    with tourradar_app_ctx():
        tour = Tour.query.filter(Tour.hero.isnot(None)).first()
    resp = client.get(f'/static/images/{tour.hero}')
    assert resp.status_code == 200
    assert len(resp.get_data()) > 500


def tourradar_app_ctx():
    from app import app
    return app.app_context()


def test_review_lists_newest_first(client):
    """Seed reviews are inserted in upstream display order (newest first), so
    ascending id renders the most recent review first — matching the live
    site's 'Most Recent' list (regression for the inverted-order bug)."""
    html = _get(client, '/t/46923/reviews')
    names = re.findall(r'<div class="name">([^<]+)</div>', html)
    assert names[0] == 'Elisa', f"expected newest review (Elisa) first, got {names[0]!r}"
    assert 'Dwight' not in names[0], 'oldest review must not lead the list'
    # tour detail panel uses the same ordering
    html = _get(client, '/t/46923')
    names = re.findall(r'<div class="name">([^<]+)</div>', html)
    assert names[0] == 'Elisa', f"tour detail panel must lead with the newest review"


def test_operator_page_reviews_newest_first(client):
    html = _get(client, '/o/expat-explore-travel')
    names = re.findall(r'<div class="name">([^<]+)</div>', html)
    assert names and names[0] == 'Adebabay', \
        f"operator panel must lead with the newest review, got {names[0]!r}"


def test_footer_and_home_links_resolve(client):
    """Every footer destination link and homepage Popular Destinations chip
    must resolve (regression for the /srp/d-north-america and
    /deals/australia 404s)."""
    html = _get(client, '/')
    hrefs = set(re.findall(r'href="(/(?:d|b|f|srp|deals)/[^"#]+)"', html))
    assert hrefs, 'home page exposes no internal links'
    for href in sorted(hrefs):
        resp = client.get(href)
        assert resp.status_code == 200, f"home link {href} -> {resp.status_code}"
    # the previously-dead footer group links now point at real pages
    for href in ('/d/africa', '/d/asia', '/d/australia', '/d/europe',
                 '/d/latin-america', '/b/south-america'):
        resp = client.get(href)
        assert resp.status_code == 200, f"{href} -> {resp.status_code}"
    assert client.get('/deals/australia-oceania').status_code == 200


def test_no_intro_summary_day_titles():
    """No itinerary day block may carry the scraped 'Intro'/'Summary' section
    header as its title (regression for the 31-tour residue)."""
    import app as appmod
    with appmod.app.app_context():
        Tour = appmod.Tour
        bad = []
        for t in Tour.query.all():
            for d in t.days_list:
                if d.get('title') in ('Intro', 'Summary'):
                    bad.append((t.id, d['day']))
        assert not bad, f"day blocks still titled Intro/Summary: {bad[:5]}"
    # spot-check the reviewer's examples against upstream titles
    with appmod.app.app_context():
        Tour = appmod.Tour
        t = Tour.query.get(244895)
        assert t.days_list[-1]['title'] == 'Departure'
        t = Tour.query.get(52308)
        assert t.days_list[-1]['title'] == 'Montreal'
        t = Tour.query.get(33509)
        assert t.days_list[-1]['title'] == 'Bomerano'
