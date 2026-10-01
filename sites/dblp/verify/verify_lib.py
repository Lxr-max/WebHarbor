#!/usr/bin/env python3
"""verify_lib.py — deterministic verifier utilities for the dblp task suite.

Philosophy: DETERMINISTIC FIRST. No LLM call is load-bearing; every check is
regex / token / SQLite after-state.

  1. Package identity (fail-closed): task_id matches, ``terminated`` with
     ``agent_done``, non-empty final answer, every recorded URL on the same
     loopback origin AND port as ``start_url``, every referenced screenshot a
     decodable PNG.
  2. Seed identity gate (fail-closed): the initial DB snapshot must BE the
     frozen in-image seed (schema + rows digest + counts). A run graded
     against a pre-mutated database fails here.
  3. Navigation gates (anti knowledge-shortcut): the agent must have opened
     the on-site surfaces the task names (search pages, venue / edition /
     record / author pages, account pages). A correct answer with no matching
     navigation is a memory-recall shortcut = FAIL.
  4. Answer check: phrase / number / ordered token matching against ground
     truth HARDCODED in each ``verify_<n>.py`` (never in tasks.jsonl).
  5. DB after-state: read-only tasks require every table row-identical to the
     seed; stateful tasks require the exact allowed row delta and nothing else.

Seed reproducibility: the dblp seed is rebuilt deterministically inside the
pinned image (PYTHONHASHSEED=0, tracked source_data snapshots). The review
image (webharbor:dblp-review, built from orch/review/dblp @ 8cdd14e1)
reproduces the seed byte-identically to the contributor's dev build; the
contract freezes the digests below.

Input signature (per task):
  --run_dir DIR        trajectory dir: trajectory.json + screenshots/step_*.png
  --initial_db PATH    initial-state SQLite DB (default: <run_dir>/initial.db)
  --after_db PATH      after-state  SQLite DB (default: <run_dir>/after.db)
Output: JSON {task_id, pass, reason, evidence[]} to stdout; exit 0 on PASS.
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

SITE = "dblp"
DEFAULT_CONTAINER = os.environ.get("WH_CONTAINER", "wh-dblp-review")
MIRROR_PORT = os.environ.get("WH_MIRROR_PORT", "49121")

# ------------------------------------------------------- frozen seed contract
TABLES = ("users", "venues", "editions", "publications", "pub_authors",
          "authors", "watch_authors", "watch_venues", "saved_searches",
          "saved_papers", "search_history")
# frozen from the review image build (webharbor:dblp-review, built from
# orch/review/dblp @ 8cdd14e1; seed md5 e42b5b2926de4c0ea989be80fce3ac04,
# byte-identical to the contributor's dev build)
SEED_COUNTS = {"users": 4, "venues": 21, "editions": 70,
               "publications": 36585, "pub_authors": 204300,
               "authors": 97090, "watch_authors": 9, "watch_venues": 9,
               "saved_searches": 6, "saved_papers": 20,
               "search_history": 13}
SCHEMA_SHA256 = "55098b4ab55aeeb343c7f070c8c0ce84af55ee775cfab4c0946faedcc156e013"
SEED_ROWS_SHA256 = "818234a56201e8a58ddbf5a8b50f9e62510a865502173d9e32abcdef6f24839a"
SEED_FILE_MD5 = "e42b5b2926de4c0ea989be80fce3ac04"
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


def check_step_action(judge, traj, check, action):
    """At least one recorded step must have the given action (e.g. download)."""
    hits = [s for s in traj.get("steps", []) if s.get("action") == action]
    if not hits:
        judge.fail(check, f"no step with action {action!r}")
    else:
        judge.ok(check, f"{len(hits)} {action} step(s)")


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


def check_answer_number_near(judge, answer, check, number, context,
                               window=90):
    """The number must appear within `window` chars after the context phrase
    (or be the only occurrence of the token in the answer) — catches swapped
    count assignments between similar keys."""
    want = str(number)
    low = _norm(answer)
    ctx = _norm(context)
    hits = 0
    start = 0
    near = False
    tokens_at = []
    for m in re.finditer(NUM_TOKEN_RX, answer):
        if m.group(0).replace(",", "").rstrip(".").lstrip("$") == want:
            hits += 1
            tokens_at.append(m.start())
    pos = low.find(ctx)
    if pos >= 0 and tokens_at:
        for t in tokens_at:
            if abs(t - pos) <= window + len(ctx):
                near = True
    if near or hits == 1:
        judge.ok(check, f"{want} near {context!r}" if near else f"{want} sole")
    else:
        judge.fail(check, f"number {want} not near {context!r} "
                          f"({hits} occurrences)")


def check_answer_number_absent(judge, answer, check, number):
    want = str(number)
    tokens = re.findall(NUM_TOKEN_RX, answer)
    if any(t.replace(",", "").rstrip(".").lstrip("$") == want for t in tokens):
        judge.fail(check, f"number {want} must not be a token in the answer")
    else:
        judge.ok(check, f"{want} absent as a token")


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
    return {row[0]: list(row)
            for row in db.execute(f'SELECT * FROM "{table}" ORDER BY {order}')}


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
        if isinstance(want, str) and want.startswith("rx:"):
            if not re.search(want[3:], str(got)):
                return False
        elif isinstance(want, (set, frozenset, list)):
            if got not in want:
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
    digest = hashlib.sha256(
        json.dumps(schema_rows, default=str).encode()).hexdigest()
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
    rdigest = hashlib.sha256(
        json.dumps(rows_src, default=str).encode()).hexdigest()
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
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    traj = load_run(run_dir)
    initial = _connect(args.initial_db or run_dir / "initial.db", args.container)
    after = _connect(args.after_db or run_dir / "after.db", args.container)

    judge = Judge(task_id)
    try:
        run_checks(judge, traj, initial, after)
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
