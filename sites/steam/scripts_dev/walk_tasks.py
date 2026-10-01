#!/usr/bin/env python3
"""End-to-end walkthrough: drive every task's honest path in a real
headless Chromium against a fresh local server, emit a browser run
(trajectory + screenshots + initial and after database snapshots),
grade it with the site's own verify_N.py contract, and assert the
verifier passes. Runs two independent rounds.

This proves the task set is solvable end to end in a real browser and
that the reviewer contract matches the honest-path evidence exactly.

Run:  python3 scripts_dev/walk_tasks.py [--rounds 2] [--only 0,1,...]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE))

EXPECTED = json.loads(
    (SITE / 'scraped_data' / 'expected_answers.json').read_text(encoding='utf-8'))
TASKS = [json.loads(line) for line in
         (SITE / 'tasks.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


class Server:
    """A fresh steam mirror serving a fresh database on an ephemeral port."""

    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix='steam-walk-', dir='/tmp'))
        self.db = self.root / 'steam.db'
        env = dict(os.environ)
        env['STEAM_DB_URI'] = f'sqlite:///{self.db}'
        env['PORT'] = str(free_port())
        self.port = int(env['PORT'])
        self.proc = subprocess.Popen(
            [sys.executable, '-m', 'app'], cwd=str(SITE), env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.base = f'http://127.0.0.1:{self.port}'
        for _ in range(60):
            try:
                with socket.create_connection(('127.0.0.1', self.port), timeout=1):
                    return
            except OSError:
                time.sleep(0.3)
        raise RuntimeError('server did not come up')

    def stop(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        shutil.rmtree(self.root, ignore_errors=True)


class Walk:
    """One task's honest browser session with atomic-action accounting."""

    def __init__(self, page, task_id, out_dir):
        self.page = page
        self.task_id = task_id
        self.out = Path(out_dir)
        (self.out / 'screenshots').mkdir(parents=True, exist_ok=True)
        self.steps = []
        self.atomic = 0
        self._shot = 0

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
                self.page.wait_for_timeout(400)
        self._shot += 1
        return p.name

    def _log(self, action, params, desc):
        url = params.get('url') or self.page.url
        rec = {'step': len(self.steps), 'url': url,
               'title': self.page.title(), 'thought': desc, 'action': action,
               'params': params,
               'observed_text': (self.page.inner_text('body') or '')[:4000],
               'screenshot_before': self._shoot()}
        self.steps.append(rec)

    def _after(self):
        try:
            self.page.wait_for_load_state('networkidle', timeout=8000)
        except Exception:
            pass
        self.page.wait_for_timeout(200)
        self.steps[-1]['screenshot_after'] = self._shoot()
        self.steps[-1]['url_after'] = self.page.url

    # ------------------------------------------------------------ actions --
    def start_home(self, base):
        self.page.goto(base + '/', timeout=45000, wait_until='load')
        self._log('navigate', {'url': base + '/'}, 'open store home (start_url)')
        self.page.reload(timeout=45000)
        self._after()
        # the initial home load is the benchmark start; not counted
        # (audit-trail standard, same as validate_tasks.py)

    def goto(self, base, path, desc):
        self._log('navigate', {'url': base + path}, desc)
        self.page.goto(base + path, timeout=30000, wait_until='load')
        self._after()
        self.atomic += 1

    def click_link(self, text, desc, exact=True):
        pattern = (r'^' + re.escape(text) + r'$') if exact else re.escape(text)
        loc = self.page.get_by_role('link', name=re.compile(pattern, re.I))
        href = None
        try:
            raw = self.page.evaluate(
                'el => el.getAttribute("href")',
                loc.first.element_handle(timeout=5000))
            if raw:
                href = urljoin(self.page.url, raw)
        except Exception:
            pass
        params = {'text': text}
        if href:
            params['url'] = href
        self._log('click', params, desc)
        loc.first.click(timeout=45000)
        self._after()
        self.atomic += 1

    def click_button(self, text, desc):
        loc = self.page.get_by_role('button', name=re.compile(re.escape(text), re.I))
        form_action = None
        try:
            handle = loc.first.element_handle(timeout=5000)
            form_action = self.page.evaluate(
                'el => el.form ? (el.form.action || el.form.getAttribute("action")) : null',
                handle)
        except Exception:
            pass
        params = {'text': text}
        if form_action:
            params['url'] = form_action
        self._log('click', params, desc)
        loc.first.click(timeout=45000)
        self._after()
        self.atomic += 1

    def fill(self, sel, value, desc):
        self._log('fill', {'selector': sel, 'value': value}, desc)
        self.page.fill(sel, value, timeout=10000)
        self._after()
        self.atomic += 1

    def select(self, sel, value, desc):
        self._log('select', {'selector': sel, 'value': str(value)}, desc)
        self.page.select_option(sel, str(value), timeout=10000)
        self._after()
        self.atomic += 1

    def select_label(self, sel, needle, desc):
        opts = self.page.eval_on_selector_all(
            f'{sel} option', 'els => els.map(e => [e.value, e.textContent])')
        for value, label in opts:
            if needle.casefold() in (label or '').casefold() and value:
                self._log('select', {'selector': sel, 'value': value,
                                     'label': label}, desc)
                self.page.select_option(sel, value, timeout=10000)
                self._after()
                self.atomic += 1
                return label
        raise AssertionError(f'no option containing {needle!r}')

    def apply(self, desc='apply filters'):
        self.click_button('Apply', desc)

    def login(self, email, password):
        self.click_link('Sign in', 'open the sign-in page')
        self.fill('input[name=email]', email, 'fill email')
        self.fill('input[name=password]', password, 'fill password')
        self.click_button('Sign in', 'submit sign-in')

    def text(self):
        return self.page.inner_text('body') or ''


# --------------------------------------------------------------------------
# answer templates
# --------------------------------------------------------------------------

def answer_for(task_id):
    a = EXPECTED[task_id]
    T = {
        'Steam--0': ("The search for RPGs under $20 returns {rpg_count} games; "
                     "{on_sale} of them are on sale. The cheapest is {cheapest_name} "
                     "at {cheapest_price}, rated {review_desc}, released "
                     "{release_date} with {total_reviews} user reviews. "
                     "Alice's wishlist now shows {wishlist} items."),
        'Steam--1': ("The Linux + discounted filter returns {count} games. The most "
                     "expensive is {expensive_name} at {expensive_price} "
                     "(-{expensive_discount}%), rated {review_desc}; its Windows "
                     "minimum OS is {min_os}. In total the store has "
                     "{all_specials} discounted games. Bob's wishlist now shows "
                     "{wishlist} items."),
        'Steam--2': ("Counter-Strike 2 needs {cs2_ram} and Dota 2 needs "
                     "{dota_ram}, so {more_ram} requires more RAM. CS2 was released "
                     "{cs2_release} and is rated {cs2_review}. Dota 2 shows "
                     "{positive_shown} positive reviews; the most recent is by "
                     "{recent_positive_author}. Bob's wishlist now shows "
                     "{wishlist} items."),
        'Steam--3': ("Removed {removed} from the wishlist. Hades II costs "
                     "{hades2_price} at -{hades2_discount}% (released "
                     "{hades2_release}). The cheapest Casual game under $10 is "
                     "{cheap_name} at {cheap_price}. Carol's wishlist now has "
                     "{wishlist} items: {remaining}."),
        'Steam--4': ("The Portal Bundle costs {bundle_price}. With ELDEN RING x2 the "
                     "cart subtotal is {subtotal}. Order {order_no} was placed "
                     "for a total of {total}."),
        'Steam--5': ("The Specials page lists {specials_count} discounted games. The "
                     "two biggest discounts: {top1_name} -{top1_discount}% from "
                     "{top1_original} to {top1_final} (saves {top1_savings}); "
                     "and Tom Clancy's The Division 2 -{top2_discount}% from "
                     "{top2_original} to {top2_final} (saves {top2_savings}). "
                     "{top1_name} is rated {review_desc}, released "
                     "{release_date}. {indie_sale} indie games are on sale and "
                     "{mac_sale} specials support macOS. The cheapest special is "
                     "{cheapest_special} at {cheapest_price}; the most expensive "
                     "is {expensive_special} at {expensive_price} rated "
                     "{expensive_review}. Carol's wishlist now shows {wishlist} items."),
        'Steam--6': ("Stellaris is rated {review_desc} with {total_reviews} total "
                     "reviews. It has {negative_count} negative reviews shown; the most "
                     "recent is by {recent_author} with {recent_playtime} hours, and "
                     "the most helpful negative review is by {helpful_author}. Stellaris "
                     "costs {price} at -{discount}%; its newest news post is "
                     "\"{newest_news}\". Bob's wishlist now shows {wishlist} items."),
        'Steam--7': ("Valve's developer page lists {valve_count} games. The most "
                     "expensive is {most_expensive} at {most_expensive_price}, "
                     "released {alyx_release} and rated {alyx_review}. The "
                     "{free_count} free-to-play games are {free_games}: "
                     "Counter-Strike 2 was released {cs2_release} and is rated "
                     "{cs2_review}; Dota 2 was released {dota_release} and is "
                     "rated {dota_review}; Team Fortress 2 was released "
                     "{tf2_release} and is rated {tf2_review}. The publisher "
                     "page lists {publisher_count} games. Dana's wishlist now "
                     "shows {wishlist} items."),
        'Steam--8': ("Counter-Strike 2's newest news post is \"{cs2_news_title}\" "
                     "(feed: {cs2_news_feed}), posted {cs2_news_date}. Dota 2's newest "
                     "is \"{dota_news_title}\" posted {dota_news_date}, so "
                     "{more_recent}'s post is more recent. CS2 is {cs2_price} and "
                     "rated {cs2_review}. Carol's wishlist now shows {wishlist} items."),
        'Steam--9': ("The Portal Bundle costs {bundle_price}; its items bought "
                     "separately cost {separate_total}, so the savings are {savings}. "
                     "The cart subtotal was {subtotal}. Order {order_no} was placed "
                     "for {total} and lists {line_item} as a line item."),
        'Steam--10': ("There are {free_count} free games. The first free Action game is "
                     "{game}, rated {review_desc} with {total_reviews} reviews. "
                     "Frank's wishlist shows {wishlist} item and it persisted after "
                     "signing out and back in: {persisted}."),
        'Steam--11': ("The Indie page lists {indie_count} games. The newest is "
                      "{newest_name} at {newest_price} ({review_desc}; "
                      "{discounted}); its reviews page shows "
                      "{newest_reviews_desc}. The most expensive is "
                      "{most_expensive} at {most_expensive_price} "
                      "(released {shovel_release}). {under15} indie games are "
                      "under $15. Dana's wishlist now shows {wishlist} items."),
        'Steam--12': ("Alice's existing order is {existing_order} totaling "
                      "{existing_total}. The new order is {new_order} totaling "
                      "{new_total}; Alice now has {order_count} orders in total."),
        'Steam--13': ("{count} Action games have Mixed reviews: {names}. The cheaper "
                      "one is {cheap_name} at {cheap_price}; it needs {min_os}, "
                      "{min_cpu} and {min_ram}, and has "
                      "{total_reviews} reviews ({cheap_pct}% positive). The more "
                      "expensive one, {exp_name} at {exp_price}, needs "
                      "{exp_min_ram}. Alice's wishlist now shows {wishlist} items."),
        'Steam--14': ("There are {free_count} free games. Dota 2 is {dota_review} "
                      "({dota_pct}% of {dota_total} reviews); Counter-Strike 2 is "
                      "{cs2_review} ({cs2_pct}% of {cs2_total}); Team Fortress 2 "
                      "is {tf2_review}. {higher} has the higher positive percentage. "
                      "Dana's wishlist now shows {wishlist} items."),
        'Steam--15': ("Dead Cells has {dlc_count} DLC items; the first is {first_dlc} "
                      "at {first_dlc_price} (released {dlc_release}); adding it made "
                      "the cart subtotal {dlc_subtotal}. Dead Cells itself is "
                      "{dc_price} ({dc_discount}). The bundle "
                      "\"{bundle_name}\" costs {bundle_price} with "
                      "{bundle_items} items; the cart subtotal was {subtotal}, then "
                      "the cart was {cart_after}. Three copies of Dead Cells total "
                      "{triple_total}. The second bundle is {second_bundle} at "
                      "{second_bundle_price}."),
        'Steam--16': ("The resident search returns {count} games: {names}; with the "
                      "Action filter {refined} remain. Resident Evil 2 costs "
                      "{re2_price} (released {re2_release}); Resident Evil Village "
                      "costs {village_price} (released {village_release}); Resident "
                      "Evil 4 costs {re4_price} (released {re4_release}), so "
                      "{most_recent} released most recently. Its reviews are "
                      "{re4_review} and its newest news post is \"{re4_news}\". "
                      "Carol's wishlist now shows {wishlist} items."),
        'Steam--17': ("The hades search returns {count} games. Hades costs "
                      "{hades_price} at -{hades_discount}% (normally "
                      "{hades_original}, released {hades_release}, rated "
                      "{hades_review}); Hades II costs {hades2_price} at "
                      "-{hades2_discount}% (normally {hades2_original}, released "
                      "{hades2_release}, rated {hades2_review}). {cheaper} is "
                      "cheaper; both support macOS: {both_mac}. The most recent positive "
                      "Hades II review is by {recent_positive_author}. The cart subtotal "
                      "with Hades was {cart_subtotal}. Alice's wishlist now shows "
                      "{wishlist} items."),
        'Steam--18': ("FINAL FANTASY VII REMAKE INTERGRADE is -{ff7_discount}% from "
                      "{ff7_original} to {ff7_final} (saves {ff7_savings}); "
                      "Hades is -{hades_discount}% from {hades_original} to "
                      "{hades_final} (saves {hades_savings}). The subtotal was "
                      "{subtotal}. Order {order_no} was placed for {total} "
                      "with line items {items}."),
        'Steam--19': ("Cyberpunk 2077 needs {cp_min_ram} minimum RAM and "
                      "{cp_rec_ram} recommended, with a {cp_gpu} graphics card and "
                      "{cp_storage} storage. ELDEN RING needs {er_min_ram} minimum "
                      "and {er_rec_ram} recommended, with {er_gpu} and "
                      "{er_storage}. {more_storage} needs more storage; "
                      "{mac_game} supports macOS. ELDEN RING costs {er_price} and is "
                      "rated {er_review}. Cyberpunk's reviews are {cp_review} with "
                      "{cp_shown} shown. The cart subtotal was {cart_subtotal}. "
                      "Dana's wishlist now shows {wishlist} items."),
    }
    return T[task_id].format(**a)


# --------------------------------------------------------------------------
# per-task browser paths (mirror of validate_tasks.py, in real Chromium)
# --------------------------------------------------------------------------

def browse_0(w, base):
    w.start_home(base)
    w.click_link('Search', 'open the search page')
    w.select('select[name=genre]', 'RPG', 'select RPG genre')
    w.select('select[name=maxprice]', '20', 'select under $20')
    w.apply('apply the filters')
    w.page.check('input[name=specials]', timeout=8000)
    w._log('check', {'name': 'specials'}, 'tick discounted-only')
    w._after()
    w.atomic += 1
    w.apply('apply the discounted filter')
    w.page.uncheck('input[name=specials]', timeout=8000)
    w._log('uncheck', {'name': 'specials'}, 'clear discounted-only')
    w._after()
    w.atomic += 1
    w.select('select[name=sort]', 'Price_ASC', 'sort by price ascending')
    w.apply('apply the sort')
    w.click_link('Black Desert', 'open the cheapest RPG')
    w.login('alice.j@test.com', 'TestPass123!')
    w.goto(base, '/app/582660/', 'reopen Black Desert page')
    w.click_button('Add to Wishlist', 'add to wishlist')
    w.click_link('Wishlist', 'open the wishlist')


def browse_1(w, base):
    w.start_home(base)
    w.click_link('Search', 'open the search page')
    w.select('select[name=os]', 'linux', 'filter to Linux')
    w.page.check('input[name=specials]', timeout=8000)
    w._log('check', {'name': 'specials'}, 'tick discounted-only')
    w._after()
    w.atomic += 1
    w.apply('apply the filters')
    w.select('select[name=sort]', 'Price_DESC', 'sort by price descending')
    w.apply('apply the sort')
    w.click_link('Stellaris', 'open the most expensive result')
    w.goto(base, '/search/', 'reopen the search page')
    w.page.check('input[name=specials]', timeout=8000)
    w._log('check', {'name': 'specials'}, 'tick discounted-only')
    w._after()
    w.atomic += 1
    w.apply('apply to count all discounted games')
    w.login('bob.s@test.com', 'TestPass123!')
    w.goto(base, '/app/281990/', 'reopen Stellaris page')
    w.click_button('Add to Wishlist', 'add to wishlist')
    w.click_link('Wishlist', 'open the wishlist')


def browse_2(w, base):
    w.start_home(base)
    w.click_link('Search', 'open the search page')
    w.fill('input[name=term]', 'counter-strike', 'search counter-strike')
    w.apply('apply the search')
    w.click_link('Counter-Strike 2', 'open Counter-Strike 2')
    w.goto(base, '/search/', 'reopen the search page')
    w.fill('input[name=term]', 'dota', 'search dota')
    w.apply('apply the search')
    w.click_link('Dota 2', 'open Dota 2')
    w.goto(base, '/app/570/reviews/', 'open Dota 2 reviews')
    w.select('select[name=filter]', 'positive', 'filter positive')
    w.apply('apply the review filter')
    w.login('bob.s@test.com', 'TestPass123!')
    w.goto(base, '/app/570/', 'open Dota 2 page')
    w.click_button('Add to Wishlist', 'add Dota 2 to wishlist')
    w.goto(base, '/app/730/', 'open CS2 page')
    w.click_button('Add to Wishlist', 'add CS2 to wishlist')
    w.click_link('Wishlist', 'open the wishlist')


def browse_3(w, base):
    w.start_home(base)
    w.login('carol.m@test.com', 'TestPass123!')
    w.click_link('Wishlist', 'open the wishlist')
    row = w.page.locator('.row', has_text='Terraria').first
    row.scroll_into_view_if_needed(timeout=45000)
    w._log('click', {'text': 'Remove'}, 'remove Terraria')
    row.get_by_role('button', name='Remove').click(timeout=10000)
    w._after()
    w.atomic += 1
    w.goto(base, '/search/?term=hades+ii', 'search Hades II')
    w.click_link('Hades II', 'open Hades II')
    w.click_button('Add to Wishlist', 'add Hades II to wishlist')
    w.goto(base, '/search/?genre=Casual&maxprice=10&sort=Price_ASC',
           'cheapest Casual under $10')
    w.click_link('Vampire Survivors', 'open Vampire Survivors')
    w.click_button('Add to Wishlist', 'add to wishlist')


def browse_4(w, base):
    w.start_home(base)
    w.goto(base, '/search/?term=elden+ring', 'search ELDEN RING')
    w.click_link('ELDEN RING', 'open ELDEN RING')
    w.click_button('Add to Cart', 'add ELDEN RING to cart')
    w.goto(base, '/search/?term=portal', 'search portal')
    w.click_link('Portal 2', 'open Portal 2')
    w.click_link('Portal Bundle', 'open the Portal Bundle')
    w.click_button('Add bundle to Cart', 'add the bundle')
    w.click_link('Cart', 'open the cart')
    row = w.page.locator('tr', has_text='ELDEN RING').first
    row.scroll_into_view_if_needed(timeout=45000)
    w._log('select', {'name': 'qty'}, 'set ELDEN RING quantity to 2')
    row.locator('select[name=qty]').select_option('2', timeout=10000)
    w._after()
    w.atomic += 1
    w._log('click', {'text': 'Update'}, 'update quantity')
    row.get_by_role('button', name='Update').click(timeout=10000)
    w._after()
    w.atomic += 1
    w.login('bob.s@test.com', 'TestPass123!')
    w.click_link('checkout', 'continue to checkout', exact=False)
    w.fill('input[name=full_name]', 'Bob Smith', 'fill name')
    w.fill('input[name=email]', 'bob.s@test.com', 'fill email')
    w.fill('input[name=address1]', '7 Coast Road', 'fill address')
    w.fill('input[name=city]', 'Austin', 'fill city')
    w.fill('input[name=state]', 'TX', 'fill state')
    w.fill('input[name=zipcode]', '78701', 'fill zip')
    w.select('select[name=payment_method]', 'Mastercard', 'pick payment')
    w.click_button('Place order', 'place the order')


def browse_5(w, base):
    w.start_home(base)
    w.click_link('Specials', 'open the specials page')
    w.click_link('Black Desert', 'open the biggest-discount cheaper game')
    w.click_link('Specials', 'reopen the specials page')
    w.select('select[name=genre]', 'Indie', 'filter specials to Indie')
    w.apply('apply the indie filter')
    w.select('select[name=genre]', '', 'clear the genre filter')
    w.select('select[name=os]', 'mac', 'filter specials to macOS')
    w.apply('apply the mac filter')
    w.select('select[name=os]', '', 'clear the os filter')
    w.select('select[name=sort]', 'Price_ASC', 'sort specials by price')
    w.apply('apply the price sort')
    w.select('select[name=sort]', 'Price_DESC', 'sort specials by price desc')
    w.apply('apply the price sort')
    w.click_link('Jurassic World Evolution 3', 'open the most expensive special')
    w.login('carol.m@test.com', 'TestPass123!')
    w.goto(base, '/app/582660/', 'reopen Black Desert')
    w.click_button('Add to Wishlist', 'add to wishlist')
    w.click_link('Wishlist', 'open the wishlist')


def browse_6(w, base):
    w.start_home(base)
    w.goto(base, '/search/?term=stellaris', 'search Stellaris')
    w.click_link('Stellaris', 'open Stellaris')
    w.click_link('Read reviews', 'open the reviews page', exact=False)
    w.select('select[name=filter]', 'negative', 'filter negative')
    w.apply('apply the review filter')
    w.select('select[name=sort]', 'helpful', 'sort by helpful')
    w.apply('apply the review sort')
    w.click_link('Stellaris', 'back to the game page')
    w.click_link('All news for this game', 'open Stellaris news', exact=False)
    w.login('bob.s@test.com', 'TestPass123!')
    w.goto(base, '/app/281990/', 'reopen Stellaris')
    w.click_button('Add to Wishlist', 'add to wishlist')
    w.click_link('Wishlist', 'open the wishlist')


def browse_7(w, base):
    w.start_home(base)
    w.goto(base, '/search/?term=counter-strike', 'search Counter-Strike 2')
    w.click_link('Counter-Strike 2', 'open Counter-Strike 2')
    w.click_link('Valve', 'open Valve developer page')
    w.click_link('Dota 2', 'open Dota 2, the first free game')
    w.goto(base, '/app/440/', 'open Team Fortress 2, the second free game')
    w.goto(base, '/app/546560/', 'open the most expensive game, Half-Life: Alyx')
    w.click_button('Add to Cart', 'add it to the cart')
    w.page.get_by_role('button', name='Remove').first.click(timeout=10000)
    w._log('click', {'text': 'Remove'}, 'remove it from the cart')
    w._after()
    w.atomic += 1
    w.goto(base, '/publisher/valve/', 'open Valve publisher page')
    w.login('dana.k@test.com', 'TestPass123!')
    w.goto(base, '/app/546560/', 'reopen Half-Life: Alyx')
    w.click_button('Add to Wishlist', 'add to wishlist')
    w.click_link('Wishlist', 'open the wishlist')


def browse_8(w, base):
    w.start_home(base)
    w.goto(base, '/search/?term=counter-strike', 'search Counter-Strike 2')
    w.click_link('Counter-Strike 2', 'open Counter-Strike 2')
    w.click_link('All news for this game', 'open CS2 news', exact=False)
    w.click_link('Counter-Strike 2 Update', 'open the newest post')
    w.goto(base, '/search/?term=dota', 'search Dota 2')
    w.click_link('Dota 2', 'open Dota 2')
    w.click_link('All news for this game', 'open Dota 2 news', exact=False)
    w.goto(base, '/app/730/', 'reopen CS2 store page')
    w.login('carol.m@test.com', 'TestPass123!')
    w.goto(base, '/app/570/', 'open Dota 2 page')
    w.click_button('Add to Wishlist', 'add Dota 2 to wishlist')
    w.click_link('Wishlist', 'open the wishlist')


def browse_9(w, base):
    w.start_home(base)
    w.goto(base, '/search/?term=portal', 'search portal')
    w.click_link('Portal 2', 'open Portal 2')
    w.click_link('Portal Bundle', 'open the Portal Bundle')
    w.click_button('Add bundle to Cart', 'add the bundle')
    w.click_link('Cart', 'open the cart')
    w.login('alice.j@test.com', 'TestPass123!')
    w.click_link('checkout', 'continue to checkout', exact=False)
    w.fill('input[name=full_name]', 'Alice Johnson', 'fill name')
    w.fill('input[name=email]', 'alice.j@test.com', 'fill email')
    w.fill('input[name=address1]', '42 Pipeline Way', 'fill address')
    w.fill('input[name=city]', 'Bellevue', 'fill city')
    w.fill('input[name=state]', 'WA', 'fill state')
    w.fill('input[name=zipcode]', '98004', 'fill zip')
    w.select('select[name=payment_method]', 'Visa', 'pick payment')
    w.click_button('Place order', 'place the order')


def browse_10(w, base):
    w.start_home(base)
    w.click_link('Sign in', 'open sign-in page')
    w.click_link('Create a free account', 'open signup')
    w.fill('input[name=name]', 'Frank Nova', 'fill name')
    w.fill('input[name=email]', 'frank.n@test.com', 'fill email')
    w.fill('input[name=password]', 'Ocean2026!', 'fill password')
    w.click_button('Create account', 'submit signup')
    w.click_link('Search', 'open the search page')
    w.select('select[name=maxprice]', 'free', 'filter to free games')
    w.apply('apply the free filter')
    w.select('select[name=genre]', 'Action', 'filter to Action games')
    w.select('select[name=sort]', 'Price_ASC', 'sort by price')
    w.apply('apply the filters')
    w.click_link('Team Fortress 2', 'open Team Fortress 2')
    w.click_button('Add to Wishlist', 'add to wishlist')
    w.click_link('Wishlist', 'open the wishlist')
    w.click_link('Sign out', 'sign out')
    w.login('frank.n@test.com', 'Ocean2026!')
    w.click_link('Wishlist', 'reopen the wishlist')


def browse_11(w, base):
    w.start_home(base)
    w.click_link('Indie', 'open the Indie genre page')
    w.select('select[name=sort]', 'Released_DESC', 'sort by release date')
    w.apply('apply the release sort')
    w.select('select[name=sort]', 'Price_DESC', 'sort by price high to low')
    w.apply('apply the price sort')
    w.click_link('Shovel Knight: Treasure Trove', 'open the most expensive')
    w.goto(base, '/genre/indie/', 'reopen the Indie genre page')
    w.select('select[name=maxprice]', '15', 'filter indie under $15')
    w.apply('apply the price filter')
    w.goto(base, '/app/1867240/', 'open WARDOGS, the newest game')
    w.click_link('Read reviews', 'open WARDOGS reviews', exact=False)
    w.login('dana.k@test.com', 'TestPass123!')
    w.goto(base, '/app/1867240/', 'reopen WARDOGS')
    w.click_button('Add to Wishlist', 'add to wishlist')
    w.click_link('Wishlist', 'open the wishlist')


def browse_12(w, base):
    w.start_home(base)
    w.login('alice.j@test.com', 'TestPass123!')
    w.goto(base, '/account/', 'open the account page')
    w.goto(base, '/search/?term=left+4+dead+2', 'search Left 4 Dead 2')
    w.click_link('Left 4 Dead 2', 'open Left 4 Dead 2')
    w.click_button('Add to Cart', 'add to cart')
    w.click_link('Cart', 'open the cart')
    w.click_link('checkout', 'continue to checkout', exact=False)
    w.fill('input[name=full_name]', 'Alice Johnson', 'fill name')
    w.fill('input[name=email]', 'alice.j@test.com', 'fill email')
    w.fill('input[name=address1]', '42 Pipeline Way', 'fill address')
    w.fill('input[name=city]', 'Bellevue', 'fill city')
    w.fill('input[name=state]', 'WA', 'fill state')
    w.fill('input[name=zipcode]', '98004', 'fill zip')
    w.select('select[name=payment_method]', 'Visa', 'pick payment')
    w.click_button('Place order', 'place the order')
    w.goto(base, '/account/', 'reopen the account page')


def browse_13(w, base):
    w.start_home(base)
    w.click_link('Search', 'open the search page')
    w.select('select[name=genre]', 'Action', 'select Action genre')
    w.select('select[name=review_type]', 'mixed', 'select Mixed reviews')
    w.apply('apply the filters')
    w.select('select[name=sort]', 'Price_ASC', 'sort by price')
    w.apply('apply the sort')
    w.click_link('Minecraft Dungeons II', 'open the cheaper one')
    w.click_link('Read reviews', 'open its reviews', exact=False)
    w.goto(base, '/app/2246340/', 'open the more expensive one')
    w.login('alice.j@test.com', 'TestPass123!')
    w.goto(base, '/app/1912410/', 'reopen the cheaper game')
    w.click_button('Add to Wishlist', 'add to wishlist')
    w.click_link('Wishlist', 'open the wishlist')


def browse_14(w, base):
    w.start_home(base)
    w.click_link('Search', 'open the search page')
    w.select('select[name=maxprice]', 'free', 'filter to free games')
    w.apply('apply the free filter')
    w.fill('input[name=term]', 'dota', 'search Dota 2')
    w.apply('apply the search')
    w.click_link('Dota 2', 'open Dota 2')
    w.goto(base, '/search/', 'reopen the search page')
    w.fill('input[name=term]', 'counter-strike', 'search CS2')
    w.apply('apply the search')
    w.click_link('Counter-Strike 2', 'open CS2')
    w.goto(base, '/search/', 'reopen the search page')
    w.fill('input[name=term]', 'team fortress', 'search Team Fortress 2')
    w.apply('apply the search')
    w.click_link('Team Fortress 2', 'open TF2')
    w.login('dana.k@test.com', 'TestPass123!')
    for appid in (570, 730, 440):
        w.goto(base, f'/app/{appid}/', 'reopen the game page')
        w.click_button('Add to Wishlist', 'add to wishlist')
    w.click_link('Wishlist', 'open the wishlist')


def browse_15(w, base):
    w.start_home(base)
    w.goto(base, '/search/?term=dead+cells', 'search Dead Cells')
    w.click_link('Dead Cells', 'open Dead Cells')
    w.click_link('Dead Cells: The Bad Seed', 'open the first DLC')
    w.click_button('Add to Cart', 'add the DLC')
    w.click_link('Cart', 'open the cart')
    w.page.get_by_role('button', name='Remove').first.click(timeout=10000)
    w._log('click', {'text': 'Remove'}, 'remove the DLC')
    w._after()
    w.atomic += 1
    w.goto(base, '/app/588650/', 'reopen Dead Cells')
    w.click_link('Dead Cells: Medley of Pain Bundle', 'open the first bundle')
    w.click_button('Add bundle to Cart', 'add the bundle')
    w.click_link('Cart', 'open the cart')
    w.page.get_by_role('button', name='Remove').first.click(timeout=10000)
    w._log('click', {'text': 'Remove'}, 'remove the bundle')
    w._after()
    w.atomic += 1
    w.goto(base, '/app/588650/', 'reopen Dead Cells')
    w.click_button('Add to Cart', 'add Dead Cells')
    w.click_link('Cart', 'open the cart')
    row = w.page.locator('tr', has_text='Dead Cells').first
    w._log('select', {'name': 'qty'}, 'set quantity to 3')
    row.locator('select[name=qty]').select_option('3', timeout=10000)
    w._after()
    w.atomic += 1
    w._log('click', {'text': 'Update'}, 'update quantity')
    row.get_by_role('button', name='Update').click(timeout=10000)
    w._after()
    w.atomic += 1
    w.page.get_by_role('button', name='Remove').first.click(timeout=10000)
    w._log('click', {'text': 'Remove'}, 'remove Dead Cells')
    w._after()
    w.atomic += 1
    w.goto(base, '/bundle/46406/', 'open the second bundle')


def browse_16(w, base):
    w.start_home(base)
    w.click_link('Search', 'open the search page')
    w.fill('input[name=term]', 'resident', 'search resident')
    w.apply('apply the search')
    w.select('select[name=genre]', 'Action', 'refine with the Action genre')
    w.apply('apply the genre filter')
    w.click_link('Resident Evil 2', 'open Resident Evil 2')
    w.goto(base, '/search/?term=resident', 'back to results')
    w.click_link('Resident Evil Village', 'open Village')
    w.goto(base, '/search/?term=resident', 'back to results')
    w.click_link('Resident Evil 4', 'open Resident Evil 4')
    w.click_link('Read reviews', 'open RE4 reviews', exact=False)
    w.click_link('Resident Evil 4', 'back to the game page')
    w.click_link('All news for this game', 'open RE4 news', exact=False)
    w.login('carol.m@test.com', 'TestPass123!')
    w.goto(base, '/app/2050650/', 'reopen RE4')
    w.click_button('Add to Wishlist', 'add to wishlist')
    w.click_link('Wishlist', 'open the wishlist')


def browse_17(w, base):
    w.start_home(base)
    w.goto(base, '/search/?term=hades', 'search hades')
    w.click_link('Hades', 'open Hades')
    w.goto(base, '/search/?term=hades', 'back to results')
    w.click_link('Hades II', 'open Hades II')
    w.click_link('Read reviews', 'open Hades II reviews', exact=False)
    w.select('select[name=filter]', 'positive', 'filter positive')
    w.apply('apply the review filter')
    w.goto(base, '/app/1145360/', 'reopen Hades')
    w.click_button('Add to Cart', 'add Hades to cart')
    w.click_link('Cart', 'open the cart')
    w.page.get_by_role('button', name='Remove').first.click(timeout=10000)
    w._log('click', {'text': 'Remove'}, 'remove Hades')
    w._after()
    w.atomic += 1
    w.login('alice.j@test.com', 'TestPass123!')
    w.goto(base, '/app/1145350/', 'reopen Hades II')
    w.click_button('Add to Wishlist', 'add Hades II to wishlist')
    w.click_link('Wishlist', 'open the wishlist')


def browse_18(w, base):
    w.start_home(base)
    w.click_link('Specials', 'open specials')
    w.click_link('FINAL FANTASY VII REMAKE INTERGRADE', 'open FF7 Remake')
    w.click_button('Add to Cart', 'add FF7 Remake')
    w.goto(base, '/specials/', 'back to specials')
    w.click_link('Hades', 'open Hades')
    w.click_button('Add to Cart', 'add Hades')
    w.click_link('Cart', 'open the cart')
    w.login('dana.k@test.com', 'TestPass123!')
    w.click_link('checkout', 'continue to checkout', exact=False)
    w.fill('input[name=full_name]', 'Dana Kim', 'fill name')
    w.fill('input[name=email]', 'dana.k@test.com', 'fill email')
    w.fill('input[name=address1]', '88 Neon Street', 'fill address')
    w.fill('input[name=city]', 'Seattle', 'fill city')
    w.fill('input[name=state]', 'WA', 'fill state')
    w.fill('input[name=zipcode]', '98101', 'fill zip')
    w.select('select[name=payment_method]', 'PayPal', 'pick payment')
    w.click_button('Place order', 'place the order')


def browse_19(w, base):
    w.start_home(base)
    w.goto(base, '/search/?term=cyberpunk', 'search cyberpunk')
    w.click_link('Cyberpunk 2077', 'open Cyberpunk 2077')
    w.click_link('Read reviews', 'open Cyberpunk reviews', exact=False)
    w.goto(base, '/app/1091500/', 'reopen Cyberpunk 2077')
    w.click_button('Add to Cart', 'add Cyberpunk to cart')
    w.click_link('Cart', 'open the cart')
    w.page.get_by_role('button', name='Remove').first.click(timeout=10000)
    w._log('click', {'text': 'Remove'}, 'remove Cyberpunk')
    w._after()
    w.atomic += 1
    w.goto(base, '/search/?term=elden+ring', 'search ELDEN RING')
    w.click_link('ELDEN RING', 'open ELDEN RING')
    w.login('dana.k@test.com', 'TestPass123!')
    w.goto(base, '/app/1245620/', 'reopen ELDEN RING')
    w.click_button('Add to Wishlist', 'add to wishlist')
    w.click_link('Wishlist', 'open the wishlist')


BROWSERS = {
    0: browse_0, 1: browse_1, 2: browse_2, 3: browse_3, 4: browse_4,
    5: browse_5, 6: browse_6, 7: browse_7, 8: browse_8, 9: browse_9,
    10: browse_10, 11: browse_11, 12: browse_12, 13: browse_13, 14: browse_14,
    15: browse_15, 16: browse_16, 17: browse_17, 18: browse_18, 19: browse_19,
}


def run_task(pw, idx, round_tag):
    task = TASKS[idx]
    task_id = task['id']
    server = Server()
    out = Path(tempfile.mkdtemp(prefix=f'steam-run-{round_tag}-{idx}-',
                                dir='/tmp'))
    try:
        shutil.copy2(server.db, out / 'initial.db')
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={'width': 1280, 'height': 900})
        w = Walk(page, task_id, out)
        try:
            BROWSERS[idx](w, server.base)
        except Exception as exc:
            browser.close()
            raise RuntimeError(f'browser path crashed: {exc}') from exc
        shutil.copy2(server.db, out / 'after.db')
        traj = {
            'task_id': task_id,
            'task': task['ques'],
            'start_url': server.base + '/',
            'terminated': True,
            'termination_reason': 'agent_done',
            'steps': w.steps,
            'final_answer': answer_for(task_id),
        }
        (out / 'trajectory.json').write_text(
            json.dumps(traj, indent=1), encoding='utf-8')
        browser.close()
    finally:
        server.stop()

    # grade with the site's own verifier
    try:
        result = subprocess.run(
            [sys.executable, f'verify/verify_{idx}.py', '--run_dir', str(out)],
            cwd=str(SITE), capture_output=True, text=True)
    finally:
        pass
    verdict = json.loads(result.stdout.strip().splitlines()[-1]) \
        if result.stdout.strip() else {'pass': False, 'reason': 'no output'}
    ok = verdict.get('pass')
    print(f'  [{round_tag}] {task_id}: {w.atomic} browser actions, '
          f'verifier {"PASS" if ok else "FAIL: " + str(verdict.get("reason"))}',
          flush=True)
    if not ok:
        keep = Path('/tmp/steam-run-failures')
        keep.mkdir(exist_ok=True)
        shutil.move(str(out), str(keep / f'{round_tag}-{task_id}'))
    else:
        shutil.rmtree(out, ignore_errors=True)
    return ok, w.atomic


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rounds', type=int, default=2)
    ap.add_argument('--only', default='')
    args = ap.parse_args()
    only = {int(x) for x in args.only.split(',')} if args.only else None

    failures = []
    with sync_playwright() as pw:
        for rnd in range(1, args.rounds + 1):
            tag = f'r{rnd}'
            for idx in range(len(TASKS)):
                if only is not None and idx not in only:
                    continue
                try:
                    ok, actions = run_task(pw, idx, tag)
                except Exception as exc:
                    print(f'  [{tag}] {TASKS[idx]["id"]}: CRASH {exc}', flush=True)
                    ok = False
                if not ok:
                    failures.append(f'{TASKS[idx]["id"]} round {tag}')
    if failures:
        print('FAILURES:', failures, flush=True)
        return 1
    print('=== all browser walkthroughs pass their verify contracts', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
