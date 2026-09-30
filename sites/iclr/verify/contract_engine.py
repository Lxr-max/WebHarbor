#!/usr/bin/env python3
"""Offline review contract for the iclr mirror: browser evidence, scoped
claims, and exact state deltas.

Every check is finite and deterministic; no LLM or live-state fallback.
Ground truth lives only here and in contract.json (never in tasks.jsonl).

Per task, ``verify()`` enforces:
  * trajectory identity: task_id + exact task wording, terminated
    agent_done, non-empty answer, all step URLs on the start origin/port;
  * screenshot evidence: every step references a decodable, non-blank PNG;
  * navigation gates: the task's required pages appear among the visited
    URLs (regex list per task);
  * seed identity: the initial snapshot is the frozen seed (see
    verify_lib.SEED_* constants);
  * exact DB delta: read-only tasks must be row-identical; stateful tasks
    must show precisely the allowed adds/removes and nothing else;
  * scoped answer claims: regex list over the normalized final answer,
    transcribed from the reviewer's honest Playwright walkthrough
    (runs_round1/, review container wh-iclr-review) and cross-checked
    against the frozen seed;
  * answer-state bindings: dynamic values the agent itself creates (the
    registration code) must appear in the answer and match the saved row.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from PIL import Image

from verify_lib import (SEED_COUNTS, SEED_ROWS_SHA256, claim_matches, database,
                        digest, norm, seed_identity)

HERE = Path(__file__).resolve().parent


def check_screenshots(run, steps):
    seen = set()
    for step in steps:
        name = step.get('screenshot_after', step.get('screenshot'))
        if not name or Path(name).name != name:
            raise ValueError('Invalid screenshot reference')
        path = run / 'screenshots' / name
        if path not in seen:
            if not path.is_file():
                raise ValueError(f'Missing screenshot: {name}')
            with Image.open(path) as im:
                im.load()
                if im.format != 'PNG' or im.width < 320 or im.height < 200:
                    raise ValueError('Screenshot is not a full browser PNG')
                if len(im.convert('RGB').resize((32, 32)).getcolors(1024)
                       or []) < 8:
                    raise ValueError('Blank browser screenshot')
            seen.add(path)
    return len(seen)


def check_identity(traj, task_id, spec):
    if traj.get('task_id') != task_id:
        raise ValueError('Wrong task identity')
    if traj.get('task', traj.get('ques')) != spec['task']:
        raise ValueError('Wrong task wording')
    if not traj.get('terminated') or traj.get('termination_reason') != 'agent_done':
        raise ValueError('Unfinished attempt')
    answer = traj.get('final_answer') or ''
    if not str(answer).strip():
        raise ValueError('Empty final answer')
    start = urlsplit(traj.get('start_url', ''))
    if start.scheme not in ('http', 'https') or start.hostname not in (
            'localhost', '127.0.0.1', '::1'):
        raise ValueError('Invalid local start URL')
    origin = (start.scheme, start.hostname, start.port)
    urls = []
    steps = traj.get('steps', [])
    if not steps:
        raise ValueError('Missing browser evidence')
    for step in steps:
        for key in ('url', 'url_before', 'url_after'):
            if key in step and step[key]:
                u = urlsplit(step[key])
                if (u.scheme, u.hostname, u.port) != origin:
                    raise ValueError('Browser evidence changes origin')
        u = urlsplit(step.get('url_after', step.get('url', '')))
        urls.append(unquote(u.path + (('?' + u.query) if u.query else '')))
    return urls, str(answer)


def check_navigation(urls, spec):
    for pattern in spec.get('paths', []):
        if not any(re.search(pattern, u, re.I) for u in urls):
            raise ValueError('Required page evidence missing: ' + pattern)


def matches(value, expected):
    if isinstance(expected, dict):
        if 'regex' in expected:
            return re.fullmatch(expected['regex'], str(value), re.I) \
                is not None
        if 'one_of' in expected:
            return value in expected['one_of']
        if 'contains' in expected:
            return str(expected['contains']).casefold() in str(value).casefold()
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
            raise ValueError(f'Wrong existing rows removed from {table}')
        added = [r for k, r in new.items() if k not in old]
        expected = rule.get('added', [])
        if len(added) != len(expected):
            raise ValueError(f'Wrong number of new rows in {table}')
        for want in expected:
            hits = [r for r in added
                    if r.keys() == want.keys()
                    and all(matches(r[k], v) for k, v in want.items())]
            if not hits:
                raise ValueError(f'Incorrect new {table} row')
            added.remove(hits[0])
        for key, before in old.items():
            if key in removed:
                continue
            changes = rule.get('updated', {}).get(key, {})
            for col, value in before.items():
                if not matches(new[key][col], changes.get(col, value)):
                    raise ValueError(f'Incorrect {table}.{col}')


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


def check_answer_state(answer, after, spec):
    """Dynamic-value bindings: values the agent created in this run (the
    registration code) must appear in its own answer."""
    for binding in spec.get('answer_state', []):
        table = binding['table']
        col = binding['column']
        rows = after[table]
        if binding.get('all_rows'):
            values = [str(r[col]) for r in rows.values()]
        else:
            # the newest row of the table (the one this run created)
            newest = max(rows.items(), key=lambda kv: kv[1].get('id', 0))
            values = [str(newest[1][col])]
        if not any(norm(v) in norm(answer) for v in values):
            raise ValueError(f'Answer does not report the saved {col}')


def verify(run_dir, task_id):
    run = Path(run_dir).resolve()
    traj = json.loads((run / 'trajectory.json').read_text())
    spec = json.loads((HERE / 'contract.json').read_text())[task_id]

    urls, answer = check_identity(traj, task_id, spec)
    n_shots = check_screenshots(run, traj['steps'])
    check_navigation(urls, spec)

    initial = database(run / 'initial.db')
    after = database(run / 'after.db')
    seed_identity(initial, run / 'initial.db')
    check_state(initial, after, spec)
    check_claims(answer, spec['claims'])
    check_answer_state(answer, after, spec)
    for pattern in spec.get('forbidden', []):
        if re.search(pattern, norm(answer), re.I):
            raise ValueError('Contradictory answer: ' + pattern)
    return {'task_id': task_id, 'pass': True,
            'reason': 'Browser evidence, scoped factual claims and exact '
                      'saved-state contract passed',
            'evidence': [f'{n_shots} decoded screenshots',
                         f'{len(spec["claims"])} checked claims',
                         'Saved initial and final databases compared']}


def main(task_id):
    parser = argparse.ArgumentParser()
    parser.add_argument('--run_dir', required=True)
    parser.add_argument('--initial_db', default=None)
    parser.add_argument('--after_db', default=None)
    args = parser.parse_args()
    try:
        result = verify(args.run_dir, task_id)
    except Exception as exc:
        result = {'task_id': task_id, 'pass': False, 'reason': str(exc),
                  'evidence': []}
    print(json.dumps(result))
    return 0 if result['pass'] else 1


if __name__ == '__main__':
    sys.exit(0)
