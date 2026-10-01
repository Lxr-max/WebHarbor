#!/usr/bin/env python3
"""Build the tracked verify/contract.json for the samsung mirror.

Derives, per task: the exact task wording, the canonical digest of the
reviewed seed database, the page-evidence patterns of the honest path, the
factual claims (regexes generated from the answers the honest-path audit
collected), and the exact database deltas the task's saved changes must
produce. Byte-reproducible: no wall clock, no RNG, stable ordering.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import shutil
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE))
sys.path.insert(0, str(SITE / 'verify'))

import contract_engine as CE  # noqa: E402

EXPECTED = json.loads(
    (SITE / 'scraped_data' / 'expected_answers.json').read_text(encoding='utf-8'))
TASKS = [json.loads(line) for line in
         (SITE / 'tasks.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]

TS_RE = r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]+Z'
SS_RE = r'SS-[0-9]+'
ST_RE = r'ST-[0-9]+'

# per-task: page evidence patterns, claims (label, answer key), state deltas
SPECS = {
    0: {
        'paths': [r'/smartphones/\?.*f_series=Galaxy', r'sort=price-low',
                  r'/smartphones/galaxy-a17-5g/',
                  r'/smartphones/galaxy-z-fold8-ultra/',
                  r'/account/login/', r'/account/'],
        'claims': [('catalog total', 'total'), ('galaxy z count', 'galaxy_z'),
                   ('cheapest name', 'cheapest_name'),
                   ('cheapest price', 'cheapest_price'),
                   ('cheapest rating', 'cheapest_rating'),
                   ('cheapest reviews', 'cheapest_reviews'),
                   ('fold8u price', 'fold8u_price'),
                   ('wishlist count', 'wishlist')],
        'state': {'wishlist_items': {'added': [
            {'id': {'regex': '[1-9][0-9]*'}, 'user_id': 1,
             'product_slug': 'galaxy-a17-5g', 'added_ts': {'regex': TS_RE}}]}},
    },
    1: {
        'paths': [r'mobile-accessories/\?.*q=case', r'f_type=Cases',
                  r'sort=rating', r'/account/login/', r'/account/'],
        'claims': [('case search count', 'case_results'),
                   ('cases and covers count', 'cases_covers'),
                   ('top case name', 'top_name'), ('top case price', 'top_price'),
                   ('wishlist count', 'wishlist')],
        'state': {'wishlist_items': {'added': [
            {'id': {'regex': '[1-9][0-9]*'}, 'user_id': 2,
             'product_slug': 'galaxy-s26-plus-clear-magnet-case-transparent-sku-ef-cs947ctegus',
             'added_ts': {'regex': TS_RE}}]}},
    },
    2: {
        'paths': [r'/tvs/\?.*f_screen_size=', r'f_type=Micro',
                  r'sort=price-high', r'/account/login/', r'/account/'],
        'claims': [('tv total', 'total'), ('size filter count', 'size_count'),
                   ('both filter count', 'both_count'),
                   ('first tv name', 'first_name'), ('first tv price', 'first_price'),
                   ('expensive tv name', 'expensive_name'),
                   ('expensive tv price', 'expensive_price'),
                   ('wishlist count', 'wishlist')],
        'state': {'wishlist_items': {'added': [
            {'id': {'regex': '[1-9][0-9]*'}, 'user_id': 3,
             'product_slug': '89-class-micro-led-sku-mna89ms1bacxza',
             'added_ts': {'regex': TS_RE}}]}},
    },
    3: {
        'paths': [r'refrigerators/\?.*q=Family', r'laundry/\?.*sort=price-low',
                  r'/account/login/', r'/account/'],
        'claims': [('family hub count', 'family_hub'),
                   ('fridge name', 'fridge_name'), ('fridge price', 'fridge_price'),
                   ('fridge model', 'fridge_model'),
                   ('laundry name', 'laundry_name'),
                   ('laundry price', 'laundry_price'),
                   ('wishlist count', 'wishlist')],
        'state': {'wishlist_items': {'added': [
            {'id': {'regex': '[1-9][0-9]*'}, 'user_id': 4,
             'product_slug': 'bespoke-4-door-flex-refrigerator-29-cu-ft-with-family-hub-32-and-ai-vision-in-stainless-steel-sku-rf29db9900qdaa',
             'added_ts': {'regex': TS_RE}}]}},
    },
    4: {
        'paths': [r'/smartphones/galaxy-s26-ultra/', r'/smartphones/galaxy-s26/',
                  r'/smartphones/galaxy-s26-fe/', r'/account/login/',
                  r'/account/wishlist/', r'/account/'],
        'claims': [('model code', 'model'), ('price', 'price'), ('rating', 'rating'),
                   ('display dimension', 'display_dim'),
                   ('resolution', 'resolution'), ('peak brightness', 'brightness'),
                   ('battery', 'battery'), ('s26 price', 's26_price'),
                   ('s26 spec table', 's26_specs'), ('fe price', 'fe_price'),
                   ('wishlist count', 'wishlist')],
        'state': {'wishlist_items': {
            'added': [{'id': {'regex': '[1-9][0-9]*'}, 'user_id': 1,
                       'product_slug': 'galaxy-s26-ultra',
                       'added_ts': {'regex': TS_RE}}],
            'removed': [json.dumps([3])]}},
    },
    5: {
        'paths': [r'galaxy-s26-ultra/buy/\?.*Storage=1TB', r'Color=Cobalt',
                  r'Carrier=Unlocked', r'/account/login/', r'/cart/'],
        'claims': [('default model', 'default_model'),
                   ('default price', 'default_price'),
                   ('terabyte price', 'tb_price'), ('terabyte model', 'tb_model'),
                   ('violet model', 'violet_model'), ('cart subtotal', 'subtotal')],
        'state': {'cart_items': {'added': [
            {'id': {'regex': '[1-9][0-9]*'}, 'cart_key': 'user:1',
             'configurator': 'smartphones_galaxy-s26-ultra',
             'model_code': 'SM-S948UZVFXAA',
             'title': 'Galaxy S26 Ultra 1TB (Unlocked)',
             'options': '{"Storage": "1TB", "Color": "Cobalt Violet", '
                        '"Carrier": "Unlocked"}',
             'unit_price': 1799.99, 'qty': 2,
             'image': 'us-galaxy-s26-ultra-s948-sm-s948uzvaatt-550993860.png'}]}},
    },
    6: {
        'paths': [r'galaxy-z-fold8-ultra/buy/\?.*Storage=1TB', r'Color=Violet',
                  r'/account/login/', r'/cart/',
                  r'/smartphones/galaxy-z-fold8-ultra/', r'/account/'],
        'claims': [('default model', 'default_model'),
                   ('default price', 'default_price'),
                   ('terabyte price', 'tb_price'), ('terabyte model', 'tb_model'),
                   ('violet shadow model', 'violet_model'),
                   ('line total', 'line_total'), ('cart after remove', 'cart_after'),
                   ('wishlist count', 'wishlist')],
        'state': {'wishlist_items': {'added': [
            {'id': {'regex': '[1-9][0-9]*'}, 'user_id': 2,
             'product_slug': 'galaxy-z-fold8-ultra',
             'added_ts': {'regex': TS_RE}}]}},
    },
    7: {
        'paths': [r'/account/login/', r'galaxy-tab-s11/buy/', r'/cart/',
                  r'/checkout/', r'/orders/SS-', r'/account/'],
        'claims': [('default model', 'default_model'),
                   ('default price', 'default_price'),
                   ('order number', 'order_no'), ('order total', 'total'),
                   ('order tax', 'tax'), ('order count', 'orders')],
        'state': {'orders': {'added': [
            {'id': 4, 'order_no': {'regex': SS_RE},
             'user_id': 1, 'email': 'alice.j@test.com',
             'full_name': 'Alice Johnson',
             'address1': '1200 Test Address Ln',
             'city': 'Ridgefield Park', 'state': 'NJ', 'zipcode': '07660',
             'payment_method': 'Samsung Pay', 'subtotal': 1299.99,
             'shipping': 0.0, 'tax': 86.12, 'total': 1386.11,
             'status': 'Processing', 'placed_ts': {'regex': TS_RE}}]},
            'order_items': {'added': [
                {'id': 4, 'order_id': 4, 'model_code': 'SM-X930NZAAXAR',
                 'title': 'Galaxy Tab S11 Ultra (14.6")',
                 'options': '{"Device": "Galaxy Tab S11 Ultra", '
                            '"Storage": "256 GB", "Screen Size": "14.6\\"", '
                            '"Color": "Gray", "Carrier": "Wi-fi"}',
                 'unit_price': 1299.99, 'qty': 1,
                 'image': 'us-galaxy-tab-s11-ultra-sm-x930-sm-x930nzaaxar-550969762.png'}]}},
        'answer_state': [['orders', 'order_no']],
    },
    8: {
        'paths': [r'/compare/\?models=SM-S942&models=SM-S948',
                  r'/compare/\?models=SM-F776&models=SM-S942&models=SM-S948',
                  r'/account/login/', r'/account/'],
        'claims': [('s26 dimension', 's26_dim'),
                   ('s26 ultra dimension', 's26u_dim'),
                   ('s26 weight', 's26_weight'),
                   ('s26 ultra weight', 's26u_weight'),
                   ('s26 wide camera', 's26_camera'),
                   ('s26 ultra wide camera', 's26u_camera'),
                   ('larger battery', 'bigger_battery'),
                   ('flip8 dimension', 'flip8_dim'),
                   ('buy model', 'buy_model'), ('wishlist count', 'wishlist')],
        'state': {'wishlist_items': {'added': [
            {'id': {'regex': '[1-9][0-9]*'}, 'user_id': 4,
             'product_slug': 'galaxy-s26-ultra', 'added_ts': {'regex': TS_RE}}]}},
    },
    9: {
        'paths': [r'/compare/\?models=SM-F971&models=SM-F976',
                  r'/compare/\?models=SM-S938&models=SM-S948',
                  r'/account/login/', r'/account/'],
        'claims': [('fold8 ultra dimension', 'fold8u_dim'),
                   ('fold8 dimension', 'fold8_dim'),
                   ('fold8 ultra weight', 'fold8u_weight'),
                   ('fold8 weight', 'fold8_weight'),
                   ('heavier model', 'heavier'),
                   ('s26 ultra brightness', 's26u_brightness'),
                   ('s25 ultra brightness', 's25u_brightness'),
                   ('s26 ultra dimension two', 's26u_dim2'),
                   ('s25 ultra dimension two', 's25u_dim2'),
                   ('wishlist count', 'wishlist')],
        'state': {'wishlist_items': {'added': [
            {'id': {'regex': '[1-9][0-9]*'}, 'user_id': 4,
             'product_slug': 'galaxy-z-fold8-ultra',
             'added_ts': {'regex': TS_RE}}]}},
    },
    10: {
        'paths': [r'/support/warranty/\?category=phones-tablets-wearables',
                  r'model=SM-S948UZVEXAA',
                  r'/support/warranty/\?category=home-appliances',
                  r'/support/contact/done/\?ticket_no=ST-',
                  r'/account/login/'],
        'claims': [('category count', 'categories'),
                   ('s26 ultra coverage', 's26u_coverage'),
                   ('s26 ultra period', 's26u_period'),
                   ('fridge coverage', 'fridge_coverage'),
                   ('ticket number', 'ticket'), ('ticket status', 'ticket_status')],
        'state': {'support_tickets': {'added': [
            {'id': {'regex': '[1-9][0-9]*'}, 'ticket_no': {'regex': ST_RE},
             'user_id': 3, 'email': 'carol.d@test.com',
             'category': 'Phones, Tablets & Wearables', 'topic': 'Warranty',
             'subject': 'S26 Ultra screen warranty question',
             'message': 'My Galaxy S26 Ultra screen has a defect and I '
                        'would like it checked under warranty.',
             'status': 'Open', 'created_ts': {'regex': TS_RE}}]}},
        'answer_state': [['support_tickets', 'ticket_no']],
    },
    11: {
        'paths': [r'/support/warranty/', r'category=tv-display-home-theater',
                  r'category=phones-tablets-wearables',
                  r'galaxy-s26-ultra/buy/\?.*Storage=512GB',
                  r'/watches/galaxy-watch9/', r'/watches/galaxy-watch9/buy/'],
        'claims': [('faq count', 'faqs'), ('validate answer', 'validate_answer'),
                   ('tv coverage', 'tv_coverage'), ('tv period', 'tv_period'),
                   ('watch coverage', 'watch_coverage'),
                   ('model 512', 'model_512'), ('price 512', 'price_512'),
                   ('watch price', 'watch_price'), ('watch model', 'watch_model')],
        'state': {},
    },
    12: {
        'paths': [r'/orders/', r'/orders/SS-', r'/account/wishlist/',
                  r'/watches/galaxy-watch9/buy/', r'/account/'],
        'claims': [('order count', 'orders'), ('recent item', 'recent_item'),
                   ('recent quantity', 'recent_qty'), ('delivery city', 'city'),
                   ('older item', 'older_item'), ('older total', 'older_total'),
                   ('watch model', 'watch_model'),
                   ('wishlist count', 'wishlist'), ('ticket count', 'tickets')],
        'state': {'wishlist_items': {
            'added': [{'id': {'regex': '[1-9][0-9]*'}, 'user_id': 1,
                       'product_slug': 'galaxy-watch9',
                       'added_ts': {'regex': TS_RE}}],
            'removed': [json.dumps([3])]}},
    },
    13: {
        'paths': [r'/support/warranty/\?category=phones-tablets-wearables',
                  r'/support/contact/', r'/account/',
                  r'/support/contact/done/\?ticket_no=ST-'],
        'claims': [('flip8 coverage', 'flip8_coverage'),
                   ('flip8 period', 'flip8_period'),
                   ('ticket number', 'ticket'), ('ticket status', 'status'),
                   ('ticket on account', 'on_account')],
        'state': {'support_tickets': {'added': [
            {'id': {'regex': '[1-9][0-9]*'}, 'ticket_no': {'regex': ST_RE},
             'user_id': 4, 'email': 'dana.k@test.com',
             'category': 'Phones, Tablets & Wearables', 'topic': 'Repair',
             'subject': 'Z Flip8 hinge repair needed',
             'message': 'The hinge on my Galaxy Z Flip8 is stiff and '
                        'clicks; please advise on repair service.',
             'status': 'Open', 'created_ts': {'regex': TS_RE}}]}},
        'answer_state': [['support_tickets', 'ticket_no']],
    },
    14: {
        'paths': [r'/search/\?.*q=Family', r'/search/\?.*q=Buds',
                  r'/search/\?.*q=case', r'/account/login/',
                  r'/audio/galaxy-buds4-pro/', r'/account/'],
        'claims': [('family hub results', 'fh_results'),
                   ('family hub categories', 'fh_categories'),
                   ('fridge price', 'fridge_price'), ('fridge model', 'fridge_model'),
                   ('buds name', 'buds_name'), ('buds price', 'buds_price'),
                   ('case results', 'case_results'),
                   ('wishlist count', 'wishlist')],
        'state': {'wishlist_items': {'added': [
            {'id': {'regex': '[1-9][0-9]*'}, 'user_id': 2,
             'product_slug': 'galaxy-buds4-pro',
             'added_ts': {'regex': TS_RE}}]}},
    },
    15: {
        'paths': [r'/account/signup/', r'/account/login/',
                  r'/watches/galaxy-watch9/',
                  r'/smartphones/galaxy-z-flip8/', r'/account/'],
        'claims': [('account page', 'account_page'), ('profile name', 'profile'),
                   ('flip8 price', 'flip8_price'), ('wishlist count', 'wishlist')],
        'state': {'users': {'added': [
            {'id': 5, 'name': 'Frank Nova', 'email': 'frank.n@test.com',
             'pw_hash': {'regex': r"b'\$2b\$12\$[./A-Za-z0-9]{53}'"}}]},
            'wishlist_items': {'added': [
                {'id': {'regex': '[1-9][0-9]*'}, 'user_id': 5,
                 'product_slug': 'galaxy-watch9',
                 'added_ts': {'regex': TS_RE}}]}},
    },
    16: {
        'paths': [r'/shop/all/', r'/tablets/', r'/watches/', r'/audio/',
                  r'/tvs/', r'/account/login/', r'/orders/SS-',
                  r'galaxy-watch9/buy/'],
        'claims': [('shop all total', 'total'), ('tablets count', 'tablets'),
                   ('watches count', 'watches'), ('audio count', 'audio'),
                   ('audio product name', 'audio_name'),
                   ('audio product price', 'audio_price'),
                   ('tvs count', 'tvs'), ('order number', 'order_no'),
                   ('order item', 'order_item'), ('watch model', 'watch_model')],
        'state': {},
    },
    17: {
        'paths': [r'galaxy-watch9/buy/\?.*Size=44mm', r'Connectivity=LTE',
                  r'Color=Graphite', r'/account/login/', r'/cart/',
                  r'/checkout/'],
        'claims': [('default model', 'default_model'),
                   ('default price', 'default_price'),
                   ('lte model', 'lte_model'), ('lte price', 'lte_price'),
                   ('graphite model', 'graphite_model'),
                   ('cart subtotal', 'subtotal'),
                   ('cart options', 'options'), ('color option', 'color_option'),
                   ('estimated tax', 'tax')],
        'state': {'cart_items': {'added': [
            {'id': {'regex': '[1-9][0-9]*'}, 'cart_key': 'user:3',
             'configurator': 'watches_galaxy-watch9',
             'model_code': 'SM-L355UZKAXAA',
             'title': 'Galaxy Watch9, 44mm, LTE, Graphite',
             'options': '{"Device": "Galaxy Watch9", "Size": "44mm", '
                        '"Watch Connectivity": "LTE", '
                        '"Watch Carrier": "Wifi", "Color": "Graphite", '
                        '"Band Type": "Sport", "Band Color": "Black", '
                        '"Band Size": "Medium/Large"}',
             'unit_price': 459.99, 'qty': 2,
             'image': 'us-galaxy-watch-sm-l350nzkaxaa-galaxy-watch-----mm--bluetooth--graphite-graphite-554056107.png'}]}},
    },
    18: {
        'paths': [r'galaxy-z-flip8/buy/\?.*Storage=512GB', r'/account/login/',
                  r'/cart/', r'galaxy-z-flip8/buy/'],
        'claims': [('default model', 'default_model'),
                   ('default price', 'default_price'),
                   ('model 512', 'model_512'), ('price 512', 'price_512'),
                   ('cart subtotal', 'subtotal'), ('cart items', 'items'),
                   ('new subtotal', 'new_subtotal'),
                   ('new options', 'new_options')],
        'state': {'cart_items': {'added': [
            {'id': {'regex': '[1-9][0-9]*'}, 'cart_key': 'user:2',
             'configurator': 'smartphones_galaxy-z-flip8',
             'model_code': 'SM-F776ULGAXAA',
             'title': 'Galaxy Z Flip8 256GB (Unlocked)',
             'options': '{"Storage": "256GB", "Color": "Mint", '
                        '"Connectivity": "Unlocked"}',
             'unit_price': 1049.99, 'qty': 1,
             'image': 'us-galaxy-zflip8-f776-sm-f776ulgaxaa-553842884.png'}]}},
    },
    19: {
        'paths': [r'/smartphones/galaxy-s25-ultra/',
                  r'/compare/\?models=SM-S938&models=SM-S948', r'/account/login/',
                  r'/smartphones/galaxy-z-flip8/', r'/account/'],
        'claims': [('model code', 'model'), ('price', 'price'), ('rating', 'rating'),
                   ('display dimension', 'dim'), ('peak brightness', 'brightness'),
                   ('s25 ultra weight', 's25u_weight'),
                   ('s26 ultra weight', 's26u_weight'),
                   ('heavier model', 'heavier'), ('flip8 price', 'flip8_price'),
                   ('wishlist count', 'wishlist')],
        'state': {'wishlist_items': {'added': [
            {'id': {'regex': '[1-9][0-9]*'}, 'user_id': 1,
             'product_slug': 'galaxy-s25-ultra',
             'added_ts': {'regex': TS_RE}}]}},
    },
}


def claim_regex(value):
    """Regex for one expected answer value, matched against norm(answer)."""
    if isinstance(value, bool):
        return r'\b' + ('yes' if value else 'no') + r'\b'
    if isinstance(value, (int, float)):
        return r'\b' + re.escape(str(value)) + r'\b'
    text = CE.norm(str(value))
    # runtime-generated ticket / order numbers are matched by shape; the
    # exact saved value is additionally enforced through answer_state
    if re.fullmatch(r's[st]-[0-9]+', text):
        return r's[st]-[0-9]+'
    first_line = text.split('\n')[0].strip()
    if first_line in ('yes', 'no', 'active', 'open', 'empty'):
        return r'\b' + first_line + r'\b'
    if re.fullmatch(r'\$[0-9,]+\.\d{2}', first_line):
        return re.escape(first_line)
    if len(first_line) > 60:
        # long text: require the distinctive first 60 characters
        first_line = first_line[:60].strip()
    return re.escape(first_line)


def seed_digest():
    """Canonical digest of a freshly seeded database."""
    root = Path(tempfile.mkdtemp(prefix='samsung-contract-seed-', dir='/tmp'))
    os.environ['SAMSUNG_DB_URI'] = f'sqlite:///{root / "samsung.db"}'
    os.environ.pop('WEBSYN_SKIP_BOOTSTRAP', None)
    for mod in list(sys.modules):
        if mod.startswith(('app', 'seed', 'contract_engine')):
            del sys.modules[mod]
    sys.path.insert(0, str(SITE))
    import app as A  # noqa: F401 - importing materializes the seed
    digest = CE.digest(CE.database(root / 'samsung.db'))
    sys.path.insert(0, str(SITE / 'verify'))
    shutil.rmtree(root, ignore_errors=True)
    return digest


def main():
    initial_digest = seed_digest()
    print(f'seed digest: {initial_digest}')
    contract = {}
    for idx, task in enumerate(TASKS):
        spec = SPECS[idx]
        answers = EXPECTED[str(idx)]['answers']
        claims = []
        for label, key in spec['claims']:
            if key not in answers:
                raise SystemExit(f'task {idx}: no expected answer for {key}')
            pattern = claim_regex(answers[key])
            if not pattern:
                raise SystemExit(f'task {idx}: empty claim for {key}')
            claims.append([label, pattern])
        entry = {
            'task': task['ques'],
            'initial_digest': initial_digest,
            'paths': spec['paths'],
            'claims': claims,
            'state': spec['state'],
        }
        if 'answer_state' in spec:
            entry['answer_state'] = spec['answer_state']
        contract[task['id']] = entry
    out = SITE / 'verify' / 'contract.json'
    out.write_text(json.dumps(contract, indent=1, sort_keys=True) + '\n',
                   encoding='utf-8')
    print(f'wrote {out} ({len(contract)} tasks)')


if __name__ == '__main__':
    main()
