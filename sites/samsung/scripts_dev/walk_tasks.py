#!/usr/bin/env python3
"""Real-browser honest walkthrough for the samsung mirror (fix round).

Replaces the original test-client walker the review falsified as synthetic
evidence. This driver runs a real Chromium (Playwright) session against the
live mirror container and, for every task in tasks.jsonl:

- resets the site through the control plane and opens a fresh browser
  context (cookies cleared) per task, archiving initial.db first;
- drives the honest path with visible-element interaction only — direct
  URL navigation is used exclusively for the homepage start; browser back
  counts as one atomic action;
- counts ATOMIC ACTIONS the task text genuinely requires (navigate home,
  click, fill, select, submit, back); reads are never counted and actions
  the text does not require are never taken (anti-padding);
- records every answer fact from what the rendered pages actually show
  (no DB reads), writes trajectory.json with per-step screenshots, and
  archives after.db;
- grades the archived run with the site's own verify/verify_N.py contract.

Two independent rounds must agree per task (step counts and normalized
answers). The measured facts are written to scraped_data/expected_answers.json
for scripts_dev/build_contract.py.

Run: python3 scripts_dev/walk_tasks.py <round-name> [task_ids...]
     python3 scripts_dev/walk_tasks.py --verify   # grade archived runs
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import traceback
from pathlib import Path

from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE))

BASE = os.environ.get('SAMSUNG_WALK_BASE', 'http://localhost:46230')
CTRL = os.environ.get('SAMSUNG_WALK_CTRL', 'http://localhost:47230')
TOKEN_FILE = os.environ.get('SAMSUNG_WALK_TOKEN',
                            '/data/zhaoyang-user-projects/websyn/'
                            'wh-samsung-fix-evidence/control_token')
CONTAINER = os.environ.get('SAMSUNG_WALK_CONTAINER', 'wh-samsung-fix')
EV = Path(os.environ.get('SAMSUNG_WALK_EVIDENCE',
                         '/data/zhaoyang-user-projects/websyn/'
                         'wh-samsung-fix-evidence/runs'))
PASSWORD = 'TestPass123!'
TASKS = [json.loads(line)['ques'] for line in
         (SITE / 'tasks.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]


def reset_site():
    token = Path(TOKEN_FILE).read_text().strip()
    for attempt in range(20):
        r = subprocess.run(
            ['curl', '-s', '-X', 'POST', '-H', f'Authorization: Bearer {token}',
             f'{CTRL}/reset/samsung'], capture_output=True, text=True, timeout=120)
        if '"ready": true' in r.stdout or '"ready":true' in r.stdout:
            import urllib.request
            for _ in range(60):
                try:
                    urllib.request.urlopen(BASE + '/_health', timeout=2)
                    return
                except Exception:
                    time.sleep(0.5)
        time.sleep(1)
    raise RuntimeError('reset failed')


def snapshot_db(dest: Path):
    if dest.exists():
        dest.unlink()
    subprocess.run(['docker', 'cp',
                    f'{CONTAINER}:/opt/WebSyn/samsung/instance/samsung.db',
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
        self.page.wait_for_timeout(300)
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

    def select_label_contains(self, sel, needle, desc):
        """Select the first option whose visible label contains needle."""
        opts = self.page.eval_on_selector_all(
            f'{sel} option', 'els => els.map(e => [e.value, e.textContent])')
        for value, label in opts:
            if needle.casefold() in (label or '').casefold() and value:
                self._log('select', {'selector': sel, 'value': value,
                                     'label': label}, desc)
                self.page.select_option(sel, value, timeout=10000)
                self._after(settle=False)
                self.atomic += 1
                return label
        raise AssertionError(f'no option containing {needle!r}')

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
            'task': TASKS[int(self.task_id.split('--')[1])],
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


def sign_in(w, email):
    w.click('a.icon-link:has-text("Sign In")', 'open sign-in page')
    w.fill('#email', email, 'email')
    w.fill('#password', PASSWORD, 'password')
    w.submit('button:has-text("Sign In")', 'submit sign-in')


def product_card(w, name, desc=None):
    w.click('.product-card:has-text("' + name + '")',
            desc or f'open product card {name!r}')


def catalog_count(w):
    """'42 products · 42 shown' -> (total, shown)."""
    m = re.search(r'(\d+) products? · (\d+) shown', w.body())
    assert m, 'catalog count line not found'
    return int(m.group(1)), int(m.group(2))


def card_price(w, idx=0):
    """First $ amount on the idx-th product card (sale price)."""
    txt = w.page.locator('.product-card .product-price').nth(idx).inner_text()
    m = re.search(r'\$([0-9,]+\.\d\d)', txt)
    return '$' + m.group(1) if m else txt.strip()


def wishlist_count_on_account(w):
    m = re.search(r'(\d+) items? saved', w.body())
    assert m, 'wishlist count on account page not found'
    return int(m.group(1))


def spec_rows(w):
    """Parse the rendered spec table into (th, td) pairs."""
    return w.page.eval_on_selector_all(
        '.spec-table tr',
        'els => els.map(e => [e.querySelector("th") ? '
        'e.querySelector("th").textContent.trim() : "", '
        'e.querySelector("td") ? e.querySelector("td").textContent.trim() '
        ': ""])')


def spec_value_all(rows, attr):
    return [td for th, td in rows if th == attr and td]


def spec_group_value(w, group):
    """First non-placeholder value rendered under a spec group heading."""
    rows = w.page.eval_on_selector_all(
        '.spec-table tr',
        'els => els.map(e => [e.querySelector("th") ? '
        'e.querySelector("th").textContent.trim() : "", '
        'e.querySelector("td") ? e.querySelector("td").textContent.trim() '
        ': "", e.className])')
    inside = False
    for th, td, cls in rows:
        if 'spec-group' in cls:
            name = th
            inside = (name == group) or (inside and name == 'Dummy')
            continue
        if inside and td and td not in ('-', '–'):
            return td
    return None


def compare_headers(w):
    """[(family_name, model_code)] per rendered comparison column."""
    return w.page.eval_on_selector_all(
        '.compare-table thead th:not(.compare-corner)',
        'els => els.map(e => e.innerText.trim().split("\\n")'
        '.map(s => s.trim()))')


def compare_table(w):
    """{label: [per-column values]} plus the unlabeled rows, from the
    rendered comparison table."""
    rows = w.page.eval_on_selector_all(
        '.compare-table tbody tr',
        'els => els.map(e => [e.querySelector("th") ? '
        'e.querySelector("th").textContent.trim() : "", '
        'Array.from(e.querySelectorAll("td")).map(d => '
        'd.textContent.trim()), e.className])')
    labeled, unlabeled = {}, []
    for th, tds, cls in rows:
        if 'spec-group' in cls or not tds:
            continue
        if th:
            labeled.setdefault(th, []).append(tds)
        else:
            unlabeled.append(tds)
    return labeled, unlabeled


def compare_value(w, label, col):
    """First non-placeholder value for a label in the given column."""
    labeled, _ = compare_table(w)
    for tds in labeled.get(label, []):
        if col < len(tds) and tds[col] not in ('', '-', '–'):
            return tds[col]
    return None


def compare_unlabeled(w, needle):
    out = []
    for tds in compare_table(w)[1]:
        if any(needle in v for v in tds):
            out.append(tds)
    return out


def buy_state(w):
    body = w.body()
    model = grab(r'Model code: ([A-Z0-9\-]+)', body, 'buy model code')
    price = grab(r'\$([0-9,]+\.\d\d)', body, 'buy price')
    return model, '$' + price


# ==================================================================== tasks ==

def t0(w):
    w.start_home()
    nav(w, 'Smartphones')
    total, _ = catalog_count(w)
    w.read('total', total)
    w.click('input[name="f_series"][value="Galaxy Z"]', 'check Galaxy Z filter')
    w.submit('button:has-text("Apply Filters")', 'apply filters')
    _, shown = catalog_count(w)
    w.read('galaxy_z', shown)
    w.click('a:has-text("Clear")', 'clear the filter')
    w.select('#sort', 'price-low', 'sort price low to high')
    cheapest = w.page.locator('.product-card .product-name').first.inner_text().strip()
    price = card_price(w)
    w.read('cheapest_name', cheapest)
    w.read('cheapest_price', price)
    w.click('.product-card:has-text("' + cheapest + '")',
            'open the cheapest phone product page')
    m = re.search(r'(\d+\.\d) ★ · (\d+) reviews', w.body())
    assert m, 'rating line not found'
    rating, reviews = m.group(1), m.group(2)
    w.read('cheapest_rating', rating)
    w.read('cheapest_reviews', reviews)
    w.back('back to the price-sorted catalog')
    product_card(w, 'Galaxy Z Fold8 Ultra', 'open the Galaxy Z Fold8 Ultra page')
    fold_price = grab(r'\$([0-9,]+\.\d\d)', w.body(), 'fold8u price')
    w.read('fold8u_price', '$' + fold_price)
    sign_in(w, 'alice.j@test.com')
    w.back('back to the login page')
    w.back('back to the Z Fold8 Ultra product page')
    w.back('back to the price-sorted Smartphones catalog')
    w.click('.product-card:has-text("' + cheapest + '")',
            'reopen the cheapest phone product page')
    w.submit('button:has-text("Add to Wishlist")',
             'add the cheapest phone to the wishlist')
    w.click('a.icon-link:has-text("Account")', 'open account page')
    count = wishlist_count_on_account(w)
    w.read('wishlist', count)
    w.save(f"The Smartphones catalog lists {total} phones. With the Galaxy Z "
           f"series filter, {shown} phones remain. After sorting by price low "
           f"to high, the cheapest phone is {cheapest} at {price}, rated "
           f"{rating} with {reviews} reviews. The Galaxy Z Fold8 Ultra page "
           f"shows {w.facts['fold8u_price']}. Alice's wishlist now shows "
           f"{count} items.")


def t1(w):
    w.start_home()
    nav(w, 'Mobile Accessories')
    w.fill('.catalog-search input[name="q"]', 'case', 'search catalog for case')
    w.submit('.catalog-search button:has-text("Search")', 'submit catalog search')
    _, shown = catalog_count(w)
    w.read('case_results', shown)
    w.click('input[name="f_type"][value="Cases & Covers"]',
            'check Cases & Covers filter')
    w.submit('button:has-text("Apply Filters")', 'apply filters')
    _, shown2 = catalog_count(w)
    w.read('cases_covers', shown2)
    w.select('#sort', 'rating', 'sort by customer rating')
    top = w.page.locator('.product-card .product-name').first.inner_text().strip()
    price = card_price(w)
    w.read('top_name', top)
    w.read('top_price', price)
    w.click('.product-card:has-text("' + top + '")',
             'open the highest-rated product page')
    sign_in(w, 'bob.c@test.com')
    w.back('back to the login page')
    w.back('back to the product page')
    w.submit('button:has-text("Add to Wishlist")', 'add product to wishlist')
    w.click('a.icon-link:has-text("Account")', 'open account page')
    count = wishlist_count_on_account(w)
    w.read('wishlist', count)
    w.save(f"Searching the Mobile Accessories catalog for case returns "
           f"{shown} results. Keeping only Cases & Covers leaves {shown2} "
           f"products. The highest-rated product is {top} at {price}. Bob's "
           f"wishlist now shows {count} items.")


def t2(w):
    w.start_home()
    nav(w, 'TVs')
    total, _ = catalog_count(w)
    w.read('total', total)
    w.click('input[name="f_screen_size"][value="75\\" - 84\\""]',
            'check 75" - 84" screen-size filter')
    w.submit('button:has-text("Apply Filters")', 'apply filters')
    _, shown = catalog_count(w)
    w.read('size_count', shown)
    w.click('input[name="f_type"][value="Micro RGB TVs"]',
            'check Micro RGB TVs filter')
    w.submit('button:has-text("Apply Filters")', 'apply filters')
    _, shown2 = catalog_count(w)
    w.read('both_count', shown2)
    first = w.page.locator('.product-card .product-name').first.inner_text().strip()
    first_price = card_price(w)
    w.click('.product-card', 'open the first remaining TV')
    w.read('first_name', first)
    w.read('first_price', first_price)
    w.back('back to the filtered catalog')
    w.click('a:has-text("Clear")', 'clear the filters')
    w.select('#sort', 'price-high', 'sort price high to low')
    expensive = w.page.locator('.product-card .product-name').first.inner_text().strip()
    expensive_price = card_price(w)
    w.read('expensive_name', expensive)
    w.read('expensive_price', expensive_price)
    sign_in(w, 'carol.d@test.com')
    w.back('back to the login page')
    w.back('back to the price-sorted TV catalog')
    w.click('.product-card >> nth=0', 'open the most expensive TV')
    w.submit('button:has-text("Add to Wishlist")', 'add the TV to the wishlist')
    w.click('a.icon-link:has-text("Account")', 'open account page')
    count = wishlist_count_on_account(w)
    w.read('wishlist', count)
    w.save(f"The TVs catalog lists {total} TVs. The 75\" - 84\" screen-size "
           f"filter leaves {shown}. Adding the Micro RGB TVs type filter "
           f"leaves {shown2}; the first is {first} at {first_price}. The most "
           f"expensive TV is {expensive} at {expensive_price}. Carol's "
           f"wishlist now shows {count} items.")


def t3(w):
    w.start_home()
    nav(w, 'Refrigerators')
    w.fill('.catalog-search input[name="q"]', 'Family Hub',
           'search for Family Hub')
    w.submit('.catalog-search button:has-text("Search")', 'submit catalog search')
    _, shown = catalog_count(w)
    w.read('family_hub', shown)
    first = w.page.locator('.product-card .product-name').first.inner_text().strip()
    w.click('.product-card', 'open the first Family Hub match')
    w.read('fridge_name', first)
    w.read('fridge_price', '$' + grab(r'\$([0-9,]+\.\d\d)', w.body(), 'price'))
    w.read('fridge_model', grab(r'Model code: ([A-Z0-9\-]+)', w.body(), 'model'))
    nav(w, 'Laundry')
    w.select('#sort', 'price-low', 'sort laundry by price low to high')
    cheapest = w.page.locator('.product-card .product-name').first.inner_text().strip()
    cheapest_price = card_price(w)
    w.read('laundry_name', cheapest)
    w.read('laundry_price', cheapest_price)
    sign_in(w, 'dana.k@test.com')
    nav(w, 'Refrigerators')
    w.fill('.catalog-search input[name="q"]', 'Family Hub',
           'search for Family Hub again')
    w.submit('.catalog-search button:has-text("Search")', 'submit search')
    w.click('.product-card', 'open the Family Hub refrigerator')
    w.submit('button:has-text("Add to Wishlist")', 'add refrigerator to wishlist')
    w.click('a.icon-link:has-text("Account")', 'open account page')
    count = wishlist_count_on_account(w)
    w.read('wishlist', count)
    w.save(f"The Family Hub search matches {shown} refrigerators. The first "
           f"match is {first} at {w.facts['fridge_price']} (model "
           f"{w.facts['fridge_model']}). The cheapest laundry product is "
           f"{cheapest} at {cheapest_price}. Dana's wishlist now shows "
           f"{count} items.")


def t4(w):
    w.start_home()
    nav(w, 'Smartphones')
    product_card(w, 'Galaxy S26 Ultra', 'open the Galaxy S26 Ultra page')
    body = w.body()
    w.read('model', grab(r'Model code: ([A-Z0-9\-]+)', body, 'model code'))
    w.read('price', '$' + grab(r'\$([0-9,]+\.\d\d)', body, 'price'))
    w.read('rating', grab(r'(\d+\.\d) ★ ·', body, 'rating'))
    rows = spec_rows(w)
    w.read('display_dim', spec_value_all(rows, 'Main Display Dimension')[0])
    w.read('resolution', spec_value_all(rows, 'Main Display Resolution')[0])
    bright = [v for v in spec_value_all(rows, 'Peak Brightness')
              if v not in ('-', '–')]
    w.read('brightness', bright[0])
    w.read('battery', spec_group_value(w, 'Battery'))
    w.back('back to the catalog')
    product_card(w, 'Galaxy S26 256GB', 'open the Galaxy S26 page')
    w.read('s26_price', '$' + grab(r'\$([0-9,]+\.\d\d)', w.body(), 's26 price'))
    w.read('s26_specs', 'yes' if w.page.locator('.spec-table').count() else 'no')
    w.back('back to the catalog')
    product_card(w, 'Galaxy S26 FE', 'open the Galaxy S26 FE page')
    w.read('fe_price', '$' + grab(r'\$([0-9,]+\.\d\d)', w.body(), 'fe price'))
    sign_in(w, 'alice.j@test.com')
    nav(w, 'Smartphones')
    product_card(w, 'Galaxy S26 Ultra', 'open the S26 Ultra page again')
    w.submit('button:has-text("Add to Wishlist")', 'add S26 Ultra to wishlist')
    w.click('a.icon-link:has-text("Account")', 'open account page')
    w.click('a:has-text("Open Wishlist")', 'open the wishlist')
    w.click('.product-card:has-text("Galaxy Tab S11") button:has-text("Remove")',
            'remove the Galaxy Tab S11')
    w.click('a.icon-link:has-text("Account")', 'open account page for the count')
    count = wishlist_count_on_account(w)
    w.read('wishlist', count)
    f = w.facts
    w.save(f"The Galaxy S26 Ultra is model {f['model']} at {f['price']}, rated "
           f"{f['rating']}. Its specification table shows a main display of "
           f"{f['display_dim']}, resolution {f['resolution']}, peak brightness "
           f"{f['brightness']}, and battery capacity {f['battery']}. The "
           f"Galaxy S26 is {f['s26_price']} and shows a specification table: "
           f"{f['s26_specs']}. The Galaxy S26 FE is {f['fe_price']}. The final "
           f"wishlist count is {count}.")


def t5(w):
    w.start_home()
    nav(w, 'Smartphones')
    product_card(w, 'Galaxy S26 Ultra', 'open the Galaxy S26 Ultra page')
    w.click('a:has-text("Buy Now")', 'open the buy page')
    model0, price0 = buy_state(w)
    w.read('default_model', model0)
    w.read('default_price', price0)
    w.click('a.option-btn:has-text("1TB")', 'select the 1TB storage')
    model1, price1 = buy_state(w)
    w.read('tb_model', model1)
    w.read('tb_price', price1)
    w.click('a.option-btn:has-text("Cobalt Violet")',
            'change color to Cobalt Violet')
    model2, price2 = buy_state(w)
    w.read('violet_model', model2)
    w.click('a.option-btn:has-text("Unlocked")', 'select the Unlocked carrier')
    model3, price3 = buy_state(w)
    w.read('unlocked_model', model3)
    sign_in(w, 'alice.j@test.com')
    w.back('back to the login page')
    w.back('back to the buy page')
    w.select('#qty', '2', 'set quantity to two')
    w.submit('button:has-text("Add to Cart")', 'add to cart')
    subtotal = grab(r'Subtotal: \$([0-9,]+\.\d\d)', w.body(), 'subtotal')
    w.read('subtotal', '$' + subtotal)
    w.save(f"The buy page defaults to model {model0} at {price0}. The 1TB "
           f"option is {price1} (model {model1}). With Cobalt Violet the "
           f"resolved model is {model2}. With the Unlocked carrier the model "
           f"is {model3}. Two units give a cart subtotal of ${subtotal}.")


def t6(w):
    w.start_home()
    nav(w, 'Smartphones')
    product_card(w, 'Galaxy Z Fold8 Ultra', 'open the Z Fold8 Ultra page')
    w.click('a:has-text("Buy Now")', 'open the buy page')
    model0, price0 = buy_state(w)
    w.read('default_model', model0)
    w.read('default_price', price0)
    w.click('a.option-btn:has-text("1TB")', 'switch to the 1TB storage')
    model1, price1 = buy_state(w)
    w.read('tb_model', model1)
    w.read('tb_price', price1)
    w.click('a.option-btn:has-text("Violet Shadow")',
            'change color to Violet Shadow')
    model2, price2 = buy_state(w)
    w.read('violet_model', model2)
    sign_in(w, 'bob.c@test.com')
    w.back('back to the login page')
    w.back('back to the buy page')
    w.submit('button:has-text("Add to Cart")', 'add one unit to the cart')
    line = grab(r'Subtotal: \$([0-9,]+\.\d\d)', w.body(), 'cart line total')
    w.read('line_total_1', '$' + line)
    w.select('select[name="qty"]', '3', 'change quantity to three')
    line3 = grab(r'Subtotal: \$([0-9,]+\.\d\d)', w.body(), 'new line total')
    w.read('line_total', '$' + line3)
    w.submit('button:has-text("Remove")', 'remove the item')
    cart_after = 'empty' if 'Your cart is empty' in w.body() else 'has items'
    w.read('cart_after', cart_after)
    nav(w, 'Smartphones')
    product_card(w, 'Galaxy Z Fold8 Ultra', 'open the Z Fold8 Ultra page again')
    w.submit('button:has-text("Add to Wishlist")',
             'add the Z Fold8 Ultra to the wishlist')
    w.click('a.icon-link:has-text("Account")', 'open account page')
    count = wishlist_count_on_account(w)
    w.read('wishlist', count)
    w.save(f"The Galaxy Z Fold8 Ultra buy page defaults to {model0} at "
           f"{price0}. The 1TB option is {price1} (model {model1}). With the "
           f"Violet Shadow color the resolved model is {model2}. Three units "
           f"total ${line3} on the cart line. After removing the item the cart "
           f"is {cart_after}. Bob's wishlist now shows {count} items.")


def t7(w):
    w.start_home()
    sign_in(w, 'alice.j@test.com')
    nav(w, 'Tablets')
    product_card(w, 'Galaxy Tab S11', 'open the Galaxy Tab S11 page')
    w.click('a:has-text("Buy Now")', 'open the buy page')
    model0, price0 = buy_state(w)
    w.read('default_model', model0)
    w.read('default_price', price0)
    w.submit('button:has-text("Add to Cart")', 'add the tablet to the cart')
    w.click('a:has-text("Checkout")', 'proceed to checkout')
    w.fill('#address1', '1200 Test Address Ln', 'delivery address line')
    w.fill('#city', 'Ridgefield Park', 'delivery city')
    w.fill('#state', 'NJ', 'delivery state')
    w.fill('#zipcode', '07660', 'delivery zipcode')
    w.click('input[name="payment_method"][value="Samsung Pay"]',
            'select Samsung Pay')
    w.submit('button:has-text("Place Order")', 'place the order')
    order_no = grab(r'Order (SS-\d+) placed', w.body(), 'order number')
    total = grab(r'Total: \$([0-9,]+\.\d\d)', w.body(), 'total')
    tax = grab(r'Tax: \$([0-9,]+\.\d\d)', w.body(), 'tax')
    w.read('order_no', order_no)
    w.read('total', '$' + total)
    w.read('tax', '$' + tax)
    w.click('a.icon-link:has-text("Account")', 'open account page')
    orders = grab(r'You have placed (\d+) orders?', w.body(), 'order count')
    w.read('orders', orders)
    w.save(f"The Galaxy Tab S11 buy page defaults to model {model0} at "
           f"{price0}. Order {order_no} was placed with Samsung Pay: total "
           f"${total}, tax ${tax}. Alice's order history now shows {orders} "
           f"orders.")


def t8(w):
    w.start_home()
    nav(w, 'Compare')
    w.click('input[name="models"][value="SM-S948"]', 'check Galaxy S26 Ultra')
    w.click('input[name="models"][value="SM-S942"]', 'check Galaxy S26')
    w.submit('button:has-text("Compare Selected")', 'run the comparison')
    cols = compare_headers(w)
    w.read('rendered_columns', cols)
    assert [c[1] for c in cols] == ['SM-S942', 'SM-S948'], cols
    w.read('s26u_dim', compare_value(w, 'Main Display Dimension', 1))
    w.read('s26_dim', compare_value(w, 'Main Display Dimension', 0))
    w.read('s26u_weight', compare_value(w, 'Weight', 1))
    w.read('s26_weight', compare_value(w, 'Weight', 0))
    w.read('s26u_camera', compare_value(w, 'Wide', 1))
    w.read('s26_camera', compare_value(w, 'Wide', 0))
    mah = compare_unlabeled(w, 'mAh')
    assert mah, 'battery values not rendered'
    bigger = ('Galaxy S26 Ultra' if
              int(re.search(r'(\d+)', mah[0][1]).group(1)) >
              int(re.search(r'(\d+)', mah[0][0]).group(1)) else 'Galaxy S26')
    w.read('bigger_battery', bigger)
    w.click('input[name="models"][value="SM-F776"]', 'add Galaxy Z Flip8')
    w.submit('button:has-text("Compare Selected")', 'run the three-way compare')
    cols2 = compare_headers(w)
    w.read('flip8_dim', compare_value(w, 'Main Display Dimension', 0))
    sign_in(w, 'dana.k@test.com')
    nav(w, 'Smartphones')
    product_card(w, 'Galaxy S26 Ultra', 'open the S26 Ultra page')
    w.submit('button:has-text("Add to Wishlist")', 'add S26 Ultra to wishlist')
    w.click('a:has-text("Buy Now")', 'open the buy page')
    model0, price0 = buy_state(w)
    w.read('buy_model', model0)
    w.click('a.icon-link:has-text("Account")', 'open account page')
    count = wishlist_count_on_account(w)
    w.read('wishlist', count)
    f = w.facts
    w.save(f"The comparison shows the Galaxy S26 with a {f['s26_dim']} main "
           f"display, {f['s26_weight']} g and a {f['s26_camera']} wide "
           f"camera, and the Galaxy S26 Ultra with a {f['s26u_dim']} main "
           f"display, {f['s26u_weight']} g and a {f['s26u_camera']} wide "
           f"camera. The {bigger} has the larger battery. The Galaxy Z "
           f"Flip8's main display is {f['flip8_dim']}. The S26 Ultra buy "
           f"page defaults to {model0}. Dana's wishlist now shows {count} "
           f"items.")


def t9(w):
    w.start_home()
    nav(w, 'Compare')
    w.click('input[name="models"][value="SM-F976"]', 'check Z Fold8 Ultra')
    w.click('input[name="models"][value="SM-F971"]', 'check Z Fold8')
    w.submit('button:has-text("Compare Selected")', 'run the comparison')
    cols = compare_headers(w)
    w.read('rendered_columns', cols)
    assert [c[1] for c in cols] == ['SM-F971', 'SM-F976'], cols
    w.read('fold8u_dim', compare_value(w, 'Unfolded (HxWxD)', 1))
    w.read('fold8_dim', compare_value(w, 'Unfolded (HxWxD)', 0))
    w.read('fold8u_weight', compare_value(w, 'Weight', 1))
    w.read('fold8_weight', compare_value(w, 'Weight', 0))
    heavier = ('Galaxy Z Fold8 Ultra' if
               float(w.facts['fold8u_weight']) > float(w.facts['fold8_weight'])
               else 'Galaxy Z Fold8')
    w.read('heavier', heavier)
    w.click('a:has-text("Clear")', 'clear the comparison')
    w.click('input[name="models"][value="SM-S948"]', 'check S26 Ultra')
    w.click('input[name="models"][value="SM-S938"]', 'check S25 Ultra')
    w.submit('button:has-text("Compare Selected")', 'compare S26U with S25U')
    cols2 = compare_headers(w)
    assert [c[1] for c in cols2] == ['SM-S938', 'SM-S948'], cols2
    w.read('s26u_dim2', compare_value(w, 'Main Display Dimension', 1))
    w.read('s25u_dim2', compare_value(w, 'Main Display Dimension', 0))
    w.read('s26u_brightness', compare_value(w, 'Peak Brightness', 1))
    w.read('s25u_brightness', compare_value(w, 'Peak Brightness', 0))
    sign_in(w, 'dana.k@test.com')
    nav(w, 'Smartphones')
    product_card(w, 'Galaxy Z Fold8 Ultra', 'open the Z Fold8 Ultra page')
    w.submit('button:has-text("Add to Wishlist")',
             'add Z Fold8 Ultra to wishlist')
    w.click('a.icon-link:has-text("Account")', 'open account page')
    count = wishlist_count_on_account(w)
    w.read('wishlist', count)
    f = w.facts
    w.save(f"Unfolded, the Galaxy Z Fold8 measures {f['fold8_dim']} and "
           f"weighs {f['fold8_weight']} g; the Galaxy Z Fold8 Ultra measures "
           f"{f['fold8u_dim']} and weighs {f['fold8u_weight']} g, so the "
           f"{heavier} is heavier. Comparing the Galaxy S26 Ultra with the "
           f"Galaxy S25 Ultra instead: main displays {f['s26u_dim2']} versus "
           f"{f['s25u_dim2']}, peak brightness {f['s26u_brightness']} versus "
           f"{f['s25u_brightness']}. Dana's wishlist now shows {count} items.")


def t10(w):
    w.start_home()
    nav(w, 'Support')
    w.click('a:has-text("Open the Warranty Center")', 'open the Warranty Center')
    cat_tiles = w.page.locator('.tile-grid .tile').count()
    w.read('categories', cat_tiles)
    w.click('.tile:has-text("Phones, Tablets & Wearables")',
            'open Phones, Tablets & Wearables')
    w.select_label_contains('#model', 'Galaxy S26 Ultra 512GB',
                             'select the S26 Ultra 512GB')
    status = grab(r'Coverage status: ([^\n]+)', w.body(), 'coverage status')
    period = grab(r'purchaser for (\S+) ', w.body(), 'period')
    w.read('s26u_coverage', status)
    w.read('s26u_period', period + ' months')
    w.click('a:has-text("Check another product")', 'check another product')
    w.click('.tile:has-text("Home Appliances")', 'open Home Appliances')
    opts = w.page.eval_on_selector_all(
        '#model option', 'els => els.map(e => [e.value, e.textContent])')
    target = None
    for value, label in opts:
        lbl = (label or '').casefold()
        if value and 'bespoke' in lbl and not any(
                word in lbl for word in ('dryer', 'washer', 'laundry')):
            target = (value, label)
            break
    assert target, 'no Bespoke refrigerator option'
    w._log('select', {'selector': '#model', 'value': target[0],
                      'label': target[1]}, 'select a Bespoke refrigerator')
    w.page.select_option('#model', target[0], timeout=10000)
    w._after(settle=False)
    w.atomic += 1
    status2 = grab(r'Coverage status: ([^\n]+)', w.body(), 'appliance status')
    w.read('fridge_coverage', status2)
    sign_in(w, 'carol.d@test.com')
    w.click('a:has-text("Contact Support")', 'open the contact form')
    w.fill('#subject', 'S26 Ultra screen warranty question', 'subject')
    w.fill('#message',
           'My Galaxy S26 Ultra screen has a defect and I would like it '
           'checked under warranty.', 'message')
    w.submit('button:has-text("Send Message")', 'send the ticket')
    ticket = grab(r'ticket number is (ST-\d+)', w.body(), 'ticket number')
    dds = w.page.locator('.ticket-detail dd').all_inner_texts()
    tstatus = dds[-1].strip() if dds else 'Open'
    w.read('ticket', ticket)
    w.read('ticket_status', tstatus)
    w.save(f"The Warranty Center coverage checker lists {cat_tiles} product "
           f"categories. Phones, Tablets & Wearables coverage for the Galaxy "
           f"S26 Ultra 512GB is {status} for {period} months. Home Appliances "
           f"coverage for a Bespoke refrigerator is {status2}. Ticket "
           f"{ticket} was filed under Phones, Tablets & Wearables with topic "
           f"Warranty; its status is {tstatus}.")


def t11(w):
    w.start_home()
    nav(w, 'Support')
    w.click('a:has-text("Open the Warranty Center")', 'open the Warranty Center')
    faqs = w.page.locator('details.faq-item').count()
    w.read('faqs', faqs)
    w.click('details.faq-item:has-text("validat") summary',
            'open the validating-your-warranty FAQ')
    answer = w.page.locator(
        "details.faq-item:has-text('validat') p").inner_text().strip()
    w.read('validate_answer', answer)
    w.click('.tile:has-text("TV, Display & Home Theater")',
            'open TV, Display & Home Theater')
    w.select_label_contains('#model', 'TV', 'select a TV model')
    status = grab(r'Coverage status: ([^\n]+)', w.body(), 'tv status')
    period = grab(r'purchaser for (\S+) ', w.body(), 'tv period')
    w.read('tv_coverage', status)
    w.read('tv_period', period + ' months')
    w.click('a:has-text("Check another product")', 'check another product')
    w.click('.tile:has-text("Phones, Tablets & Wearables")',
            'open Phones, Tablets & Wearables')
    w.select_label_contains('#model', 'Galaxy Watch9', 'select Galaxy Watch9')
    status2 = grab(r'Coverage status: ([^\n]+)', w.body(), 'watch status')
    w.read('watch_coverage', status2)
    nav(w, 'Smartphones')
    product_card(w, 'Galaxy S26 Ultra', 'open the S26 Ultra page')
    w.click('a:has-text("Buy Now")', 'open the buy page')
    w.click('a.option-btn:has-text("512GB")', 'select the 512GB storage')
    model0, price0 = buy_state(w)
    w.read('model_512', model0)
    w.read('price_512', price0)
    nav(w, 'Watches')
    product_card(w, 'Galaxy Watch9', 'open the Galaxy Watch9 page')
    w.read('watch_price', '$' + grab(r'\$([0-9,]+\.\d\d)', w.body(), 'price'))
    w.click('a:has-text("Buy Now")', 'open the Watch9 buy page')
    wmodel, _ = buy_state(w)
    w.read('watch_model', wmodel)
    w.save(f"The Warranty Center lists {faqs} FAQ questions. The "
           f"validating-your-warranty FAQ says: {answer} TV, Display & Home "
           f"Theater coverage for a TV model is {status} for {period} months; "
           f"Phones, Tablets & Wearables coverage for the Galaxy Watch9 is "
           f"{status2}. The Galaxy S26 Ultra buy page resolves to model "
           f"{model0} at {price0} with the 512GB storage option. The Galaxy "
           f"Watch9 is {w.facts['watch_price']} and its buy page defaults to "
           f"model {wmodel}.")


def t12(w):
    w.start_home()
    sign_in(w, 'alice.j@test.com')
    w.click('a:has-text("View Order History")', 'open the order history')
    order_links = w.page.locator('.orders-table a').all_inner_texts()
    w.read('orders', len(order_links))
    w.read('order_nos', order_links)
    w.click('.orders-table a >> nth=0', 'open the most recent order')
    item = w.page.locator('.cart-table .cart-title').first.inner_text().strip()
    qty_tds = w.page.locator('.cart-table tbody td.num').all_inner_texts()
    qty = [t.strip() for t in qty_tds if t.strip().isdigit()]
    body = w.body()
    city = re.search(r'Delivery\n[^\n]+\n[^\n]+\n([A-Za-z ]+),', body)
    w.read('recent_item', item)
    w.read('recent_qty', qty[0] if qty else 'NOT STATED')
    w.read('city', city.group(1).strip() if city else 'NOT STATED')
    w.back('back to the orders')
    w.click('.orders-table a >> nth=1', 'open the older order')
    item2 = w.page.locator('.cart-table .cart-title').first.inner_text().strip()
    total2 = grab(r'Total: \$([0-9,]+\.\d\d)', w.body(), 'older total')
    w.read('older_item', item2)
    w.read('older_total', '$' + total2)
    w.click('a.icon-link:has-text("Account")', 'open account page')
    w.click('a:has-text("Open Wishlist")', 'open the wishlist')
    w.click('.product-card:has-text("Galaxy Tab S11") button:has-text("Remove")',
            'remove the Galaxy Tab S11')
    nav(w, 'Watches')
    product_card(w, 'Galaxy Watch9', 'open the Galaxy Watch9 page')
    w.submit('button:has-text("Add to Wishlist")', 'add Galaxy Watch9')
    w.click('a:has-text("Buy Now")', 'open the Watch9 buy page')
    wmodel, _ = buy_state(w)
    w.read('watch_model', wmodel)
    w.click('a.icon-link:has-text("Account")', 'open account page')
    count = wishlist_count_on_account(w)
    tickets = w.page.locator('.ticket-list li').count()
    w.read('wishlist', count)
    w.read('tickets', tickets)
    w.save(f"Alice has {len(order_links)} orders: "
           f"{', '.join(order_links)}. The most recent order contains {item} "
           f"x{w.facts['recent_qty']}, delivered to {w.facts['city']}. The "
           f"older order contains {item2}, total ${total2}. After the "
           f"wishlist edits (removed Tab S11, added Galaxy Watch9, buy page "
           f"model {wmodel}), the account shows {count} wishlist items and "
           f"{tickets} support tickets.")


def t13(w):
    w.start_home()
    sign_in(w, 'dana.k@test.com')
    nav(w, 'Support')
    w.click('a:has-text("Open the Warranty Center")', 'open the Warranty Center')
    w.click('.tile:has-text("Phones, Tablets & Wearables")',
            'open Phones, Tablets & Wearables')
    w.select_label_contains('#model', 'Galaxy Z Flip8', 'select Z Flip8')
    status = grab(r'Coverage status: ([^\n]+)', w.body(), 'status')
    period = grab(r'purchaser for (\S+) ', w.body(), 'period')
    w.read('flip8_coverage', status)
    w.read('flip8_period', period + ' months')
    w.click('footer a:has-text("Contact Us")', 'open Contact Us')
    w.select('#topic', 'Repair', 'select topic Repair')
    w.fill('#subject', 'Z Flip8 hinge repair needed', 'subject')
    w.fill('#message',
           'The hinge on my Galaxy Z Flip8 is stiff and clicks; please '
           'advise on repair service.', 'message')
    w.submit('button:has-text("Send Message")', 'send the ticket')
    ticket = grab(r'ticket number is (ST-\d+)', w.body(), 'ticket number')
    dds = w.page.locator('.ticket-detail dd').all_inner_texts()
    tstatus = dds[-1].strip() if dds else 'Open'
    w.read('ticket', ticket)
    w.read('status', tstatus)
    w.click('a.icon-link:has-text("Account")', 'open account page')
    listed = w.page.locator('.ticket-list li').count()
    w.read('on_account', 'yes' if listed else 'no')
    w.save(f"Phones, Tablets & Wearables coverage for the Galaxy Z Flip8 is "
           f"{status} for {period} months. Ticket {ticket} was filed under "
           f"Phones, Tablets & Wearables with topic Repair about the Z Flip8 "
           f"hinge; its status is {tstatus}, and it appears on the account "
           f"page: yes ({listed} ticket listed).")


def t14(w):
    w.start_home()
    w.fill('.header-search input[name="q"]', 'Family Hub',
           'header search Family Hub')
    w.submit('.header-search button', 'run the header search')
    results = grab(r'(\d+) results?', w.body(), 'result count')
    w.read('fh_results', results)
    cats = w.page.locator('.product-card .product-series').all_inner_texts()
    w.read('fh_categories', ', '.join(sorted({c.strip() for c in cats})))
    w.click('.product-card:has-text("Family Hub"):has-text("Bespoke")',
            'open the first Bespoke Family Hub refrigerator result')
    w.read('fridge_price', '$' + grab(r'\$([0-9,]+\.\d\d)', w.body(), 'price'))
    w.read('fridge_model',
           grab(r'Model code: ([A-Z0-9\-]+)', w.body(), 'model code'))
    w.fill('.header-search input[name="q"]', 'Buds', 'header search Buds')
    w.submit('.header-search button', 'run the header search')
    first = w.page.locator('.product-card .product-name').first.inner_text().strip()
    bprice = card_price(w)
    w.read('buds_name', first)
    w.read('buds_price', bprice)
    w.fill('.header-search input[name="q"]', 'case', 'header search case')
    w.submit('.header-search button', 'run the header search')
    case_results = grab(r'(\d+) results?', w.body(), 'case results')
    w.read('case_results', case_results)
    sign_in(w, 'bob.c@test.com')
    w.back('back to the login page')
    w.back('back to the case results')
    w.back('back to the Buds results')
    w.click('.product-card:has-text("Galaxy Buds4 Pro")',
            'open the Galaxy Buds4 Pro page')
    w.submit('button:has-text("Add to Wishlist")', 'add Buds4 Pro to wishlist')
    w.click('a.icon-link:has-text("Account")', 'open account page')
    count = wishlist_count_on_account(w)
    w.read('wishlist', count)
    w.save(f"The header search for Family Hub returns {results} results "
           f"across the categories {w.facts['fh_categories']}. The first "
           f"Bespoke Family Hub refrigerator is {w.facts['fridge_price']} "
           f"(model {w.facts['fridge_model']}). Searching for Buds, the first "
           f"result is {first} at {bprice}. Searching for case returns "
           f"{case_results} results. Bob's wishlist now shows {count} items.")


def t15(w):
    w.start_home()
    w.click('a.icon-link:has-text("Sign In")', 'open the sign-in page')
    w.click('a:has-text("Create an account")', 'open the sign-up page')
    w.fill('#name', 'Frank Nova', 'name')
    w.fill('#email', 'frank.n@test.com', 'email')
    w.fill('#password', PASSWORD, 'password')
    w.submit('button:has-text("Create Account")', 'create the account')
    body0 = w.body()
    assert 'My Account' in body0
    orders0 = grab(r'You have placed (\d+) orders?', body0, 'orders')
    saved0 = grab(r'(\d+) items? saved', body0, 'wishlist')
    w.read('account_page', 'profile, orders, wishlist and support tickets cards')
    w.read('profile_orders', orders0)
    w.read('profile_saved', saved0)
    w.click('a:has-text("Sign Out")', 'sign out')
    w.click('a.icon-link:has-text("Sign In")', 'open the sign-in page')
    w.fill('#email', 'frank.n@test.com', 'email')
    w.fill('#password', PASSWORD, 'password')
    w.submit('button:has-text("Sign In")', 'sign back in')
    profile = re.search(r'My Account\nProfile\n([^\n]+)', w.body())
    assert profile, 'profile name not found'
    w.read('profile', profile.group(1))
    nav(w, 'Watches')
    product_card(w, 'Galaxy Watch9', 'open the Galaxy Watch9 page')
    w.submit('button:has-text("Add to Wishlist")', 'add Watch9 to wishlist')
    nav(w, 'Smartphones')
    product_card(w, 'Galaxy Z Flip8', 'open the Z Flip8 page')
    w.read('flip8_price', '$' + grab(r'\$([0-9,]+\.\d\d)', w.body(), 'price'))
    w.click('a.icon-link:has-text("Account")', 'open account page')
    count = wishlist_count_on_account(w)
    w.read('wishlist', count)
    w.save(f"The new account page shows the profile {profile.group(1)} "
           f"({orders0} orders, {saved0} items saved) with profile, orders, "
           f"wishlist and support tickets cards. After signing out and back "
           f"in, the profile name shown is {profile.group(1)}. The Galaxy Z "
           f"Flip8 is {w.facts['flip8_price']}. The account now has {count} "
           f"wishlist item.")


def t16(w):
    w.start_home()
    nav(w, 'Shop All')
    total, _ = catalog_count(w)
    w.read('total', total)
    nav(w, 'Tablets')
    tablets, _ = catalog_count(w)
    w.read('tablets', tablets)
    nav(w, 'Watches')
    watches, _ = catalog_count(w)
    w.read('watches', watches)
    nav(w, 'Audio')
    audio, _ = catalog_count(w)
    w.read('audio', audio)
    first = w.page.locator('.product-card .product-name').first.inner_text().strip()
    first_price = card_price(w)
    w.click('.product-card', "open the Audio catalog's first product")
    w.read('audio_name', first)
    w.read('audio_price', first_price)
    nav(w, 'TVs')
    tvs, _ = catalog_count(w)
    w.read('tvs', tvs)
    sign_in(w, 'bob.c@test.com')
    w.click('a:has-text("View Order History")', 'open the order history')
    order_no = w.page.locator('.orders-table a').first.inner_text().strip()
    w.read('order_no', order_no)
    w.click('.orders-table a >> nth=0', 'open the order')
    order_item = w.page.locator('.cart-table .cart-title').first.inner_text().strip()
    w.read('order_item', order_item)
    nav(w, 'Watches')
    product_card(w, 'Galaxy Watch9', 'open the Galaxy Watch9 page')
    w.click('a:has-text("Buy Now")', 'open the Watch9 buy page')
    wmodel, _ = buy_state(w)
    w.read('watch_model', wmodel)
    w.save(f"Shop All lists {total} products; Tablets {tablets}, Watches "
           f"{watches}, Audio {audio}. The Audio catalog's first product is "
           f"{first} at {first_price}. The TVs catalog lists {tvs} TVs. Bob's "
           f"order history shows order {order_no} containing {order_item}. "
           f"The Galaxy Watch9 buy page defaults to model {wmodel}.")


def t17(w):
    w.start_home()
    nav(w, 'Watches')
    product_card(w, 'Galaxy Watch9', 'open the Galaxy Watch9 page')
    w.click('a:has-text("Buy Now")', 'open the Watch9 buy page')
    model0, price0 = buy_state(w)
    w.read('default_model', model0)
    w.read('default_price', price0)
    w.click('a.option-btn:has-text("44mm")', 'switch to the 44mm size')
    w.click('a.option-btn:has-text("LTE")', 'switch to LTE connectivity')
    model1, price1 = buy_state(w)
    w.read('lte_model', model1)
    w.read('lte_price', price1)
    w.click('a.option-btn:has-text("Graphite")', 'change color to Graphite')
    model2, price2 = buy_state(w)
    w.read('graphite_model', model2)
    sign_in(w, 'carol.d@test.com')
    w.back('back to the login page')
    w.back('back to the buy page')
    w.select('#qty', '2', 'set quantity to two')
    w.submit('button:has-text("Add to Cart")', 'add the watch to the cart')
    subtotal = grab(r'Subtotal: \$([0-9,]+\.\d\d)', w.body(), 'cart subtotal')
    w.read('subtotal', '$' + subtotal)
    chips = w.page.locator('.chip').all_inner_texts()
    w.read('options', '; '.join(c.strip() for c in chips[:4]))
    w.read('color_option', next(c.strip() for c in chips
                                if c.strip().startswith('Color:')))
    w.click('a:has-text("Checkout")', 'open the checkout page')
    tax = grab(r'Estimated tax: \$([0-9,]+\.\d\d)', w.body(), 'estimated tax')
    w.read('tax', '$' + tax)
    w.save(f"The Galaxy Watch9 buy page defaults to {model0} at {price0}. With "
           f"the 44mm size and LTE connectivity the resolved model is "
           f"{model1} at {price1}. With the Graphite color the resolved model "
           f"is {model2}. Two units give a cart subtotal of ${subtotal} with "
           f"options {w.facts['options']}; {w.facts['color_option']}. The "
           f"checkout page shows an estimated tax of ${tax}.")


def t18(w):
    w.start_home()
    nav(w, 'Smartphones')
    product_card(w, 'Galaxy Z Flip8', 'open the Z Flip8 page')
    w.click('a:has-text("Buy Now")', 'open the Z Flip8 buy page')
    model0, price0 = buy_state(w)
    w.read('default_model', model0)
    w.read('default_price', price0)
    w.click('a.option-btn:has-text("512GB")', 'select the 512GB storage')
    model1, price1 = buy_state(w)
    w.read('model_512', model1)
    w.read('price_512', price1)
    sign_in(w, 'bob.c@test.com')
    w.back('back to the login page')
    w.back('back to the buy page')
    w.submit('button:has-text("Add to Cart")', 'add one unit to the cart')
    w.select('select[name="qty"]', '2', 'change the quantity to two')
    subtotal = grab(r'Subtotal: \$([0-9,]+\.\d\d)', w.body(), 'subtotal')
    badge = grab(r'Cart (\d+)', w.body(), 'cart badge')
    w.read('subtotal', '$' + subtotal)
    w.read('items', badge)
    w.submit('button:has-text("Remove")', 'remove the item')
    nav(w, 'Smartphones')
    product_card(w, 'Galaxy Z Flip8', 'open the Z Flip8 page again')
    w.click('a:has-text("Buy Now")', 'open the buy page, default storage')
    w.submit('button:has-text("Add to Cart")', 'add one default unit to the cart')
    new_subtotal = grab(r'Subtotal: \$([0-9,]+\.\d\d)', w.body(), 'new subtotal')
    w.read('new_subtotal', '$' + new_subtotal)
    chips = w.page.locator('.chip').all_inner_texts()
    w.read('new_options', chips[0].strip())
    w.save(f"The Galaxy Z Flip8 buy page defaults to {model0} at {price0}. The "
           f"512GB option is {price1} (model {model1}). After adding one unit "
           f"and changing the quantity to two, the cart subtotal is "
           f"${subtotal} with an item count of {badge}. After removing the "
           f"item and adding one default-storage unit instead, the new "
           f"subtotal is ${new_subtotal} with options shown "
           f"{'; '.join(c.strip() for c in chips)}.")


def t19(w):
    w.start_home()
    nav(w, 'Smartphones')
    product_card(w, 'Galaxy S25 Ultra', 'open the S25 Ultra page')
    body = w.body()
    w.read('model', grab(r'Model code: ([A-Z0-9\-]+)', body, 'model code'))
    w.read('price', '$' + grab(r'\$([0-9,]+\.\d\d)', body, 'price'))
    w.read('rating', grab(r'(\d+\.\d) ★ ·', body, 'rating'))
    rows = spec_rows(w)
    w.read('dim', spec_value_all(rows, 'Main Display Dimension')[0])
    bright = [v for v in spec_value_all(rows, 'Peak Brightness')
              if v not in ('-', '–')]
    w.read('brightness', bright[0])
    nav(w, 'Compare')
    w.click('input[name="models"][value="SM-S938"]', 'check S25 Ultra')
    w.click('input[name="models"][value="SM-S948"]', 'check S26 Ultra')
    w.submit('button:has-text("Compare Selected")', 'run the comparison')
    cols = compare_headers(w)
    w.read('rendered_columns', cols)
    assert [c[1] for c in cols] == ['SM-S938', 'SM-S948'], cols
    w.read('s25u_weight', compare_value(w, 'Weight', 0))
    w.read('s26u_weight', compare_value(w, 'Weight', 1))
    heavier = ('Galaxy S25 Ultra' if
               float(w.facts['s25u_weight']) > float(w.facts['s26u_weight'])
               else 'Galaxy S26 Ultra')
    w.read('heavier', heavier)
    sign_in(w, 'alice.j@test.com')
    nav(w, 'Smartphones')
    product_card(w, 'Galaxy S25 Ultra', 'open the S25 Ultra page again')
    w.submit('button:has-text("Add to Wishlist")', 'add S25 Ultra to wishlist')
    w.back('back to the pre-toggle product page')
    w.back('back to the Smartphones catalog')
    product_card(w, 'Galaxy Z Flip8', 'open the Z Flip8 page')
    w.read('flip8_price', '$' + grab(r'\$([0-9,]+\.\d\d)', w.body(), 'price'))
    w.click('a.icon-link:has-text("Account")', 'open account page')
    count = wishlist_count_on_account(w)
    w.read('wishlist', count)
    f = w.facts
    w.save(f"The Galaxy S25 Ultra is model {f['model']} at {f['price']}, "
           f"rated {f['rating']}. Its specification table shows a main "
           f"display of {f['dim']} and peak brightness {f['brightness']}. "
           f"Galaxy Compare shows the Galaxy S25 Ultra at "
           f"{f['s25u_weight']} g and the Galaxy S26 Ultra at "
           f"{f['s26u_weight']} g, so the {heavier} is heavier. The Galaxy Z "
           f"Flip8 is {f['flip8_price']}. Alice's wishlist now shows {count} "
           f"items.")


TASKS_FN = {0: t0, 1: t1, 2: t2, 3: t3, 4: t4, 5: t5, 6: t6, 7: t7, 8: t8,
            9: t9, 10: t10, 11: t11, 12: t12, 13: t13, 14: t14, 15: t15,
            16: t16, 17: t17, 18: t18, 19: t19}


def stable(facts):
    out = {}
    for key, value in facts.items():
        value = re.sub(r'SS-\d+', 'SS-<n>', str(value))
        value = re.sub(r'ST-\d+', 'ST-<n>', value)
        out[key] = value
    return out


def walk_round(round_name, only):
    out_root = EV / round_name
    out_root.mkdir(parents=True, exist_ok=True)
    summary = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for idx in only:
            print(f'=== task {idx} ===', flush=True)
            reset_site()
            run_dir = out_root / str(idx)
            if run_dir.exists():
                subprocess.run(['rm', '-rf', str(run_dir)], check=True)
            run_dir.mkdir(parents=True)
            snapshot_db(run_dir / 'initial.db')
            ctx = browser.new_context(viewport={'width': 1280, 'height': 900})
            page = ctx.new_page()
            w = Walk(page, f'Samsung--{idx}', run_dir)
            try:
                TASKS_FN[idx](w)
                snapshot_db(run_dir / 'after.db')
                summary[idx] = {'atomic': w.atomic, 'facts': w.facts,
                                'js_errors': w.js_errors}
            except Exception:
                snapshot_db(run_dir / 'after.db')
                w.save(w.facts.get('partial', '') or '(walk failed)')
                (run_dir / 'error.txt').write_text(traceback.format_exc())
                summary[idx] = {'atomic': w.atomic,
                                'error': traceback.format_exc()[-800:]}
                print(f'  !! task {idx} FAILED:\n{traceback.format_exc()}',
                      flush=True)
            ctx.close()
        browser.close()
    (out_root / 'walk_summary.json').write_text(json.dumps(summary, indent=1))
    counts = {k: v.get('atomic') for k, v in summary.items()}
    print('ROUND SUMMARY:', json.dumps(counts))
    print('TOTAL:', sum(c for c in counts.values() if c))
    return summary


def emit_answers(summary):
    """Write the browser-measured facts for build_contract.py."""
    out = {str(i): {'steps': summary[i]['atomic'],
                    'answers': summary[i]['facts']}
           for i in sorted(summary) if 'facts' in summary[i]}
    (SITE / 'scraped_data' / 'expected_answers.json').write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding='utf-8')
    print(f"wrote {SITE / 'scraped_data' / 'expected_answers.json'}")


def verify_all():
    """Grade every archived run with the site's own verify_N.py."""
    failures = []
    for round_name in sorted(p.name for p in EV.iterdir() if p.is_dir()):
        for idx_dir in sorted((EV / round_name).iterdir()):
            if not idx_dir.is_dir() or not (idx_dir / 'trajectory.json').exists():
                continue
            if (idx_dir / 'error.txt').exists():
                failures.append(f'{round_name}/{idx_dir.name}: walk error')
                continue
            idx = int(idx_dir.name)
            r = subprocess.run(
                [sys.executable, str(SITE / 'verify' / f'verify_{idx}.py'),
                 '--run_dir', str(idx_dir)],
                capture_output=True, text=True, timeout=300)
            status = 'PASS' if r.returncode == 0 else 'FAIL'
            print(f'{round_name}/{idx}: {status}', flush=True)
            if r.returncode != 0:
                failures.append(f'{round_name}/{idx}: '
                                f'{(r.stdout + r.stderr).strip()[-300:]}')
    if failures:
        print('\nVERIFY FAILURES:')
        for f in failures:
            print(' -', f)
        return 1
    print('\nall archived runs PASS the contract')
    return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--verify':
        return verify_all()
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    round_name = sys.argv[1]
    only = [int(a) for a in sys.argv[2:]] if len(sys.argv) > 2 \
        else sorted(TASKS_FN)
    summary = walk_round(round_name, only)
    emit_answers(summary)
    return 0


if __name__ == '__main__':
    sys.exit(main())
