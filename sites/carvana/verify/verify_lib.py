#!/usr/bin/env python3
"""verify_lib.py — deterministic verifier utilities for carvana task
verification (reviewer contract, orch/review/carvana).

Philosophy: DETERMINISTIC FIRST. No LLM call is load-bearing; every check
is regex / token / SQLite after-state.

  1. Package identity (fail-closed): task_id matches, ``terminated`` with
     ``agent_done``, non-empty final answer, every recorded URL on the same
     loopback origin AND port as ``start_url``, every referenced screenshot
     a decodable PNG.
  2. Seed identity gate (fail-closed): the initial DB snapshot must BE the
     frozen in-image seed (schema + rows digest + counts). A run graded
     against a pre-mutated database fails here. The frozen seed file
     (instance/carvana.db, md5 b93c6c2ecaa2447704a2e0ee4b3e15c4,
     sha256 f10d6bc7ae652d07feba4e84f9a5aac84f5c51f8157577b7b633f5530ae3f455)
     was rebuilt byte-identically twice from the pinned image and every
     per-task reset snapshot in the review evidence matched it.
  3. Navigation gates (anti knowledge-shortcut): the agent MUST have opened
     the on-site surfaces the task names (SERP filter states, the target
     VDPs, the estimator, checkout / order pages, account pages, the sell
     flow, help articles). A correct answer with no matching navigation is
     a memory-recall shortcut = FAIL.
  4. Answer check: affirmative token / phrase / number matching against
     ground truth HARDCODED in each ``verify_<n>.py`` (never in tasks.jsonl)
     — transcribed from the reviewer's honest Playwright walk of the mirror
     (wh-carvana-review, seed md5 b93c6c2e...).
  5. DB after-state: read-only tasks require every table row-identical to
     the seed; stateful tasks require the exact allowed row delta and
     nothing else.

Input signature (per task):
  --run_dir DIR        agent trajectory dir: trajectory.json + screenshots/step_NNN.png
  --initial_db PATH    initial-state SQLite DB (default: <run_dir>/initial.db)
  --after_db PATH      after-state  SQLite DB (default: <run_dir>/after.db)
  --no_llm true|false  accepted for compatibility; never changes grading
Output: JSON {task_id, pass, reason, evidence[]} to stdout; exit 0 on PASS, 1 on FAIL.
"""
import hashlib
import ipaddress
import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

SITE = "carvana"
DEFAULT_CONTAINER = "wh-carvana-review"

# ---------------------------------------------------------------- frozen seed contract
TABLES = ("users", "vehicles", "vehicle_reviews", "search_snapshots",
          "help_articles", "profiles", "favorites", "orders",
          "trade_in_offers", "order_events")
SEED_COUNTS = {"users": 4, "vehicles": 1544, "vehicle_reviews": 722,
               "search_snapshots": 97, "help_articles": 16, "profiles": 4,
               "favorites": 8, "orders": 3, "trade_in_offers": 1,
               "order_events": 10}
# sha256 over sqlite_master (type, name, tbl_name, sql) of the frozen seed.
SCHEMA_SHA256 = "3ea5009b15d8cb379c5e4d99aef471eaae9db4b453c10b90d72e15e37256426a"
# sha256 over every seed row (table-canonical, ORDER BY all columns).
SEED_ROWS_SHA256 = "de3c45e60f9ef95622f123edf8ff6386c290d4a3c9fd22dbcc3a4d1bbbdb0bcf"
NUM_TOKEN_RX = r"[0-9,.\-]+"


# ---------------------------------------------------------------- trajectory
def load_run(run_dir):
    d = Path(run_dir)
    traj = json.loads((d / "trajectory.json").read_text(encoding="utf-8"))
    if not isinstance(traj, dict):
        raise ValueError("trajectory.json must contain a JSON object")
    traj["_run_dir"] = d
    shots_dir = d / "screenshots"
    traj["_shots"] = {p.name: p for p in sorted(shots_dir.glob("step_*.png"))} \
        if shots_dir.is_dir() else {}
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


def _png_ok(path: Path) -> bool:
    try:
        data = path.read_bytes()[:8]
    except OSError:
        return False
    return data == b"\x89PNG\r\n\x1a\n"


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
    rx = re.compile(pattern, re.IGNORECASE)
    hit = [u for u in trajectory_urls(traj) if rx.search(u)]
    if not hit:
        judge.fail(check, f"no visited URL matches {pattern!r}")
    else:
        judge.ok(check, hit[0])


def check_visited_any(judge, traj, check, patterns):
    for pattern in patterns:
        rx = re.compile(pattern, re.IGNORECASE)
        if any(rx.search(u) for u in trajectory_urls(traj)):
            judge.ok(check, pattern)
            return
    judge.fail(check, f"no visited URL matches any of {patterns!r}")


def check_visited_all(judge, traj, check, patterns):
    urls = trajectory_urls(traj)
    missing = []
    for pattern in patterns:
        rx = re.compile(pattern, re.IGNORECASE)
        if not any(rx.search(u) for u in urls):
            missing.append(pattern)
    if missing:
        judge.fail(check, f"no visited URL matches {missing}")
    else:
        judge.ok(check, f"{len(patterns)} required surfaces opened")


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


def _num_token(t):
    return t.replace(",", "").rstrip(".").lstrip("$").replace("-", "")


def check_answer_number(judge, answer, check, number):
    want = str(number)
    tokens = re.findall(NUM_TOKEN_RX, answer)
    if any(_num_token(t) == want for t in tokens):
        judge.ok(check, want)
    else:
        judge.fail(check, f"number {want} not in answer tokens")


def check_answer_number_absent(judge, answer, check, number):
    want = str(number)
    tokens = re.findall(NUM_TOKEN_RX, answer)
    if any(_num_token(t) == want for t in tokens):
        judge.fail(check, f"number {want} must not be a token in the answer")
    else:
        judge.ok(check, f"{want} absent as a token")


def check_answer_money(judge, answer, check, amount):
    """Accept $X / $X.00 / X,comma-grouped forms; reject longer numbers
    that merely CONTAIN the digits (e.g. 22,990 inside 22,990,000)."""
    want = float(amount)
    pat = rf"(?:\$)?{want:.2f}".replace(".", r"\.")
    pat2 = rf"(?:\$)?{int(want)}(?![\d.]|,\d)(?:\.0*)?"
    pat3 = rf"(?:\$)?{re.escape(f'{int(want):,}')}(?![\d]|,\d)"
    if re.search(pat, answer) or re.search(pat2, answer) or re.search(pat3, answer):
        judge.ok(check, f"${want:.2f}")
    else:
        judge.fail(check, f"amount ${want:.2f} not in answer")


def check_answer_count_at_least(judge, answer, check, options, minimum):
    found = sum(1 for o in options if _norm(o) in _norm(answer))
    if found >= minimum:
        judge.ok(check, f"{found}/{len(options)} item(s)")
    else:
        judge.fail(check, f"only {found}/{minimum} of {options!r} in answer")


def check_answer_sequence(judge, answer, check, tokens):
    """Each token must appear AFTER the previous token's match (sequential
    scan) — robust to words that also occur earlier in the answer."""
    low = _norm(answer)
    pos = 0
    for tok in tokens:
        p = low.find(_norm(tok), pos)
        if p < 0:
            judge.fail(check, f"sequence token {tok!r} not found in order")
            return
        pos = p + len(_norm(tok))
    judge.ok(check, f"{len(tokens)} tokens found in sequence")


def check_answer_absent(judge, answer, check, phrase):
    if _norm(phrase) in _norm(answer):
        judge.fail(check, f"answer must not contain {phrase!r}")
    else:
        judge.ok(check, f"absent: {phrase!r}")


def check_answer_regex(judge, answer, check, pattern):
    if re.search(pattern, answer, re.IGNORECASE):
        judge.ok(check, f"matches {pattern!r}")
    else:
        judge.fail(check, f"answer does not match {pattern!r}")


def check_answer_ordered(judge, answer, check, tokens):
    low = _norm(answer)
    positions = []
    for tok in tokens:
        pos = low.find(_norm(tok))
        if pos < 0:
            judge.fail(check, f"missing ordered token {tok!r}")
            return
        positions.append(pos)
    if positions == sorted(positions):
        judge.ok(check, f"{len(tokens)} tokens in order")
    else:
        judge.fail(check, f"tokens out of order: {tokens!r}")


# ---------------------------------------------------------------- DB after-state
def _connect(path):
    p = Path(path)
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
    if len(row) != len(template):
        return False
    for got, want in zip(row, template):
        if want is None:
            continue
        if isinstance(want, (set, frozenset)):
            if got not in want:
                return False
        elif isinstance(want, str) and want.startswith("rx:"):
            if not re.search(want[3:], str(got)):
                return False
        elif got != want:
            return False
    return True


def check_rows_added(judge, initial_db, after_db, table, templates, check):
    added, _, _ = _diff(initial_db, after_db, table)
    if len(added) != len(templates):
        judge.fail(check, f"expected {len(templates)} added row(s) in {table}, "
                          f"got {len(added)}: {added}")
        return
    for tpl in templates:
        if not any(_match(row, tpl) for row in added):
            judge.fail(check, f"no added row in {table} matches {tpl}")
            return
    judge.ok(check, f"{len(templates)} row(s) added to {table}")


def check_rows_removed(judge, initial_db, after_db, table, templates, check):
    _, removed, _ = _diff(initial_db, after_db, table)
    if len(removed) != len(templates):
        judge.fail(check, f"expected {len(templates)} removed row(s) in {table}, "
                          f"got {len(removed)}")
        return
    for tpl in templates:
        if not any(_match(row, tpl) for row in removed):
            judge.fail(check, f"no removed row in {table} matches {tpl}")
            return
    judge.ok(check, f"{len(templates)} row(s) removed from {table}")


def check_rows_changed(judge, initial_db, after_db, table, templates, check):
    _, _, changed = _diff(initial_db, after_db, table)
    if len(changed) != len(templates):
        judge.fail(check, f"expected {len(templates)} changed row(s) in {table}, "
                          f"got {len(changed)}")
        return
    for tpl in templates:
        if not any(_match(new, tpl) for _, new in changed):
            judge.fail(check, f"no changed row in {table} matches {tpl}")
            return
    judge.ok(check, f"{len(templates)} row(s) changed in {table}")


# ---------------------------------------------------------------- seed contract
def check_seed_contract(judge, seed_db):
    counts = {t: seed_db.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
              for t in TABLES}
    if counts != SEED_COUNTS:
        judge.fail("seed_counts", f"counts differ: {counts}")
    else:
        judge.ok("seed_counts", f"{sum(counts.values())} rows across {len(TABLES)} tables")
    schema_rows = list(seed_db.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"))
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
    parser.add_argument("--container", default=DEFAULT_CONTAINER)
    parser.add_argument("--no_llm", nargs="?", const=True, default=False,
                        type=lambda v: str(v).casefold() in {"1", "true", "yes", "on"})
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    traj = load_run(run_dir)
    initial = _connect(args.initial_db or run_dir / "initial.db")
    after = _connect(args.after_db or run_dir / "after.db")

    judge = Judge(task_id)
    try:
        run_checks(judge, traj, initial, after)
    finally:
        initial.close()
        after.close()
    verdict = {"task_id": task_id, "pass": not judge.failures,
               "reason": "all checks passed" if not judge.failures
                         else "; ".join(judge.failures[:6]),
               "evidence": judge.evidence}
    print(json.dumps(verdict, indent=1))
    return 0 if not judge.failures else 1
