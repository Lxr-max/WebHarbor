"""Contract tests: every route family renders real upstream-sourced content."""
import json
import re


def _get(client, path):
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"
    return resp.get_data(as_text=True)


def test_health(client):
    data = json.loads(client.get('/_health').get_data())
    assert data['ok'] is True
    assert data['site'] == 'u_s_customs'
    assert data['pages'] >= 40
    assert data['crossings'] >= 80
    assert data['ports'] >= 300
    assert data['releases'] >= 40
    assert data['forms'] >= 90
    assert data['jobs'] >= 40
    assert data['users'] == 4


def test_homepage(client):
    html = _get(client, '/')
    for marker in ['U.S. Customs and Border Protection', 'Apply for an ESTA',
                   'Border Wait Times', 'Locate a Port of Entry',
                   'Latest News Releases', 'CBP Forms']:
        assert marker in html, f"homepage missing {marker!r}"


def test_travel_pages(client):
    html = _get(client, '/travel/international-visitors/esta')
    assert 'Electronic System for Travel Authorization' in html
    assert '40.27' in html
    html = _get(client, '/travel/international-visitors/i-94')
    assert 'Arrival/Departure Forms: I-94' in html
    html = _get(client, '/travel/international-visitors/visa-waiver-program')
    assert '42 countries' in html
    html = _get(client, '/travel/us-citizens/know-before-you-go')
    assert 'Know Before You Go' in html


def test_ttp_pages(client):
    html = _get(client, '/travel/trusted-traveler-programs')
    assert 'Global Entry' in html and 'NEXUS' in html
    assert '$120.00' in html and '$50.00' in html and '$122.25' in html
    html = _get(client, '/travel/trusted-traveler-programs/global-entry')
    assert 'Global Entry' in html and '$120.00' in html
    html = _get(client, '/travel/trusted-traveler-programs/nexus')
    assert 'NEXUS' in html
    html = _get(client, '/travel/trusted-traveler-programs/tsa-precheck')
    assert 'TSA PreCheck' in html


def test_bwt_listing(client):
    html = _get(client, '/bwt')
    assert 'Border Wait Times' in html
    assert 'San Ysidro' in html
    html = _get(client, '/bwt?border=canada')
    assert 'Blaine' in html
    html = _get(client, '/bwt?border=mexico&sort=delay')
    assert 'Otay Mesa' in html
    # every lane cell renders its open-lane count (`open` JSON key)
    assert '185 min · 3 open' in html
    assert re.search(r'\d+ min · \d+ open', html)


def test_bwt_crossing_detail(client):
    html = _get(client, '/bwt/crossing/250601')
    assert 'Otay Mesa' in html
    assert '185' in html
    assert 'Ready Lanes' in html


def test_ports_directory(client):
    html = _get(client, '/contact/ports')
    assert 'Locate a Port of Entry' in html
    assert 'California' in html
    html = _get(client, '/about/contact/ports/CA')
    assert 'Calexico East' in html
    html = _get(client,
                '/contact/ports/calexico-east-class-california-2507')
    assert '2507' in html
    assert '+1 760-768-8282' in html
    assert 'Roque Caza' in html


def test_newsroom(client):
    html = _get(client, '/newsroom/media-releases/all')
    assert 'Media Releases' in html
    html = _get(client, '/newsroom/media-releases/all?q=khat')
    assert 'khat' in html.lower()
    html = _get(client,
                '/newsroom/local-media-release/new-york-man-arrested-after-cbp-officers-seize-65-pounds-khat')
    assert 'Bakari Wally' in html
    assert 'Washington Dulles International Airport' in html


def test_forms_catalog(client):
    html = _get(client, '/newsroom/publications/forms')
    assert 'CBP Form 7501' in html
    html = _get(client,
                '/newsroom/publications/forms/7501-entry-summary-with-continuation-sheets')
    assert 'Entry Summary with Continuation Sheets' in html
    pdf = client.get('/forms/download/7501-entry-summary-with-continuation-sheets')
    assert pdf.status_code == 200
    assert pdf.get_data()[:8] == b'%PDF-1.7'


def test_trade_pages(client):
    html = _get(client, '/trade/basic-import-export/importing-car')
    assert 'Motor Vehicle Safety Act of 1966' in html
    html = _get(client, '/trade/priority-issues')
    assert 'Antidumping and Countervailing Duty' in html
    html = _get(client, '/trade/rulings/informed-compliance-publications')
    assert 'Informed Compliance' in html


def test_content_page_related_links(client):
    # content pages render the internal links scraped upstream, so no
    # content page is a navigation island
    html = _get(client, '/travel/international-visitors')
    assert 'href="/travel/international-visitors/visa-waiver-program"' in html
    assert 'href="/travel/international-visitors/know-before-you-visit"' in html
    html = _get(client, '/trade/basic-import-export')
    assert 'href="/trade/basic-import-export/importing-car"' in html
    assert 'href="/trade/basic-import-export/internet-purchases"' in html
    html = _get(client, '/travel/us-citizens')
    assert 'href="/travel/us-citizens/canada-mexico-travel"' in html


def test_priority_issues_links_resolve(client):
    # every Priority Trade Issues child link must resolve (hyphen routes)
    html = _get(client, '/trade/priority-issues')
    hrefs = re.findall(r'<li><a href="(/trade/priority-issues/[^"]*)">', html)
    assert len(hrefs) == 7
    for href in hrefs:
        resp = client.get(href)
        assert resp.status_code == 200, f'{href} -> {resp.status_code}'


def test_careers_search_acronym(client):
    # "CBP Officer" must also match "Customs and Border Protection Officer"
    html = _get(client, '/careers/search?q=CBP+Officer')
    assert '/careers/job/882166800' in html
    assert '/careers/job/886464900' in html


def test_forms_catalog_6059b_variants(client):
    html = _get(client, '/newsroom/publications/forms?q=6059B')
    # all 18 variants render their form number (no dangling "CBP Form " cells)
    assert html.count('CBP Form 6059B') == 18
    assert 'CBP Form </a>' not in html


def test_careers(client):
    html = _get(client, '/careers/search?q=Border+Patrol')
    assert 'Border Patrol Agent' in html
    html = _get(client, '/careers/job/882256600')
    assert '$51,632 - $92,912' in html
    assert '09/30/2026' in html
    html = _get(client, '/careers/events')
    assert 'Fall Hiring Fair' in html


def test_vwp_country_list(client):
    html = _get(client, '/travel/international-visitors/visa-waiver-program')
    for country in ['Germany', 'Italy', 'Qatar', 'Taiwan', 'Chile']:
        assert country in html


def test_site_search(client):
    html = _get(client, '/search?q=Global+Entry')
    assert 'Global Entry' in html
    html = _get(client, '/search?q=San+Ysidro')
    assert 'Border Crossings' in html and 'Ports of Entry' in html


def test_404(client):
    resp = client.get('/no/such/page')
    assert resp.status_code == 404
    assert b'Page not found' in resp.data
