#!/usr/bin/env python3
"""verify_lib.py — deterministic verifier utilities for trip_com task
verification.

Philosophy: DETERMINISTIC FIRST — same contract as the hardened reviewer suites
(``sites/super_lawyers/verify/verify_lib.py``). No LLM call is load-bearing;
every check is regex / token / SQLite after-state.

  1. Package identity (fail-closed): task_id matches, ``terminated`` with
     ``agent_done``, non-empty final answer, every recorded URL on the same
     loopback origin AND port as ``start_url``, every referenced screenshot a
     decodable PNG.
  2. Navigation gates (anti knowledge-shortcut): the agent MUST have opened the
     on-site surfaces the task names (search / list / detail / book /
     confirmation / account pages). A correct answer with no matching
     navigation is a memory-recall shortcut = FAIL.
  3. Answer check: affirmative token / phrase / number matching against frozen
     ground truth HARDCODED in each ``verify_N.py`` (never in tasks.jsonl).
     Price ties are graded as documented accepted sets (e.g. the three $213
     Delta nonstop outbounds on SFO->JFK, the three $93 Miami rooms).
  4. DB after-state: initial (seed) vs after (instance) SQLite snapshots.
     Read-only tasks require every table row-identical to the seed; stateful
     tasks require the exact allowed row delta and nothing else (one booking
     row with the frozen price math, a status flip, a wishlist set-delta).

Seed reproducibility: the trip_com seed is byte-reproducible — the r2
reviewer's independent image build (from contribution a375a671) reproduces
md5 99cb40509b521600acb46295220db12d across fresh seed builds. The contract
freezes the logical digests (schema + rows + counts) computed with the exact
functions below.

Input signature (per task):
  --run_dir DIR        agent trajectory dir: trajectory.json + screenshots/step_NNN.png
  --initial_db PATH    initial-state SQLite DB (default: <run_dir>/initial.db, else
                       instance_seed from the container)
  --after_db PATH      after-state  SQLite DB (default: <run_dir>/after.db, else live
                       instance DB from the container)
  --container NAME     docker container to fetch DBs from (default: $WH_CONTAINER or
                       wh-trip-com-review)
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
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

SITE = "trip_com"
DEFAULT_CONTAINER = os.environ.get("WH_CONTAINER", "wh-trip-com-review")

# ---------------------------------------------------------------- frozen seed contract
TABLES = ("airports", "attraction_bookings", "attraction_packages", "attractions",
          "cities", "coupons", "flight_bookings", "flight_routes", "flights",
          "guides", "hotel_bookings", "hotel_photos", "hotel_reviews", "hotels",
          "room_rates", "users", "wishlist_items")
SEED_COUNTS = {'airports': 7, 'attraction_bookings': 2, 'attraction_packages': 95, 'attractions': 131, 'cities': 11, 'coupons': 4, 'flight_bookings': 2, 'flight_routes': 6, 'flights': 946, 'guides': 6, 'hotel_bookings': 4, 'hotel_photos': 1494, 'hotel_reviews': 83, 'hotels': 1110, 'room_rates': 588, 'users': 4, 'wishlist_items': 12}
# sha256 over sqlite_master (type, name, tbl_name, sql) of instance_seed/trip_com.db.
SCHEMA_SHA256 = "e3307500b48521fc859bc2b859b5b41e020292fa4daae898d355fb143cf3ea86"
# sha256 over every seed row (table-canonical, ORDER BY all columns).
# r2 re-freeze (2026-09-28): 12 attractions.img values changed via the
# contributor's tracked asset path manifest (image de-duplication pass); table
# counts and schema digest are unchanged.
SEED_ROWS_SHA256 = "6f6a7eb4c4ccde9a6100dc80bdc166e614ab93f480e8afa8100474a70d0e67b3"
# Byte-level md5 of the seed produced inside the pinned image. r2 value:
# reproduced independently by the r2 reviewer's image build (two fresh
# PYTHONHASHSEED=0 seed builds inside the image, byte-identical).
SEED_FILE_MD5 = "99cb40509b521600acb46295220db12d"
DEMO_PASSWORD = "TestPass123!"
SEED_USERS = {  # email -> (id, display); identity columns never change
    "alice.j@test.com": (1, "Alice Johnson"),
    "bob.c@test.com": (2, "Bob Chen"),
    "carol.d@test.com": (3, "Carol Davis"),
    "david.k@test.com": (4, "David Kim"),
}
NUM_TOKEN_RX = r"[0-9,.]+"


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
    for step in traj.get("steps", []):
        for key in ("url", "url_after"):
            if step.get(key):
                urls.append(str(step[key]))
    return urls


def final_answer(traj):
    answer = traj.get("final_answer")
    return "" if answer is None else str(answer)


def _png_ok(path):
    try:
        from PIL import Image
        with Image.open(path) as image:
            image.load()
            valid = image.format == "PNG" and image.width > 0 and image.height > 0
        return valid
    except (OSError, ValueError) as exc:
        return False


# ---------------------------------------------------------------- judge
@dataclass
class Judge:
    task_id: str
    evidence: list = field(default_factory=list)
    failures: list = field(default_factory=list)

    def ok(self, check, note):
        self.evidence.append(f"PASS {check}: {note}")

    def fail(self, check, note):
        self.failures.append(f"FAIL {check}: {note}")
        self.evidence.append(f"FAIL {check}: {note}")


def _is_loopback(hostname) -> bool:
    if not hostname:
        return False
    if hostname == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def check_trajectory_identity(judge, traj, task_id):
    if traj.get("task_id") != task_id:
        judge.fail("task_id", f"expected {task_id!r}, got {traj.get('task_id')!r}")
    else:
        judge.ok("task_id", traj.get("task_id"))
    if not traj.get("terminated") or traj.get("termination_reason") != "agent_done":
        judge.fail("terminated", "trajectory must be terminated with agent_done")
    else:
        judge.ok("terminated", "agent_done")
    if not final_answer(traj).strip():
        judge.fail("final_answer", "empty final answer")
    else:
        judge.ok("final_answer", f"{len(final_answer(traj))} chars")
    start = urlparse(str(traj.get("start_url", "")))
    if not _is_loopback(start.hostname):
        judge.fail("start_url_loopback", f"start_url not loopback: {start}")
    else:
        judge.ok("start_url_loopback", f"{start.hostname}:{start.port}")
    bad = []
    for url in trajectory_urls(traj):
        u = urlparse(url)
        if not _is_loopback(u.hostname) or u.port != start.port:
            bad.append(url)
    if bad:
        judge.fail("urls_same_origin", f"{len(bad)} off-site/other-port URLs: {bad[:3]}")
    else:
        judge.ok("urls_same_origin", f"{len(trajectory_urls(traj))} URLs on {start.netloc}")


def check_screenshots(judge, traj):
    shots = traj.get("_shots", {})
    referenced = set()
    for step in traj.get("steps", []):
        for key in ("screenshot_before", "screenshot_after"):
            if step.get(key):
                referenced.add(step[key])
    if not referenced:
        judge.fail("screenshots_present", "no screenshots referenced")
        return
    bad = [name for name in sorted(referenced)
           if name not in shots or not _png_ok(shots[name])]
    if bad:
        judge.fail("screenshots_decode", f"undecodable/missing: {bad[:3]}")
    else:
        judge.ok("screenshots_decode", f"{len(referenced)} PNGs decode")


def check_visited_path(judge, traj, check, pattern):
    rx = re.compile(pattern)
    urls = trajectory_urls(traj)
    hit = [u for u in urls if rx.search(u)]
    if not hit:
        judge.fail(check, f"no visited URL matches {pattern!r}")
    else:
        judge.ok(check, hit[0])


def check_visited_any(judge, traj, check, patterns):
    for pattern in patterns:
        rx = re.compile(pattern)
        if any(rx.search(u) for u in trajectory_urls(traj)):
            judge.ok(check, pattern)
            return
    judge.fail(check, f"no visited URL matches any of {patterns!r}")


# ---------------------------------------------------------------- answers
def _norm(text):
    return re.sub(r"\s+", " ", str(text)).lower()


def check_answer_phrase(judge, answer, check, phrase):
    if _norm(phrase) in _norm(answer):
        judge.ok(check, repr(phrase))
    else:
        judge.fail(check, f"answer lacks {phrase!r}")


def check_answer_any(judge, answer, check, phrases):
    for phrase in phrases:
        if _norm(phrase) in _norm(answer):
            judge.ok(check, repr(phrase))
            return
    judge.fail(check, f"answer lacks all of {phrases!r}")


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
    if hit: judge.ok(label, value)
    else: judge.fail(label, f"missing or incorrectly associated value {value}")


def check_answer_money(judge, answer, label, amount):
    from answer_bindings import BINDINGS, number_bound, _number_pattern, _affirmed, _assertions
    task_no = int(getattr(judge, 'task_id', '--0').split('--')[-1])
    groups = BINDINGS.get(task_no, {}).get(label)
    value = str(amount)
    if groups:
        hit = number_bound(answer, value, groups)
    else:
        hit = any(_affirmed(segment, m.start()) for segment in _assertions(answer)
                  for m in _number_pattern(value).finditer(segment))
    if hit: judge.ok(label, value)
    else: judge.fail(label, f"missing or incorrectly associated value {value}")


def check_answer_count_at_least(judge, answer, check, options, minimum):
    found = sum(1 for o in options if _norm(o) in _norm(answer))
    if found >= minimum:
        judge.ok(check, f"{found}/{len(options)} item(s)")
    else:
        judge.fail(check, f"only {found}/{minimum} of {options!r} in answer")


def check_answer_absent(judge, answer, check, phrase):
    if _norm(phrase) in _norm(answer):
        judge.fail(check, f"answer must not contain {phrase!r}")
    else:
        judge.ok(check, f"absent: {phrase!r}")


def check_blocked(judge, check, note):
    """BLOCKED task machinery: the check can never pass at the current site
    state (documented review finding); every run fails here by design."""
    judge.fail(check, f"BLOCKED: {note}")


# ---------------------------------------------------------------- DB after-state
def _connect(path, container):
    p = Path(path)
    if not p.is_file() and container:
        inner = ("/opt/WebSyn/trip_com/instance/trip_com.db"
                 if "after" in p.name else
                 "/opt/WebSyn/trip_com/instance_seed/trip_com.db")
        subprocess.run(["docker", "cp", f"{container}:{inner}", str(p)],
                       check=True, capture_output=True)
    if not p.is_file():
        raise FileNotFoundError(f"database not found: {p}")
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True)


def _table_rows(db, table):
    cols = [r[1] for r in db.execute(f'PRAGMA table_info("{table}")')]
    if not cols:
        return {}
    order = ", ".join(f'"{c}"' for c in cols)
    return {row[0]: list(row) for row in db.execute(f'SELECT * FROM "{table}" ORDER BY {order}')}


def _diff(initial, after, table):
    a = _table_rows(initial, table)
    b = _table_rows(after, table)
    added = [b[k] for k in b if k not in a]
    removed = [a[k] for k in a if k not in b]
    changed = [(a[k], b[k]) for k in a if k in b and a[k] != b[k]]
    return added, removed, changed


def check_read_only(judge, initial_db, after_db):
    """Every table must be row-identical to the seed snapshot."""
    bad = []
    for table in TABLES:
        added, removed, changed = _diff(initial_db, after_db, table)
        if added or removed or changed:
            bad.append(f"{table}(+{len(added)}/-{len(removed)}/~{len(changed)})")
    if bad:
        judge.fail("db_read_only", f"unexpected deltas: {bad}")
    else:
        judge.ok("db_read_only", f"all {len(TABLES)} tables row-identical to seed")


def check_only_tables_changed(judge, initial_db, after_db, allowed):
    bad = []
    for table in TABLES:
        added, removed, changed = _diff(initial_db, after_db, table)
        if (added or removed or changed) and table not in allowed:
            bad.append(table)
    if bad:
        judge.fail("db_tables_changed", f"unexpected writes: {bad}")
    else:
        judge.ok("db_tables_changed", f"only {sorted(allowed)} changed")


def _match(row, template):
    """Row matches template; None in a template slot is a wildcard; a leading
    'rx:' value is a regex on str(field); a set value accepts any member."""
    if len(row) != len(template):
        return False
    for got, want in zip(row, template):
        if want is None:
            continue
        if isinstance(want, (set, frozenset, list)) and not (
                isinstance(want, str) and want.startswith("rx:")):
            if got not in want:
                return False
        elif isinstance(want, str) and want.startswith("rx:"):
            if not re.search(want[3:], str(got)):
                return False
        elif got != want:
            return False
    return True


def check_rows_added(judge, initial_db, after_db, table, templates, check):
    added, removed, changed = _diff(initial_db, after_db, table)
    if removed or changed:
        judge.fail(check, "unrequested removal or modification of existing rows")
    if len(added) != len(templates):
        judge.fail(check, f"expected {len(templates)} added row(s) in {table}, got {len(added)}: {added}")
        return
    for tpl in templates:
        if not any(_match(row, tpl) for row in added):
            judge.fail(check, f"no added row in {table} matches {tpl}")
            return
    judge.ok(check, f"{len(templates)} row(s) added to {table}")


def check_rows_changed(judge, initial_db, after_db, table, templates, check):
    added, removed, changed = _diff(initial_db, after_db, table)
    if added or removed:
        judge.fail(check, "unrequested addition or removal")
    if len(changed) != len(templates):
        judge.fail(check, f"expected {len(templates)} changed row(s) in {table}, got {len(changed)}")
        return
    for tpl in templates:
        if not any(_match(new, tpl) for _, new in changed):
            judge.fail(check, f"no changed row in {table} matches {tpl}")
            return
    judge.ok(check, f"{len(templates)} row(s) changed in {table}")


def check_set_delta(judge, initial_db, after_db, table, key_cols, removed_templates,
                    added_templates, check):
    """Set-semantics delta on `key_cols` (SQLite reuses the max rowid, so a
    remove-then-add rewrites the same id and exact-row diffing sees a 'change')."""
    def keyset(db):
        cols = ", ".join(f'"{c}"' for c in key_cols)
        return {tuple(str(v) for v in row) for row in
                db.execute(f'SELECT {cols} FROM "{table}"')}
    a, b = keyset(initial_db), keyset(after_db)
    removed = a - b
    added = b - a
    want_removed = {tuple(str(x) for x in t) for t in removed_templates}
    want_added = {tuple(str(x) for x in t) for t in added_templates}
    if removed != want_removed or added != want_added:
        judge.fail(check, f"removed={sorted(removed)} (want {sorted(want_removed)}); "
                          f"added={sorted(added)} (want {sorted(want_added)})")
    else:
        judge.ok(check, f"-{len(removed)}/+{len(added)} on {key_cols}")


# ---------------------------------------------------------------- seed contract
def check_seed_contract(judge, seed_db):
    counts = {t: seed_db.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in TABLES}
    if counts != SEED_COUNTS:
        judge.fail("seed_counts", f"counts differ: {counts}")
    else:
        judge.ok("seed_counts", f"{sum(counts.values())} rows across {len(TABLES)} tables")
    schema_rows = list(seed_db.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"))
    digest = hashlib.sha256(json.dumps(schema_rows, default=str).encode()).hexdigest()
    if digest != SCHEMA_SHA256:
        judge.fail("seed_schema", f"schema digest {digest}")
    else:
        judge.ok("seed_schema", digest[:16])
    rows_src = []
    for t in TABLES:
        cols = [r[1] for r in seed_db.execute(f'PRAGMA table_info("{t}")')]
        order = ", ".join(f'"{c}"' for c in cols)
        for row in seed_db.execute(f'SELECT * FROM "{t}" ORDER BY {order}'):
            rows_src.append([t, list(row)])
    rdigest = hashlib.sha256(json.dumps(rows_src, default=str).encode()).hexdigest()
    if rdigest != SEED_ROWS_SHA256:
        judge.fail("seed_rows", f"rows digest {rdigest}")
    else:
        judge.ok("seed_rows", rdigest[:16])


# ---------------------------------------------------------------- runner
def run_verifier(task_id, run_checks):
    from argparse import ArgumentParser
    parser = ArgumentParser(description=f"Deterministic verifier for {task_id}")
    parser.add_argument("--run_dir", required=True)
    parser.add_argument("--initial_db", default=None)
    parser.add_argument("--after_db", default=None)
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    traj = load_run(run_dir)
    initial = _connect(args.initial_db or run_dir / "initial.db", DEFAULT_CONTAINER)
    after = _connect(args.after_db or run_dir / "after.db", DEFAULT_CONTAINER)

    judge = Judge(task_id)
    try:
        check_seed_contract(judge, initial)
        check_schema_unchanged(judge, initial, after)
        run_checks(judge, traj, initial, after)
        check_booking_identity(judge, traj, initial, after)
    finally:
        initial.close()
        after.close()
    verdict = {"task_id": task_id, "pass": not judge.failures,
               "reason": "; ".join(judge.failures) or "all checks passed",
               "evidence": judge.evidence}
    print(json.dumps(verdict, indent=1))
    return 0 if verdict["pass"] else 1


if __name__ == "__main__":
    raise SystemExit("import this module from verify_<n>.py")


def check_schema_unchanged(judge, initial, after):
    query = "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
    if list(initial.execute(query)) != list(after.execute(query)):
        judge.fail("schema", "after-state schema differs from seed")


def check_booking_identity(judge, traj, initial, after):
    for table in ('hotel_bookings','flight_bookings','attraction_bookings'):
        added, _, _ = _diff(initial, after, table)
        columns = [r[1] for r in after.execute('PRAGMA table_info('+table+')')]
        for values in added:
            row = dict(zip(columns, values))
            if row['user_id'] is not None:
                judge.fail('booking_owner', 'guest booking attached to an account')
            if 'booking reference' in str(traj.get('task', traj.get('ques', ''))).lower() and row['ref'] not in final_answer(traj):
                judge.fail('booking_reference', 'answer omits actual booking reference')
