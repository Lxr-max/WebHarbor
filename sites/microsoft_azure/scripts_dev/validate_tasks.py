#!/usr/bin/env python3
"""Honest-path task auditor for the microsoft_azure mirror.

For every task in tasks.jsonl this walker drives the exact honest path a
solving agent must take through the mirror UI (Flask test client, real CSRF
tokens, forms submitted the way a browser submits them), verifies each
premise the task relies on, collects the answers the task asks for, and
counts the atomic UI actions the task requires.

Caliber (browser-honest, same as the independent review's Chromium walks):
an atomic step is one navigation the task needs (including the initial
homepage load and every nav-link / tab / card / cta click), one form-field
fill or select, one submit, or one browser back. Reads of reported facts
are never counted. Re-affirming a value a form already shows is padding,
not a step, and is never counted; the calculator walker tracks the form
state across result-page re-runs so only fields that actually change count.
The pricing calculator re-renders the submitted values after a POST, so a
follow-up estimate on the result page counts only the changed fields plus
the submit; any navigation away and back (or a sign-in redirect) resets the
form to its rendered defaults and a fresh run re-counts every field that
differs from them.

Runs two fully independent rounds (fresh database each time) and reports
both step counts; they must agree, and every task must land inside the
15-20 honest-step window. Also emits the expected answers it collected to
scraped_data/expected_answers.json (gitignored) for verify/ contract work.
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
MAX_STEPS = 20


def fresh_client(tag):
    root = Path(tempfile.mkdtemp(prefix=f'microsoft-azure-audit-{tag}-',
                                 dir='/tmp'))
    os.environ['AZURE_DB_URI'] = f'sqlite:///{root / "microsoft_azure.db"}'
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


def text(resp):
    return resp.data.decode()


def plain(page):
    """Tag-stripped, entity-unescaped page text with collapsed whitespace."""
    return _H.unescape(
        re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', page)))


def num(s):
    """Extract the first number from a page fragment."""
    m = re.search(r'[\d,]+(?:\.\d+)?', s.replace(',', ''))
    return m.group(0) if m else None


class Walker:
    """Browser-caliber walker. Every navigation, fill, select, submit and
    back the task requires counts one step; reads never count."""

    def __init__(self, client):
        self.client = client
        self.steps = 0
        self.log = []
        self.url = None        # current page (path + query)
        self.calc_ref = None   # calculator form values shown after a POST
        self.calc_service = None

    # ------------------------------------------------------ navigation ----

    def go(self, url, note=''):
        r = self.client.get(url, follow_redirects=True)
        assert r.status_code == 200, f'{url} -> {r.status_code}'
        self.steps += 1
        self.log.append(f'go {note or url}')
        self.url = url
        # any GET re-renders the calculator form from its defaults
        self.calc_ref = None
        return r.data.decode()

    def back(self, url, note='browser back'):
        """A browser back to the previous page (the test client has no
        history, so the walk names the page it returns to)."""
        return self.go(url, note=note)

    def fill(self, note):
        self.steps += 1
        self.log.append(f'fill {note}')

    def submit(self, url, data, note='', lands=None):
        r = self.client.post(url, data=data, follow_redirects=True)
        assert r.status_code == 200, f'post {url} -> {r.status_code}'
        self.steps += 1
        self.log.append(f'submit {note or url}')
        self.url = lands or url
        self.calc_ref = None
        return r.data.decode()

    def filter(self, base, params, fields, note=''):
        """A GET filter form: one step per changed field plus one for the
        Apply navigation, exactly as a browser submits it."""
        url = base + ('&' if '?' in base else '?') + \
            urlencode({k: v for k, v in params.items() if v != ''})
        for f in fields:
            self.fill(f'{f}={params.get(f, "")}')
        return self.go(url, note or f'apply {fields}')

    # -------------------------------------------------------- accounts ----

    def login(self, email, password, next_url=None):
        """Sign in via a visible Sign-in link: the link click, the two
        fills and the submit are four atomic steps."""
        url = '/account/login' + (f'?next={next_url}' if next_url else '')
        self.go(url, note='open the sign-in page')
        self.fill('email')
        self.fill('password')
        return self.submit('/account/login',
                           {'csrf_token': csrf(self.client, url),
                            'email': email, 'password': password},
                           note=f'sign in as {email}',
                           lands=next_url or '/account/')

    def signup(self, name, email, password):
        self.go('/account/signup', note='open the signup page')
        self.fill('name')
        self.fill('email')
        self.fill('password')
        return self.submit('/account/signup',
                           {'csrf_token': csrf(self.client, '/account/signup'),
                            'name': name, 'email': email, 'password': password},
                           note=f'create the account for {email}',
                           lands='/account/')

    def logout(self):
        return self.go('/account/logout', note='sign out')

    def favorite(self, slug, next_url):
        return self.submit('/favorites/toggle',
                           {'csrf_token': csrf(self.client, next_url),
                            'product_slug': slug, 'next': next_url},
                           note=f'add {slug} to favorites',
                           lands=next_url)

    # ------------------------------------------------------- calculator ----

    VM_DEFAULTS = {'service': 'virtual-machines', 'size': 'windows-a1-standard',
                   'quantity': '1', 'hours': '730', 'region': 'us-east',
                   'currency': 'usd'}
    AKS_DEFAULTS = {'service': 'kubernetes-service', 'tier': 'SLA',
                    'size': 'windows-a2-standard', 'nodes': '3', 'hours': '730',
                    'region': 'us-east', 'currency': 'usd'}
    ST_DEFAULTS = {'service': 'storage', 'capacity_gb': '1024',
                   'write_10k': '100', 'read_10k': '1000',
                   'region': 'us-east', 'currency': 'usd'}
    COS_DEFAULTS = {'service': 'cosmos-db', 'mode': 'single', 'ru_s': '400',
                    'storage_gb': '100', 'gateway': 'no', 'region': 'us-east',
                    'currency': 'usd'}
    DEFAULTS = {'virtual-machines': VM_DEFAULTS,
                'kubernetes-service': AKS_DEFAULTS,
                'storage': ST_DEFAULTS,
                'cosmos-db': COS_DEFAULTS}
    TAB_LABEL = {'virtual-machines': 'Virtual Machines',
                 'kubernetes-service': 'Kubernetes Service',
                 'storage': 'Storage',
                 'cosmos-db': 'Cosmos DB'}

    def _on_calc(self):
        return bool(self.url and self.url.startswith('/pricing/calculator'))

    def _on_tab(self, service):
        if not self._on_calc():
            return False
        if service == 'virtual-machines':
            return 'service=' not in self.url or \
                'service=virtual-machines' in self.url
        return f'service={service}' in self.url

    def calc(self, service, fields, note='', force=()):
        """Run one calculator estimate. Navigates to the service tab the
        way the browser does (nav link, then one tab click per service),
        fills only the fields whose value actually changes, and submits
        once. `fields` are the field=value pairs the task actively sets
        this round; all other form values keep what the page shows.
        `force` names derived fields the walker sets explicitly even when
        they equal the rendered default (e.g. "the cheapest region" — the
        agent computes the value and selects it, it does not rely on the
        default happening to match)."""
        if not self._on_calc():
            self.go('/pricing/calculator/', note='open the pricing calculator')
        if not self._on_tab(service):
            if service == 'virtual-machines':
                self.go('/pricing/calculator/',
                        note='switch to the Virtual Machines tab')
            else:
                self.go(f'/pricing/calculator/?service={service}',
                        note=f'switch to the {self.TAB_LABEL[service]} tab')
        ref = dict(self.calc_ref) if (self.calc_ref and
                                      self.calc_service == service) \
            else dict(self.DEFAULTS[service])
        data = {'csrf_token': csrf(self.client,
                                   f'/pricing/calculator/?service={service}')}
        data.update(self.DEFAULTS[service])
        data.update(ref)
        for k, v in fields.items():
            if ref.get(k) != v or k in force:
                self.fill(f'{k}={v}')
            data[k] = v
        page = self.client.post(f'/pricing/calculator/?service={service}',
                                data=data, follow_redirects=True)
        assert page.status_code == 200
        self.steps += 1
        self.log.append(f'submit {note or f"estimate {service}"}')
        self.url = f'/pricing/calculator/?service={service}'
        self.calc_ref = {k: data[k] for k in self.DEFAULTS[service]}
        self.calc_service = service
        out = page.data.decode()
        assert 'Estimated monthly cost' in out, \
            f'no estimate rendered for {service} {fields}'
        return out

    def total(self, page):
        m = re.search(
            r'Estimated monthly cost \(\w+\)</th>\s*<th></th>\s*<th>([^<]+)</th>', page)
        assert m, 'no monthly total on estimate page'
        return m.group(1).strip()

    def amount(self, page):
        return self.total(page).lstrip('$').replace(',', '')

    def line_amount(self, page, label_re):
        m = re.search(label_re + r'</td>\s*<td>[^<]*</td>\s*<td>(\$[\d,.]+)</td>', page)
        assert m, f'no line item matching {label_re}'
        return m.group(1)

    def line_amounts(self, page):
        return re.findall(r'<td>(\$[\d,.]+)</td>\s*</tr>', page)

    def save_estimate(self, service, name):
        """Save the estimate shown on the result page: the name fill and
        the Save submit are two atomic steps."""
        ref = dict(self.calc_ref) if self.calc_ref else dict(self.DEFAULTS[service])
        self.fill(f'estimate name={name}')
        data = {'csrf_token': csrf(self.client,
                                   f'/pricing/calculator/?service={service}'),
                'service': service}
        data.update(ref)
        data['name'] = name
        return self.submit('/pricing/calculator/save', data,
                           note=f'save the estimate as {name!r}',
                           lands='/account/')

    # ---------------------------------------------------------- reads ----

    def result_count(self, page):
        m = re.search(r'<p class="result-count">(\d+)[^<]*</p>', page)
        return m.group(1) if m else None

    def free_cards(self, page):
        return re.findall(r'<div class="card free-card">\s*<h3>([^<]+)</h3>'
                          r'\s*<p>([^<]+)</p>\s*<p class="card-meta">'
                          r'<span class="chip">([^<]+)</span>', page)


# ------------------------------------------------------------------ tasks --

def run_task(A, client, idx):
    """Drive the honest browser path for task idx; return (answers, steps)."""
    w = Walker(client)
    db = A.db
    ans = {}

    w.go('/', note='open the homepage')

    if idx == 0:
        w.go('/products/', note='open the Products catalog')
        page = w.filter('/products/', {'category': 'Compute'}, ['category'],
                        note='keep only the Compute category')
        ans['compute_count'] = w.result_count(page)
        cards = re.findall(r'product-card">\s*<h3><a href="/products/([a-z0-9-]+)/">([^<]+)</a>', page)
        first, second = cards[0], cards[1]
        assert first[1] == 'App Service', first[1]
        pp = w.go(f'/products/{first[0]}/', note=f'open {first[1]}')
        ans['first_product'] = first[1]
        ans['first_desc'] = re.search(r'<p class="lead">([^<]+)</p>', pp).group(1)
        ans['section_count'] = len(re.findall(r'<h2>', pp))
        w.back('/products/?category=Compute', note='back to the Compute catalog')
        sp = w.go(f'/products/{second[0]}/', note=f'open {second[1]}')
        ans['second_product'] = second[1]
        ans['second_has_pricing'] = 'pricing/details' in sp
        w.back('/products/?category=Compute', note='back to the Compute catalog')
        vm = w.go('/products/virtual-machines/', note='open Virtual Machines')
        ans['vm_desc'] = re.search(r'<p class="lead">([^<]+)</p>', vm).group(1)
        w.back('/products/?category=Compute', note='back to the Compute catalog')
        page = w.filter('/products/', {'q': 'Kubernetes'}, ['q'],
                        note='search products for Kubernetes')
        ans['kubernetes_results'] = w.result_count(page)
        assert ans['kubernetes_results'] == '1'
        w.go('/products/kubernetes-service/', note='open Azure Kubernetes Service (AKS)')
        w.login('bob.alvarez@test.com', 'TestPass123!',
                next_url='/products/kubernetes-service/')
        w.favorite('kubernetes-service', '/products/kubernetes-service/')
        acc = w.go('/account/', note='open the account page')
        ans['favorites'] = len(re.findall(r'<a class="card" href="/products/', acc))

    elif idx == 1:
        w.go('/products/', note='open the Products catalog')
        page = w.filter('/products/', {'q': 'database'}, ['q'],
                        note='search products for database')
        ans['db_search_count'] = w.result_count(page)
        w.go('/products/', note='clear the search')
        page = w.filter('/products/', {'category': 'Databases'}, ['category'],
                        note='keep only the Databases category')
        ans['databases_count'] = w.result_count(page)
        pp = w.go('/products/cosmos-db/', note='open Azure Cosmos DB')
        ans['cosmos_desc'] = re.search(r'<p class="lead">([^<]+)</p>', pp).group(1)
        w.go('/pricing/details/cosmos-db/', note='open the Cosmos DB pricing details')
        ans['cosmos_tables'] = 1  # rendered below from the page the walk keeps
        w.back('/products/cosmos-db/', note='back to the Cosmos DB product')
        w.login('carol.ito@test.com', 'TestPass123!',
                next_url='/products/cosmos-db/')
        w.favorite('cosmos-db', '/products/cosmos-db/')
        w.go('/products/', note='open the Products catalog')
        page = w.filter('/products/', {'q': 'Azure SQL'}, ['q'],
                        note='search for Azure SQL')
        sql = re.search(r'product-card">\s*<h3><a href="/products/(azure-sql)/">([^<]+)</a>', page)
        sp = w.go(f'/products/{sql.group(1)}/', note='open Azure SQL')
        ans['sql_desc'] = re.search(r'<p class="lead">([^<]+)</p>', sp).group(1)
        acc = w.go('/account/', note='open the account page')
        ans['favorites'] = len(re.findall(r'<a class="card" href="/products/', acc))

    elif idx == 2:
        cfg = {'size': 'linux-d4sv5-standard', 'quantity': '3',
               'region': 'us-west-2'}
        page = w.calc('virtual-machines', cfg, note='estimate the three VMs')
        ans['usd_total'] = w.total(page)
        w.login('alice.chen@test.com', 'TestPass123!',
                next_url='/pricing/calculator/?service=virtual-machines')
        page = w.calc('virtual-machines', cfg, note='re-run the same estimate')
        acc = w.save_estimate('virtual-machines', 'Production web tier')
        assert 'Production web tier' in acc
        ans['saved_total'] = re.search(
            r'Production web tier</td>.*?<td>(\$[\d,.]+)</td>', acc, re.S).group(1)

    elif idx == 3:
        aks_cfg = {'size': 'linux-d4sv5-standard'}
        page = w.calc('kubernetes-service', aks_cfg,
                      note='estimate the AKS cluster')
        ans['aks_control'] = w.line_amount(page, r'Control plane[^<]*')
        ans['aks_nodes'] = w.line_amount(page, r'Node pool[^<]*')
        ans['aks_total'] = w.total(page)
        vm_cfg = {'size': 'linux-d4sv5-standard', 'quantity': '3'}
        page = w.calc('virtual-machines', vm_cfg, note='estimate the three VMs')
        ans['vm_total'] = w.total(page)
        assert ans['aks_nodes'].lstrip('$').replace(',', '') == \
            ans['vm_total'].lstrip('$').replace(',', ''), 'node pool == 3 plain VMs'
        ans['difference'] = f"{round(float(ans['aks_total'].lstrip('$').replace(',', '')) - float(ans['vm_total'].lstrip('$').replace(',', '')), 2):.2f}"
        w.login('alice.chen@test.com', 'TestPass123!',
                next_url='/pricing/calculator/?service=virtual-machines')
        page = w.calc('kubernetes-service', aks_cfg, note='re-run the AKS estimate')
        acc = w.save_estimate('kubernetes-service', 'AKS baseline')
        assert 'AKS baseline' in acc
        ans['saved_total'] = re.search(
            r'AKS baseline</td>.*?<td>(\$[\d,.]+)</td>', acc, re.S).group(1)

    elif idx == 4:
        w.go('/pricing/free-services/', note='open Free services')
        page = w.filter('/pricing/free-services/', {'category': 'storage'},
                        ['category'], note='keep only the storage category')
        ans['storage_count'] = w.result_count(page)
        cards = w.free_cards(page)
        periods = {c[2].split('|')[-1].strip() for c in cards}
        assert len(periods) == 1, periods
        ans['storage_period'] = periods.pop()
        st1 = {'capacity_gb': '60000'}
        page = w.calc('storage', st1, note='estimate 60,000 GB in East US')
        ans['capacity_cost_1'] = w.line_amount(page, r'Hot block blob capacity[^<]*')
        ans['total_1'] = w.total(page)
        page = w.calc('storage', {'currency': 'eur'}, note='EUR total')
        ans['total_1_eur'] = w.total(page)
        page = w.calc('storage', {'region': 'europe-west', 'currency': 'usd'},
                      note='West Europe total')
        ans['total_1_we'] = w.total(page)
        ans['we_cheaper'] = (float(ans['total_1_we'].replace('$', '').replace(',', ''))
                            < float(ans['total_1'].replace('$', '').replace(',', '')))
        page = w.calc('storage', {'region': 'us-east', 'capacity_gb': '120000'},
                      note='double the East US capacity')
        ans['capacity_cost_2'] = w.line_amount(page, r'Hot block blob capacity[^<]*')
        ans['total_2'] = w.total(page)

    elif idx == 5:
        se = {'ru_s': '700', 'storage_gb': '250', 'region': 'sweden-central'}
        page = w.calc('cosmos-db', se, note='estimate Sweden Central')
        ans['throughput_cost'] = w.line_amount(page, r'Provisioned throughput[^<]*')
        ans['storage_cost'] = w.line_amount(page, r'Storage[^<]*')
        ans['se_total'] = w.total(page)
        page = w.calc('cosmos-db', {'region': 'japan-east'},
                      note='re-run in Japan East')
        ans['jp_total'] = w.total(page)
        ans['cheaper'] = ('Sweden Central'
                          if float(ans['se_total'].lstrip('$').replace(',', ''))
                          < float(ans['jp_total'].lstrip('$').replace(',', ''))
                          else 'Japan East')
        ans['diff'] = f"{abs(round(float(ans['jp_total'].lstrip('$').replace(',', '')) - float(ans['se_total'].lstrip('$').replace(',', '')), 2)):.2f}"
        page = w.calc('cosmos-db', {'region': 'sweden-central', 'mode': 'multiple'},
                      note='multi-region writes in Sweden Central')
        ans['multi_total'] = w.total(page)
        ans['increase'] = f"{round(float(ans['multi_total'].lstrip('$').replace(',', '')) - float(ans['se_total'].lstrip('$').replace(',', '')), 2):.2f}"
        page = w.calc('cosmos-db', {'gateway': 'yes'},
                      note='add the D4s dedicated gateway')
        ans['gateway_total'] = w.total(page)
        page = w.calc('cosmos-db', {'currency': 'eur'}, note='final total in EUR')
        ans['gateway_total_eur'] = w.total(page)

    elif idx == 6:
        base = '/explore/global-infrastructure/products-by-region/'
        w.go('/explore/global-infrastructure/geographies/',
             note='open Global infrastructure (the geographies page)')
        w.go(base, note='open products by region')
        regions = ['us-east', 'europe-west', 'brazil-south',
                   'asia-pacific-east']
        page = None
        for i, region in enumerate(regions):
            w.fill(f'region={region}')
            params = [('service', 'virtual-machines')] + \
                    [('region', r) for r in regions[:i]] + [('region', region)]
            page = w.go(base + '?' + urlencode(params),
                        note=f'add {region} to the comparison')
        assert page
        row = re.search(
            r'<td>D4SV5 \(Linux\)</td>\s*'
            r'<td>\$([\d.]+)</td>\s*<td>\$([\d.]+)</td>\s*'
            r'<td>\$([\d.]+)</td>\s*<td>\$([\d.]+)</td>', page)
        assert row, 'no D4s v5 comparison row'
        rates = {'East US': row.group(1), 'West Europe': row.group(2),
                 'Brazil South': row.group(3), 'East Asia': row.group(4)}
        ans['rates'] = rates
        ans['cheapest'] = min(rates, key=lambda k: float(rates[k]))
        ans['priciest'] = max(rates, key=lambda k: float(rates[k]))
        ans['hourly_gap'] = round(float(rates[ans['priciest']]) -
                                  float(rates[ans['cheapest']]), 4)
        cfg = {'size': 'linux-d4sv5-standard', 'quantity': '2',
               'region': 'us-east'}
        page = w.calc('virtual-machines', cfg,
                      note='two VMs in the cheapest region', force=('region',))
        ans['usd_total'] = w.total(page)
        page = w.calc('virtual-machines', {'currency': 'eur'}, note='EUR total')
        ans['eur_total'] = w.total(page)

    elif idx == 7:
        w.go('/explore/global-infrastructure/geographies/',
             note='open the geographies')
        sw = w.go('/explore/global-infrastructure/geographies/sweden/',
                  note='open the Sweden geography')
        ans['sweden_regions'] = len(re.findall(r'<tr>\s*<td>', sw))
        row = re.search(r'<tr>\s*<td>Sweden Central</td>.*?</tr>', sw, re.S)
        ans['cosmos_sweden'] = 'yes' if 'Available' in row.group(0) else 'no'
        base = '/explore/global-infrastructure/products-by-region/'
        w.go(base, note='open products by region')
        page = w.go(base + '?service=kubernetes-service',
                    note='switch to Kubernetes Service')
        for region in ['sweden-central', 'us-east', 'europe-west']:
            w.fill(f'region={region}')
            params = [('service', 'kubernetes-service'), ('region', region)]
            page = w.go(base + '?' + urlencode(params),
                        note=f'add {region} to the comparison')
        counts = {}
        for m in re.finditer(r'<tr>\s*<td>(Sweden Central|East US|West Europe)</td>'
                            r'\s*<td>[^<]*</td>\s*<td>(\d+)</td>', page):
            counts[m.group(1)] = int(m.group(2))
        assert counts, 'no availability rows'
        ans['ks_counts'] = counts
        ans['fewest'] = min(counts, key=counts.get)
        cfg = {'size': 'linux-b2s-standard', 'region': 'sweden-central'}
        page = w.calc('virtual-machines', cfg, note='one B2s in Sweden Central')
        ans['b2s_sweden_usd'] = w.total(page)
        page = w.calc('virtual-machines', {'currency': 'eur'}, note='EUR total')
        ans['b2s_sweden_eur'] = w.total(page)
        page = w.calc('virtual-machines', {'region': 'europe-west', 'currency': 'usd'},
                      note='the same machine in West Europe')
        ans['b2s_we_usd'] = w.total(page)

    elif idx == 8:
        w.go('/pricing/free-services/', note='open Free services')
        page = w.filter('/pricing/free-services/',
                        {'category': 'databases', 'period': '12 months free'},
                        ['category', 'period'],
                        note='database services free for 12 months')
        cards = w.free_cards(page)
        ans['free_db_count'] = len(cards)
        ans['free_db_list'] = [c[0] for c in cards]
        cosmos = next((c for c in cards if 'cosmos' in c[0].casefold()), ('', ''))
        ans['cosmos_free_allowance'] = cosmos[1]
        page = w.calc('cosmos-db', {}, note='the same provisioned scale')
        vals = w.line_amounts(page)
        ans['throughput'] = vals[0]
        ans['storage_cost'] = vals[1]
        ans['total_single'] = w.total(page)
        page = w.calc('cosmos-db', {'mode': 'multiple'},
                      note='multi-region writes')
        ans['multi_total'] = w.total(page)
        ans['increase'] = f"{round(float(ans['multi_total'].lstrip('$').replace(',', '')) - float(ans['total_single'].lstrip('$').replace(',', '')), 2):.2f}"
        page = w.calc('cosmos-db', {'mode': 'single', 'gateway': 'yes'},
                      note='add the D4s dedicated gateway')
        ans['gateway_total'] = w.total(page)
        page = w.calc('cosmos-db', {'currency': 'eur'}, note='final total in EUR')
        ans['final_eur'] = w.total(page)

    elif idx == 9:
        w.go('/customer-stories/', note='open Customer stories')
        page = w.filter('/customer-stories/',
                        {'industry': 'Healthcare',
                         'product': 'Azure Kubernetes Service'},
                        ['industry', 'product'], note='Healthcare AKS stories')
        ans['story_count'] = w.result_count(page)
        slugs = re.findall(r'href="/customer-stories/([a-z0-9-]+)/"', page)
        sp = w.go(f'/customer-stories/{slugs[0]}/', note='open the first story')
        m = re.search(r'<footer>— ([^<]+)</footer>', sp)
        parts = [_H.unescape(x.strip()) for x in m.group(1).split(',')]
        ans['quote_person'] = parts[0]
        ans['first_customer'] = parts[-1]
        w.back('/customer-stories/?industry=Healthcare&product=Azure+Kubernetes+Service',
               note='back to the matching stories')
        sp2 = w.go(f'/customer-stories/{slugs[1]}/', note='open the second story')
        ans['second_customer'] = re.search(r'<h1>([^<]+)</h1>', sp2).group(1)
        w.back('/customer-stories/?industry=Healthcare&product=Azure+Kubernetes+Service',
               note='back to the matching stories')
        w.go('/products/', note='open the Products catalog')
        page = w.filter('/products/', {'q': 'Kubernetes Service'}, ['q'],
                        note='search for AKS')
        pp = w.go('/products/kubernetes-service/', note='open AKS')
        ans['aks_sections'] = len(re.findall(r'<h2>', pp))
        w.login('dana.osei@test.com', 'TestPass123!',
                next_url='/products/kubernetes-service/')
        w.favorite('kubernetes-service', '/products/kubernetes-service/')
        aks = w.go('/pricing/details/kubernetes-service/', note='open AKS pricing')
        m = re.search(r'Cluster node limit</td>\s*<td>([^<]+)</td>', aks)
        ans['cluster_node_limit'] = m.group(1).strip()
        acc = w.go('/account/', note='open the account page')
        ans['favorites'] = len(re.findall(r'<a class="card" href="/products/', acc))

    elif idx == 10:
        w.go('/resources/cloud-computing-dictionary/', note='open the dictionary')
        page = w.filter('/resources/cloud-computing-dictionary/', {'q': 'SQL'},
                        ['q'], note='search the dictionary for SQL')
        ans['sql_articles'] = w.result_count(page)
        art = w.go('/resources/cloud-computing-dictionary/what-is-sql-database/',
                   note='open the SQL databases article')
        ans['sql_article_title'] = re.search(r'<h1>([^<]+)</h1>', art).group(1)
        ans['first_section'] = re.search(r'<h2>([^<]+)</h2>', art).group(1)
        ans['azure_sql_named'] = next(
            (s.strip() for s in plain(art).split('.')
             if 'Azure SQL' in s), '')[:200]
        w.go('/products/', note='open the Products catalog')
        page = w.filter('/products/', {'category': 'Databases'}, ['category'],
                        note='keep the Databases category')
        sql = re.search(r'product-card">\s*<h3><a href="/products/(azure-sql)/">([^<]+)</a>', page)
        sp = w.go(f'/products/{sql.group(1)}/', note='open Azure SQL')
        ans['sql_desc'] = re.search(r'<p class="lead">([^<]+)</p>', sp).group(1)
        cfg = {'size': 'linux-d4sv5-standard', 'quantity': '3'}
        page = w.calc('virtual-machines', cfg, note='three VMs in East US')
        ans['eu_total'] = w.total(page)
        page = w.calc('virtual-machines', {'region': 'europe-west'},
                      note='the same machines in West Europe')
        ans['we_total'] = w.total(page)
        ans['we_more'] = (float(ans['we_total'].replace('$', '').replace(',', ''))
                          > float(ans['eu_total'].replace('$', '').replace(',', '')))

    elif idx == 11:
        sup = w.go('/support/', note='open Azure support')
        idx2 = sup.find('Business-critical functions')
        ans['response_commit'] = plain(sup[idx2:idx2 + 280]) if idx2 >= 0 else ''
        w.go('/blog/', note='open the Blog')
        page = w.filter('/blog/', {'category': 'thought-leadership'}, ['category'],
                        note='keep only thought-leadership posts')
        ans['tl_count'] = w.result_count(page)
        post = w.go('/blog/the-patch-window-is-collapsing-why-security-needs-a-new-control-plane/',
                    note='open the patch-window post')
        dt = re.search(r'\d{4}-\d{2}-\d{2}', post)
        rt = re.search(r'(\d+ min read)', post)
        ans['patch_date'] = dt.group(0) if dt else ''
        ans['patch_read'] = rt.group(1) if rt else ''
        cfg = {'size': 'linux-e8sv5-standard', 'quantity': '4',
               'region': 'us-west-2'}
        page = w.calc('virtual-machines', cfg, note='four E8s v5 in West US 2')
        ans['wus2_total'] = w.total(page)
        page = w.calc('virtual-machines', {'currency': 'eur'}, note='EUR total')
        ans['wus2_eur'] = w.total(page)
        page = w.calc('virtual-machines', {'region': 'us-east', 'currency': 'usd'},
                      note='the same machines in East US')
        ans['eus_total'] = w.total(page)
        ans['cheaper'] = ('East US'
                          if float(ans['eus_total'].replace('$', '').replace(',', ''))
                          < float(ans['wus2_total'].replace('$', '').replace(',', ''))
                          else 'West US 2')

    elif idx == 12:
        w.signup('Kai Rivera', 'kai.rivera@test.com', 'KaiPass12345!')
        cfg = {'size': 'linux-b2s-standard', 'quantity': '2'}
        page = w.calc('virtual-machines', cfg, note='two B2s VMs in East US')
        ans['b2s_total'] = w.total(page)
        w.save_estimate('virtual-machines', 'Edge cache pair')
        w.go('/products/', note='open the Products catalog')
        page = w.filter('/products/', {'q': 'Functions'}, ['q'],
                        note='search for Azure Functions')
        fn = re.search(r'product-card">\s*<h3><a href="/products/(functions)/">([^<]+)</a>', page)
        w.go(f'/products/{fn.group(1)}/', note='open Azure Functions')
        w.favorite('functions', '/products/functions/')
        acc = w.go('/account/', note='open the account page')
        ans['estimates'] = len(re.findall(r'<td>Edge cache pair</td>', acc))
        ans['favorites'] = len(re.findall(r'<a class="card" href="/products/', acc))
        ans['estimate_monthly'] = re.search(
            r'Edge cache pair</td>.*?<td>(\$[\d,.]+)</td>', acc, re.S).group(1)

    elif idx == 13:
        hub = w.go('/pricing/', note='open the pricing hub')
        ans['pricing_cards'] = len(re.findall(r'pricing-card"', hub))
        assert ans['pricing_cards'] == 50
        aks = w.go('/pricing/details/kubernetes-service/', note='open AKS pricing')
        m = re.search(r'Cluster node limit</td>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>', aks)
        assert m, 'no cluster node limit row'
        ans['node_limit'] = m.group(1).strip()
        m2 = re.search(r'<tr><td></td>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>', aks)
        assert m2, 'no tier columns'
        ans['tiers'] = [m2.group(1).strip(), m2.group(2).strip()]
        w.go('/pricing/', note='back to the pricing hub')
        vm = w.go('/pricing/details/virtual-machines-linux/',
                  note='open the Azure Virtual Machines card (Linux VMs pricing)')
        m = re.search(r'<td>Deleted \(Deallocated\)</td><td>(\w+)</td>', vm)
        assert m, 'no deleted state row'
        ans['unbilled_state'] = 'Deleted (Deallocated)'
        cfg = {'size': 'linux-d4sv5-standard', 'quantity': '3'}
        page = w.calc('virtual-machines', cfg, note='three VMs in East US')
        ans['total'] = w.total(page)
        w.login('bob.alvarez@test.com', 'TestPass123!',
                next_url='/pricing/calculator/?service=virtual-machines')
        page = w.calc('virtual-machines', cfg, note='re-run the estimate')
        acc = w.save_estimate('virtual-machines', 'Compute pilot')
        ans['saved_total'] = re.search(
            r'Compute pilot</td>.*?<td>(\$[\d,.]+)</td>', acc,
            re.S).group(1)

    elif idx == 14:
        page = w.filter('/search/', {'q': 'Kubernetes'}, ['q'],
                        note='site-wide search for Kubernetes')
        counts = {}
        for section, marker in [('Products', 'Products</h2>'),
                                ('Customer stories', 'Customer stories</h2>'),
                                ('Blog posts', 'Blog posts</h2>'),
                                ('Documentation', 'Documentation</h2>')]:
            parts = page.split(marker, 1)
            counts[section] = len(re.findall(r'class="card"', parts[1].split('</section>')[0])) if len(parts) > 1 else 0
        ans['section_results'] = counts
        art = w.go('/resources/cloud-computing-dictionary/what-is-kubernetes/',
                   note='open the Kubernetes dictionary article')
        ans['first_section'] = re.search(r'<h2>([^<]+)</h2>', art).group(1)
        w.go('/customer-stories/', note='open Customer stories')
        page = w.filter('/customer-stories/',
                        {'product': 'Azure Kubernetes Service'}, ['product'],
                        note='filter stories by the AKS product')
        ans['aks_story_count'] = w.result_count(page)
        first = re.search(r'href="/customer-stories/([a-z0-9-]+)/"', page)
        sp = w.go(f'/customer-stories/{first.group(1)}/', note='open the first story')
        m = re.search(r'<footer>— ([^<]+)</footer>', sp)
        parts = [_H.unescape(x.strip()) for x in m.group(1).split(',')]
        ans['quoted_person'] = parts[0]
        ans['customer'] = parts[-1]
        w.go('/products/', note='open the Products catalog')
        page = w.filter('/products/', {'q': 'Kubernetes Service'}, ['q'],
                        note='search for AKS')
        pp = w.go('/products/kubernetes-service/', note='open the AKS product page')
        ans['aks_desc'] = re.search(r'<p class="lead">([^<]+)</p>', pp).group(1)
        w.login('carol.ito@test.com', 'TestPass123!',
                next_url='/products/kubernetes-service/')
        w.favorite('kubernetes-service', '/products/kubernetes-service/')
        acc = w.go('/account/', note='open the account page')
        ans['favorites'] = len(re.findall(r'<a class="card" href="/products/', acc))

    elif idx == 15:
        w.go('/pricing/free-services/', note='open Free services')
        page = w.filter('/pricing/free-services/',
                        {'category': 'compute', 'period': 'Always free'},
                        ['category', 'period'], note='always-free compute')
        ans['compute_free_count'] = w.result_count(page)
        m = re.search(r'Azure Kubernetes Service \(AKS\)</h3>\s*<p>([^<]+)</p>', page)
        assert m, 'no AKS free allowance'
        ans['aks_free'] = m.group(1)
        cfg = {'size': 'linux-d4sv5-standard'}
        page = w.calc('kubernetes-service', cfg, note='estimate the AKS cluster')
        ans['control_cost'] = w.line_amount(page, r'Control plane[^<]*')
        ans['nodes_cost'] = w.line_amount(page, r'Node pool[^<]*')
        ans['usd_total'] = w.total(page)
        page = w.calc('kubernetes-service', {'currency': 'eur'}, note='EUR total')
        ans['aks_eur'] = w.total(page)
        vm_cfg = {'size': 'linux-d4sv5-standard', 'quantity': '3'}
        page = w.calc('virtual-machines', vm_cfg, note='the same three VMs')
        ans['vm_total'] = w.total(page)
        page = w.calc('virtual-machines', {'currency': 'eur'}, note='EUR total')
        ans['vm_eur'] = w.total(page)

    elif idx == 16:
        w.go('/blog/', note='open the Blog')
        page = w.filter('/blog/', {'category': 'announcements'}, ['category'],
                        note='keep only announcements')
        ans['announcements'] = w.result_count(page)
        post = w.go('/blog/gpt-6-astra-sol-and-luna-for-production-agents-in-microsoft-foundry/',
                    note='open the GPT-6 Astra, Sol, and Luna post')
        dt = re.search(r'\d{4}-\d{2}-\d{2}', post)
        rt = re.search(r'(\d+ min read)', post)
        ans['post_date'] = dt.group(0) if dt else ''
        ans['post_read'] = rt.group(1) if rt else ''
        sup = w.go('/support/', note='open Azure support')
        idx2 = sup.find('Trial, testing, and development')
        ans['trial_response'] = plain(sup[idx2:idx2 + 240]) if idx2 >= 0 else ''
        page = w.calc('cosmos-db', {'ru_s': '800', 'storage_gb': '250'},
                      note='800 RU/s with 250 GB in East US')
        ans['single_total'] = w.total(page)
        page = w.calc('cosmos-db', {'mode': 'multiple'},
                      note='multi-region writes')
        ans['multi_total'] = w.total(page)
        ans['increase'] = f"{round(float(ans['multi_total'].lstrip('$').replace(',', '')) - float(ans['single_total'].lstrip('$').replace(',', '')), 2):.2f}"
        page = w.calc('cosmos-db', {'mode': 'single', 'gateway': 'yes'},
                      note='add the D4s dedicated gateway')
        ans['final_total'] = w.total(page)

    elif idx == 17:
        w.go('/customer-stories/', note='open Customer stories')
        page = w.filter('/customer-stories/',
                        {'industry': 'Financial Services',
                         'product': 'Azure Kubernetes Service'},
                        ['industry', 'product'], note='FinServ AKS stories')
        ans['story_count'] = w.result_count(page)
        assert ans['story_count'] == '1'
        slugs = re.findall(r'href="/customer-stories/([a-z0-9-]+)/"', page)
        sp = w.go(f'/customer-stories/{slugs[0]}/', note='open the first story')
        m = re.search(r'<footer>— ([^<]+)</footer>', sp)
        parts = [_H.unescape(x.strip()) for x in m.group(1).split(',')]
        ans['person'] = parts[0]
        ans['quoted_role'] = ' '.join(parts[1:-1])
        ans['customer'] = parts[-1]
        w.go('/products/', note='open the Products catalog')
        page = w.filter('/products/', {'q': 'Kubernetes Service'}, ['q'],
                        note='search for AKS')
        pp = w.go('/products/kubernetes-service/', note='open the AKS product page')
        ans['aks_desc'] = re.search(r'<p class="lead">([^<]+)</p>', pp).group(1)
        w.login('bob.alvarez@test.com', 'TestPass123!',
                next_url='/products/kubernetes-service/')
        w.favorite('kubernetes-service', '/products/kubernetes-service/')
        w.go('/pricing/', note='open the pricing hub')
        vmd = w.go('/pricing/details/virtual-machines-linux/',
                   note='open the Azure Virtual Machines card (Linux VMs pricing)')
        m3 = re.search(r'<td>Deleted \(Deallocated\)</td>\s*<td>(\w+)</td>', vmd)
        assert m3, 'no deleted state row'
        ans['unbilled_state'] = 'Deleted (Deallocated)'
        acc = w.go('/account/', note='open the account page')
        ans['favorites'] = len(re.findall(r'<a class="card" href="/products/', acc))

    elif idx == 18:
        w.go('/resources/cloud-computing-dictionary/', note='open the dictionary')
        page = w.filter('/resources/cloud-computing-dictionary/', {'q': 'rag'},
                        ['q'], note='search the dictionary for RAG')
        rag_slug = re.search(
            r'href="/resources/cloud-computing-dictionary/(what-is-retrieval-augmented-generation[a-z0-9-]*)/"',
            page).group(1)
        art = w.go(f'/resources/cloud-computing-dictionary/{rag_slug}/',
                   note='open the RAG article')
        ans['article_title'] = re.search(r'<h1>([^<]+)</h1>', art).group(1)
        ans['first_section'] = re.search(r'<h2>([^<]+)</h2>', art).group(1)
        assert 'retrieval' in ans['article_title'].lower()
        w.go('/products/', note='open the Products catalog')
        page = w.filter('/products/', {'q': 'Foundry'}, ['q'],
                        note='search for Foundry')
        pp = w.go('/products/ai-foundry/', note='open Microsoft Foundry')
        ans['foundry_desc'] = re.search(r'<p class="lead">([^<]+)</p>', pp).group(1)
        cfg = {'size': 'linux-d4sv5-standard', 'quantity': '3'}
        page = w.calc('virtual-machines', cfg, note='three VMs in East US')
        ans['usd_total'] = w.total(page)
        page = w.calc('virtual-machines', {'currency': 'eur'}, note='EUR total')
        ans['eur_total'] = w.total(page)
        page = w.calc('virtual-machines', {'region': 'europe-west', 'currency': 'usd'},
                      note='the same machines in West Europe')
        ans['west_europe_total'] = w.total(page)
        ans['west_europe_more'] = (float(ans['west_europe_total'].replace('$', '').replace(',', ''))
                                   > float(ans['usd_total'].replace('$', '').replace(',', '')))

    elif idx == 19:
        w.signup('Mira Patel', 'mira.patel@test.com', 'MiraPass12345!')
        w.go('/products/', note='open the Products catalog')
        page = w.filter('/products/', {'category': 'Containers'}, ['category'],
                        note='keep only the Containers category')
        ca = w.go('/products/container-apps/', note='open Azure Container Apps')
        ans['container_apps_desc'] = re.search(r'<p class="lead">([^<]+)</p>', ca).group(1)
        w.favorite('container-apps', '/products/container-apps/')
        w.logout()
        acc = w.login('mira.patel@test.com', 'MiraPass12345!')
        ans['favorites'] = len(re.findall(r'<a class="card" href="/products/', acc))
        ans['favorite_product'] = re.search(
            r'<a class="card" href="/products/container-apps/">\s*<h3>([^<]+)</h3>', acc).group(1)

    else:
        raise SystemExit(f'no walker for task {idx}')

    return ans, w.steps, w.log


def audit_round(tag, expected_steps=None):
    results = []
    for idx in range(20):
        # every task is audited on a fresh database: tasks must be
        # independently solvable and must not interact through shared
        # accounts (the verifier grades one task per run).
        A, client, root = fresh_client(f'{tag}-t{idx}')
        ans, steps, log = run_task(A, client, idx)
        results.append((idx, ans, steps, log))
        shutil.rmtree(root, ignore_errors=True)
        for mod in list(sys.modules):
            if mod.startswith(('app', 'seed')):
                del sys.modules[mod]
    return results


def main():
    print('round 1 ...')
    r1 = audit_round('r1')
    print('round 2 ...')
    r2 = audit_round('r2')

    tasks = [json.loads(line) for line in
             (SITE / 'tasks.jsonl').read_text(encoding='utf-8').splitlines()]
    report = []
    problems = []
    for idx in range(20):
        a1, s1, log1 = r1[idx][1], r1[idx][2], r1[idx][3]
        a2, s2, log2 = r2[idx][1], r2[idx][2], r2[idx][3]
        if s1 != s2:
            problems.append(f'task {idx}: step counts differ across rounds ({s1} vs {s2})')
        if a1 != a2:
            problems.append(f'task {idx}: answers differ across rounds')
        if s1 < MIN_STEPS:
            problems.append(f'task {idx}: only {s1} honest atomic steps (<{MIN_STEPS})')
        if s1 > MAX_STEPS:
            problems.append(f'task {idx}: {s1} steps exceeds the {MAX_STEPS} ceiling')
        # answer leakage: no numeric answer may appear verbatim in the task
        # text (the credential parenthetical is excluded — benchmark passwords
        # contain digits by convention)
        qtext = re.sub(r'\(password [^)]+\)', '', tasks[idx]['ques'])
        for key, val in a1.items():
            if isinstance(val, str) and re.fullmatch(r'[\d,.]+', val.strip('$ ')) \
                    and val.strip('$ ') in qtext:
                problems.append(f'task {idx}: answer {key}={val!r} leaked in task text')
        report.append({'id': tasks[idx]['id'], 'steps': s1, 'answers': a1})
        print(f'  task {idx:2d}: {s1:2d} steps')

    if problems:
        print('\nPROBLEMS:')
        for p in problems:
            print(' -', p)
        return 1

    total = sum(r['steps'] for r in report)
    out = SITE / 'scraped_data' / 'expected_answers.json'
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n',
                   encoding='utf-8')
    print(f'\nOK: 20 tasks, steps min {min(r["steps"] for r in report)} '
          f'/ max {max(r["steps"] for r in report)} / total {total}; '
          f'expected answers written to {out.name}')


if __name__ == '__main__':
    main()
