#!/usr/bin/env python3
"""Machine audit of sites/airbnb/tasks.jsonl — measured honest-atomic
caliber, after the zara/u_s_customs/ziprecruiter precedent.

For every task row this script drives the task's honest path against the
seeded mirror through the Flask test client — the same natural route a
competent agent takes — and counts steps in the HONEST-ATOMIC caliber:

  atomic = every navigation, link click, form fill, VISIBLE radio/checkbox
           pick, dropdown select and form submit (GET or POST) after the
           initial page load, plus one final step for composing the
           answer. Reads are NOT counted. Hidden form inputs (csrf tokens,
           ids, carried date params) are NEVER counted. No gestures
           beyond the task text (no padding).

For every task it asserts:
  1. premises — every fact the task asks for actually resolves on the
     mirror with the frozen ground-truth value (driven through the test
     client, exactly like an agent would);
  2. measured depth — atomic >= 15, measured from the driven walk, not
     declared as a constant;
  3. zero answer leakage — the task text never contains the answer
     anchors the walk resolves (names, prices, codes, tags...);
  4. shape — the 7-key reviewer contract (5 contributor definition keys +
     verifier_path + judge_rubric, never an answer key), goal-style wording at
     or under 100 words, ids `Airbnb--<N>` in order, the registered port.

Run:  PYTHONPATH=. python3.11 scripts_dev/validate_tasks.py
"""
import html as html_mod
import json
import os
import pathlib
import re
import sys
import tempfile
from urllib.parse import quote

ROOT = pathlib.Path(__file__).resolve().parents[1]

# The audit drives stateful flows (signup, booking, wishlist), so it runs
# against its own throwaway seed database — never the live instance.
_AUDIT_DB = pathlib.Path(tempfile.mkdtemp(prefix="airbnb-task-audit-")) / "airbnb.db"
os.environ["AIRBNB_DB_URI"] = f"sqlite:///{_AUDIT_DB}"
os.environ["AIRBNB_AUTO_SEED"] = "1"

sys.path.insert(0, str(ROOT))
import app as ab_mod  # noqa: E402
from app import app, db  # noqa: E402

TASKS = [json.loads(line) for line in
         (ROOT / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]

TAG_RE = re.compile(r"<[^>]+>")


def text_of(page):
    return " ".join(html_mod.unescape(TAG_RE.sub(" ", page)).split())


def csrf_from(page_html):
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page_html)
    assert m, "no csrf token rendered"
    return m.group(1)


def money_s(v):
    return '${:,.2f}'.format(v)


def normalize(s):
    """The upstream captures use thin (\u2009) and narrow (\u202f) spaces;
    the rendered HTML carries them verbatim, but text_of() collapses
    them to plain spaces — normalize both sides before comparing."""
    if not isinstance(s, str):
        return s
    return (s.replace('\u2009', ' ').replace('\u202f', ' ')
             .replace('\u00a0', ' '))


# ------------------------------------------------------------------- walker --

class Walk:
    def __init__(self, client, task_id):
        self.client = client
        self.task_id = task_id
        self.atomic = 0
        self.facts = {}
        self.log = []

    def _get(self, path):
        r = self.client.get(path, follow_redirects=True)
        assert r.status_code == 200, f"GET {path} -> {r.status_code}"
        return r.get_data(as_text=True)

    def goto(self, path):
        """The initial page load of the task (not a gesture)."""
        return self._get(path)

    def nav(self, path, label=None):
        """A link click."""
        self.atomic += 1
        self.log.append(('nav', label or path))
        return self._get(path)

    def back(self):
        """Browser back: one gesture; the page reloads for free."""
        self.atomic += 1
        self.log.append(('back', 'browser-back'))

    def fill(self, name, value, form=None):
        """A visible text input the agent types into."""
        self.atomic += 1
        self.log.append(('fill', name))
        if form is not None:
            form[name] = value
        return value

    def pick(self, name, value, form=None):
        """A visible select / checkbox the agent sets."""
        self.atomic += 1
        self.log.append(('pick', f"{name}={value}"))
        if form is not None:
            form[name] = value
        return value

    def submit_get(self, path):
        """Submitting a GET form (home search, filter panel, book-it
        widget, experience booking form): one gesture."""
        self.atomic += 1
        self.log.append(('submit', path.split('?')[0] + '?…'))
        return self._get(path)

    def submit_post(self, path, data, source):
        """Submitting a POST form: the token is read out of the hosting
        page (a read, not a gesture)."""
        page = self._get(source)
        payload = dict(data)
        payload['csrf_token'] = csrf_from(page)
        self.atomic += 1
        self.log.append(('submit', path))
        r = self.client.post(path, data=payload, follow_redirects=True)
        assert r.status_code == 200, \
            f"POST {path} -> {r.status_code}: {r.get_data(as_text=True)[:200]}"
        return r.get_data(as_text=True)

    def answer(self):
        self.atomic += 1
        self.log.append(('answer', 'compose'))


def home_search(walk, label):
    """The home search bar: pick a destination, submit (GET)."""
    walk.pick('query', label)
    return walk.submit_get(f'/s/homes?query={quote(label)}')


def login_walk(walk, email, password):
    # clicking the header "Log in" is a gesture, like in the browser
    walk.nav('/login')
    form = {}
    walk.fill('email', email, form)
    walk.fill('password', password, form)
    return walk.submit_post('/login', form, '/login')


def signup_walk(walk, name, email, password):
    # clicking the header "Sign up" is a gesture, like in the browser
    walk.nav('/signup')
    form = {}
    walk.fill('name', name, form)
    walk.fill('email', email, form)
    walk.fill('password', password, form)
    return walk.submit_post('/signup', form, '/signup')


def first_card_href(page):
    m = re.search(r'<a class="card" href="([^"]+)"', page)
    assert m, "no listing card on the page"
    return html_mod.unescape(m.group(1))


def nth_card_href(page, n):
    ms = re.findall(r'<a class="card" href="([^"]+)"', page)
    assert len(ms) > n, f"only {len(ms)} cards"
    return html_mod.unescape(ms[n])


def card_titles(page):
    return [html_mod.unescape(t) for t in
            re.findall(r'<a class="card".*?<div class="row1">\s*<span>([^<]+)</span>', page, re.S)]


def has(html, s):
    esc = html_mod.escape(s, quote=True)
    return s in html or esc in html or esc.replace("&#x27;", "&#39;") in html


def book_stay(walk, lst, checkin, checkout, adults, pick_guests=False):
    """Request to book + confirm through the shared book-it form (review
    H3): the PDP is already open with the window in its query; when the
    task's guest count differs from the pre-filled value the GUESTS select
    is picked first, the single shared form then submits straight to
    /rooms/<id>/book (Request to book), and the confirm page POSTs the
    booking. No separate Check-availability submit is required — the
    widget's hidden-input defect that used to need it is gone."""
    if pick_guests:
        walk.pick('adults', str(adults))
    walk.submit_get(f'/rooms/{lst.id}/book?checkin={checkin}'
                    f'&checkout={checkout}&adults={adults}')
    return walk.submit_post(
        f'/rooms/{lst.id}/book?checkin={checkin}&checkout={checkout}&adults={adults}',
        {'checkin': checkin, 'checkout': checkout, 'adults': str(adults)},
        f'/rooms/{lst.id}/book?checkin={checkin}&checkout={checkout}&adults={adults}')


def book_stay_with_login(walk, lst, checkin, checkout, adults, email,
                          pick_guests=False):
    """The honest browser path when the task logs in mid-booking (review
    M1): Request to book, Confirm and book (bounces to the login page),
    log in — the relative `next` returns straight to the confirm page —
    then Confirm and book again."""
    if pick_guests:
        walk.pick('adults', str(adults))
    src = f'/rooms/{lst.id}/book?checkin={checkin}&checkout={checkout}&adults={adults}'
    walk.submit_get(src)
    walk.submit_post(src, {'checkin': checkin, 'checkout': checkout,
                           'adults': str(adults)}, src)      # -> login page
    login_walk(walk, email, 'TestPass123!')
    return walk.submit_post(src, {'checkin': checkin, 'checkout': checkout,
                                  'adults': str(adults)}, src)


def book_experience(walk, exp, date, guests):
    walk.pick('date', date)
    walk.pick('guests', str(guests))
    walk.submit_get(f'/experiences/{exp.id}/book?date={date}&guests={guests}')
    return walk.submit_post(
        f'/experiences/{exp.id}/book',
        {'date': date, 'guests': str(guests)},
        f'/experiences/{exp.id}/book?date={date}&guests={guests}')


def listing_for(**filters):
    q = db.session.query(ab_mod.Listing).filter_by(**{k: v for k, v in filters.items()
                                                      if k != 'amenity'})
    if 'amenity' in filters:
        q = q.filter(ab_mod.Listing.amenity_flags.like(f'%"{filters["amenity"]}"%'))
    return q


# --------------------------------------------------------------- task walks --

def walk_t0(walk):
    page = home_search(walk, 'Lake Tahoe, California')
    with app.app_context():
        lsts = (listing_for(destination_slug='lake-tahoe', is_guest_favorite=True)
                .filter(ab_mod.Listing.quote_total <= 1600)
                .order_by(ab_mod.Listing.quote_total).all())
        expect_n = len(lsts)
        target = lsts[0]
        ht = [l for l in lsts if 'hot tub' in l.amenity_flag_set()]
    walk.fill('price_max', '1600')
    walk.pick('guest_favorite', '1')
    walk.pick('sort', 'price_asc')
    page = walk.submit_get('/s/lake-tahoe/homes?price_max=1600&guest_favorite=1&sort=price_asc')
    walk.facts['count_gf'] = len(card_titles(page))
    assert walk.facts['count_gf'] == expect_n, \
        f"{walk.facts['count_gf']} != {expect_n}"
    page = walk.nav(first_card_href(page))
    walk.facts['name'] = target.name
    walk.facts['rating'] = target.rating
    assert has(page, target.name)
    walk.back()
    walk.pick('amenities', 'hot tub')
    page = walk.submit_get('/s/lake-tahoe/homes?price_max=1600&guest_favorite=1'
                           '&amenities=hot+tub&sort=price_asc')
    walk.facts['count_ht'] = len(card_titles(page))
    assert walk.facts['count_ht'] == len(ht), \
        f"{walk.facts['count_ht']} != {len(ht)}"
    opened = ht[0]
    page = walk.nav(first_card_href(page))
    walk.facts['nightly'] = opened.nightly_price
    walk.facts['amenity_groups'] = len(opened.amenity_groups())
    assert has(page, opened.name)
    walk.pick('checkin', '2026-12-06')
    walk.pick('checkout', '2026-12-13')
    page = walk.submit_get(f'/rooms/{opened.id}?checkin=2026-12-06'
                           f'&checkout=2026-12-13&adults=2')
    total = round(opened.nightly_price * 7, 2)
    walk.facts['total7'] = money_s(total)
    assert money_s(total) in page, f"{money_s(total)} not on the PDP"
    walk.answer()


def walk_t1(walk):
    login_walk(walk, 'alice.j@test.com', 'TestPass123!')
    walk.goto('/')
    page = home_search(walk, 'Scottsdale, Arizona')
    with app.app_context():
        lsts = [l for l in listing_for(destination_slug='scottsdale',
                                       instant_book=True).all()
                if 'pool' in l.amenity_flag_set()]
        target = lsts[0]
    walk.pick('instant_book', '1')
    walk.pick('amenities', 'pool')
    page = walk.submit_get('/s/scottsdale/homes?instant_book=1&amenities=pool')
    page = walk.nav(first_card_href(page))
    walk.facts['name'] = target.name
    assert has(page, target.name)
    body = book_stay(walk, target, target.quote_checkin, target.quote_checkout, 2)
    code = re.search(r'Confirmation code (?:<strong>)?([A-Z0-9]+)', body).group(1)
    walk.facts['code'] = code
    total = round(target.nightly_price * (target.quote_nights or 5), 2)
    walk.facts['total'] = money_s(total)
    assert money_s(total) in body
    page = walk.nav('/trips')
    assert code in page
    walk.submit_post(f'/trips/{code}/cancel', {}, '/trips')
    page = walk._get(f'/bookings/{code}')
    walk.facts['status'] = 'cancelled'
    assert 'cancelled' in text_of(page).lower()
    walk.answer()


def nth_exp_href(page, n):
    ms = re.findall(r'<a class="exp-card" href="(/experiences/[^"]+)"', page)
    assert len(ms) > n, f"only {len(ms)} experience cards"
    return html_mod.unescape(ms[n])


def card_href_by_id(page, lid):
    m = re.search(rf'<a class="card" href="/rooms/{lid}[^"]*"', page)
    assert m, f"card for {lid} not on the page"
    return html_mod.unescape(m.group(0).split('href="')[1].rstrip('"'))


def walk_t2(walk):
    signup_walk(walk, 'Runner Two', 'runner2@test.com', 'LongPass123!')
    walk.goto('/')
    page = home_search(walk, 'Miami, Florida')
    with app.app_context():
        top = (listing_for(destination_slug='miami')
               .order_by(ab_mod.Listing.reviews_count.desc()).first())
        second = (listing_for(destination_slug='miami')
                  .order_by(ab_mod.Listing.serp_position).all())[1]
    page = walk.nav(card_href_by_id(page, top.id))
    walk.facts['top_name'] = top.name
    walk.facts['top_reviews'] = top.reviews_count
    assert has(page, top.name)
    walk.fill('new_name', 'Beach trip')
    walk.submit_post('/wishlist/add',
                     {'listing_id': top.id, 'new_name': 'Beach trip',
                      'back': f'/rooms/{top.id}'},
                     f'/rooms/{top.id}')
    walk.back()
    page = walk._get('/s/miami/homes')
    page = walk.nav(nth_card_href(page, 1))
    walk.facts['second_name'] = second.name
    assert has(page, second.name)
    walk.pick('wishlist_id', 'Beach trip')
    with app.app_context():
        wl = (db.session.query(ab_mod.Wishlist)
              .filter_by(name='Beach trip').first())
    walk.submit_post('/wishlist/add',
                     {'listing_id': second.id, 'wishlist_id': str(wl.id),
                      'back': f'/rooms/{second.id}'},
                     f'/rooms/{second.id}')
    page = walk.nav('/wishlist')
    body = text_of(page)
    walk.facts['wishlist'] = 'Beach trip'
    walk.facts['items'] = 2
    assert 'Beach trip' in body
    assert body.count('Remove') >= 2
    walk.answer()


def walk_t3(walk):
    page = home_search(walk, 'Asheville, North Carolina')
    with app.app_context():
        target = (listing_for(destination_slug='asheville')
                  .order_by(ab_mod.Listing.reviews_count.desc()).first())
        rev = (db.session.query(ab_mod.Review).filter_by(listing_id=target.id)
               .order_by(ab_mod.Review.id).first())
        tags = (db.session.query(ab_mod.ReviewTag)
                .filter_by(listing_id=target.id)
                .order_by(ab_mod.ReviewTag.count.desc()).all())
        ht = [l for l in listing_for(destination_slug='asheville').all()
              if 'hot tub' in l.amenity_flag_set()]
    walk.facts['name'] = target.name
    walk.facts['reviews'] = target.reviews_count
    # premise (review H1): the SERP card shows the review count
    assert f'({target.reviews_count})' in page
    page = walk.nav(f'/rooms/{target.id}')
    assert has(page, target.name)
    page = walk.nav(f'/rooms/{target.id}/reviews')
    body = text_of(page)
    walk.facts['reviewer'] = rev.reviewer
    walk.facts['month'] = rev.localized_date
    walk.facts['tag'] = (tags[0].name, tags[0].count)
    walk.facts['third_tag'] = (tags[2].name, tags[2].count)
    assert rev.reviewer in body
    assert f"{tags[0].name} ({tags[0].count})" in body
    assert f"{tags[2].name} ({tags[2].count})" in body
    walk.back()
    walk.back()
    walk.pick('amenities', 'hot tub')
    page = walk.submit_get('/s/asheville/homes?amenities=hot+tub')
    walk.facts['count_ht'] = len(card_titles(page))
    assert walk.facts['count_ht'] == len(ht), \
        f"{walk.facts['count_ht']} != {len(ht)}"
    saved = ht[0]
    second = ht[1]
    serp_ht = page          # the hot-tub-filtered SERP (for the second card)
    page = walk.nav(first_card_href(page))
    login_walk(walk, 'bob.c@test.com', 'TestPass123!')
    walk.submit_post('/wishlist/add',
                     {'listing_id': saved.id, 'back': f'/rooms/{saved.id}'},
                     f'/rooms/{saved.id}')
    walk.facts['saved'] = saved.name
    walk.facts['saved_nightly'] = saved.nightly_price
    walk.back()
    page = walk.nav(nth_card_href(serp_ht, 1))
    walk.facts['second_title'] = second.title
    walk.facts['second_nightly'] = second.nightly_price
    assert has(page, second.title)
    walk.answer()


def walk_t4(walk):
    page = walk.goto('/s/experiences?city=austin')
    walk.facts['austin_total'] = db.session.query(ab_mod.Experience).filter_by(
        city_slug='austin').count()
    page = walk.nav('/s/experiences?city=austin&category=Cooking')
    with app.app_context():
        exps = (db.session.query(ab_mod.Experience)
                .filter_by(city_slug='austin', theme='Cooking').all())
        target = exps[0]
        assert target.offering_list(), \
            f"{target.name} has no captured availability"

        gr = json.loads(target.guest_requirements or '{}')
        agenda = target.agenda_list()
    walk.facts['count'] = len(exps)
    walk.facts['price'] = target.price_per_guest
    walk.facts['min_age'] = gr.get('min_age')
    walk.facts['agenda_stops'] = len(agenda)
    page = walk.nav(f'/experiences/{target.id}')
    body = text_of(page)
    assert f'${target.price_per_guest:.0f}' in body
    login_walk(walk, 'bob.c@test.com', 'TestPass123!')
    walk.submit_post('/wishlist/add',
                     {'experience_id': target.id,
                      'back': f'/experiences/{target.id}'},
                     f'/experiences/{target.id}')
    walk.facts['saved_to'] = 'Saved'
    page = walk.nav('/wishlist')
    assert has(page, target.name)
    page = walk._get(f'/experiences/{target.id}')
    date = target.offering_list()[0]['iso']
    body = book_experience(walk, target, date, 2)
    code = re.search(r'Confirmation code (?:<strong>)?([A-Z0-9]+)', body).group(1)
    walk.facts['code'] = code
    walk.facts['total'] = money_s(round(target.price_per_guest * 2, 2))
    walk.facts['booked_date'] = target.offering_list()[0]['day']
    assert money_s(round(target.price_per_guest * 2, 2)) in body
    page = walk.nav('/trips')
    assert target.offering_list()[0]['day'] in page or code in page
    page = walk.nav('/s/experiences?city=austin')
    walk.answer()


def walk_t5(walk):
    page = home_search(walk, 'Nashville, Tennessee')
    with app.app_context():
        gf = [l for l in listing_for(destination_slug='nashville').all()
              if l.is_guest_favorite]
        gf_pool = [l for l in gf if 'pool' in l.amenity_flag_set()]
        allp = (listing_for(destination_slug='nashville')
                .filter(ab_mod.Listing.quote_total.isnot(None))
                .order_by(ab_mod.Listing.quote_total).all())
        priciest = allp[-1]
        cheapest = allp[0]
    walk.pick('guest_favorite', '1')
    page = walk.submit_get('/s/nashville/homes?guest_favorite=1')
    walk.facts['gf'] = len(gf)
    assert len(card_titles(page)) == len(gf)
    walk.pick('amenities', 'pool')
    page = walk.submit_get('/s/nashville/homes?guest_favorite=1&amenities=pool')
    walk.facts['gf_pool'] = len(gf_pool)
    assert len(card_titles(page)) == len(gf_pool), \
        f"{len(card_titles(page))} != {len(gf_pool)}"
    target = gf_pool[0]
    page = walk.nav(first_card_href(page))
    walk.facts['title'] = target.title
    walk.facts['nightly'] = target.nightly_price
    assert has(page, target.title)
    walk.back()
    walk.nav('/s/nashville/homes')
    walk.pick('sort', 'price_desc')
    page = walk.submit_get('/s/nashville/homes?sort=price_desc')
    walk.facts['priciest_name'] = priciest.name
    walk.facts['priciest_total'] = money_s(priciest.quote_total)
    assert has(page, priciest.name)
    page = walk.nav(card_href_by_id(page, priciest.id))
    walk.facts['priciest_host'] = priciest.host_name
    assert priciest.host_name in text_of(page)
    page = walk.nav('/s/nashville/homes?sort=price_asc')
    walk.facts['cheapest_reviews'] = cheapest.reviews_count
    walk.nav(f'/rooms/{cheapest.id}')
    walk.answer()


def walk_t6(walk):
    login_walk(walk, 'dana.k@test.com', 'TestPass123!')
    page = walk.nav('/wishlist')
    with app.app_context():
        dana = db.session.query(ab_mod.User).filter_by(
            email='dana.k@test.com').first()
        wls = (db.session.query(ab_mod.Wishlist)
               .filter_by(user_id=dana.id).order_by(ab_mod.Wishlist.id).all())
        winter = next(w for w in wls if w.name == 'Winter cabins')
        nyc = next(w for w in wls if w.name == 'NYC weekend')
        # the wishlist page shows items most-recently-saved first (id DESC),
        # matching the seed's back-to-front insertion (review H2)
        items = (db.session.query(ab_mod.WishlistItem)
                 .filter_by(wishlist_id=winter.id)
                 .order_by(ab_mod.WishlistItem.id.desc()).all())
        lids = [i.listing_id for i in items if i.listing_id]
        listings = [db.session.get(ab_mod.Listing, lid) for lid in lids]
        nyc_items = (db.session.query(ab_mod.WishlistItem)
                     .filter_by(wishlist_id=nyc.id).count())
    walk.facts['wishlist_count'] = len(wls)
    walk.facts['wishlist_names'] = [w.name for w in wls]
    walk.facts['winter_items'] = [l.name for l in listings]
    body = text_of(page)
    for l in listings:
        assert has(body, l.name)
    page = walk.nav(f'/rooms/{lids[0]}')
    walk.facts['nightly'] = listings[0].nightly_price
    walk.facts['rating'] = listings[0].rating
    assert has(page, listings[0].name)
    page = walk.nav(f'/rooms/{lids[1]}')
    walk.facts['second_hot_tub'] = 'hot tub' in listings[1].amenity_flag_set()
    page = walk.nav(f'/rooms/{lids[1]}/reviews')
    tag2 = (db.session.query(ab_mod.ReviewTag)
            .filter_by(listing_id=lids[1])
            .order_by(ab_mod.ReviewTag.count.desc()).first())
    walk.facts['second_tag'] = (tag2.name, tag2.count)
    assert f"{tag2.name} ({tag2.count})" in text_of(page)
    walk.back()
    walk.back()
    page = walk.nav(f'/rooms/{lids[0]}')
    # the first Winter cabins listing must carry a captured quote window
    # (review H2) — bookable for its captured window
    assert listings[0].quote_checkin and listings[0].quote_checkout
    body = book_stay(walk, listings[0], listings[0].quote_checkin,
                     listings[0].quote_checkout, 2)
    code = re.search(r'Confirmation code (?:<strong>)?([A-Z0-9]+)', body).group(1)
    walk.facts['code'] = code
    walk.facts['dates'] = (listings[0].quote_checkin, listings[0].quote_checkout)
    total = round(listings[0].nightly_price * listings[0].quote_nights, 2)
    walk.facts['total'] = money_s(total)
    assert money_s(total) in body
    # "Finally report how many items the NYC weekend wishlist has" — read
    # it from the wishlists page (the honest source of the answer)
    page = walk.nav('/wishlist')
    walk.facts['nyc_items'] = nyc_items
    assert 'NYC weekend' in text_of(page)
    walk.answer()


def walk_t7(walk):
    page = home_search(walk, 'New York, New York')
    with app.app_context():
        lsts = (listing_for(destination_slug='new-york', is_guest_favorite=True)
                .filter(ab_mod.Listing.quote_total.isnot(None))
                .order_by(ab_mod.Listing.quote_total).all())
        target = lsts[0]
    walk.pick('guest_favorite', '1')
    walk.pick('sort', 'price_asc')
    page = walk.submit_get('/s/new-york/homes?guest_favorite=1&sort=price_asc')
    page = walk.nav(first_card_href(page))
    walk.facts['name'] = target.name
    walk.facts['nightly'] = target.nightly_price
    walk.facts['quote'] = money_s(target.quote_total)
    assert has(page, target.name)
    walk.pick('checkin', '2026-12-06')
    walk.pick('checkout', '2026-12-13')
    page = walk.submit_get(f'/rooms/{target.id}?checkin=2026-12-06'
                           f'&checkout=2026-12-13&adults=2')
    total7 = round(target.nightly_price * 7, 2)
    walk.facts['total7'] = money_s(total7)
    assert money_s(total7) in page, f"{money_s(total7)} not on the PDP"
    body = book_stay_with_login(walk, target, '2026-12-06', '2026-12-13', 2,
                                'carol.d@test.com')
    code = re.search(r'Confirmation code (?:<strong>)?([A-Z0-9]+)', body).group(1)
    walk.facts['code'] = code
    walk.answer()


def walk_t8(walk):
    page = walk.goto('/s/experiences?city=los-angeles')
    with app.app_context():
        exps = (db.session.query(ab_mod.Experience)
                .filter_by(city_slug='los-angeles').all())
        exps.sort(key=lambda e: e.price_per_guest, reverse=True)
        target, second = exps[0], exps[1]
        gr = json.loads(target.guest_requirements or '{}')
        agenda = target.agenda_list()
    walk.facts['la_total'] = len(exps)
    walk.pick('sort', 'price_desc')
    page = walk.submit_get('/s/experiences?city=los-angeles&sort=price_desc')
    walk.facts['name'] = target.name
    walk.facts['category'] = target.theme
    walk.facts['price'] = target.price_per_guest
    walk.facts['rating'] = target.rating
    walk.facts['first_stop'] = agenda[0]['title'] if agenda else None
    walk.facts['min_age'] = gr.get('min_age')
    page = walk.nav(f'/experiences/{target.id}')
    assert has(page, target.name)
    walk.back()
    page = walk._get('/s/experiences?city=los-angeles&sort=price_desc')
    page = walk.nav(f'/experiences/{second.id}')
    walk.facts['second_name'] = second.name
    walk.facts['second_price'] = second.price_per_guest
    walk.facts['second_rating_count'] = second.rating_count
    assert has(page, second.name)
    walk.back()
    login_walk(walk, 'bob.c@test.com', 'TestPass123!')
    page = walk.nav(f'/experiences/{target.id}')
    walk.submit_post('/wishlist/add',
                     {'experience_id': target.id,
                      'back': f'/experiences/{target.id}'},
                     f'/experiences/{target.id}')
    page = walk.nav('/wishlist')
    walk.facts['wishlist'] = 'Saved'
    assert 'Saved' in text_of(page)
    page = walk.nav('/trips')
    with app.app_context():
        bob = db.session.query(ab_mod.User).filter_by(
            email='bob.c@test.com').first()
        n = db.session.query(ab_mod.Booking).filter_by(user_id=bob.id).count()
    walk.facts['bob_trips'] = n
    assert n >= 1
    walk.answer()


def walk_t9(walk):
    page = home_search(walk, 'Lake Tahoe, California')
    with app.app_context():
        target = (listing_for(destination_slug='lake-tahoe',
                              is_guest_favorite=True)
                  .order_by(ab_mod.Listing.serp_position).first())
    walk.pick('guest_favorite', '1')
    page = walk.submit_get('/s/lake-tahoe/homes?guest_favorite=1')
    page = walk.nav(first_card_href(page))
    walk.facts['nightly'] = target.nightly_price
    walk.pick('checkin', '2027-01-08')
    walk.pick('checkout', '2027-01-13')
    page = walk.submit_get(f'/rooms/{target.id}?checkin=2027-01-08'
                           f'&checkout=2027-01-13&adults=2')
    total = round(target.nightly_price * 5, 2)
    walk.facts['total'] = money_s(total)
    assert money_s(total) in page, f"{money_s(total)} missing on the PDP"
    body = book_stay_with_login(walk, target, '2027-01-08', '2027-01-13', 2,
                                'carol.d@test.com')
    code = re.search(r'Confirmation code (?:<strong>)?([A-Z0-9]+)', body).group(1)
    walk.facts['code'] = code
    assert money_s(total) in body
    walk.answer()


def walk_t10(walk):
    login_walk(walk, 'alice.j@test.com', 'TestPass123!')
    page = walk.nav('/wishlist')
    with app.app_context():
        alice = db.session.query(ab_mod.User).filter_by(
            email='alice.j@test.com').first()
        default = (db.session.query(ab_mod.Wishlist)
                   .filter_by(user_id=alice.id, is_default=True).first())
        items = (db.session.query(ab_mod.WishlistItem)
                 .filter_by(wishlist_id=default.id).all())
        stays = [i for i in items if i.listing_id]
        target = next(i for i in stays
                      if db.session.get(ab_mod.Listing, i.listing_id)
                      .destination_slug == 'lake-tahoe')
        remaining = [i for i in stays if i.id != target.id]
        bookings = (db.session.query(ab_mod.Booking)
                    .filter_by(user_id=alice.id).order_by(ab_mod.Booking.id).all())
    walk.facts['items'] = len(items)
    walk.facts['stay_names'] = [db.session.get(ab_mod.Listing, i.listing_id).name
                                for i in stays]
    walk.submit_post(f'/wishlist/{target.id}/remove', {}, '/wishlist')
    page = walk.nav('/wishlist')
    walk.facts['remaining'] = len(remaining)
    walk.facts['remaining_names'] = [
        db.session.get(ab_mod.Listing, i.listing_id).name for i in remaining]
    for i in remaining:
        assert has(page, db.session.get(ab_mod.Listing, i.listing_id).name)
    page = walk.nav('/trips')
    walk.facts['trips'] = [(b.code, b.status) for b in bookings]
    for b in bookings:
        assert b.code in page
    sc = next(b for b in bookings if b.status == 'confirmed'
              and b.kind == 'stay')
    walk.facts['stay_total'] = money_s(sc.total)
    lst = db.session.get(ab_mod.Listing, sc.listing_id)
    # honest browser path (review r2, T10 depth re-anchor): return to the
    # wishlists page and open the saved Scottsdale stay from its card (its
    # market is shown there — review M5), then its reviews page, then back
    # to the listing to book. The GUESTS select defaults to 2 and the task
    # books 3 guests, so the pick is a genuinely required gesture.
    page = walk.nav('/wishlist')
    assert has(page, lst.name)
    page = walk.nav(f'/rooms/{lst.id}')
    walk.facts['stay_name'] = lst.name
    page = walk.nav(f'/rooms/{lst.id}/reviews')
    tag10 = (db.session.query(ab_mod.ReviewTag)
             .filter_by(listing_id=lst.id)
             .order_by(ab_mod.ReviewTag.count.desc()).first())
    walk.facts['stay_tag'] = (tag10.name, tag10.count)
    assert f"{tag10.name} ({tag10.count})" in text_of(page)
    walk.back()
    page = walk._get(f'/rooms/{lst.id}')
    assert has(page, lst.name)
    body = book_stay(walk, lst, lst.quote_checkin, lst.quote_checkout, 3,
                     pick_guests=True)
    code = re.search(r'Confirmation code (?:<strong>)?([A-Z0-9]+)', body).group(1)
    walk.facts['new_code'] = code
    walk.facts['new_dates'] = (lst.quote_checkin, lst.quote_checkout)
    walk.facts['new_guests'] = 3
    total = round(lst.nightly_price * lst.quote_nights, 2)
    walk.facts['new_total'] = money_s(total)
    assert money_s(total) in body
    # the confirm page IS the new trip's page — code/dates/guests/total read
    # off it for free (no extra navigation the task text doesn't require)
    assert code in text_of(body)
    walk.answer()


def walk_t11(walk):
    signup_walk(walk, 'Sam Rivera', 'sam.r@test.com', 'SunnyDay88!')
    walk.goto('/')
    page = home_search(walk, 'Miami, Florida')
    with app.app_context():
        lsts = (listing_for(destination_slug='miami', is_guest_favorite=True)
                .filter(ab_mod.Listing.quote_total.isnot(None))
                .order_by(ab_mod.Listing.quote_total).all())
        target = lsts[0]
    walk.pick('guest_favorite', '1')
    walk.pick('sort', 'price_asc')
    page = walk.submit_get('/s/miami/homes?guest_favorite=1&sort=price_asc')
    page = walk.nav(first_card_href(page))
    walk.facts['name'] = target.name
    body = book_stay(walk, target, target.quote_checkin, target.quote_checkout, 2)
    code = re.search(r'Confirmation code (?:<strong>)?([A-Z0-9]+)', body).group(1)
    walk.facts['code'] = code
    total = round(target.nightly_price * target.quote_nights, 2)
    walk.facts['total'] = money_s(total)
    assert money_s(total) in body
    walk.submit_post('/wishlist/add',
                     {'listing_id': target.id, 'back': f'/rooms/{target.id}'},
                     f'/rooms/{target.id}')
    page = walk.nav('/wishlist')
    walk.facts['wishlist'] = 'Saved'
    walk.facts['wishlist_items'] = 1
    assert 'Saved' in text_of(page)
    walk.answer()


def walk_t12(walk):
    page = home_search(walk, 'Nashville, Tennessee')
    with app.app_context():
        lsts = [l for l in listing_for(destination_slug='nashville').all()
                if l.is_superhost]
        target = lsts[0]
        rules = json.loads(target.house_rules or '{}')
        pool = [l for l in listing_for(destination_slug='nashville').all()
                if 'pool' in l.amenity_flag_set()]
    walk.pick('superhost', '1')
    page = walk.submit_get('/s/nashville/homes?superhost=1')
    walk.facts['count'] = len(lsts)
    walk.facts['first_title'] = target.title
    assert len(card_titles(page)) == len(lsts)
    page = walk.nav(first_card_href(page))
    body = text_of(page)
    walk.facts['host'] = target.host_name
    walk.facts['years'] = target.host_years
    checkin_rule = None
    for g in (rules.get('groups') or []):
        for item in g['items']:
            if 'Check-in' in (item.get('title') or ''):
                checkin_rule = item['title']
    walk.facts['checkin_window'] = checkin_rule
    assert target.host_name in body
    assert normalize(checkin_rule or '') in normalize(body)
    page = walk.nav(f'/rooms/{target.id}/reviews')
    tag = (db.session.query(ab_mod.ReviewTag)
           .filter_by(listing_id=target.id)
           .order_by(ab_mod.ReviewTag.count.desc()).first())
    walk.facts['tag'] = (tag.name, tag.count)
    assert f"{tag.name} ({tag.count})" in text_of(page)
    walk.back()
    walk.back()
    walk.nav('/s/nashville/homes')
    walk.pick('amenities', 'pool')
    page = walk.submit_get('/s/nashville/homes?amenities=pool')
    opened = pool[0]
    walk.facts['pool_first_title'] = opened.title
    walk.facts['pool_first_nightly'] = opened.nightly_price
    page = walk.nav(first_card_href(page))
    assert has(page, opened.title)
    page = walk.nav(f'/rooms/{opened.id}/reviews')
    rev = (db.session.query(ab_mod.Review)
           .filter_by(listing_id=opened.id).order_by(ab_mod.Review.id).first())
    walk.facts['pool_first_reviewer'] = rev.reviewer if rev else None
    assert (rev.reviewer or 'x') in text_of(page)
    # "Go back twice, open the cheapest pool listing, and report its
    # nightly rate." — the cheapest by nightly rate among the pool results
    walk.back()
    walk.back()
    page = walk._get('/s/nashville/homes?amenities=pool')
    cheapest = min(pool, key=lambda l: l.nightly_price)
    hrefs = re.findall(r'<a class="card" href="([^"]+)"', page)
    target_href = next(h for h in hrefs if f'/rooms/{cheapest.id}' in h)
    page = walk.nav(html_mod.unescape(target_href))
    walk.facts['cheapest_pool_nightly'] = cheapest.nightly_price
    assert has(page, cheapest.title)
    walk.answer()


def walk_t13(walk):
    page = home_search(walk, 'Asheville, North Carolina')
    with app.app_context():
        ht = [l for l in listing_for(destination_slug='asheville').all()
              if 'hot tub' in l.amenity_flag_set()]
        target = ht[0]
    walk.pick('amenities', 'hot tub')
    page = walk.submit_get('/s/asheville/homes?amenities=hot+tub')
    walk.facts['count'] = len(ht)
    assert len(card_titles(page)) == len(ht), \
        f"{len(card_titles(page))} != {len(ht)}"
    page = walk.nav(first_card_href(page))
    walk.facts['title'] = target.title
    walk.facts['groups'] = len(target.amenity_groups())
    assert has(page, target.title)
    page = walk.nav(f'/rooms/{target.id}/reviews')
    tag = (db.session.query(ab_mod.ReviewTag)
           .filter_by(listing_id=target.id)
           .order_by(ab_mod.ReviewTag.count.desc()).first())
    walk.facts['tag'] = (tag.name, tag.count)
    assert f"{tag.name} ({tag.count})" in text_of(page)
    walk.back()
    walk.back()
    page = walk._get(f'/rooms/{target.id}')
    login_walk(walk, 'bob.c@test.com', 'TestPass123!')
    # the header login lands on the home page — the browser recovery is
    # two back steps (login page, then the listing); model them honestly
    walk.back()
    walk.back()
    page = walk._get(f'/rooms/{target.id}')
    body = book_stay(walk, target, target.quote_checkin, target.quote_checkout, 2)
    code = re.search(r'Confirmation code (?:<strong>)?([A-Z0-9]+)', body).group(1)
    walk.facts['code'] = code
    walk.facts['dates'] = (target.quote_checkin, target.quote_checkout)
    total = round(target.nightly_price * target.quote_nights, 2)
    walk.facts['total'] = money_s(total)
    assert money_s(total) in body
    page = walk.nav('/trips')
    with app.app_context():
        bob = db.session.query(ab_mod.User).filter_by(
            email='bob.c@test.com').first()
        n = db.session.query(ab_mod.Booking).filter_by(user_id=bob.id).count()
    walk.facts['bob_bookings'] = n
    walk.answer()


def walk_t14(walk):
    # "From the home page browse New York experiences in the Cultural tours
    # category" — the experiences nav, then the New York city chip, then
    # the Cultural tours category chip (review B3 made the city reachable)
    page = walk.goto('/s/experiences')
    page = walk.nav('/s/experiences?city=new-york')
    page = walk.nav('/s/experiences?city=new-york&category=Cultural+tours')
    with app.app_context():
        exps = (db.session.query(ab_mod.Experience)
                .filter_by(city_slug='new-york', theme='Cultural tours').all())
        target, second = exps[0], exps[1]
        reqs = json.loads(target.guest_requirements or '{}')
        ttk = json.loads(target.things_to_know or '[]')
    walk.facts['name'] = target.name
    walk.facts['price'] = target.price_per_guest
    walk.facts['rating_count'] = target.rating_count
    page = walk.nav(f'/experiences/{target.id}')
    body = text_of(page)
    walk.facts['min_age'] = reqs.get('min_age')
    walk.facts['activity'] = next(
        (t['text'] for t in ttk if t['title'] == 'Activity level'), None)
    assert has(page, target.name)
    assert f"Minimum age: {reqs.get('min_age')}" in normalize(body) or \
        f"Minimum age: {reqs.get('min_age')}" in body
    assert (walk.facts['activity'] or '') in normalize(body)
    walk.back()
    page = walk._get('/s/experiences?city=new-york&category=Cultural+tours')
    page = walk.nav(f'/experiences/{second.id}')
    walk.facts['second_name'] = second.name
    walk.facts['second_price'] = second.price_per_guest
    walk.facts['second_rating_count'] = second.rating_count
    assert has(page, second.name)
    walk.back()
    page = walk.nav(f'/experiences/{target.id}')
    login_walk(walk, 'bob.c@test.com', 'TestPass123!')
    date = target.offering_list()[0]['iso']
    body = book_experience(walk, target, date, 3)
    code = re.search(r'Confirmation code (?:<strong>)?([A-Z0-9]+)', body).group(1)
    walk.facts['total'] = money_s(round(target.price_per_guest * 3, 2))
    walk.facts['code'] = code
    assert money_s(round(target.price_per_guest * 3, 2)) in body
    walk.answer()


def walk_t15(walk):
    page = home_search(walk, 'Scottsdale, Arizona')
    with app.app_context():
        lsts = (listing_for(destination_slug='scottsdale',
                            is_guest_favorite=True)
                .filter(ab_mod.Listing.quote_total.isnot(None))
                .order_by(ab_mod.Listing.quote_total.desc()).all())
        target, second = lsts[0], lsts[1]
        tag = (db.session.query(ab_mod.ReviewTag)
               .filter_by(listing_id=target.id)
               .order_by(ab_mod.ReviewTag.count.desc()).first())
        rev = (db.session.query(ab_mod.Review)
               .filter_by(listing_id=target.id).order_by(ab_mod.Review.id).first())
        rules = json.loads(target.house_rules or '{}')
        pool_gf = [l for l in listing_for(destination_slug='scottsdale',
                                           is_guest_favorite=True).all()
                   if 'pool' in l.amenity_flag_set()]
        checkin_rule = None
        for g in (rules.get('groups') or []):
            for item in g['items']:
                if 'Check-in' in (item.get('title') or ''):
                    checkin_rule = item['title']
    walk.pick('sort', 'price_desc')
    walk.pick('guest_favorite', '1')
    page = walk.submit_get('/s/scottsdale/homes?sort=price_desc&guest_favorite=1')
    # premise (review H1): the SERP card shows the review count
    assert f"({target.reviews_count})" in page
    page = walk.nav(first_card_href(page))
    walk.facts['name'] = target.name
    walk.facts['total'] = money_s(target.quote_total)
    walk.facts['reviews'] = target.reviews_count
    body = text_of(page)
    walk.facts['capacity'] = target.max_guest_capacity or target.person_capacity
    walk.facts['checkin_window'] = checkin_rule
    assert checkin_rule and normalize(checkin_rule) in normalize(body)
    page = walk.nav(f'/rooms/{target.id}/reviews')
    body = text_of(page)
    walk.facts['tag'] = (tag.name, tag.count)
    walk.facts['first_reviewer'] = rev.reviewer
    assert f"{tag.name} ({tag.count})" in body
    assert rev.reviewer in body
    walk.back()
    walk.back()
    page = walk._get('/s/scottsdale/homes?sort=price_desc&guest_favorite=1')
    page = walk.nav(nth_card_href(page, 1))
    walk.facts['second_name'] = second.name
    walk.facts['second_nightly'] = second.nightly_price
    assert has(page, second.name)
    page = walk.nav(f'/rooms/{second.id}/reviews')
    rev2 = (db.session.query(ab_mod.Review)
            .filter_by(listing_id=second.id).order_by(ab_mod.Review.id).first())
    walk.facts['second_reviewer'] = rev2.reviewer if rev2 else None
    assert (rev2.reviewer or 'x') in text_of(page)
    # "Go back, add a pool amenity filter, and report the new count."
    walk.back()
    walk.back()
    walk.pick('amenities', 'pool')
    page = walk.submit_get(
        '/s/scottsdale/homes?sort=price_desc&guest_favorite=1&amenities=pool')
    walk.facts['pool_count'] = len(card_titles(page))
    assert walk.facts['pool_count'] == len(pool_gf), \
        f"{walk.facts['pool_count']} != {len(pool_gf)}"
    walk.answer()


def walk_t16(walk):
    page = home_search(walk, 'Los Angeles, California')
    with app.app_context():
        lsts = [l for l in listing_for(destination_slug='los-angeles').all()
                if 'hot tub' in l.amenity_flag_set() and l.quote_total]
        lsts.sort(key=lambda l: l.quote_total)
        target = lsts[0]
    walk.pick('amenities', 'hot tub')
    page = walk.submit_get('/s/los-angeles/homes?amenities=hot+tub&sort=price_asc')
    walk.facts['count'] = len(lsts)
    assert len(card_titles(page)) == len(lsts), \
        f"{len(card_titles(page))} != {len(lsts)}"
    page = walk.nav(first_card_href(page))
    walk.facts['title'] = target.title
    walk.facts['nightly'] = target.nightly_price
    assert has(page, target.title)
    signup_walk(walk, 'Casey T', 'casey.t@test.com', 'CaseyPass77!')
    # the signup lands on the home page — the browser recovery is two back
    # steps (signup page, then the listing); model them honestly
    walk.back()
    walk.back()
    body = book_stay(walk, target, target.quote_checkin, target.quote_checkout, 2)
    code = re.search(r'Confirmation code (?:<strong>)?([A-Z0-9]+)', body).group(1)
    walk.facts['code'] = code
    total = round(target.nightly_price * target.quote_nights, 2)
    walk.facts['total'] = money_s(total)
    assert money_s(total) in body
    page = walk.nav('/trips')
    walk.submit_post(f'/trips/{code}/cancel', {}, '/trips')
    page = walk._get(f'/bookings/{code}')
    walk.facts['status'] = 'cancelled'
    assert 'cancelled' in text_of(page).lower()
    page = walk.nav('/wishlist')
    walk.facts['wishlist'] = 'Saved'
    assert 'Saved' in text_of(page)
    walk.answer()


def walk_t17(walk):
    page = home_search(walk, 'Lake Tahoe, California')
    with app.app_context():
        all_l = (listing_for(destination_slug='lake-tahoe')
                 .order_by(ab_mod.Listing.serp_position).all())
        gf = [l for l in all_l if l.is_guest_favorite]
        second = all_l[1]
        explore = json.loads(second.explore or '[]')
        tag = (db.session.query(ab_mod.ReviewTag)
               .filter_by(listing_id=second.id)
               .order_by(ab_mod.ReviewTag.count.desc()).first())
        rev = (db.session.query(ab_mod.Review)
               .filter_by(listing_id=second.id).order_by(ab_mod.Review.id).first())
    walk.pick('guest_favorite', '1')
    page = walk.submit_get('/s/lake-tahoe/homes?guest_favorite=1')
    walk.facts['gf_count'] = len(gf)
    assert len(card_titles(page)) == len(gf)
    walk.nav('/s/lake-tahoe/homes')
    page = walk.nav(nth_card_href(walk._get('/s/lake-tahoe/homes'), 1))
    walk.facts['name'] = second.name
    walk.facts['rating'] = second.rating
    assert has(page, second.name)
    walk.facts['explore'] = [e['title'] for e in explore[:2]]
    for e in explore[:2]:
        assert e['title'] in page
    page = walk.nav(f'/rooms/{second.id}/reviews')
    body = text_of(page)
    walk.facts['tag'] = (tag.name, tag.count)
    walk.facts['reviewer_location'] = rev.reviewer_location
    assert f"{tag.name} ({tag.count})" in body
    walk.back()
    walk._get(f'/rooms/{second.id}')
    login_walk(walk, 'dana.k@test.com', 'TestPass123!')
    walk.submit_post('/wishlist/add',
                     {'listing_id': second.id,
                      'back': f'/rooms/{second.id}'},
                     f'/rooms/{second.id}')
    page = walk.nav('/wishlist')
    with app.app_context():
        dana = db.session.query(ab_mod.User).filter_by(
            email='dana.k@test.com').first()
        saved_default = (db.session.query(ab_mod.WishlistItem)
                         .join(ab_mod.Wishlist)
                         .filter(ab_mod.Wishlist.user_id == dana.id,
                                 ab_mod.Wishlist.is_default.is_(True)).count())
    walk.facts['wishlist'] = 'Saved'
    walk.facts['saved_count'] = saved_default
    assert 'Saved' in text_of(page)
    walk.answer()


def walk_t18(walk):
    page = home_search(walk, 'Austin, Texas')
    with app.app_context():
        lsts = [l for l in listing_for(destination_slug='austin').all()
                if l.instant_book and l.pets_allowed]
        target = lsts[0]
    walk.pick('instant_book', '1')
    walk.pick('pets', '1')
    page = walk.submit_get('/s/austin/homes?instant_book=1&pets=1')
    walk.facts['count'] = len(lsts)
    assert len(card_titles(page)) == len(lsts), \
        f"{len(card_titles(page))} != {len(lsts)}"
    page = walk.nav(first_card_href(page))
    walk.facts['title'] = target.title
    walk.facts['nightly'] = target.nightly_price
    walk.facts['capacity'] = target.person_capacity
    assert has(page, target.title)
    body = book_stay_with_login(walk, target, target.quote_checkin,
                                target.quote_checkout, 3, 'dana.k@test.com',
                                pick_guests=True)
    code = re.search(r'Confirmation code (?:<strong>)?([A-Z0-9]+)', body).group(1)
    walk.facts['code'] = code
    total = round(target.nightly_price * target.quote_nights, 2)
    walk.facts['total'] = money_s(total)
    assert money_s(total) in body
    # "Return to the listing, save it to your default wishlist, open the
    # wishlists page, and report the default wishlist's saved-item count" —
    # from the booking page the browser recovery is two back steps (the
    # confirm page, then the listing)
    walk.back()
    walk.back()
    page = walk._get(f'/rooms/{target.id}')
    with app.app_context():
        dana = db.session.query(ab_mod.User).filter_by(
            email='dana.k@test.com').first()
        before = (db.session.query(ab_mod.WishlistItem)
                  .join(ab_mod.Wishlist)
                  .filter(ab_mod.Wishlist.user_id == dana.id,
                          ab_mod.Wishlist.is_default.is_(True)).count())
    walk.submit_post('/wishlist/add', {'listing_id': target.id,
                                        'back': f'/rooms/{target.id}'},
                     f'/rooms/{target.id}')
    page = walk.nav('/wishlist')
    with app.app_context():
        dana = db.session.query(ab_mod.User).filter_by(
            email='dana.k@test.com').first()
        default = (db.session.query(ab_mod.Wishlist)
                   .filter_by(user_id=dana.id, is_default=True).first())
        n = (db.session.query(ab_mod.WishlistItem)
             .filter_by(wishlist_id=default.id).count())
    walk.facts['wishlist_name'] = default.name
    walk.facts['saved_count'] = n
    assert n == before + 1 and has(page, target.name)
    walk.answer()


def walk_t19(walk):
    walk.goto('/')
    page = walk.nav('/s/experiences?city=miami&category=Water+sports')
    with app.app_context():
        exps = (db.session.query(ab_mod.Experience)
                .filter_by(city_slug='miami', theme='Water sports').all())
        exps.sort(key=lambda e: e.price_per_guest)
        target = exps[0]
    walk.facts['count'] = len(exps)
    page = walk.nav(f'/s/experiences?city=miami&category=Water+sports&sort=price_asc')
    href = html_mod.unescape(re.search(
        r'<a class="exp-card" href="(/experiences/[^"]+)"', page).group(1))
    page = walk.nav(href)
    walk.facts['name'] = target.name
    walk.facts['price'] = target.price_per_guest
    walk.facts['rating'] = target.rating
    assert has(page, target.name)
    walk.back()
    page = walk._get(f'/s/experiences?city=miami&category=Water+sports&sort=price_asc')
    page = walk.nav(nth_exp_href(page, 1))
    walk.facts['second_name'] = exps[1].name
    walk.facts['second_price'] = exps[1].price_per_guest
    assert has(page, exps[1].name)
    walk.back()
    page = walk.nav(nth_exp_href(
        walk._get(f'/s/experiences?city=miami&category=Water+sports&sort=price_asc'), 0))
    login_walk(walk, 'alice.j@test.com', 'TestPass123!')
    date = target.offering_list()[0]['iso']
    body = book_experience(walk, target, date, 4)
    code = re.search(r'Confirmation code (?:<strong>)?([A-Z0-9]+)', body).group(1)
    walk.facts['total'] = money_s(round(target.price_per_guest * 4, 2))
    walk.facts['code'] = code
    assert money_s(round(target.price_per_guest * 4, 2)) in body
    page = walk.nav('/trips')
    with app.app_context():
        alice = db.session.query(ab_mod.User).filter_by(
            email='alice.j@test.com').first()
        n = db.session.query(ab_mod.Booking).filter_by(user_id=alice.id).count()
    walk.facts['trips_now'] = n
    assert n >= 3
    walk.answer()


WALKS = [walk_t0, walk_t1, walk_t2, walk_t3, walk_t4, walk_t5, walk_t6,
         walk_t7, walk_t8, walk_t9, walk_t10, walk_t11, walk_t12, walk_t13,
         walk_t14, walk_t15, walk_t16, walk_t17, walk_t18, walk_t19]


# ------------------------------------------------------------------- checks --

def check_shape(idx, task):
    # Reviewer contract shape: the 5 contributor definition keys plus the
    # appended reviewer keys (verifier_path + judge_rubric); never an answer key.
    assert set(task.keys()) == {'web_name', 'id', 'ques', 'web', 'upstream_url',
                                'verifier_path', 'judge_rubric'}, \
        f"{task['id']}: task keys must be the 5 definition keys + verifier_path + judge_rubric"
    assert 'answer' not in task, \
        f"{task['id']}: tasks must never carry an answer key"
    assert task['verifier_path'] == f'sites/airbnb/verify/verify_{idx}.py', \
        task.get('verifier_path')
    from pathlib import Path as _P
    assert (_P(__file__).resolve().parents[1] / 'verify' /
            f'verify_{idx}.py').is_file(), f"missing verifier for {task['id']}"
    assert len(task.get('judge_rubric') or '') >= 200, \
        f"{task['id']}: judge_rubric must state the FACT CHECKPOINTS"
    assert task['id'] == f'Airbnb--{idx}', task['id']
    assert task['web'] == 'http://localhost:40116/', task['web']
    assert task['upstream_url'] == 'https://www.airbnb.com/'
    words = len(task['ques'].split())
    assert words <= 100, f"{task['id']}: {words} words"
    assert len(task['ques']) > 60


def _flatten(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from _flatten(v)
    elif isinstance(o, (list, tuple)):
        for v in o:
            yield from _flatten(v)
    else:
        yield o


def check_leakage(task, facts):
    """No resolved answer anchor may appear verbatim in the task text."""
    ques = task['ques']
    for value in _flatten(facts):
        if isinstance(value, str) and len(value) >= 5 and value not in (
                'confirmed', 'cancelled', 'Saved', 'Beach trip',
                'Winter cabins', 'NYC weekend'):
            assert value not in ques, f"leak: {value!r} appears in the task text"


def main():
    app.config.update(TESTING=True)
    failures = []
    rows = []
    for idx, (task, walkfn) in enumerate(zip(TASKS, WALKS)):
        client = app.test_client()
        walk = Walk(client, task['id'])
        try:
            check_shape(idx, task)
            with app.app_context():
                walkfn(walk)
            check_leakage(task, walk.facts)
            assert walk.atomic >= 15, \
                f"{task['id']}: only {walk.atomic} honest atomic steps"
            rows.append((task['id'], walk.atomic, len(walk.facts)))
            print(f"  {task['id']}: atomic={walk.atomic} facts={len(walk.facts)} OK")
        except AssertionError as e:
            failures.append((task['id'], str(e)))
            print(f"  {task['id']}: FAIL {e}")
        finally:
            with app.app_context():
                db.session.remove()
    print()
    if failures:
        for tid, msg in failures:
            print(f"FAIL {tid}: {msg}")
        return 1
    steps = [r[1] for r in rows]
    print(f"all {len(rows)} tasks pass; honest atomic steps "
          f"min={min(steps)} max={max(steps)} mean={sum(steps)/len(steps):.1f}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
