#!/usr/bin/env python3
"""verify_lib.py — deterministic verifier utilities for samsung task
verification (reviewer contract, orch/review/samsung).

Philosophy: DETERMINISTIC FIRST. No LLM call is load-bearing; every check is
regex / token / SQLite after-state.

  1. Package identity (fail-closed): task_id matches, ``terminated`` with
     ``agent_done``, non-empty final answer, every recorded URL on the same
     loopback origin AND port as ``start_url``, every referenced screenshot a
     decodable PNG.
  2. Seed identity gate (fail-closed): the initial DB snapshot must BE the
     frozen in-image seed (file md5 + per-table counts + schema digest + rows
     digest). A run graded against a pre-mutated database fails here.
  3. Navigation gates (anti knowledge-shortcut): the agent MUST have opened
     the on-site surfaces the task names (catalogs with their filters, product
     and buy pages, compare, support/warranty, orders, account). A correct
     answer with no matching navigation is a memory-recall shortcut = FAIL.
  4. Answer check: affirmative token / phrase / number matching against
     ground truth HARDCODED in each ``verify_<n>.py`` (never in tasks.jsonl).
     r2 re-freeze (fix commit fac9a96e): the two r1 grounding defects are
     fixed at the render layer — the product spec table renders the
     unlabeled Battery-group value row, and Galaxy Compare's route reads the
     full ``models`` parameter list so a real form submit renders every
     checked model as its own column — so the r1 honest-absence gradings for
     those slots became POSITIVE anchors, re-frozen from the reviewer's r2
     two-round walks. Stale r1-style absence answers and the old wrong
     heavier-model claim FAIL via the per-task ``forbidden`` patterns.
  5. DB after-state: read-only tasks require every table row-identical to the
     seed; stateful tasks require the exact allowed row delta and nothing
     else.

Seed reproducibility: the samsung seed is rebuilt deterministically inside
the pinned image (PYTHONHASHSEED=0, frozen bcrypt benchmark password). The
r2 review image (webharbor:samsung-r2, built independently by the reviewer
from orch/contribute/samsung @ fac9a96e via the real Dockerfile's samsung
site block: 644-asset inventory gate -> deterministic seed ->
instance_seed freeze -> seed-database check) reproduces seed md5
cc018b53658bfb13f07637892409287a byte-identically with the r1 frozen
fingerprint and the contributor's declared seed; every per-task reset
snapshot is byte-identical (40-reset byte-identity re-proven in r2).

Input signature (per task):
  --run_dir DIR        agent trajectory dir: trajectory.json + screenshots/
  --initial_db PATH    initial-state SQLite DB (default: <run_dir>/initial.db)
  --after_db PATH      after-state  SQLite DB (default: <run_dir>/after.db)
Output: JSON {task_id, pass, reason, evidence[]} to stdout; exit 0 on PASS,
1 on FAIL.
"""
import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlsplit

SITE = "samsung"

# ---- frozen seed identity (computed from the in-image instance_seed) -------
SEED_MD5 = "cc018b53658bfb13f07637892409287a"
SEED_COUNTS = {
    "cart_items": 0, "categories": 8, "config_products": 213,
    "config_relations": 6, "heroes": 4, "order_items": 3, "orders": 3,
    "product_specs": 1775, "products": 505, "site_search": 505,
    "support_tickets": 2, "users": 4, "warranty_categories": 5,
    "warranty_faqs": 7, "warranty_terms": 0, "wishlist_items": 7,
}
SEED_SCHEMA_SHA256 = ("e2b5780fc1f113177b48ee8ca712253e"
                     "3de26875cfcc81114edf09ecf3b0c714")
SEED_ROWS_SHA256 = ("8569b3b6f2538327a50bcd4e52237b88"
                    "68d23a01c79639b062993bfd70773b1f")


def norm(text):
    """Normalize an answer string for deterministic matching."""
    text = str(text).replace('|', ' ').replace('**', '').casefold()
    for a, b in (('\u201d', '"'), ('\u201c', '"'), ('\u2019', "'"),
                 ('\u2013', '-'), ('\u2014', '-'), ('\u2212', '-'),
                 ('\u00ae', ''), ('\u2122', ''), ('\u2120', ''),
                 ('\u00b7', ' '), ('\u2026', '...')):
        text = text.replace(a, b)
    text = re.sub(r'(?<=\d),(?=\d)', '', text)          # 3,599.98 -> 3599.98
    text = re.sub(r'\$\s*', '$', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def load_db(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError('Missing saved database: ' + path.name)
    con = sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    try:
        if con.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Corrupt database: ' + path.name)
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        data = {}
        schema_parts = []
        for t in tables:
            cols = [(r[1], r[2]) for r in con.execute(f'PRAGMA table_info("{t}")')]
            schema_parts.append([t, cols])
            pk = [r[1] for r in sorted(con.execute(f'PRAGMA table_info("{t}")'),
                                        key=lambda r: r[5]) if r[5]]
            keys = pk or [c[0] for c in cols]
            rows = {}
            for r in con.execute(f'SELECT * FROM "{t}"'):
                d = dict(r)
                rows[json.dumps([d[k] for k in keys], default=str)] = d
            data[t] = rows
        return data, schema_parts
    finally:
        con.close()


def db_counts(data):
    return {t: len(rows) for t, rows in data.items()}


def schema_digest(schema_parts):
    return hashlib.sha256(json.dumps(
        schema_parts, sort_keys=True, default=str).encode()).hexdigest()


def rows_digest(data):
    payload = [[t, [[k, row] for k, row in rows.items()]]
               for t, rows in sorted(data.items())]
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, default=str).encode()).hexdigest()


def file_md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def png_ok(path):
    try:
        from PIL import Image
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            return im.format == 'PNG'
    except Exception:
        return False


class Fail(Exception):
    pass


def check_package(run, spec):
    if run.get('task_id') != spec['task_id']:
        raise Fail(f"task_id mismatch: {run.get('task_id')!r} != "
                   f"{spec['task_id']!r}")
    if not run.get('terminated'):
        raise Fail('trajectory not terminated')
    if run.get('termination_reason') != 'agent_done':
        raise Fail('termination_reason is not agent_done')
    answer = run.get('final_answer') or ''
    if not str(answer).strip():
        raise Fail('empty final answer')
    start = urlsplit(run.get('start_url') or '')
    if start.hostname not in ('localhost', '127.0.0.1'):
        raise Fail('start_url is not loopback: ' + str(run.get('start_url')))
    port = start.port or 80
    urls = []
    for step in run.get('steps') or []:
        for key in ('url', 'url_after'):
            u = (step or {}).get(key)
            if u:
                urls.append(u)
    for u in urls:
        if u == 'about:blank':
            continue  # the fresh tab's pre-navigation URL, not a target
        p = urlsplit(u)
        if p.hostname not in ('localhost', '127.0.0.1') or \
                (p.port or 80) != port:
            raise Fail('off-origin or cross-port URL in trajectory: ' + u)
    shots = set()
    for step in run.get('steps') or []:
        for key in ('screenshot_before', 'screenshot_after'):
            s = (step or {}).get(key)
            if s:
                shots.add(s)
    if not shots:
        raise Fail('no screenshots in trajectory')
    for s in sorted(shots):
        p = Path(run.get('_run_dir', '.')) / 'screenshots' / s
        if not p.is_file():
            raise Fail('missing screenshot: ' + s)
        if not png_ok(p):
            raise Fail('screenshot is not a decodable PNG: ' + s)
    return urls


def check_seed(initial_db):
    if file_md5(initial_db) != SEED_MD5:
        raise Fail('initial database is not the frozen seed '
                   '(md5 ' + file_md5(initial_db) + ')')
    data, schema = load_db(initial_db)
    counts = db_counts(data)
    if counts != SEED_COUNTS:
        raise Fail('seed table counts differ: ' + json.dumps(counts))
    if schema_digest(schema) != SEED_SCHEMA_SHA256:
        raise Fail('seed schema digest differs')
    if rows_digest(data) != SEED_ROWS_SHA256:
        raise Fail('seed rows digest differs')
    return data


def check_navigation(urls, spec):
    joined = '\n'.join(urls)
    for pattern in spec.get('paths', []):
        if not re.search(pattern, joined, re.I):
            raise Fail('navigation gate: required surface not visited: '
                       + pattern)


def check_answer(answer, spec):
    text = norm(answer)
    for label, pattern in spec.get('claims', []):
        if not re.search(pattern, text, re.I):
            raise Fail(f'answer claim missing: {label} (pattern {pattern!r})')
    for label, pattern in spec.get('forbidden', []):
        if re.search(pattern, text, re.I):
            raise Fail(f'answer contains fabricated/unreachable value '
                       f'for: {label}')


def row_matches(row, expect):
    """expect: dict of column matchers (value, regex: or one_of:)."""
    for col, want in expect.items():
        if col not in row:
            return False
        value = row[col]
        if isinstance(want, dict):
            if 'regex' in want:
                if re.fullmatch(want['regex'], str(value), re.I) is None:
                    return False
            elif 'one_of' in want:
                if str(value) not in want['one_of']:
                    return False
            else:
                return False
        elif str(value) != str(want):
            return False
    return True


def check_state(initial, after, spec):
    diffs = {}
    for table in sorted(set(initial) | set(after)):
        i_rows = initial.get(table, {})
        a_rows = after.get(table, {})
        added = [a_rows[k] for k in a_rows if k not in i_rows]
        removed = [i_rows[k] for k in i_rows if k not in a_rows]
        changed = []
        for k in i_rows:
            if k in a_rows and i_rows[k] != a_rows[k]:
                changed.append((i_rows[k], a_rows[k]))
        if added or removed or changed:
            diffs[table] = {'added': added, 'removed': removed,
                            'changed': changed}
    allowed = spec.get('state', {})
    for table, delta in diffs.items():
        if table not in allowed:
            raise Fail('unexpected DB change in table ' + table + ': '
                       + json.dumps(delta, default=str)[:400])
        for row in delta['added']:
            if not any(row_matches(row, exp) for exp in allowed[table].get('added', [])):
                raise Fail('unexpected added row in ' + table + ': '
                           + json.dumps(row, default=str)[:300])
        if len(delta['added']) != len(allowed[table].get('added', [])):
            raise Fail(f'added-row count mismatch in {table}: '
                       f"{len(delta['added'])} != "
                       f"{len(allowed[table].get('added', []))}")
        for row in delta['removed']:
            if not any(row_matches(row, exp) for exp in allowed[table].get('removed', [])):
                raise Fail('unexpected removed row in ' + table + ': '
                           + json.dumps(row, default=str)[:300])
        if len(delta['removed']) != len(allowed[table].get('removed', [])):
            raise Fail(f'removed-row count mismatch in {table}: '
                       f"{len(delta['removed'])} != "
                       f"{len(allowed[table].get('removed', []))}")
        if delta['changed']:
            raise Fail('unexpected row mutation in ' + table + ': '
                       + json.dumps(delta['changed'], default=str)[:300])
    # every allowed delta must actually be present
    for table, delta in allowed.items():
        if table not in diffs:
            raise Fail('expected state change missing in table ' + table)


def verify(run_dir, spec):
    run_dir = Path(run_dir)
    traj_path = run_dir / 'trajectory.json'
    if not traj_path.is_file():
        raise Fail('missing trajectory.json')
    run = json.loads(traj_path.read_text())
    run['_run_dir'] = str(run_dir)
    initial_db = Path(os.environ.get('WH_INITIAL_DB', '')) if \
        os.environ.get('WH_INITIAL_DB') else run_dir / 'initial.db'
    after_db = Path(os.environ.get('WH_AFTER_DB', '')) if \
        os.environ.get('WH_AFTER_DB') else run_dir / 'after.db'
    evidence = []
    urls = check_package(run, spec)
    evidence.append('package identity ok')
    initial = check_seed(initial_db)
    evidence.append('seed identity ok (md5 ' + SEED_MD5 + ')')
    check_navigation(urls, spec)
    evidence.append('navigation gates ok')
    check_answer(run.get('final_answer') or '', spec)
    evidence.append('answer claims ok')
    after, _schema = load_db(after_db)
    check_state(initial, after, spec)
    evidence.append('db after-state ok')
    return {
        'task_id': spec['task_id'],
        'pass': True,
        'reason': 'all contract checks passed',
        'evidence': evidence,
    }


def main(task_id, spec):
    ap = argparse.ArgumentParser()
    ap.add_argument('--run_dir', required=True)
    ap.add_argument('--initial_db')
    ap.add_argument('--after_db')
    args = ap.parse_args()
    if args.initial_db:
        os.environ['WH_INITIAL_DB'] = args.initial_db
    if args.after_db:
        os.environ['WH_AFTER_DB'] = args.after_db
    try:
        result = verify(args.run_dir, spec)
    except Fail as e:
        print(json.dumps({'task_id': task_id, 'pass': False,
                          'reason': str(e), 'evidence': []}, indent=1))
        return 1
    print(json.dumps(result, indent=1))
    return 0
