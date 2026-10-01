"""Offline review contract: browser evidence, scoped claims, and exact state deltas.

Language recognition is finite and deterministic; no LLM or live-state fallback.
Includes precise favorite ownership and dynamic practice-contest scoring.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import urlsplit, unquote
from PIL import Image


def norm(text):
    text = str(text).replace('|', ' ').replace('**', '').casefold()
    text = text.replace('−', '-').replace('®', '').replace('™', '')
    text = text.replace('’', "'").replace('–', '-').replace('—', '-')
    text = re.sub(r'\b([0-9][0-9,.]*)\s*usd\b', r'$\1', text)
    text = re.sub(r'\busd\s*', '$', text)
    text = re.sub(r'(?<=\d),(?=\d)', '', text)
    text = re.sub(r'\b(zero|one|two|three|four|five|six|seven|eight|nine|ten)\b(?!-tone)',
                  lambda m: str(['zero', 'one', 'two', 'three', 'four', 'five',
                                'six', 'seven', 'eight', 'nine', 'ten'].index(m[0])), text)
    for old, new in [(r'\bhrs?\b', 'hours'), (r'\bper hour\b', 'hour'),
                     (r'\bfree of charge\b', 'free'), (r'\bcomplimentary\b', 'free')]:
        text = re.sub(old, new, text)
    return re.sub(r'\s+', ' ', text).strip()


def database(path):
    if not path.is_file():
        raise ValueError('Missing saved database: ' + path.name)
    with sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True) as con:
        con.row_factory = sqlite3.Row
        if con.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Corrupt database')
        data = {}
        for (table,) in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            keys = [r[1] for r in sorted(con.execute(f'PRAGMA table_info("{table}")'),
                                          key=lambda r: r[5]) if r[5]]
            data[table] = {json.dumps([r[k] for k in keys]): dict(r)
                           for r in con.execute(f'SELECT * FROM "{table}"')}
        return data


def digest(data):
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def canonical_json(value):
    if isinstance(value, dict):
        return {k: canonical_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return sorted([canonical_json(v) for v in value],
                      key=lambda v: json.dumps(v, sort_keys=True))
    return value


def matches(value, expected):
    if isinstance(expected, dict):
        if 'json_value' in expected:
            return canonical_json(json.loads(value)) == canonical_json(expected['json_value'])
        if 'regex' in expected:
            return re.fullmatch(expected['regex'], str(value), re.I) is not None
        if 'one_of' in expected:
            return value in expected['one_of']
    return value == expected


def check_state(initial, after, spec):
    if digest(initial) != spec['initial_digest']:
        raise ValueError('Initial state does not match reviewed seed')
    if initial.keys() != after.keys():
        raise ValueError('Database tables changed')
    for table, old in initial.items():
        new = after[table]
        if table == 'super6_entries' and spec.get('contest'):
            check_contest(initial, after, spec['contest'])
            continue
        rule = spec.get('state', {}).get(table, {})
        removed = set(rule.get('removed', []))
        if old.keys() - new.keys() != removed:
            raise ValueError('Wrong existing rows removed from ' + table)
        added = [r for k, r in new.items() if k not in old]
        expected = rule.get('added', [])
        if len(added) != len(expected):
            raise ValueError('Wrong number of new rows in ' + table)
        for want in expected:
            hits = [r for r in added
                    if r.keys() == want.keys()
                    and all(matches(r[k], v) for k, v in want.items())]
            if not hits:
                raise ValueError('Incorrect new ' + table + ' row')
            added.remove(hits[0])
        for key, before in old.items():
            if key in removed:
                continue
            changes = rule.get('updated', {}).get(key, {})
            for col, value in before.items():
                if not matches(new[key][col], changes.get(col, value)):
                    raise ValueError('Incorrect ' + table + '.' + col)


def check_claims(answer, claims):
    text = norm(answer)
    if re.search(r'\b(?:not true|incorrect answer|ignore these facts|'
                 r'the following is false|these claims are false)\b', text):
        raise ValueError('Answer rejects its own claims')
    for label, pattern in claims:
        hits = list(re.finditer(pattern, text, re.I))
        if not hits:
            raise ValueError('Missing or incorrect ' + label)
        for m in hits:
            claim = m.group()
            if re.search(r'\b(?:reference (?:number|id)|unrelated (?:number|value))\b', claim + ' ' + text[max(0, m.start()-22):m.start()]):
                raise ValueError('Reference value substituted for ' + label)
            if re.search(r'\b(?:not|never|incorrect|false)\s*$',
                         text[max(0, m.start() - 18):m.start()]):
                raise ValueError('Negated ' + label)
            if re.search(r"\b(?:not|never|isn't|aren't|doesn't|don't|cannot)\b",
                         claim) and not re.search(r'not|never|ineligible|unavailable|prohibit',
                                                  pattern):
                raise ValueError('Contradicted ' + label)


def verify(run_dir, task_id):
    run = Path(run_dir).resolve()
    traj = json.loads((run / 'trajectory.json').read_text())
    spec = json.loads(Path(__file__).with_name('contract.json').read_text())[task_id]
    if traj.get('task_id') != task_id or \
            traj.get('task', traj.get('ques')) != spec['task']:
        raise ValueError('Wrong task identity or wording')
    if not traj.get('terminated') or traj.get('termination_reason') != 'agent_done':
        raise ValueError('Unfinished attempt')
    start = urlsplit(traj.get('start_url', ''))
    if start.scheme not in ['http', 'https'] or \
            start.hostname not in ['localhost', '127.0.0.1', '::1']:
        raise ValueError('Invalid local start URL')
    origin = (start.scheme, start.hostname, start.port)
    urls = []
    seen = set()
    steps = traj.get('steps', [])
    if not steps:
        raise ValueError('Missing browser evidence')
    for step in steps:
        for key in ['url', 'url_before', 'url_after']:
            if key in step:
                u = urlsplit(step[key])
                if (u.scheme, u.hostname, u.port) != origin:
                    raise ValueError('Browser evidence changes origin')
        u = urlsplit(step.get('url_after', step.get('url', '')))
        urls.append(unquote(u.path + ('?' + u.query if u.query else '')))
        name = step.get('screenshot_after', step.get('screenshot'))
        if not name or Path(name).name != name:
            raise ValueError('Invalid screenshot reference')
        path = run / 'screenshots' / name
        if path not in seen:
            with Image.open(path) as im:
                im.load()
                if im.format != 'PNG' or im.width < 320 or im.height < 200:
                    raise ValueError('Screenshot is not a full browser PNG')
                if len(im.convert('RGB').resize((32, 32)).getcolors(1024) or []) < 8:
                    raise ValueError('Blank browser screenshot')
            seen.add(path)
    for pattern in spec['paths']:
        if not any(re.search(pattern, u, re.I) for u in urls):
            raise ValueError('Required page evidence missing: ' + pattern)
    initial = database(run / 'initial.db')
    after = database(run / 'after.db')
    check_state(initial, after, spec)
    check_signup_password(traj, initial, after, spec)
    answer = traj.get('final_answer', '')
    check_claims(answer, spec['claims'])
    if spec.get('contest'):
        check_contest_answer(answer, initial, after, spec['contest'])
    for pattern in spec.get('forbidden', []):
        if re.search(pattern, norm(answer), re.I):
            raise ValueError('Contradictory answer: ' + pattern)
    for table, col in spec.get('answer_state', []):
        rows = [r for k, r in after[table].items() if k not in initial[table]]
        if len(rows) != 1:
            raise ValueError('Expected one saved ' + table + ' row')
        value = str(rows[0][col])
        if norm(value) not in norm(answer):
            raise ValueError('Answer does not match saved ' + col)
    return {'task_id': task_id, 'pass': True,
            'reason': 'Browser evidence, scoped factual claims and exact '
                      'saved-state contract passed',
            'evidence': [f'{len(seen)} decoded screenshots',
                         f'{len(spec["claims"])} checked claims',
                         'Saved initial and final databases compared']}


def main(task_id):
    parser = argparse.ArgumentParser()
    parser.add_argument('--run_dir', required=True)
    args = parser.parse_args()
    try:
        result = verify(args.run_dir, task_id)
    except Exception as exc:
        result = {'task_id': task_id, 'pass': False, 'reason': str(exc),
                  'evidence': []}
    print(json.dumps(result))
    return 0 if result['pass'] else 1





def check_signup_password(traj, initial, after, spec):
    column = spec.get('signup_password_column')
    if not column:
        return
    import bcrypt
    rows = [r for k,r in after['users'].items() if k not in initial['users']]
    passwords = [(s.get('params') or {}).get('text', '') for s in traj['steps'] if 'password' in str(s.get('params', {}).get('target', ''))]
    if len(rows) != 1 or not any(len(p) >= 8 and bcrypt.checkpw(p.encode(), rows[0][column].encode()) for p in passwords):
        raise ValueError('New account password does not match the submitted password')


def check_contest(initial, after, rule):
    uid, cid = rule['user_id'], rule['contest_id']
    old, new = initial['super6_entries'], after['super6_entries']
    if old.keys() != new.keys():
        raise ValueError('Contest entry set changed')
    questions = sorted((q for q in initial['super6_questions'].values() if q['contest_id']==cid), key=lambda q:q['order'])
    target_count = 0
    for key, before in old.items():
        row = new[key]
        if before['user_id'] != uid or before['contest_id'] != cid:
            if row != before: raise ValueError('Another contest entry changed')
            continue
        target_count += 1
        if {k:v for k,v in row.items() if k not in ('picks','score')} != {k:v for k,v in before.items() if k not in ('picks','score')}:
            raise ValueError('Contest ownership or metadata changed')
        picks=row['picks'].split('|')
        if len(picks)!=len(questions) or any(p not in (q['away_team'],q['home_team']) for p,q in zip(picks,questions)):
            raise ValueError('Invalid matchup picks')
        if rule['strategy']=='alternating' and picks != [q['home_team'] if q['order']%2 else q['away_team'] for q in questions]:
            raise ValueError('Wrong alternating picks')
        if row['score'] != sum(p==q['correct_pick'] for p,q in zip(picks,questions)):
            raise ValueError('Score does not match submitted picks')
    if target_count != 1:
        raise ValueError('Missing owned contest entry')


def check_contest_answer(answer, initial, after, rule):
    row=next(r for r in after['super6_entries'].values() if r['user_id']==rule['user_id'] and r['contest_id']==rule['contest_id'])
    text=norm(answer);score=row['score']
    if not re.search(r'(?:my|your|entry|i|dana)[^.;]{0,35}(?:score[ds]?|scored)[^.;]{0,15}'+str(score)+r'(?![0-9])',text):
        raise ValueError('Reported score does not match owned entry')
    if rule['strategy']=='alternating':
        if not re.search(r'(?:missed|misses)[^.;]{0,15}'+str(6-score)+r'(?![0-9])',text):
            raise ValueError('Reported misses do not match entry')
        questions=sorted(initial['super6_questions'].values(),key=lambda q:q['order'])
        first=next(q for p,q in zip(row['picks'].split('|'),questions) if p!=q['correct_pick'])
        game=next(g for g in initial['games'].values() if g['slug']==first['game_slug'])
        winner=next(t['full_name'] for t in initial['teams'].values() if t['slug']==first['correct_pick'])
        if norm(winner) not in text or norm(game['venue']) not in text:
            raise ValueError('Missing first missed matchup winner or venue')
        spread=str(game['spread'])
        if spread not in text:
            raise ValueError('Missing first missed matchup spread')
