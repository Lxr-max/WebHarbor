"""Offline review contract: browser evidence, scoped claims, and exact state deltas.

Language recognition is finite and deterministic; no LLM or live-state fallback.
Adapted from the shared WebHarbor contract-engine standard (verizon / usps /
virginia_dmv precedents) for the microsoft_azure tables (users, estimates,
favorites).
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
    answer = traj.get('final_answer', '')
    check_claims(answer, spec['claims'])
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


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith('-')
             else main(None))
