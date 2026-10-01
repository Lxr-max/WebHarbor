#!/usr/bin/env python3
"""Honest-path browser auditor for the yahoo_finance mirror.

For every task in tasks.jsonl this harness drives the exact honest path a
solving agent must take through the mirror UI with a REAL headless Chromium
(Playwright against a live werkzeug server on 127.0.0.1 — no Flask test
client, no direct DB reads for evidence): it performs each required atomic
action with real browser events (clicks, typing, form submits with rendered
CSRF tokens), verifies every premise the task relies on against the visible
page content (DOM locators + rendered text), collects the answers the task
asks for, and counts the atomic UI actions.

Counting rules (the measured browser caliber the review track established):
  - home(): the start_url navigation counts as one atomic action.
  - nav()/click on any link, tab or pagination control: one step.
  - fill(): every form field a browser must type or select: one step.
  - submit(): every form submission (search, login, watchlist toggle,
    alert create/delete, screener/calendar filters): one step.
  - Reading a page, hovering or confirming a visible default costs
    nothing: reads do not count.
  - Anti-padding (r1 review caliber): a control whose visible default
    already satisfies the task requirement is NOT re-operated and does
    NOT count (e.g. the alert direction dropdown defaults to "Above",
    so an "above N" alert needs no select after the free read confirms
    the default; a "below N" alert must select and counts one step).
  - Actions the task text does not require are NOT taken (no detour
    tab navigations, no redundant default-value selects).

Runs two fully independent rounds (fresh server + fresh database + fresh
browser per task per round) and reports both step counts; they must agree
and each task must require at least 15 honest atomic steps.

Usage (from sites/yahoo_finance):
    python3 scripts_dev/validate_tasks.py [--tasks 0,1] [--rounds 2]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.async_api import async_playwright

SITE = Path(__file__).resolve().parent.parent
SEED = SITE / 'instance_seed' / 'yahoo_finance.db'
# Allocated fix-round port block 46239/47239/48239 (ss -ltn verified free
# before first bind; the control-plane slot 47239 is used by the container
# walk harness, the site-secondary slot 48239 by smoke_verifier.py).
PORT = 46239
BASE = f'http://127.0.0.1:{PORT}'
MIN_STEPS = 15

PY = sys.executable


class Server:
    def __init__(self, db_path):
        self.db_path = db_path
        self.proc = None

    def start(self):
        env = dict(os.environ)
        env['YF_DB_URI'] = 'sqlite:///' + str(self.db_path)
        env['YF_AUTO_SEED'] = '0'
        env['PYTHONHASHSEED'] = '0'
        self.proc = subprocess.Popen(
            [PY, '-c',
             "import sys; sys.path.insert(0, %r)\n"
             "from app import app\n"
             "app.run(host='127.0.0.1', port=%d, threaded=True)" % (
                 str(SITE), PORT)],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            preexec_fn=os.setsid)
        for _ in range(120):
            try:
                with socket.create_connection(('127.0.0.1', PORT), timeout=0.4):
                    return
            except OSError:
                if self.proc.poll() is not None:
                    err = self.proc.stderr.read().decode()[-2000:]
                    raise RuntimeError('server died: ' + err)
                time.sleep(0.15)
        raise RuntimeError('server did not come up')

    def stop(self):
        if self.proc and self.proc.poll() is None:
            try:
                os.killpg(self.proc.pid, signal.SIGTERM)
                self.proc.wait(timeout=10)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(self.proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


class Walker:
    def __init__(self, page):
        self.page = page
        self.steps = 0
        self.log = []
        self.answers = {}

    async def home(self):
        await self.page.goto(BASE + '/', wait_until='domcontentloaded')
        self.steps += 1
        self.log.append('open homepage (start_url)')

    async def nav(self, selector, note):
        await self.page.click(selector)
        await self.page.wait_for_load_state('domcontentloaded')
        self.steps += 1
        self.log.append(f'click {note}')

    async def fill(self, selector, value, note):
        await self.page.fill(selector, value)
        self.steps += 1
        self.log.append(f'fill {note}')

    async def select(self, selector, value, note):
        await self.page.select_option(selector, value)
        self.steps += 1
        self.log.append(f'select {note}')

    async def submit(self, selector, note):
        await self.page.click(selector)
        await self.page.wait_for_load_state('domcontentloaded')
        self.steps += 1
        self.log.append(f'submit {note}')

    async def press_enter(self, selector, note):
        await self.page.press(selector, 'Enter')
        await self.page.wait_for_load_state('domcontentloaded')
        self.steps += 1
        self.log.append(f'submit {note}')

    # ---------------------------------------------------------- reads --

    async def text(self):
        return await self.page.inner_text('body')

    async def contains(self, needle):
        text = await self.text()
        if needle not in text:
            raise AssertionError(f'premise failed: {needle!r} not on page '
                                 f'({self.page.url})')
        return text

    async def rows(self, selector):
        """First-cell texts of a table's tbody rows (symbol column)."""
        loc = self.page.locator(selector)
        n = await loc.count()
        return [await loc.nth(i).inner_text() for i in range(n)]

    async def row_count(self, selector):
        return await self.page.locator(selector).count()

    async def texts(self, selector):
        loc = self.page.locator(selector)
        n = await loc.count()
        return [await loc.nth(i).inner_text() for i in range(n)]

    async def text_of(self, selector):
        return await self.page.inner_text(selector)

    def answer(self, key, value):
        self.answers[key] = value


async def lookup_open(w, term, symbol, display=None):
    await w.fill('.search-form input', term, f'search box: "{term}"')
    await w.press_enter('.search-form input', f'search for "{term}"')
    await w.contains(display or symbol)
    await w.nav(f'a[href="/quote/{symbol}"]', f'open {display or symbol} quote')


async def login(w, email, password='TestPass123!'):
    await w.nav('.nav-auth a[href^="/login"]', 'Sign in link')
    await w.fill('#email', email, 'email')
    await w.fill('#password', password, 'password')
    await w.submit('form[action="/login"] button[type=submit]', f'login {email}')


async def add_to_watchlist(w, symbol):
    await w.contains(f'({symbol})')
    await w.submit('form[action="/watchlist/toggle"] button',
                   f'add {symbol} to watchlist')
    await w.contains('Remove from Watchlist')


async def create_alert(w, direction, threshold, note=None):
    # Anti-padding: the direction dropdown's visible default is read for
    # free; it is only re-operated (and only then counted) when the default
    # does not already satisfy the requested direction.
    current = await w.page.eval_on_selector(
        '#direction', 'el => el.options[el.selectedIndex].value')
    if current != direction:
        await w.select('#direction', direction,
                       f'alert direction {direction}')
    await w.fill('#threshold', str(threshold), 'alert target price')
    if note is not None:
        await w.fill('#note', note, 'alert note')
    await w.submit('form[action="/alerts/create"] button',
                   f'create alert {direction} {threshold}')


async def alert_rows(w):
    """[symbol, direction+threshold, status] per alerts-page row."""
    symbols = await w.texts('table.yf tbody tr td:nth-child(1)')
    alerts = await w.texts('table.yf tbody tr td:nth-child(3)')
    statuses = await w.texts('table.yf tbody tr td:nth-child(6)')
    return list(zip(symbols, alerts, statuses))


async def run_task(index, w):
    t = TASKS[index]

    if index == 0:
        await w.home()
        await lookup_open(w, 'apple', 'AAPL')
        text = await w.contains('52 Week Range')
        overview = re.search(r'Overview [^\n]+/ ([^\n]+)', text)
        w.answer('sector', overview.group(1).strip())
        m = re.search(r'52 Week Range\s*\n([\d.]+ - [\d.]+)', text)
        w.answer('w52', m.group(1))
        await w.nav('a.quote-tab[href="/quote/AAPL/statistics"]',
                    'Statistics tab')
        text = await w.contains('Profit Margin')
        w.answer('profit_margin', re.search(
            r'Profit Margin\s*\n([\d.]+%)', text).group(1))
        w.answer('target', re.search(
            r'1y Target Estimate\s*\n([\d,.]+)', text).group(1))
        await w.nav('a.quote-tab[href="/quote/AAPL/profile"]',
                    'Profile tab')
        text = await w.contains('Company Facts')
        facts = await w.texts('.fact .fact-value')
        w.answer('website', facts[4])
        w.answer('city', facts[6])
        await login(w, 'alice.j@test.com')
        await add_to_watchlist(w, 'AAPL')
        await w.nav('.nav-auth a[href="/watchlist"]', 'My Watchlist link')
        symbols = await w.rows('table.yf tbody tr td:first-child')
        w.answer('watchlist', symbols)
        w.answer('watch_count', len(symbols))
        prices = await w.texts('table.yf tbody tr td:nth-child(3)')
        w.answer('aapl_price',
                  prices[symbols.index('AAPL')] if 'AAPL' in symbols else None)
        await w.nav('a[href="/quote/AAPL"]', 'AAPL row link')
        await create_alert(w, 'above', 350, 'iPhone cycle')
        rows = await alert_rows(w)
        w.answer('alerts', rows)
        w.answer('alert_status', [r[2] for r in rows if r[0] == 'AAPL'][0])
        w.answer('alert_total', len(rows))

    elif index == 1:
        await w.home()
        await w.nav('.nav-auth a[href="/signup"]', 'Sign up link')
        await w.fill('#name', 'Jordan Vale', 'full name')
        await w.fill('#email', 'jordan.vale@test.com', 'email')
        await w.fill('#password', 'TestPass123!', 'password')
        await w.submit('form[action="/signup"] button[type=submit]', 'sign up')
        await w.contains('Jordan')
        await w.nav('nav.main-nav a[href="/screener"]', 'Screener nav')
        text = await w.contains('Day Gainers')
        cells = await w.texts('table.preset-table tbody tr:first-child td')
        w.answer('top_gainer', cells[0])
        w.answer('top_price', cells[2])
        w.answer('top_chg', cells[4])
        await w.select('#sector', 'Technology', 'sector filter')
        await w.fill('#pe_min', '12', 'P/E min')
        await w.fill('#pe_max', '40', 'P/E max')
        await w.select('#sort', 'pe', 'sort by P/E')
        await w.select('#dir', 'asc', 'ascending')
        await w.submit('form.filter-form button[type=submit]', 'apply filters')
        rows = await w.rows('table.results-table tbody tr td:first-child')
        w.answer('first_result', rows[0])
        first = await w.texts('table.results-table tbody tr:first-child td')
        w.answer('first_industry', first[3])
        await w.nav(f'a[href="/quote/{rows[0]}"]', f'first result {rows[0]}')
        await add_to_watchlist(w, rows[0])
        await w.nav('.nav-auth a[href="/watchlist"]', 'My Watchlist link')
        symbols = await w.rows('table.yf tbody tr td:first-child')
        w.answer('watchlist', symbols)

    elif index == 2:
        await w.home()
        await w.nav('nav.main-nav a[href="/calendar/earnings"]', 'Calendars nav')
        await w.contains('Earnings Calendar')
        await w.nav('a[href="/calendar/earnings?day=2026-09-20"]',
                    'previous week link')
        text = await w.contains('September 24, 2026')
        # find the September 24 row with the biggest positive surprise
        body_rows = await w.texts('table.yf tbody tr')
        best = None
        for row in body_rows:
            cells = [c.strip() for c in row.split('\t')]
            if len(cells) < 9 or 'September 24, 2026' not in cells[3]:
                continue
            if cells[7] in ('—', '-', ''):
                continue
            val = float(cells[7].replace(',', ''))
            if best is None or val > best[0]:
                best = (val, cells)
        assert best and best[1][0] == 'SFIX', f'unexpected best: {best}'
        w.answer('company', best[1][1])
        w.answer('est', best[1][5])
        w.answer('act', best[1][6])
        w.answer('surp', best[1][7])
        await w.select('#time', 'AMC', 'After market close filter')
        await w.submit('form.filter-form button[type=submit]', 'apply AMC filter')
        text = await w.text()
        w.answer('amc_events', int(re.search(r'(\d+) events? shown', text).group(1)))
        await w.nav('a.btn[href="/calendar/earnings?day=2026-09-20"]',
                    'clear filters')
        await w.fill('#symbol', 'COST', 'symbol filter')
        await w.submit('form.filter-form button[type=submit]', 'apply COST filter')
        rows = await w.texts('table.yf tbody tr')
        cost_row = [r for r in rows if r.startswith('COST\t')][0]
        cost_cells = [c.strip() for c in cost_row.split('\t')]
        w.answer('cost_time', cost_cells[4])
        w.answer('cost_est', cost_cells[5])
        await w.nav('a[href="/quote/COST"]', 'COST quote link')
        await login(w, 'dana.k@test.com')
        await create_alert(w, 'above', 1000, 'Earnings prep')
        rows = await alert_rows(w)
        w.answer('alerts', rows)
        w.answer('dana_alerts', len(rows))

    elif index == 3:
        await w.home()
        await w.nav('nav.main-nav a[href="/sectors"]', 'Markets nav')
        text = await w.contains('Sectors')
        rows = await w.texts('table.yf tbody tr')
        cells = [c.strip() for c in rows[0].split('\t')]
        w.answer('sector', cells[0])
        w.answer('day_chg', cells[1])
        w.answer('top_loser', cells[6].split(' ')[0])
        await w.nav('a[href="/sectors/technology"]', 'Technology sector link')
        text = await w.contains('Software - Infrastructure')
        m = re.search(r'\(15 companies', text)
        assert m, 'industry count not visible'
        blocks = await w.texts('.industry-block h3')
        w.answer('industry', 'Software - Infrastructure')
        w.answer('industry_count', 15)
        await w.nav('a[href="/quote/NVDA"]', 'largest company NVDA')
        text = await w.contains('NVIDIA')
        w.answer('nvda_pe', re.search(
            r'PE Ratio \(TTM\)\s*\n([\d.]+)', text).group(1))
        m = re.search(r'Forward Dividend & Yield\s*\n[\d.]+ \(([\d.]+%)\)', text)
        w.answer('nvda_dy', m.group(1) if m else None)
        await w.nav('a.quote-tab[href="/quote/NVDA/statistics"]',
                    'Statistics tab')
        text = await w.contains('50-Day Average')
        w.answer('nvda_day50', re.search(r'50-Day Average\s*\n([\d,.]+)',
                                         text).group(1))
        await login(w, 'carol.d@test.com')
        await add_to_watchlist(w, 'NVDA')
        await create_alert(w, 'below', 200, 'Dip buy')
        rows = await alert_rows(w)
        w.answer('alert_status', [r[2] for r in rows if r[0] == 'NVDA'][0])
        await w.nav('.nav-auth a[href="/watchlist"]', 'My Watchlist link')
        symbols = await w.rows('table.yf tbody tr td:first-child')
        w.answer('watch_count', len(symbols))

    elif index == 4:
        await w.home()
        await w.nav('nav.main-nav a[href="/news"]', 'News nav')
        await w.contains('Latest Financial News')
        await w.fill('#q', 'Nvidia', 'news search box')
        await w.submit('form.filter-form button[type=submit]', 'search news')
        text = await w.contains('match')
        w.answer('matches', int(re.search(r'(\d+) articles? match', text).group(1)))
        await w.nav('.news-list h3 a', 'most recent Nvidia article')
        text = await w.contains('Simply Wall St.')
        w.answer('publisher', 'Simply Wall St.')
        w.answer('author', re.search(r'(Sasha Jovanovic)', text).group(1))
        tickers = await w.texts('p.muted a')
        w.answer('tickers', [t for t in tickers if re.fullmatch(
            r'[A-Z^=.]+', t.strip())])
        await w.nav('nav.main-nav a[href="/news"]', 'News nav')
        await w.nav('a.topic-tab[href="/news?topic=economy"]', 'Economy tab')
        text = await w.contains("Fed's Kashkari")
        w.answer('econ_title', 'Fed\'s Kashkari says central bank must lower '
                               'inflation pressures')
        econ_pub = await w.texts(
            '.news-list .news-item .news-meta span')
        w.answer('econ_publisher', econ_pub[0])
        await login(w, 'dana.k@test.com')
        await lookup_open(w, 'NVDA', 'NVDA')
        await create_alert(w, 'below', 200, 'AI pullback')
        rows = await alert_rows(w)
        w.answer('alert_status', [r[2] for r in rows if r[0] == 'NVDA'][0])
        w.answer('dana_alerts', len(rows))

    elif index == 5:
        await w.home()
        await w.nav('nav.main-nav a[href="/trending"]', 'Trending nav')
        text = await w.contains('Trending Stocks')
        symbols = await w.rows('table.yf tbody tr td:nth-child(2)')
        chgs = await w.texts('table.yf tbody tr td:nth-child(6)')
        w.answer('top3', list(zip(symbols[:3], chgs[:3])))
        await w.nav('a[href="/quote/MU"]', 'open MU quote')
        await w.nav('a.quote-tab[href="/quote/MU/statistics"]',
                    'Statistics tab')
        text = await w.contains('Market Cap (intraday)')
        w.answer('mcap', re.search(
            r'Market Cap \(intraday\)\s*\n([\d.]+[TBK])', text).group(1))
        w.answer('pe', re.search(r'Trailing P/E\s*\n([\d.]+)', text).group(1))
        w.answer('day50', re.search(
            r'50-Day Average\s*\n([\d,.]+)', text).group(1))
        text = await w.contains('52 Week Range')
        w.answer('w52', re.search(r'52 Week Range\s*\n([\d.,]+ - [\d.,]+)',
                                  text).group(1))
        await login(w, 'carol.d@test.com')
        await add_to_watchlist(w, 'MU')
        await create_alert(w, 'above', 1200, 'Memory cycle')
        rows = await alert_rows(w)
        w.answer('alert_status', [r[2] for r in rows if r[0] == 'MU'][0])
        w.answer('carol_alerts', len(rows))
        await w.nav('nav.main-nav a[href="/trending"]', 'Trending nav')
        await w.nav('a[href="/quote/LQDA"]', 'open LQDA quote')
        text = await w.contains('Liquidia')
        w.answer('lqda_mcap', re.search(r'Market Cap\s*\n([\d.]+[BTK])',
                                        text).group(1))
        await w.nav('.nav-auth a[href="/watchlist"]', 'My Watchlist link')
        symbols = await w.rows('table.yf tbody tr td:first-child')
        w.answer('watch_count', len(symbols))

    elif index == 6:
        await w.home()
        await lookup_open(w, 'AMD', 'AMD')
        await w.nav('a.quote-tab[href="/quote/AMD/statistics"]',
                    'AMD Statistics tab')
        text = await w.contains('Trailing P/E')
        w.answer('amd_pe', re.search(r'Trailing P/E\s*\n([\d.]+)', text).group(1))
        w.answer('amd_pm', re.search(r'Profit Margin\s*\n([\d.]+%)', text).group(1))
        await lookup_open(w, 'NVDA', 'NVDA')
        await w.nav('a.quote-tab[href="/quote/NVDA/statistics"]',
                    'NVDA Statistics tab')
        text = await w.contains('Trailing P/E')
        w.answer('nvda_pe', re.search(r'Trailing P/E\s*\n([\d.]+)', text).group(1))
        w.answer('nvda_pm', re.search(r'Profit Margin\s*\n([\d.]+%)', text).group(1))
        await login(w, 'bob.c@test.com')
        await add_to_watchlist(w, 'NVDA')
        await create_alert(w, 'above', 700)
        rows = await alert_rows(w)
        w.answer('alert_status', [r[2] for r in rows if r[0] == 'NVDA'][0])
        await w.nav('.nav-auth a[href="/watchlist"]', 'My Watchlist link')
        symbols = await w.rows('table.yf tbody tr td:first-child')
        w.answer('watchlist', symbols)

    elif index == 7:
        await w.home()
        await w.nav('nav.main-nav a[href="/screener"]', 'Screener nav')
        await w.nav('a.topic-tab[href="/screener?preset=most_actives"]',
                    'Most Actives preset tab')
        text = await w.contains('Most Actives')
        rows = await w.texts('div.card table.yf tbody tr')
        # preset table is the first card table on the page
        first = await w.texts('table.yf tbody tr:first-child td')
        w.answer('most_active', first[0])
        w.answer('volume', first[5])
        w.answer('chg', first[4])
        await w.nav('a[href="/quote/NU"]', 'NU quote link')
        text = await w.contains('Nu Holdings')
        w.answer('industry', re.search(
            r'Overview ([^\n]+) / [^\n]+', text).group(1).strip())
        await w.nav('a.quote-tab[href="/quote/NU/history"]',
                    'Historical Data tab')
        text = await w.contains('Historical Prices')
        dates = await w.texts('table.yf tbody tr td:first-child')
        closes = await w.texts('table.yf tbody tr td:nth-child(2)')
        w.answer('last_close', closes[0])
        w.answer('first_close', closes[-1])
        await w.nav('a.quote-tab[href="/quote/NU/statistics"]',
                    'Statistics tab')
        text = await w.contains('50-Day Average')
        w.answer('day50', re.search(r'50-Day Average\s*\n([\d,.]+)', text).group(1))
        await login(w, 'dana.k@test.com')
        await add_to_watchlist(w, 'NU')
        await create_alert(w, 'above', 20, 'LatAm growth')
        await w.nav('.nav-auth a[href="/watchlist"]', 'My Watchlist link')
        symbols = await w.rows('table.yf tbody tr td:first-child')
        w.answer('watchlist', symbols)

    elif index == 8:
        await w.home()
        await w.nav('nav.main-nav a[href="/news"]', 'News nav')
        await w.fill('#q', 'buyback', 'news search box')
        await w.submit('form.filter-form button[type=submit]', 'search news')
        text = await w.contains('match')
        w.answer('matches', int(re.search(r'(\d+) articles? match', text).group(1)))
        await w.nav('.news-list h3 a', 'most recent buyback article')
        text = await w.contains('Motley Fool')
        w.answer('publisher', 'Motley Fool')
        w.answer('author', re.search(r'(Will Healy)', text).group(1))
        w.answer('nvda_close', re.search(r'closed at \$([\d.]+)', text).group(1))
        w.answer('nvda_chg', re.search(r'up ([\d.]+%)', text).group(1))
        w.answer('volume', re.search(
            r'Trading volume reached ([\d.]+M shares)', text).group(1))
        await w.nav('nav.main-nav a[href="/news"]', 'News nav')
        await w.nav('a.topic-tab[href="/news?topic=earnings"]', 'Earnings tab')
        text = await w.contains('CBOE')
        w.answer('earnings_article', re.search(r'(CBOE.{0,70}Gains\?)',
                                               text).group(1))
        await login(w, 'dana.k@test.com')
        await lookup_open(w, 'NVDA', 'NVDA')
        await add_to_watchlist(w, 'NVDA')
        await w.nav('.nav-auth a[href="/watchlist"]', 'My Watchlist link')
        symbols = await w.rows('table.yf tbody tr td:first-child')
        w.answer('watch_count', len(symbols))

    elif index == 9:
        await w.home()
        await w.nav('.nav-auth a[href="/signup"]', 'Sign up link')
        await w.fill('#name', 'Priya Nair', 'full name')
        await w.fill('#email', 'priya.nair@test.com', 'email')
        await w.fill('#password', 'TestPass123!', 'password')
        await w.submit('form[action="/signup"] button[type=submit]', 'sign up')
        await w.contains('Priya')
        await lookup_open(w, 'Apple', 'AAPL')
        await w.nav('a.quote-tab[href="/quote/AAPL/financials"]',
                    'Financials tab')
        text = await w.contains('Income Statement (Annual)')
        rows = await w.texts('table.yf tbody tr')
        last = rows[-1]
        cells = [c.strip() for c in last.split('\t')]
        w.answer('fy_end', cells[0])
        w.answer('revenue', cells[1])
        w.answer('net_income', cells[5])
        await w.nav('a.quote-tab[href="/quote/AAPL/statistics"]',
                    'Statistics tab')
        text = await w.contains('PEG Ratio')
        w.answer('peg', re.search(
            r'PEG Ratio \(5Y expected\)\s*\n([\d.]+)', text).group(1))
        w.answer('beta', re.search(r'Beta \(5Y Monthly\)\s*\n([\d.]+)',
                                   text).group(1))
        await add_to_watchlist(w, 'AAPL')
        await w.nav('a.quote-tab[href="/quote/AAPL/profile"]', 'Profile tab')
        text = await w.contains('Full Time Employees')
        facts = await w.texts('.fact .fact-value')
        w.answer('employees', facts[2])
        await w.nav('.nav-auth a[href="/watchlist"]', 'My Watchlist link')
        symbols = await w.rows('table.yf tbody tr td:first-child')
        w.answer('watchlist', symbols)
        await w.nav('nav.main-nav a[href="/news"]', 'News nav')
        await w.fill('#q', 'Apple', 'news search box')
        await w.submit('form.filter-form button[type=submit]', 'search news')
        text = await w.contains('match')
        w.answer('matches', int(re.search(r'(\d+) articles? match', text).group(1)))
        await w.nav('.news-list h3 a', 'most recent Apple article')
        text = await w.contains('TheStreet')
        w.answer('publisher', 'TheStreet')
        w.answer('author', re.search(r'(Hillary Remy)', text).group(1))

    elif index == 10:
        await w.home()
        await lookup_open(w, 'Coca-Cola', 'KO')
        await w.nav('a.quote-tab[href="/quote/KO/profile"]', 'Profile tab')
        text = await w.contains('Company Facts')
        facts = await w.texts('.fact .fact-value')
        w.answer('sector', facts[0])
        w.answer('industry', facts[1])
        w.answer('employees', facts[2])
        w.answer('website', facts[4])
        await w.nav('a.quote-tab[href="/quote/KO"]', 'Summary tab')
        text = await w.contains('Forward Dividend')
        m = re.search(r'Forward Dividend & Yield\s*\n([\d.]+) \(([\d.]+%)\)', text)
        w.answer('div_rate', m.group(1))
        w.answer('div_yield', m.group(2))
        await lookup_open(w, 'PepsiCo', 'PEP')
        await w.nav('a.quote-tab[href="/quote/PEP/statistics"]',
                    'Statistics tab')
        text = await w.contains('Profit Margin')
        w.answer('pep_pm', re.search(r'Profit Margin\s*\n([\d.]+%)', text).group(1))
        w.answer('pep_pe', re.search(r'Trailing P/E\s*\n([\d.]+)', text).group(1))
        await login(w, 'bob.c@test.com')
        await create_alert(w, 'above', 100, 'Cola wars')
        rows = await alert_rows(w)
        w.answer('alert_status', [r[2] for r in rows if r[0] == 'PEP'][0])
        await w.nav('.nav-auth a[href="/watchlist"]', 'My Watchlist link')
        symbols = await w.rows('table.yf tbody tr td:first-child')
        w.answer('bob_watch', len(symbols))

    elif index == 11:
        await w.home()
        await w.nav('nav.main-nav a[href="/calendar/earnings"]', 'Calendars nav')
        await w.contains('Earnings Calendar')
        await w.nav('a[href="/calendar/earnings?day=2026-10-04"]',
                    'next week link')
        text = await w.contains('October 8, 2026 (97)')
        tabs = await w.texts('.day-tab')
        best = max(tabs, key=lambda t: int(re.search(r'\((\d+)\)', t).group(1)))
        w.answer('busiest_day', best.split(' (')[0])
        w.answer('busiest_count', int(re.search(r'\((\d+)\)', best).group(1)))
        await w.nav('a[href="/calendar/earnings?day=2026-09-27"]',
                    'this week link')
        text = await w.contains('Earnings Calendar')
        tabs = await w.texts('.day-tab')
        best = max(tabs, key=lambda t: int(re.search(r'\((\d+)\)', t).group(1)))
        w.answer('this_week_day', best.split(' (')[0])
        w.answer('this_week_count', int(re.search(r'\((\d+)\)', best).group(1)))
        await lookup_open(w, 'Apple', 'AAPL')
        text = await w.contains('Next earnings')
        w.answer('earnings_date', re.search(r'Next earnings:\s*(.*)', text).group(1))
        await w.nav('a.quote-tab[href="/quote/AAPL/statistics"]',
                    'Statistics tab')
        text = await w.contains('1y Target Estimate')
        w.answer('target', re.search(r'1y Target Estimate\s*\n([\d,.]+)',
                                     text).group(1))
        w.answer('day50', re.search(r'50-Day Average\s*\n([\d,.]+)',
                                     text).group(1))
        await login(w, 'dana.k@test.com')
        await create_alert(w, 'above', 400, 'Earnings run')
        rows = await alert_rows(w)
        w.answer('alert_status', [r[2] for r in rows if r[0] == 'AAPL'][0])
        w.answer('dana_alerts', len(rows))

    elif index == 12:
        await w.home()
        await login(w, 'carol.d@test.com')
        await w.nav('.nav-auth a[href="/watchlist"]', 'My Watchlist link')
        symbols = await w.rows('table.yf tbody tr td:first-child')
        w.answer('initial', symbols)
        await w.nav('tr:has-text("UNH") form[action="/watchlist/toggle"] button',
                    'remove UNH')
        symbols = await w.rows('table.yf tbody tr td:first-child')
        assert 'UNH' not in symbols, 'UNH still on watchlist'
        await lookup_open(w, 'Merck', 'MRK')
        text = await w.contains('Merck')
        w.answer('mrk_pe', re.search(r'PE Ratio \(TTM\)\s*\n([\d.]+)',
                                     text).group(1))
        w.answer('mrk_w52', re.search(
            r'52 Week Range\s*\n([\d.]+ - [\d.]+)', text).group(1))
        await add_to_watchlist(w, 'MRK')
        await create_alert(w, 'above', 160, 'Pharma rotation')
        rows = await alert_rows(w)
        w.answer('alert_status', [r[2] for r in rows if r[0] == 'MRK'][0])
        await w.nav('.nav-auth a[href="/watchlist"]', 'My Watchlist link')
        symbols = await w.rows('table.yf tbody tr td:first-child')
        w.answer('final_watch', symbols)

    elif index == 13:
        await w.home()
        await login(w, 'alice.j@test.com')
        await w.nav('.nav-auth a[href="/alerts"]', 'Alerts link')
        rows = await alert_rows(w)
        w.answer('seeded_alerts', rows)
        await w.nav('tr:has-text("TSLA") form[action="/alerts/delete"] button',
                    'delete TSLA alert')
        rows = await alert_rows(w)
        assert all(r[0] != 'TSLA' for r in rows), 'TSLA alert not deleted'
        await lookup_open(w, 'TSLA', 'TSLA')
        await create_alert(w, 'above', 900, 'Upside breakout')
        rows = await alert_rows(w)
        w.answer('new_status', [r[2] for r in rows if r[0] == 'TSLA'][0])
        w.answer('final_count', len(rows))
        await w.nav('table.yf tbody a[href="/quote/TSLA"]', 'TSLA row link')
        await w.nav('a.quote-tab[href="/quote/TSLA/statistics"]',
                    'Statistics tab')
        text = await w.contains('50-Day Average')
        w.answer('day50', re.search(r'50-Day Average\s*\n([\d,.]+)',
                                    text).group(1))

    elif index == 14:
        await w.home()
        text = await w.contains('Day Gainers')
        movers = await w.texts('.mover-card:first-of-type table tbody tr td:first-child')
        mover_chgs = await w.texts(
            '.mover-card:first-of-type table tbody tr td:nth-child(3)')
        w.answer('top_gainer', movers[0])
        w.answer('top_gainer_chg', mover_chgs[0])
        await w.nav('nav.main-nav a[href="/screener"]', 'Screener nav')
        await w.select('#sector', 'Healthcare', 'sector filter')
        await w.fill('#mcap_min', '10000000000', 'market cap min')
        await w.fill('#mcap_max', '200000000000', 'market cap max')
        await w.select('#sort', 'change', 'sort by % change')
        await w.submit('form.filter-form button[type=submit]', 'apply filters')
        text = await w.contains('ImmunityBio')
        syms = await w.rows('table.results-table tbody tr td:first-child')
        chgs = await w.texts(
            'table.results-table tbody tr td:nth-child(6)')
        w.answer('first3', list(zip(syms[:3], chgs[:3])))
        await w.nav('a[href="/quote/UTHR"]', 'UTHR quote link')
        await w.nav('a.quote-tab[href="/quote/UTHR/statistics"]',
                    'Statistics tab')
        text = await w.contains('52-Week Change')
        w.answer('w52_chg', re.search(r'52-Week Change\s*\n([+-][\d.]+%)',
                                      text).group(1))
        await login(w, 'bob.c@test.com')
        await add_to_watchlist(w, 'UTHR')
        await w.nav('.nav-auth a[href="/watchlist"]', 'My Watchlist link')
        symbols = await w.rows('table.yf tbody tr td:first-child')
        w.answer('watchlist', symbols)

    elif index == 15:
        await w.home()
        await w.fill('.search-form input', 'bitcoin', 'search box: bitcoin')
        await w.press_enter('.search-form input', 'search for bitcoin')
        text = await w.contains('Bitcoin USD')
        syms = await w.rows('table.yf tbody tr td:first-child')
        w.answer('symbols', syms)
        await w.nav('a[href="/quote/BTC-USD"]', 'Bitcoin USD quote link')
        text = await w.contains('Bitcoin USD')
        w.answer('price', re.search(r'\n(83,?452\.08)\n', text).group(1))
        w.answer('mcap', re.search(r'Market Cap\s*\n([\d.]+[TBK])',
                                   text).group(1))
        w.answer('w52', re.search(r'52 Week Range\s*\n([\d.,]+ - [\d.,]+)',
                                  text).group(1))
        await w.nav('nav.main-nav a[href="/news"]', 'News nav')
        await w.fill('#q', 'stablecoin', 'news search box')
        await w.submit('form.filter-form button[type=submit]', 'search news')
        text = await w.contains('match')
        w.answer('matches', int(re.search(r'(\d+) articles? match', text).group(1)))
        await w.nav('.news-list h3 a', 'most recent stablecoin article')
        text = await w.contains('Bankless')
        w.answer('publisher', 'Bankless')
        w.answer('author', re.search(r'(William Peaster)', text).group(1))
        w.answer('reserves', re.search(
            r'(BlackRock, BNY, and Lead Bank) handle reserves',
            text).group(1))
        await login(w, 'dana.k@test.com')
        await lookup_open(w, 'bitcoin', 'BTC-USD')
        await add_to_watchlist(w, 'BTC-USD')
        await create_alert(w, 'above', 90000, 'ETF bid')
        rows = await alert_rows(w)
        w.answer('alert_status', [r[2] for r in rows if r[0] == 'BTC-USD'][0])
        await w.nav('.nav-auth a[href="/watchlist"]', 'My Watchlist link')
        symbols = await w.rows('table.yf tbody tr td:first-child')
        w.answer('watchlist', symbols)

    elif index == 16:
        await w.home()
        await w.nav('nav.main-nav a[href="/sectors"]', 'Markets nav')
        await w.nav('a[href="/sectors/healthcare"]', 'Healthcare sector link')
        text = await w.contains('Healthcare Sector')
        w.answer('companies', int(re.search(r'(\d+) captured companies',
                                            text).group(1)))
        blocks = await w.texts('.industry-block h3')
        w.answer('industry', blocks[0].split(' (')[0].strip())
        await w.nav('a[href="/quote/LLY"]', 'largest company LLY')
        await w.nav('a.quote-tab[href="/quote/LLY/statistics"]',
                    'LLY Statistics tab')
        text = await w.contains('Trailing P/E')
        w.answer('lly_pe', re.search(r'Trailing P/E\s*\n([\d.]+)', text).group(1))
        w.answer('lly_pm', re.search(r'Profit Margin\s*\n([\d.]+%)',
                                     text).group(1))
        await w.nav('nav.main-nav a[href="/sectors"]', 'Markets nav')
        await w.nav('a[href="/sectors/healthcare"]', 'Healthcare sector link')
        await w.nav('a[href="/quote/JNJ"]', 'second largest JNJ')
        await w.nav('a.quote-tab[href="/quote/JNJ/statistics"]',
                    'JNJ Statistics tab')
        text = await w.contains('Trailing P/E')
        w.answer('jnj_pe', re.search(r'Trailing P/E\s*\n([\d.]+)', text).group(1))
        w.answer('jnj_pm', re.search(r'Profit Margin\s*\n([\d.]+%)',
                                     text).group(1))
        await login(w, 'bob.c@test.com')
        await add_to_watchlist(w, 'JNJ')
        await create_alert(w, 'above', 300, 'Dividend value')
        rows = await alert_rows(w)
        w.answer('alert_status', [r[2] for r in rows if r[0] == 'JNJ'][0])
        await w.nav('.nav-auth a[href="/watchlist"]', 'My Watchlist link')
        symbols = await w.rows('table.yf tbody tr td:first-child')
        w.answer('watch_count', len(symbols))

    elif index == 17:
        await w.home()
        await lookup_open(w, 'Microsoft', 'MSFT')
        await w.nav('a.quote-tab[href="/quote/MSFT/history"]',
                    'Historical Data tab')
        text = await w.contains('Historical Prices')
        dates = await w.texts('table.yf tbody tr td:first-child')
        closes = await w.texts('table.yf tbody tr td:nth-child(2)')
        w.answer('last_close', closes[0])
        w.answer('first_close', closes[-1])
        await w.nav('a.quote-tab[href="/quote/MSFT/statistics"]',
                    'Statistics tab')
        text = await w.contains('50-Day Average')
        w.answer('day50', re.search(r'50-Day Average\s*\n([\d,.]+)',
                                    text).group(1))
        w.answer('day200', re.search(r'200-Day Average\s*\n([\d,.]+)',
                                     text).group(1))
        await login(w, 'alice.j@test.com')
        await w.nav('.nav-auth a[href="/watchlist"]', 'My Watchlist link')
        symbols = await w.rows('table.yf tbody tr td:first-child')
        w.answer('watch_count', len(symbols))
        await w.nav('a[href="/quote/MSFT"]', 'MSFT row link')
        await create_alert(w, 'above', 600, 'Azure wave')
        rows = await alert_rows(w)
        w.answer('alert_status', [r[2] for r in rows if r[0] == 'MSFT'][0])
        w.answer('alice_alerts', len(rows))

    elif index == 18:
        await w.home()
        await w.nav('nav.main-nav a[href="/news"]', 'News nav')
        await w.fill('#q', 'inflation', 'news search box')
        await w.submit('form.filter-form button[type=submit]', 'search news')
        text = await w.contains('match')
        w.answer('matches', int(re.search(r'(\d+) articles? match', text).group(1)))
        await w.nav('.news-list h3 a', 'most recent inflation article')
        text = await w.contains('Reuters')
        w.answer('publisher', 'Reuters')
        w.answer('author', re.search(r'(Michael S\. Derby)', text).group(1))
        await lookup_open(w, 'gold', 'GC%3DF', display='GC=F')
        text = await w.contains('Gold Dec 26')
        w.answer('price', re.search(r'\n(4,?183\.20)\n', text).group(1))
        w.answer('chg', re.search(r'\((-[\d.]+%)\)', text).group(1))
        await login(w, 'carol.d@test.com')
        await add_to_watchlist(w, 'GC=F')
        await create_alert(w, 'above', 4300, 'Rally hedge')
        rows = await alert_rows(w)
        w.answer('alert_status', [r[2] for r in rows if r[0] == 'GC=F'][0])
        await w.nav('.nav-auth a[href="/watchlist"]', 'My Watchlist link')
        symbols = await w.rows('table.yf tbody tr td:first-child')
        w.answer('watch_count', len(symbols))

    elif index == 19:
        await w.home()
        await w.nav('nav.main-nav a[href="/screener"]', 'Screener nav')
        await w.select('#sector', 'Utilities', 'sector filter')
        await w.fill('#yield_min', '4', 'dividend yield min')
        await w.select('#sort', 'yield', 'sort by yield')
        await w.submit('form.filter-form button[type=submit]', 'apply filters')
        text = await w.contains('Dominion Energy')
        syms = await w.rows('table.results-table tbody tr td:first-child')
        dys = await w.texts(
            'table.results-table tbody tr td:nth-child(9)')
        w.answer('first3', list(zip(syms[:3], dys[:3])))
        await w.nav('a[href="/quote/D"]', 'third result D')
        text = await w.contains('Dominion Energy')
        m = re.search(r'Forward Dividend & Yield\s*\n([\d.]+) \(([\d.]+%)\)', text)
        w.answer('dy', m.group(2))
        w.answer('mcap', re.search(r'Market Cap\s*\n([\d,.]+[BTK])',
                                   text).group(1))
        w.answer('edate', re.search(r'Next earnings:\s*(.*)', text).group(1))
        await login(w, 'dana.k@test.com')
        await add_to_watchlist(w, 'D')
        await w.nav('.nav-auth a[href="/alerts"]', 'Alerts link')
        rows = await alert_rows(w)
        w.answer('seeded_alerts', rows)
        await w.nav('tr:has-text("META") form[action="/alerts/delete"] button',
                    'delete META alert')
        text = await w.contains('no alerts')
        w.answer('remaining', 0)
        await w.nav('.nav-auth a[href="/watchlist"]', 'My Watchlist link')
        symbols = await w.rows('table.yf tbody tr td:first-child')
        w.answer('watch_count', len(symbols))

    else:
        raise AssertionError(f'no walker for task {index}')


TASKS = [json.loads(l) for l in (SITE / 'tasks.jsonl').read_text()
         .splitlines() if l.strip()]


async def walk_task(index, round_no):
    tmp = Path(tempfile.mkdtemp(prefix=f'yf-task-{index}-r{round_no}-'))
    db_path = tmp / 'yahoo_finance.db'
    shutil.copy(SEED, db_path)
    server = Server(db_path)
    server.start()
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(viewport={'width': 1440,
                                                       'height': 900})
            page = await ctx.new_page()
            w = Walker(page)
            try:
                await run_task(index, w)
            finally:
                await browser.close()
    finally:
        server.stop()
    return w


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tasks', default='')
    parser.add_argument('--rounds', type=int, default=2)
    parser.add_argument('--dump', action='store_true')
    args = parser.parse_args()
    if args.tasks:
        indexes = [int(x) for x in args.tasks.split(',')]
    else:
        indexes = list(range(len(TASKS)))

    results = {}
    problems = []
    for index in indexes:
        counts = []
        answers = None
        logs = None
        for round_no in range(1, args.rounds + 1):
            w = asyncio.run(walk_task(index, round_no))
            counts.append(w.steps)
            answers = w.answers
            logs = w.log
        same = all(c == counts[0] for c in counts)
        ok = min(counts) >= MIN_STEPS and same
        results[TASKS[index]['id']] = {'steps': counts, 'pass': ok}
        print(f'{TASKS[index]["id"]}: steps={counts} '
              f'{"OK" if ok else "FAIL"}')
        if not ok or args.dump:
            print('  log:', logs)
            print('  answers:', json.dumps(answers, default=str)[:400])
        if not ok:
            problems.append(TASKS[index]['id'])
    print('\n=== summary')
    for tid, r in results.items():
        print(f'{tid}: steps={r["steps"]} pass={r["pass"]}')
    if problems:
        print('FAILURES:', problems)
        return 1
    print(f'all {len(indexes)} tasks pass two-round browser audit '
          f'(>= {MIN_STEPS} steps each)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
