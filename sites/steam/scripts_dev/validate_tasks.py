#!/usr/bin/env python3
"""Honest-path task auditor for the steam mirror.

For every task in tasks.jsonl this walker drives the exact honest path a
solving agent must take through the mirror UI (Flask test client, real CSRF
tokens, forms submitted the way a browser submits them), verifies each
premise the task relies on, collects the answers the task asks for, counts
the atomic UI actions the task requires, and fails when a task leaks its
own answers or can be finished in fewer than 15 honest atomic steps.

Caliber (frozen audit-trail standard, same as the WebHarbor audits): an
atomic step is one navigation the task needs, one form-field fill, one
select, or one submit; reads of reported facts are never counted; the
initial home load is not counted. GET filter forms count one fill per
changed field plus the Apply navigation, exactly as a browser submits
them. Search-box term entry counts one fill.

Runs two fully independent rounds (fresh database each time) and reports
both step counts; they must agree. Also emits the expected answers it
collected to scraped_data/expected_answers.json (gitignored) for the
verify/ contract.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE))

MIN_STEPS = 15
MAX_STEPS = 24

# answers whose values the task premise legitimately names (comparison
# choices between items the text itself lists, or status words); these are
# exempt from the naive text-leak check.
EXEMPT_LEAK_KEYS = {
    'more_ram', 'higher', 'cheaper', 'more_recent', 'more_storage',
    'mac_game', 'both_mac', 'persisted', 'cart_after', 'line_item', 'items',
    'removed',
}


class Walker:
    """Counts honest atomic actions and collects expected answers."""

    def __init__(self, client):
        self.c = client
        self.steps = 0
        self.answers = {}
        self.visited = []

    # ---------------------------------------------------------------- nav --
    def nav(self, path, follow=False):
        r = self.c.get(path, follow_redirects=follow)
        assert r.status_code == 200, f'{path} -> {r.status_code}'
        self.steps += 1
        self.visited.append(path)
        return r.data.decode()

    def nav_home(self):
        """The initial store load is the benchmark start; not counted."""
        r = self.c.get('/')
        assert r.status_code == 200
        self.visited.append('/')
        return r.data.decode()

    # --------------------------------------------------------------- forms --
    def csrf(self, path):
        r = self.c.get(path)
        assert r.status_code == 200, f'{path} -> {r.status_code}'
        m = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', r.data)
        assert m, f'no csrf token on {path}'
        return m.group(1).decode()

    def fill_get(self, path, fields):
        """A GET filter form: one step per changed field, one for Apply."""
        self.steps += len(fields)
        query = '&'.join(f'{k}={quote(str(v))}' for k, v in fields.items())
        r = self.c.get(f'{path}?{query}')
        assert r.status_code == 200, f'{path}?{query} -> {r.status_code}'
        self.steps += 1
        self.visited.append(f'{path}?{query}')
        return r.data.decode()

    def login(self, email, password):
        token = self.csrf('/account/login/')
        self.steps += 3  # email fill + password fill + submit
        r = self.c.post('/account/login/', data={
            'email': email, 'password': password, 'csrf_token': token,
        }, follow_redirects=True)
        assert r.status_code == 200
        return r.data.decode()

    def signup(self, name, email, password):
        token = self.csrf('/account/signup/')
        self.steps += 4  # name + email + password fills + submit
        r = self.c.post('/account/signup/', data={
            'name': name, 'email': email, 'password': password,
            'csrf_token': token,
        }, follow_redirects=True)
        assert r.status_code == 200
        return r.data.decode()

    def post(self, path, data, from_path='/'):
        token = self.csrf(from_path)
        self.steps += 1
        r = self.c.post(path, data={**data, 'csrf_token': token},
                        follow_redirects=True)
        assert r.status_code == 200, f'{path} -> {r.status_code}'
        self.visited.append(path)
        return r.data.decode()

    def checkout(self, full_name, email, address1, city, state, zipcode,
                 payment):
        token = self.csrf('/checkout/')
        self.steps += 7  # 6 address fields + payment select
        self.steps += 1  # place order
        r = self.c.post('/checkout/', data={
            'full_name': full_name, 'email': email, 'address1': address1,
            'city': city, 'state': state, 'zipcode': zipcode,
            'payment_method': payment, 'csrf_token': token,
        }, follow_redirects=True)
        assert r.status_code == 200
        self.visited.append('/checkout/')
        return r.data.decode()

    # ------------------------------------------------------------- helpers --
    def rows(self, html):
        return re.findall(
            r'<a class="t" href="(/app/(\d+)/[^"]*)">([^<]+)</a>', html)

    def row_for(self, html, name):
        for url, appid, title in self.rows(html):
            if title == name:
                return url, appid
        raise AssertionError(f'no search row named {name!r}')

    def wishlist_names(self, html):
        return re.findall(
            r'class="capsule" href="(/app/(\d+)/[^"]*)">\s*'
            r'<img src="[^"]*" alt="([^"]+)"', html)

    def wishlist_count(self, html):
        return len(re.findall(r'class="capsule"', html))

    def order_no(self, html):
        m = re.search(r'[Yy]our order (ST-\d+) is confirmed', html)
        assert m, 'no order confirmation number on page'
        return m.group(1)

    def game_url(self, appid):
        return f'/app/{appid}/'

    def open_game(self, appid):
        return self.nav(self.game_url(appid))

    def spec(self, html, level, key):
        m = re.search(
            rf'windows &mdash; {level}.*?<th>{key}</th><td>([^<]+)</td>',
            html, re.S)
        assert m, f'missing {level} {key} spec'
        return m.group(1).strip()


# --------------------------------------------------------------------------
# per-task honest paths
# --------------------------------------------------------------------------

def task_0(w):
    """RPG under $20 -> discounted count -> cheapest -> detail -> wishlist."""
    w.nav_home()
    html = w.fill_get('/search/', {'genre': 'RPG', 'maxprice': 20})
    total = int(re.search(r'([\d,]+) results', html).group(1).replace(',', ''))
    assert total == 15, f'premise: expected 15 paid RPGs under $20, got {total}'
    html = w.fill_get('/search/', {'genre': 'RPG', 'maxprice': 20,
                                    'specials': 1})
    on_sale = int(re.search(r'([\d,]+) results', html)
                  .group(1).replace(',', ''))
    assert on_sale == 9, f'premise: expected 9 discounted paid RPGs under $20, got {on_sale}'
    html = w.fill_get('/search/', {'genre': 'RPG', 'maxprice': 20,
                                   'sort': 'Price_ASC'})
    rows = w.rows(html)
    assert rows[0][2] == 'Black Desert', f'cheapest is {rows[0][2]}'
    html = w.open_game(582660)
    assert 'Mostly Positive' in html and 'May 24, 2017' in html
    assert '51,519' in html
    w.login('alice.j@test.com', 'TestPass123!')
    w.post('/wishlist/toggle', {'appid': '582660', 'next': '/wishlist/'},
           from_path=w.game_url(582660))
    html = w.nav('/wishlist/')
    count = w.wishlist_count(html)
    assert count == 3, f'alice wishlist should show 3, got {count}'
    w.answers = {
        'rpg_count': total, 'on_sale': on_sale,
        'cheapest_name': 'Black Desert', 'cheapest_price': '$0.99',
        'review_desc': 'Mostly Positive', 'release_date': 'May 24, 2017',
        'total_reviews': '51,519', 'wishlist': 3,
    }


def task_1(w):
    """Linux + discounted -> most expensive -> sysreq; total specials."""
    w.nav_home()
    html = w.fill_get('/search/', {'os': 'linux', 'specials': 1})
    total = int(re.search(r'([\d,]+) results', html).group(1).replace(',', ''))
    assert total == 2, f'premise: expected 2 linux specials, got {total}'
    html = w.fill_get('/search/', {'os': 'linux', 'specials': 1,
                                   'sort': 'Price_DESC'})
    rows = w.rows(html)
    assert rows[0][2] == 'Stellaris', f'most expensive is {rows[0][2]}'
    html = w.open_game(281990)
    min_os = w.spec(html, 'minimum', 'OS')
    assert 'Very Positive' in html
    html = w.fill_get('/search/', {'specials': 1})
    all_specials = int(re.search(r'([\d,]+) results', html)
                       .group(1).replace(',', ''))
    assert all_specials == 24, all_specials
    w.login('bob.s@test.com', 'TestPass123!')
    w.post('/wishlist/toggle', {'appid': '281990', 'next': '/wishlist/'},
           from_path=w.game_url(281990))
    html = w.nav('/wishlist/')
    count = w.wishlist_count(html)
    assert count == 3, f'bob wishlist should show 3, got {count}'
    w.answers = {
        'count': total, 'expensive_name': 'Stellaris',
        'expensive_price': '$14.99', 'expensive_discount': '70',
        'min_os': min_os, 'review_desc': 'Very Positive',
        'all_specials': all_specials, 'wishlist': 3,
    }


def task_2(w):
    """CS2 vs Dota 2 min RAM; Dota positive reviews; both to Bob."""
    w.nav_home()
    html = w.fill_get('/search/', {'term': 'counter-strike'})
    _, cs2_id = w.row_for(html, 'Counter-Strike 2')
    html = w.open_game(cs2_id)
    cs2_ram = w.spec(html, 'minimum', 'Memory')
    assert cs2_ram == '8 GB RAM', cs2_ram
    assert 'Aug 21, 2012' in html and 'Very Positive' in html
    html = w.fill_get('/search/', {'term': 'dota'})
    _, dota_id = w.row_for(html, 'Dota 2')
    html = w.open_game(dota_id)
    dota_ram = w.spec(html, 'minimum', 'Memory')
    assert dota_ram == '4 GB RAM', dota_ram
    html = w.nav(f'/app/{dota_id}/reviews/')
    html = w.fill_get(f'/app/{dota_id}/reviews/', {'filter': 'positive'})
    shown = len(re.findall(r'class="review-card"', html))
    assert shown == 10, f'expected 10 positive reviews shown, got {shown}'
    first = re.search(r'<span class="who">([^<]+) <small>', html).group(1)
    w.login('bob.s@test.com', 'TestPass123!')
    w.post('/wishlist/toggle', {'appid': dota_id, 'next': '/wishlist/'},
           from_path=w.game_url(dota_id))
    w.post('/wishlist/toggle', {'appid': cs2_id, 'next': '/wishlist/'},
           from_path=w.game_url(cs2_id))
    html = w.nav('/wishlist/')
    count = w.wishlist_count(html)
    assert count == 4, count
    w.answers = {
        'cs2_ram': cs2_ram, 'dota_ram': dota_ram,
        'more_ram': 'Counter-Strike 2', 'cs2_release': 'Aug 21, 2012',
        'cs2_review': 'Very Positive', 'positive_shown': 10,
        'recent_positive_author': first, 'wishlist': 4,
    }


def task_3(w):
    """Carol: remove Terraria, add Hades II + Vampire Survivors."""
    w.nav_home()
    w.login('carol.m@test.com', 'TestPass123!')
    html = w.nav('/wishlist/')
    names = [n for _, _, n in w.wishlist_names(html)]
    assert 'Terraria' in names and len(names) == 3, names
    terraria_id = next(a for _, a, n in w.wishlist_names(html)
                       if n == 'Terraria')
    w.post('/wishlist/toggle', {'appid': terraria_id, 'next': '/wishlist/'},
           from_path='/wishlist/')
    html = w.fill_get('/search/', {'term': 'hades ii'})
    _, hades2_id = w.row_for(html, 'Hades II')
    html = w.open_game(hades2_id)
    assert '$20.99' in html and 'Sep 25, 2025' in html
    assert '30' in html
    w.post('/wishlist/toggle', {'appid': hades2_id, 'next': '/wishlist/'},
           from_path=w.game_url(hades2_id))
    html = w.fill_get('/search/', {'genre': 'Casual', 'maxprice': 10,
                                   'sort': 'Price_ASC'})
    _, cheap_id = w.row_for(html, 'Vampire Survivors')
    html = w.open_game(cheap_id)
    assert '$4.99' in html
    w.post('/wishlist/toggle', {'appid': cheap_id, 'next': '/wishlist/'},
           from_path=w.game_url(cheap_id))
    html = w.nav('/wishlist/')
    names = [n for _, _, n in w.wishlist_names(html)]
    assert len(names) == 4 and 'Terraria' not in names, names
    w.answers = {
        'removed': 'Terraria', 'hades2_price': '$20.99',
        'hades2_discount': '30', 'hades2_release': 'Sep 25, 2025',
        'cheap_name': 'Vampire Survivors', 'cheap_price': '$4.99',
        'remaining': ', '.join(sorted(names)), 'wishlist': 4,
    }


def task_4(w):
    """Elden Ring x2 + Portal Bundle -> checkout as Bob."""
    w.nav_home()
    html = w.fill_get('/search/', {'term': 'elden ring'})
    _, elden_id = w.row_for(html, 'ELDEN RING')
    w.post('/cart/add', {'kind': 'game', 'appid': elden_id, 'qty': '1'},
           from_path=w.game_url(elden_id))
    html = w.fill_get('/search/', {'term': 'portal'})
    _, portal2_id = w.row_for(html, 'Portal 2')
    html = w.open_game(portal2_id)
    m = re.search(r'href="(/bundle/(\d+)/[^"]*)">Portal Bundle</a>', html)
    assert m, 'no Portal Bundle link on Portal 2 page'
    bundle_url, bundle_id = m.group(1), m.group(2)
    assert bundle_id == '234'
    html = w.nav(bundle_url)
    assert '$14.98' in html
    w.post('/cart/add', {'kind': 'bundle', 'bundle_id': bundle_id,
                          'qty': '1'}, from_path=bundle_url)
    html = w.nav('/cart/')
    item_id = re.search(r'name="item_id" value="(\d+)"', html).group(1)
    w.steps += 1  # quantity select
    html = w.post('/cart/update', {'item_id': item_id, 'qty': '2'},
                  from_path='/cart/')
    assert '$134.96' in html, 'subtotal after qty=2 expected $134.96'
    w.login('bob.s@test.com', 'TestPass123!')
    html = w.checkout('Bob Smith', 'bob.s@test.com', '7 Coast Road',
                     'Austin', 'TX', '78701', 'Mastercard')
    order = w.order_no(html)
    assert '$134.96' in html
    w.answers = {
        'bundle_price': '$14.98', 'subtotal': '$134.96',
        'order_no': order, 'total': '$134.96',
    }


def task_5(w):
    """Specials: top-2 discounts, indie filter, cheapest; wishlist add."""
    w.nav_home()
    html = w.nav('/specials/')
    total = int(re.search(r'(\d+) discounted games', html).group(1))
    assert total == 24, f'premise: 24 specials, got {total}'
    blocks = re.findall(
        r'<div class="row">.*?href="/app/(\d+)/[^"]*">.*?'
        r'<a class="t" href="/app/\d+/[^"]*">([^<]+)</a>.*?'
        r'<span class="discount-badge">-(\d+)%</span>', html, re.S)
    top = sorted(blocks, key=lambda b: -int(b[2]))[:2]
    assert top[0][1] == 'Black Desert', top
    assert top[1][1].startswith('Tom Clancy'), top
    html = w.open_game(582660)
    assert 'Mostly Positive' in html and 'May 24, 2017' in html
    html = w.fill_get('/specials/', {'genre': 'Indie'})
    indie_sale = int(re.search(r'(\d+) discounted games', html).group(1))
    assert indie_sale == 6, indie_sale
    html = w.fill_get('/specials/', {'os': 'mac'})
    mac_sale = int(re.search(r'(\d+) discounted games', html).group(1))
    assert mac_sale == 5, mac_sale
    html = w.fill_get('/specials/', {'sort': 'Price_ASC'})
    rows = w.rows(html)
    assert rows[0][2] == 'Black Desert', rows[0][2]
    html = w.open_game(582660)
    assert 'May 24, 2017' in html
    html = w.fill_get('/specials/', {'sort': 'Price_DESC'})
    rows = w.rows(html)
    assert rows[0][2] == 'Jurassic World Evolution 3', rows[0][2]
    html = w.open_game(2958130)
    assert 'Very Positive' in html and '$40.19' in html
    w.login('carol.m@test.com', 'TestPass123!')
    w.post('/wishlist/toggle', {'appid': '582660', 'next': '/wishlist/'},
           from_path=w.game_url(582660))
    html = w.nav('/wishlist/')
    count = w.wishlist_count(html)
    assert count == 4, count
    w.answers = {
        'specials_count': total,
        'top1_name': 'Black Desert', 'top1_discount': '90',
        'top1_final': '$0.99', 'top1_original': '$9.99',
        'top1_savings': '$9.00',
        'top2_discount': '90', 'top2_final': '$2.99',
        'top2_original': '$29.99', 'top2_savings': '$27.00',
        'indie_sale': indie_sale, 'mac_sale': mac_sale,
        'cheapest_special': 'Black Desert', 'cheapest_price': '$0.99',
        'expensive_special': 'Jurassic World Evolution 3',
        'expensive_review': 'Very Positive', 'expensive_price': '$40.19',
        'review_desc': 'Mostly Positive', 'release_date': 'May 24, 2017',
        'wishlist': 4,
    }


def task_6(w):
    """Stellaris negative reviews + news + Bob wishlist."""
    w.nav_home()
    html = w.fill_get('/search/', {'term': 'stellaris'})
    _, st_id = w.row_for(html, 'Stellaris')
    html = w.open_game(st_id)
    assert '$14.99' in html
    html = w.nav(f'/app/{st_id}/reviews/')
    desc = re.search(r'<div class="desc">([^<]+)</div>', html).group(1).strip()
    total_reviews = re.search(r'([\d,]+) total reviews', html).group(1)
    html = w.fill_get(f'/app/{st_id}/reviews/', {'filter': 'negative'})
    shown = len(re.findall(r'class="review-card"', html))
    assert shown == 10, f'expected 10 negative, got {shown}'
    first = re.search(r'<span class="who">([^<]+) <small>', html).group(1)
    playtime = re.search(r'([\d,.]+) hrs on record', html).group(1)
    html = w.fill_get(f'/app/{st_id}/reviews/', {'filter': 'negative',
                                                 'sort': 'helpful'})
    helpful = re.search(r'<span class="who">([^<]+) <small>', html).group(1)
    html = w.nav(f'/news/{st_id}/')
    newest = re.search(r'<div class="t"><a href="[^"]+">([^<]+)</a>',
                       html).group(1)
    w.login('bob.s@test.com', 'TestPass123!')
    w.post('/wishlist/toggle', {'appid': st_id, 'next': '/wishlist/'},
           from_path=w.game_url(st_id))
    html = w.nav('/wishlist/')
    count = w.wishlist_count(html)
    assert count == 3, count
    w.answers = {
        'review_desc': desc, 'total_reviews': total_reviews,
        'negative_count': 10, 'recent_author': first,
        'recent_playtime': playtime, 'helpful_author': helpful,
        'price': '$14.99', 'discount': '70', 'newest_news': newest,
        'wishlist': 3,
    }


def task_7(w):
    """Valve developer + publisher pages; free games' facts; HL:Alyx to Dana."""
    w.nav_home()
    html = w.fill_get('/search/', {'term': 'counter-strike'})
    _, cs2_id = w.row_for(html, 'Counter-Strike 2')
    html = w.open_game(cs2_id)
    cs2_release = re.search(r'Release Date: ([^<]+)<', html).group(1).strip()
    assert 'Very Positive' in html
    m = re.search(r'href="(/developer/[^"]+)">Valve</a>', html)
    assert m, 'no Valve developer link'
    html = w.nav(m.group(1))
    count = int(re.search(r'(\d+) games in the catalog', html).group(1))
    assert count == 17, f'premise: 17 Valve games, got {count}'
    rows = w.rows(html)
    assert rows[0][2] == 'Half-Life: Alyx', rows[0][2]
    free = len(re.findall(r'price-final free', html))
    assert free == 3, f'premise: 3 free Valve games, got {free}'
    html = w.open_game(570)
    assert 'Dota 2' in html
    dota_release = re.search(r'Release Date: ([^<]+)<', html).group(1).strip()
    assert 'Very Positive' in html
    html = w.open_game(440)
    assert 'Team Fortress 2' in html
    tf2_release = re.search(r'Release Date: ([^<]+)<', html).group(1).strip()
    assert 'Very Positive' in html
    html = w.open_game(546560)
    assert 'Mar 23, 2020' in html and 'Overwhelmingly Positive' in html
    w.post('/cart/add', {'kind': 'game', 'appid': '546560', 'qty': '1'},
           from_path=w.game_url(546560))
    html = w.nav('/cart/')
    assert '$59.99' in html
    item_id = re.search(r'name="item_id" value="(\d+)"', html).group(1)
    html = w.post('/cart/remove', {'item_id': item_id}, from_path='/cart/')
    assert 'Your cart is empty' in html
    html = w.nav('/publisher/valve/')
    pub_count = int(re.search(r'(\d+) games in the catalog', html).group(1))
    assert pub_count == 19, pub_count
    w.login('dana.k@test.com', 'TestPass123!')
    w.post('/wishlist/toggle', {'appid': '546560', 'next': '/wishlist/'},
           from_path=w.game_url(546560))
    html = w.nav('/wishlist/')
    wl = w.wishlist_count(html)
    assert wl == 2, wl
    w.answers = {
        'valve_count': count, 'most_expensive': 'Half-Life: Alyx',
        'most_expensive_price': '$59.99', 'free_count': 3,
        'cs2_release': cs2_release, 'cs2_review': 'Very Positive',
        'dota_release': dota_release, 'dota_review': 'Very Positive',
        'tf2_release': tf2_release, 'tf2_review': 'Very Positive',
        'alyx_release': 'Mar 23, 2020',
        'alyx_review': 'Overwhelmingly Positive',
        'publisher_count': pub_count,
        'free_games': 'Counter-Strike 2, Dota 2, Team Fortress 2',
        'wishlist': 2,
    }


def task_8(w):
    """CS2 vs Dota 2 news recency; Dota 2 to Carol."""
    w.nav_home()
    html = w.fill_get('/search/', {'term': 'counter-strike'})
    _, cs2_id = w.row_for(html, 'Counter-Strike 2')
    html = w.open_game(cs2_id)
    html = w.nav(f'/news/{cs2_id}/')
    items = re.findall(r'<div class="t"><a href="(/news/item/[^"]+)">'
                       r'([^<]+)</a></div>\s*<div class="d">Posted ([^<]+)<',
                       html)
    assert items, 'no cs2 news items'
    cs2_title, cs2_date = items[0][1], items[0][2]
    assert cs2_title == 'Counter-Strike 2 Update', cs2_title
    gid = items[0][0].rstrip('/').rsplit('/', 1)[-1]
    html = w.nav(f'/news/item/{gid}/')
    feed = re.search(r'<div class="feed"[^>]*>\s*([^<]+)', html) \
        .group(1).strip()
    assert 'Community Announcements' in feed, feed
    html = w.fill_get('/search/', {'term': 'dota'})
    _, dota_id = w.row_for(html, 'Dota 2')
    html = w.open_game(dota_id)
    html = w.nav(f'/news/{dota_id}/')
    items = re.findall(r'<div class="t"><a href="(/news/item/[^"]+)">'
                       r'([^<]+)</a></div>\s*<div class="d">Posted ([^<]+)<',
                       html)
    dota_title, dota_date = items[0][1], items[0][2]
    assert dota_title.startswith('7.41f'), dota_title
    html = w.nav(w.game_url(cs2_id))
    assert 'Free To Play' in html and 'Very Positive' in html
    w.login('carol.m@test.com', 'TestPass123!')
    w.post('/wishlist/toggle', {'appid': dota_id, 'next': '/wishlist/'},
           from_path=w.game_url(dota_id))
    html = w.nav('/wishlist/')
    wl = w.wishlist_count(html)
    assert wl == 4, wl
    w.answers = {
        'cs2_news_title': cs2_title, 'cs2_news_feed': feed,
        'cs2_news_date': cs2_date, 'dota_news_title': dota_title,
        'dota_news_date': dota_date, 'more_recent': 'Counter-Strike 2',
        'cs2_price': 'Free To Play', 'cs2_review': 'Very Positive',
        'wishlist': 4,
    }


def task_9(w):
    """Portal Bundle math + checkout as Alice."""
    w.nav_home()
    html = w.fill_get('/search/', {'term': 'portal'})
    _, portal2_id = w.row_for(html, 'Portal 2')
    html = w.open_game(portal2_id)
    m = re.search(r'href="(/bundle/(\d+)/[^"]*)">Portal Bundle</a>', html)
    assert m, 'no portal bundle link'
    bundle_url, bundle_id = m.group(1), m.group(2)
    html = w.nav(bundle_url)
    assert '$14.98' in html and '$19.98' in html and '$5.00' in html
    w.post('/cart/add', {'kind': 'bundle', 'bundle_id': bundle_id,
                          'qty': '1'}, from_path=bundle_url)
    html = w.nav('/cart/')
    assert '$14.98' in html
    w.login('alice.j@test.com', 'TestPass123!')
    html = w.checkout('Alice Johnson', 'alice.j@test.com', '42 Pipeline Way',
                      'Bellevue', 'WA', '98004', 'Visa')
    order = w.order_no(html)
    assert 'Portal Bundle' in html and '$14.98' in html
    w.answers = {
        'bundle_price': '$14.98', 'separate_total': '$19.98',
        'savings': '$5.00', 'subtotal': '$14.98',
        'order_no': order, 'total': '$14.98',
        'line_item': 'Portal Bundle',
    }


def task_10(w):
    """Signup + free Action game + wishlist persistence."""
    w.nav_home()
    w.signup('Frank Nova', 'frank.n@test.com', 'Ocean2026!')
    html = w.fill_get('/search/', {'maxprice': 'free'})
    total = int(re.search(r'([\d,]+) results', html).group(1).replace(',', ''))
    assert total == 14, f'premise: 14 free games, got {total}'
    html = w.fill_get('/search/', {'maxprice': 'free', 'genre': 'Action',
                                   'sort': 'Price_ASC'})
    _, tf2_id = w.row_for(html, 'Team Fortress 2')
    html = w.open_game(tf2_id)
    assert 'Very Positive' in html and '743,012' in html
    w.post('/wishlist/toggle', {'appid': tf2_id, 'next': '/wishlist/'},
           from_path=w.game_url(tf2_id))
    html = w.nav('/wishlist/')
    assert 'Team Fortress 2' in html
    w.nav('/account/logout', follow=True)
    w.login('frank.n@test.com', 'Ocean2026!')
    html = w.nav('/wishlist/')
    assert 'Team Fortress 2' in html
    count = w.wishlist_count(html)
    assert count == 1, count
    w.answers = {
        'free_count': total, 'game': 'Team Fortress 2',
        'review_desc': 'Very Positive', 'total_reviews': '743,012',
        'wishlist': 1, 'persisted': 'yes',
    }


def task_11(w):
    """Indie survey: newest (WARDOGS) + most expensive + under $15."""
    w.nav_home()
    html = w.nav('/genre/indie/')
    total = int(re.search(r'(\d+) games', html).group(1))
    assert total == 31, f'premise: 31 indie games, got {total}'
    html = w.fill_get('/genre/indie/', {'sort': 'Released_DESC'})
    rows = w.rows(html)
    assert rows[0][2] == 'WARDOGS', rows[0][2]
    newest_id = rows[0][1]
    html = w.fill_get('/genre/indie/', {'sort': 'Price_DESC'})
    rows = w.rows(html)
    assert rows[0][2] == 'Shovel Knight: Treasure Trove', rows[0][2]
    shovel_id = rows[0][1]
    html = w.open_game(shovel_id)
    shovel_release = re.search(r'Release Date: ([^<]+)<', html).group(1)
    html = w.fill_get('/genre/indie/', {'maxprice': 15})
    under15 = int(re.search(r'(\d+) games', html).group(1))
    assert under15 == 10, under15
    html = w.open_game(newest_id)
    area = re.search(r'<div class="purchase-box">.*?'
                     r'<div class="price-area">(.*?)</div>', html,
                     re.S).group(1)
    assert 'discount-badge' not in area, 'newest indie game must not be discounted'
    assert 'Very Positive' in html
    html = w.nav(f'/app/{newest_id}/reviews/')
    newest_desc = re.search(r'<div class="desc">([^<]+)</div>',
                            html).group(1).strip()
    w.login('dana.k@test.com', 'TestPass123!')
    w.post('/wishlist/toggle', {'appid': newest_id, 'next': '/wishlist/'},
           from_path=w.game_url(newest_id))
    html = w.nav('/wishlist/')
    wl = w.wishlist_count(html)
    assert wl == 2, wl
    w.answers = {
        'indie_count': total, 'newest_name': 'WARDOGS',
        'newest_price': '$39.99',
        'most_expensive': 'Shovel Knight: Treasure Trove',
        'most_expensive_price': '$39.99', 'shovel_release': shovel_release,
        'under15': under15, 'review_desc': 'Very Positive',
        'discounted': 'no discount', 'newest_reviews_desc': newest_desc,
        'wishlist': 2,
    }


def task_12(w):
    """Alice order history + new L4D2 order."""
    w.nav_home()
    w.login('alice.j@test.com', 'TestPass123!')
    html = w.nav('/account/')
    m = re.search(r'(ST-\d+)</a>', html)
    assert m and m.group(1) == 'ST-1001', m.group(1) if m else None
    assert '$19.98' in html, 'fixture order total expected'
    html = w.fill_get('/search/', {'term': 'left 4 dead 2'})
    _, l4d2_id = w.row_for(html, 'Left 4 Dead 2')
    w.post('/cart/add', {'kind': 'game', 'appid': l4d2_id, 'qty': '1'},
           from_path=w.game_url(l4d2_id))
    w.nav('/cart/')
    html = w.checkout('Alice Johnson', 'alice.j@test.com', '42 Pipeline Way',
                      'Bellevue', 'WA', '98004', 'Visa')
    order = w.order_no(html)
    assert '$9.99' in html
    html = w.nav('/account/')
    orders = re.findall(r'(ST-\d+)</a>', html)
    assert len(orders) == 2, orders
    w.answers = {
        'existing_order': 'ST-1001', 'existing_total': '$19.98',
        'new_order': order, 'new_total': '$9.99', 'order_count': 2,
    }


def task_13(w):
    """Mixed Action games; cheapest (Minecraft Dungeons II) requirements."""
    w.nav_home()
    html = w.fill_get('/search/', {'genre': 'Action', 'review_type': 'mixed'})
    total = int(re.search(r'([\d,]+) results', html).group(1).replace(',', ''))
    assert total == 2, f'premise: 2 mixed action games, got {total}'
    names = [n for _, _, n in w.rows(html)]
    assert sorted(names) == ['Minecraft Dungeons II',
                              'Monster Hunter Wilds'], names
    html = w.fill_get('/search/', {'genre': 'Action', 'review_type': 'mixed',
                                   'sort': 'Price_ASC'})
    rows = w.rows(html)
    assert rows[0][2] == 'Minecraft Dungeons II', rows[0][2]
    cheap_id, exp_id = rows[0][1], rows[1][1]
    html = w.open_game(cheap_id)
    min_os = w.spec(html, 'minimum', 'OS')
    min_cpu = w.spec(html, 'minimum', 'Processor')
    min_ram = w.spec(html, 'minimum', 'Memory')
    assert 'Mixed' in html and '2,709' in html and '61%' in html
    html = w.nav(f'/app/{cheap_id}/reviews/')
    cheap_desc = re.search(r'<div class="desc">([^<]+)</div>',
                           html).group(1).strip()
    html = w.open_game(exp_id)
    exp_ram = w.spec(html, 'minimum', 'Memory')
    assert exp_ram == '16 GB RAM', exp_ram
    w.login('alice.j@test.com', 'TestPass123!')
    w.post('/wishlist/toggle', {'appid': cheap_id, 'next': '/wishlist/'},
           from_path=w.game_url(cheap_id))
    html = w.nav('/wishlist/')
    wl = w.wishlist_count(html)
    assert wl == 3, wl
    w.answers = {
        'count': total, 'names': ', '.join(sorted(names)),
        'cheap_name': 'Minecraft Dungeons II', 'cheap_price': '$29.99',
        'exp_name': 'Monster Hunter Wilds', 'exp_price': '$39.99',
        'min_os': min_os, 'min_cpu': min_cpu, 'min_ram': min_ram,
        'total_reviews': '2,709', 'cheap_pct': '61',
        'exp_min_ram': exp_ram, 'wishlist': 3,
    }


def task_14(w):
    """Dota vs CS2 percentages; TF2 too; all three to Dana."""
    w.nav_home()
    html = w.fill_get('/search/', {'maxprice': 'free'})
    total = int(re.search(r'([\d,]+) results', html).group(1).replace(',', ''))
    assert total == 14, total
    html = w.fill_get('/search/', {'term': 'dota'})
    _, dota_id = w.row_for(html, 'Dota 2')
    html = w.open_game(dota_id)
    assert 'Very Positive' in html and '88%' in html and '840,128' in html
    html = w.fill_get('/search/', {'term': 'counter-strike'})
    _, cs2_id = w.row_for(html, 'Counter-Strike 2')
    html = w.open_game(cs2_id)
    assert 'Very Positive' in html and '86%' in html and '2,624,184' in html
    html = w.fill_get('/search/', {'term': 'team fortress'})
    _, tf2_id = w.row_for(html, 'Team Fortress 2')
    html = w.open_game(tf2_id)
    assert 'Very Positive' in html
    w.login('dana.k@test.com', 'TestPass123!')
    for appid in (dota_id, cs2_id, tf2_id):
        w.post('/wishlist/toggle', {'appid': appid, 'next': '/wishlist/'},
               from_path=w.game_url(appid))
    html = w.nav('/wishlist/')
    wl = w.wishlist_count(html)
    assert wl == 4, wl
    w.answers = {
        'free_count': total, 'dota_review': 'Very Positive',
        'dota_pct': '88', 'dota_total': '840,128',
        'cs2_review': 'Very Positive', 'cs2_pct': '86',
        'cs2_total': '2,624,184', 'tf2_review': 'Very Positive',
        'higher': 'Dota 2', 'wishlist': 4,
    }


def task_15(w):
    """Dead Cells DLC + bundles + cart add/remove."""
    w.nav_home()
    html = w.fill_get('/search/', {'term': 'dead cells'})
    _, dc_id = w.row_for(html, 'Dead Cells')
    html = w.open_game(dc_id)
    dlcs = re.findall(r'href="(/app/(\d+)/[^"]*)">([^<]+)</a>'
                      r'\s*</span>\s*<span class="price-final">(\$[\d.]+)</span>',
                      html)
    assert len(dlcs) == 4, f'premise: 4 DLCs, got {len(dlcs)}'
    assert dlcs[0][2] == 'Dead Cells: The Bad Seed', dlcs
    html = w.nav(dlcs[0][0])
    dlc_release = re.search(r'Release Date: ([^<]+)<', html).group(1).strip()
    w.post('/cart/add', {'kind': 'game', 'appid': dlcs[0][1], 'qty': '1'},
           from_path=dlcs[0][0])
    html = w.nav('/cart/')
    assert '$4.99' in html
    item_id = re.search(r'name="item_id" value="(\d+)"', html).group(1)
    html = w.post('/cart/remove', {'item_id': item_id}, from_path='/cart/')
    assert 'Your cart is empty' in html
    html = w.nav(w.game_url(dc_id))
    area = re.search(r'<div class="purchase-box">.*?'
                     r'<div class="price-area">(.*?)</div>', html,
                     re.S).group(1)
    dc_price = re.search(r'<span class="price-final">(\$[\d.]+)</span>',
                         area).group(1)
    dc_discount = 'discounted' if 'discount-badge' in area \
        else 'no discount'
    assert dc_discount == 'no discount', \
        'premise: Dead Cells carries no active discount in the seed'
    bundles = re.findall(r'href="(/bundle/(\d+)/[^"]*)">([^<]+)</a>'
                         r'\s*</span>\s*<span class="discount-badge">',
                         html)
    assert len(bundles) == 3, f'premise: 3 bundles, got {len(bundles)}'
    first_bundle = bundles[0]
    assert first_bundle[2] == 'Dead Cells: Medley of Pain Bundle', bundles
    html = w.nav(first_bundle[0])
    assert '$39.95' in html
    w.post('/cart/add', {'kind': 'bundle', 'bundle_id': first_bundle[1],
                          'qty': '1'}, from_path=first_bundle[0])
    html = w.nav('/cart/')
    assert '$39.95' in html
    item_id = re.search(r'name="item_id" value="(\d+)"', html).group(1)
    html = w.post('/cart/remove', {'item_id': item_id},
                  from_path='/cart/')
    assert 'Your cart is empty' in html
    w.post('/cart/add', {'kind': 'game', 'appid': dc_id, 'qty': '1'},
           from_path=w.game_url(dc_id))
    html = w.nav('/cart/')
    item_id = re.search(r'name="item_id" value="(\d+)"', html).group(1)
    w.steps += 1  # quantity select
    html = w.post('/cart/update', {'item_id': item_id, 'qty': '3'},
                  from_path='/cart/')
    assert '$74.97' in html, '3x Dead Cells expected $74.97'
    item_id = re.search(r'name="item_id" value="(\d+)"', html).group(1)
    html = w.post('/cart/remove', {'item_id': item_id},
                  from_path='/cart/')
    assert 'Your cart is empty' in html
    second_bundle = bundles[1]
    html = w.nav(second_bundle[0])
    second_price = re.search(r'<span class="price-final">(\$[\d.]+)</span>',
                             html).group(1)
    w.answers = {
        'dlc_count': 4, 'first_dlc': dlcs[0][2], 'first_dlc_price': dlcs[0][3],
        'dlc_release': dlc_release, 'dlc_subtotal': '$4.99',
        'dc_price': dc_price, 'dc_discount': dc_discount,
        'bundle_name': 'Dead Cells: Medley of Pain Bundle',
        'bundle_price': '$39.95', 'bundle_items': 5,
        'subtotal': '$39.95', 'cart_after': 'empty',
        'triple_total': '$74.97',
        'second_bundle': second_bundle[2], 'second_bundle_price': second_price,
    }


def task_16(w):
    """Resident Evil trio; Action refine; newest to Carol."""
    w.nav_home()
    html = w.fill_get('/search/', {'term': 'resident'})
    total = int(re.search(r'([\d,]+) results', html).group(1).replace(',', ''))
    assert total == 3, total
    rows = w.rows(html)
    names = [n for _, _, n in rows]
    assert sorted(names) == ['Resident Evil 2', 'Resident Evil 4',
                              'Resident Evil Village'], names
    html = w.fill_get('/search/', {'term': 'resident', 'genre': 'Action'})
    refined = int(re.search(r'([\d,]+) results', html)
                  .group(1).replace(',', ''))
    assert refined == 3, refined
    infos = {}
    for appid, name in [(883710, 'Resident Evil 2'),
                        (1196590, 'Resident Evil Village'),
                        (2050650, 'Resident Evil 4')]:
        html = w.open_game(appid)
        price = re.search(r'<span class="price-final">(\$[\d.]+)</span>',
                          html).group(1)
        rel = re.search(r'Release Date: ([^<]+)<', html).group(1).strip()
        infos[name] = (price, rel)
    assert infos['Resident Evil 4'][1] == 'Mar 23, 2023'
    html = w.nav('/app/2050650/reviews/')
    re4_desc = re.search(r'<div class="desc">([^<]+)</div>',
                         html).group(1).strip()
    html = w.nav('/news/2050650/')
    re4_news = re.search(r'<div class="t"><a href="[^"]+">([^<]+)</a>',
                         html).group(1)
    w.login('carol.m@test.com', 'TestPass123!')
    w.post('/wishlist/toggle', {'appid': '2050650', 'next': '/wishlist/'},
           from_path=w.game_url(2050650))
    html = w.nav('/wishlist/')
    wl = w.wishlist_count(html)
    assert wl == 4, wl
    w.answers = {
        'count': total, 'refined': refined,
        'names': ', '.join(sorted(names)),
        're4_price': infos['Resident Evil 4'][0],
        're4_release': infos['Resident Evil 4'][1],
        're2_price': infos['Resident Evil 2'][0],
        're2_release': infos['Resident Evil 2'][1],
        'village_price': infos['Resident Evil Village'][0],
        'village_release': infos['Resident Evil Village'][1],
        'most_recent': 'Resident Evil 4', 're4_review': re4_desc,
        're4_news': re4_news, 'wishlist': 4,
    }


def task_17(w):
    """Hades vs Hades II; reviews; cart add/remove; Hades II to Alice."""
    w.nav_home()
    html = w.fill_get('/search/', {'term': 'hades'})
    total = int(re.search(r'([\d,]+) results', html).group(1).replace(',', ''))
    assert total == 2, total
    html = w.open_game(1145360)
    assert '$6.24' in html and '75' in html and '$24.99' in html
    assert 'Sep 17, 2020' in html and 'Overwhelmingly Positive' in html
    hades_mac = 'mac' in html
    html = w.open_game(1145350)
    assert '$20.99' in html and '30' in html and '$29.99' in html
    assert 'Sep 25, 2025' in html and 'Overwhelmingly Positive' in html
    hades2_mac = 'mac' in html
    assert hades_mac and hades2_mac
    html = w.nav('/app/1145350/reviews/')
    html = w.fill_get('/app/1145350/reviews/', {'filter': 'positive'})
    first = re.search(r'<span class="who">([^<]+) <small>', html).group(1)
    w.post('/cart/add', {'kind': 'game', 'appid': '1145360', 'qty': '1'},
           from_path=w.game_url(1145360))
    html = w.nav('/cart/')
    assert '$6.24' in html
    item_id = re.search(r'name="item_id" value="(\d+)"', html).group(1)
    html = w.post('/cart/remove', {'item_id': item_id},
                  from_path='/cart/')
    assert 'Your cart is empty' in html
    w.login('alice.j@test.com', 'TestPass123!')
    w.post('/wishlist/toggle', {'appid': '1145350', 'next': '/wishlist/'},
           from_path=w.game_url(1145350))
    html = w.nav('/wishlist/')
    wl = w.wishlist_count(html)
    assert wl == 3, wl
    w.answers = {
        'count': total,
        'hades_price': '$6.24', 'hades_discount': '75',
        'hades_original': '$24.99', 'hades_release': 'Sep 17, 2020',
        'hades_review': 'Overwhelmingly Positive',
        'hades2_price': '$20.99', 'hades2_discount': '30',
        'hades2_original': '$29.99', 'hades2_release': 'Sep 25, 2025',
        'hades2_review': 'Overwhelmingly Positive',
        'cheaper': 'Hades', 'both_mac': 'yes',
        'recent_positive_author': first, 'cart_subtotal': '$6.24',
        'wishlist': 3,
    }


def task_18(w):
    """FF7R + Hades deals; checkout as Dana."""
    w.nav_home()
    html = w.nav('/specials/')
    html = w.open_game(1462040)
    assert '75' in html and '$9.99' in html and '$39.99' in html
    w.post('/cart/add', {'kind': 'game', 'appid': '1462040', 'qty': '1'},
           from_path=w.game_url(1462040))
    html = w.nav('/specials/')
    html = w.open_game(1145360)
    assert '75' in html and '$6.24' in html and '$24.99' in html
    w.post('/cart/add', {'kind': 'game', 'appid': '1145360', 'qty': '1'},
           from_path=w.game_url(1145360))
    html = w.nav('/cart/')
    assert '$16.23' in html
    w.login('dana.k@test.com', 'TestPass123!')
    html = w.checkout('Dana Kim', 'dana.k@test.com', '88 Neon Street',
                      'Seattle', 'WA', '98101', 'PayPal')
    order = w.order_no(html)
    assert '$16.23' in html
    assert 'FINAL FANTASY VII REMAKE INTERGRADE' in html and 'Hades' in html
    w.answers = {
        'ff7_discount': '75', 'ff7_final': '$9.99', 'ff7_original': '$39.99',
        'ff7_savings': '$30.00', 'hades_discount': '75',
        'hades_final': '$6.24', 'hades_original': '$24.99',
        'hades_savings': '$18.75', 'subtotal': '$16.23',
        'order_no': order, 'total': '$16.23',
        'items': 'FINAL FANTASY VII REMAKE INTERGRADE, Hades',
    }


def task_19(w):
    """Cyberpunk vs Elden Ring requirements; reviews; cart; wishlist."""
    w.nav_home()
    html = w.fill_get('/search/', {'term': 'cyberpunk'})
    _, cp_id = w.row_for(html, 'Cyberpunk 2077')
    html = w.open_game(cp_id)
    cp_min_ram = w.spec(html, 'minimum', 'Memory')
    cp_rec_ram = w.spec(html, 'recommended', 'Memory')
    cp_min_gpu = w.spec(html, 'minimum', 'Graphics')
    cp_storage = w.spec(html, 'minimum', 'Storage')
    assert cp_min_ram == '12 GB RAM' and cp_rec_ram == '16 GB RAM'
    cp_mac = 'mac' in html
    html = w.fill_get('/search/', {'term': 'elden ring'})
    _, er_id = w.row_for(html, 'ELDEN RING')
    html = w.open_game(er_id)
    er_min_ram = w.spec(html, 'minimum', 'Memory')
    er_rec_ram = w.spec(html, 'recommended', 'Memory')
    er_min_gpu = w.spec(html, 'minimum', 'Graphics')
    er_storage = w.spec(html, 'minimum', 'Storage')
    assert er_min_ram == '12 GB RAM' and er_rec_ram == '16 GB RAM'
    assert 'mac' not in html
    assert cp_mac
    assert '$59.99' in html and 'Very Positive' in html
    html = w.nav(f'/app/{cp_id}/reviews/')
    cp_desc = re.search(r'<div class="desc">([^<]+)</div>',
                        html).group(1).strip()
    cp_shown = len(re.findall(r'class="review-card"', html))
    w.post('/cart/add', {'kind': 'game', 'appid': cp_id, 'qty': '1'},
           from_path=w.game_url(cp_id))
    html = w.nav('/cart/')
    assert '$59.99' in html
    item_id = re.search(r'name="item_id" value="(\d+)"', html).group(1)
    html = w.post('/cart/remove', {'item_id': item_id},
                  from_path='/cart/')
    assert 'Your cart is empty' in html
    w.login('dana.k@test.com', 'TestPass123!')
    w.post('/wishlist/toggle', {'appid': er_id, 'next': '/wishlist/'},
           from_path=w.game_url(er_id))
    html = w.nav('/wishlist/')
    wl = w.wishlist_count(html)
    assert wl == 2, wl
    w.answers = {
        'cp_min_ram': cp_min_ram, 'cp_rec_ram': cp_rec_ram,
        'cp_gpu': cp_min_gpu, 'cp_storage': cp_storage,
        'er_min_ram': er_min_ram, 'er_rec_ram': er_rec_ram,
        'er_gpu': er_min_gpu, 'er_storage': er_storage,
        'more_storage': 'Cyberpunk 2077', 'mac_game': 'Cyberpunk 2077',
        'er_price': '$59.99', 'er_review': 'Very Positive',
        'cp_review': cp_desc, 'cp_shown': cp_shown,
        'cart_subtotal': '$59.99', 'wishlist': 2,
    }


TASKS = {
    0: task_0, 1: task_1, 2: task_2, 3: task_3, 4: task_4, 5: task_5,
    6: task_6, 7: task_7, 8: task_8, 9: task_9, 10: task_10, 11: task_11,
    12: task_12, 13: task_13, 14: task_14, 15: task_15, 16: task_16,
    17: task_17, 18: task_18, 19: task_19,
}


# --------------------------------------------------------------------------
# harness
# --------------------------------------------------------------------------

def fresh_client(tag):
    root = Path(tempfile.mkdtemp(prefix=f'steam-audit-{tag}-', dir='/tmp'))
    os.environ['STEAM_DB_URI'] = f'sqlite:///{root / "steam.db"}'
    os.environ.pop('WEBSYN_SKIP_BOOTSTRAP', None)
    for mod in list(sys.modules):
        if mod.startswith(('app', 'seed')):
            del sys.modules[mod]
    import app as A
    A.app.config.update(TESTING=True)
    return A, A.app.test_client(), root


def check_no_leak(task_text, answers):
    """The task wording must not already contain a discovery answer."""
    text = task_text.casefold()
    for key, value in answers.items():
        if key in EXEMPT_LEAK_KEYS:
            continue
        value = str(value).casefold().strip()
        if value and len(value) > 3 and value in text:
            raise AssertionError(f'task text leaks answer {key}={value!r}')


TASK_TEXTS = {}


def run_round(tag):
    results = {}
    for idx in sorted(TASKS):
        A, client, root = fresh_client(f'{tag}-{idx}')
        w = Walker(client)
        status = 'ok'
        try:
            TASKS[idx](w)
            check_no_leak(TASK_TEXTS[idx], w.answers)
            results[idx] = {'steps': w.steps, 'answers': w.answers}
        except AssertionError as exc:
            results[idx] = {'steps': w.steps, 'answers': w.answers,
                            'error': str(exc)}
            status = f'FAIL: {exc}'
        finally:
            shutil.rmtree(root, ignore_errors=True)
        print(f'  [{tag}] Steam--{idx}: {w.steps} steps  {status}', flush=True)
    return results


def check_task_shape(tasks):
    """Reviewer contract shape gate: the contributor's five keys plus the
    reviewer contract keys verifier_path and judge_rubric (never an answer
    key), goal-style wording at or under 100 words."""
    failures = []
    for idx, task in enumerate(tasks):
        keys = list(task.keys())
        want = ['web_name', 'id', 'ques', 'web', 'upstream_url',
                'verifier_path', 'judge_rubric']
        if keys != want:
            failures.append(f'Steam--{idx}: key shape {keys} != {want}')
        if 'answer' in task:
            failures.append(f'Steam--{idx}: answer key must never exist')
        if task.get('id') != f'Steam--{idx}':
            failures.append(f'Steam--{idx}: id mismatch {task.get("id")}')
        if task.get('web') != 'http://localhost:40140/':
            failures.append(f'Steam--{idx}: web port mismatch {task.get("web")}')
        if task.get('verifier_path') != f'sites/steam/verify/verify_{idx}.py':
            failures.append(f'Steam--{idx}: verifier_path mismatch '
                            f'{task.get("verifier_path")}')
        if not (SITE / 'verify' / f'verify_{idx}.py').is_file():
            failures.append(f'Steam--{idx}: verifier file missing')
        rubric = task.get('judge_rubric') or ''
        if not rubric.startswith('FACT CHECKPOINTS:'):
            failures.append(f'Steam--{idx}: judge_rubric must be English '
                            f'rules only (FACT CHECKPOINTS style)')
        words = len(task['ques'].split())
        if words > 100:
            failures.append(f'Steam--{idx}: ques too long ({words} words)')
    return failures


def main():
    global TASK_TEXTS
    lines = (SITE / 'tasks.jsonl').read_text(encoding='utf-8').splitlines()
    tasks = [json.loads(line) for line in lines if line.strip()]
    assert len(tasks) == len(TASKS), f'{len(tasks)} tasks vs {len(TASKS)} walkers'
    shape_failures = check_task_shape(tasks)
    if shape_failures:
        for f in shape_failures:
            print(f'  FAIL: {f}', flush=True)
        return 1
    TASK_TEXTS = {i: t['ques'] for i, t in enumerate(tasks)}

    print('=== honest-path audit, two independent rounds', flush=True)
    r1 = run_round('r1')
    r2 = run_round('r2')

    failures = []
    total_steps = 0
    for idx in sorted(TASKS):
        a, b = r1[idx], r2[idx]
        if 'error' in a:
            failures.append(f'Steam--{idx} round1: {a["error"]}')
        if 'error' in b:
            failures.append(f'Steam--{idx} round2: {b["error"]}')
        if a['steps'] != b['steps']:
            failures.append(f'Steam--{idx}: step counts disagree '
                            f'({a["steps"]} vs {b["steps"]})')
        if a.get('answers') != b.get('answers'):
            failures.append(f'Steam--{idx}: answers disagree between rounds')
        if a['steps'] < MIN_STEPS:
            failures.append(f'Steam--{idx}: only {a["steps"]} honest steps '
                            f'(< {MIN_STEPS})')
        if a['steps'] > MAX_STEPS:
            failures.append(f'Steam--{idx}: {a["steps"]} honest steps '
                            f'(> {MAX_STEPS})')
        total_steps += a['steps']

    expected = {f'Steam--{idx}': r1[idx]['answers'] for idx in sorted(TASKS)}
    out = SITE / 'scraped_data' / 'expected_answers.json'
    out.write_text(json.dumps(expected, indent=1, sort_keys=True),
                   encoding='utf-8')

    print(f'=== {len(TASKS)} tasks, {total_steps} atomic actions total, '
          f'min {min(r1[i]["steps"] for i in TASKS)} / '
          f'max {max(r1[i]["steps"] for i in TASKS)} / '
          f'mean {total_steps / len(TASKS):.1f} per task', flush=True)
    if failures:
        for f in failures:
            print(f'  FAIL: {f}', flush=True)
        return 1
    print('=== all tasks pass the honest-path audit in both rounds', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
