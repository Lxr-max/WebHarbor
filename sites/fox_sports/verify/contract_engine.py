#!/usr/bin/env python3
"""Offline review contract for the fox_sports mirror: browser evidence,
scoped claims, and exact state deltas.

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
  * exact DB delta: each task allows precisely its measured favorite /
    account / Super 6-entry changes and nothing else;
  * Super 6 consistency: any graded entry's stored score must equal the
    number of its picks matching the frozen correct picks (a self-reported
    score the DB contradicts is a FAIL);
  * scoped answer claims: regex list over the normalized final answer,
    transcribed from the reviewer's two independent honest Playwright
    walkthrough rounds (r2runs_round0/, r2runs_round1/, review container
    wh-fox-review-r2) and cross-checked against the frozen r2 seed
    (db_crosscheck_r2.py, 330/330);
  * answer-state bindings: dynamic values that depend on the agent's own
    choices (the Super 6 picks it submitted) must be reported and must
    match the saved row.
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
                        digest, norm, seed_identity, super6_correct,
                        super6_score)

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
        # pre-action URL + navigation targets: intermediate redirects
        # (e.g. /logout -> /, /nascar -> /nascar/cup-series/standings)
        # must leave navigation evidence for the pages the task names;
        # the benchmark agent logs its goto target in params.url
        if step.get('url') and step['url'] != step.get('url_after'):
            u = urlsplit(step['url'])
            urls.append(unquote(u.path + (('?' + u.query) if u.query else '')))
        target = (step.get('params') or {}).get('url')
        if target:
            u = urlsplit(str(target))
            if u.scheme:
                if (u.scheme, u.hostname, u.port) != origin:
                    raise ValueError('Navigation target changes origin')
                urls.append(unquote(u.path + (('?' + u.query) if u.query else '')))
            else:
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
            if re.search(r'\b(?:not|never|incorrect|false)\s*$',
                         text[max(0, m.start() - 18):m.start()]):
                raise ValueError('Negated ' + label)


def check_answer_state(answer, after, spec):
    """Dynamic-value bindings: values that depend on the agent's own
    submitted picks (the Super 6 graded score) must appear in its answer
    and match the saved row."""
    for binding in spec.get('answer_state', []):
        table = binding['table']
        col = binding['column']
        if table == 'super6_entries':
            _, value = super6_score(after, binding['user_id'],
                                    binding.get('contest_id', 1))
        else:
            rows = list(after[table].values())
            if binding.get('all_rows'):
                values = [str(r[col]) for r in rows]
            else:
                newest = max(rows, key=lambda r: r.get('id', 0))
                values = [str(newest[col])]
            if not any(norm(v) in norm(answer) for v in values):
                raise ValueError(f'Answer does not report the saved {col}')
            continue
        if norm(str(value)) not in norm(answer):
            raise ValueError(f'Answer does not report the saved {col}')


def check_super6_consistency(after, spec):
    """Every graded entry's stored score must equal the number of its
    picks matching the frozen correct picks (the app computes this at
    submit time; a run that fakes its DB row fails here)."""
    if not spec.get('super6_consistency'):
        return
    correct = super6_correct(after, spec['super6_consistency'].get(
        'contest_id', 1))
    for row in after['super6_entries'].values():
        picks = row['picks'].split('|')
        if len(picks) != len(correct):
            raise ValueError('Super 6 entry has wrong pick count')
        expected = sum(1 for p, c in zip(picks, correct) if p == c)
        if row['score'] != expected:
            raise ValueError('Super 6 entry score does not match its picks')


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
    check_super6_consistency(after, spec)
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
