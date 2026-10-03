#!/usr/bin/env python3
"""verify_lib.py — deterministic verifier utilities for iclr task
verification.

Same contract as the hardened reviewer suites (``sites/tumblr/verify/
verify_lib.py``, ``sites/uscis/verify/verify_lib.py``): DETERMINISTIC FIRST.
No LLM call is load-bearing; every check is regex / token / SQLite
after-state.

  1. Package identity (fail-closed): task_id matches, ``terminated`` with
     ``agent_done``, non-empty final answer, every recorded URL on the same
     loopback origin AND port as ``start_url``, every referenced screenshot a
     decodable PNG.
  2. Seed identity gate (fail-closed): the initial DB snapshot must BE the
     frozen in-image seed (schema + rows digest + counts + file md5). A run
     graded against a pre-mutated database fails here.
  3. Navigation gates (anti knowledge-shortcut): the agent MUST have opened
     the on-site surfaces the task names (papers browser + filters, paper
     detail pages, schedule day tabs, the session paper lists, workshops /
     invited-talk hubs and event pages, sponsors, organizers, awards, blog
     posts, dates, venue, FAQ, the registration form, HelpDesk, account
     pages, the site search). A correct answer with no matching navigation
     is a memory-recall shortcut = FAIL.
  4. Answer check: phrase / token / count matching against frozen ground
     truth that is HARDCODED in ``contract.json`` (never in tasks.jsonl);
     the facts were transcribed from the reviewer's real Playwright
     walkthroughs of the review container (runs_round1/, 2026-09-30) and
     cross-checked against the frozen seed DB.
  5. DB after-state: read-only tasks require every table row-identical to
     the seed; stateful tasks require the exact allowed row delta and
     nothing else (a bookmark add, a schedule save, a schedule removal, a
     registration row whose dynamic code must appear in the answer, a new
     benchmark user, a HelpDesk message).

Seed reproducibility: the iclr seed is rebuilt deterministically inside
the pinned image (PYTHONHASHSEED=0, alphabetical index creation). The
reviewer's independent image build (webharbor:iclr-review, from
contribution 20059edc) reproduces seed sha256 a6c96a5e8217feee340c85bd
001f0c7bb55c39fbf122a3c1a3a3c0f320f19709 — byte-identical to the
contributor's dev container — and repeated control-plane resets restore
the instance byte-identically (md5 4fb437f600b076e9216a45e5bdd9b32d).
The contract freezes the logical digest (rows sha256 below), computed with
the exact function in contract_engine.database().

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
# Computed from the reviewer's independent container build
# (webharbor:iclr-review, Containerfile.review, 2026-09-30).
SEED_COUNTS = {
    "awards": 5, "bookmarks": 7, "contact_messages": 0, "date_items": 35,
    "events": 112, "news_posts": 8, "organizers": 29, "papers": 5691,
    "registrations": 1, "schedule_saves": 4, "session_events": 47,
    "sponsors": 60, "users": 4,
}
SEED_ROWS_SHA256 = ("35eb4f433045ed1a9f34b6c688187673b8ffe90aa6c"
                   "39080592fa20be3584613")
SEED_FILE_MD5 = "4fb437f600b076e9216a45e5bdd9b32d"
SEED_FILE_SHA256 = ("a6c96a5e8217feee340c85bd001f0c7bb55c39fbf1"
                    "22a3c1a3a3c0f320f19709")


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


# --------------------------------------------------------------- answer snapshots --

def answer_reg_code(after_db_path, table='registrations'):
    """Dynamic-value binding helper: the registration code the agent must
    report is the code saved in the run's own DB row."""
    con = sqlite3.connect(f'file:{after_db_path}?mode=ro', uri=True)
    try:
        rows = con.execute(
            f'SELECT reg_code FROM "{table}" ORDER BY id').fetchall()
        return [r[0] for r in rows]
    finally:
        con.close()
