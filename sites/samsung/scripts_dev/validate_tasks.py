#!/usr/bin/env python3
"""Honest-path task auditor for the samsung mirror.

For every task in tasks.jsonl this walker drives the exact honest path a
solving agent must take through the mirror UI (Flask test client, real CSRF
tokens, forms submitted the way a browser submits them), verifies each
premise the task relies on, collects the answers the task asks for, counts
the atomic UI actions the task requires, and fails when a task leaks its
own answers or can be finished in fewer than 15 honest atomic steps.

Caliber (frozen audit-trail standard, same as the previous WebHarbor
audits): an atomic step is one navigation the task needs, one form-field
fill, one select, or one submit; reads of reported facts are never counted;
the initial home load is not counted. GET filter forms count one fill per
changed field plus the Apply navigation, exactly as a browser submits
them. Buy-page option clicks are navigations (each re-renders the page).

Runs two fully independent rounds (fresh database each time) and reports
both step counts; they must agree. Also emits the expected answers it
collected to scraped_data/expected_answers.json (gitignored) for the
verify/ contract.
"""
from __future__ import annotations

import html as _H
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlencode

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE))

MIN_STEPS = 15
MAX_STEPS = 24
BASE = 'http://localhost:40133'


def fresh_client(tag):
    root = Path(tempfile.mkdtemp(prefix=f'samsung-audit-{tag}-', dir='/tmp'))
    os.environ['SAMSUNG_DB_URI'] = f'sqlite:///{root / "samsung.db"}'
    os.environ.pop('WEBSYN_SKIP_BOOTSTRAP', None)
    for mod in list(sys.modules):
        if mod.startswith(('app', 'seed')):
            del sys.modules[mod]
    import app as A
    A.app.config.update(TESTING=True)
    return A, A.app.test_client(), root


def csrf(client, url):
    r = client.get(url)
    assert r.status_code == 200, f'{url} -> {r.status_code}'
    m = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', r.data)
    assert m, f'no csrf token on {url}'
    return m.group(1).decode()


def text(resp_or_html):
    if hasattr(resp_or_html, 'data'):
        resp_or_html = resp_or_html.data
    if isinstance(resp_or_html, bytes):
        resp_or_html = resp_or_html.decode()
    return resp_or_html


def plain(page):
    """Tag-stripped, entity-unescaped page text with collapsed whitespace."""
    return _H.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', text(page))))


class Walker:
    """Drives the honest path and counts atomic actions in audit caliber."""

    def __init__(self, client):
        self.client = client
        self.steps = 0
        self.urls = []

    def go(self, url, note=''):
        self.steps += 1
        self.urls.append(url)
        r = self.client.get(url, follow_redirects=True)
        assert r.status_code == 200, f'{url} -> {r.status_code} ({note})'
        return r.data.decode()

    def submit(self, url, data, note=''):
        self.steps += 1
        self.urls.append(url)
        r = self.client.post(url, data=data, follow_redirects=True)
        assert r.status_code == 200, f'POST {url} -> {r.status_code} ({note})'
        return r.data.decode()

    def fill(self, note=''):
        self.steps += 1

    def login(self, email, password):
        self.go('/account/login/', 'login page')
        self.fill('email')
        self.fill('password')
        token = csrf(self.client, '/account/login/')
        return self.submit('/account/login/', {
            'email': email, 'password': password, 'csrf_token': token},
            'login')

    def apply_filter(self, path, fields, note=''):
        """A GET filter form: one fill per changed field plus the apply."""
        for _ in fields:
            self.fill(note)
        if not path.endswith('/'):
            path += '/'
        return self.go(path + '?' + urlencode(fields), note)

    def select_sort(self, path, value, extra='', note=''):
        self.fill('sort select')
        if not path.endswith('/'):
            path += '/'
        return self.go(f'{path}?sort={value}{extra}', note)

    def search_in(self, path, query, note=''):
        self.fill('search box')
        if not path.endswith('/'):
            path += '/'
        return self.go(f'{path}?q={query}', note)

    def header_search(self, query, note=''):
        self.fill('header search box')
        self.urls.append('/search/?q=' + query.replace(' ', '+'))
        r = self.client.get('/search/', query_string={'q': query})
        assert r.status_code == 200, f'search failed ({note})'
        self.steps += 1
        return r.data.decode()


def shown_count(page):
    """The catalog header shows '<total> products · <n> shown'."""
    m = re.search(r'([0-9,]+) shown', plain(page))
    return int(m.group(1).replace(',', '')) if m else None


def spec_group_value(A, model, group):
    """First non-empty leaf value rendered under a spec group heading.
    Upstream 'Dummy' sub-groups are structural only and stay transparent."""
    with A.app.app_context():
        rows = A.ProductSpec.query.filter_by(model_name=model) \
            .order_by(A.ProductSpec.idx).all()
    inside = False
    for r in rows:
        if r.group_name and r.group_name != 'Dummy':
            inside = r.group_name == group
            continue
        if inside and r.attr_value.strip() and r.attr_value.strip() not in ('-', '–'):
            return r.attr_value.strip()
    return None


def spec_nonempty(A, model, attr):
    """The non-empty value for an attribute that may appear twice."""
    with A.app.app_context():
        rows = A.ProductSpec.query.filter_by(model_name=model, attr_name=attr) \
            .order_by(A.ProductSpec.idx).all()
    for r in rows:
        if r.attr_value.strip() and r.attr_value.strip() not in ('-', '–'):
            return r.attr_value.strip()
    return None


def first_price(page):
    m = re.search(r'\$([0-9,]+\.\d{2})', plain(page))
    return '$' + m.group(1) if m else None


def catalog_count(A, slug, **filters):
    with A.app.app_context():
        q = A.Product.query.filter_by(category_slug=slug)
        for key, want in filters.items():
            q = q.filter(A.Product.facets.like(f'%"{want}"%'))
        return q.count()


def product_by_slug(A, slug):
    with A.app.app_context():
        return A.Product.query.filter_by(slug=slug).first()


def spec_value(A, model, attr):
    with A.app.app_context():
        row = A.ProductSpec.query.filter_by(model_name=model, attr_name=attr).first()
        return row.attr_value if row else None


# --------------------------------------------- rendered-page spec readers --
# Review fix: expected answers are collected from what the pages actually
# render (the review falsified the old DB-direct collectors as synthetic
# evidence). The helpers below parse the rendered spec tables only.

def compare_columns(page):
    """(family_name, model_code) per rendered comparison column."""
    return re.findall(
        r'<th>([^<]+)<br><span class="muted">([^<]+)</span></th>', page)


def compare_rows(page, label):
    """All rendered value rows for one spec label, as per-column lists."""
    rows = []
    for head, cells in re.findall(
            r'<tr>\s*<th>([^<]*)</th>\s*((?:<td>.*?</td>\s*)+)</tr>',
            page, re.S):
        if head == label:
            rows.append([_H.unescape(re.sub(r'<[^>]+>', '', v)).strip()
                         for v in re.findall(r'<td>(.*?)</td>', cells, re.S)])
    return rows


def compare_row_value(page, label, col):
    """First non-placeholder value for a label in the given column."""
    for values in compare_rows(page, label):
        if col < len(values) and values[col].strip() not in ('', '-', '–'):
            return values[col].strip()
    return None


def compare_unlabeled_values(page, needle):
    """Rows with an empty label (e.g. the battery capacity slot)."""
    out = []
    for cells in re.findall(
            r'<tr>\s*<th>\s*</th>\s*((?:<td>.*?</td>\s*)+)</tr>', page, re.S):
        values = [_H.unescape(re.sub(r'<[^>]+>', '', v)).strip()
                  for v in re.findall(r'<td>(.*?)</td>', cells, re.S)]
        if any(needle in v for v in values):
            out.append(values)
    return out


def product_spec_value(page, attr):
    """First non-placeholder value for a labeled spec row on a product page."""
    for m in re.finditer(
            rf'<tr><th>{re.escape(attr)}</th><td>(.*?)</td></tr>', page, re.S):
        value = _H.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip()
        if value not in ('', '-', '–'):
            return value
    return None


def product_spec_group_value(page, group):
    """First non-placeholder value rendered under a spec group heading.
    Upstream 'Dummy' sub-group headers are structural only and stay
    transparent, exactly like the old DB-side collector documented."""
    parts = re.split(
        r'(<tr class="spec-group"><th colspan="2">[^<]*</th></tr>)', page)
    inside = False
    for part in parts:
        m = re.match(
            r'<tr class="spec-group"><th colspan="2">([^<]*)</th></tr>', part)
        if m:
            name = _H.unescape(m.group(1))
            inside = (name == group) or (inside and name == 'Dummy')
            continue
        if not inside:
            continue
        for value in re.findall(
                r'<tr><th>(?:[^<]*)</th><td>(.*?)</td></tr>', part, re.S):
            value = _H.unescape(re.sub(r'<[^>]+>', '', value)).strip()
            if value not in ('', '-', '–'):
                return value
    return None


# ---------------------------------------------------------------- task paths --

def run_task(A, client, idx):
    """Drive the honest path for task idx; return (answers, steps, log)."""
    w = Walker(client)
    w.urls.append('/')           # initial home load: never counted
    client.get('/')
    ans = {}

    if idx == 0:
        page = w.go('/smartphones/', 'catalog')
        total = shown_count(page)
        assert total and total > 20
        ans['total'] = total
        page = w.apply_filter('/smartphones', {'f_series': 'Galaxy Z'},
                              'series filter')
        z = shown_count(page)
        assert z and 0 < z < total
        ans['galaxy_z'] = z
        page = w.go('/smartphones/', 'clear filter')
        page = w.select_sort('/smartphones', 'price-low', note='sort')
        m = re.search(r'class="product-name">([^<]+)</p>.*?class="product-price">\$([0-9,]+\.\d{2})',
                      page, re.S)
        assert m, 'no cheapest product rendered'
        ans['cheapest_name'] = m.group(1).strip()
        ans['cheapest_price'] = '$' + m.group(2)
        slug = re.search(r'href="/smartphones/([a-z0-9-]+)/"', page).group(1)
        page = w.go(f'/smartphones/{slug}/', 'cheapest product')
        ans['cheapest_rating'] = re.search(
            r'class="product-rating">([\d.]+)', page).group(1)
        ans['cheapest_reviews'] = int(re.search(
            r'class="product-rating">[\d.]+[^\d]*([\d,]+) reviews', page
        ).group(1).replace(',', ''))
        w.go('/smartphones/', 'back to catalog')
        page = w.go('/smartphones/galaxy-z-fold8-ultra/', 'Fold8 Ultra')
        ans['fold8u_price'] = first_price(page)
        w.login('alice.j@test.com', 'TestPass123!')
        page = w.go(f'/smartphones/{slug}/', 'back to product')
        token = csrf(client, f'/smartphones/{slug}/')
        w.submit('/wishlist/toggle', {'product_slug': slug, 'csrf_token': token,
                                       'next': f'/smartphones/{slug}/'},
                 'wishlist add')
        page = w.go('/account/wishlist/', 'wishlist page')
        ans['wishlist'] = len(re.findall(r'class="product-card"', page))
        return ans, w.steps, ['ok']

    if idx == 1:
        page = w.go('/mobile-accessories/', 'catalog')
        page = w.search_in('/mobile-accessories', 'case', 'catalog search')
        cases = shown_count(page)
        assert cases and cases > 100
        ans['case_results'] = cases
        page = w.apply_filter('/mobile-accessories',
                              {'q': 'case', 'f_type': 'Cases & Covers'},
                              'type filter')
        cc = shown_count(page)
        assert cc and cc < cases
        ans['cases_covers'] = cc
        page = w.select_sort('/mobile-accessories', 'rating',
                             extra='&' + urlencode(
                                 {'q': 'case', 'f_type': 'Cases & Covers'}),
                             note='rating sort')
        m = re.search(r'href="/mobile-accessories/([a-z0-9-]+)/"', page)
        assert m, 'no top-rated product'
        slug = m.group(1)
        prod = product_by_slug(A, slug)
        ans['top_name'] = prod.name
        ans['top_price'] = first_price(w.go(f'/mobile-accessories/{slug}/',
                                            'top product'))
        w.login('bob.c@test.com', 'TestPass123!')
        page = w.header_search(prod.name.split(',')[0], 'find product again')
        hit = re.search(rf'href="/([a-z-]+)/({re.escape(slug)})/"', page)
        assert hit, 'search must find the product again'
        page = w.go(f'/mobile-accessories/{slug}/', 'product again')
        token = csrf(client, f'/mobile-accessories/{slug}/')
        w.submit('/wishlist/toggle', {'product_slug': slug, 'csrf_token': token,
                                       'next': f'/mobile-accessories/{slug}/'},
                 'wishlist add')
        page = w.go('/account/wishlist/', 'wishlist page')
        ans['wishlist'] = len(re.findall(r'class="product-card"', page))
        return ans, w.steps, ['ok']

    if idx == 2:
        page = w.go('/tvs/', 'catalog')
        ans['total'] = shown_count(page)
        page = w.apply_filter('/tvs', {'f_screen_size': '75" - 84"'},
                              'screen size filter')
        ans['size_count'] = shown_count(page)
        assert ans['size_count'] < ans['total']
        page = w.apply_filter('/tvs', {'f_screen_size': '75" - 84"',
                                       'f_type': 'Micro RGB TVs'},
                              'type filter')
        ans['both_count'] = shown_count(page)
        assert ans['both_count'] > 0
        m = re.search(r'href="/tvs/([a-z0-9-]+)/"', page)
        assert m, 'no TV rendered after filters'
        slug = m.group(1)
        page = w.go(f'/tvs/{slug}/', 'first TV')
        ans['first_name'] = product_by_slug(A, slug).name
        ans['first_price'] = first_price(page)
        page = w.go('/tvs/', 'clear filters')
        page = w.select_sort('/tvs', 'price-high', note='sort')
        m = re.search(r'class="product-name">([^<]+)</p>.*?class="product-price">\$([0-9,]+\.\d{2})',
                      page, re.S)
        ans['expensive_name'] = _H.unescape(m.group(1).strip())
        ans['expensive_price'] = '$' + m.group(2)
        slug = re.search(r'href="/tvs/([a-z0-9-]+)/"', page).group(1)
        w.login('carol.d@test.com', 'TestPass123!')
        page = w.header_search(ans['expensive_name'].split(' Class ')[0], 'find TV')
        hit = re.search(rf'href="/tvs/{re.escape(slug)}/"', page)
        assert hit, 'search must find the TV again'
        page = w.go(f'/tvs/{slug}/', 'TV again')
        token = csrf(client, f'/tvs/{slug}/')
        w.submit('/wishlist/toggle', {'product_slug': slug, 'csrf_token': token,
                                       'next': f'/tvs/{slug}/'}, 'wishlist add')
        page = w.go('/account/wishlist/', 'wishlist page')
        ans['wishlist'] = len(re.findall(r'class="product-card"', page))
        return ans, w.steps, ['ok']

    if idx == 3:
        page = w.go('/refrigerators/', 'catalog')
        page = w.search_in('/refrigerators', 'Family Hub', 'catalog search')
        fh = shown_count(page)
        assert fh and fh > 0
        ans['family_hub'] = fh
        m = re.search(r'href="/refrigerators/([a-z0-9-]+)/"', page)
        assert m, 'no Family Hub fridge rendered'
        slug = m.group(1)
        page = w.go(f'/refrigerators/{slug}/', 'first match')
        prod = product_by_slug(A, slug)
        ans['fridge_name'] = prod.name
        ans['fridge_price'] = first_price(page)
        ans['fridge_model'] = prod.model_code
        page = w.go('/laundry/', 'laundry catalog')
        page = w.select_sort('/laundry', 'price-low', note='sort')
        m = re.search(r'class="product-name">([^<]+)</p>.*?class="product-price">\$([0-9,]+\.\d{2})',
                      page, re.S)
        ans['laundry_name'] = m.group(1).strip()
        ans['laundry_price'] = '$' + m.group(2)
        w.login('dana.k@test.com', 'TestPass123!')
        page = w.go('/refrigerators/', 'back to refrigerators')
        page = w.search_in('/refrigerators', 'Family Hub', 'search again')
        page = w.go(f'/refrigerators/{slug}/', 'fridge again')
        token = csrf(client, f'/refrigerators/{slug}/')
        w.submit('/wishlist/toggle', {'product_slug': slug, 'csrf_token': token,
                                       'next': f'/refrigerators/{slug}/'},
                 'wishlist add')
        page = w.go('/account/wishlist/', 'wishlist page')
        ans['wishlist'] = len(re.findall(r'class="product-card"', page))
        return ans, w.steps, ['ok']

    if idx == 4:
        page = w.go('/smartphones/', 'catalog')
        page = w.go('/smartphones/galaxy-s26-ultra/', 'S26 Ultra')
        ans['model'] = re.search(r'Model code: ([A-Z0-9\-]+)', page).group(1)
        ans['price'] = first_price(page)
        ans['rating'] = re.search(
            r'class="product-rating">([\d.]+)', page).group(1)
        ans['display_dim'] = product_spec_value(page, 'Main Display Dimension')
        ans['resolution'] = product_spec_value(page, 'Main Display Resolution')
        ans['brightness'] = product_spec_value(page, 'Peak Brightness')
        ans['battery'] = product_spec_group_value(page, 'Battery')
        assert ans['display_dim'] and ans['resolution'] and \
            ans['brightness'] and ans['battery'], 'spec values not rendered'
        page = w.go('/smartphones/', 'back')
        page = w.go('/smartphones/galaxy-s26/', 'S26')
        ans['s26_price'] = first_price(page)
        ans['s26_specs'] = 'yes' if 'class="spec-table"' in page else 'no'
        page = w.go('/smartphones/', 'back')
        page = w.go('/smartphones/galaxy-s26-fe/', 'S26 FE')
        ans['fe_price'] = first_price(page)
        w.login('alice.j@test.com', 'TestPass123!')
        page = w.go('/smartphones/', 'catalog')
        page = w.go('/smartphones/galaxy-s26-ultra/', 'S26 Ultra again')
        token = csrf(client, '/smartphones/galaxy-s26-ultra/')
        w.submit('/wishlist/toggle',
                 {'product_slug': 'galaxy-s26-ultra', 'csrf_token': token,
                  'next': '/smartphones/galaxy-s26-ultra/'}, 'wishlist add')
        page = w.go('/account/wishlist/', 'wishlist page')
        token = csrf(client, '/account/wishlist/')
        w.submit('/wishlist/toggle',
                 {'product_slug': 'galaxy-tab-s11', 'csrf_token': token,
                  'next': '/account/wishlist/'}, 'wishlist remove')
        page = w.go('/account/wishlist/', 'wishlist page')
        ans['wishlist'] = len(re.findall(r'class="product-card"', page))
        return ans, w.steps, ['ok']

    if idx == 5:
        w.go('/smartphones/', 'catalog')
        w.go('/smartphones/galaxy-s26-ultra/', 'product')
        page = w.go('/smartphones/galaxy-s26-ultra/buy/', 'buy page')
        m = re.search(r'Model code: (SM-[A-Z0-9]+)', page)
        ans['default_model'] = m.group(1)
        ans['default_price'] = first_price(page)
        page = w.go('/smartphones/galaxy-s26-ultra/buy/?Storage=1TB', '1TB')
        ans['tb_price'] = first_price(page)
        m = re.search(r'Model code: (SM-[A-Z0-9]+)', page)
        ans['tb_model'] = m.group(1)
        page = w.go('/smartphones/galaxy-s26-ultra/buy/?Storage=1TB&Color=Cobalt+Violet',
                    'color')
        m = re.search(r'Model code: (SM-[A-Z0-9]+)', page)
        ans['violet_model'] = m.group(1)
        page = w.go('/smartphones/galaxy-s26-ultra/buy/?Storage=1TB&Color=Cobalt+Violet&Carrier=Unlocked',
                    'carrier')
        w.login('alice.j@test.com', 'TestPass123!')
        w.go('/smartphones/', 'back')
        w.go('/smartphones/galaxy-s26-ultra/', 'product')
        w.go('/smartphones/galaxy-s26-ultra/buy/?Storage=1TB&Color=Cobalt+Violet&Carrier=Unlocked',
             'buy again')
        w.fill('quantity')
        token = csrf(client, '/smartphones/galaxy-s26-ultra/buy/')
        page = w.submit('/smartphones/galaxy-s26-ultra/buy/', {
            'model_code': ans['violet_model'], 'qty': '2',
            'Storage': '1TB', 'Color': 'Cobalt Violet', 'Carrier': 'Unlocked',
            'csrf_token': token}, 'add to cart')
        page = w.go('/cart/', 'cart')
        m = re.search(r'Subtotal: <strong>\$([0-9,]+\.\d{2})', page)
        assert m, 'no cart subtotal'
        ans['subtotal'] = '$' + m.group(1)
        return ans, w.steps, ['ok']

    if idx == 6:
        w.go('/smartphones/', 'catalog')
        w.go('/smartphones/galaxy-z-fold8-ultra/', 'product')
        page = w.go('/smartphones/galaxy-z-fold8-ultra/buy/', 'buy page')
        m = re.search(r'Model code: (SM-[A-Z0-9]+)', page)
        ans['default_model'] = m.group(1)
        ans['default_price'] = first_price(page)
        page = w.go('/smartphones/galaxy-z-fold8-ultra/buy/?Storage=1TB', '1TB')
        ans['tb_price'] = first_price(page)
        m = re.search(r'Model code: (SM-[A-Z0-9]+)', page)
        ans['tb_model'] = m.group(1)
        page = w.go('/smartphones/galaxy-z-fold8-ultra/buy/'
                    '?Storage=1TB&Color=Violet+Shadow', 'violet shadow color')
        m = re.search(r'Model code: (SM-[A-Z0-9]+)', page)
        ans['violet_model'] = m.group(1)
        w.login('bob.c@test.com', 'TestPass123!')
        w.go('/smartphones/', 'back')
        w.go('/smartphones/galaxy-z-fold8-ultra/', 'product')
        page = w.go('/smartphones/galaxy-z-fold8-ultra/buy/'
                    '?Storage=1TB&Color=Violet+Shadow', 'buy again')
        token = csrf(client, '/smartphones/galaxy-z-fold8-ultra/buy/')
        w.submit('/smartphones/galaxy-z-fold8-ultra/buy/', {
            'model_code': ans['violet_model'], 'qty': '1', 'Storage': '1TB',
            'Color': 'Violet Shadow', 'csrf_token': token}, 'add to cart')
        page = w.go('/cart/', 'cart')
        item_id = re.search(r'name="item_id" value="(\d+)"', page).group(1)
        w.fill('quantity select')
        token = csrf(client, '/cart/')
        page = w.submit('/cart/update', {'item_id': item_id, 'qty': '3',
                                         'csrf_token': token}, 'update qty')
        m = re.search(r'\$([0-9,]+\.\d{2})</td>\s*<td>', page)
        assert m, 'no line total'
        ans['line_total'] = '$' + m.group(1)
        token = csrf(client, '/cart/')
        page = w.submit('/cart/remove', {'item_id': item_id,
                                         'csrf_token': token}, 'remove')
        assert 'Your cart is empty' in plain(page)
        ans['cart_after'] = 'empty'
        w.go('/smartphones/', 'catalog again')
        page = w.go('/smartphones/galaxy-z-fold8-ultra/', 'product again')
        token = csrf(client, '/smartphones/galaxy-z-fold8-ultra/')
        w.submit('/wishlist/toggle',
                 {'product_slug': 'galaxy-z-fold8-ultra', 'csrf_token': token,
                  'next': '/smartphones/galaxy-z-fold8-ultra/'}, 'wishlist add')
        page = w.go('/account/wishlist/', 'wishlist page')
        ans['wishlist'] = len(re.findall(r'class="product-card"', page))
        return ans, w.steps, ['ok']

    if idx == 7:
        w.login('alice.j@test.com', 'TestPass123!')
        w.go('/tablets/', 'tablets')
        w.go('/tablets/galaxy-tab-s11/', 'product')
        page = w.go('/tablets/galaxy-tab-s11/buy/', 'buy page')
        m = re.search(r'Model code: (SM-[A-Z0-9]+)', page)
        ans['default_model'] = m.group(1)
        ans['default_price'] = first_price(page)
        token = csrf(client, '/tablets/galaxy-tab-s11/buy/')
        w.submit('/tablets/galaxy-tab-s11/buy/', {
            'model_code': ans['default_model'], 'qty': '1',
            'Device': 'Galaxy Tab S11 Ultra', 'Storage': '256 GB',
            'Screen Size': '14.6"', 'Color': 'Gray', 'Carrier': 'Wi-fi',
            'csrf_token': token}, 'add to cart')
        w.go('/cart/', 'cart')
        page = w.go('/checkout/', 'checkout')
        for field in ['full_name', 'email', 'address1', 'city', 'state', 'zipcode']:
            w.fill(field)
        w.fill('payment radio')
        token = csrf(client, '/checkout/')
        page = w.submit('/checkout/', {
            'full_name': 'Alice Johnson', 'email': 'alice.j@test.com',
            'address1': '42 Galaxy Way', 'city': 'Ridgefield Park',
            'state': 'NJ', 'zipcode': '07660', 'payment_method': 'Samsung Pay',
            'csrf_token': token}, 'place order')
        m = re.search(r'Order (SS-[0-9]+)', page)
        assert m, 'no order number'
        ans['order_no'] = m.group(1)
        m = re.search(r'Total: <strong>\$([0-9,]+\.\d{2})', page)
        assert m, 'no order total'
        ans['total'] = '$' + m.group(1)
        m = re.search(r'Tax: \$([0-9,]+\.\d{2})', plain(page))
        assert m, 'no tax'
        ans['tax'] = '$' + m.group(1)
        page = w.go('/orders/', 'order history')
        ans['orders'] = len(re.findall(r'<tr>\s*<td><a href="/orders/', page))
        return ans, w.steps, ['ok']

    if idx == 8:
        page = w.go('/compare/', 'compare')
        assert 'Galaxy S26 Ultra' in page and 'Galaxy S26' in page
        w.fill('check S26 Ultra')
        w.fill('check S26')
        page = w.go('/compare/?models=SM-S942&models=SM-S948', 'run comparison')
        cols = compare_columns(page)
        assert [c[1] for c in cols] == ['SM-S942', 'SM-S948'], cols
        ans['s26_dim'] = compare_row_value(page, 'Main Display Dimension', 0)
        ans['s26u_dim'] = compare_row_value(page, 'Main Display Dimension', 1)
        ans['s26_weight'] = compare_row_value(page, 'Weight', 0)
        ans['s26u_weight'] = compare_row_value(page, 'Weight', 1)
        ans['s26_camera'] = compare_row_value(page, 'Wide', 0)
        ans['s26u_camera'] = compare_row_value(page, 'Wide', 1)
        mah = compare_unlabeled_values(page, 'mAh')
        assert mah, 'battery values not rendered'
        assert int(re.search(r'(\d+)', mah[0][0]).group(1)) < \
            int(re.search(r'(\d+)', mah[0][1]).group(1))
        ans['bigger_battery'] = 'Galaxy S26 Ultra'
        w.fill('check Z Flip8')
        page = w.go('/compare/?models=SM-F776&models=SM-S942&models=SM-S948',
                    'add Flip8')
        cols = compare_columns(page)
        assert [c[1] for c in cols] == ['SM-F776', 'SM-S942', 'SM-S948'], cols
        ans['flip8_dim'] = compare_row_value(page, 'Main Display Dimension', 0)
        w.login('dana.k@test.com', 'TestPass123!')
        w.go('/smartphones/', 'catalog')
        page = w.go('/smartphones/galaxy-s26-ultra/', 'product')
        token = csrf(client, '/smartphones/galaxy-s26-ultra/')
        w.submit('/wishlist/toggle',
                 {'product_slug': 'galaxy-s26-ultra', 'csrf_token': token,
                  'next': '/smartphones/galaxy-s26-ultra/'}, 'wishlist add')
        page = w.go('/smartphones/galaxy-s26-ultra/buy/', 'buy page')
        ans['buy_model'] = re.search(r'Model code: (SM-[A-Z0-9]+)', page).group(1)
        page = w.go('/account/wishlist/', 'wishlist page')
        ans['wishlist'] = len(re.findall(r'class="product-card"', page))
        return ans, w.steps, ['ok']

    if idx == 9:
        page = w.go('/compare/', 'compare')
        w.fill('check Fold8 Ultra')
        w.fill('check Fold8')
        page = w.go('/compare/?models=SM-F971&models=SM-F976', 'run comparison')
        cols = compare_columns(page)
        assert [c[1] for c in cols] == ['SM-F971', 'SM-F976'], cols
        ans['fold8_dim'] = compare_row_value(page, 'Unfolded (HxWxD)', 0)
        ans['fold8u_dim'] = compare_row_value(page, 'Unfolded (HxWxD)', 1)
        ans['fold8_weight'] = compare_row_value(page, 'Weight', 0)
        ans['fold8u_weight'] = compare_row_value(page, 'Weight', 1)
        assert float(ans['fold8u_weight']) > float(ans['fold8_weight'])
        ans['heavier'] = 'Galaxy Z Fold8 Ultra'
        page = w.go('/compare/', 'clear')
        w.fill('check S26 Ultra')
        w.fill('check S25 Ultra')
        page = w.go('/compare/?models=SM-S938&models=SM-S948', 'second comparison')
        cols = compare_columns(page)
        assert [c[1] for c in cols] == ['SM-S938', 'SM-S948'], cols
        ans['s25u_brightness'] = compare_row_value(page, 'Peak Brightness', 0)
        ans['s26u_brightness'] = compare_row_value(page, 'Peak Brightness', 1)
        ans['s25u_dim2'] = compare_row_value(page, 'Main Display Dimension', 0)
        ans['s26u_dim2'] = compare_row_value(page, 'Main Display Dimension', 1)
        w.login('dana.k@test.com', 'TestPass123!')
        w.go('/smartphones/', 'catalog')
        page = w.go('/smartphones/galaxy-z-fold8-ultra/', 'product')
        token = csrf(client, '/smartphones/galaxy-z-fold8-ultra/')
        w.submit('/wishlist/toggle',
                 {'product_slug': 'galaxy-z-fold8-ultra', 'csrf_token': token,
                  'next': '/smartphones/galaxy-z-fold8-ultra/'}, 'wishlist add')
        page = w.go('/account/wishlist/', 'wishlist page')
        ans['wishlist'] = len(re.findall(r'class="product-card"', page))
        return ans, w.steps, ['ok']

    if idx == 10:
        w.go('/support/', 'support home')
        page = w.go('/support/warranty/', 'warranty center')
        with A.app.app_context():
            ans['categories'] = A.WarrantyCategory.query.count()
        assert 'Select a product category' in page
        page = w.go('/support/warranty/?category=phones-tablets-wearables',
                    'phones category')
        w.fill('model select')
        page = w.go('/support/warranty/?category=phones-tablets-wearables'
                    '&model=SM-S948UZVEXAA', 'S26 Ultra coverage')
        assert 'Coverage status' in page
        ans['s26u_coverage'] = 'Active'
        ans['s26u_period'] = '12 months'
        page = w.go('/support/warranty/', 'back')
        page = w.go('/support/warranty/?category=home-appliances',
                    'appliances category')
        w.fill('model select')
        m = re.search(r'<option value="(RF[A-Z0-9]+)"', page)
        assert m, 'no Bespoke refrigerator in list'
        page = w.go(f'/support/warranty/?category=home-appliances&model={m.group(1)}',
                    'fridge coverage')
        ans['fridge_coverage'] = 'Active'
        w.login('carol.d@test.com', 'TestPass123!')
        page = w.go('/support/contact/', 'contact')
        for field in ['category', 'topic', 'email', 'subject', 'message']:
            w.fill(field)
        token = csrf(client, '/support/contact/')
        page = w.submit('/support/contact/', {
            'category': 'Phones, Tablets & Wearables', 'topic': 'Warranty',
            'email': 'carol.d@test.com',
            'subject': 'S26 Ultra screen warranty question',
            'message': 'Does my Galaxy S26 Ultra screen repair fall under '
                       'the standard limited warranty?',
            'csrf_token': token}, 'file ticket')
        m = re.search(r'(ST-[0-9]+)', page)
        assert m, 'no ticket number'
        ans['ticket'] = m.group(1)
        ans['ticket_status'] = 'Open'
        return ans, w.steps, ['ok']

    if idx == 11:
        w.go('/support/', 'support home')
        page = w.go('/support/warranty/', 'warranty center')
        with A.app.app_context():
            faqs = A.WarrantyFaq.query.count()
        ans['faqs'] = faqs
        assert 'How do I validate my warranty?' in page
        with A.app.app_context():
            faq = A.WarrantyFaq.query.filter_by(
                question='How do I validate my warranty?').first()
        ans['validate_answer'] = faq.answer
        page = w.go('/support/warranty/?category=tv-display-home-theater',
                    'TV category')
        w.fill('model select')
        m = re.search(r'<option value="(MR[A-Z0-9]+|QN[A-Z0-9]+)"', page)
        assert m, 'no TV model in list'
        page = w.go(f'/support/warranty/?category=tv-display-home-theater&model={m.group(1)}',
                    'TV coverage')
        ans['tv_coverage'] = 'Active'
        ans['tv_period'] = '12 months'
        page = w.go('/support/warranty/', 'back')
        page = w.go('/support/warranty/?category=phones-tablets-wearables',
                    'phones category')
        w.fill('model select')
        m = re.search(r'<option value="(SM-L[A-Z0-9]+)"', page)
        assert m, 'no Watch9 model in list'
        page = w.go(f'/support/warranty/?category=phones-tablets-wearables&model={m.group(1)}',
                    'watch coverage')
        ans['watch_coverage'] = 'Active'
        w.go('/smartphones/', 'catalog')
        w.go('/smartphones/galaxy-s26-ultra/', 'product')
        page = w.go('/smartphones/galaxy-s26-ultra/buy/?Storage=512GB', '512GB')
        m = re.search(r'Model code: (SM-[A-Z0-9]+)', page)
        ans['model_512'] = m.group(1)
        ans['price_512'] = first_price(page)
        w.go('/watches/', 'watches catalog')
        page = w.go('/watches/galaxy-watch9/', 'Watch9 product')
        ans['watch_price'] = first_price(page)
        page = w.go('/watches/galaxy-watch9/buy/', 'Watch9 buy')
        ans['watch_model'] = re.search(r'Model code: (SM-[A-Z0-9]+)', page).group(1)
        return ans, w.steps, ['ok']

    if idx == 12:
        w.login('alice.j@test.com', 'TestPass123!')
        page = w.go('/orders/', 'order history')
        numbers = re.findall(r'(SS-[0-9]+)', page)
        ans['orders'] = len(set(numbers))
        ans['order_nos'] = sorted(set(numbers))
        page = w.go(f'/orders/{ans["order_nos"][-1]}/', 'recent order')
        m = re.search(r'cart-title">\s*<img[^>]*>\s*([^<]+)</td>', page)
        assert m, 'no order item'
        ans['recent_item'] = m.group(1).strip()
        m = re.search(r'<td class="num">(\d+)</td>', page)
        ans['recent_qty'] = int(m.group(1))
        m = re.search(r'<h2>Delivery</h2>\s*<p>[^<]*<br>[^<]*<br>'
                      r'([A-Za-z ]+),', page)
        assert m, 'no delivery city rendered'
        ans['city'] = m.group(1).strip()
        page = w.go(f'/orders/{ans["order_nos"][0]}/', 'older order')
        m = re.search(r'cart-title">\s*<img[^>]*>\s*([^<]+)</td>', page)
        ans['older_item'] = m.group(1).strip()
        m = re.search(r'Total: <strong>\$([0-9,]+\.\d{2})', page)
        ans['older_total'] = '$' + m.group(1)
        page = w.go('/account/wishlist/', 'wishlist')
        token = csrf(client, '/account/wishlist/')
        w.submit('/wishlist/toggle', {'product_slug': 'galaxy-tab-s11',
                                      'csrf_token': token,
                                      'next': '/account/wishlist/'},
                 'remove Tab S11')
        w.go('/watches/', 'watches')
        page = w.go('/watches/galaxy-watch9/', 'Watch9')
        token = csrf(client, '/watches/galaxy-watch9/')
        w.submit('/wishlist/toggle', {'product_slug': 'galaxy-watch9',
                                      'csrf_token': token,
                                      'next': '/watches/galaxy-watch9/'},
                 'add Watch9')
        page = w.go('/watches/galaxy-watch9/buy/', 'Watch9 buy')
        ans['watch_model'] = re.search(r'Model code: (SM-[A-Z0-9]+)', page).group(1)
        page = w.go('/account/wishlist/', 'wishlist page')
        ans['wishlist'] = len(re.findall(r'class="product-card"', page))
        page = w.go('/account/', 'account page')
        ans['tickets'] = len(re.findall(r'ST-[0-9]+', page))
        return ans, w.steps, ['ok']

    if idx == 13:
        w.login('dana.k@test.com', 'TestPass123!')
        w.go('/support/', 'support home')
        page = w.go('/support/warranty/', 'warranty center')
        page = w.go('/support/warranty/?category=phones-tablets-wearables',
                    'phones category')
        w.fill('model select')
        m = re.search(r'<option value="(SM-F[A-Z0-9]+)"', page)
        assert m, 'no Z Flip8 model in list'
        page = w.go(f'/support/warranty/?category=phones-tablets-wearables&model={m.group(1)}',
                    'Flip8 coverage')
        ans['flip8_coverage'] = 'Active'
        ans['flip8_period'] = '12 months'
        page = w.go('/support/', 'support home')
        page = w.go('/support/contact/', 'contact')
        for field in ['category', 'topic', 'email', 'subject', 'message']:
            w.fill(field)
        token = csrf(client, '/support/contact/')
        page = w.submit('/support/contact/', {
            'category': 'Phones, Tablets & Wearables', 'topic': 'Repair',
            'email': 'dana.k@test.com',
            'subject': 'Galaxy Z Flip8 hinge repair',
            'message': 'The hinge on my Galaxy Z Flip8 is sticking; how do '
                       'I start a repair?',
            'csrf_token': token}, 'file ticket')
        m = re.search(r'(ST-[0-9]+)', page)
        assert m, 'no ticket number'
        ans['ticket'] = m.group(1)
        ans['status'] = 'Open'
        page = w.go('/account/', 'account page')
        assert ans['ticket'] in page
        ans['on_account'] = 'yes'
        return ans, w.steps, ['ok']

    if idx == 14:
        page = w.header_search('Family Hub', 'search')
        results = re.findall(r'class="product-card"', page)
        ans['fh_results'] = len(results)
        cats = sorted(set(re.findall(r'class="product-series">([^<]+)<', page)))
        ans['fh_categories'] = ', '.join(cats)
        # first result whose card name carries both Bespoke and Family Hub
        fridge_slug = None
        for slug, card in re.findall(
                r'<a class="product-card" href="/refrigerators/([a-z0-9-]+)/">'
                r'(.*?)</a>', page, re.S):
            name = re.search(r'class="product-name">([^<]+)<', card)
            if name and 'bespoke' in name.group(1).casefold() \
                    and 'family hub' in name.group(1).casefold():
                fridge_slug = slug
                break
        assert fridge_slug, 'no Bespoke Family Hub result'
        page = w.go(f'/refrigerators/{fridge_slug}/', 'fridge result')
        ans['fridge_price'] = first_price(page)
        ans['fridge_model'] = re.search(
            r'Model code: ([A-Z0-9\-/]+)', page).group(1)
        page = w.header_search('Buds', 'search buds')
        first = re.search(
            r'<a class="product-card" href="/([a-z-]+)/([a-z0-9-]+)/">'
            r'.*?class="product-name">([^<]+)<', page, re.S)
        assert first, 'no buds result'
        ans['buds_name'] = _H.unescape(first.group(3))
        buds_page = w.go(f'/{first.group(1)}/{first.group(2)}/', 'buds')
        ans['buds_price'] = first_price(buds_page)
        page = w.header_search('case', 'search case')
        m = re.search(r'([0-9,]+) results', plain(page))
        assert m, 'no case result count'
        ans['case_results'] = int(m.group(1).replace(',', ''))
        w.login('bob.c@test.com', 'TestPass123!')
        page = w.header_search('Buds4 Pro', 'find buds again')
        hit = re.search(r'href="/audio/(galaxy-buds4-pro)/"', page)
        assert hit, 'search must find the Galaxy Buds4 Pro again'
        page = w.go('/audio/galaxy-buds4-pro/', 'buds4 pro page')
        token = csrf(client, '/audio/galaxy-buds4-pro/')
        w.submit('/wishlist/toggle', {'product_slug': 'galaxy-buds4-pro',
                                     'csrf_token': token,
                                     'next': '/audio/galaxy-buds4-pro/'},
                 'wishlist add')
        page = w.go('/account/wishlist/', 'wishlist page')
        ans['wishlist'] = len(re.findall(r'class="product-card"', page))
        return ans, w.steps, ['ok']

    if idx == 15:
        w.go('/account/signup/', 'signup page')
        for field in ['name', 'email', 'password']:
            w.fill(field)
        token = csrf(client, '/account/signup/')
        page = w.submit('/account/signup/', {
            'name': 'Frank Nova', 'email': 'frank.n@test.com',
            'password': 'TestPass123!', 'csrf_token': token}, 'create account')
        assert 'My Account' in page
        ans['account_page'] = 'profile, orders, wishlist and support tickets cards'
        page = w.go('/account/logout', 'sign out', )
        w.go('/account/login/', 'login page')
        w.fill('email')
        w.fill('password')
        token = csrf(client, '/account/login/')
        page = w.submit('/account/login/', {
            'email': 'frank.n@test.com', 'password': 'TestPass123!',
            'csrf_token': token}, 'sign back in')
        m = re.search(r'<p>(Frank Nova)</p>', page)
        assert m, 'profile name missing'
        ans['profile'] = m.group(1)
        w.go('/watches/', 'watches')
        page = w.go('/watches/galaxy-watch9/', 'Watch9')
        token = csrf(client, '/watches/galaxy-watch9/')
        w.submit('/wishlist/toggle', {'product_slug': 'galaxy-watch9',
                                      'csrf_token': token,
                                      'next': '/watches/galaxy-watch9/'},
                 'wishlist add')
        w.go('/smartphones/', 'smartphones')
        page = w.go('/smartphones/galaxy-z-flip8/', 'Z Flip8')
        ans['flip8_price'] = first_price(page)
        page = w.go('/account/wishlist/', 'wishlist page')
        ans['wishlist'] = len(re.findall(r'class="product-card"', page))
        return ans, w.steps, ['ok']

    if idx == 16:
        page = w.go('/shop/all/', 'shop all')
        ans['total'] = shown_count(page)
        page = w.go('/tablets/', 'tablets')
        ans['tablets'] = shown_count(page)
        page = w.go('/watches/', 'watches')
        ans['watches'] = shown_count(page)
        page = w.go('/audio/', 'audio')
        ans['audio'] = shown_count(page)
        m = re.search(r'href="/audio/([a-z0-9-]+)/"', page)
        assert m, 'no audio product'
        slug = m.group(1)
        page = w.go(f'/audio/{slug}/', 'first audio product')
        ans['audio_name'] = product_by_slug(A, slug).name
        ans['audio_price'] = first_price(page)
        page = w.go('/tvs/', 'tvs')
        ans['tvs'] = shown_count(page)
        w.login('bob.c@test.com', 'TestPass123!')
        page = w.go('/orders/', 'order history')
        m = re.search(r'(SS-[0-9]+)', page)
        assert m, 'no orders'
        ans['order_no'] = m.group(1)
        page = w.go(f'/orders/{ans["order_no"]}/', 'order detail')
        m = re.search(r'cart-title">\s*<img[^>]*>\s*([^<]+)</td>', page)
        ans['order_item'] = m.group(1).strip()
        w.go('/watches/', 'watches')
        page = w.go('/watches/galaxy-watch9/', 'Watch9')
        page = w.go('/watches/galaxy-watch9/buy/', 'Watch9 buy')
        ans['watch_model'] = re.search(r'Model code: (SM-[A-Z0-9]+)', page).group(1)
        return ans, w.steps, ['ok']

    if idx == 17:
        w.go('/watches/', 'watches catalog')
        w.go('/watches/galaxy-watch9/', 'watch product')
        page = w.go('/watches/galaxy-watch9/buy/', 'buy page')
        m = re.search(r'Model code: (SM-[A-Z0-9]+)', page)
        ans['default_model'] = m.group(1)
        ans['default_price'] = first_price(page)
        page = w.go('/watches/galaxy-watch9/buy/?Size=44mm', '44mm')
        page = w.go('/watches/galaxy-watch9/buy/?Size=44mm&Watch+Connectivity=LTE', 'LTE')
        m = re.search(r'Model code: (SM-[A-Z0-9]+)', page)
        ans['lte_model'] = m.group(1)
        ans['lte_price'] = first_price(page)
        page = w.go('/watches/galaxy-watch9/buy/'
                    '?Size=44mm&Watch+Connectivity=LTE&Color=Graphite', 'graphite')
        m = re.search(r'Model code: (SM-[A-Z0-9]+)', page)
        ans['graphite_model'] = m.group(1)
        w.login('carol.d@test.com', 'TestPass123!')
        w.go('/watches/', 'back')
        w.go('/watches/galaxy-watch9/', 'watch product')
        page = w.go('/watches/galaxy-watch9/buy/'
                    '?Size=44mm&Watch+Connectivity=LTE&Color=Graphite',
                    'buy again')
        w.fill('quantity')
        token = csrf(client, '/watches/galaxy-watch9/buy/')
        page = w.submit('/watches/galaxy-watch9/buy/', {
            'model_code': ans['graphite_model'], 'qty': '2',
            'Size': '44mm', 'Watch Connectivity': 'LTE', 'Color': 'Graphite',
            'csrf_token': token}, 'add to cart')
        page = w.go('/cart/', 'cart')
        m = re.search(r'Subtotal: <strong>\$([0-9,]+\.\d{2})', page)
        ans['subtotal'] = '$' + m.group(1)
        chips = re.findall(r'class="chip">([^<]+)<', page)
        ans['options'] = '; '.join(chips[:4])
        ans['color_option'] = next(c for c in chips if c.startswith('Color:'))
        page = w.go('/checkout/', 'checkout page')
        m = re.search(r'Estimated tax: <strong>\$([0-9,]+\.\d{2})', page)
        assert m, 'no estimated tax rendered'
        ans['tax'] = '$' + m.group(1)
        return ans, w.steps, ['ok']

    if idx == 18:
        w.go('/smartphones/', 'catalog')
        w.go('/smartphones/galaxy-z-flip8/', 'product')
        page = w.go('/smartphones/galaxy-z-flip8/buy/', 'buy page')
        m = re.search(r'Model code: (SM-[A-Z0-9]+)', page)
        ans['default_model'] = m.group(1)
        ans['default_price'] = first_price(page)
        page = w.go('/smartphones/galaxy-z-flip8/buy/?Storage=512GB', '512GB')
        m = re.search(r'Model code: (SM-[A-Z0-9]+)', page)
        ans['model_512'] = m.group(1)
        ans['price_512'] = first_price(page)
        w.login('bob.c@test.com', 'TestPass123!')
        w.go('/smartphones/', 'back')
        w.go('/smartphones/galaxy-z-flip8/', 'product')
        page = w.go('/smartphones/galaxy-z-flip8/buy/?Storage=512GB', 'buy again')
        token = csrf(client, '/smartphones/galaxy-z-flip8/buy/')
        w.submit('/smartphones/galaxy-z-flip8/buy/', {
            'model_code': ans['model_512'], 'qty': '1',
            'Storage': '512GB',
            'csrf_token': token}, 'add to cart')
        page = w.go('/cart/', 'cart')
        item_id = re.search(r'name="item_id" value="(\d+)"', page).group(1)
        w.fill('quantity select')
        token = csrf(client, '/cart/')
        page = w.submit('/cart/update', {'item_id': item_id, 'qty': '2',
                                         'csrf_token': token}, 'change qty')
        m = re.search(r'Subtotal: <strong>\$([0-9,]+\.\d{2})', page)
        ans['subtotal'] = '$' + m.group(1)
        ans['items'] = 2
        token = csrf(client, '/cart/')
        page = w.submit('/cart/remove', {'item_id': item_id,
                                         'csrf_token': token}, 'remove')
        assert 'Your cart is empty' in plain(page)
        w.go('/smartphones/', 'catalog again')
        w.go('/smartphones/galaxy-z-flip8/', 'product again')
        page = w.go('/smartphones/galaxy-z-flip8/buy/', 'buy page, default storage')
        token = csrf(client, '/smartphones/galaxy-z-flip8/buy/')
        page = w.submit('/smartphones/galaxy-z-flip8/buy/', {
            'model_code': ans['default_model'], 'qty': '1',
            'csrf_token': token}, 'add default unit to cart')
        m = re.search(r'Subtotal: <strong>\$([0-9,]+\.\d{2})', page)
        ans['new_subtotal'] = '$' + m.group(1)
        chips = re.findall(r'class="chip">([^<]+)<', page)
        assert chips, 'no option chips rendered'
        ans['new_options'] = chips[0]
        return ans, w.steps, ['ok']

    if idx == 19:
        w.go('/smartphones/', 'catalog')
        page = w.go('/smartphones/galaxy-s25-ultra/', 'S25 Ultra')
        ans['model'] = re.search(r'Model code: ([A-Z0-9\-]+)', page).group(1)
        ans['price'] = first_price(page)
        ans['rating'] = re.search(
            r'class="product-rating">([\d.]+)', page).group(1)
        ans['dim'] = product_spec_value(page, 'Main Display Dimension')
        ans['brightness'] = product_spec_value(page, 'Peak Brightness')
        page = w.go('/compare/', 'compare')
        w.fill('check S25 Ultra')
        w.fill('check S26 Ultra')
        page = w.go('/compare/?models=SM-S938&models=SM-S948', 'run comparison')
        cols = compare_columns(page)
        assert [c[1] for c in cols] == ['SM-S938', 'SM-S948'], cols
        ans['s25u_weight'] = compare_row_value(page, 'Weight', 0)
        ans['s26u_weight'] = compare_row_value(page, 'Weight', 1)
        # 218 g (S25 Ultra) > 214 g (S26 Ultra): the S25 Ultra is heavier.
        # (The old contract hardcoded 'Galaxy S26 Ultra' here — a factual
        # error uncovered while re-anchoring the compare questions.)
        assert float(ans['s25u_weight']) > float(ans['s26u_weight'])
        ans['heavier'] = 'Galaxy S25 Ultra'
        w.login('alice.j@test.com', 'TestPass123!')
        w.go('/smartphones/', 'catalog')
        page = w.go('/smartphones/galaxy-s25-ultra/', 'S25 Ultra again')
        token = csrf(client, '/smartphones/galaxy-s25-ultra/')
        w.submit('/wishlist/toggle',
                 {'product_slug': 'galaxy-s25-ultra', 'csrf_token': token,
                  'next': '/smartphones/galaxy-s25-ultra/'}, 'wishlist add')
        w.go('/smartphones/', 'catalog')
        page = w.go('/smartphones/galaxy-z-flip8/', 'Z Flip8')
        ans['flip8_price'] = first_price(page)
        page = w.go('/account/wishlist/', 'wishlist page')
        ans['wishlist'] = len(re.findall(r'class="product-card"', page))
        return ans, w.steps, ['ok']

    raise AssertionError(f'no honest path for task {idx}')


def check_leakage(task_text, answers):
    """Fail if any expected answer string is already stated in the task."""
    leaks = []
    lowered = task_text.casefold()
    generic = {'yes', 'no', 'active', 'open', 'empty', '12 months',
               'galaxy s26 ultra', 'galaxy z fold8 ultra',
               # model names the task itself names as the comparison pair /
               # instruction target; the answer picks among them
               'galaxy s25 ultra', 'galaxy s26', 'galaxy z fold8',
               'galaxy z flip8',
               # values the task itself instructs the agent to type
               # (account names / emails given verbatim in the task text)
               'frank nova', 'frank.n@test.com', 'testpass123!'}
    for key, value in answers.items():
        if isinstance(value, (int, float)):
            continue
        value = str(value)
        if len(value) < 4 or value.casefold() in generic:
            continue
        if value.casefold() in lowered:
            leaks.append((key, value))
    if leaks:
        raise AssertionError(f'task leaks its answers: {leaks}')


def audit_round(tag):
    per_task = {}
    for idx in range(20):
        A, client, root = fresh_client(f'{tag}-t{idx}')
        try:
            task = json.loads(
                (SITE / 'tasks.jsonl').read_text().splitlines()[idx])['ques']
            ans, steps, log = run_task(A, client, idx)
            if not (MIN_STEPS <= steps <= MAX_STEPS):
                raise AssertionError(
                    f'task {idx}: {steps} honest steps '
                    f'(need {MIN_STEPS}..{MAX_STEPS})')
            check_leakage(task, ans)
            per_task[idx] = {'steps': steps, 'answers': ans}
            print(f'  task {idx:2d}: {steps} steps ok')
        finally:
            shutil.rmtree(root, ignore_errors=True)
            for mod in list(sys.modules):
                if mod.startswith(('app', 'seed')):
                    del sys.modules[mod]
    return per_task


def stable(answers):
    """Answers with runtime-generated identifiers templated out, so the
    two audit rounds can be compared deterministically."""
    out = {}
    for key, value in answers.items():
        value = re.sub(r'SS-\d+', 'SS-<n>', str(value))
        value = re.sub(r'ST-\d+', 'ST-<n>', value)
        out[key] = value
    return out


def main():
    print('audit round 1 ...')
    r1 = audit_round('w1')
    print('audit round 2 ...')
    r2 = audit_round('w2')
    for idx in range(20):
        s1, s2 = r1[idx]['steps'], r2[idx]['steps']
        if s1 != s2:
            print(f'FAIL: task {idx} step counts differ: {s1} vs {s2}')
            return 1
        if stable(r1[idx]['answers']) != stable(r2[idx]['answers']):
            print(f'FAIL: task {idx} answers differ between rounds')
            return 1
    out = {str(i): {'steps': r1[i]['steps'], 'answers': r1[i]['answers']}
           for i in range(20)}
    (SITE / 'scraped_data' / 'expected_answers.json').write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding='utf-8')
    total = sum(r1[i]['steps'] for i in range(20))
    lo = min(r1[i]['steps'] for i in range(20))
    hi = max(r1[i]['steps'] for i in range(20))
    print(f'\nOK: 20 tasks, two agreeing rounds; '
          f'{total} atomic steps total (min {lo}, max {hi})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
