from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SITE_DIR))

# The verifier contract must stay in sync with the tasks and the seeded
# state it was reviewed against.


def load_tasks():
    rows = [json.loads(l) for l in
            (SITE_DIR / 'tasks.jsonl').read_text().splitlines() if l.strip()]
    return rows


def load_contract():
    return json.loads((SITE_DIR / 'verify' / 'contract.json').read_text())


def test_tasks_shape():
    tasks = load_tasks()
    assert 15 <= len(tasks) <= 25
    keys = {'web_name', 'id', 'ques', 'web', 'upstream_url',
            'verifier_path', 'judge_rubric'}
    for task in tasks:
        assert set(task.keys()) == keys, task['id']
        assert task['web'] == 'http://localhost:40223/'
        assert task['upstream_url'] == 'https://finance.yahoo.com/'
        assert len(task['ques'].split()) <= 100, task['id']
        # reviewer track: rubrics re-frozen as reviewer-authored judging
        # rules (see scripts_dev/append_rubrics.py); English pure rules,
        # no answer values.
        assert task['judge_rubric'].startswith(
            'Judge whether the agent completed this single user goal:')
        n = int(task['id'].split('--')[1])
        assert task['verifier_path'] == f'sites/yahoo_finance/verify/verify_{n}.py'
        assert (SITE_DIR / 'verify' / f'verify_{n}.py').is_file()


def test_verifier_files_exist():
    tasks = load_tasks()
    for task in tasks:
        assert (SITE_DIR.parent.parent / task['verifier_path']).is_file()
    assert (SITE_DIR / 'verify' / 'contract_engine.py').is_file()


def test_contract_matches_tasks_and_seed():
    contract = load_contract()
    tasks = load_tasks()
    for task in tasks:
        spec = contract[task['id']]
        assert spec['task'] == task['ques'], task['id']
        assert spec['initial_digest'], task['id']
        assert spec['claims'], task['id']
        assert spec['paths'], task['id']
    # the digest must match the tracked seed database
    import hashlib
    import sqlite3

    def digest(path):
        with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as con:
            con.row_factory = sqlite3.Row
            data = {}
            for (table,) in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%' ORDER BY name"):
                keys = [r[1] for r in sorted(
                    con.execute(f'PRAGMA table_info("{table}")'),
                    key=lambda r: r[5]) if r[5]]
                data[table] = {
                    json.dumps([r[k] for k in keys]): dict(r)
                    for r in con.execute(f'SELECT * FROM "{table}"')}
            return hashlib.sha256(json.dumps(
                data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    seed = SITE_DIR / 'instance_seed' / 'yahoo_finance.db'
    if seed.is_file():          # present in dev worktrees / built images
        tid = load_tasks()[0]['id']
        assert contract[tid]['initial_digest'] == digest(seed)


def test_no_task_leaks_its_own_answers():
    """The task wording must not contain the literal values it asks the
    agent to look up (answer-leak guard for the strongest anchors)."""
    leaks = {
        'YahooFinance--0': ['243.42', '345.34', '333.02', '328.22', '27.62',
                            'Cupertino', 'apple.com'],
        'YahooFinance--1': ['UTHR', '541.89', 'SMCI', 'Computer Hardware'],
        'YahooFinance--2': ['Stitch Fix', '84.92', 'TAS', '6.53'],
        'YahooFinance--5': ['1065.11', '949.71', '24.10'],
        'YahooFinance--6': ['154.88', '28.87', '63.66'],
        'YahooFinance--7': ['100,868,354', '12.66', '14.46', '14.33'],
        'YahooFinance--8': ['150B', '228.38', 'Healy', '117.7'],
        'YahooFinance--9': ['2025-09-30', '416.16', '112.01', '2.64', '1.08',
                            'Hillary', 'TheStreet'],
        'YahooFinance--10': ['65,900', '2.12', '2.46', '10.79', '16.61'],
        'YahooFinance--11': ['97', 'October 29', '328.22', '321.98'],
        'YahooFinance--12': ['116.25', '82.01', '156.92'],
        'YahooFinance--13': ['347.45'],
        'YahooFinance--14': ['8.58'],
        'YahooFinance--15': ['83,452.08', '1.68T', '57,747.77', 'Peaster',
                            'BlackRock', 'Bankless', 'OUSD', 'BNY'],
        'YahooFinance--16': ['38.92', '33.53', '30.71', '21.48'],
        'YahooFinance--17': ['512.90', '501.02', '480.25', '432.30'],
        'YahooFinance--18': ['4,183.20', 'Banerjee', '18 articles'],
        'YahooFinance--19': ['6.59', '4.40', '53.23'],
    }
    tasks = {t['id']: t['ques'] for t in load_tasks()}
    for task_id, values in leaks.items():
        for value in values:
            assert value.lower() not in tasks[task_id].lower(), \
                f'{task_id} leaks {value!r}'


def test_task_answers_are_deterministic_against_seed():
    """Every hard value the contracts check must match the seeded state."""
    import sqlite3
    seed = SITE_DIR / 'instance_seed' / 'yahoo_finance.db'
    if not seed.is_file():
        pytest.skip('seed database not built')
    con = sqlite3.connect(f'file:{seed}?mode=ro', uri=True)
    con.row_factory = sqlite3.Row

    def quote(sym):
        return con.execute('SELECT * FROM quotes WHERE symbol=?',
                           (sym,)).fetchone()
    assert quote('AAPL')['price'] == 333.02
    assert quote('AAPL')['sector'] == 'Technology'
    assert abs(quote('AAPL')['wk52_low'] - 243.42) < 0.01
    assert abs(quote('AAPL')['wk52_high'] - 345.34) < 0.01
    assert abs(quote('NVDA')['pe_ttm'] - 28.872314) < 0.001
    assert abs(quote('MU')['price'] - 1065.11) < 0.01
    assert abs(quote('GC=F')['price'] - 4183.2) < 0.01
    assert abs(quote('BTC-USD')['price'] - 83452.08) < 0.01
    assert quote('GC=F')['short_name'] == 'Gold Dec 26'
    # r1-fix anchors: the reworded T0/T8/T9/T15 question points
    assert abs(quote('AAPL')['target_mean'] - 328.22205) < 1e-4
    assert abs(quote('AAPL')['profit_margin'] - 27.618998) < 1e-4
    assert abs(quote('AAPL')['day50_avg'] - 321.9814) < 1e-4
    assert quote('AAPL')['website'].endswith('apple.com')
    assert quote('AAPL')['city'] == 'Cupertino'
    row = con.execute("SELECT * FROM earnings_events WHERE ticker='SFIX' "
                      "AND day='2026-09-24'").fetchone()
    assert row and abs(row['eps_estimate'] + 0.06) < 1e-9
    assert abs(row['surprise_pct'] - 84.92) < 0.01
    n = con.execute("SELECT COUNT(*) FROM earnings_events WHERE day BETWEEN "
                    "'2026-09-20' AND '2026-09-26' AND time_type='AMC'"
                    ).fetchone()[0]
    assert n == 2
    # most recent 'Apple' news match: TheStreet, author Hillary Remy
    row = con.execute("SELECT provider, author FROM news_articles WHERE "
                      "title LIKE '%Apple%' OR summary LIKE '%Apple%' "
                      "ORDER BY pub_time DESC LIMIT 1").fetchone()
    assert row['provider'] == 'TheStreet' and row['author'] == 'Hillary Remy'
    # most recent 'stablecoin' news match: Bankless, author William Peaster,
    # with the three reserve custodians named in the body text
    row = con.execute("SELECT provider, author, body FROM news_articles "
                      "WHERE title LIKE '%stablecoin%' OR summary LIKE "
                      "'%stablecoin%' ORDER BY pub_time DESC LIMIT 1"
                      ).fetchone()
    assert row['provider'] == 'Bankless'
    assert row['author'] == 'William Peaster'
    assert 'BlackRock, BNY, and Lead Bank handle reserves' in row['body']
    # most recent 'buyback' news match: Motley Fool, author Will Healy
    row = con.execute("SELECT provider, author, body FROM news_articles "
                      "WHERE title LIKE '%buyback%' OR summary LIKE "
                      "'%buyback%' ORDER BY pub_time DESC LIMIT 1").fetchone()
    assert row['provider'] == 'Motley Fool' and 'Will Healy' in row['author']
    assert 'Trading volume reached 117.7M shares' in row['body']
    con.close()


import pytest  # noqa: E402  (used in skip above)
