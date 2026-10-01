#!/usr/bin/env python3
"""Reviewer verifier library for the yahoo_finance mirror (review track).

Independent of the contributor's verify/contract_engine.py + contract.json:
this library implements the deterministic package/seed/state/claim gates the
review track established (disney/sec/umich reviewer contracts), with ground
truth frozen from the reviewer's own two-round honest Chromium walks of the
independently built review container (webharbor:yf-review, ports
46138/47138/48138, per-task control-plane reset + fresh context; evidence tree
wh-yf-review-evidence/runs/round1|2).

Gates per task package (run directory with trajectory.json, screenshots/,
initial.db, after.db):
  1. identity   — trajectory task_id and question equal the frozen spec;
  2. termination— terminated with reason agent_done;
  3. origin    — start_url is loopback and every recorded step URL stays on
                 that origin;
  4. evidence  — every step carries a decodable full-browser PNG
                 (>= 320x200, non-blank);
  5. paths     — every required page pattern occurs among visited URLs;
  6. seed      — initial.db is the frozen in-image seed (sha256 + table
                 counts), so grading starts from the exact shipped state;
  7. state     — content-multiset diff(initial, after) equals the spec's
                 added/removed rows exactly (rowid-reuse safe: a
                 delete+insert is added+removed, never a row mutation);
                 runtime-generated values (bcrypt hashes of newly created
                 accounts) are shape- and password-checked, never frozen;
  8. claims    — every (label, regex) claim matches the normalized final
                 answer, with negation/contradiction rejection;
  9. forbidden — spec patterns must not appear in the normalized answer.

No LLM, no live-state fallback, fully offline and deterministic.
"""
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit, unquote

# The frozen in-image seed the review container resets to (built by the real
# Dockerfile's yahoo_finance block inside webharbor:yf-review).
SEED_SHA256 = 'c04adf18b4403d3cef65b3a03d9c63277451b7743f81e6c7bbe996fe41ac852d'
SEED_COUNTS = {
    'chart_points': 6734,
    'earnings_events': 902,
    'income_rows': 1126,
    'news_articles': 385,
    'price_alerts': 6,
    'quotes': 318,
    'screener_presets': 6,
    'trending_items': 20,
    'users': 4,
    'watch_items': 14,
}
BCRYPT_RE = re.compile(r'^\$2[aby]\$1[0-9]\$[./A-Za-z0-9]{53}$')


class VerifyError(ValueError):
    pass


def norm(text):
    """Deterministic answer normalization."""
    text = str(text).casefold()
    text = text.replace('\u2212', '-').replace('\u2013', '-').replace(
        '\u2014', '-').replace('\u2019', "'").replace('\u201c', '"').replace(
        '\u201d', '"').replace('\u00ae', '').replace('\u2122', '')
    text = text.replace('&', ' and ')
    text = re.sub(r'\$\s*', '', text)                      # $350 -> 350
    text = re.sub(r'(?<=\d),(?=\d)', '', text)             # 83,452 -> 83452
    text = re.sub(r'(\d)\s*%', r'\1 percent', text)        # 84.92% -> 84.92 percent
    text = re.sub(r'(?<=\d)\s*usd\b', '', text)          # 350 usd -> 350
    text = re.sub(
        r'\b(zero|one|two|three|four|five|six|seven|eight|nine|ten)\b',
        lambda m: str(['zero', 'one', 'two', 'three', 'four', 'five', 'six',
                       'seven', 'eight', 'nine', 'ten'].index(m.group())),
        text)
    return re.sub(r'\s+', ' ', text).strip()


def load_db(path):
    """Read a sqlite database into {table: {rowkey: row-dict}} (read-only)."""
    path = Path(path)
    if not path.is_file():
        raise VerifyError(f'missing database: {path.name}')
    con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    try:
        con.row_factory = sqlite3.Row
        if con.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise VerifyError('corrupt database: ' + path.name)
        data = {}
        for (table,) in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            rows = {}
            for r in con.execute(f'SELECT * FROM "{table}"'):
                d = dict(r)
                key = json.dumps(d, sort_keys=True)
                # content multiset: identical content rows must accumulate
                rows[key] = rows.get(key, 0) + 1
            data[table] = rows
        return data
    finally:
        con.close()


def row_key(row):
    return json.dumps(row, sort_keys=True)


def check_package(run, spec):
    """Gates 1-5: identity, termination, origin, evidence, paths."""
    traj = json.loads((run / 'trajectory.json').read_text(encoding='utf-8'))
    if traj.get('task_id') != spec['task_id']:
        raise VerifyError('wrong task id')
    if traj.get('task', traj.get('ques')) != spec['question']:
        raise VerifyError('stale or modified task question')
    if not traj.get('terminated') or \
            traj.get('termination_reason') != 'agent_done':
        raise VerifyError('unfinished attempt')
    start = urlsplit(traj.get('start_url', ''))
    if start.scheme not in ('http', 'https') or \
            start.hostname not in ('localhost', '127.0.0.1', '::1'):
        raise VerifyError('non-local start url')
    origin = (start.scheme, start.hostname, start.port)
    steps = traj.get('steps') or []
    if not steps:
        raise VerifyError('missing browser evidence')
    urls = []
    shots = 0
    seen = set()
    for step in steps:
        for key in ('url', 'url_before', 'url_after'):
            if key in step:
                u = urlsplit(step[key])
                if step[key] == 'about:blank':
                    continue
                if (u.scheme, u.hostname, u.port) != origin:
                    raise VerifyError('browser evidence changes origin')
        u = urlsplit(step.get('url_after', step.get('url', '')))
        urls.append(unquote(u.path + (('?' + u.query) if u.query else '')))
        for skey in ('screenshot_before', 'screenshot_after', 'screenshot'):
            if skey not in step:
                continue
            name = step.get(skey)
            if not name or Path(name).name != name:
                raise VerifyError('invalid screenshot reference')
            path = run / 'screenshots' / name
            if not path.is_file():
                raise VerifyError('missing screenshot: ' + name)
            if path in seen:
                continue
            seen.add(path)
            # the pre-navigation shot of the initial about:blank start page
            # may legitimately be blank; every real-page shot must not be
            if step.get('url') != 'about:blank' or skey != 'screenshot_before':
                _check_png(path)
            shots += 1
    if shots == 0:
        raise VerifyError('no decoded screenshots')
    for pattern in spec.get('paths', []):
        if not any(re.search(pattern, u, re.I) for u in urls):
            raise VerifyError('required page evidence missing: ' + pattern)
    return traj, urls, shots


def _check_png(path):
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover
        return
    with Image.open(path) as im:
        im.load()
        if im.format != 'PNG' or im.width < 320 or im.height < 200:
            raise VerifyError('screenshot is not a full browser PNG')
        if len(im.convert('RGB').resize((32, 32)).getcolors(1024) or []) < 8:
            raise VerifyError('blank screenshot')


def check_seed(run):
    """Gate 6: the run started from the frozen in-image seed."""
    initial = run / 'initial.db'
    if hashlib.sha256(initial.read_bytes()).hexdigest() != SEED_SHA256:
        raise VerifyError('initial database is not the frozen seed')
    data = load_db(initial)
    for table, count in SEED_COUNTS.items():
        n = sum(data.get(table, {}).values())
        if n != count:
            raise VerifyError(f'seed table {table} has {n} rows, '
                              f'expected {count}')


def diff_state(initial, after):
    """Content-multiset diff: ({table: {key: n}}, removed, added)."""
    removed, added = {}, {}
    for table in set(initial) | set(after):
        a = initial.get(table, {})
        b = after.get(table, {})
        for key, n in a.items():
            if b.get(key, 0) < n:
                removed.setdefault(table, {})[key] = n - b.get(key, 0)
        for key, n in b.items():
            if a.get(key, 0) < n:
                added.setdefault(table, {})[key] = n - a.get(key, 0)
    return removed, added


def _match_row(got, expected):
    """True if got-row content satisfies expected (subset + bcrypt shapes).

    expected values of the form 'SHAPE:bcrypt:<password>' require the got
    value to be a valid bcrypt hash of <password> (runtime-generated salts
    are never frozen literally)."""
    import bcrypt
    for col, want in expected.items():
        if isinstance(want, str) and want.startswith('SHAPE:bcrypt:'):
            pw = want[len('SHAPE:bcrypt:'):]
            h = got.get(col)
            if not isinstance(h, str) or not BCRYPT_RE.match(h) or \
                    not bcrypt.checkpw(pw.encode(), h.encode()):
                return False
        elif got.get(col) != want:
            return False
    return True


def check_state(run, spec):
    """Gate 7: exact state delta between initial.db and after.db."""
    initial = load_db(run / 'initial.db')
    after = load_db(run / 'after.db')
    removed, added = diff_state(initial, after)
    exp_added = spec.get('added', {})
    exp_removed = spec.get('removed', {})
    for table, rows in exp_added.items():
        got = added.get(table, {})
        if sum(got.values()) != len(rows) or \
                not all(sum(1 for k, n in got.items() if n and _match_row(
                    json.loads(k), r)) >= 1 for r in rows):
            raise VerifyError(f'unexpected {table} additions')
    for table, rows in exp_removed.items():
        got = removed.get(table, {})
        if sum(got.values()) != len(rows) or \
                not all(any(_match_row(json.loads(k), r) for k in got)
                        for r in rows):
            raise VerifyError(f'unexpected {table} removals')
    exp_tables = set(exp_added) | set(exp_removed)
    for table in set(added) | set(removed):
        if table not in exp_tables and (added.get(table) or
                                        removed.get(table)):
            raise VerifyError(f'unexpected changes in {table}')
        if table in exp_tables:
            exp_n = len(exp_added.get(table, [])) + \
                len(exp_removed.get(table, []))
            got_n = sum(added.get(table, {}).values()) + \
                sum(removed.get(table, {}).values())
            if got_n != exp_n:
                raise VerifyError(f'unexpected extra changes in {table}')
    # no row mutation: every table not in the delta must be content-identical
    for table in set(initial) & set(after) - exp_tables:
        if initial[table] != after[table]:
            raise VerifyError(f'row mutation detected in {table}')


def check_claims(answer, claims):
    """Gate 8: normalized regex claims with negation/contradiction rejection."""
    text = norm(answer)
    if re.search(r'\b(?:not true|incorrect answer|ignore these facts|'
                 r'the following is false|these claims are false)\b', text):
        raise VerifyError('answer rejects its own claims')
    for label, pattern in claims:
        hits = list(re.finditer(pattern, text, re.I))
        if not hits:
            raise VerifyError('missing or incorrect ' + label)
        for m in hits:
            claim = m.group()
            if re.search(r'\b(?:not|never|isn\'t|aren\'t|doesn\'t|don\'t|'
                         r'cannot)\b', claim) and \
                    not re.search(r'not|never', pattern):
                raise VerifyError('contradicted ' + label)
            if re.search(r'\b(?:not|never)\s*$', text[max(0, m.start() - 18):
                                                       m.start()]):
                raise VerifyError('negated ' + label)


def check_forbidden(answer, forbidden):
    """Gate 9: patterns that must not appear in the normalized answer."""
    text = norm(answer)
    for pattern in forbidden:
        if re.search(pattern, text, re.I):
            raise VerifyError('contradictory answer: ' + pattern)


def verify(run_dir, spec):
    run = Path(run_dir).resolve()
    traj, urls, shots = check_package(run, spec)
    check_seed(run)
    check_state(run, spec)
    answer = traj.get('final_answer', '')
    check_claims(answer, spec.get('claims', []))
    check_forbidden(answer, spec.get('forbidden', []))
    return {'task_id': spec['task_id'], 'pass': True,
            'reason': 'package, seed, state and claim gates passed',
            'evidence': [f'{shots} decoded screenshots',
                         f'{len(spec.get("claims", []))} checked claims',
                         'frozen seed verified',
                         'state delta exactly as specified']}


def main(spec):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--run_dir', required=True)
    args = parser.parse_args()
    try:
        result = verify(args.run_dir, spec)
    except Exception as exc:  # noqa: BLE001 - deterministic failure report
        result = {'task_id': spec['task_id'], 'pass': False,
                  'reason': str(exc), 'evidence': []}
    print(json.dumps(result))
    return 0 if result['pass'] else 1
