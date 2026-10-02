#!/usr/bin/env python3
"""verify_lib.py — deterministic verifier utilities for thumbtack task
verification (review track, orch/review/thumbtack).

Philosophy: DETERMINISTIC FIRST — same contract as the hardened reviewer
suites (``sites/statista/verify/verify_lib.py``). No LLM call is load-bearing;
every check is regex / token / SQLite after-state.

  1. Package identity (fail-closed): task_id matches, ``terminated`` with
     ``agent_done``, non-empty final answer, every recorded URL on the same
     loopback origin AND port as ``start_url``, every referenced screenshot a
     decodable PNG.
  2. Navigation gates (anti knowledge-shortcut): the agent MUST have opened
     the on-site surfaces the task names (login, category listings with the
     required sort, pro profiles, cost guides, the quote wizard, project
     pages, message threads, the account area). A correct answer with no
     matching navigation is a memory-recall shortcut = FAIL.
  3. Answer check: affirmative token / phrase / number matching against
     frozen ground truth HARDCODED in each ``verify_N.py`` (never in
     tasks.jsonl).
  4. DB after-state: initial (seed) vs after (instance) SQLite snapshots.
     Read-only tasks require every table row-identical to the seed; stateful
     tasks require the exact allowed row delta and nothing else (a new
     project + its 5 deterministic matches, a saved-pro row, a review row,
     a thread + user/pro message pair, a registered user with a bcrypt hash,
     a cancelled project). The seed contract is pinned to the review
     container's deterministic build (PYTHONHASHSEED=0 seed build, md5
     0c1320fd…).

Input signature (per task):
  --run_dir DIR        agent trajectory dir: trajectory.json + screenshots/step_NNN.png
  --initial_db PATH    initial-state SQLite DB (default: <run_dir>/initial.db, else
                       instance_seed from the container)
  --after_db PATH      after-state  SQLite DB (default: <run_dir>/after.db, else live
                       instance DB from the container)
  --container NAME     docker container to fetch DBs from (default: $WH_CONTAINER or
                       wh-tt-review)
Output: JSON {task_id, pass, reason, evidence[]} to stdout; exit 0 on PASS, 1 on FAIL.
"""
import hashlib
import ipaddress
import json
import os
import re
import sqlite3
import subprocess
import sys
import zlib
from pathlib import Path
from urllib.parse import urlparse

SITE = "thumbtack"
DEFAULT_CONTAINER = os.environ.get("WH_CONTAINER", "wh-tt-review")

# ---------------------------------------------------------------- frozen seed contract
# Review container wh-tt-review, image webharbor:tt-review (built from the
# committed tree at 371b81fa), thumbtack seed built in-image with
# PYTHONHASHSEED=0; instance == instance_seed, md5 0c1320fd…, byte-reproducible.
TABLES = ("content_records", "categories", "cost_guides", "users", "pros", "projects",
          "enrollments", "reviews", "saved_pros", "project_matches",
          "threads", "messages")
SEED_COUNTS = {"content_records": 1, "categories": 16, "cost_guides": 26, "users": 4, "pros": 177,
               "projects": 5, "enrollments": 0, "reviews": 856,
               "saved_pros": 13, "project_matches": 25, "threads": 1,
               "messages": 2}
SEED_DB_MD5 = "0c1320fdc70f24df23f84cc3a4a0b222"
SEED_USERS = {  # email -> (id, display_name); identity columns never change
    "alice.j@test.com": (1, "Alice Johnson"),
    "bob.c@test.com": (2, "Bob Chen"),
    "carol.d@test.com": (3, "Carol Davis"),
    "david.k@test.com": (4, "David Kim"),
}
DEMO_PASSWORD = "TestPass123!"
BCRYPT_RX = re.compile(r"^\$2[aby]\$12\$[./A-Za-z0-9]{53}$")
MIRROR_TS = "2026-09-26 12:00:00.000000"
MSG_USER_TS = "2026-09-26 12:30:00.000000"
MSG_PRO_TS = "2026-09-26 12:32:00.000000"

# ---------------------------------------------------------------- trajectory
def load_run(run_dir):
    d = Path(run_dir)
    traj = json.loads((d / "trajectory.json").read_text(encoding="utf-8"))
    if not isinstance(traj, dict):
        raise ValueError("trajectory.json must contain a JSON object")
    traj["_run_dir"] = d
    shots_dir = d / "screenshots"
    traj["_shots"] = {p.name: p for p in sorted(shots_dir.glob("step_*.png"))} if shots_dir.is_dir() else {}
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
    if parsed.port is None:
        return False
    host = parsed.hostname.casefold()
    if host == "localhost":
        loopback = True
    else:
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = False
    return loopback


def decode_png(path):
    try:
        from PIL import Image
        with Image.open(path) as image:
            image.load()
            valid = image.format == "PNG" and image.width > 0 and image.height > 0
        return (valid, "decoded PNG")
    except (OSError, ValueError) as exc:
        return (False, str(exc))


def check_trajectory_identity(judge, traj, task_id):
    if traj.get("task_id") != task_id:
        judge.fail(f"task_id mismatch: {traj.get('task_id')!r} != {task_id!r}")
        return
    judge.evidence(f"task_id matches: {task_id}")
    if not traj.get("terminated"):
        judge.fail("trajectory not terminated")
    elif traj.get("termination_reason") != "agent_done":
        judge.fail(f"termination_reason is {traj.get('termination_reason')!r}, expected 'agent_done'")
    else:
        judge.evidence("terminated with agent_done")
    answer = final_answer(traj)
    if not answer:
        judge.fail("empty final_answer")
    else:
        judge.evidence(f"final answer present ({len(answer)} chars)")
    urls = trajectory_urls(traj)
    if not urls:
        judge.fail("no urls recorded in trajectory")
        return
    if not is_site_url(urls[0]):
        judge.fail(f"start_url is not a loopback site url: {urls[0]!r}")
        return
    first = urlparse(urls[0])
    for u in urls[1:]:
        p = urlparse(u)
        if (p.scheme, p.hostname, p.port) != (first.scheme, first.hostname, first.port):
            judge.fail(f"off-origin url in trajectory: {u!r} (start {urls[0]!r})")
            return
    judge.evidence(f"all {len(urls)} recorded urls on origin {first.scheme}://{first.hostname}:{first.port}")
    shots = traj.get("_shots") or {}
    if not shots:
        judge.fail("no step screenshots found in run dir")
        return
    referenced = []
    for step in traj.get("steps") or []:
        if not isinstance(step, dict):
            continue
        for key in ("screenshot_before", "screenshot_after"):
            if step.get(key):
                referenced.append(str(step[key]))
    bad = []
    for name in referenced:
        if name not in shots:
            bad.append(f"{name}: missing from run dir")
            continue
        ok, detail = decode_png(shots[name])
        if not ok:
            bad.append(f"{name}: {detail}")
    if bad:
        judge.fail("screenshot integrity broken: " + "; ".join(bad[:3]))
    else:
        judge.evidence(f"{len(referenced)} referenced screenshots present and decodable")


def check_visited_path(judge, traj, label, pattern):
    rx = re.compile(pattern)
    for u in trajectory_urls(traj):
        if rx.search(u):
            judge.evidence(f"visited {label}: {u}")
            return
    judge.fail(f"never visited {label} (no url matches {pattern!r})")


def check_input_action(judge, traj, label, pattern):
    """The agent must have typed text matching pattern (fill/input action)."""
    rx = re.compile(pattern)
    for step in traj.get("steps") or []:
        if not isinstance(step, dict):
            continue
        action = str(step.get("action") or "")
        params = step.get("params") or {}
        if action in ("input", "type", "fill", "input_text", "type_text"):
            text = str(params.get("text") or params.get("value") or "")
            if rx.search(text):
                judge.evidence(f"typed {label}: {text!r}")
                return
    judge.fail(f"never typed {label} (no input text matches {pattern!r})")


# ---------------------------------------------------------------- answers
def _norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def check_answer_phrase(judge, answer, label, phrase):
    if _norm(phrase) in _norm(answer):
        judge.evidence(f"answer mentions {label}: {phrase!r}")
    else:
        judge.fail(f"answer does not mention {label} (expected phrase {phrase!r})")


def check_answer_any(judge, answer, label, phrases):
    for ph in phrases:
        if _norm(ph) in _norm(answer):
            judge.evidence(f"answer mentions {label}: {ph!r}")
            return
    judge.fail(f"answer does not mention {label} (expected any of {phrases!r})")


def check_answer_number(judge, answer, label, number, context=None):
    from answer_bindings import BINDINGS, number_bound, _number_pattern, _affirmed, _assertions
    task_no = int(getattr(judge, 'task_id', '--0').split('--')[-1])
    groups = BINDINGS.get(task_no, {}).get(label)
    value = str(number)
    if groups:
        hit = number_bound(answer, value, groups)
    else:
        hit = any(_affirmed(segment, m.start()) for segment in _assertions(answer)
                  for m in _number_pattern(value).finditer(segment))
    if hit: judge.evidence(f"{label}: {value}")
    else: judge.fail(f"{label}: missing or incorrectly associated value {value}")


# ---------------------------------------------------------------- db helpers
def _connect(path):
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def fetch_counts(path):
    db = _connect(path)
    try:
        return {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}
    finally:
        db.close()


def table_rows(path, table):
    db = _connect(path)
    try:
        cols = [r[1] for r in db.execute(f"PRAGMA table_info({table})")]
        order = ", ".join(f'"{c}"' for c in cols)
        rows = [tuple(r) for r in db.execute(f"SELECT * FROM {table} ORDER BY {order}")]
        return cols, rows
    finally:
        db.close()


def check_read_only(judge, initial_db, after_db):
    """Every table must be row-identical between initial and after snapshots."""
    for table in TABLES:
        _, rows_i = table_rows(initial_db, table)
        _, rows_a = table_rows(after_db, table)
        if rows_i != rows_a:
            judge.fail(f"read-only task but table {table!r} changed "
                       f"({len(rows_i)} -> {len(rows_a)} rows)")
            return
    judge.evidence(f"read-only verified: all {len(TABLES)} tables row-identical to the seed")


def _diff_rows(initial_db, after_db, table):
    """Key-aware diff: a changed row is an UPDATE, not add+remove."""
    cols, rows_i = table_rows(initial_db, table)
    _, rows_a = table_rows(after_db, table)
    key = cols.index("id") if "id" in cols else 0
    ids_i = {r[key] for r in rows_i}
    ids_a = {r[key] for r in rows_a}
    added = [r for r in rows_a if r[key] not in ids_i]
    removed = [r for r in rows_i if r[key] not in ids_a]
    return added, removed


def _updated_rows(initial_db, after_db, table):
    """Rows whose id exists on both sides but whose content differs."""
    cols, rows_i = table_rows(initial_db, table)
    _, rows_a = table_rows(after_db, table)
    key = cols.index("id") if "id" in cols else 0
    by_id_i = {r[key]: r for r in rows_i}
    by_id_a = {r[key]: r for r in rows_a}
    updated = [by_id_a[k] for k in by_id_a
               if k in by_id_i and by_id_a[k] != by_id_i[k]]
    return updated


def check_only_tables_changed(judge, initial_db, after_db, allowed):
    """Only the allowed tables may differ (added/removed/updated rows);
    every other table must be row-identical."""
    for table in TABLES:
        added, removed = _diff_rows(initial_db, after_db, table)
        updated = _updated_rows(initial_db, after_db, table)
        changed = bool(added or removed or updated)
        if table in allowed:
            if changed:
                judge.evidence(f"table {table!r} changed as allowed "
                               f"(+{len(added)} -{len(removed)} ~{len(updated)})")
            else:
                judge.fail(f"table {table!r} is in the allowed set but did not change")
        elif changed:
            judge.fail(f"unexpected change in table {table!r} "
                       f"(+{len(added)} -{len(removed)} ~{len(updated)} rows)")


def check_table_added(judge, initial_db, after_db, table, expect_rows, key_index=0):
    """Exactly `expect_rows` rows must be added to `table`, matching the
    frozen ground-truth tuples on the non-timestamp columns."""
    added, removed = _diff_rows(initial_db, after_db, table)
    if removed:
        judge.fail(f"unexpected row removal from {table!r}: {removed[:2]}")
        return
    if len(added) != len(expect_rows):
        judge.fail(f"{table!r}: expected {len(expect_rows)} added row(s), got {len(added)}")
        return
    for exp in expect_rows:
        # match on all non-timestamp positions
        matched = False
        for got in added:
            if all(g == e for i, (g, e) in enumerate(zip(got, exp)) if e is not None and not (table == "saved_pros" and i == 0)):
                matched = True
                break
        if not matched:
            judge.fail(f"{table!r}: expected added row {exp!r} not found "
                       f"(added: {[tuple(a) for a in added][:3]})")
            return
    judge.evidence(f"{table!r}: +{len(expect_rows)} expected row(s) verified")


def check_table_removed(judge, initial_db, after_db, table, expect_count, where):
    added, removed = _diff_rows(initial_db, after_db, table)
    if added:
        judge.fail(f"unexpected row addition to {table!r}: {added[:2]}")
        return
    if len(removed) != expect_count:
        judge.fail(f"{table!r}: expected {expect_count} removed row(s), got {len(removed)}")
        return
    db = _connect(after_db)
    try:
        left = db.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()[0]
    finally:
        db.close()
    if left != 0:
        judge.fail(f"{table!r}: rows matching {where!r} still present ({left})")
        return
    judge.evidence(f"{table!r}: {expect_count} row(s) removed as expected")


def check_row_updated(judge, initial_db, after_db, table, where, column, expect):
    """The single row selected by `where` must have `column` == expect in the
    after DB (and a different/None-ish value before is not required)."""
    db = _connect(after_db)
    try:
        rows = db.execute(f"SELECT {column} FROM {table} WHERE {where}").fetchall()
    finally:
        db.close()
    if len(rows) != 1:
        judge.fail(f"{table!r}: expected exactly 1 row for {where!r}, got {len(rows)}")
        return
    got = rows[0][0]
    if str(got) != str(expect):
        judge.fail(f"{table!r}.{column} for {where!r} is {got!r}, expected {expect!r}")
        return
    judge.evidence(f"{table!r}.{column} updated to {expect!r} ({where})")


def check_new_user(judge, initial_db, after_db, email, username, display_name):
    added, _ = _diff_rows(initial_db, after_db, "users")
    if len(added) != 1:
        judge.fail(f"users: expected exactly 1 added row, got {len(added)}")
        return
    row = added[0]  # (id, username, email, display_name, password_hash, phone, zip, address, created_at)
    if row[2] != email:
        judge.fail(f"registered email is {row[2]!r}, expected {email!r}")
        return
    if row[1] != username or row[3] != display_name:
        judge.fail(f"registered identity is {row[1]!r}/{row[3]!r}, "
                   f"expected {username!r}/{display_name!r}")
        return
    if not BCRYPT_RX.match(row[4] or ""):
        judge.fail(f"registered password_hash is not a bcrypt hash: {row[4]!r}")
        return
    judge.evidence(f"new user registered: {email} ({display_name}) with bcrypt hash")


def check_seed_contract(judge, db_path):
    if logical_digest(db_path) != "37db1a9fdccea722938aabb9746bf1694c3546411dc7183c93e35eb750d6e2ec":
        judge.fail("initial database differs from reviewed seed schema or rows")
        return
    counts = fetch_counts(db_path)
    for table, count in SEED_COUNTS.items():
        if counts.get(table) != count:
            judge.fail(f"seed contract broken: {table} has {counts.get(table)} rows, "
                       f"expected {count}")
            return
    judge.evidence("seed table counts match the frozen contract "
                   f"({sum(SEED_COUNTS.values())} rows over {len(TABLES)} tables)")


# ---------------------------------------------------------------- runner
class Judge:
    def __init__(self):
        self.passed = True
        self.reason = ""
        self.evidence_list = []

    def evidence(self, msg):
        self.evidence_list.append(msg)

    def fail(self, msg):
        self.passed = False
        if not self.reason:
            self.reason = msg
        self.evidence_list.append("FAIL: " + msg)


def acquire_dbs(run_dir, initial_arg, after_arg, container):
    run_dir = Path(run_dir)
    initial = Path(initial_arg) if initial_arg else run_dir / "initial.db"
    after = Path(after_arg) if after_arg else run_dir / "after.db"
    if not initial.is_file():
        subprocess.run(["docker", "cp",
                        f"{container}:/opt/WebSyn/thumbtack/instance_seed/thumbtack.db",
                        str(initial)], check=True)
    if not after.is_file():
        subprocess.run(["docker", "cp",
                        f"{container}:/opt/WebSyn/thumbtack/instance/thumbtack.db",
                        str(after)], check=True)
    return initial, after


def run_verifier(task_id, run_checks):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--run_dir", required=True)
    ap.add_argument("--initial_db", default=None)
    ap.add_argument("--after_db", default=None)
    ap.add_argument("--container", default=DEFAULT_CONTAINER)
    args = ap.parse_args()
    judge = Judge()
    judge.task_id = task_id
    result = {"task_id": task_id, "pass": False, "reason": "", "evidence": []}
    try:
        traj = load_run(args.run_dir)
        initial, after = acquire_dbs(args.run_dir, args.initial_db,
                                     args.after_db, args.container)
        check_seed_contract(judge, initial)
        check_trajectory_identity(judge, traj, task_id)
        if judge.passed:
            run_checks(judge, traj, initial, after)
            from state_contract import check
            check(judge, task_id, initial, after)
    except Exception as e:  # fail closed on any verifier error
        judge.fail(f"verifier error: {type(e).__name__}: {e}")
    result["pass"] = judge.passed
    result["reason"] = judge.reason or ("all checks passed" if judge.passed else "failed")
    result["evidence"] = judge.evidence_list
    print(json.dumps(result, indent=1))
    return 0 if judge.passed else 1


def logical_digest(path):
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as con:
        schema = list(con.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"))
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        rows = {t: sorted([list(r) for r in con.execute('SELECT * FROM "'+t+'"')], key=repr) for t in tables}
    return hashlib.sha256(json.dumps([schema, rows], default=str).encode()).hexdigest()
