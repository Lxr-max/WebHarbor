#!/usr/bin/env python3
"""Real-browser honest walkthrough for the yahoo_finance mirror (review track).

Reviewer-written driver (independent of the contributor's
scripts_dev/validate_tasks.py): runs a real Chromium session against the
reviewer's own container (webharbor:yf-review, ports 46138 site / 47138
control plane) and, for every task in tasks.jsonl:

- resets the site through the control plane and opens a fresh browser
  context (cookies cleared) per task, archiving initial.db first;
- drives the honest MINIMAL path with visible-element interaction only —
  direct URL navigation is used exclusively for the homepage start;
  browser back counts as one atomic action;
- counts ATOMIC ACTIONS the task text genuinely requires (navigate, click,
  fill, select, submit, back). Reads are never counted. Redundant form
  interactions whose visible default already satisfies the task (verified
  by a read) are NOT taken (anti-padding): e.g. the alert direction select
  defaults to "Above" on every quote page, so an "above N dollars" alert
  needs no select, while "below" alerts do;
- records every answer fact from what the rendered pages actually show (no
  DB reads), writes trajectory.json with per-step screenshots, and
  archives after.db for state-delta ground truth.

Two independent rounds must agree per task (step counts and normalized
answers).

Run: python3 walk_tasks_review.py <round-name> [task_indexes...]
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parent.parent
BASE = os.environ.get('YF_WALK_BASE', 'http://localhost:46138')
CTRL = os.environ.get('YF_WALK_CTRL', 'http://localhost:47138')
TOKEN_FILE = os.environ.get(
    'YF_WALK_TOKEN',
    '/data/zhaoyang-user-projects/websyn/wh-yf-review-evidence/control_token')
CONTAINER = os.environ.get('YF_WALK_CONTAINER', 'wh-yf-r2')
EV = Path(os.environ.get(
    'YF_WALK_EVIDENCE',
    '/data/zhaoyang-user-projects/websyn/wh-yf-review-evidence/runs'))
PASSWORD = 'TestPass123!'
TASKS = {json.loads(line)['id']: json.loads(line)['ques'] for line in
         (SITE / 'tasks.jsonl').read_text(encoding='utf-8').splitlines()
         if line.strip()}


def reset_site():
    token = Path(TOKEN_FILE).read_text().strip()
    r = ''
    for _ in range(30):
        r = subprocess.run(
            ['curl', '-s', '-X', 'POST', '-H', f'Authorization: Bearer {token}',
             f'{CTRL}/reset/yahoo_finance'], capture_output=True, text=True,
            timeout=120).stdout
        if '"ready": true' in r or '"ready":true' in r:
            import urllib.request
            for _ in range(90):
                try:
                    urllib.request.urlopen(BASE + '/', timeout=2)
                    return
                except Exception:
                    time.sleep(0.5)
        time.sleep(1)
    raise RuntimeError('reset failed: ' + r[:300])


def snapshot_db(dest: Path):
    if dest.exists():
        dest.unlink()
    subprocess.run(['docker', 'cp',
                    f'{CONTAINER}:/opt/WebSyn/yahoo_finance/instance/yahoo_finance.db',
                    str(dest)], check=True, timeout=60)


class Walk:
    """One task's honest browser session with atomic-action accounting."""

    def __init__(self, page, task_id, out_dir):
        self.page = page
        self.task_id = task_id
        self.out = Path(out_dir)
        (self.out / 'screenshots').mkdir(parents=True, exist_ok=True)
        self.steps = []
        self.atomic = 0
        self.reads = []
        self.facts = {}
        self.js_errors = []
        self._shot = 0
        page.on('pageerror', lambda e: self.js_errors.append(str(e)[:200]))

    # ---------------------------------------------------------------- io --
    def _shoot(self):
        p = self.out / 'screenshots' / f'step_{self._shot:03d}.png'
        for attempt in range(3):
            try:
                self.page.screenshot(path=str(p), timeout=15000)
                break
            except Exception:
                if attempt == 2:
                    raise
                try:
                    self.page.wait_for_load_state('load', timeout=5000)
                except Exception:
                    pass
                self.page.wait_for_timeout(500)
        self._shot += 1
        return p.name

    def _log(self, action, params, desc):
        rec = {'step': len(self.steps), 'url': self.page.url,
               'title': self.page.title(), 'thought': desc, 'action': action,
               'params': params,
               'observed_text': (self.page.inner_text('body') or '')[:4000],
               'screenshot_before': self._shoot()}
        self.steps.append(rec)
        print(f'  [{self.atomic + 1:02d}] {action}: {desc}', flush=True)

    def _after(self, settle=True):
        try:
            self.page.wait_for_load_state('networkidle', timeout=8000)
        except Exception:
            pass
        self.page.wait_for_timeout(250)
        self.steps[-1]['screenshot_after'] = self._shoot()
        self.steps[-1]['url_after'] = self.page.url

    # ------------------------------------------------------------ actions --
    def start_home(self, desc='open homepage (start_url)'):
        self._log('navigate', {'url': BASE + '/'}, desc)
        self.page.goto(BASE + '/', timeout=45000, wait_until='load')
        self._after()
        self.atomic += 1

    def click(self, sel, desc, has=None):
        loc = self.page.locator(sel)
        if has is not None:
            loc = loc.filter(has_text=has)
        loc.first.scroll_into_view_if_needed(timeout=8000)
        self._log('click', {'selector': sel}, desc)
        loc.first.click(timeout=10000)
        self._after()
        self.atomic += 1

    def back(self, desc='browser back'):
        self._log('back', {}, desc)
        self.page.go_back()
        self._after()
        self.atomic += 1

    def select(self, sel, value, desc, by_label=False):
        self._log('select', {'selector': sel, 'value': str(value)}, desc)
        if by_label:
            self.page.select_option(sel, label=str(value), timeout=10000)
        else:
            self.page.select_option(sel, value, timeout=10000)
        self._after(settle=False)
        self.atomic += 1

    def fill(self, sel, value, desc):
        self._log('fill', {'selector': sel, 'value': value}, desc)
        self.page.fill(sel, value, timeout=10000)
        self._after(settle=False)
        self.atomic += 1

    def submit(self, sel, desc):
        self._log('click', {'selector': sel}, desc)
        self.page.locator(sel).first.scroll_into_view_if_needed(timeout=8000)
        self.page.locator(sel).first.click(timeout=10000)
        self._after()
        self.atomic += 1

    # -------------------------------------------------------------- reads --
    def read(self, key, value):
        self.reads.append({'key': key, 'value': str(value)})
        self.facts[key] = value
        print(f'      read {key} = {str(value)[:110]}', flush=True)

    def body(self):
        text = self.page.inner_text('body') or ''
        text = '\n'.join(line.strip() for line in text.splitlines())
        return re.sub(r'\n{2,}', '\n', text).strip()

    def save(self, answer):
        traj = {
            'task_id': self.task_id,
            'task': TASKS[self.task_id],
            'start_url': BASE + '/',
            'terminated': True,
            'termination_reason': 'agent_done',
            'final_answer': answer,
            'steps': self.steps,
            'reads': self.reads,
            'facts': self.facts,
            'js_errors': self.js_errors,
            'step_count': self.atomic,
            'final_url': self.page.url,
        }
        (self.out / 'trajectory.json').write_text(json.dumps(traj, indent=1))
        print(f'  => {self.atomic} atomic actions, answer saved', flush=True)


# ---------------------------------------------------------------- helpers --

def grab(pattern, body, what, flags=0):
    m = re.search(pattern, body, flags)
    assert m, f'pattern for {what} not found'
    return m.group(1).strip() if m.groups() else m.group(0).strip()


def nav(w, label):
    w.click(f'nav.main-nav a:has-text("{label}")', f'nav {label}')


def search_open(w, term, symbol):
    w.fill('.search-form input[name="s"]', term, f'header search "{term}"')
    w.submit('.search-form button[type="submit"]', f'submit search "{term}"')
    w.click(f'a[href="/quote/{symbol}"]', f'open {symbol} quote row')


def sign_in(w, email, password=PASSWORD):
    w.click('.nav-auth a[href^="/login"]', 'open log-in page')
    w.fill('#email', email, 'email')
    w.fill('#password', password, 'password')
    w.submit('form[action="/login"] button[type="submit"]', 'submit log-in')


def sign_up(w, name, email, password=PASSWORD):
    w.click('.nav-auth a[href="/signup"]', 'open sign-up page')
    w.fill('#name', name, 'full name')
    w.fill('#email', email, 'email')
    w.fill('#password', password, 'password')
    w.submit('form[action="/signup"] button[type="submit"]', 'submit sign-up')


def add_watchlist(w):
    w.submit('form[action="/watchlist/toggle"] button', 'add to watchlist')


def create_alert(w, direction, threshold, note=None):
    """Honest alert creation. The direction select defaults to 'above' on
    every quote page; an honest agent reads it (free) and only selects when
    the task's direction differs from the visible default."""
    cur = w.page.locator('#direction').input_value()
    if cur != direction:
        w.select('#direction', direction, f'alert direction {direction}')
    w.fill('#threshold', str(threshold), 'alert target price')
    if note is not None:
        w.fill('#note', note, 'alert note')
    w.submit('form[action="/alerts/create"] button', f'create alert')


def stat_value(w, label):
    """Read a dt/dd stat row by its exact label (any stat-rows block)."""
    dls = w.page.locator('dl.stat-rows').all_inner_texts()
    dl = '\n'.join(dls)
    m = re.search(re.escape(label) + r'\s*\n([^\n]+)', dl)
    assert m, f'stat {label!r} not found'
    return m.group(1).strip()


def watchlist_symbols(w):
    rows = w.page.locator('table.yf tbody tr').all_inner_texts()
    syms = [r.split('\t')[0].strip() for r in rows if r.strip()]
    return syms


def alert_rows(w):
    rows = w.page.locator('table.yf tbody tr').all_inner_texts()
    out = []
    for r in rows:
        cells = [c.strip() for c in r.split('\t')]
        if len(cells) >= 6:
            out.append(cells)
    return out


def news_rows(w):
    items = w.page.locator('ul.news-list li.news-item').all_inner_texts()
    return [i.replace('\n', ' ') for i in items]


def quote_about_line(w):
    m = re.search(r'Overview ([^\n/]+) / ([^\n]+)', w.body())
    return (m.group(1).strip(), m.group(2).strip()) if m else (None, None)


def calendar_events(w):
    rows = w.page.locator('table.yf tbody tr').all_inner_texts()
    out = []
    for r in rows:
        cells = [c.strip() for c in r.split('\t')]
        if len(cells) >= 8 and cells[0] and 'No earnings' not in r:
            out.append(cells)
    return out


# ------------------------------------------------------------------ tasks --

def article_meta(w):
    """{'author','publisher','title','related_tickers'} from an article page."""
    out = {}
    out['title'] = w.page.locator('h1').inner_text().strip()
    meta = w.page.locator('div.news-meta').first.inner_text()
    first_line = meta.split('\n')[0]
    if ' · ' in first_line:
        out['author'], out['publisher'] = [x.strip() for x in first_line.split(' · ', 1)]
    else:
        out['author'], out['publisher'] = None, first_line.strip()
    body = w.body()
    m = re.search(r'Related tickers:?\s*([^\n]+)', body)
    out['related_tickers'] = m.group(1).strip() if m else None
    return out


def task_00(w):
    w.start_home()
    search_open(w, 'Apple', 'AAPL')
    industry, sector = quote_about_line(w)
    w.read('sector', sector)
    w.read('w52', grab(r'52 Week Range\s*\n([^\n]+)', w.body(), '52w'))
    w.click('a.quote-tab:has-text("Statistics")', 'Statistics tab')
    w.read('margin', stat_value(w, 'Profit Margin'))
    w.read('target', stat_value(w, '1y Target Estimate'))
    w.click('a.quote-tab:has-text("Profile")', 'Profile tab')
    facts = w.page.locator('.fact').all_inner_texts()
    fd = {f.split('\n')[0]: f.split('\n')[1] for f in facts}
    w.read('website', fd.get('Website'))
    w.read('city', fd.get('City'))
    sign_in(w, 'alice.j@test.com')
    add_watchlist(w)
    w.click('.nav-auth a[href="/watchlist"]', 'open watchlist page')
    syms = watchlist_symbols(w)
    w.read('watch_symbols', syms)
    w.read('watch_count', len(syms))
    rows = w.page.locator('table.yf tbody tr').all_inner_texts()
    for r in rows:
        if r.startswith('AAPL'):
            w.read('aapl_last', r.split('\t')[2])
    w.click('a[href="/quote/AAPL"]', 'back to AAPL quote from watchlist')
    create_alert(w, 'above', 350, 'iPhone cycle')
    rows = alert_rows(w)
    w.read('alerts', rows)
    w.read('new_alert_status', [r[5] for r in rows if r[0] == 'AAPL'][0])
    w.read('alert_total', len(rows))
    return (f"Apple's sector is {sector} and its 52-week range is "
            f"{w.facts['w52']}. Apple's profit margin is {w.facts['margin']} "
            f"and its 1-year target estimate is {w.facts['target']}; its "
            f"website is {w.facts['website']} and headquarters city is "
            f"{w.facts['city']}. Alice's watchlist now lists {len(syms)} "
            f"symbols ({', '.join(syms)}); Apple's last price is "
            f"{w.facts['aapl_last']}. The new AAPL alert status is "
            f"{w.facts['new_alert_status']} and Alice has {len(rows)} alerts.")


def task_01(w):
    w.start_home()
    sign_up(w, 'Jordan Vale', 'jordan.vale@test.com')
    nav(w, 'Screener')
    cells = w.page.locator('table.preset-table tbody tr:first-child td').all_inner_texts()
    w.read('top_gainer', cells[0])
    w.read('top_price', cells[2])
    w.read('top_chg', cells[4])
    w.select('#sector', 'Technology', 'custom filter sector Technology')
    w.fill('#pe_min', '12', 'P/E min 12')
    w.fill('#pe_max', '40', 'P/E max 40')
    w.select('#sort', 'pe', 'sort by P/E')
    w.select('#dir', 'asc', 'ascending')
    w.submit('form.filter-form button[type="submit"]', 'apply custom filters')
    rows = w.page.locator('table.results-table tbody tr').all_inner_texts()
    first = rows[0].split('\t')
    w.read('first_symbol', first[0])
    w.read('first_name', first[1])
    w.click(f'a[href="/quote/{first[0]}"]', 'open first result quote')
    industry, sector = quote_about_line(w)
    w.read('industry', industry)
    add_watchlist(w)
    w.click('.nav-auth a[href="/watchlist"]', 'open watchlist page')
    syms = watchlist_symbols(w)
    w.read('watch_symbols', syms)
    return (f"Day Gainers top symbol is {cells[0]} at {cells[2]} "
            f"({cells[4]}). The first Technology P/E 12-40 ascending result "
            f"is {first[0]} ({first[1]}), industry {industry}. Watchlist "
            f"symbols: {', '.join(syms)}.")


def task_02(w):
    w.start_home()
    nav(w, 'Calendars')
    w.click('a:has-text("Previous week")', 'go to previous week')
    events = calendar_events(w)
    sep24 = [e for e in events if 'September 24' in e[3]]
    def _surp(e):
        try:
            return float(e[7].replace('%', '').replace('+', ''))
        except ValueError:
            return None
    cand = [e for e in sep24 if _surp(e) is not None and _surp(e) > 0]
    best = max(cand, key=_surp)
    w.read('biggest_surprise_company', best[1])
    w.read('eps_estimate', best[5])
    w.read('eps_actual', best[6])
    w.read('surprise_pct', best[7])
    w.select('#time', 'AMC', 'filter After market close')
    w.submit('form.filter-form button[type="submit"]', 'apply filter')
    events = calendar_events(w)
    w.read('amc_event_count', len(events))
    w.click('a.btn:has-text("Clear")', 'clear filters')
    w.fill('#symbol', 'COST', 'symbol filter COST')
    w.submit('form.filter-form button[type="submit"]', 'apply symbol filter')
    events = calendar_events(w)
    cost = events[0]
    w.read('cost_call_time', cost[4])
    w.read('cost_eps_estimate', cost[5])
    w.click('a[href="/quote/COST"]', 'open COST quote')
    sign_in(w, 'dana.k@test.com')
    create_alert(w, 'above', 1000, 'Earnings prep')
    rows = alert_rows(w)
    w.read('alert_total', len(rows))
    return (f"On September 24 the biggest positive EPS surprise was "
            f"{best[1]} ({best[0]}): estimate {best[5]}, actual {best[6]}, "
            f"surprise {best[7]}. After-market-close events that week: "
            f"{w.facts['amc_event_count']}. Costco's call time is {cost[4]} "
            f"with EPS estimate {cost[5]}. Dana now has {len(rows)} alerts.")


def parse_big(s):
    """'26.69T' / '4.96B' -> float in dollars."""
    s = s.strip()
    mult = {'T': 1e12, 'B': 1e9, 'M': 1e6, 'K': 1e3}.get(s[-1], 1)
    return float(s.rstrip('TBMK').replace(',', '')) * mult


def sector_rows(w):
    rows = w.page.locator('table.yf tbody tr').all_inner_texts()
    out = []
    for r in rows:
        cells = [c.strip() for c in r.split('\t')]
        if len(cells) >= 7:
            out.append(cells)
    return out


def industry_blocks(w):
    """[(name, member_count)] from sector-detail industry blocks."""
    out = []
    for h in w.page.locator('div.industry-block h3').all_inner_texts():
        m = re.match(r'(.+?)\s*\((\d+) compan', h)
        if m:
            out.append((m.group(1).strip(), int(m.group(2))))
    return out


def task_03(w):
    w.start_home()
    nav(w, 'Markets')
    rows = sector_rows(w)
    top = max(rows, key=lambda c: parse_big(c[2]))
    cells = top
    w.read('top_sector', cells[0])
    w.read('top_sector_chg', cells[1])
    w.read('top_loser', cells[6])
    slug = cells[0].lower().replace(' ', '-')
    w.click(f'a[href="/sectors/{slug}"]', 'open sector page')
    body = w.body()
    m = re.search(r'(\d+) captured companies', body)
    w.read('sector_companies', m.group(1) if m else None)
    inds = industry_blocks(w)
    best_ind = max(inds, key=lambda t: t[1])
    w.read('top_industry', best_ind[0])
    w.read('top_industry_count', best_ind[1])
    comp_rows = w.page.locator('table.yf tbody tr').all_inner_texts()
    largest = comp_rows[0].split('\t')
    w.read('largest_company', largest[0])
    w.click(f'a[href="/quote/{largest[0]}"]', 'open largest company quote')
    w.read('pe_ttm', grab(r'PE Ratio \(TTM\)\s*\n([^\n]+)', w.body(), 'pe'))
    w.read('div_rate', grab(r'Forward Dividend & Yield\s*\n([^\n]+)', w.body(), 'div'))
    w.click('a.quote-tab:has-text("Statistics")', 'Statistics tab')
    w.read('day50', stat_value(w, '50-Day Average'))
    sign_in(w, 'carol.d@test.com')
    add_watchlist(w)
    create_alert(w, 'below', 200, 'Dip buy')
    rows = alert_rows(w)
    w.read('new_alert_status', [r[5] for r in rows if r[0] == largest[0]][0])
    w.click('.nav-auth a[href="/watchlist"]', 'open watchlist page')
    syms = watchlist_symbols(w)
    w.read('watch_count', len(syms))
    return (f"Largest sector by aggregate market cap: {cells[0]} "
            f"({cells[1]} day change, top loser {cells[6]}). Its industry "
            f"with most companies: {best_ind[0]} with {best_ind[1]} "
            f"companies. Largest company {largest[0]}: P/E "
            f"{w.facts['pe_ttm']}, div {w.facts['div_rate']}, 50-day avg "
            f"{w.facts['day50']}. New alert status "
            f"{w.facts['new_alert_status']}; watchlist count {len(syms)}.")


def task_04(w):
    w.start_home()
    nav(w, 'News')
    w.fill('#q', 'Nvidia', 'news search Nvidia')
    w.submit('form.filter-form button[type="submit"]', 'submit news search')
    items = news_rows(w)
    w.read('match_count', len(items))
    w.click('ul.news-list li.news-item:first-child a', 'open most recent article')
    meta = article_meta(w)
    w.read('publisher', meta['publisher'])
    w.read('related_tickers', meta['related_tickers'])
    w.read('author', meta['author'])
    nav(w, 'News')
    w.click('a.topic-tab:has-text("Economy")', 'switch to Economy topic')
    items = news_rows(w)
    first = items[0] if items else None
    w.read('econ_first', first)
    sign_in(w, 'dana.k@test.com')
    search_open(w, 'NVDA', 'NVDA')
    create_alert(w, 'below', 200, 'AI pullback')
    rows = alert_rows(w)
    w.read('new_alert_status', [r[5] for r in rows if r[0] == 'NVDA'][0])
    w.read('alert_total', len(rows))
    return (f"{w.facts['match_count']} articles match Nvidia; most recent "
            f"{meta['title'][:60]} by {meta['publisher']}, author "
            f"{meta['author']}, tickers {meta['related_tickers']}. Economy "
            f"first: {first}. New NVDA alert {w.facts['new_alert_status']}; "
            f"Dana has {len(rows)} alerts.")


def task_05(w):
    w.start_home()
    nav(w, 'Trending')
    rows = w.page.locator('table.yf tbody tr').all_inner_texts()
    top3 = [r.split('\t') for r in rows[:3]]
    for i, r in enumerate(top3):
        w.read(f'trend{i+1}_sym', r[1])
        w.read(f'trend{i+1}_chg', r[5])
    w.click(f'a[href="/quote/{top3[0][1]}"]', 'open #1 trending quote')
    w.click('a.quote-tab:has-text("Statistics")', 'Statistics tab')
    w.read('mcap', stat_value(w, 'Market Cap (intraday)'))
    w.read('w52', stat_value(w, '52 Week Range'))
    w.read('pe_ttm', stat_value(w, 'Trailing P/E'))
    w.read('day50', stat_value(w, '50-Day Average'))
    sign_in(w, 'carol.d@test.com')
    add_watchlist(w)
    create_alert(w, 'above', 1200, 'Memory cycle')
    rows = alert_rows(w)
    w.read('alert_total', len(rows))
    nav(w, 'Trending')
    w.click(f'a[href="/quote/{top3[2][1]}"]', 'open #3 trending quote')
    w.read('trend3_mcap', grab(r'Market Cap\s*\n([^\n]+)', w.body(), 'mcap'))
    w.click('.nav-auth a[href="/watchlist"]', 'open watchlist page')
    syms = watchlist_symbols(w)
    w.read('watch_count', len(syms))
    return (f"Top trending: {top3[0][1]} ({top3[0][5]}), {top3[1][1]} "
            f"({top3[1][5]}), {top3[2][1]} ({top3[2][5]}). #1 stats: mcap "
            f"{w.facts['mcap']}, 52w {w.facts['w52']}, P/E {w.facts['pe_ttm']}, "
            f"50-day {w.facts['day50']}. #3 mcap {w.facts['trend3_mcap']}. "
            f"Watchlist {len(syms)} symbols; Carol has {len(rows)} alerts.")


def task_06(w):
    w.start_home()
    search_open(w, 'AMD', 'AMD')
    w.click('a.quote-tab:has-text("Statistics")', 'AMD Statistics tab')
    amd_pe = stat_value(w, 'Trailing P/E')
    amd_pm = stat_value(w, 'Profit Margin')
    w.read('amd_pe', amd_pe)
    w.read('amd_margin', amd_pm)
    search_open(w, 'NVDA', 'NVDA')
    w.click('a.quote-tab:has-text("Statistics")', 'NVDA Statistics tab')
    nvda_pe = stat_value(w, 'Trailing P/E')
    nvda_pm = stat_value(w, 'Profit Margin')
    w.read('nvda_pe', nvda_pe)
    w.read('nvda_margin', nvda_pm)
    lower = 'AMD' if float(amd_pe.replace(',', '')) < float(nvda_pe.replace(',', '')) else 'NVDA'
    w.read('lower_pe', lower)
    sign_in(w, 'bob.c@test.com')
    add_watchlist(w)
    create_alert(w, 'above', 700)
    rows = alert_rows(w)
    w.read('new_alert_status', [r[5] for r in rows if r[0] == lower][0])
    w.click('.nav-auth a[href="/watchlist"]', 'open watchlist page')
    syms = watchlist_symbols(w)
    w.read('watch_symbols', syms)
    return (f"AMD trailing P/E {amd_pe}, profit margin {amd_pm}; NVDA "
            f"trailing P/E {nvda_pe}, profit margin {nvda_pm}. Lower P/E: "
            f"{lower}. New alert status {w.facts['new_alert_status']}. "
            f"Bob's watchlist: {', '.join(syms)}.")


def task_07(w):
    w.start_home()
    nav(w, 'Screener')
    w.click('a.topic-tab:has-text("Most Actives")', 'Most Actives preset')
    cells = w.page.locator('table.preset-table tbody tr:first-child td').all_inner_texts()
    w.read('most_traded', cells[0])
    w.read('volume', cells[5])
    w.read('chg_pct', cells[4])
    w.click(f'a[href="/quote/{cells[0]}"]', 'open most-traded quote')
    industry, sector = quote_about_line(w)
    w.read('industry', industry)
    w.click('a.quote-tab:has-text("Historical Data")', 'Historical Data tab')
    rows = w.page.locator('table.yf tbody tr').all_inner_texts()
    w.read('last_close', rows[0].split('\t')[1])
    w.read('first_close', rows[-1].split('\t')[1])
    w.read('last_day', rows[0].split('\t')[0])
    w.read('first_day', rows[-1].split('\t')[0])
    w.click('a.quote-tab:has-text("Statistics")', 'Statistics tab')
    w.read('day50', stat_value(w, '50-Day Average'))
    sign_in(w, 'dana.k@test.com')
    add_watchlist(w)
    create_alert(w, 'above', 20, 'LatAm growth')
    w.click('.nav-auth a[href="/watchlist"]', 'open watchlist page')
    syms = watchlist_symbols(w)
    w.read('watch_symbols', syms)
    return (f"Most traded {cells[0]} volume {cells[5]} ({cells[4]}). Closes: "
            f"{w.facts['last_day']} {w.facts['last_close']}, "
            f"{w.facts['first_day']} {w.facts['first_close']}. 50-day avg "
            f"{w.facts['day50']}. Industry {industry}. Watchlist: "
            f"{', '.join(syms)}.")


def task_08(w):
    w.start_home()
    nav(w, 'News')
    w.fill('#q', 'buyback', 'news search buyback')
    w.submit('form.filter-form button[type="submit"]', 'submit news search')
    items = news_rows(w)
    w.read('match_count', len(items))
    w.click('ul.news-list li.news-item:first-child a', 'open most recent article')
    meta = article_meta(w)
    w.read('title', meta['title'])
    w.read('publisher', meta['publisher'])
    w.read('author', meta['author'])
    body = w.body()
    m = re.search(r'\$([\d.]+[BMT])\s*[Bb]uyback', meta['title']) or \
        re.search(r'[Bb]uyback[^\n]{0,30}\$([\d.]+[BMT])', meta['title'])
    w.read('buyback_size', m.group(1) if m else None)
    m = re.search(r'closed at \$([\d,.]+),\s*(up|down)\s*([\d.]+%)', body)
    if m:
        w.read('nvda_close', m.group(1))
        w.read('nvda_chg', f"{m.group(2)} {m.group(3)}")
    m = re.search(r'[Tt]rading volume reached ([\d.]+[BM])', body)
    w.read('nvda_volume', m.group(1) if m else None)
    nav(w, 'News')
    w.click('a.topic-tab:has-text("Earnings")', 'switch to Earnings topic')
    items = news_rows(w)
    w.read('earnings_only_title', items[0] if len(items) == 1 else items)
    sign_in(w, 'dana.k@test.com')
    search_open(w, 'NVDA', 'NVDA')
    add_watchlist(w)
    w.click('.nav-auth a[href="/watchlist"]', 'open watchlist page')
    syms = watchlist_symbols(w)
    w.read('watch_count', len(syms))
    return (f"{w.facts['match_count']} buyback articles; most recent: "
            f"{meta['title'][:70]} by {meta['publisher']}, author "
            f"{meta['author']}, buyback size {w.facts.get('buyback_size')}. "
            f"NVDA closed at {w.facts.get('nvda_close')}, "
            f"{w.facts.get('nvda_chg')}, trading volume "
            f"{w.facts.get('nvda_volume')} shares. Earnings topic only "
            f"article: {w.facts['earnings_only_title']}. Dana watches "
            f"{len(syms)} symbols.")


def task_09(w):
    w.start_home()
    sign_up(w, 'Priya Nair', 'priya.nair@test.com')
    search_open(w, 'Apple', 'AAPL')
    w.click('a.quote-tab:has-text("Financials")', 'Financials tab')
    rows = w.page.locator('table.yf tbody tr').all_inner_texts()
    last = rows[-1].split('\t')
    w.read('fy_end', last[0])
    w.read('revenue', last[1])
    w.read('net_income', last[5])
    w.click('a.quote-tab:has-text("Statistics")', 'Statistics tab')
    w.read('peg', stat_value(w, 'PEG Ratio (5Y expected)'))
    w.read('beta', stat_value(w, 'Beta (5Y Monthly)'))
    add_watchlist(w)
    w.click('a.quote-tab:has-text("Profile")', 'Profile tab')
    employees = w.page.locator('div.fact:has-text("Full Time Employees") .fact-value').inner_text()
    w.read('employees', employees)
    w.click('.nav-auth a[href="/watchlist"]', 'open watchlist page')
    syms = watchlist_symbols(w)
    w.read('watch_symbols', syms)
    nav(w, 'News')
    w.fill('#q', 'Apple', 'news search Apple')
    w.submit('form.filter-form button[type="submit"]', 'submit news search')
    items = news_rows(w)
    w.read('news_match_count', len(items))
    w.click('ul.news-list li.news-item:first-child a',
            'open most recent article')
    meta = article_meta(w)
    w.read('news_publisher', meta['publisher'])
    w.read('news_author', meta['author'])
    return (f"Apple FY end {last[0]}: revenue {last[1]}, net income "
            f"{last[5]}. PEG {w.facts['peg']}, beta {w.facts['beta']}, "
            f"employees {employees}. Watchlist: {', '.join(syms)}. "
            f"{len(items)} articles match Apple; the most recent is by "
            f"{meta['publisher']} with author {meta['author']}.")


def task_10(w):
    w.start_home()
    search_open(w, 'Coca-Cola', 'KO')
    w.click('a.quote-tab:has-text("Profile")', 'Profile tab')
    facts = w.page.locator('.fact').all_inner_texts()
    fd = {f.split('\n')[0]: f.split('\n')[1] for f in facts}
    w.read('sector', fd.get('Sector'))
    w.read('industry', fd.get('Industry'))
    w.read('employees', fd.get('Full Time Employees'))
    w.read('website', fd.get('Website'))
    w.click('a.quote-tab:has-text("Summary")', 'Summary tab')
    w.read('div_rate', grab(r'Forward Dividend & Yield\s*\n([^\n]+)', w.body(), 'div'))
    search_open(w, 'PepsiCo', 'PEP')
    w.click('a.quote-tab:has-text("Statistics")', 'Statistics tab')
    w.read('pep_margin', stat_value(w, 'Profit Margin'))
    w.read('pep_pe', stat_value(w, 'Trailing P/E'))
    sign_in(w, 'bob.c@test.com')
    create_alert(w, 'above', 100, 'Cola wars')
    rows = alert_rows(w)
    w.read('alert_status', [r[5] for r in rows if r[0] == 'PEP'][0])
    w.click('.nav-auth a[href="/watchlist"]', 'open watchlist page')
    syms = watchlist_symbols(w)
    w.read('watch_count', len(syms))
    return (f"KO: sector {fd.get('Sector')}, industry {fd.get('Industry')}, "
            f"employees {fd.get('Full Time Employees')}, website "
            f"{fd.get('Website')}, forward dividend {w.facts['div_rate']}. "
            f"PEP: margin {w.facts['pep_margin']}, P/E {w.facts['pep_pe']}. "
            f"PEP alert status {w.facts['alert_status']}; Bob watches "
            f"{len(syms)} symbols.")


def task_11(w):
    w.start_home()
    nav(w, 'Calendars')
    w.click('a:has-text("Next week")', 'go to next week')
    events = calendar_events(w)
    by_day = {}
    for e in events:
        by_day[e[3]] = by_day.get(e[3], 0) + 1
    best_day = max(by_day.items(), key=lambda kv: kv[1])
    w.read('next_week_best_day', best_day[0])
    w.read('next_week_best_count', best_day[1])
    w.click('a:has-text("This week")', 'back to this week')
    events = calendar_events(w)
    by_day = {}
    for e in events:
        by_day[e[3]] = by_day.get(e[3], 0) + 1
    best_day = max(by_day.items(), key=lambda kv: kv[1])
    w.read('this_week_best_day', best_day[0])
    w.read('this_week_best_count', best_day[1])
    search_open(w, 'Apple', 'AAPL')
    w.read('earnings_date', grab(r'Earnings Date\s*\n([^\n]+)', w.body(), 'earnings'))
    w.click('a.quote-tab:has-text("Statistics")', 'Statistics tab')
    w.read('target', stat_value(w, '1y Target Estimate'))
    w.read('day50', stat_value(w, '50-Day Average'))
    sign_in(w, 'dana.k@test.com')
    create_alert(w, 'above', 400, 'Earnings run')
    rows = alert_rows(w)
    w.read('new_alert_status', [r[5] for r in rows if r[0] == 'AAPL'][0])
    w.read('alert_total', len(rows))
    return (f"Next week busiest day {w.facts['next_week_best_day']} with "
            f"{w.facts['next_week_best_count']} events; this week busiest "
            f"{w.facts['this_week_best_day']} with "
            f"{w.facts['this_week_best_count']} events. Apple next earnings "
            f"{w.facts['earnings_date']}, 1y target {w.facts['target']}, "
            f"50-day average {w.facts['day50']}. "
            f"New alert {w.facts['new_alert_status']}; Dana has {len(rows)} "
            f"alerts.")


def task_12(w):
    w.start_home()
    sign_in(w, 'carol.d@test.com')
    w.click('.nav-auth a[href="/watchlist"]', 'open watchlist page')
    syms = watchlist_symbols(w)
    w.read('initial_symbols', syms)
    row = w.page.locator('table.yf tbody tr', has_text='UNH').first
    row.locator('button:has-text("Remove")').click()
    w.page.wait_for_load_state('networkidle')
    w.atomic += 1
    w._log('click', {'selector': 'UNH Remove'}, 'remove UNH from watchlist')
    search_open(w, 'Merck', 'MRK')
    w.read('pe_ttm', grab(r'PE Ratio \(TTM\)\s*\n([^\n]+)', w.body(), 'pe'))
    w.read('w52', grab(r'52 Week Range\s*\n([^\n]+)', w.body(), '52w'))
    add_watchlist(w)
    create_alert(w, 'above', 160, 'Pharma rotation')
    rows = alert_rows(w)
    w.read('new_alert_status', [r[5] for r in rows if r[0] == 'MRK'][0])
    w.click('.nav-auth a[href="/watchlist"]', 'open watchlist page')
    syms = watchlist_symbols(w)
    w.read('final_symbols', syms)
    return (f"Carol's watchlist was {w.facts['initial_symbols']}; after "
            f"removing UNH and adding MRK it is {syms}. MRK P/E "
            f"{w.facts['pe_ttm']}, 52w {w.facts['w52']}. New alert status "
            f"{w.facts['new_alert_status']}.")


def task_13(w):
    w.start_home()
    sign_in(w, 'alice.j@test.com')
    w.click('.nav-auth a[href="/alerts"]', 'open alerts page')
    rows = alert_rows(w)
    w.read('initial_alerts', rows)
    row = w.page.locator('table.yf tbody tr', has_text='TSLA').first
    row.locator('button:has-text("Delete")').click()
    w.page.wait_for_load_state('networkidle')
    w.atomic += 1
    w._log('click', {'selector': 'TSLA Delete'}, 'delete Tesla alert')
    search_open(w, 'Tesla', 'TSLA')
    create_alert(w, 'above', 900, 'Upside breakout')
    rows = alert_rows(w)
    w.read('new_alert_status', [r[5] for r in rows if r[0] == 'TSLA'][0])
    w.read('alert_count', len(rows))
    w.click('a[href="/quote/TSLA"]', 'open TSLA quote from alerts page')
    w.click('a.quote-tab:has-text("Statistics")', 'Statistics tab')
    w.read('day50', stat_value(w, '50-Day Average'))
    return (f"Alice's alerts were {w.facts['initial_alerts']}; after "
            f"deleting Tesla and creating a new TSLA above 900 alert "
            f"(status {w.facts['new_alert_status']}) she has {len(rows)} "
            f"alerts. Tesla 50-day average {w.facts['day50']}.")


def task_14(w):
    w.start_home()
    row = w.page.locator('div.mover-card:has(h3:text("Day Gainers")) tbody tr').first
    top_txt = row.inner_text()
    top_sym = top_txt.split('\t')[0].strip()
    w.read('day_gainer_top', top_txt.replace('\n', ' '))
    nav(w, 'Screener')
    w.select('#sector', 'Healthcare', 'filter sector Healthcare')
    w.fill('#mcap_min', '10000000000', 'market cap min 10B')
    w.fill('#mcap_max', '200000000000', 'market cap max 200B')
    w.select('#sort', 'change', 'sort by % change')
    w.submit('form.filter-form button[type="submit"]', 'apply custom filters')
    rows = w.page.locator('table.results-table tbody tr').all_inner_texts()
    for i, r in enumerate(rows[:3]):
        cells = r.split('\t')
        w.read(f'filtered{i+1}', f"{cells[0]} {cells[5]}")
    first = rows[0].split('\t')
    w.click(f'a[href="/quote/{first[0]}"]', 'open first filtered result')
    w.click('a.quote-tab:has-text("Statistics")', 'Statistics tab')
    w.read('w52_change', stat_value(w, '52-Week Change'))
    sign_in(w, 'bob.c@test.com')
    add_watchlist(w)
    w.click('.nav-auth a[href="/watchlist"]', 'open watchlist page')
    syms = watchlist_symbols(w)
    w.read('watch_symbols', syms)
    return (f"Home Day Gainers top: {top_txt.replace(chr(10), ' ')}. "
            f"Healthcare 10-200B by %chg: {w.facts['filtered1']}, "
            f"{w.facts['filtered2']}, {w.facts['filtered3']}. First result "
            f"{first[0]} 52-week change {w.facts['w52_change']}. Bob's "
            f"watchlist: {', '.join(syms)}.")


def task_15(w):
    w.start_home()
    w.fill('.search-form input[name="s"]', 'bitcoin', 'header search bitcoin')
    w.submit('.search-form button[type="submit"]', 'submit search')
    rows = w.page.locator('table.yf tbody tr').all_inner_texts()
    syms = [r.split('\t')[0].strip() for r in rows]
    w.read('btc_matches', syms)
    w.click('a[href="/quote/BTC-USD"]', 'open Bitcoin USD quote')
    body = w.body()
    m = re.search(r'\n([\d,]+\.\d\d)\s*\n[-+]', body)
    w.read('btc_price', m.group(1) if m else None)
    w.read('btc_mcap', grab(r'Market Cap\s*\n([^\n]+)', body, 'mcap'))
    w.read('btc_w52', grab(r'52 Week Range\s*\n([^\n]+)', body, '52w'))
    nav(w, 'News')
    w.fill('#q', 'stablecoin', 'news search stablecoin')
    w.submit('form.filter-form button[type="submit"]', 'submit news search')
    items = news_rows(w)
    w.read('match_count', len(items))
    w.click('ul.news-list li.news-item:first-child a',
            'open most recent article')
    meta = article_meta(w)
    w.read('title', meta['title'])
    w.read('publisher', meta['publisher'])
    w.read('author', meta['author'])
    body = w.body()
    m = re.search(r'([\w& ]+?), ([\w& ]+?), and ([\w& ]+?) '
                  r'handle reserves', body)
    w.read('custodians', [g.strip() for g in m.groups()] if m else None)
    sign_in(w, 'dana.k@test.com')
    w.fill('.search-form input[name="s"]', 'bitcoin', 'header search bitcoin')
    w.submit('.search-form button[type="submit"]', 'submit search')
    w.click('a[href="/quote/BTC-USD"]', 'open Bitcoin USD quote')
    add_watchlist(w)
    create_alert(w, 'above', 90000, 'ETF bid')
    rows = alert_rows(w)
    w.read('alert_status', [r[5] for r in rows if r[0] == 'BTC-USD'][0])
    w.click('.nav-auth a[href="/watchlist"]', 'open watchlist page')
    syms = watchlist_symbols(w)
    w.read('watch_count', len(syms))
    return (f"Bitcoin search matches {w.facts['btc_matches']}. BTC-USD price "
            f"{w.facts['btc_price']}, mcap {w.facts['btc_mcap']}, 52w "
            f"{w.facts['btc_w52']}. Stablecoin articles: {len(items)} "
            f"stablecoin article{'' if len(items) == 1 else 's'} matched; "
            f"the most recent is by {w.facts['publisher']} with author "
            f"{w.facts['author']}, and {', '.join(w.facts['custodians'])} "
            f"handle the stablecoin's reserves. Alert status "
            f"{w.facts['alert_status']}; Dana watches {len(syms)} "
            f"symbols.")


def task_16(w):
    w.start_home()
    nav(w, 'Markets')
    w.click('a[href="/sectors/healthcare"]', 'open Healthcare sector page')
    body = w.body()
    m = re.search(r'(\d+) captured companies', body)
    w.read('companies', m.group(1) if m else None)
    inds = industry_blocks(w)
    best_ind = max(inds, key=lambda t: t[1])
    w.read('top_industry', best_ind[0])
    w.read('top_industry_count', best_ind[1])
    comp_rows = w.page.locator('table.yf tbody tr').all_inner_texts()
    largest = comp_rows[0].split('\t')
    second = comp_rows[1].split('\t')
    w.read('largest', largest[0])
    w.read('second', second[0])
    w.click(f'a[href="/quote/{largest[0]}"]', 'open largest company')
    w.click('a.quote-tab:has-text("Statistics")', 'Statistics tab')
    w.read('largest_pe', stat_value(w, 'Trailing P/E'))
    w.read('largest_margin', stat_value(w, 'Profit Margin'))
    w.back('back to LLY summary')
    w.back('back to Healthcare sector page')
    w.click(f'a[href="/quote/{second[0]}"]', 'open second largest')
    w.click('a.quote-tab:has-text("Statistics")', 'Statistics tab')
    w.read('second_pe', stat_value(w, 'Trailing P/E'))
    w.read('second_margin', stat_value(w, 'Profit Margin'))
    sign_in(w, 'bob.c@test.com')
    add_watchlist(w)
    create_alert(w, 'above', 300, 'Dividend value')
    rows = alert_rows(w)
    w.read('alert_status', [r[5] for r in rows if r[0] == second[0]][0])
    w.click('.nav-auth a[href="/watchlist"]', 'open watchlist page')
    syms = watchlist_symbols(w)
    w.read('watch_count', len(syms))
    return (f"Healthcare has {w.facts['companies']} companies; biggest "
            f"industry {w.facts['top_industry']} with "
            f"{w.facts['top_industry_count']} companies. "
            f"Largest {largest[0]}: P/E {w.facts['largest_pe']}, margin "
            f"{w.facts['largest_margin']}. Second {second[0]}: P/E "
            f"{w.facts['second_pe']}, margin {w.facts['second_margin']}. "
            f"Alert {w.facts['alert_status']}; watchlist {len(syms)}.")


def task_17(w):
    w.start_home()
    search_open(w, 'Microsoft', 'MSFT')
    w.click('a.quote-tab:has-text("Historical Data")', 'Historical Data tab')
    rows = w.page.locator('table.yf tbody tr').all_inner_texts()
    w.read('last_close', rows[0].split('\t')[1])
    w.read('first_close', rows[-1].split('\t')[1])
    w.click('a.quote-tab:has-text("Statistics")', 'Statistics tab')
    w.read('day50', stat_value(w, '50-Day Average'))
    w.read('day200', stat_value(w, '200-Day Average'))
    sign_in(w, 'alice.j@test.com')
    w.click('.nav-auth a[href="/watchlist"]', 'open watchlist page')
    syms = watchlist_symbols(w)
    w.read('watch_count', len(syms))
    w.click('a[href="/quote/MSFT"]', 'open MSFT quote from watchlist')
    create_alert(w, 'above', 600, 'Azure wave')
    rows = alert_rows(w)
    w.read('new_alert_status', [r[5] for r in rows if r[0] == 'MSFT'][0])
    w.read('alert_total', len(rows))
    return (f"MSFT closes: {w.facts['last_close']} (latest) and "
            f"{w.facts['first_close']} (first). 50-day {w.facts['day50']}, "
            f"200-day {w.facts['day200']}. Alice watches {len(syms)} "
            f"symbols. New MSFT alert {w.facts['new_alert_status']}; Alice "
            f"has {len(rows)} alerts.")


def task_18(w):
    w.start_home()
    nav(w, 'News')
    w.fill('#q', 'inflation', 'news search inflation')
    w.submit('form.filter-form button[type="submit"]', 'submit news search')
    items = news_rows(w)
    w.read('match_count', len(items))
    w.click('ul.news-list li.news-item:first-child a', 'open most recent article')
    meta = article_meta(w)
    w.read('publisher', meta['publisher'])
    w.read('author', meta['author'])
    w.fill('.search-form input[name="s"]', 'gold', 'header search gold')
    w.submit('.search-form button[type="submit"]', 'submit search')
    w.click('a[href="/quote/GC%3DF"], a[href="/quote/GC=F"]', 'open Gold futures quote')
    body = w.body()
    m = re.search(r'\n([\d,]+\.\d\d)\s*\n[-+]', body)
    w.read('gold_price', m.group(1) if m else None)
    m = re.search(r'\n[-+][\d.]+ \(([-+][\d.]+%)\)', body)
    w.read('gold_chg', m.group(1) if m else None)
    sign_in(w, 'carol.d@test.com')
    add_watchlist(w)
    create_alert(w, 'above', 4300, 'Rally hedge')
    rows = alert_rows(w)
    w.read('alert_status', [r[5] for r in rows if r[0] == 'GC=F'][0])
    w.click('.nav-auth a[href="/watchlist"]', 'open watchlist page')
    syms = watchlist_symbols(w)
    w.read('watch_count', len(syms))
    return (f"{len(items)} inflation articles; publisher "
            f"{w.facts['publisher']}, author {w.facts['author']}. Gold price "
            f"{w.facts['gold_price']} ({w.facts['gold_chg']}). Alert status "
            f"{w.facts['alert_status']}; Carol watches {len(syms)} symbols.")


def task_19(w):
    w.start_home()
    nav(w, 'Screener')
    w.select('#sector', 'Utilities', 'filter sector Utilities')
    w.fill('#yield_min', '4', 'dividend yield min 4')
    w.select('#sort', 'yield', 'sort by dividend yield')
    w.submit('form.filter-form button[type="submit"]', 'apply custom filters')
    rows = w.page.locator('table.results-table tbody tr').all_inner_texts()
    for i, r in enumerate(rows[:3]):
        cells = r.split('\t')
        w.read(f'util{i+1}', f"{cells[0]} {cells[8]}")
    third = rows[2].split('\t')
    w.click(f'a[href="/quote/{third[0]}"]', 'open third result quote')
    body = w.body()
    w.read('div_yield', grab(r'Forward Dividend & Yield\s*\n([^\n]+)', body, 'yield'))
    w.read('mcap', grab(r'Market Cap\s*\n([^\n]+)', body, 'mcap'))
    w.read('earnings_date', grab(r'Earnings Date\s*\n([^\n]+)', body, 'earnings'))
    sign_in(w, 'dana.k@test.com')
    add_watchlist(w)
    w.click('.nav-auth a[href="/alerts"]', 'open alerts page')
    row = w.page.locator('table.yf tbody tr', has_text='META').first
    row.locator('button:has-text("Delete")').click()
    w.page.wait_for_load_state('networkidle')
    w.atomic += 1
    w._log('click', {'selector': 'META Delete'}, 'delete META alert')
    rows = alert_rows(w)
    w.read('alerts_remaining', len(rows))
    w.click('.nav-auth a[href="/watchlist"]', 'open watchlist page')
    syms = watchlist_symbols(w)
    w.read('watch_count', len(syms))
    return (f"Utilities yield>=4 desc: {w.facts['util1']}, {w.facts['util2']}, "
            f"{w.facts['util3']}. Third result {third[0]}: yield "
            f"{w.facts['div_yield']}, mcap {w.facts['mcap']}, next earnings "
            f"{w.facts['earnings_date']}. Dana has {len(rows)} alerts left "
            f"and {len(syms)} watchlist symbols.")


TASK_FUNCS = [task_00, task_01, task_02, task_03, task_04, task_05, task_06,
              task_07, task_08, task_09, task_10, task_11, task_12, task_13,
              task_14, task_15, task_16, task_17, task_18, task_19]


def run_one(index, round_name):
    task_id = TASKS and list(TASKS.keys())[index]
    out = EV / round_name / f'task_{index:02d}'
    if out.exists():
        subprocess.run(['rm', '-rf', str(out)], check=True)
    out.mkdir(parents=True, exist_ok=True)
    reset_site()
    snapshot_db(out / 'initial.db')
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
        page = ctx.new_page()
        w = Walk(page, task_id, out)
        try:
            answer = TASK_FUNCS[index](w)
            w.save(answer)
        finally:
            snapshot_db(out / 'after.db')
            browser.close()
    return w, answer


def main():
    round_name = sys.argv[1] if len(sys.argv) > 1 else 'round1'
    indexes = [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 \
        else list(range(20))
    summary = {}
    for i in indexes:
        task_id = list(TASKS.keys())[i]
        print(f'=== {task_id} ({round_name})', flush=True)
        w, answer = run_one(i, round_name)
        summary[task_id] = {'steps': w.atomic, 'facts': w.facts}
        print(f'--- {task_id}: {w.atomic} atomic actions\n', flush=True)
    out = EV / f'summary_{round_name}.json'
    out.write_text(json.dumps(summary, indent=1, default=str))
    print(json.dumps({k: v['steps'] for k, v in summary.items()}, indent=1))


if __name__ == '__main__':
    main()
