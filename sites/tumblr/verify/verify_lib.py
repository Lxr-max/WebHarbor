#!/usr/bin/env python3
"""verify_lib.py — deterministic verifier utilities for tumblr task verification.

Same contract as the hardened reviewer suites (``sites/ryanair/verify/
verify_lib.py``, ``sites/megabus/verify/verify_lib.py``): DETERMINISTIC FIRST.
No LLM call is load-bearing; every check is regex / token / SQLite after-state.

  1. Package identity: task_id matches, ``terminated`` with ``agent_done``,
     non-empty final answer, every recorded URL on the same loopback origin AND
     port as ``start_url``, every referenced screenshot a decodable PNG.
  2. Navigation gates (anti knowledge-shortcut): the agent MUST have opened the
     on-site surfaces the task names — the home trending feed, tag hubs, search
     results (Top/Recent), blog pages, archives, permalinks, the login form,
     the dashboard/likes/following/activity/inbox pages, the composer, settings
     and registration. A correct answer with no matching navigation is a
     memory-recall shortcut = FAIL.
  3. Answer check: phrase / token / count matching against frozen ground
     truth that is HARDCODED in each ``verify_N.py`` (never in tasks.jsonl).
  4. DB after-state: initial (seed) vs after (instance) SQLite snapshots.
     Read-only tasks require every table row-identical; stateful tasks require
     the exact allowed row delta and nothing else (a like row, a reblog post +
     reblog row, a follow row, a message row, a new post row, a settings
     update, a registration).

Input signature (per task):
  --run_dir DIR        agent trajectory dir: trajectory.json + screenshots/step_NNN.png
  --initial_db PATH    initial-state SQLite DB (default: <run_dir>/initial.db, else
                       instance_seed from the container)
  --after_db PATH      after-state  SQLite DB (default: <run_dir>/after.db, else live
                       instance DB from the container)
  --container NAME     docker container to fetch DBs from (default: $WH_CONTAINER or
                       wh-tumblr-review-1)
Output: JSON {task_id, pass, reason, evidence[]} to stdout; exit 0 on PASS, 1 on FAIL.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

SITE = "tumblr"
DEFAULT_CONTAINER = os.environ.get("WH_CONTAINER", "wh-tumblr-review-1")

# ---------------------------------------------------------------- frozen seed contract
# The seed is rebuilt deterministically at image build time (PYTHONHASHSEED=0,
# TZ=UTC in the python:3.12-slim-bookworm image) exactly as the production
# Dockerfile does. These hashes freeze that contract.
TABLES = ("blogs", "conversations", "follows", "likes", "messages", "notes",
          "notifications", "posts", "reblogs", "search_queries", "tag_hubs",
          "tag_posts", "trending", "users")
SEED_COUNTS = {"blogs": 512, "conversations": 6, "follows": 26, "likes": 36,
               "messages": 15, "notes": 6985, "notifications": 10, "posts": 1491,
               "reblogs": 3, "search_queries": 8, "tag_hubs": 12,
               "tag_posts": 240, "trending": 40, "users": 4}
# sha256 over sqlite_master (type, name, tbl_name, sql).
SCHEMA_SHA256 = "51e9f35f69f6545a16db640826fb154b3a45144ca976771dbd3d99482c46a9fd"
# sha256 over every seed row (table-canonical, ORDER BY all columns) of the
# production (TZ=UTC) seed build — re-frozen at the r2 re-review for the
# ab8382a9 fix deltas (+1 teaboot blog, +3 teaboot posts, +1 seeded unread
# message, 6 hub editorial fields, 2 conversation updated_at).
SEED_ROWS_SHA256 = "3ed05f1b61d14bc79657d85d795adeaa2b511d6d3352bc1a22d324f14abf296a"
SEED_USERS = {  # email -> username; identity columns never change
    "alice.j@test.com": "alice-j",
    "bob.c@test.com": "bob-c",
    "carol.d@test.com": "carol-d",
    "david.k@test.com": "david-k",
}
DEMO_PASSWORD = "TestPass123!"
INPUT_ACTIONS = {"input", "type", "fill", "input_text", "type_text", "check"}


# ---------------------------------------------------------------- trajectory
def load_run(run_dir):
    d = Path(run_dir)
    traj = json.loads((d / "trajectory.json").read_text(encoding="utf-8"))
    if not isinstance(traj, dict):
        raise ValueError("trajectory.json must contain a JSON object")
    traj["_run_dir"] = d
    shots_dir = d / "screenshots"
    traj["_shots"] = ({p.name: p for p in sorted(shots_dir.glob("step_*.png"))}
                      if shots_dir.is_dir() else {})
    return traj


def trajectory_urls(traj):
    urls = []
    if traj.get("start_url"):
        urls.append(str(traj["start_url"]))
    for step in traj.get("steps") or []:
        if not isinstance(step, dict):
            continue
        for key in ("url", "url_before", "url_after"):
            if step.get(key):
                urls.append(str(step[key]))
    if traj.get("final_url"):
        urls.append(str(traj["final_url"]))
    return urls


def final_answer(traj):
    return str(traj.get("final_answer") or "").strip()


def is_site_url(url):
    parsed = urlparse(str(url or ""))
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    host = parsed.hostname.casefold()
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def site_urls(traj):
    return [u for u in trajectory_urls(traj) if is_site_url(u)]


def normalized_url_path(url):
    path = urlparse(str(url or "")).path or "/"
    return unquote(path.rstrip("/") or "/")


def navigated_to(traj, substr, times=1):
    return sum(1 for u in site_urls(traj) if substr in unquote(u)) >= times


def navigated_path(traj, expected_path):
    expected = normalized_url_path(expected_path)
    return any(normalized_url_path(u) == expected for u in site_urls(traj))


def navigated_path_prefix(traj, expected_prefix, times=1):
    prefix = normalized_url_path(expected_prefix)
    return (sum(1 for u in site_urls(traj)
                if normalized_url_path(u).startswith(prefix)) >= times)


def navigated_search(traj, query):
    """/search/<query> visit with the task's query (URL-decoded compare)."""
    want = normalized_url_path(f"/search/{query}")
    return any(normalized_url_path(u) == want for u in site_urls(traj))


def visited_permalink(traj, blog_name, post_id):
    """/blog/<name>/<post_id> or /post/<post_id> visit."""
    want_a = normalized_url_path(f"/blog/{blog_name}/{post_id}")
    want_b = normalized_url_path(f"/post/{post_id}")
    return any(normalized_url_path(u) in (want_a, want_b) for u in site_urls(traj))


def entered_identity(traj, expected):
    """The expected string appears in an input step (case-insensitive)."""
    wanted = normalize_text(expected)
    for step in traj.get("steps") or []:
        if not isinstance(step, dict) or step.get("action") not in INPUT_ACTIONS:
            continue
        params = step.get("params") or {}
        for v in (params.get("text"), params.get("value")):
            if v is not None and wanted in normalize_text(str(v)):
                return True
    return False


def input_texts(traj):
    out = []
    for step in traj.get("steps") or []:
        if isinstance(step, dict) and step.get("action") in INPUT_ACTIONS:
            params = step.get("params") or {}
            for v in (params.get("text"), params.get("value")):
                if v is not None:
                    out.append(str(v))
    return out


def normalize_text(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = (s.replace("\u2019", "'").replace("\u2018", "'")
         .replace("\u201c", '"').replace("\u201d", '"')
         .replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-"))
    return re.sub(r"\s+", " ", s).strip().lower()


# ---------------------------------------------------------------- answer matching
def contains_all(answer, tokens):
    a = normalize_text(answer)
    return all(normalize_text(t) in a for t in tokens)


def contains_any(answer, tokens):
    a = normalize_text(answer)
    return any(normalize_text(t) in a for t in tokens)


def contains_phrase(answer, phrase):
    return normalize_text(phrase) in normalize_text(answer)


def contains_number(answer, value):
    """The integer value appears standalone, with or without thousands
    separators ("582" or "582" / "3,405" / "3.405")."""
    wanted = int(value)
    a = normalize_text(str(answer))
    for m in re.finditer(r"(?<![\d])[\d.,]*\d+(?![\d])", a):
        token = m.group(0).replace(",", "").replace(".", "")
        token = token.lstrip("0") or "0"
        if token.isdigit() and int(token) == wanted:
            return True
    return False


def contains_count(answer, count):
    """The integer count appears as a standalone number (not a decimal)."""
    for m in re.finditer(r"(?<![\d.,£$])\d+(?![\d.,])", str(answer)):
        if int(m.group(0)) == int(count):
            return True
    return False


# ---------------------------------------------------------------- snapshots
def db_query(db_path, sql, params=()):
    con = sqlite3.connect(str(db_path))
    try:
        con.row_factory = sqlite3.Row
        return [dict(r) for r in con.execute(sql, params)]
    finally:
        con.close()


def resolve_db(path, container, which):
    if path:
        p = Path(path)
        return p if p.is_file() else None
    cache = Path(tempfile.gettempdir()) / f"{SITE}_verify_{which}.db"
    if cache.is_file():
        return cache
    try:
        subprocess.run(["docker", "cp",
                        f"{container}:/opt/WebSyn/{SITE}/{which}/{SITE}.db",
                        str(cache)],
                       check=True, capture_output=True, text=True, timeout=120)
    except Exception:
        return None
    return cache if cache.is_file() else None


def _canon_value(v):
    """Python-version-stable encoding of a SQLite value (repr() of astral
    characters changed in 3.12, so raw repr() is not portable)."""
    if v is None:
        return b"z:"
    if isinstance(v, bool):
        return (b"n:1" if v else b"n:0")
    if isinstance(v, int):
        return b"n:" + str(v).encode()
    if isinstance(v, float):
        return b"f:" + repr(v).encode()
    if isinstance(v, bytes):
        return b"b:" + v
    return b"s:" + str(v).encode("utf-8", "surrogatepass")


def _rows_sha_rows(con, names):
    h = hashlib.sha256()
    for t in names:
        cols = [r[1] for r in con.execute(f'PRAGMA table_info("{t}")')]
        order = ", ".join(f'"{c}"' for c in cols)
        for row in con.execute(f'SELECT * FROM "{t}" ORDER BY {order}'):
            for v in row:
                h.update(_canon_value(v))
            h.update(b"\x1e")
    return h.hexdigest()


def schema_sha(db_path):
    con = sqlite3.connect(str(db_path))
    try:
        rows = con.execute("SELECT type, name, tbl_name, sql FROM sqlite_master "
                           "ORDER BY type, name").fetchall()
        h = hashlib.sha256()
        for r in rows:
            for v in r:
                h.update(_canon_value(v))
            h.update(b"\x1e")
        return h.hexdigest()
    finally:
        con.close()


def rows_sha(db_path):
    con = sqlite3.connect(str(db_path))
    try:
        names = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return _rows_sha_rows(con, names)
    finally:
        con.close()


def table_counts(db_path):
    con = sqlite3.connect(str(db_path))
    try:
        out = {}
        for t in TABLES:
            out[t] = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        return out
    finally:
        con.close()


def validate_snapshot_contract(initial_db, after_db):
    if schema_sha(initial_db) != SCHEMA_SHA256:
        raise ValueError(f"initial_db schema sha mismatch: {schema_sha(initial_db)}")
    counts = table_counts(initial_db)
    if counts != SEED_COUNTS:
        raise ValueError(f"initial_db table counts mismatch: {counts!r}")
    if rows_sha(initial_db) != SEED_ROWS_SHA256:
        raise ValueError("initial_db is not the frozen tumblr seed (rows sha mismatch)")
    if schema_sha(after_db) != SCHEMA_SHA256:
        raise ValueError(f"after_db schema sha mismatch: {schema_sha(after_db)}")


def changed_tables(initial_db, after_db, tables=None):
    con_i = sqlite3.connect(str(initial_db))
    con_a = sqlite3.connect(str(after_db))
    try:
        names = tuple(tables) if tables else TABLES
        changed = []
        for t in names:
            cols = [r[1] for r in con_i.execute(f'PRAGMA table_info("{t}")')]
            order = ", ".join(f'"{c}"' for c in cols) or "1"
            ri = con_i.execute(f'SELECT * FROM "{t}" ORDER BY {order}').fetchall()
            ra = con_a.execute(f'SELECT * FROM "{t}" ORDER BY {order}').fetchall()
            if ri != ra:
                changed.append(t)
        return changed
    finally:
        con_i.close()
        con_a.close()


def resolve_snapshots(args, task_id):
    initial_db = resolve_db(args.initial_db, args.container, "instance_seed")
    after_db = resolve_db(args.after_db, args.container, "instance")
    if not initial_db or not after_db:
        fail_closed(task_id, "database_unavailable",
                    "both initial (seed) and after (instance) tumblr database "
                    "snapshots are required")
    try:
        validate_snapshot_contract(initial_db, after_db)
    except (OSError, sqlite3.Error, ValueError) as exc:
        fail_closed(task_id, "snapshot_contract_invalid", str(exc))
    return str(initial_db), str(after_db)


# ---------------------------------------------------------------- tumblr-specific helpers
def user_by_email(db_path, email):
    rows = db_query(db_path, "SELECT * FROM users WHERE lower(email) = lower(?) "
                    "LIMIT 1", (email,))
    return rows[0] if rows else None


def blog_by_name(db_path, name):
    rows = db_query(db_path, "SELECT * FROM blogs WHERE name = ? LIMIT 1", (name,))
    return rows[0] if rows else None


def post_by_id(db_path, post_id):
    rows = db_query(db_path, "SELECT * FROM posts WHERE id = ? LIMIT 1", (str(post_id),))
    return rows[0] if rows else None


def follow_pairs(db_path):
    return {(r["user_id"], r["blog_id"]): r for r in
            db_query(db_path, "SELECT * FROM follows")}


def like_pairs(db_path):
    return {(r["user_id"], r["post_id"]): r for r in
            db_query(db_path, "SELECT * FROM likes")}


def check_trajectory_identity(judge, traj, task_id):
    judge.check("package_task_id", traj.get("task_id") == task_id,
                f"task_id={traj.get('task_id')!r}")
    judge.check("terminated_agent_done", traj.get("terminated") == "agent_done",
                f"terminated={traj.get('terminated')!r}")
    answer = final_answer(traj)
    judge.check("nonempty_final_answer", bool(answer), "final answer is empty")
    start = traj.get("start_url")
    urls = site_urls(traj)
    judge.check("has_site_urls", bool(urls), "no loopback site URLs recorded")
    if start:
        p = urlparse(str(start))
        origin = (p.scheme, p.hostname.casefold(),
                  p.port or (443 if p.scheme == "https" else 80))

        def _origin(u):
            q = urlparse(str(u))
            return (q.scheme, (q.hostname or "").casefold(),
                    q.port or (443 if q.scheme == "https" else 80))

        recorded = [u for u in trajectory_urls(traj)
                    if urlparse(str(u)).scheme in {"http", "https"}]
        off = [u for u in recorded if _origin(u) != origin]
        judge.check("same_origin_urls", not off,
                    f"off-origin URLs: {off[:3]!r}")
    shots = traj.get("_shots") or {}
    judge.check("screenshots_present", bool(shots),
                "no step_*.png screenshots found")
    bad = []
    for name, path in list(shots.items())[:40]:
        data = path.read_bytes()[:8]
        if data[:8] != b"\x89PNG\r\n\x1a\n":
            bad.append(name)
    judge.check("screenshots_are_png", not bad, f"non-PNG shots: {bad[:3]!r}")


def check_read_only(judge, initial_db, after_db):
    changed = changed_tables(initial_db, after_db)
    judge.check("db_unchanged", not changed,
                f"read-only task mutated tables: {changed!r}")


# ---------------------------------------------------------------- judge + CLI
class Judge:
    def __init__(self, task_id, no_llm=False):
        self.task_id = task_id
        self.no_llm = bool(no_llm)
        self.ok = True
        self.reason = ""
        self.evidence = []

    def check(self, name, cond, evidence=""):
        if cond:
            self.evidence.append(f"[PASS] {name}: {evidence}")
        else:
            self.ok = False
            if not self.reason:
                self.reason = name
            self.evidence.append(f"[FAIL] {name}: {evidence}")
        return bool(cond)

    def note(self, name, text):
        self.evidence.append(f"[INFO] {name}: {text}")

    def emit(self):
        print(json.dumps({"task_id": self.task_id, "pass": self.ok,
                          "reason": self.reason or "all checks passed",
                          "evidence": self.evidence}, ensure_ascii=False, indent=2))
        sys.exit(0 if self.ok else 1)


def fail_closed(task_id, reason, detail):
    print(json.dumps({"task_id": task_id, "pass": False, "infra_error": True,
                      "reason": reason,
                      "evidence": [f"[FAIL] {reason}: {detail}"]},
                     ensure_ascii=False, indent=2))
    sys.exit(1)


@dataclass
class VerifyArgs:
    run_dir: str = ""
    initial_db: str = ""
    after_db: str = ""
    container: str = ""
    no_llm: str = "False"

    def post_process(self):
        if not self.container:
            self.container = DEFAULT_CONTAINER
        if self.run_dir:
            run = Path(self.run_dir)
            if not self.initial_db and (run / "initial.db").is_file():
                self.initial_db = str(run / "initial.db")
            if not self.after_db and (run / "after.db").is_file():
                self.after_db = str(run / "after.db")


def parse_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_dir", required=True)
    parser.add_argument("--initial_db", default="")
    parser.add_argument("--after_db", default="")
    parser.add_argument("--container", default="")
    parser.add_argument("--no_llm", default="False")
    ns = parser.parse_args()
    return VerifyArgs(run_dir=ns.run_dir, initial_db=ns.initial_db,
                      after_db=ns.after_db, container=ns.container,
                      no_llm=str(ns.no_llm))


def run_verifier(task_id, run_checks, module_vars):
    args = parse_args()
    args.post_process()
    run_dir = args.run_dir
    try:
        traj = load_run(run_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        fail_closed(task_id, "trajectory_unreadable", str(exc))
    initial_db, after_db = resolve_snapshots(args, task_id)
    judge = Judge(task_id, no_llm=str(args.no_llm).lower() in ("1", "true", "yes"))
    try:
        run_checks(judge, traj, initial_db, after_db)
    except (OSError, sqlite3.Error, ValueError, KeyError) as exc:
        fail_closed(task_id, "verifier_error", f"{type(exc).__name__}: {exc}")
    judge.emit()
