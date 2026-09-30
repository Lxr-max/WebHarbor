#!/usr/bin/env python3
"""verify_lib.py — deterministic verifier utilities for disney task
verification (reviewer track).

Philosophy: DETERMINISTIC FIRST. No LLM call is load-bearing; every check is
regex / token / phrase / SQLite after-state.

  1. Package identity (fail-closed): task_id matches, ``terminated`` with
     ``agent_done``, non-empty final answer, every recorded URL on the same
     loopback origin AND port as ``start_url``, every referenced screenshot
     a decodable PNG.
  2. Seed identity gate (fail-closed): the initial DB snapshot must BE the
     frozen in-image seed (schema + rows digest + counts + file md5/sha256).
     A run graded against a pre-mutated database fails here.
  3. Navigation gates (anti knowledge-shortcut): the agent MUST have opened
     the on-site surfaces the task names (catalog pages with the exact
     filter query strings, detail pages, the schedule, the booking form, the
     account area). A correct answer with no matching navigation is a
     memory-recall shortcut = FAIL.
  4. Answer check: affirmative token / phrase / number matching against
     ground truth HARDCODED in each ``verify_<n>.py`` (never in
     tasks.jsonl).
  5. DB after-state: read-only tasks require every table row-identical to
     the seed; stateful tasks require exactly the allowed row delta and
     nothing else.

Seed reproducibility: the disney seed is rebuilt deterministically inside
the pinned image (PYTHONHASHSEED=0, Dockerfile disney block: asset
inventory gate 1247/1247 + in-image seed build). The r2 reviewer's
independent image build (webharbor-disney-r2:dev, from the fixed
contribution 038c6d43 with the committed 116-archive manifest) reproduces
seed sha256 344b6c2a… byte-identically across the fresh boot, two in-image
rebuilds, and per-task resets; /reset/disney restores instance ==
instance_seed byte-identically (md5 9f231a5a…).

r2 re-freeze — the r1 known mirror defects are FIXED on the site and the
contract now pins the fixed truths (all re-derived from the r2 reviewer's
own Playwright walks on wh-disney-r2-review):
  - attraction favorites post the full park/slug key and /favorites
    renders every favorited card; T7/T9/T19 pin count == rendered cards
    and the DB rows now carry the full key;
  - the site-wide search lists full result sets, so the printed section
    counts are true match counts (T4 pins Parks & Entertainment 13;
    T13 pins Shop 25);
  - sale items still render no original price (upstream has none), but
    T11 no longer asks for it;
  - the first plush search hit still has no reviews row, but T13 no
    longer asks for it;
  - game titles are clean hub names and game descriptions render real
    upstream rich text — T17 pins the on-page strings;
  - two shows share the title "DuckTales" (1987 / 2017), but T3 now says
    "the newer DuckTales series" — pinned to the 2017 reboot (TV-Y7);
  - two EPCOT fireworks exist, but T7 now names "the Heartbeat of
    Freedom fireworks show at EPCOT" — pinned to that one.

Input signature (per task):
  --run_dir DIR        agent trajectory dir: trajectory.json + screenshots/step_NNN.png
  --initial_db PATH    initial-state SQLite DB (default: <run_dir>/initial.db)
  --after_db PATH      after-state  SQLite DB (default: <run_dir>/after.db)
  --container NAME     container to fetch the seed/live DB from when the
                       snapshots are absent (default wh-disney-r2-review)
Output: JSON {task_id, pass, reason, evidence[]} on stdout; exit 0 on PASS,
1 on FAIL.
"""
import hashlib
import ipaddress
import json
import os
import re
import sqlite3
import struct
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlparse

SITE = "disney"
DEFAULT_CONTAINER = os.environ.get("WH_CONTAINER", "wh-disney-r2-review")
MIRROR_PORT = os.environ.get("WH_MIRROR_PORT", "50122")
BENCHMARK_PASSWORD = "TestPass123!"

# ------------------------------------------------------------- frozen seed contract
TABLES = ("cart_items", "favorites", "games", "home_tiles", "ice_events",
          "live_shows", "movies", "park_entities", "products", "shop_orders",
          "shows", "ticket_orders", "users")
SEED_COUNTS = {"cart_items": 0, "favorites": 11, "games": 4,
               "home_tiles": 23, "ice_events": 89, "live_shows": 4,
               "movies": 40, "park_entities": 267, "products": 150,
               "shop_orders": 1, "shows": 54, "ticket_orders": 1, "users": 4}
# sha256 over sqlite_master (type, name, tbl_name, sql) — frozen from the
# r2 reviewer's independent image build (webharbor-disney-r2:dev, from the
# fixed contribution 038c6d43; games table schema paragraphs→sections).
SCHEMA_SHA256 = "f8bb11a8490e11fbbe281da157652a628d3fe228deb0faa967e9d1ddcbe379dd"
# sha256 over every seed row (table-canonical, ORDER BY all columns).
ROWS_SHA256 = "8571db9da5c7224bb35d95808c77b1bfdf9ede145f503723584c90a4b4cdf076"
# Byte-level digests of the seed produced inside the pinned image.
SEED_FILE_MD5 = "9f231a5add117650cf1e8edb07b89fa3"
SEED_FILE_SHA256 = ("344b6c2ae7fa80f7c5bb929e4391a03f2e0ef9f3"
                    "1ac92a61feca50514c0a118d")

MIRROR_DATE_ISO = "2026-09-29"
NUM_TOKEN_RX = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"


# ------------------------------------------------------------------ trajectory
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
        if step.get("action") == "goto" and step.get("locator", "").startswith("http"):
            urls.append(str(step["locator"]))
    return urls


def final_answer(traj):
    answer = traj.get("final_answer")
    return "" if answer is None else str(answer)


def _png_ok(path: Path) -> bool:
    """Full structural gate: magic + IHDR + decoded dimensions + IEND tail.

    A truncated PNG (magic kept, payload cut) or a magic-only stub fails;
    a real Playwright screenshot passes. (Audit hardening: the r2 gate
    read only the 8-byte magic, so truncated evidence passed.)
    """
    try:
        data = path.read_bytes()
    except OSError:
        return False
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return False
    if data[12:16] != b"IHDR":
        return False
    width, height = struct.unpack(">II", data[16:24])
    if not (0 < width <= 100000 and 0 < height <= 100000):
        return False
    return b"IEND" in data[-32:]


# ---------------------------------------------------------------------- judge
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
        judge.ok("task_id", f"{task_id}")
    if not (traj.get("terminated") and traj.get("agent_done")):
        judge.fail("termination", f"terminated={traj.get('terminated')!r} agent_done={traj.get('agent_done')!r}")
    else:
        judge.ok("termination", "terminated with agent_done")
    answer = final_answer(traj)
    if not answer.strip():
        judge.fail("answer_nonempty", "final_answer is empty")
    else:
        judge.ok("answer_nonempty", f"{len(answer)} chars")
    start = urlparse(str(traj.get("start_url", "")))
    if not _is_loopback(start.hostname):
        judge.fail("start_origin", f"start_url host {start.hostname!r} is not loopback")
    else:
        judge.ok("start_origin", f"{start.hostname}:{start.port}")
    for u in trajectory_urls(traj):
        p = urlparse(u)
        if not _is_loopback(p.hostname) or p.port != start.port:
            judge.fail("url_origin", f"{u!r} is off the start origin/port")
            return
    judge.ok("url_origin", f"all {len(trajectory_urls(traj))} recorded URLs on {start.hostname}:{start.port}")


def check_screenshots(judge, traj, min_shots=1):
    shots = traj.get("_shots", {})
    if len(shots) < min_shots:
        judge.fail("screenshots", f"expected >= {min_shots} step screenshots, got {len(shots)}")
        return
    bad = [name for name, path in shots.items() if not _png_ok(path)]
    if bad:
        judge.fail("screenshots", f"non-PNG screenshots: {bad[:3]}")
    else:
        judge.ok("screenshots", f"{len(shots)} decodable PNGs")


# ------------------------------------------------------------------ seed gate
def _db_rows(db_path):
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        counts, rows = {}, []
        for t in tables:
            cols = [r[1] for r in con.execute(f'PRAGMA table_info("{t}")')]
            counts[t] = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            rows.append([t, [list(r) for r in con.execute(
                f'SELECT * FROM "{t}" ORDER BY ' + ",".join(f'"{c}"' for c in cols))]])
        schema = con.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY name").fetchall()
        return tables, counts, rows, schema
    finally:
        con.close()


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, default=str).encode()).hexdigest()


def _resolve_db(judge, explicit, run_dir, name):
    if explicit:
        return Path(explicit)
    cand = Path(run_dir) / name
    if cand.is_file():
        return cand
    # fetch from the review container
    out = Path(run_dir) / f"_fetched_{name}"
    src = f"{DEFAULT_CONTAINER}:/opt/WebSyn/disney/{'instance_seed' if name == 'initial.db' else 'instance'}/disney.db"
    proc = subprocess.run(["docker", "cp", src, str(out)], capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        judge.fail("db_access", f"cannot obtain {name}: {proc.stderr[:120]}")
        return None
    return out


def check_seed_contract(judge, initial_db):
    if initial_db is None:
        judge.fail("seed_contract", "no initial DB available")
        return
    path = str(initial_db)
    data = Path(path).read_bytes()
    md5 = hashlib.md5(data).hexdigest()
    if md5 != SEED_FILE_MD5:
        judge.fail("seed_contract", f"initial DB md5 {md5} != frozen seed {SEED_FILE_MD5}")
        return
    tables, counts, rows, schema = _db_rows(path)
    if sorted(tables) != sorted(TABLES):
        judge.fail("seed_contract", f"table set mismatch: {sorted(tables)}")
        return
    bad_counts = {t: (counts[t], SEED_COUNTS[t]) for t in TABLES if counts[t] != SEED_COUNTS[t]}
    if bad_counts:
        judge.fail("seed_contract", f"row-count mismatch: {bad_counts}")
        return
    if _sha(schema) != SCHEMA_SHA256 or _sha(rows) != ROWS_SHA256:
        judge.fail("seed_contract", "schema/rows digest mismatch vs frozen seed")
        return
    judge.ok("seed_contract", f"seed md5 {md5} + schema/rows digests match")


# ---------------------------------------------------------------- navigation
def _norm(url):
    return unquote(str(url))


def check_visited_path(judge, traj, name, pattern):
    for u in trajectory_urls(traj):
        if re.search(pattern, _norm(u)):
            judge.ok(f"nav_{name}", _norm(u)[:120])
            return
    judge.fail(f"nav_{name}", f"no visited URL matches {pattern!r}")


def check_visited_all(judge, traj, gates):
    for name, pattern in gates:
        check_visited_path(judge, traj, name, pattern)


def check_visited_any(judge, traj, name, patterns):
    for pattern in patterns:
        for u in trajectory_urls(traj):
            if re.search(pattern, _norm(u)):
                judge.ok(f"nav_{name}", _norm(u)[:120])
                return
    judge.fail(f"nav_{name}", f"no visited URL matches any of {patterns!r}")


# -------------------------------------------------------------------- answers
MONEY_RX = re.compile(r"(?<![\d.,])\$?\d{1,3}(?:,\d{3})*\.\d{2}(?!\d)")


def check_answer_money(judge, answer, name, value):
    """Money gate with token boundaries: a value passes only when a whole
    money token equal to it appears ("$70.00" yes; "170.00", "70.0",
    "70.001", "1227.99" no). Numeric-equivalent honest forms ($-prefixed,
    comma thousands, trailing sentence punctuation) all pass."""
    want = float(value)
    for tok in MONEY_RX.findall(answer.replace("\n", " ")):
        try:
            if float(tok.replace("$", "").replace(",", "")) == want:
                judge.ok(f"ans_{name}", f"{value:.2f} as an exact money token")
                return
        except ValueError:
            continue
    judge.fail(f"ans_{name}",
               f"money value {value:.2f} not present as an exact money token")


def _num_tokens(answer):
    return re.findall(NUM_TOKEN_RX, answer)


def _fold(s):
    """Normalize typographic variants so a verbatim page quote (curly
    quotes, en/em dashes, nbsp) matches the contract's ASCII anchor and
    vice versa (audit hardening: r2 pinned "It's" while the page renders
    "It’s", failing honest answers)."""
    return (s.replace("‘", "'").replace("’", "'")
             .replace("“", '"').replace("”", '"')
             .replace("–", "-").replace("—", "-")
             .replace(" ", " "))


def check_answer_phrase(judge, answer, name, phrase, case_sensitive=False):
    hay, needle = _fold(answer), _fold(phrase)
    if not case_sensitive:
        hay, needle = hay.lower(), needle.lower()
    if needle in hay:
        judge.ok(f"ans_{name}", f"contains {phrase!r}")
    else:
        judge.fail(f"ans_{name}", f"missing phrase {phrase!r}")


def check_answer_any(judge, answer, name, phrases):
    for ph in phrases:
        if _fold(ph).lower() in _fold(answer).lower():
            judge.ok(f"ans_{name}", f"contains {ph!r}")
            return
    judge.fail(f"ans_{name}", f"none of {phrases!r} present")


def check_answer_regex(judge, answer, name, pattern):
    if re.search(pattern, answer, re.I):
        judge.ok(f"ans_{name}", f"matches {pattern!r}")
    else:
        judge.fail(f"ans_{name}", f"no match for {pattern!r}")


def check_answer_number(judge, answer, name, value):
    want = f"{value:,}" if isinstance(value, int) else str(value)
    if want in _num_tokens(answer) or str(value) in _num_tokens(answer):
        judge.ok(f"ans_{name}", f"{value}")
    else:
        judge.fail(f"ans_{name}", f"number {value} not found in answer tokens")


def check_answer_number_absent(judge, answer, name, value):
    for tok in _num_tokens(answer):
        if tok.replace(",", "") == str(value):
            judge.fail(f"ans_{name}", f"forbidden number {value} appears in the answer")
            return
    judge.ok(f"ans_{name}", f"{value} absent")


def check_answer_count_at_least(judge, answer, name, items, minimum):
    present = sum(1 for it in items if it.lower() in answer.lower())
    if present >= minimum:
        judge.ok(f"ans_{name}", f"{present}/{len(items)} tokens >= {minimum}")
    else:
        judge.fail(f"ans_{name}", f"only {present}/{len(items)} tokens present, need >= {minimum}")


def check_answer_ordered(judge, answer, name, items):
    pos = []
    for it in items:
        idx = answer.lower().find(it.lower())
        if idx < 0:
            judge.fail(f"ans_{name}", f"missing ordered item {it!r}")
            return
        pos.append(idx)
    if pos == sorted(pos):
        judge.ok(f"ans_{name}", f"{len(items)} items in order")
    else:
        judge.fail(f"ans_{name}", "items appear out of order")


def check_answer_absent(judge, answer, name, phrase):
    if phrase.lower() in answer.lower():
        judge.fail(f"ans_{name}", f"forbidden phrase {phrase!r} appears")
    else:
        judge.ok(f"ans_{name}", f"{phrase!r} absent")


# ------------------------------------------------------------------ DB deltas
def _table_rows(db_path, table):
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        cols = [r[1] for r in con.execute(f'PRAGMA table_info("{table}")')]
        return cols, con.execute(f'SELECT * FROM "{table}" ORDER BY ' + ",".join(f'"{c}"' for c in cols)).fetchall()
    finally:
        con.close()


def check_read_only(judge, initial_db, after_db):
    if initial_db is None or after_db is None:
        judge.fail("read_only", "DB snapshots unavailable")
        return
    for t in TABLES:
        _, a = _table_rows(initial_db, t)
        _, b = _table_rows(after_db, t)
        if a != b:
            judge.fail("read_only", f"table {t} changed ({len(a)} -> {len(b)} rows or content)")
            return
    judge.ok("read_only", "all 13 tables row-identical to the seed")


def check_only_tables_changed(judge, initial_db, after_db, allowed):
    if initial_db is None or after_db is None:
        judge.fail("table_delta", "DB snapshots unavailable")
        return
    changed = []
    for t in TABLES:
        _, a = _table_rows(initial_db, t)
        _, b = _table_rows(after_db, t)
        if a != b:
            changed.append(t)
    unexpected = [t for t in changed if t not in allowed]
    if unexpected:
        judge.fail("table_delta", f"unexpected table changes: {unexpected}")
    else:
        judge.ok("table_delta", f"changed tables {changed} within allowed {sorted(allowed)}")


def check_rows_added(judge, initial_db, after_db, table, count):
    if initial_db is None or after_db is None:
        judge.fail(f"rows_added[{table}]", "DB snapshots unavailable")
        return
    _, a = _table_rows(initial_db, table)
    _, b = _table_rows(after_db, table)
    if len(b) - len(a) != count:
        judge.fail(f"rows_added[{table}]", f"{len(a)} -> {len(b)} rows (expected +{count})")
    else:
        judge.ok(f"rows_added[{table}]", f"{len(a)} -> {len(b)} rows (+{count})")


def check_row_matches(judge, after_db, sql, params, name):
    if after_db is None:
        judge.fail(f"row[{name}]", "after DB unavailable")
        return
    con = sqlite3.connect(f"file:{after_db}?mode=ro", uri=True)
    try:
        row = con.execute(sql, params).fetchone()
        if row is None:
            judge.fail(f"row[{name}]", f"no row matches {name}")
        else:
            judge.ok(f"row[{name}]", f"{row}")
    finally:
        con.close()


def db_one(db_path, sql, params=()):
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return con.execute(sql, params).fetchone()
    finally:
        con.close()


# ---------------------------------------------------------------------- entry
def run_verifier(task_id, run_checks):
    ap = sys.argv
    run_dir = None
    initial_db = after_db = None
    i = 1
    while i < len(ap):
        if ap[i] == "--run_dir":
            run_dir = ap[i + 1]; i += 2
        elif ap[i] == "--initial_db":
            initial_db = ap[i + 1]; i += 2
        elif ap[i] == "--after_db":
            after_db = ap[i + 1]; i += 2
        elif ap[i] == "--container":
            global DEFAULT_CONTAINER
            DEFAULT_CONTAINER = ap[i + 1]; i += 2
        else:
            i += 1
    if not run_dir:
        print(json.dumps({"task_id": task_id, "pass": False,
                          "reason": "--run_dir is required", "evidence": []}))
        return 1
    traj = load_run(run_dir)
    judge = Judge(task_id)
    check_trajectory_identity(judge, traj, task_id)
    check_screenshots(judge, traj)
    initial_db = _resolve_db(judge, initial_db, traj["_run_dir"], "initial.db")
    after_db = _resolve_db(judge, after_db, traj["_run_dir"], "after.db")
    check_seed_contract(judge, initial_db)
    run_checks(judge, traj, initial_db, after_db)
    verdict = {"task_id": task_id, "pass": not judge.failures,
               "reason": "; ".join(judge.failures) if judge.failures else "all checks passed",
               "evidence": judge.evidence}
    print(json.dumps(verdict, indent=1))
    return 0 if not judge.failures else 1
