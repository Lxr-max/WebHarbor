"""Task-specific state deltas and evidence identity, independent of answer keywords.

The frozen contract is reviewer ground truth. Input and final DBs are read-only;
existing rows and all unrelated tables must remain unchanged. Unspecified
pickup times and optional sauce/drink choices remain flexible.
"""
from pathlib import Path
from urllib.parse import urlparse
import hashlib
import json
import re
import sqlite3

CONTRACT = json.loads(Path(__file__).with_name('state_contract.json').read_text())


def snapshot(path):
    con = sqlite3.connect(f'file:{Path(path).resolve()}?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    try:
        return {t: [dict(r) for r in con.execute(f'SELECT * FROM "{t}" ORDER BY id')]
                for t, in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")}
    finally:
        con.close()


def normalized(row, table, task):
    row = dict(row)
    for name in ('placed_at', 'created_at'):
        row.pop(name, None)
    if table == 'food_orders' and task in (1, 3):
        for name in ('pickup_date', 'pickup_time'):
            row.pop(name, None)
    if table == 'food_orders' and task == 1:
        for name in ('contact_name', 'contact_phone', 'payment_method'):
            row.pop(name, None)
    if table == 'gear_order_items' and task == 12 and row['product_id'] == 86:
        row['variant_title'] = 'valid' if row['variant_title'] in ('Large', 'Small') else row['variant_title']
    if table == 'gear_order_items' and task == 18 and row['product_id'] == 26:
        row['variant_title'] = 'valid' if row['variant_title'] in ('Red', 'Black', 'Grey') else row['variant_title']
    if table == 'food_order_items':
        choices = json.loads(row['selections'])
        # Task-specific mandatory customization; unspecified options may vary.
        mandatory = {0:['No Slaw (NSL)', 'Large Sweet Tea'], 1:['Family-Style'],
                     4:['No Drink'], 5:['Milk'], 9:['Family-Style'],
                     10:['Regular Sweet Tea']}.get(task, [])
        row['selections'] = [x for x in mandatory if any(x in choice for choice in choices)]
    return row


def check(judge, args, traj):
    n = int(judge.task_id.rsplit('--', 1)[1])
    judge.check('task_identity', traj.get('task_id') == judge.task_id, 'task must match verifier')
    judge.check('completed', traj.get('terminated') and traj.get('termination_reason') == 'agent_done', 'completed browser run')
    start = urlparse(traj.get('start_url', ''))
    origin = (start.scheme, start.hostname, start.port)
    urls = [traj.get('start_url', ''), traj.get('final_url', '')]
    for step in traj.get('steps', []):
        urls.extend(step[k] for k in ('url', 'url_before', 'url_after') if step.get(k))
    valid_origin = start.scheme in ('http', 'https') and start.hostname in ('localhost', '127.0.0.1', '::1')
    judge.check('same_origin', valid_origin and all((urlparse(u).scheme, urlparse(u).hostname, urlparse(u).port) == origin for u in urls if u), 'all evidence is on the preview origin')
    try:
        from PIL import Image
        shots = list((Path(args.run_dir) / 'screenshots').glob('step_*.png'))
        assert shots
        for p in shots:
            with Image.open(p) as image:
                assert image.format == 'PNG'
                image.verify()
        judge.check('screenshots_decode', True)
    except Exception as exc:
        judge.check('screenshots_decode', False, str(exc))
    before = snapshot(args.initial_db); after = snapshot(args.after_db)
    judge.check('frozen_initial_state', hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest() == CONTRACT['seed_sha'], 'seed rows and tables')
    rules = CONTRACT['tasks'][str(n)]
    judge.check('same_tables', set(before) == set(after), 'schema table inventory')
    for table, rows in before.items():
        original = {r['id']:r for r in rows}; actual = {r['id']:r for r in after.get(table, [])}
        rule = rules.get(table, {'added':[], 'removed':[], 'updated':[]})
        expected = dict(original)
        for row in rule['removed']:
            expected.pop(row['id'], None)
        for pair in rule['updated']:
            expected[pair['after']['id']] = pair['after']
        for row in rule['added']:
            expected[row['id']] = row
        # Pre-existing rows are exact; only fields not specified by the task
        # may vary in newly created orders.
        new_ids = {r['id'] for r in rule['added']}
        def normalize(values):
            if table in ('food_order_items', 'gear_order_items'):
                old = {id:row for id,row in values.items() if id not in new_ids}
                new = []
                for id,row in values.items():
                    if id in new_ids:
                        row = normalized(row, table, n); row.pop('id', None)
                        new.append(row)
                return old, sorted(new, key=lambda row: json.dumps(row, sort_keys=True))
            return {id:(normalized(row, table, n) if id in new_ids else row) for id,row in values.items()}

        judge.check('exact_delta_' + table, normalize(actual) == normalize(expected), 'only the requested rows and fields may change')
    answer = traj.get('final_answer', '')
    reported = re.findall(r'\b(?:RC|GEAR)-\d+\b', answer)
    for ref in reported:
        found = any(r.get('order_number') == ref for table in ('food_orders','gear_orders') for r in after[table])
        judge.check('reported_order_exists', found, ref)
    for table in ('food_orders','gear_orders'):
        old = {r['id'] for r in before[table]}
        for row in after[table]:
            if row['id'] not in old:
                judge.check('order_confirmation', any('/confirmation/'+row['order_number'] in u for u in urls), 'visit the actual confirmation')
