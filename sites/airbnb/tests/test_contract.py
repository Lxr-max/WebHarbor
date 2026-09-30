"""Contract tests: seeded data, public pages, CSRF on every POST form,
asset integrity and the search/filter semantics."""
import hashlib
import json
import os
import re

import app as ab
from conftest import with_csrf


# ------------------------------------------------------------------- seeds --

def test_seed_counts():
    with ab.app.app_context():
        assert ab.Destination.query.count() == 8
        assert ab.Listing.query.count() >= 80
        assert ab.Experience.query.count() >= 40
        assert ab.Review.query.count() >= 200
        assert ab.User.query.count() == 4
        assert ab.Wishlist.query.count() >= 5
        assert ab.Booking.query.count() >= 3
        # every listing carries captured content
        for lst in ab.Listing.query.all():
            assert lst.name
            assert lst.title
            assert lst.city
            assert lst.nightly_price and lst.nightly_price > 0
            assert lst.photo_list(), f"listing {lst.id} has no photos"
        # the corpus is listing pages with full captures: amenity trees,
        # availability calendars and review lists (a handful of upstream
        # hotel-style listings don't expose a calendar at all)
        n_cal = sum(1 for lst in ab.Listing.query.all() if lst.calendar_map())
        n_amen = sum(1 for lst in ab.Listing.query.all() if lst.amenity_groups())
        assert n_cal >= 84
        assert n_amen >= 88
        assert ab.Review.query.count() >= 200


def test_every_listing_photo_is_a_managed_local_asset():
    """Review B1: no listing may carry a NULL (or remote) photo URI — every
    gallery comes from the captured ld_images/card photo URLs and maps to
    an inventoried local file."""
    inv = json.load(open(os.path.join(ab.BASE_DIR, 'asset_inventory.json')))
    paths = {row['path'] for row in inv['assets']}
    with ab.app.app_context():
        for lst in ab.Listing.query.all():
            photos = lst.photo_list()
            assert photos, f"listing {lst.id}: empty photo list"
            for p in photos:
                uri = p.get('uri')
                assert uri, f"listing {lst.id}: NULL photo uri"
                assert uri.startswith('/static/images/upstream/'), \
                    f"listing {lst.id}: non-local photo uri {uri!r}"
                assert uri.lstrip('/') in paths, \
                    f"listing {lst.id}: photo {uri} not in the asset inventory"


def test_serp_cards_show_review_counts(client):
    """Review H1: each rated SERP card renders its review count."""
    with ab.app.app_context():
        top = (ab.Listing.query
               .order_by(ab.Listing.reviews_count.desc()).first())
    body = client.get(f'/s/{top.destination_slug}/homes') \
        .get_data(as_text=True)
    assert f'&#9733; {top.rating} <span class="revcount">({top.reviews_count})</span>' in body


def test_benchmark_password_frozen():
    with ab.app.app_context():
        alice = ab.User.query.filter_by(email='alice.j@test.com').first()
        assert alice is not None
        assert ab.bcrypt.check_password_hash(alice.password_hash,
                                             'TestPass123!')


def test_health_ok(client):
    r = client.get('/_health')
    assert r.status_code == 200
    data = json.loads(r.get_data(as_text=True))
    assert data['ok'] is True
    assert data['listings'] >= 80
    assert data['experiences'] >= 40


def test_every_seed_image_is_real_upstream():
    """Every image served from static/images/upstream is inventoried with
    an https source URL, exact byte length and sha256 (no placeholders)."""
    inv = json.load(open(os.path.join(ab.BASE_DIR, 'asset_inventory.json')))
    rows = inv['assets']
    assert inv['asset_count'] == len(rows) == len({r['path'] for r in rows})
    for row in rows:
        path = os.path.join(ab.BASE_DIR, row['path'])
        data = open(path, 'rb').read()
        assert len(data) == row['bytes']
        assert row['source_url'].startswith('https://')
        assert hashlib.sha256(data).hexdigest() == row['sha256']
        assert len(data) > 1000, f"placeholder-sized image: {row['path']}"


def test_rendered_images_are_managed(client):
    """No <img src> in any public page may point outside managed assets —
    every image must be a local /static/images/ path (or an inline data: URI);
    raw upstream CDN URLs are a defect (they break offline)."""
    with ab.app.app_context():
        lst = ab.Listing.query.first()
        exp = ab.Experience.query.first()
        exp_with_agenda = next(e for e in ab.Experience.query.all()
                               if any(a.get('image') for a in e.agenda_list()))
    seen = set()
    for path in ('/', '/s/asheville/homes', f'/rooms/{lst.id}',
                 f'/experiences/{exp.id}', f'/experiences/{exp_with_agenda.id}',
                 '/s/experiences?city=austin'):
        body = client.get(path).get_data(as_text=True)
        for m in re.finditer(r'<img[^>]+src="([^"]+)"', body):
            src = m.group(1)
            assert src.startswith('/static/images/') or src.startswith('data:'), \
                f"{path}: non-managed img src {src!r}"
            if src.startswith('/static/images/'):
                seen.add(src)
    assert seen, "no managed images rendered"
    for s in seen:
        assert os.path.exists(os.path.join(ab.BASE_DIR, s.lstrip('/')))


# ------------------------------------------------------------ public pages --

def test_home(client):
    r = client.get('/')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Find your next stay' in body
    assert 'Asheville' in body
    assert 'Experiences to try' in body


def test_all_destinations_render(client):
    for slug in ('asheville', 'austin', 'new-york', 'los-angeles',
                 'miami', 'lake-tahoe', 'nashville', 'scottsdale'):
        r = client.get(f'/s/{slug}/homes')
        assert r.status_code == 200, slug
        body = r.get_data(as_text=True)
        assert 'Stays in' in body
        assert 'card' in body


def test_pdp_renders(client):
    with ab.app.app_context():
        lst = ab.Listing.query.filter_by(is_guest_favorite=True).first() \
            or ab.Listing.query.first()
    r = client.get(f'/rooms/{lst.id}')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert lst.name in body
    assert 'What this place offers' in body
    assert 'About this space' in body
    assert 'Request to book' in body or 'Check availability' in body


def test_pdp_price_uses_captured_quote(client):
    with ab.app.app_context():
        lst = (ab.Listing.query
               .filter(ab.Listing.quote_total.isnot(None),
                       ab.Listing.quote_checkin.isnot(None))
               .order_by(ab.Listing.quote_total.desc()).first())
    r = client.get(f'/rooms/{lst.id}?checkin={lst.quote_checkin}'
                   f'&checkout={lst.quote_checkout}&adults=2')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert f"{lst.quote_nights} night" in body
    # the captured upstream trip price appears verbatim
    assert '${:,.2f}'.format(lst.quote_total) in body


def test_reviews_page(client):
    with ab.app.app_context():
        lst = ab.Listing.query.filter(ab.Listing.reviews_count > 10).first()
    r = client.get(f'/rooms/{lst.id}/reviews')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Rating breakdown' in body
    assert 'captured reviews' in body


def test_404_for_unknown_listing(client):
    assert client.get('/rooms/doesnotexist99').status_code == 404


def test_experiences_pages(client):
    r = client.get('/s/experiences?city=austin')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Experiences in Austin' in body
    with ab.app.app_context():
        exp = ab.Experience.query.filter_by(city_slug='austin').first()
    r = client.get(f'/experiences/{exp.id}')
    assert r.status_code == 200
    assert exp.name.replace("'", "&#39;") in r.get_data(as_text=True)


def test_csrf_required_on_stateful_posts(client):
    with ab.app.app_context():
        lst = ab.Listing.query.first()
    # no token -> 400 (CSRF enabled)
    r = client.post('/wishlist/add', data={'listing_id': lst.id})
    assert r.status_code == 400
    r = client.post(f'/rooms/{lst.id}/book',
                    data={'checkin': '2026-12-06', 'checkout': '2026-12-11'})
    assert r.status_code == 400
    r = client.post('/login', data={'email': 'a', 'password': 'b'})
    assert r.status_code == 400


# -------------------------------------------------------- search + filters --

def _cards(client, slug, qs=''):
    body = client.get(f'/s/{slug}/homes{qs}').get_data(as_text=True)
    return body.count('class="card"')


def test_search_filter_price(client):
    with ab.app.app_context():
        n_all = ab.Listing.query.filter_by(
            destination_slug='asheville').count()
        priced = (ab.Listing.query
                  .filter(ab.Listing.destination_slug == 'asheville',
                          ab.Listing.quote_total.isnot(None))
                  .order_by(ab.Listing.quote_total).all())
        lo, hi = priced[0].quote_total, priced[-1].quote_total
    all_n = _cards(client, 'asheville')
    assert all_n == n_all
    assert _cards(client, 'asheville', f'?price_min={hi - 1}') < all_n
    assert _cards(client, 'asheville', f'?price_max={lo + 1}') <= all_n


def test_search_filter_guest_favorite_and_superhost(client):
    with ab.app.app_context():
        gf = ab.Listing.query.filter_by(destination_slug='asheville',
                                        is_guest_favorite=True).count()
        sh = ab.Listing.query.filter_by(destination_slug='asheville',
                                        is_superhost=True).count()
    assert _cards(client, 'asheville', '?guest_favorite=1') == gf
    assert _cards(client, 'asheville', '?superhost=1') == sh


def test_search_filter_amenities(client):
    with ab.app.app_context():
        pool = ab.Listing.query.filter(
            ab.Listing.destination_slug == 'asheville',
            ab.Listing.amenity_flags.like('%"pool"%')).count()
    assert _cards(client, 'asheville', '?amenities=pool') == pool


def test_search_sort_price(client):
    body = client.get('/s/asheville/homes?sort=price_asc').get_data(as_text=True)
    prices = [float(p.replace(',', '')) for p in
              re.findall(r'\$([0-9][0-9,]*) for \d+ nights', body)]
    assert prices, "no trip prices rendered"
    assert prices == sorted(prices)


def test_search_date_params_kept(client):
    r = client.get('/s/asheville/homes?checkin=2026-12-06&checkout=2026-12-11&adults=2')
    assert r.status_code == 200
    assert 'name="checkin" value="2026-12-06"' in r.get_data(as_text=True)


# ------------------------------------------------- r2 fix-round contracts --

def test_amenity_panel_renders_canonical_taxonomy(client):
    """Review B2: the panel renders the upstream canonical amenity set
    intersected with the corpus — Hot tub and Pool are checkable in every
    market whose corpus carries them ( Asheville/Lake Tahoe/LA hot tub,
    Scottsdale/Nashville/Miami pool)."""
    for slug, amenity in (('asheville', 'hot tub'), ('lake-tahoe', 'hot tub'),
                          ('los-angeles', 'hot tub'), ('scottsdale', 'pool'),
                          ('nashville', 'pool'), ('miami', 'pool')):
        body = client.get(f'/s/{slug}/homes').get_data(as_text=True)
        assert f'name="amenities" value="{amenity}"' in body, \
            f"{slug}: no {amenity!r} checkbox on the filter panel"
        # canonical labels, not corpus-count long tokens
        label = {'hot tub': 'Hot tub', 'pool': 'Pool'}[amenity]
        assert f'>{label} <span' in body, f"{slug}: no canonical {label} label"


def test_experiences_city_selector(client):
    """Review B3: the experiences SERP renders a destination selector, so
    LA/NYC/Miami experiences are reachable through the UI."""
    body = client.get('/s/experiences').get_data(as_text=True)
    for city_slug, city in (('los-angeles', 'Los Angeles'), ('new-york', 'New York'),
                            ('miami', 'Miami'), ('austin', 'Austin')):
        assert f'href="/s/experiences?city={city_slug}' in body, \
            f"no city chip for {city}"
    body = client.get('/s/experiences?city=los-angeles').get_data(as_text=True)
    assert 'Experiences in Los Angeles' in body


def test_experience_detail_renders_structured_sections(client):
    """Review B4: the experience PDP renders the captured JSON payloads as
    structured text — no Python repr leakage (method/str AND dict-repr
    classes), real min_age values, and badges flattened to their texts."""
    with ab.app.app_context():
        exp = (ab.Experience.query
               .filter(ab.Experience.rating_count > 100).first())
        reqs = exp.requirements()
    body = client.get(f'/experiences/{exp.id}').get_data(as_text=True)
    assert 'built-in method' not in body
    assert 'str object at' not in body
    assert '__typename' not in body
    assert '{&#39;' not in body
    assert 'Things to know' in body
    if reqs.get('min_age') is not None:
        assert f"Minimum age: {reqs['min_age']}" in body
    else:
        assert 'Minimum age: any' in body
    for b in exp.badge_list():
        assert b in body


def test_experience_agenda_titles_render_localized_text(client):
    """Review r2 (B4 residual): every agenda stop title is captured as an
    upstream localized envelope ({'__typename': 'ListingDescription',
    'localizedValue': {'localizedString': ...}}) — the PDP must render the
    inner localizedString, never a Python dict repr. The r2 round's 69/80
    leaking experience pages included the T4/T8/T14 target pages."""
    # the T8 target page's first stop must read its true title
    body = client.get('/experiences/109978').get_data(as_text=True)
    assert '<h3>Step into the cockpit</h3>' in body
    # the T14 / T4 target pages render their first stop titles too
    assert '<h3>Introduction to Revolutionary NYC</h3>' in \
        client.get('/experiences/371834').get_data(as_text=True)
    assert '<h3>Welcome &amp; Break The Ice</h3>' in \
        client.get('/experiences/6190940').get_data(as_text=True)
    # no experience PDP may leak any repr class (dict, method or str)
    with ab.app.app_context():
        eids = [e.id for e in ab.Experience.query.order_by(ab.Experience.id)]
    for eid in eids:
        page = client.get(f'/experiences/{eid}').get_data(as_text=True)
        for marker in ('__typename', '{&#39;', 'built-in method',
                       'str object at', 'object at 0x'):
            assert marker not in page, \
                f"repr leak {marker!r} on /experiences/{eid}"
        assert '<strong>None</strong>' not in page, \
            f"None placeholder on /experiences/{eid}"


def test_listing_pdp_renders_localized_sections(client):
    """Review r2 (B4 residual, same root cause): the listing PDP's
    'Listing highlights' bodies are captured as LocalizedContent envelopes
    with null titles — render the unpacked text, never
    ``<strong>None</strong> — {…}``. House-rules/safety item descriptions
    and the sleeping-arrangement null bed labels use the same envelope /
    null-placeholder family and must render as text too."""
    body = client.get('/rooms/1025161').get_data(as_text=True)
    assert ('This home is one of the highest ranked based on ratings, '
            'reviews, and reliability.') in body
    # no listing PDP may leak any repr class or null placeholder
    with ab.app.app_context():
        lids = [l.id for l in ab.Listing.query.order_by(ab.Listing.id)]
    for lid in lids:
        page = client.get(f'/rooms/{lid}').get_data(as_text=True)
        for marker in ('__typename', '{&#39;', 'built-in method',
                       'str object at', 'object at 0x'):
            assert marker not in page, \
                f"repr leak {marker!r} on /rooms/{lid}"
        assert '<strong>None</strong>' not in page, \
            f"None placeholder on /rooms/{lid}"
        assert 'value="None"' not in page, \
            f"None date value on /rooms/{lid}"


def test_listing_pdp_renders_bed_lines_unpacked(client):
    """Audit finding (r3 tree): the bed_lines column is a stored JSON
    array of captured '1 king bed' style lines, and the PDP rendered the
    raw stored string verbatim on every listing page (['1 bedroom', ...]
    visible on all 96 PDPs — a JSON-text leak the r1-r3 repr sweeps missed
    because their patterns covered Python repr forms, not the stored
    double-quoted JSON). The page must render the unpacked lines joined
    with ' · ', never the bracketed JSON text."""
    body = client.get('/rooms/39290956').get_data(as_text=True)
    assert '1 bedroom &middot; 1 king bed &middot; 1 bath' in body or \
        '1 bedroom · 1 king bed · 1 bath' in body
    with ab.app.app_context():
        lids = [l.id for l in ab.Listing.query.order_by(ab.Listing.id)]
    for lid in lids:
        page = client.get(f'/rooms/{lid}').get_data(as_text=True)
        assert '["' not in page, f"raw JSON bed_lines on /rooms/{lid}"
        assert '{"' not in page, f"raw JSON object on /rooms/{lid}"


def test_bookit_widget_is_one_shared_form(client):
    """Review H3: the PDP book-it widget must be ONE shared form — the
    Request-to-book button submits the CURRENT GUESTS select via
    formaction; the old hidden adults input that silently dropped a
    changed guest count must be gone."""
    with ab.app.app_context():
        lst = (ab.Listing.query
               .filter(ab.Listing.quote_checkin.isnot(None)).first())
    body = client.get(
        f'/rooms/{lst.id}?checkin={lst.quote_checkin}'
        f'&checkout={lst.quote_checkout}&adults=2').get_data(as_text=True)
    assert '<form id="bookit"' in body
    assert f'form="bookit" formaction="/rooms/{lst.id}/book"' in body
    assert '<input type="hidden" name="adults"' not in body


def test_booking_login_round_trip_returns_to_confirm(client):
    """Review M1: the unauthenticated confirm POST redirects to login with
    a RELATIVE next, and logging in returns straight to the book page."""
    with ab.app.app_context():
        lst = (ab.Listing.query
               .filter(ab.Listing.quote_checkin.isnot(None)).first())
    r = client.post(f'/rooms/{lst.id}/book?checkin={lst.quote_checkin}'
                    f'&checkout={lst.quote_checkout}&adults=2',
                    data=with_csrf(
                        client,
                        f'/rooms/{lst.id}/book?checkin={lst.quote_checkin}'
                        f'&checkout={lst.quote_checkout}&adults=2',
                        {'checkin': lst.quote_checkin,
                         'checkout': lst.quote_checkout, 'adults': '2'}))
    assert r.status_code in (302, 303)
    loc = r.headers['Location']
    assert loc.startswith('/login?next=/rooms/'), \
        f"next must be relative, got {loc!r}"
    # log in and land back on the confirm page
    r = client.post(loc, data=with_csrf(client, '/login', {
        'email': 'carol.d@test.com', 'password': 'TestPass123!'}))
    assert r.status_code in (302, 303)
    assert r.headers['Location'].startswith(f'/rooms/{lst.id}/book')


def test_winter_cabins_first_listing_is_bookable():
    """Review H2: the first Winter cabins wishlist entry (most recently
    saved, shown first) carries a captured quote window and is bookable."""
    with ab.app.app_context():
        dana = ab.User.query.filter_by(email='dana.k@test.com').first()
        winter = (ab.Wishlist.query.filter_by(user_id=dana.id, name='Winter cabins')
                  .first())
        items = (ab.WishlistItem.query.filter_by(wishlist_id=winter.id)
                 .order_by(ab.WishlistItem.id.desc()).all())
        first = ab.db.session.get(ab.Listing, items[0].listing_id)
        assert first.quote_checkin and first.quote_checkout and first.quote_total


def test_pdp_shows_saved_state(auth_client):
    """Review M4: the PDP shows the Saved state for a listing already in
    the user's wishlist."""
    with ab.app.app_context():
        alice = ab.User.query.filter_by(email='alice.j@test.com').first()
        item = (ab.WishlistItem.query.join(ab.Wishlist)
                .filter(ab.Wishlist.user_id == alice.id,
                        ab.WishlistItem.listing_id.isnot(None)).first())
        lst = ab.db.session.get(ab.Listing, item.listing_id)
    body = auth_client.get(f'/rooms/{lst.id}').get_data(as_text=True)
    assert '&#9829; Saved' in body
    assert 'Already saved to' in body


def test_wishlist_card_shows_market(auth_client):
    """Review M5: the wishlist cards show each saved stay's market (the
    destination city), so a suburb-localized stay is identifiable."""
    with ab.app.app_context():
        alice = ab.User.query.filter_by(email='alice.j@test.com').first()
        item = (ab.WishlistItem.query.join(ab.Wishlist)
                .filter(ab.Wishlist.user_id == alice.id,
                        ab.WishlistItem.listing_id.isnot(None)).first())
        lst = ab.db.session.get(ab.Listing, item.listing_id)
        market = (ab.Destination.query
                  .filter_by(slug=lst.destination_slug).first().city)
    body = auth_client.get('/wishlist').get_data(as_text=True)
    assert lst.title in body
    assert market in body


def test_uncaptured_sections_render_honest_notes(client):
    """Reviews M2/M3: listings whose amenity groups / category ratings
    weren't captured say so instead of rendering empty sections."""
    with ab.app.app_context():
        empty_amen = (ab.Listing.query
                      .filter(ab.Listing.amenities == '[]',
                              ab.Listing.amenity_count > 0).first())
        body = client.get(f'/rooms/{empty_amen.id}').get_data(as_text=True)
        assert "The amenity group details weren't captured for this listing." in body
        no_ratings = (ab.Listing.query
                      .filter(ab.Listing.quality.like('%"category_ratings": []%'))
                      .first())
        body = client.get(f'/rooms/{no_ratings.id}/reviews').get_data(as_text=True)
        assert "Category ratings weren't captured for this listing." in body
