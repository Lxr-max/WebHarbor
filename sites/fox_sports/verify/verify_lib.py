#!/usr/bin/env python3
"""verify_lib.py — deterministic verifier utilities for fox_sports task
verification.

Same contract as the hardened reviewer suites (``sites/tumblr/verify/
verify_lib.py``, ``sites/iclr/verify/verify_lib.py``): DETERMINISTIC FIRST.
No LLM call is load-bearing; every check is regex / token / SQLite
after-state.

  1. Package identity (fail-closed): task_id matches, ``terminated`` with
     ``agent_done``, non-empty final answer, every recorded URL on the same
     loopback origin AND port as ``start_url``, every referenced screenshot a
     decodable PNG.
  2. Seed identity gate (fail-closed): the initial DB snapshot must BE the
     frozen in-image seed (schema + rows digest + counts + file sha256). A
     run graded against a pre-mutated database fails here.
  3. Navigation gates (anti knowledge-shortcut): the agent MUST have opened
     the on-site surfaces the task names (standings, team/roster/player
     pages, boxscores, schedules, stat leaders, search, shows /
     personalities, betting hubs, the FOX Super 6 contest pages, the
     account pages). A correct answer with no matching navigation is a
     memory-recall shortcut = FAIL.
  4. Answer check: phrase / token / count matching against frozen ground
     truth that is HARDCODED in ``contract.json`` (never in tasks.jsonl);
     the facts were transcribed from the reviewer's two independent
     Playwright walkthrough rounds of the review container
     (r2runs_round0/ + r2runs_round1/, identical step counts and facts)
     and cross-checked against the frozen r2 seed DB (330/330 comparisons,
     db_crosscheck_r2.py).
  5. DB after-state: every fox_sports task is stateful; each requires the
     exact allowed row delta and nothing else (a favorite add, a new
     benchmark account with its favorites, an updated Super 6 entry whose
     score must equal the number of picks matching the frozen correct
     picks).

Seed reproducibility (r2): the fox_sports seed is rebuilt deterministically
inside the pinned image (PYTHONHASHSEED=0, schema-order-pinned canonical
rebuild). The reviewer's independent r2 image build (webharbor:fox-review-r2,
from the fix commit 7249daad) rebuilds seed sha256 4d157dd2b72bd729c15d57c7
af4f9caf0324db688221f2152edca3155ae95baa — byte-identical across three
in-image rebuilds and to the contributor's declared in-image hash (their
host-toolchain build, sha256 a1551ec2… — the tarball member — differs only
by the SQLite version, 3.45.1 vs 3.40.1, and is content-identical: schema
objects and all 20 tables row-identical). Repeated control-plane resets
restore the instance byte-identically (md5 3c9809d0a3db203d45aa0f768c24
d7ca).

Input signature (per task):
  --run_dir DIR        agent trajectory dir: trajectory.json + screenshots/step_NNN.png
  --initial_db PATH    initial-state SQLite DB (default: <run_dir>/initial.db)
  --after_db PATH      after-state  SQLite DB (default: <run_dir>/after.db)
Output: JSON {task_id, pass, reason, evidence[]} to stdout; exit 0 on PASS, 1 on FAIL.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

# ---------------------------------------------------------------- frozen seed contract
# Computed from the reviewer's independent r2 container build
# (webharbor:fox-review-r2, Containerfile.review, 2026-09-30, from the
# fix commit 7249daad + the re-staged tarball fd7bb6a7…).
SEED_COUNTS = {
    "episodes": 155, "favorites": 23, "games": 315, "home_tiles": 32,
    "leagues": 5, "nascar_drivers": 53, "nascar_races": 2,
    "personalities": 109, "personality_videos": 838, "player_news": 1446,
    "player_stats": 60, "players": 3425, "shows": 17, "stories": 120,
    "super6_contests": 1, "super6_entries": 4, "super6_questions": 6,
    "teams": 214, "ufc_events": 4, "users": 4,
}
SEED_ROWS_SHA256 = ("25499c92536a857801b548ec3ac1eddb898cf212a5dd126f"
                    "280e3a593038f179")
SEED_FILE_MD5 = "3c9809d0a3db203d45aa0f768c24d7ca"
SEED_FILE_SHA256 = ("4d157dd2b72bd729c15d57c7af4f9caf0324db688221f215"
                    "2edca3155ae95baa")


# --------------------------------------------------------------------- db helpers --

def database(path):
    """Read every table as {primary-key-json: row-dict} — the exact shape
    contract_engine.check_state digests."""
    path = Path(path)
    if not path.is_file():
        raise ValueError(f'Missing saved database: {path.name}')
    con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    try:
        if con.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Corrupt database')
        data = {}
        for (table,) in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name"
                " NOT LIKE 'sqlite_%' ORDER BY name"):
            keys = [r[1] for r in sorted(con.execute(
                f'PRAGMA table_info("{table}")'), key=lambda r: r[5]) if r[5]]
            data[table] = {json.dumps([r[k] for k in keys]):
                           dict(r) for r in con.execute(
                               f'SELECT * FROM "{table}"')}
        return data
    finally:
        con.close()


def digest(data):
    return hashlib.sha256(json.dumps(
        data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def seed_identity(initial, initial_path):
    """Fail-closed: the initial snapshot must BE the frozen seed."""
    counts = {t: len(rows) for t, rows in initial.items()}
    if counts != SEED_COUNTS:
        raise ValueError(f'Initial DB table counts differ from the frozen '
                         f'seed: {counts}')
    if digest(initial) != SEED_ROWS_SHA256:
        raise ValueError('Initial DB rows differ from the frozen seed')
    f = Path(initial_path).read_bytes()
    if hashlib.md5(f).hexdigest() != SEED_FILE_MD5:
        raise ValueError('Initial DB file md5 differs from the frozen seed')
    if hashlib.sha256(f).hexdigest() != SEED_FILE_SHA256:
        raise ValueError('Initial DB file sha256 differs from the frozen seed')
    return True


# ------------------------------------------------------------------ text helpers --

def norm(text):
    """Case-fold, strip markdown/punctuation noise, unify dashes and
    number words, collapse whitespace."""
    text = str(text).replace('|', ' ').replace('**', '')
    text = text.casefold().replace('\u2212', '-').replace('\u00ae', '') \
        .replace('\u2122', '').replace('\u2019', "'").replace(
            '\u2013', '-').replace('\u2014', '-')
    text = re.sub(r'(?<=\d),(?=\d)', '', text)
    text = re.sub(r'\b(zero|one|two|three|four|five|six|seven|eight|nine'
                  r'|ten|eleven|twelve)\b',
                  lambda m: str(['zero', 'one', 'two', 'three', 'four',
                                 'five', 'six', 'seven', 'eight', 'nine',
                                 'ten', 'eleven', 'twelve'].index(m.group(0))),
                  text)
    text = re.sub(r'\$?\s*(\d+(?:\.\d+)?)\s*usd\b', r'$\1', text)
    text = re.sub(r'\busd\b', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def claim_matches(answer, pattern):
    """A claim regex must appear (case-insensitive) in the normalized
    answer."""
    return re.search(pattern, norm(answer), re.I) is not None


# --------------------------------------------------------------- super 6 helpers --

def super6_score(after, user_id, contest_id=1):
    """Return (picks, score) for a user's entry in the frozen contest."""
    rows = [r for r in after['super6_entries'].values()
            if r.get('user_id') == user_id
            and r.get('contest_id') == contest_id]
    if len(rows) != 1:
        raise ValueError(f'Expected exactly one Super 6 entry for user '
                         f'{user_id} in contest {contest_id}')
    return rows[0]['picks'], rows[0]['score']


def super6_correct(after, contest_id=1):
    """The frozen correct picks for each question of the contest."""
    rows = sorted((r for r in after['super6_questions'].values()
                   if r.get('contest_id') == contest_id),
                  key=lambda r: r['order'])
    return [r['correct_pick'] for r in rows]
