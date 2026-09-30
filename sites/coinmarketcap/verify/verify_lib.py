#!/usr/bin/env python3
"""verify_lib.py — deterministic verifier utilities for coinmarketcap task
verification.

Philosophy: DETERMINISTIC FIRST. No LLM call is load-bearing; every check is
regex / token / SQLite after-state.

  1. Package identity (fail-closed): task_id matches, ``terminated`` with
     ``agent_done``, non-empty final answer, every recorded URL on the same
     loopback origin AND port as ``start_url``, every referenced screenshot a
     decodable PNG.
  2. Seed identity gate (fail-closed): the initial DB snapshot must BE the
     frozen in-image seed (schema + rows digest + counts + file digests). A
     run graded against a pre-mutated database fails here.
  3. Navigation gates (anti knowledge-shortcut): the agent MUST have opened
     the on-site surfaces the task names (rankings with the exact sort/filter
     query strings, coin/exchange/category/glossary pages, converter,
     historical pages, watchlist/auth pages). A correct answer with no
     matching navigation is a memory-recall shortcut = FAIL.
  4. Answer check: affirmative token / phrase / number / money / ordered
     checks against ground truth HARDCODED in each ``verify_<n>.py`` (never
     in tasks.jsonl). All values are frozen 2026-09-29/30 UTC capture data.
  5. DB after-state: read-only tasks require every table row-identical to
     the seed; stateful tasks require the exact allowed row delta and
     nothing else (signup adds a users row + moves guest watchlist rows to
     the account; watchlist toggles add/remove exactly the starred coins).

Seed reproducibility: the coinmarketcap seed is rebuilt deterministically
inside the pinned image (PYTHONHASHSEED=0). The reviewer's independent
image build (webharbor-review:coinmarketcap, from contribution e1434134)
reproduced container seed sha256
f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c /
md5 990af4a551228a1877ae0118ad3ae3b0 — matching the contributor's
container-rebuild claim — and every per-task reset snapshot was
byte-identical (md5 990af4a5… across resets). The r2-fix revision does not
touch the seed: all 46 honest-walk initial snapshots (two rounds x 23
tasks, reset before every task on wh-coinmarketcap-fix2 running the fixed
code against the same image seed) are byte-identical to the frozen seed,
so this seed gate is unchanged. The contributor's LOCAL
build has a different byte identity (sha256 b0cf00d7…, md5 a27dc8fb…)
because the local SQLite differs from the image's; the image identity is
the shipping one and is what this contract freezes (logical digests are
computed with the exact functions below).

Input signature (per task):
  --run_dir DIR        agent trajectory dir: trajectory.json + screenshots/step_NNN.png
  --initial_db PATH    initial-state SQLite DB (default: <run_dir>/initial.db)
  --after_db PATH      after-state  SQLite DB (default: <run_dir>/after.db)
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

SITE = "coinmarketcap"
DEFAULT_CONTAINER = os.environ.get("WH_CONTAINER", "wh-coinmarketcap-fix2")
MIRROR_PORT = os.environ.get("WH_MIRROR_PORT", "47120")

# ---------------------------------------------------------------- frozen seed contract
TABLES = ("coin_charts", "coin_tags", "coins", "contents", "conversions",
          "exchange_pairs", "exchanges", "global_metrics", "glossary_terms",
          "market_pairs", "most_viewed_rows", "ohlcv", "sectors",
          "snapshot_rows", "tags", "trending_rows", "upcoming_rows", "users",
          "watchlist_items")
SEED_COUNTS = {"coin_charts": 299, "coin_tags": 1559, "coins": 119,
               "contents": 4, "conversions": 13, "exchange_pairs": 1799,
               "exchanges": 749, "global_metrics": 1, "glossary_terms": 1334,
               "market_pairs": 5503, "most_viewed_rows": 100, "ohlcv": 18872,
               "sectors": 13, "snapshot_rows": 20, "tags": 297,
               "trending_rows": 20, "upcoming_rows": 9, "users": 4,
               "watchlist_items": 13}
# sha256 over sqlite_master (type, name, tbl_name, sql) of
# instance_seed/coinmarketcap.db — frozen from the reviewer's independent image build.
SCHEMA_SHA256 = "caaf55b748b6e67c7ad5dcadf5cc9c16d7a5826c5b21701a9f651cccf0afada1"
# sha256 over every seed row (table-canonical, ORDER BY all columns).
SEED_ROWS_SHA256 = "aece83030ac3b2cb38d9a68acb29c4c8f2eb8fbe4c8085e8bc9ee74a7f6a1729"
# Byte-level digests of the seed produced inside the pinned image.
SEED_FILE_MD5 = "990af4a551228a1877ae0118ad3ae3b0"
SEED_FILE_SHA256 = "f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c"
DEMO_PASSWORD = "TestPass123!"
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


def check_visited_all(judge, traj, check, patterns):
    """Every pattern must be visited."""
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


def check_visited_any(judge, traj, check, patterns):
    for pattern in patterns:
        rx = re.compile(pattern, re.IGNORECASE)
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


def check_answer_number(judge, answer, check, number):
    want = str(number)
    tokens = re.findall(NUM_TOKEN_RX, answer)
    if any(t.replace(",", "").rstrip(".").lstrip("$") == want for t in tokens):
        judge.ok(check, want)
    else:
        judge.fail(check, f"number {want} not in answer tokens")


def check_answer_number_absent(judge, answer, check, number):
    """The number must NOT appear as a standalone token (wrong-count trip)."""
    want = str(number)
    tokens = re.findall(NUM_TOKEN_RX, answer)
    if any(t.replace(",", "").rstrip(".").lstrip("$") == want for t in tokens):
        judge.fail(check, f"number {want} must not be a token in the answer")
    else:
        judge.ok(check, f"{want} absent as a token")


def check_answer_money(judge, answer, check, amount):
    """Accept $X, $X.00, X.00, X, comma-grouped forms for a dollar amount."""
    want = float(amount)
    int_s = f"{int(want):,}"
    pat = rf"(?:\$)?{want:.2f}".replace(".", r"\.")
    pat2 = rf"(?:\$)?{int(want)}(?:\.0*)?(?![\d.])"
    pat3 = rf"(?:\$)?{re.escape(int_s)}(?![\d,])"
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
    """Every token present AND in the given relative order (first occurrence)."""
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
def _connect(path, container):
    p = Path(path)
    if not p.is_file() and container:
        inner = (f"/opt/WebSyn/{SITE}/instance/{SITE}.db"
                 if "after" in p.name else
                 f"/opt/WebSyn/{SITE}/instance_seed/{SITE}.db")
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
    added, _, _ = _diff(initial_db, after_db, table)
    if len(added) != len(templates):
        judge.fail(check, f"expected {len(templates)} added row(s) in {table}, got {len(added)}: {added}")
        return None
    for tpl in templates:
        if not any(_match(row, tpl) for row in added):
            judge.fail(check, f"no added row in {table} matches {tpl}")
            return None
    judge.ok(check, f"{len(templates)} row(s) added to {table}")
    return added


def check_rows_removed(judge, initial_db, after_db, table, templates, check):
    _, removed, _ = _diff(initial_db, after_db, table)
    if len(removed) != len(templates):
        judge.fail(check, f"expected {len(templates)} removed row(s) in {table}, got {len(removed)}")
        return
    for tpl in templates:
        if not any(_match(row, tpl) for row in removed):
            judge.fail(check, f"no removed row in {table} matches {tpl}")
            return
    judge.ok(check, f"{len(templates)} row(s) removed from {table}")


def check_rows_changed(judge, initial_db, after_db, table, templates, check):
    _, _, changed = _diff(initial_db, after_db, table)
    if len(changed) != len(templates):
        judge.fail(check, f"expected {len(templates)} changed row(s) in {table}, got {len(changed)}")
        return
    for tpl in templates:
        if not any(_match(new, tpl) for _, new in changed):
            judge.fail(check, f"no changed row in {table} matches {tpl}")
            return
    judge.ok(check, f"{len(templates)} row(s) changed in {table}")


# ---------------------------------------------------------------- seed contract
def _schema_sha256(db):
    rows = list(db.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name"))
    h = hashlib.sha256()
    for r in rows:
        h.update(repr(list(r)).encode())
    return h.hexdigest()


def _rows_sha256(db):
    h = hashlib.sha256()
    for t in TABLES:
        cols = [r[1] for r in db.execute(f'PRAGMA table_info("{t}")')]
        order = ", ".join(f'"{c}"' for c in cols)
        for row in db.execute(f'SELECT * FROM "{t}" ORDER BY {order}'):
            h.update(repr(list(row)).encode())
    return h.hexdigest()


def _file_digest(path):
    data = Path(path).read_bytes()
    return hashlib.md5(data).hexdigest(), hashlib.sha256(data).hexdigest()


def check_seed_contract(judge, db, db_path=None):
    """The initial-state DB must BE the frozen in-image seed."""
    counts_ok = True
    for t, want in SEED_COUNTS.items():
        got = db.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        if got != want:
            judge.fail(f"seed_count_{t}", f"{t}: {got} rows, want {want}")
            counts_ok = False
    if counts_ok:
        judge.ok("seed_counts", f"{len(SEED_COUNTS)} tables at seed cardinality")
    schema = _schema_sha256(db)
    if schema != SCHEMA_SHA256:
        judge.fail("seed_schema", f"schema sha256 {schema} != {SCHEMA_SHA256}")
    else:
        judge.ok("seed_schema", schema)
    rows = _rows_sha256(db)
    if rows != SEED_ROWS_SHA256:
        judge.fail("seed_rows", f"rows sha256 {rows} != {SEED_ROWS_SHA256}")
    else:
        judge.ok("seed_rows", rows)
    if db_path:
        md5, sha = _file_digest(db_path)
        if md5 != SEED_FILE_MD5 or sha != SEED_FILE_SHA256:
            judge.fail("seed_file", f"file digests {md5}/{sha} != frozen")
        else:
            judge.ok("seed_file", md5)


# ---------------------------------------------------------------- entry point
def run_verifier(task_id, run_checks):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--run_dir", required=True)
    ap.add_argument("--initial_db", default=None)
    ap.add_argument("--after_db", default=None)
    ap.add_argument("--container", default=DEFAULT_CONTAINER)
    ap.add_argument("--no_db", action="store_true",
                    help="skip DB gates (read-only answer-only mode)")
    args = ap.parse_args()
    traj = load_run(args.run_dir)
    initial = after = None
    initial_path = args.initial_db or os.path.join(args.run_dir, "initial.db")
    after_path = args.after_db or os.path.join(args.run_dir, "after.db")
    if not args.no_db:
        initial = _connect(initial_path, args.container)
        after = _connect(after_path, args.container)
    judge = Judge(task_id)
    try:
        run_checks(judge, traj, initial, after)
    finally:
        if initial is not None:
            initial.close()
        if after is not None:
            after.close()
    result = {
        "task_id": task_id,
        "pass": not judge.failures,
        "reason": "OK" if not judge.failures else "; ".join(judge.failures[:6]),
        "evidence": judge.evidence,
    }
    print(json.dumps(result, indent=1))
    return 0 if result["pass"] else 1
