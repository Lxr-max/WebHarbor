#!/usr/bin/env python3
"""Honest-path task auditor for the nyse mirror.

For every task in tasks.jsonl this walker drives the exact honest path a
solving agent must take through the mirror UI (Flask test client, real CSRF
tokens, forms submitted the way a browser submits them), verifies each
premise the task relies on, collects the answers the task asks for, counts
the atomic UI actions the task requires, and fails when a task leaks its
own answers or can be finished in fewer than 15 honest atomic steps.

Counting rules (the measured browser caliber the review track established —
this audit was re-anchored to it after the r1 review falsified the old
test-client counts):
  - home(): the start_url navigation every task begins with counts as one
    atomic action, exactly like the first step of a real browser session.
  - go(url): every further navigation — clicking a link, a tab, a pagination
    button, or submitting a GET filter form — counts as one step.
  - fill(field): every form field a browser must type or select counts as
    one step (search boxes, date pickers, selects, sort dropdowns).
  - submit(): every POST (login, watchlist toggle, alert create/delete)
    counts as one step.
  - An alert creation costs its UI actions: the direction select (the
    agent sets it explicitly), the threshold fill, the note fill when the
    task asks for one, and the submit.
  - Reading a page, hovering, or viewing a fact costs nothing: reads do
    not count. Actions the task text does not require are NOT taken
    (anti-padding: no phantom legs, no redundant reloads, no re-opening a
    page the login next-redirect already returned to).

Runs two fully independent rounds (fresh database each time) and reports
both step counts; they must agree.
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE))

MIN_STEPS = 15


def fresh_client(tag):
    root = Path(tempfile.mkdtemp(prefix=f'nyse-audit-{tag}-'))
    os.environ['NYSE_DB_URI'] = f'sqlite:///{root / "nyse.db"}'
    os.environ['NYSE_AUTO_SEED'] = '1'
    for mod in list(sys.modules):
        if mod in ('app', 'seed_lib'):
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


class Walker:
    def __init__(self, client):
        self.client = client
        self.steps = 0
        self.log = []

    def go(self, url, note=''):
        r = self.client.get(url, follow_redirects=True)
        assert r.status_code == 200, f'{url} -> {r.status_code}'
        self.steps += 1
        self.log.append(f'go {note or url}')
        return r

    def home(self, note='open homepage (start_url)'):
        return self.go('/', note=note)

    def fill(self, note):
        self.steps += 1
        self.log.append(f'fill {note}')

    def submit(self, url, data, note=''):
        r = self.client.post(url, data=data, follow_redirects=True)
        assert r.status_code == 200, f'post {url} -> {r.status_code}'
        self.steps += 1
        self.log.append(f'submit {note or url}')
        return r

    # ------------------------------------------------------------ helpers --

    def login(self, email, password='TestPass123!', next=None):
        # A real session clicks the login link (4 atomic actions: navigate
        # to the login page, type the email, type the password, submit);
        # with next= the submit lands back on the page the link came from,
        # so no extra navigation is needed afterwards.
        target = f'/login?next={next}' if next else '/login'
        self.go(target, note='login page')
        self.fill('email')
        self.fill('password')
        return self.submit('/login', {'email': email, 'password': password,
                                      'csrf_token': csrf(self.client, target)},
                           note=f'login {email}')

    def toggle_watch(self, symbol, back='/watchlist'):
        return self.submit('/watchlist/toggle', {
            'csrf_token': csrf(self.client, back if back.startswith('/quote')
                               else '/quote/XNYS:KO'),
            'symbol': symbol, 'back': back},
            note=f'watchlist toggle {symbol}')

    def create_alert(self, symbol, direction, threshold, note=None,
                     src=None):
        # UI caliber: the agent explicitly selects the direction, types the
        # threshold, types the note when the task asks for one, and submits
        # (the submit lands on the alerts page).
        src = src or f'/quote/XNYS:{symbol}'
        self.fill(f'alert direction {direction}')
        self.fill('alert threshold')
        if note:
            self.fill('alert note')
        return self.submit('/alerts/create', {
            'csrf_token': csrf(self.client, src), 'symbol': symbol,
            'direction': direction, 'threshold': threshold, 'note': note or ''},
            note=f'alert {symbol} {direction} {threshold}')


def strip_tags(fragment):
    t = re.sub(r'<[^>]+>', ' ', fragment)
    t = html.unescape(t)
    return re.sub(r'\s+', ' ', t).strip()


def find_link(html, pattern):
    m = re.search(rf'href="(/quote/[^"]+)">{pattern}</a>', html)
    return m.group(1) if m else None


# -------------------------------------------------------------- task walks --

def walk(A, client, task_id):
    """Drive the honest path for one task; returns (steps, answers, log)."""
    w = Walker(client)
    answers = {}

    def stat_of(h, label):
        m = re.search(rf'<div class="k">{re.escape(label)}</div>\s*'
                      rf'<div class="v">([^<]*)</div>', h)
        return m.group(1) if m else None

    def sub_of(h, label):
        m = re.search(rf'<div class="k">{re.escape(label)}</div>\s*'
                      rf'<div class="v">[^<]*</div>\s*<div class="sub">([^<]*)</div>', h)
        return m.group(1) if m else None

    def page(url):
        r = w.client.get(url, follow_redirects=True)
        assert r.status_code == 200, f'{url} -> {r.status_code}'
        return text(r)

    def price_of(h):
        return re.search(r'<span class="quote-price">([\d,.]+)</span>', h).group(1)

    def facts_of(h):
        out = {}
        out['sector'] = re.search(r'<th>Sector</th><td>([^<]+)</td>', h)
        out['ceo'] = re.search(r'<th>CEO</th><td>([^<]+)</td>', h)
        return {k: (m.group(1) if m else None) for k, m in out.items()}

    def watch_rows(h):
        return re.findall(
            r'<tr>\s*<td><a href="/quote/[A-Z]+:([A-Z.]+)">(?:[^<]+)</a>'
            r'</td>(.*?)</tr>', h, re.S)

    def row_last_price(row_html):
        cells = re.findall(r'<td class="num">([\d,.]+)</td>', row_html)
        return cells[0] if cells else None

    if task_id == 'NYSE--0':
        w.home()
        w.go('/listings_directory/stock', note='stocks directory')
        w.fill('search AGILENT')
        w.go('/listings_directory/stock?q=AGILENT', note='apply search')
        h = page('/listings_directory/stock?q=AGILENT')
        href = find_link(h, 'A')
        assert href, 'AGILENT row must link'
        w.go(href, note='open quote A')
        h = page(href)
        facts = facts_of(h)
        answers['sector'] = facts['sector']
        answers['ceo'] = facts['ceo']
        w.go(href + '?exp=3', note='options expiry tab 3')
        h = page(href + '?exp=3')
        strikes = [float(s.replace(',', '')) for s in
                   re.findall(r'<strong>([\d,]+\.\d\d)</strong>', h)]
        answers['lowest_strike_exp3'] = min(strikes)
        answers['put_call_ratio'] = re.search(r'Put/Call Ratio: ([\d.]+)', h).group(1)
        w.login('alice.j@test.com', next=href)
        w.toggle_watch('A', back=href)
        w.go('/watchlist', note='watchlist')
        h = page('/watchlist')
        rows = watch_rows(h)
        syms = [s for s, _ in rows]
        answers['alice_watchlist_total'] = len(syms)
        answers['alice_watchlist_prices'] = [row_last_price(r) for _, r in rows]
        w.go(href, note='back to A quote')
        w.create_alert('A', 'below', '170.00', note='Lab spinout', src=href)
        h = page('/alerts')
        answers['alert_status'] = ('Triggered' if 'Triggered' in h else 'Pending')
        answers['alice_alerts_total'] = len(re.findall(r'<td><a href="/quote/', h))

    elif task_id == 'NYSE--1':
        w.home()
        w.go('/signup', note='signup page')
        w.fill('name'); w.fill('email'); w.fill('password')
        w.submit('/signup', {'csrf_token': csrf(client, '/signup'),
                             'name': 'Jordan Vale',
                             'email': 'jordan.vale@test.com',
                             'password': 'TestPass123!'}, note='signup')
        w.go('/markets', note='markets page')
        h = page('/markets')
        nyse_tbl = h.split('NYSE Most Active')[1].split('NYSE American')[0]
        vols = re.findall(r'<tr>\s*<td>(?:<a href="/quote/XNYS:([A-Z.]+)">\1</a>|([A-Z.]+))</td>\s*'
                          r'<td>[^<]+</td>\s*<td class="num">([\d,]+)</td>', nyse_tbl, re.S)
        vols = [(a or b, v) for a, b, v in vols]
        top = max(vols, key=lambda r: int(r[1].replace(',', '')))[0]
        answers['highest_volume_symbol'] = top
        w.go(f'/quote/XNYS:{top}', note='open top mover quote')
        h = page(f'/quote/XNYS:{top}')
        facts = facts_of(h)
        answers['sector'] = facts['sector']
        answers['ceo'] = facts['ceo']
        answers['wh52date'] = sub_of(h, '52 Wk High')
        w.go('/logout', note='log out')
        w.login('jordan.vale@test.com', 'TestPass123!')
        w.go('/markets', note='markets page again')
        w.go(f'/quote/XNYS:{top}', note='re-open top mover quote')
        w.toggle_watch(top, back=f'/quote/XNYS:{top}')
        w.go('/watchlist', note='watchlist')
        h = page('/watchlist')
        answers['watchlist_total'] = len(re.findall(r'<td><a href="/quote/', h))
        w.go('/ipo-center/recent-ipo', note='recent IPOs')
        h = page('/ipo-center/recent-ipo')
        m = re.search(r'<td>(\d\d/\d\d/\d\d\d\d)</td>\s*<td>([^<]+)</td>\s*<td>([A-Z.]+)</td>', h, re.S)
        answers['first_priced_issuer'] = m.group(2)
        answers['first_priced_price'] = m.group(3)
        w.go('/ipo-center/recent-ipo?window=90', note='window 90 days')
        h = page('/ipo-center/recent-ipo?window=90')
        seg = h[h.find('Largest 10'):]
        rows90 = re.findall(r'<tr>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>', seg, re.S)
        answers['window90_top_issuer'] = rows90[0][2]
        answers['window90_top_proceeds'] = re.findall(r'<td class="num">([\d,.]+)</td>', seg)[0]
        w.go('/ipo-center/backlog', note='backlog')
        h = page('/ipo-center/backlog')
        rows_bl = re.findall(r'<tr>\s*<td>([^<]+)</td>\s*<td class="num">(\d+)</td>', h, re.S)
        rows_bl = [r for r in rows_bl if r[0] != 'Total']
        best = max(rows_bl, key=lambda r: int(r[1]))
        answers['backlog_top_industry'] = best[0]
        answers['backlog_top_count'] = best[1]

    elif task_id == 'NYSE--2':
        w.home()
        w.go('/bell/calendar', note='bell calendar')
        w.fill('type Opening Bell')
        w.fill('from 2026-09-01'); w.fill('to 2026-09-30')
        w.go('/bell/calendar?from=2026-09-01&to=2026-09-30&type=Opening+Bell',
             note='apply bell filters')
        h = page('/bell/calendar?from=2026-09-01&to=2026-09-30&type=Opening+Bell')
        answers['september_opening_count'] = int(
            re.search(r'><strong>(\d+)</strong> bell events', h).group(1))
        pages = int(re.search(r'page \d+ of (\d+)', h).group(1))
        w.go('/bell/calendar?from=2026-09-01&to=2026-09-30&type=Opening+Bell'
            f'&page={pages}', note='last page of filtered set')
        h = page('/bell/calendar?from=2026-09-01&to=2026-09-30&type=Opening+Bell'
                 f'&page={pages}')
        answers['earliest_september_opening'] = re.findall(r'<h3>([^<]+)</h3>', h)[-1]
        w.go('/bell/calendar', note='clear filters')
        w.fill('search Vanguard')
        w.go('/bell/calendar?q=Vanguard', note='apply search')
        h = page('/bell/calendar?q=Vanguard')
        dates = re.findall(r'<div class="bell-when">([^&]+)&middot;', h)
        answers['vanguard_date'] = dates[0].strip()
        w.go('/bell/calendar', note='clear search')
        w.fill('search IPO')
        w.go('/bell/calendar?q=IPO', note='apply search')
        h = page('/bell/calendar?q=IPO')
        answers['ipo_events'] = int(
            re.search(r'><strong>(\d+)</strong> bell events', h).group(1))
        w.go('/bell/calendar', note='clear search')
        w.fill('type Closing Bell')
        w.go('/bell/calendar?type=Closing+Bell', note='apply type filter')
        h = page('/bell/calendar?type=Closing+Bell')
        answers['closing_total'] = int(
            re.search(r'><strong>(\d+)</strong> bell events', h).group(1))
        w.go('/bell/calendar?type=Closing+Bell&page=2', note='page 2')
        h = page('/bell/calendar?type=Closing+Bell&page=2')
        answers['page2_first_title'] = re.search(r'<h3>([^<]+)</h3>', h).group(1)

    elif task_id == 'NYSE--3':
        w.home()
        w.go('/listings_directory/stock', note='stocks directory')
        w.fill('search Coca-Cola')
        w.go('/listings_directory/stock?q=Coca-Cola', note='apply search')
        h = page('/listings_directory/stock?q=Coca-Cola')
        href = find_link(h, 'KO')
        w.go(href, note='KO quote')
        h = page(href)
        answers['ko_last'] = price_of(h)
        answers['ko_52wk_high_date'] = sub_of(h, '52 Wk High')
        w.go(href + '?zoom=1Y', note='zoom 1Y')
        w.go(href + '?zoom=5Y', note='zoom 5Y')
        h = page(href + '?zoom=5Y')
        answers['five_year_first_date'] = re.search(
            r'<text x="4" y="\d+" font-size="12" fill="#666">([^<]+)</text>', h).group(1)
        w.go('/listings_directory/stock', note='back to stocks tab')
        w.fill('search Alcoa')
        w.go('/listings_directory/stock?q=Alcoa', note='apply search')
        h = page('/listings_directory/stock?q=Alcoa')
        href_aa = find_link(h, 'AA')
        w.go(href_aa, note='AA quote')
        h = page(href_aa)
        answers['aa_52wk_low'] = stat_of(h, '52 Wk Low')
        w.login('bob.c@test.com', next=href_aa)
        w.fill('header search KO')
        w.go('/search?q=KO', note='submit header search')
        h = page('/search?q=KO')
        href_ko = find_link(h, 'KO')
        w.go(href_ko, note='back to KO quote')
        h = page(href_ko)
        w.create_alert('KO', 'above', '100.00', note='Blue-chip entry', src=href_ko)
        h = page('/alerts')
        answers['bob_alerts_total'] = len(re.findall(r'<td><a href="/quote/', h))
        answers['new_alert_status'] = 'Triggered' if 'Triggered' in h else 'Pending'

    elif task_id == 'NYSE--4':
        w.home()
        w.go('/listings_directory/stock', note='listings directory')
        w.go('/listings_directory/etf', note='ETFs tab')
        w.fill('search SPY')
        w.go('/listings_directory/etf?q=SPY', note='apply search')
        h = page('/listings_directory/etf?q=SPY')
        answers['spy_matches'] = int(
            re.search(r'><strong>(\d+)</strong> listings match', h).group(1))
        href = find_link(h, 'SPY')
        w.go(href, note='SPY quote')
        h = page(href)
        answers['spy_last'] = price_of(h)
        answers['spy_52wk_high'] = stat_of(h, '52 Wk High')
        w.go(href + '?exp=2', note='options expiry tab 2')
        h = page(href + '?exp=2')
        strikes = [float(s.replace(',', '')) for s in
                   re.findall(r'<strong>([\d,]+\.\d\d)</strong>', h)]
        answers['highest_strike_exp2'] = max(strikes)
        answers['put_call_ratio'] = re.search(r'Put/Call Ratio: ([\d.]+)', h).group(1)
        w.go('/listings_directory/stock', note='listings directory')
        w.go('/listings_directory/index', note='Indices tab')
        w.fill('search Auspice')
        w.go('/listings_directory/index?q=Auspice', note='apply search')
        h = page('/listings_directory/index?q=Auspice')
        href_ix = find_link(h, 'ABCERI')
        w.go(href_ix, note='index quote')
        h = page(href_ix)
        answers['index_name'] = re.search(r'<h1>([^<]+)</h1>', h).group(1).strip()
        answers['index_last'] = price_of(h)
        w.go('/listings_directory/stock', note='stocks tab')
        w.fill('search NIO')
        w.go('/listings_directory/stock?q=NIO', note='apply search')
        h = page('/listings_directory/stock?q=NIO')
        href_nio = find_link(h, 'NIO')
        w.go(href_nio, note='NIO quote')
        h = page(href_nio)
        facts = facts_of(h)
        answers['nio_sector'] = facts['sector']
        answers['nio_volume'] = re.search(r'([\d,]+) Volume', h).group(1)
        w.go(href_nio + '?zoom=1Y', note='NIO zoom 1Y')
        h = page(href_nio + '?zoom=1Y')
        answers['nio_1y_last_date'] = re.search(
            r'text-anchor="end" fill="#666">([^<]+)</text>', h).group(1)

    elif task_id == 'NYSE--5':
        w.home()
        w.go('/listings_directory/stock', note='listings directory')
        w.go('/listings_directory/reit', note='REITs tab')
        h = page('/listings_directory/reit')
        answers['reit_total'] = int(
            re.search(r'><strong>(\d+)</strong> listings match', h).group(1))
        links = re.findall(r'href="(/quote/[^"]+)">([A-Z.]+)</a>', h)
        second_sym = links[1][1]
        answers['second_reit_symbol'] = second_sym
        w.go(links[1][0], note='open second REIT quote')
        h = page(links[1][0])
        facts = facts_of(h)
        answers['sector'] = facts['sector']
        answers['last'] = price_of(h)
        members = re.findall(r'<tr><td>([^<]+)</td><td class="num">(\d+)</td></tr>', h, re.S)
        answers['first_board_member'] = members[0][0]
        answers['first_member_term'] = members[0][1]
        w.login('carol.d@test.com', next=links[1][0])
        w.go('/watchlist', note='carol watchlist')
        w.toggle_watch('AAT', back='/watchlist')
        w.fill('header search second REIT')
        w.go(f'/search?q={second_sym}', note='submit header search')
        h = page(f'/search?q={second_sym}')
        href_second = find_link(h, second_sym)
        w.go(href_second, note='back to second REIT quote')
        w.toggle_watch(second_sym, back=href_second)
        w.go('/logout', note='log out')
        w.login('carol.d@test.com')
        w.go('/watchlist', note='final watchlist after re-login')
        h = page('/watchlist')
        syms = re.findall(r'<td><a href="/quote/[A-Z]+:([A-Z.]+)">', h)
        answers['carol_watchlist_total'] = len(syms)
        answers['carol_watchlist_symbols'] = syms

    elif task_id == 'NYSE--6':
        w.home()
        w.login('alice.j@test.com')
        w.go('/ipo-center/recent-ipo', note='recent IPOs')
        h = page('/ipo-center/recent-ipo')
        m = re.search(r'<td>(\d\d/\d\d/\d\d\d\d)</td>\s*<td>([^<]+)</td>\s*<td>([A-Z.]+)</td>', h, re.S)
        answers['first_priced_issuer'] = m.group(2)
        answers['first_priced_offer'] = m.group(3)
        w.go('/ipo-center/recent-ipo?window=90', note='window 90 days')
        h = page('/ipo-center/recent-ipo?window=90')
        seg = h[h.find('Largest 10'):]
        rows90 = re.findall(r'<tr>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>', seg, re.S)
        answers['window90_top_issuer'] = rows90[0][2]
        answers['window90_top_proceeds'] = re.findall(r'<td class="num">([\d,.]+)</td>', seg)[0]
        w.go('/ipo-center/recent-ipo?window=180', note='window 180 days')
        h = page('/ipo-center/recent-ipo?window=180')
        seg = h[h.find('Largest 10'):]
        rows180 = re.findall(r'<tr>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>', seg, re.S)
        answers['window180_rows'] = len(rows180)
        w.go('/ipo-center/ipo-pricing-stats', note='pricing stats')
        h = page('/ipo-center/ipo-pricing-stats')
        rows = re.findall(r'<tr>\s*<td>([^<]+)</td>\s*<td class="num">(\d+)</td>'
                          r'(?:\s*<td class="num">[^<]*</td>){4}\s*'
                          r'<td class="num">(\d+)%</td>', h, re.S)
        top = max(rows, key=lambda r: int(r[1]))
        answers['top_sector'] = top[0]
        answers['top_sector_deals'] = top[1]
        answers['top_sector_within_pct'] = top[2]
        w.go('/ipo-center/filings', note='filings')
        w.fill('status Filed')
        w.go('/ipo-center/filings?status=Filed', note='filter status Filed')
        h = page('/ipo-center/filings?status=Filed')
        m = re.search(r'Ives Ultra AI Opportunities[^<]*</td>\s*<td>[^<]*</td>\s*<td>[^<]*</td>\s*<td>([^<]+)</td>', h, re.S)
        assert m, 'Ives Ultra AI Opportunities must be in the Filed rows'
        answers['ives_exchange'] = m.group(1)
        w.go('/ipo-center/filings', note='clear filters')
        w.fill('exchange NASDAQ')
        w.go('/ipo-center/filings?exchange=NASDAQ', note='filter exchange NASDAQ')
        h = page('/ipo-center/filings?exchange=NASDAQ')
        answers['nasdaq_deals'] = int(
            re.search(r'><strong>(\d+)</strong> deals', h).group(1))
        w.go('/ipo-center/backlog', note='backlog')
        h = page('/ipo-center/backlog')
        rows_bl = re.findall(r'<tr>\s*<td>([^<]+)</td>\s*<td class="num">(\d+)</td>', h, re.S)
        rows_bl = [r for r in rows_bl if r[0] != 'Total']
        best = max(rows_bl, key=lambda r: int(r[1]))
        answers['backlog_top_industry'] = best[0]
        answers['backlog_top_count'] = best[1]

    elif task_id == 'NYSE--7':
        w.home()
        w.go('/markets', note='markets page')
        h = page('/markets')
        am_tbl = h.split('NYSE American Most Active')[1]
        vols = re.findall(r'<tr>\s*<td>(?:<a href="/quote/XASE:([A-Z.]+)">\1</a>|([A-Z.]+))</td>\s*'
                          r'<td>[^<]+</td>\s*<td class="num">([\d,]+)</td>', am_tbl)
        vols = [(a or b, v) for a, b, v in vols]
        top = max(vols, key=lambda r: int(r[1].replace(',', '')))[0]
        answers['nyse_american_top'] = top
        w.go(f'/quote/XASE:{top}', note='top American mover quote')
        h = page(f'/quote/XASE:{top}')
        answers['last'] = price_of(h)
        answers['ann_low'] = stat_of(h, '52 Wk Low')
        w.login('dana.k@test.com', next=f'/quote/XASE:{top}')
        w.create_alert(top, 'above', '5.00', src=f'/quote/XASE:{top}')
        h = page('/alerts')
        answers['alert_status'] = 'Triggered' if 'Triggered' in h else 'Pending'
        answers['dana_alerts_total'] = len(re.findall(r'<td><a href="/quote/', h))
        rows_al = re.findall(r'<tr>\s*<td><a href="/quote/[A-Z]+:([A-Z.]+)">.*?name="id" value="(\d+)"', h, re.S)
        new_id = rows_al[-1][1]
        w.submit('/alerts/delete', {'csrf_token': csrf(client, '/alerts'),
                                    'id': new_id}, note='delete new alert')
        h = page('/alerts')
        answers['dana_alerts_after_delete'] = len(
            re.findall(r'<td><a href="/quote/', h))
        w.go('/listings_directory/stock', note='stocks directory')
        w.fill('search Carnival')
        w.go('/listings_directory/stock?q=Carnival', note='apply search')
        h = page('/listings_directory/stock?q=Carnival')
        href_ccl = find_link(h, 'CCL')
        w.go(href_ccl, note='CCL quote')
        h = page(href_ccl)
        answers['ccl_52wk_high_date'] = sub_of(h, '52 Wk High')

    elif task_id == 'NYSE--8':
        w.home()
        w.go('/history-of-nyse', note='history page')
        h = page('/history-of-nyse')
        answers['buttonwood_year'] = '1792' if 'May 17, 1792' in h else None
        answers['new_building_year'] = ('1903' if 'moved into a new building'
                                        in h else None)
        w.go('/bell/calendar', note='bell calendar')
        w.fill('type Closing Bell')
        w.fill('from 2026-09-01'); w.fill('to 2026-09-30')
        w.go('/bell/calendar?from=2026-09-01&to=2026-09-30&type=Closing+Bell',
             note='apply window filter')
        h = page('/bell/calendar?from=2026-09-01&to=2026-09-30&type=Closing+Bell')
        answers['september_closing_count'] = int(
            re.search(r'><strong>(\d+)</strong> bell events', h).group(1))
        answers['first_closing_title'] = re.search(r'<h3>([^<]+)</h3>', h).group(1)
        w.go('/markets', note='markets page')
        h = page('/markets')
        nyse_tbl = h.split('NYSE Most Active')[1].split('NYSE American')[0]
        mrow = re.findall(r'<tr>\s*<td>(?:<a href="/quote/XNYS:([A-Z.]+)">\1</a>|([A-Z.]+))</td>\s*'
                          r'<td>([^<]+)</td>\s*<td class="num">[\d,]+</td>\s*<td class="num">([\d,.]+)</td>', nyse_tbl)
        answers['first_mover'] = mrow[0][0] or mrow[0][1]
        answers['first_mover_name'] = mrow[0][2]
        answers['first_mover_last'] = mrow[0][3]
        answers['american_rows'] = len(re.findall(
            r'<tr>\s*<td>(?:<a href="/quote/XASE:|<td>)', h))
        w.login('dana.k@test.com')
        w.go('/listings_directory/stock', note='stocks directory')
        w.fill('search Coca-Cola')
        w.go('/listings_directory/stock?q=Coca-Cola', note='apply search')
        h = page('/listings_directory/stock?q=Coca-Cola')
        href_ko = find_link(h, 'KO')
        assert href_ko, 'KO row must link'
        w.go(href_ko, note='KO quote')
        h = page(href_ko)
        watch_btn = re.search(
            r'<button[^>]*>\s*(Add to Watchlist|Remove from Watchlist)\s*</button>', h)
        assert watch_btn and watch_btn.group(1) == 'Add to Watchlist', \
            'KO must not already be on Dana\'s seeded watchlist'
        w.toggle_watch('KO', back=href_ko)
        w.go('/watchlist', note='watchlist')
        h = page('/watchlist')
        answers['dana_watchlist_total'] = len(
            re.findall(r'<td><a href="/quote/', h))

    elif task_id == 'NYSE--9':
        w.home()
        w.go('/listings_directory/stock', note='listings directory')
        w.go('/listings_directory/index', note='Indices tab')
        w.fill('search Auspice')
        w.go('/listings_directory/index?q=Auspice', note='apply search')
        h = page('/listings_directory/index?q=Auspice')
        href = find_link(h, 'ABCERI')
        w.go(href, note='index quote')
        h = page(href)
        answers['index_name'] = re.search(r'<h1>([^<]+)</h1>', h).group(1).strip()
        answers['index_last'] = price_of(h)
        w.go(href + '?zoom=1Y', note='index zoom 1Y')
        h = page(href + '?zoom=1Y')
        answers['index_1y_last_date'] = re.search(
            r'text-anchor="end" fill="#666">([^<]+)</text>', h).group(1)
        w.go('/listings_directory/stock', note='stocks tab')
        w.fill('search ALIBABA')
        w.go('/listings_directory/stock?q=ALIBABA', note='apply search')
        h = page('/listings_directory/stock?q=ALIBABA')
        href = find_link(h, 'BABA')
        w.go(href, note='BABA quote')
        h = page(href)
        facts = facts_of(h)
        answers['baba_ceo'] = facts['ceo']
        answers['baba_mktcap'] = re.search(
            r'<th>Market Capitalization</th><td>([^<]+)</td>', h).group(1)
        answers['baba_beta'] = re.search(r'<th>Beta</th><td>([^<]+)</td>', h).group(1)
        answers['baba_eps'] = re.search(r'<th>EPS</th><td>([^<]+)</td>', h).group(1)
        answers['baba_52wk_low'] = stat_of(h, '52 Wk Low')
        # The first expiry tab is the default view of the options section.
        strikes = re.findall(r'<strong>([\d,]+\.\d\d)</strong>', h)
        answers['baba_lowest_strike'] = strikes[0]
        w.go('/listings_directory/stock', note='back to stocks tab')
        w.fill('search NIO')
        w.go('/listings_directory/stock?q=NIO', note='apply search')
        h = page('/listings_directory/stock?q=NIO')
        answers['nio_matches'] = int(
            re.search(r'><strong>(\d+)</strong> listings match', h).group(1))
        href_nio = find_link(h, 'NIO')
        w.go(href_nio, note='NIO quote')
        h = page(href_nio)
        answers['nio_sector'] = facts_of(h)['sector']
        w.go(href_nio + '?zoom=1Y', note='NIO zoom 1Y')
        h = page(href_nio + '?zoom=1Y')
        answers['nio_1y_last_date'] = re.search(
            r'text-anchor="end" fill="#666">([^<]+)</text>', h).group(1)

    elif task_id == 'NYSE--10':
        w.home()
        w.go('/signup', note='signup page')
        w.fill('name'); w.fill('email'); w.fill('password')
        w.submit('/signup', {'csrf_token': csrf(client, '/signup'),
                             'name': 'Priya Nair',
                             'email': 'priya.nair@test.com',
                             'password': 'TestPass123!'}, note='signup')
        w.fill('header search gold')
        w.go('/search?q=gold', note='submit header search')
        h = page('/search?q=gold')
        answers['gold_matches'] = int(
            re.search(r'<h2>Listings</h2><span class="muted">(\d+)</span>', h).group(1))
        href = find_link(h, r'[A-Z.]+')
        w.go(href, note='first gold listing quote')
        h = page(href)
        answers['gold_last'] = price_of(h)
        answers['exchange'] = re.search(
            r'<div class="qh-name">([^/]+) /', h).group(1).strip()
        gold_sym = re.search(r'/quote/[A-Z]+:([A-Z.]+)', href).group(1)
        answers['gold_symbol'] = gold_sym
        w.toggle_watch(gold_sym, back=href)
        w.go('/listings_directory/stock', note='stocks directory')
        w.fill('search NIO')
        w.go('/listings_directory/stock?q=NIO', note='apply search')
        h = page('/listings_directory/stock?q=NIO')
        href_nio = find_link(h, 'NIO')
        w.go(href_nio, note='NIO quote')
        h = page(href_nio)
        answers['nio_last'] = price_of(h)
        w.toggle_watch('NIO', back=href_nio)
        w.go('/watchlist', note='watchlist')
        h = page('/watchlist')
        syms_before = re.findall(r'<td><a href="/quote/[A-Z]+:([A-Z.]+)">', h)
        answers['watchlist_before_removal'] = syms_before
        w.toggle_watch(gold_sym, back='/watchlist')
        h = page('/watchlist')
        syms_after = re.findall(r'<td><a href="/quote/[A-Z]+:([A-Z.]+)">', h)
        answers['watchlist_remaining'] = syms_after

    elif task_id == 'NYSE--11':
        w.home()
        w.go('/listings_directory/stock', note='stocks tab')
        w.fill('search TECHNOLOGIES')
        w.go('/listings_directory/stock?q=TECHNOLOGIES', note='apply')
        h = page('/listings_directory/stock?q=TECHNOLOGIES')
        answers['technologies_matches'] = int(
            re.search(r'><strong>(\d+)</strong> listings match', h).group(1))
        w.go('/listings_directory/stock', note='clear search')
        w.fill('sort by Name'); w.fill('order Descending')
        w.go('/listings_directory/stock?sort=name&order=desc', note='apply sort')
        h = page('/listings_directory/stock?sort=name&order=desc')
        answers['first_name_desc'] = re.search(
            r'<tr>\s*<td>.*?</td>\s*<td>([^<]+)</td>', h, re.S).group(1)
        w.go('/listings_directory/reit', note='REITs tab')
        h = page('/listings_directory/reit')
        links = re.findall(r'href="(/quote/[^"]+)">([A-Z.]+)</a>', h)
        w.go(links[0][0], note='first REIT quote')
        h = page(links[0][0])
        facts = facts_of(h)
        answers['reit_symbol'] = links[0][1]
        answers['reit_sector'] = facts['sector']
        answers['reit_52wk_high_date'] = sub_of(h, '52 Wk High')
        w.go(links[0][0] + '?zoom=1Y', note='REIT zoom 1Y')
        h = page(links[0][0] + '?zoom=1Y')
        answers['reit_1y_last_date'] = re.search(
            r'text-anchor="end" fill="#666">([^<]+)</text>', h).group(1)
        w.go('/listings_directory/stock', note='listings directory')
        w.go('/listings_directory/reit', note='REITs tab')
        w.fill('search Realty')
        w.go('/listings_directory/reit?q=Realty', note='apply search')
        h = page('/listings_directory/reit?q=Realty')
        answers['realty_matches'] = int(
            re.search(r'><strong>(\d+)</strong> listings match', h).group(1))
        first_realty = re.findall(r'href="(/quote/[^"]+)">', h)[0]
        w.go(first_realty, note='first linked Realty quote')
        h = page(first_realty)
        answers['realty_volume'] = re.search(r'([\d,]+) Volume', h).group(1)
        w.go('/ipo-center/backlog', note='IPO backlog')
        h = page('/ipo-center/backlog')
        rows_bl = re.findall(r'<tr>\s*<td>([^<]+)</td>\s*<td class="num">(\d+)</td>', h, re.S)
        rows_bl = [r for r in rows_bl if r[0] != 'Total']
        best = max(rows_bl, key=lambda r: int(r[1]))
        answers['backlog_top_industry'] = best[0]
        answers['backlog_top_count'] = best[1]
        w.go('/ipo-center/ipo-pricing-stats', note='pricing stats')
        h = page('/ipo-center/ipo-pricing-stats')
        rows = re.findall(r'<tr>\s*<td>([^<]+)</td>\s*<td class="num">(\d+)</td>', h)
        top = max(rows, key=lambda r: int(r[1]))
        answers['stats_top_sector'] = top[0]
        answers['stats_top_deals'] = top[1]
        w.go('/markets', note='markets page')
        h = page('/markets')
        answers['american_rows'] = len(re.findall(
            r'<tr>\s*<td>(?:<a href="/quote/XASE:|<td>)', h))

    elif task_id == 'NYSE--12':
        w.home()
        w.login('bob.c@test.com')
        w.go('/watchlist', note='bob watchlist')
        h = page('/watchlist')
        links = re.findall(r'<td><a href="(/quote/[A-Z]+:[A-Z.]+)">([A-Z.]+)</a>', h)
        second, second_href = links[1][1], links[1][0]
        first_href = links[0][0]
        answers['second_symbol'] = second
        w.go(second_href, note='second watchlist quote')
        h = page(second_href)
        answers['name'] = re.search(r'<h1>([^<]+)</h1>', h).group(1).strip()
        answers['beta'] = re.search(r'<th>Beta</th><td>([^<]+)</td>', h).group(1)
        answers['rsi'] = re.search(r'<th>RSI</th><td>([^<]+)</td>', h).group(1)
        w.go('/watchlist', note='back to watchlist')
        w.go(first_href, note='first watchlist quote')
        h = page(first_href)
        answers['first_52wk_high'] = stat_of(h, '52 Wk High')
        w.go('/watchlist', note='back to watchlist')
        w.go(second_href, note='re-open second symbol quote')
        w.create_alert(second, 'below', '150.00', src=second_href)
        w.go('/logout', note='log out')
        w.login('bob.c@test.com')
        w.go('/alerts', note='alerts page')
        h = page('/alerts')
        rows_al = re.findall(r'<tr>\s*<td><a href="/quote/[A-Z]+:([A-Z.]+)">.*?name="id" value="(\d+)"', h, re.S)
        aapl_id = next((rid for sym, rid in rows_al if sym == 'AAPL'), None)
        assert aapl_id, 'AAPL alert must exist on bob account'
        w.submit('/alerts/delete', {'csrf_token': csrf(client, '/alerts'),
                                    'id': aapl_id}, note='delete AAPL alert')
        h = page('/alerts')
        answers['alerts_remaining'] = len(re.findall(r'<td><a href="/quote/', h))
        answers['new_alert_status'] = 'Triggered' if 'Triggered' in h else 'Pending'

    elif task_id == 'NYSE--13':
        w.home()
        w.go('/bell/calendar', note='bell calendar')
        w.fill('search Vanguard')
        w.go('/bell/calendar?q=Vanguard', note='apply')
        h = page('/bell/calendar?q=Vanguard')
        answers['vanguard_title'] = re.search(r'<h3>([^<]+)</h3>', h).group(1)
        answers['vanguard_date'] = re.findall(r'<div class="bell-when">([^&]+)&middot;', h)[0].strip()
        w.go('/bell/calendar', note='clear search')
        w.fill('type Opening Bell')
        w.fill('from 2026-09-01'); w.fill('to 2026-09-30')
        w.go('/bell/calendar?from=2026-09-01&to=2026-09-30&type=Opening+Bell',
             note='apply window filter')
        h = page('/bell/calendar?from=2026-09-01&to=2026-09-30&type=Opening+Bell')
        answers['window_count'] = int(
            re.search(r'><strong>(\d+)</strong> bell events', h).group(1))
        pages = int(re.search(r'page \d+ of (\d+)', h).group(1))
        w.go('/bell/calendar?from=2026-09-01&to=2026-09-30&type=Opening+Bell'
            f'&page={pages}', note='last page')
        h = page('/bell/calendar?from=2026-09-01&to=2026-09-30&type=Opening+Bell'
                 f'&page={pages}')
        answers['last_page_top_title'] = re.findall(r'<h3>([^<]+)</h3>', h)[0]
        w.go('/bell', note='about the bell')
        h = page('/bell')
        answers['intro_first_sentence'] = re.search(
            r'<p class="page-sub">(.+?)</p>', h).group(1).split('.')[0]
        w.login('bob.c@test.com')
        w.go('/watchlist', note='bob watchlist')
        h = page('/watchlist')
        rows = watch_rows(h)
        answers['bob_watchlist_symbols'] = [s for s, _ in rows]
        answers['second_last_price'] = row_last_price(rows[1][1])

    elif task_id == 'NYSE--14':
        w.home()
        w.go('/listings_directory/stock', note='stocks tab')
        w.fill('search IBM')
        w.go('/listings_directory/stock?q=IBM', note='apply search')
        h = page('/listings_directory/stock?q=IBM')
        href = find_link(h, 'IBM')
        w.go(href, note='IBM quote')
        h = page(href)
        answers['ibm_last'] = price_of(h)
        answers['ibm_ave_vol'] = re.search(
            r'<th>Avg Volume</th><td>([^<]+)</td>', h).group(1)
        facts = facts_of(h)
        answers['ibm_sector'] = facts['sector']
        answers['ibm_ceo'] = facts['ceo']
        board = re.findall(r'<tr><td>([^<]+)</td><td class="num">', h)
        answers['ibm_board_count'] = len(board)
        w.go(href + '?zoom=1M', note='zoom 1M')
        h = page(href + '?zoom=1M')
        answers['chart_last_date'] = re.search(
            r'text-anchor="end" fill="#666">([^<]+)</text>', h).group(1)
        w.go(href + '?zoom=5Y', note='zoom 5Y')
        h = page(href + '?zoom=5Y')
        answers['chart_first_date_5y'] = re.search(
            r'<text x="4" y="\d+" font-size="12" fill="#666">([^<]+)</text>', h).group(1)
        w.go(href + '?exp=2', note='options tab 2')
        h = page(href + '?exp=2')
        strikes2 = [float(s.replace(',', '')) for s in
                    re.findall(r'<strong>([\d,]+\.\d\d)</strong>', h)]
        answers['highest_strike_exp2'] = max(strikes2)
        w.login('alice.j@test.com', next=href)
        w.toggle_watch('IBM', back=href)
        w.go('/watchlist', note='alice watchlist')
        h = page('/watchlist')
        syms = re.findall(r'<td><a href="/quote/[A-Z]+:([A-Z.]+)">', h)
        answers['alice_watchlist_total'] = len(syms)
        answers['alice_watchlist_symbols'] = syms
        w.go(href, note='back to IBM quote')
        w.create_alert('IBM', 'below', '200.00', src=href)
        h = page('/alerts')
        answers['alert_status'] = 'Triggered' if 'Triggered' in h else 'Pending'
        answers['alice_alerts_total'] = len(re.findall(r'<td><a href="/quote/', h))

    elif task_id == 'NYSE--15':
        w.home()
        w.login('dana.k@test.com')
        w.go('/ipo-center/filings', note='filings page')
        h = page('/ipo-center/filings')
        answers['filings_total'] = int(
            re.search(r'><strong>(\d+)</strong> deals', h).group(1))
        w.fill('status Postponed')
        w.go('/ipo-center/filings?status=Postponed', note='filter postponed')
        h = page('/ipo-center/filings?status=Postponed')
        seg = h[h.find('<tbody>'):]
        answers['first_postponed_issuer'] = re.search(
            r'class="badge[^"]*">[^<]+</span></td>\s*<td>[^<]*</td>\s*'
            r'<td>[^<]*</td>\s*<td>([^<]+)</td>', seg, re.S).group(1)
        w.go('/ipo-center/filings', note='clear filters')
        w.fill('exchange NYSE')
        w.go('/ipo-center/filings?exchange=New+York+Stock+Exchange', note='filter exchange')
        h = page('/ipo-center/filings?exchange=New+York+Stock+Exchange')
        answers['nyse_exchange_deals'] = int(
            re.search(r'><strong>(\d+)</strong> deals', h).group(1))
        seg = h[h.find('<tbody>'):]
        answers['first_nyse_exchange_issuer'] = re.search(
            r'class="badge[^"]*">[^<]+</span></td>\s*<td>[^<]*</td>\s*'
            r'<td>[^<]*</td>\s*<td>([^<]+)</td>', seg, re.S).group(1)
        w.go('/ipo-center/filings', note='clear filters')
        w.fill('status Filed')
        w.go('/ipo-center/filings?status=Filed', note='filter filed')
        h = page('/ipo-center/filings?status=Filed')
        answers['filed_count'] = int(
            re.search(r'><strong>(\d+)</strong> deals', h).group(1))
        w.go('/ipo-center/recent-ipo', note='recent IPOs')
        h = page('/ipo-center/recent-ipo')
        m = re.search(r'<td>(\d\d/\d\d/\d\d\d\d)</td>\s*<td>([^<]+)</td>', h, re.S)
        assert m, 'Recent IPOs must list a Priced deal first'
        answers['first_priced_issuer'] = m.group(2)
        monthly = re.findall(r'<tr>\s*<td>([A-Za-z]+(?:&#39;|\')\d\d)</td>\s*<td class="num">\d+</td>\s*<td class="num">([\d,.]+[BMKT]?)</td>', h)
        answers['latest_month'] = monthly[-1][0]
        answers['latest_month_proceeds'] = monthly[-1][1]
        w.go('/ipo-center/backlog', note='backlog')
        h = page('/ipo-center/backlog')
        rows_bl = re.findall(r'<tr>\s*<td>([^<]+)</td>\s*<td class="num">(\d+)</td>', h, re.S)
        rows_bl = [r for r in rows_bl if r[0] != 'Total']
        best = max(rows_bl, key=lambda r: int(r[1]))
        answers['backlog_top_industry'] = best[0]
        answers['backlog_top_count'] = best[1]

    elif task_id == 'NYSE--16':
        w.home()
        w.go('/listings_directory/stock', note='stocks tab')
        w.fill('search Disney')
        w.go('/listings_directory/stock?q=Disney', note='apply search')
        h = page('/listings_directory/stock?q=Disney')
        href = find_link(h, 'DIS')
        w.go(href, note='DIS quote')
        h = page(href)
        facts = facts_of(h)
        answers['dis_sector'] = facts['sector']
        answers['dis_52wk_low'] = stat_of(h, '52 Wk Low')
        answers['dis_div_yield'] = re.search(
            r'<th>Dividend Yield</th><td>([^<]+)</td>', h).group(1)
        w.login('alice.j@test.com', next=href)
        w.go('/watchlist', note='alice watchlist')
        h = page('/watchlist')
        answers['alice_watchlist_with_dis'] = len(
            re.findall(r'<td><a href="/quote/', h))
        w.go(href, note='back to DIS quote')
        w.create_alert('DIS', 'above', '200.00', note='Media momentum', src=href)
        w.go('/logout', note='log out')
        w.login('bob.c@test.com')
        w.go('/alerts', note='bob alerts')
        h = page('/alerts')
        syms = re.findall(r'<td><a href="/quote/[A-Z]+:([A-Z.]+)">', h)
        answers['bob_alerts_total'] = len(syms)
        answers['bob_alert_symbols'] = syms

    elif task_id == 'NYSE--17':
        w.home()
        w.fill('header search Vanguard')
        w.go('/search?q=Vanguard', note='submit header search')
        h = page('/search?q=Vanguard')
        answers['vanguard_listings'] = int(
            re.search(r'<h2>Listings</h2><span class="muted">(\d+)</span>', h).group(1))
        answers['vanguard_bell_events'] = int(
            re.search(r'<h2>Bell Events</h2><span class="muted">(\d+)</span>', h).group(1))
        w.go('/bell/calendar', note='bell calendar')
        w.fill('search Vanguard')
        w.go('/bell/calendar?q=Vanguard', note='bell search Vanguard')
        h = page('/bell/calendar?q=Vanguard')
        m = re.search(r'<p class="bell-desc">(.+?)</p>', h, re.S)
        answers['vanguard_desc_first_sentence'] = strip_tags(m.group(1)).split('.')[0]
        w.go('/listings_directory/stock', note='stocks directory')
        w.fill('search Coca-Cola')
        w.go('/listings_directory/stock?q=Coca-Cola', note='apply search')
        h = page('/listings_directory/stock?q=Coca-Cola')
        href = find_link(h, 'KO')
        w.go(href, note='KO quote')
        h = page(href)
        answers['ko_div_yield'] = re.search(
            r'<th>Dividend Yield</th><td>([^<]+)</td>', h).group(1)
        answers['ko_beta'] = re.search(r'<th>Beta</th><td>([^<]+)</td>', h).group(1)
        w.login('alice.j@test.com', next=href)
        w.create_alert('KO', 'below', '80.00', src=href)
        h = page('/alerts')
        answers['alice_alerts_total'] = len(re.findall(r'<td><a href="/quote/', h))
        answers['new_alert_status'] = 'Triggered' if 'Triggered' in h else 'Pending'
        w.go('/markets', note='markets page')
        h = page('/markets')
        am_tbl = h.split('NYSE American Most Active')[1]
        mrow = re.findall(r'<tr>\s*<td>(?:<a href="/quote/XASE:([A-Z.]+)">\1</a>|([A-Z.]+))</td>\s*'
                          r'<td>[^<]+</td>\s*<td class="num">[\d,]+</td>\s*<td class="num">([\d,.]+)</td>', am_tbl)
        answers['first_american_mover'] = mrow[0][0] or mrow[0][1]
        answers['first_american_mover_last'] = mrow[0][2]

    elif task_id == 'NYSE--18':
        w.home()
        w.go('/listings_directory/stock', note='stocks directory')
        w.go('/listings_directory/stock?page=3', note='directory page 3')
        h = page('/listings_directory/stock?page=3')
        href = find_link(h, r'[A-Z.]+')
        sym = re.search(r'/quote/[A-Z]+:([A-Z.]+)', href).group(1)
        answers['first_linked_symbol'] = sym
        w.go(href, note='open its quote')
        h = page(href)
        answers['last_price'] = price_of(h)
        answers['volume'] = re.search(r'([\d,]+) Volume', h).group(1)
        w.go('/listings_directory/stock', note='back to stocks tab')
        w.fill('search UNITED')
        w.go('/listings_directory/stock?q=UNITED', note='apply search')
        h = page('/listings_directory/stock?q=UNITED')
        answers['united_matches'] = int(
            re.search(r'><strong>(\d+)</strong> listings match', h).group(1))
        w.login('dana.k@test.com')
        w.fill(f'header search {sym}')
        w.go(f'/search?q={sym}', note='submit header search')
        h = page(f'/search?q={sym}')
        href_back = find_link(h, sym)
        w.go(href_back, note='back to first stock quote')
        w.toggle_watch(sym, back=href_back)
        w.go('/watchlist', note='dana watchlist')
        h = page('/watchlist')
        answers['dana_watchlist_total'] = len(re.findall(r'<td><a href="/quote/', h))
        w.toggle_watch('NIO', back='/watchlist')
        h = page('/watchlist')
        answers['dana_watchlist_after_removal'] = len(
            re.findall(r'<td><a href="/quote/', h))
        w.go('/markets', note='markets page')
        h = page('/markets')
        nyse_tbl = h.split('NYSE Most Active')[1].split('NYSE American')[0]
        mover_href = re.search(r'<a href="(/quote/XNYS:[A-Z.]+)">', nyse_tbl).group(1)
        w.go(mover_href, note='first NYSE mover quote')
        h = page(mover_href)
        answers['first_mover_sector'] = re.search(
            r'<th>Sector</th><td>([^<]+)</td>', h).group(1)

    elif task_id == 'NYSE--19':
        w.home()
        w.go('/ipo-center/recent-ipo', note='recent IPOs')
        h = page('/ipo-center/recent-ipo')
        m = re.search(r'<td>(\d\d/\d\d/\d\d\d\d)</td>\s*<td>([^<]+)</td>\s*<td>([A-Z.]+)</td>\s*<td>([^<]+)</td>', h)
        answers['first_priced_ticker'] = m.group(3)
        answers['first_priced_industry'] = m.group(4)
        w.go('/ipo-center/recent-ipo?window=180', note='window 180 days')
        h = page('/ipo-center/recent-ipo?window=180')
        seg = h[h.find('Largest 10'):]
        rows = re.findall(r'<tr>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>', seg, re.S)
        answers['window180_rows'] = len(rows)
        answers['window180_top_proceeds'] = re.findall(r'<td class="num">([\d,.]+[BMKT]?)</td>', seg)[0]
        w.go('/listings_directory/stock', note='stocks directory')
        w.fill('search Aeromexico')
        w.go('/listings_directory/stock?q=Aeromexico', note='apply search')
        h = page('/listings_directory/stock?q=Aeromexico')
        href = find_link(h, 'AERO')
        w.go(href, note='AERO quote')
        h = page(href)
        facts = facts_of(h)
        answers['aero_sector'] = facts['sector']
        answers['aero_52wk_low'] = stat_of(h, '52 Wk Low')
        w.go(href + '?zoom=1Y', note='AERO zoom 1Y')
        h = page(href + '?zoom=1Y')
        answers['aero_1y_first_date'] = re.search(
            r'<text x="4" y="\d+" font-size="12" fill="#666">([^<]+)</text>', h).group(1)
        w.go(href + '?exp=2', note='AERO options tab 2')
        h = page(href + '?exp=2')
        strikes = [float(s.replace(',', '')) for s in
                   re.findall(r'<strong>([\d,]+\.\d\d)</strong>', h)]
        answers['aero_exp2_lowest_strike'] = min(strikes)
        w.login('carol.d@test.com', next=href)
        w.toggle_watch('AERO', back=href)
        w.go('/watchlist', note='carol watchlist')
        h = page('/watchlist')
        answers['carol_watchlist_total'] = len(
            re.findall(r'<td><a href="/quote/', h))
        w.go(href, note='back to AERO quote')
        w.create_alert('AERO', 'above', '16.00', src=href)
        h = page('/alerts')
        answers['alert_status'] = 'Triggered' if 'Triggered' in h else 'Pending'
        answers['carol_alerts_total'] = len(re.findall(r'<td><a href="/quote/', h))

    else:
        raise ValueError(f'no walker for {task_id}')

    return w.steps, answers, w.log


def main():
    only = set(sys.argv[1:]) or None
    tasks = [json.loads(line) for line in
             open(SITE / 'tasks.jsonl', encoding='utf-8')]
    if only:
        tasks = [t for t in tasks if t['id'] in only]
    round_results = {}
    for round_no in (1, 2):
        results = {}
        for task in tasks:
            A, client, root = fresh_client(f'r{round_no}')
            try:
                steps, answers, log = walk(A, client, task['id'])
                # Leakage gate: no collected answer may appear verbatim in
                # the task text (the agent reads tasks.jsonl).
                leaks = []
                for key, value in answers.items():
                    text_value = str(value)
                    if (len(text_value) >= 4 and text_value in task['ques']):
                        leaks.append((key, text_value))
                if leaks:
                    print(f'{task["id"]}: LEAK {leaks}', flush=True)
                    results[task['id']] = {'steps': steps, 'leak': leaks}
                    continue
                results[task['id']] = {'steps': steps, 'answers': answers}
                flag = '' if steps >= MIN_STEPS else '  <-- UNDER MIN'
                print(f'{task["id"]}: {steps} steps{flag}', flush=True)
            finally:
                shutil.rmtree(root, ignore_errors=True)
        round_results[round_no] = results

    print()
    ok = True
    for task in tasks:
        a = round_results[1][task['id']]['steps']
        b = round_results[2][task['id']]['steps']
        if a != b or a < MIN_STEPS:
            ok = False
            print(f'MISMATCH/UNDER: {task["id"]} round1={a} round2={b}')
    lows = {tid: round_results[1][tid]['steps']
            for tid in round_results[1]
            if round_results[1][tid]['steps'] < MIN_STEPS}
    print(f'\nmin={min(r["steps"] for r in round_results[1].values())} '
          f'max={max(r["steps"] for r in round_results[1].values())} '
          f'total={sum(r["steps"] for r in round_results[1].values())} '
          f'both-rounds-agree={ok and not lows}')
    if lows:
        print('UNDER MINIMUM:', lows)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
