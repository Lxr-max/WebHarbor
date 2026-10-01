#!/usr/bin/env python3
"""Build the tracked verify/contract.json for the steam mirror.

Derives, per task: the exact task wording, the canonical digest of the
reviewed seed database, the page-evidence patterns of the honest path, the
factual claims (regexes generated from the answers the honest-path audit
collected), and the exact database deltas the task's saved changes must
produce. Byte-reproducible: no wall clock, no RNG, stable ordering.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
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
ST_RE = r'ST-[0-9]+'

# ---------------------------------------------------------------- helpers --

def claim_pattern(value):
    """A regex that matches this expected answer inside normed text."""
    text = CE.norm(value)
    if re.fullmatch(r'\d+', text):
        return r'\b' + re.escape(text) + r'\b'
    return re.escape(text)


def claims_for(task_id, pairs):
    """(label, answer-key) pairs -> (label, regex) claim list."""
    answers = EXPECTED[task_id]
    out = []
    for label, key in pairs:
        if key not in answers:
            raise SystemExit(f'{task_id}: expected answer {key!r} missing')
        out.append([label, claim_pattern(answers[key])])
    return out


def seed_snapshot():
    """Seed a fresh DB and return (digest, sqlite connection) for id maps."""
    root = Path(tempfile.mkdtemp(prefix='steam-contract-', dir='/tmp'))
    os.environ['STEAM_DB_URI'] = f'sqlite:///{root / "steam.db"}'
    os.environ.pop('WEBSYN_SKIP_BOOTSTRAP', None)
    for mod in list(sys.modules):
        if mod.startswith(('app', 'seed')):
            del sys.modules[mod]
    import app as A
    with A.app.app_context():
        A.db.create_all()
        A.seed_database()
        A.seed_benchmark_users()
    data = CE.database(root / 'steam.db')
    return CE.digest(data), root, data


def game_pk(data, appid):
    for key, row in data['games'].items():
        if row['appid'] == appid:
            return row['id']
    raise SystemExit(f'appid {appid} not in seed')


def wishlist_pk(data, user_id, appid):
    gid = game_pk(data, appid)
    for key, row in data['wishlist_items'].items():
        if row['user_id'] == user_id and row['game_id'] == gid:
            return json.loads(key)[0]
    raise SystemExit(f'wishlist row user={user_id} appid={appid} not in seed')


def wish_added(user_id, appid, data, ts_regex=TS_RE):
    return {'id': {'regex': r'[1-9][0-9]*'}, 'user_id': user_id,
            'game_id': game_pk(data, appid), 'added_ts': {'regex': ts_regex}}


# -------------------------------------------------------------------- main --

def main():
    digest, root, data = seed_snapshot()

    S = {}

    S['Steam--0'] = {
        'paths': [r'/search/\?', r'specials=1', r'sort=Price_ASC',
                  r'/app/582660/', r'/account/login/', r'/wishlist/',
                  r'/wishlist/'],
        'claims': claims_for('Steam--0', [
            ('rpg count', 'rpg_count'), ('discounted rpgs', 'on_sale'),
            ('cheapest name', 'cheapest_name'),
            ('cheapest price', 'cheapest_price'),
            ('review summary', 'review_desc'), ('release date', 'release_date'),
            ('total reviews', 'total_reviews'), ('wishlist count', 'wishlist')]),
        'state': {'wishlist_items': {'added': [wish_added(1, 582660, data)]}},
    }
    S['Steam--1'] = {
        'paths': [r'/search/\?.*os=linux', r'specials=1', r'sort=Price_DESC',
                  r'/app/281990/', r'/account/login/', r'/wishlist/',
                  r'/wishlist/'],
        'claims': claims_for('Steam--1', [
            ('linux specials count', 'count'),
            ('expensive name', 'expensive_name'),
            ('expensive price', 'expensive_price'),
            ('expensive discount', 'expensive_discount'),
            ('minimum os', 'min_os'), ('review summary', 'review_desc'),
            ('all specials', 'all_specials'), ('wishlist count', 'wishlist')]),
        'state': {'wishlist_items': {'added': [wish_added(2, 281990, data)]}},
    }
    S['Steam--2'] = {
        'paths': [r'/search/\?.*term=counter', r'/app/730/', r'/app/570/',
                  r'/app/570/reviews/\?.*filter=positive', r'/account/login/',
                  r'/wishlist/', r'/wishlist/'],
        'claims': claims_for('Steam--2', [
            ('cs2 ram', 'cs2_ram'), ('dota ram', 'dota_ram'),
            ('more ram', 'more_ram'), ('cs2 release', 'cs2_release'),
            ('cs2 review', 'cs2_review'), ('positive shown', 'positive_shown'),
            ('recent positive author', 'recent_positive_author'),
            ('wishlist count', 'wishlist')]),
        'state': {'wishlist_items': {'added': [wish_added(2, 570, data),
                                               wish_added(2, 730, data)]}},
    }
    S['Steam--3'] = {
        'paths': [r'/account/login/', r'/wishlist/', r'/wishlist/',
                  r'/search/\?.*term=hades', r'/app/1145350/',
                  r'/search/\?.*genre=Casual', r'/app/1794680/'],
        'claims': claims_for('Steam--3', [
            ('hades ii price', 'hades2_price'),
            ('hades ii discount', 'hades2_discount'),
            ('hades ii release', 'hades2_release'),
            ('cheap casual name', 'cheap_name'),
            ('cheap casual price', 'cheap_price'),
            ('remaining games', 'remaining'), ('wishlist count', 'wishlist')]),
        'state': {'wishlist_items': {
            'removed': [json.dumps([wishlist_pk(data, 3, 105600)])],
            'added': [wish_added(3, 1145350, data),
                      wish_added(3, 1794680, data)]}},
    }
    S['Steam--4'] = {
        'paths': [r'/search/\?.*term=elden', r'/cart/', r'/app/620/',
                  r'/bundle/234/', r'/cart/', r'/cart/', r'/account/login/',
                  r'/checkout/', r'/order/'],
        'claims': claims_for('Steam--4', [
            ('bundle price', 'bundle_price'), ('subtotal', 'subtotal'),
            ('order number', 'order_no'), ('total', 'total')]),
        'state': {
            'orders': {'added': [{
                'id': {'regex': r'[1-9][0-9]*'}, 'order_no': {'regex': ST_RE},
                'user_id': 2, 'email': 'bob.s@test.com',
                'full_name': 'Bob Smith', 'address1': '7 Coast Road',
                'city': 'Austin', 'state': 'TX', 'zipcode': '78701',
                'payment_method': 'Mastercard', 'subtotal': 13496,
                'tax': 0, 'total': 13496, 'placed_at': {'regex': TS_RE}}]},
            'order_items': {'added': [
                {'id': {'regex': r'[1-9][0-9]*'},
                 'order_id': {'regex': r'[1-9][0-9]*'},
                 'kind': 'game', 'game_id': game_pk(data, 1245620),
                 'bundle_id': None, 'title': 'ELDEN RING',
                 'unit_price': 5999, 'qty': 2},
                {'id': {'regex': r'[1-9][0-9]*'},
                 'order_id': {'regex': r'[1-9][0-9]*'},
                 'kind': 'bundle', 'game_id': None,
                 'bundle_id': {'regex': r'[1-9][0-9]*'},
                 'title': 'Portal Bundle', 'unit_price': 1498, 'qty': 1}]},
        },
        'answer_state': [['orders', 'order_no']],
    }
    S['Steam--5'] = {
        'paths': [r'/specials/', r'/app/582660/', r'/specials/\?.*genre=Indie',
                  r'/specials/\?.*os=mac', r'/specials/\?.*sort=Price_ASC',
                  r'/app/2958130/', r'/account/login/', r'/wishlist/',
                  r'/wishlist/'],
        'claims': claims_for('Steam--5', [
            ('specials count', 'specials_count'),
            ('top1 name', 'top1_name'), ('top1 discount', 'top1_discount'),
            ('top1 final', 'top1_final'), ('top1 original', 'top1_original'),
            ('top1 savings', 'top1_savings'), ('top2 discount', 'top2_discount'),
            ('top2 final', 'top2_final'), ('top2 original', 'top2_original'),
            ('top2 savings', 'top2_savings'), ('indie sale', 'indie_sale'),
            ('mac sale', 'mac_sale'), ('cheapest special', 'cheapest_special'),
            ('cheapest price', 'cheapest_price'),
            ('expensive special', 'expensive_special'),
            ('expensive price', 'expensive_price'),
            ('expensive review', 'expensive_review'),
            ('review summary', 'review_desc'), ('release date', 'release_date'),
            ('wishlist count', 'wishlist')]),
        'state': {'wishlist_items': {'added': [wish_added(3, 582660, data)]}},
    }
    S['Steam--6'] = {
        'paths': [r'/search/\?.*term=stellaris', r'/app/281990/',
                  r'/app/281990/reviews/', r'filter=negative', r'sort=helpful',
                  r'/news/281990/', r'/account/login/', r'/wishlist/',
                  r'/wishlist/'],
        'claims': claims_for('Steam--6', [
            ('review summary', 'review_desc'), ('total reviews', 'total_reviews'),
            ('negative count', 'negative_count'),
            ('recent author', 'recent_author'), ('recent playtime', 'recent_playtime'),
            ('helpful author', 'helpful_author'), ('price', 'price'),
            ('discount', 'discount'), ('newest news', 'newest_news'),
            ('wishlist count', 'wishlist')]),
        'state': {'wishlist_items': {'added': [wish_added(2, 281990, data)]}},
    }
    S['Steam--7'] = {
        'paths': [r'/search/\?.*term=counter', r'/app/730/',
                  r'/developer/valve/', r'/app/546560/', r'/app/570/',
                  r'/app/440/', r'/cart/', r'/cart/', r'/cart/',
                  r'/publisher/valve/', r'/account/login/', r'/wishlist/',
                  r'/wishlist/'],
        'claims': claims_for('Steam--7', [
            ('valve count', 'valve_count'),
            ('most expensive', 'most_expensive'),
            ('most expensive price', 'most_expensive_price'),
            ('free count', 'free_count'), ('free games', 'free_games'),
            ('cs2 release', 'cs2_release'), ('cs2 review', 'cs2_review'),
            ('dota release', 'dota_release'), ('dota review', 'dota_review'),
            ('tf2 release', 'tf2_release'), ('tf2 review', 'tf2_review'),
            ('alyx release', 'alyx_release'), ('alyx review', 'alyx_review'),
            ('publisher count', 'publisher_count'),
            ('wishlist count', 'wishlist')]),
        'state': {'wishlist_items': {'added': [wish_added(4, 546560, data)]}},
    }
    S['Steam--8'] = {
        'paths': [r'/search/\?.*term=counter', r'/app/730/', r'/news/730/',
                  r'/news/item/', r'/search/\?.*term=dota', r'/app/570/',
                  r'/news/570/', r'/account/login/', r'/wishlist/',
                  r'/wishlist/'],
        'claims': claims_for('Steam--8', [
            ('cs2 news title', 'cs2_news_title'),
            ('cs2 news feed', 'cs2_news_feed'), ('cs2 news date', 'cs2_news_date'),
            ('dota news title', 'dota_news_title'),
            ('dota news date', 'dota_news_date'),
            ('more recent', 'more_recent'), ('cs2 price', 'cs2_price'),
            ('cs2 review', 'cs2_review'), ('wishlist count', 'wishlist')]),
        'state': {'wishlist_items': {'added': [wish_added(3, 570, data)]}},
    }
    S['Steam--9'] = {
        'paths': [r'/search/\?.*term=portal', r'/app/620/', r'/bundle/234/',
                  r'/cart/', r'/cart/', r'/account/login/', r'/checkout/',
                  r'/order/'],
        'claims': claims_for('Steam--9', [
            ('bundle price', 'bundle_price'),
            ('separate total', 'separate_total'), ('savings', 'savings'),
            ('subtotal', 'subtotal'), ('order number', 'order_no'),
            ('total', 'total'), ('line item', 'line_item')]),
        'state': {
            'orders': {'added': [{
                'id': {'regex': r'[1-9][0-9]*'}, 'order_no': {'regex': ST_RE},
                'user_id': 1, 'email': 'alice.j@test.com',
                'full_name': 'Alice Johnson', 'address1': '42 Pipeline Way',
                'city': 'Bellevue', 'state': 'WA', 'zipcode': '98004',
                'payment_method': 'Visa', 'subtotal': 1498, 'tax': 0,
                'total': 1498, 'placed_at': {'regex': TS_RE}}]},
            'order_items': {'added': [{
                'id': {'regex': r'[1-9][0-9]*'},
                'order_id': {'regex': r'[1-9][0-9]*'},
                'kind': 'bundle', 'game_id': None,
                'bundle_id': {'regex': r'[1-9][0-9]*'},
                'title': 'Portal Bundle', 'unit_price': 1498, 'qty': 1}]},
        },
        'answer_state': [['orders', 'order_no']],
    }
    S['Steam--10'] = {
        'paths': [r'/account/signup/', r'/search/\?.*maxprice=free',
                  r'/app/440/', r'/wishlist/', r'/account/login/'],
        'claims': claims_for('Steam--10', [
            ('free count', 'free_count'), ('game', 'game'),
            ('review summary', 'review_desc'), ('total reviews', 'total_reviews'),
            ('wishlist count', 'wishlist'), ('persisted', 'persisted')]),
        'state': {
            'users': {'added': [{
                'id': {'regex': r'[1-9][0-9]*'}, 'name': 'Frank Nova',
                'email': 'frank.n@test.com',
                'pw_hash': {'regex': r'\$2b\$12\$[./A-Za-z0-9]{53}'}}]},
            'wishlist_items': {'added': [{
                'id': {'regex': r'[1-9][0-9]*'},
                'user_id': {'regex': r'[1-9][0-9]*'},
                'game_id': game_pk(data, 440), 'added_ts': {'regex': TS_RE}}]},
        },
    }
    S['Steam--11'] = {
        'paths': [r'/genre/indie/', r'sort=Released_DESC', r'sort=Price_DESC',
                  r'/app/250760/', r'maxprice=15', r'/app/1867240/',
                  r'/app/1867240/reviews/', r'/account/login/',
                  r'/wishlist/', r'/wishlist/'],
        'claims': claims_for('Steam--11', [
            ('indie count', 'indie_count'), ('newest name', 'newest_name'),
            ('newest price', 'newest_price'),
            ('most expensive', 'most_expensive'),
            ('most expensive price', 'most_expensive_price'),
            ('shovel release', 'shovel_release'), ('under 15', 'under15'),
            ('review summary', 'review_desc'), ('newest reviews', 'newest_reviews_desc'),
            ('discounted', 'discounted'), ('wishlist count', 'wishlist')]),
        'state': {'wishlist_items': {'added': [wish_added(4, 1867240, data)]}},
    }
    S['Steam--12'] = {
        'paths': [r'/account/login/', r'/account/', r'/search/\?.*term=left',
                  r'/cart/', r'/cart/', r'/checkout/', r'/order/'],
        'claims': claims_for('Steam--12', [
            ('existing order', 'existing_order'), ('existing total', 'existing_total'),
            ('new order', 'new_order'), ('new total', 'new_total'),
            ('order count', 'order_count')]),
        'state': {
            'orders': {'added': [{
                'id': {'regex': r'[1-9][0-9]*'}, 'order_no': {'regex': ST_RE},
                'user_id': 1, 'email': 'alice.j@test.com',
                'full_name': 'Alice Johnson', 'address1': '42 Pipeline Way',
                'city': 'Bellevue', 'state': 'WA', 'zipcode': '98004',
                'payment_method': 'Visa', 'subtotal': 999, 'tax': 0,
                'total': 999, 'placed_at': {'regex': TS_RE}}]},
            'order_items': {'added': [{
                'id': {'regex': r'[1-9][0-9]*'},
                'order_id': {'regex': r'[1-9][0-9]*'},
                'kind': 'game', 'game_id': game_pk(data, 550),
                'bundle_id': None, 'title': 'Left 4 Dead 2',
                'unit_price': 999, 'qty': 1}]},
        },
        'answer_state': [['orders', 'order_no']],
    }
    S['Steam--13'] = {
        'paths': [r'/search/\?.*genre=Action', r'review_type=mixed',
                  r'sort=Price_ASC', r'/app/1912410/', r'/app/1912410/reviews/',
                  r'/app/2246340/', r'/account/login/', r'/wishlist/',
                  r'/wishlist/'],
        'claims': claims_for('Steam--13', [
            ('count', 'count'), ('names', 'names'),
            ('cheap name', 'cheap_name'), ('cheap price', 'cheap_price'),
            ('expensive name', 'exp_name'), ('expensive price', 'exp_price'),
            ('minimum os', 'min_os'), ('minimum processor', 'min_cpu'),
            ('minimum ram', 'min_ram'),
            ('total reviews', 'total_reviews'), ('positive pct', 'cheap_pct'),
            ('expensive ram', 'exp_min_ram'), ('wishlist count', 'wishlist')]),
        'state': {'wishlist_items': {'added': [wish_added(1, 1912410, data)]}},
    }
    S['Steam--14'] = {
        'paths': [r'/search/\?.*maxprice=free', r'/app/570/', r'/app/730/',
                  r'/app/440/', r'/account/login/', r'/wishlist/',
                  r'/wishlist/'],
        'claims': claims_for('Steam--14', [
            ('free count', 'free_count'), ('dota review', 'dota_review'),
            ('dota pct', 'dota_pct'), ('dota total', 'dota_total'),
            ('cs2 review', 'cs2_review'), ('cs2 pct', 'cs2_pct'),
            ('cs2 total', 'cs2_total'), ('tf2 review', 'tf2_review'),
            ('higher pct', 'higher'), ('wishlist count', 'wishlist')]),
        'state': {'wishlist_items': {'added': [wish_added(4, 570, data),
                                               wish_added(4, 730, data),
                                               wish_added(4, 440, data)]}},
    }
    S['Steam--15'] = {
        'paths': [r'/search/\?.*term=dead', r'/app/588650/', r'/app/1204130/',
                  r'/cart/', r'/cart/', r'/cart/', r'/bundle/30317/',
                  r'/cart/', r'/bundle/46406/'],
        'claims': claims_for('Steam--15', [
            ('dlc count', 'dlc_count'), ('first dlc', 'first_dlc'),
            ('first dlc price', 'first_dlc_price'),
            ('dlc release', 'dlc_release'), ('dlc subtotal', 'dlc_subtotal'),
            ('dc price', 'dc_price'), ('dc discount', 'dc_discount'),
            ('bundle name', 'bundle_name'), ('bundle price', 'bundle_price'),
            ('bundle items', 'bundle_items'), ('subtotal', 'subtotal'),
            ('cart after', 'cart_after'), ('triple total', 'triple_total'),
            ('second bundle', 'second_bundle'),
            ('second bundle price', 'second_bundle_price')]),
    }
    S['Steam--16'] = {
        'paths': [r'/search/\?.*term=resident', r'genre=Action',
                  r'/app/883710/', r'/app/1196590/', r'/app/2050650/',
                  r'/app/2050650/reviews/', r'/news/2050650/',
                  r'/account/login/', r'/wishlist/', r'/wishlist/'],
        'claims': claims_for('Steam--16', [
            ('count', 'count'), ('refined', 'refined'), ('names', 'names'),
            ('re2 price', 're2_price'), ('re2 release', 're2_release'),
            ('village price', 'village_price'),
            ('village release', 'village_release'),
            ('re4 price', 're4_price'), ('re4 release', 're4_release'),
            ('most recent', 'most_recent'), ('re4 review', 're4_review'),
            ('re4 news', 're4_news'), ('wishlist count', 'wishlist')]),
        'state': {'wishlist_items': {'added': [wish_added(3, 2050650, data)]}},
    }
    S['Steam--17'] = {
        'paths': [r'/search/\?.*term=hades', r'/app/1145360/', r'/app/1145350/',
                  r'/app/1145350/reviews/\?.*filter=positive', r'/cart/',
                  r'/cart/', r'/cart/', r'/account/login/',
                  r'/wishlist/', r'/wishlist/'],
        'claims': claims_for('Steam--17', [
            ('count', 'count'), ('hades price', 'hades_price'),
            ('hades discount', 'hades_discount'), ('hades original', 'hades_original'),
            ('hades release', 'hades_release'), ('hades review', 'hades_review'),
            ('hades2 price', 'hades2_price'), ('hades2 discount', 'hades2_discount'),
            ('hades2 original', 'hades2_original'), ('hades2 release', 'hades2_release'),
            ('hades2 review', 'hades2_review'), ('cheaper', 'cheaper'),
            ('both mac', 'both_mac'),
            ('recent positive author', 'recent_positive_author'),
            ('cart subtotal', 'cart_subtotal'), ('wishlist count', 'wishlist')]),
        'state': {'wishlist_items': {'added': [wish_added(1, 1145350, data)]}},
    }
    S['Steam--18'] = {
        'paths': [r'/specials/', r'/app/1462040/', r'/app/1145360/',
                  r'/cart/', r'/cart/', r'/account/login/', r'/checkout/',
                  r'/order/'],
        'claims': claims_for('Steam--18', [
            ('ff7 discount', 'ff7_discount'), ('ff7 final', 'ff7_final'),
            ('ff7 original', 'ff7_original'), ('ff7 savings', 'ff7_savings'),
            ('hades discount', 'hades_discount'), ('hades final', 'hades_final'),
            ('hades original', 'hades_original'), ('hades savings', 'hades_savings'),
            ('subtotal', 'subtotal'), ('order number', 'order_no'),
            ('total', 'total'), ('items', 'items')]),
        'state': {
            'orders': {'added': [{
                'id': {'regex': r'[1-9][0-9]*'}, 'order_no': {'regex': ST_RE},
                'user_id': 4, 'email': 'dana.k@test.com',
                'full_name': 'Dana Kim', 'address1': '88 Neon Street',
                'city': 'Seattle', 'state': 'WA', 'zipcode': '98101',
                'payment_method': 'PayPal', 'subtotal': 1623, 'tax': 0,
                'total': 1623, 'placed_at': {'regex': TS_RE}}]},
            'order_items': {'added': [
                {'id': {'regex': r'[1-9][0-9]*'},
                 'order_id': {'regex': r'[1-9][0-9]*'},
                 'kind': 'game', 'game_id': game_pk(data, 1462040),
                 'bundle_id': None,
                 'title': 'FINAL FANTASY VII REMAKE INTERGRADE',
                 'unit_price': 999, 'qty': 1},
                {'id': {'regex': r'[1-9][0-9]*'},
                 'order_id': {'regex': r'[1-9][0-9]*'},
                 'kind': 'game', 'game_id': game_pk(data, 1145360),
                 'bundle_id': None, 'title': 'Hades', 'unit_price': 624,
                 'qty': 1}]},
        },
        'answer_state': [['orders', 'order_no']],
    }
    S['Steam--19'] = {
        'paths': [r'/search/\?.*term=cyberpunk', r'/app/1091500/',
                  r'/search/\?.*term=elden', r'/app/1245620/',
                  r'/app/1091500/reviews/', r'/cart/', r'/cart/',
                  r'/cart/', r'/account/login/', r'/wishlist/',
                  r'/wishlist/'],
        'claims': claims_for('Steam--19', [
            ('cp min ram', 'cp_min_ram'), ('cp rec ram', 'cp_rec_ram'),
            ('cp gpu', 'cp_gpu'), ('cp storage', 'cp_storage'),
            ('er min ram', 'er_min_ram'), ('er rec ram', 'er_rec_ram'),
            ('er gpu', 'er_gpu'), ('er storage', 'er_storage'),
            ('more storage', 'more_storage'), ('mac game', 'mac_game'),
            ('er price', 'er_price'), ('er review', 'er_review'),
            ('cp review', 'cp_review'), ('cp shown', 'cp_shown'),
            ('cart subtotal', 'cart_subtotal'), ('wishlist count', 'wishlist')]),
        'state': {'wishlist_items': {'added': [wish_added(4, 1245620, data)]}},
    }

    contract = {}
    for task in TASKS:
        task_id = task['id']
        spec = S[task_id]
        contract[task_id] = {
            'task': task['ques'],
            'initial_digest': digest,
            'paths': spec['paths'],
            'claims': spec['claims'],
            'state': spec.get('state', {}),
        }
        if 'answer_state' in spec:
            contract[task_id]['answer_state'] = spec['answer_state']

    out = SITE / 'verify' / 'contract.json'
    out.write_text(json.dumps(contract, indent=1, sort_keys=True) + '\n',
                   encoding='utf-8')
    shutil.rmtree(root, ignore_errors=True)
    print(f'[contract] {len(contract)} tasks, digest {digest[:16]}…, '
          f'written to verify/contract.json')


if __name__ == '__main__':
    main()
