"""Regression tests for the 2026-09-30 review fixes (REPORT.md items 1-3
and the snapshot-date alignment):

  1. photo URLs must render as /static/images/... — the stored repo-relative
     "static/..." prefix is stripped once in photo_list() so url_for('static')
     does not double it to /static/static/... (156/156 sampled 404s before);
  2. a real browser submits EVERY filter-form control, including the untouched
     selects' empty "All ..." values — the four slug params
     (exterior_color_slugs / fuel_slugs / transmission_slugs /
     drivetrain_slugs) need the same empty-value guard as the other 12
     filter params or any form submission returns 0 results;
  3. the model/compare pages' "See all listings/results" links must emit
     models[] (the spelling the SERP sort form, filter form and select
     state round-trip) or the model filter is silently dropped on the
     first sort/Update interaction;
  4. the mirror stamp is the real capture day (2026-09-29, provenance.json
     captured_at) while the benchmark seed rows keep their frozen fixture
     stamp (the seed DB is byte-frozen by the grading contract).
"""
import html
import json
import re


def _serp_count(body):
    m = re.search(r'class="result-count-pill">(\d+) results', body)
    assert m, "no result count rendered"
    return int(m.group(1))


def _card_titles(body):
    return re.findall(r'class="card-title">\s*<a[^>]*>([^<]+)</a>', body)


def _first_img_src(body):
    m = re.search(r'<img src="(/static/[^"]+)"', body)
    assert m, "no image rendered"
    return m.group(1)


def _hrefs(body, label):
    """The SERP hrefs for a link label, HTML-unescaped like a browser."""
    return [html.unescape(h) for h in
            re.findall(r'href="(/shopping/results/\?[^"]*)"[^>]*>' + label,
                       body)]


def test_srp_images_render(client):
    """Fix 1: SERP card photos render at /static/images/... and resolve 200."""
    r = client.get('/shopping/results/?stock_type=used')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert '/static/static/' not in body, "double /static/static/ prefix is back"
    src = _first_img_src(body)
    assert src.startswith('/static/images/upstream/'), src
    img = client.get(src)
    assert img.status_code == 200, f"{src} -> {img.status_code}"
    assert len(img.get_data()) > 1000  # a real JPEG, not an error page


def test_vdp_and_research_images_render(client):
    """Fix 1: VDP gallery, model page and compare page photos resolve 200."""
    from app import Listing, ModelPage
    with client.application.app_context():
        lid = Listing.query.filter(Listing.photos.isnot(None)).first().id
        slug = ModelPage.query.filter(ModelPage.photos.isnot(None)).first().slug
    r = client.get(f'/vehicledetail/{lid}/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert '/static/static/' not in body
    srcs = re.findall(r'<img[^>]+src="(/static/[^"]+)"', body)
    assert srcs, "no VDP photos rendered"
    for src in srcs[:6]:
        assert client.get(src).status_code == 200, src

    r = client.get(f'/research/{slug}/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert '/static/static/' not in body
    for src in re.findall(r'<img[^>]+src="(/static/[^"]+)"', body)[:4]:
        assert client.get(src).status_code == 200, src

    r = client.get('/research/compare/honda-civic-vs-toyota-corolla/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert '/static/static/' not in body
    for src in re.findall(r'<img[^>]+src="(/static/[^"]+)"', body)[:2]:
        assert client.get(src).status_code == 200, src


def test_filter_form_browser_submission(client):
    """Fix 2: a browser submits every select, empty ones included — the
    four unguarded slug params must not turn that into 0 results."""
    # exactly what the filter form posts with only body style + stock set
    browser_style = ('/shopping/results/?stock_type=used&list_price_min=&'
                     'list_price_max=&mileage_max=&deal_ratings=&seller_type=&'
                     'year_min=&year_max=&makes[]=&models[]=&keyword=&'
                     'body_style_slugs=suv&exterior_color_slugs=&fuel_slugs=&'
                     'transmission_slugs=&drivetrain_slugs=&cylinder_counts=&'
                     'maximum_distance=&zip=98101')
    r = client.get(browser_style)
    assert r.status_code == 200
    assert _serp_count(r.get_data(as_text=True)) == 190, \
        "used SUVs must still be 190 with the empty selects submitted"


def test_empty_slug_params_never_filter(client):
    """Fix 2: each of the four params with an empty value alone is a no-op."""
    total = _serp_count(client.get('/shopping/results/').get_data(as_text=True))
    assert total == 736
    for param in ('exterior_color_slugs', 'fuel_slugs', 'transmission_slugs',
                  'drivetrain_slugs'):
        body = client.get(f'/shopping/results/?{param}=')
        assert _serp_count(body.get_data(as_text=True)) == total, param


def test_slug_params_still_filter_when_set(client):
    """Fix 2 positive control: setting the params still narrows results."""
    cases = {'fuel_slugs=electric': 101, 'transmission_slugs=manual': 27,
             'drivetrain_slugs=all_wheel_drive': 316,
             'exterior_color_slugs=black': 138}
    for qs, expected in cases.items():
        body = client.get(f'/shopping/results/?{qs}').get_data(as_text=True)
        assert _serp_count(body) == expected, qs


def test_model_page_listings_link_uses_models_bracket(client):
    """Fix 3: the model page's See-all-listings link emits models[] so the
    SERP round-trips it through the sort form and the filter panel."""
    r = client.get('/research/honda-civic-2026/')
    assert r.status_code == 200
    hrefs = _hrefs(r.get_data(as_text=True), 'See all listings')
    assert hrefs, "no See-all-listings link"
    href = hrefs[0]
    assert 'models%5B%5D=honda-civic' in href or 'models[]=honda-civic' in href, href
    body = client.get(href).get_data(as_text=True)
    assert _serp_count(body) == 68, "all-stock Civic listings must be 68"
    assert all('Civic' in t for t in _card_titles(body))


def test_model_filter_survives_sort_roundtrip(client):
    """Fix 3: sorting from the model-linked SERP keeps the model filter —
    the cheapest Civic stays a Civic (was a $2,500 Nissan Rogue before)."""
    r = client.get('/shopping/results/?stock_type=all&models%5B%5D=honda-civic'
                   '&sort=list_price_asc')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert _serp_count(body) == 68
    titles = _card_titles(body)
    assert titles and all('Civic' in t for t in titles), titles[:3]
    first_id = re.search(r'id="vehicle-card-([0-9a-f-]{36})"', body).group(1)
    assert first_id == '659632f3-b6f0-4128-9e3a-1fccff084bcc', \
        "the cheapest Civic listing must stay first after sorting"
    price = re.search(r'class="price">\$([\d,]+)', body).group(1)
    assert price == '8,971', price


def test_compare_page_results_links_use_models_bracket(client):
    """Fix 3: both compare-page See-all-results links emit models[]. The
    Civic column has 45 new listings; the Corolla column has none in the
    frozen corpus (its honest empty state must render, not a crash)."""
    r = client.get('/research/compare/honda-civic-vs-toyota-corolla/')
    assert r.status_code == 200
    hrefs = _hrefs(r.get_data(as_text=True), 'See all results')
    assert len(hrefs) == 2, hrefs
    counts = []
    for href in hrefs:
        assert 'models%5B%5D=' in href or 'models[]=' in href, href
        body = client.get(href).get_data(as_text=True)
        counts.append((_serp_count(body), href))
    by_count = {n: h for n, h in counts}
    assert 45 in by_count, counts
    civic_body = client.get(by_count[45]).get_data(as_text=True)
    assert all('Civic' in t for t in _card_titles(civic_body))
    assert 0 in by_count, counts
    empty_body = client.get(by_count[0]).get_data(as_text=True)
    assert 'No results match those filters' in empty_body


def test_mirror_stamp_is_real_capture_day(client):
    """Fix 4: pages stamp the real capture day; provenance agrees."""
    import app as cars_app
    from pathlib import Path
    r = client.get('/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert '2026-09-29' in body, "the mirror stamp must be the capture day"
    assert '2026-10-13' not in body
    prov = json.loads((Path(cars_app.BASE_DIR) / 'provenance.json')
                      .read_text(encoding='utf-8'))
    assert prov['captured_at'] == cars_app.MIRROR_TS == prov['mirror_date']


def test_seed_rows_keep_frozen_fixture_stamp(client):
    """Fix 4: the benchmark seed keeps its frozen fixture stamp (the seed
    DB is byte-frozen by the grading contract) even though MIRROR_TS moved
    to the real capture day; rows written at run time stamp MIRROR_TS."""
    import app as cars_app
    from app import db, SavedCar, SavedSearch
    assert cars_app.SEED_STAMP == '2026-10-13'
    assert cars_app.MIRROR_TS == '2026-09-29'
    with client.application.app_context():
        stamps = {row.saved_at for row in SavedCar.query.all()}
        stamps |= {row.created_at for row in SavedSearch.query.all()}
    assert cars_app.SEED_STAMP in stamps, stamps
    assert stamps <= {cars_app.SEED_STAMP, cars_app.MIRROR_TS}, stamps
