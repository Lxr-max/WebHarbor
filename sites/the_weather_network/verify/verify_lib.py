#!/usr/bin/env python3
"""verify_lib.py — deterministic verifier utilities for the_weather_network tasks.

Philosophy: DETERMINISTIC FIRST (same contract as the hardened reviewer
suites ``sites/student_com/verify/verify_lib.py`` /
``sites/sourceforge/verify/verify_lib.py``). No LLM call is load-bearing;
every check is regex / token / SQLite after-state.

  1. Package identity (fail-closed): task_id matches, ``terminated`` with
     ``agent_done``, non-empty final answer, every recorded URL on the same
     loopback origin AND port as ``start_url``, every referenced screenshot a
     decodable PNG.
  2. Navigation gates (anti knowledge-shortcut): the agent MUST have opened
     the on-site surfaces the task names (location forecast tabs, alerts,
     radar, news articles, video index, vacation country pages, explore hubs,
     account pages). A correct answer with no matching navigation is a
     memory-recall shortcut = FAIL.
  3. Answer check: affirmative token / phrase / number matching against frozen
     ground truth HARDCODED in each ``verify_N.py`` (never in tasks.jsonl).
     Two tasks (ski first-snow, golf best-day) allow the agent a free choice of
     Alberta location; their verifiers resolve the location the agent actually
     opened from the trajectory and validate the reported (date, high) pair
     against that location's frozen daily_forecasts rows.
  4. DB after-state: initial (seed) vs after (instance) SQLite snapshots.
     Read-only tasks require every table row-identical to the seed; stateful
     tasks (T5 bob's saved locations, T14 new account) require the exact
     allowed row delta and nothing else. The unit toggle (T4) is session-only
     when signed out, so T4 is read-only too.

Seed reproducibility note (review finding): the seed BUILD is not
byte-reproducible at the SQLite file level across build-time SQLite library
versions (host sqlite 3.45.1 vs in-container 3.40.1 produce different file
md5s), but the LOGICAL content is stable: the schema digest and the row
digest reproduce exactly across environments (verified against both the
contributor's host-built seed and the reviewer's in-container rebuild). The
contract therefore freezes the logical digests, NOT a file md5.

Input signature (per task):
  --run_dir DIR        agent trajectory dir: trajectory.json + screenshots/step_NNN.png
  --initial_db PATH    initial-state SQLite DB (default: <run_dir>/initial.db, else
                       instance_seed from the container)
  --after_db PATH      after-state  SQLite DB (default: <run_dir>/after.db, else live
                       instance DB from the container)
  --container NAME     docker container to fetch DBs from (default: $WH_CONTAINER or
                       wh-twn-review)
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
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

SITE = "the_weather_network"
DEFAULT_CONTAINER = os.environ.get("WH_CONTAINER", "wh-twn-review")

# ---------------------------------------------------------------- frozen seed contract
TABLES = ("alerts", "articles", "authors", "daily_forecasts", "hourly_forecasts",
          "locations", "monthly_averages", "observations", "saved_locations",
          "users", "videos", "wellbeing", "site_content")
SEED_COUNTS = {"alerts": 51, "articles": 638, "authors": 42,
               "daily_forecasts": 8700, "hourly_forecasts": 41760,
               "locations": 580, "monthly_averages": 23744,
               "observations": 580, "saved_locations": 15, "users": 4,
               "videos": 782, "wellbeing": 525, "site_content": 2}
# sha256 over sqlite_master (type, name, tbl_name, sql) of instance_seed/the_weather_network.db.
# Environment-stable: identical for the contributor's host-built seed (sqlite 3.45.1)
# and the reviewer's in-container rebuild (sqlite 3.40.1).
SCHEMA_SHA256 = "4ba151cf98be0352f32ba8e10e9782450884f63b1980bea0500d7c846e3eaa24"
# sha256 over every seed row (table-canonical, ORDER BY all columns).
SEED_ROWS_SHA256 = "c5994c0f36421a173db7885f8be84f9b1462c93bbc0d6cf10f86796acfd0eff2"
SEED_USERS = {  # email -> (id, display); identity columns never change
    "alice.j@test.com": (1, "Alice Johnson"),
    "bob.c@test.com": (2, "Bob Chen"),
    "carol.d@test.com": (3, "Carol Davis"),
    "david.k@test.com": (4, "David Kim"),
}
DEMO_PASSWORD = "TestPass123!"
INPUT_ACTIONS = {"input", "type", "fill", "input_text", "type_text", "check"}
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


def same_origin_port(traj):
    urls = trajectory_urls(traj)
    if not urls:
        return False, "no urls recorded"
    first = urlparse(urls[0])
    if not is_site_url(urls[0]):
        return False, f"start_url is not a loopback site url: {urls[0]!r}"
    for u in urls[1:]:
        p = urlparse(u)
        if (p.scheme, p.hostname, p.port) != (first.scheme, first.hostname, first.port):
            return False, f"off-origin url in trajectory: {u!r} (start {urls[0]!r})"
    return True, ""


def decode_png(path):
    """Return (ok, detail) for a PNG file: signature, chunk CRCs, IEND presence."""
    try:
        data = Path(path).read_bytes()
    except OSError as e:
        return False, f"unreadable: {e}"
    if len(data) < 8 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return False, "missing PNG signature"
    pos, seen_iend, chunks = 8, False, 0
    while pos + 8 <= len(data):
        length = int.from_bytes(data[pos:pos + 4], "big")
        ctype = data[pos + 4:pos + 8]
        if pos + 12 + length > len(data):
            return False, f"truncated chunk {ctype!r}"
        crc = int.from_bytes(data[pos + 8 + length:pos + 12 + length], "big")
        if zlib.crc32(data[pos + 4:pos + 8 + length]) != crc:
            return False, f"chunk {ctype!r} CRC mismatch"
        if ctype == b"IEND":
            seen_iend = True
            break
        pos += 12 + length
        chunks += 1
    if not seen_iend:
        return False, "missing IEND chunk"
    return True, f"ok ({chunks} chunks, {len(data)} bytes)"


def screenshots_ok(traj):
    refs = set()
    for step in traj.get("steps") or []:
        for key in ("screenshot_before", "screenshot_after"):
            if isinstance(step, dict) and step.get(key):
                refs.add(str(step[key]))
    if not refs:
        return False, "no screenshots referenced"
    for ref in sorted(refs):
        path = traj["_run_dir"] / "screenshots" / ref
        if not path.is_file():
            return False, f"missing screenshot: {ref}"
        ok, detail = decode_png(path)
        if not ok:
            return False, f"undecodable screenshot {ref}: {detail}"
    return True, f"{len(refs)} screenshots decode"


# ---------------------------------------------------------------- judge
@dataclass
class Judge:
    task_id: str
    evidence: list = field(default_factory=list)
    failures: list = field(default_factory=list)

    def check(self, name, ok, detail=""):
        if ok:
            self.evidence.append(f"PASS {name}: {detail}")
        else:
            self.failures.append(f"FAIL {name}: {detail}")
        return ok

    @property
    def verdict(self):
        if self.failures:
            return {"task_id": self.task_id, "pass": False,
                    "reason": "; ".join(self.failures[:6]),
                    "evidence": self.evidence + self.failures}
        return {"task_id": self.task_id, "pass": True,
                "reason": "all checks passed", "evidence": self.evidence}


def check_package(judge, traj, task_id):
    judge.check("task_id_match", traj.get("task_id") == task_id,
                f"trajectory task_id={traj.get('task_id')!r}")
    judge.check("terminated_agent_done",
                traj.get("terminated") is True and traj.get("termination_reason") == "agent_done",
                f"terminated={traj.get('terminated')!r} reason={traj.get('termination_reason')!r}")
    answer = final_answer(traj)
    judge.check("nonempty_answer", len(answer) >= 8, f"answer length={len(answer)}")
    ok, detail = same_origin_port(traj)
    judge.check("same_origin_port", ok, detail)
    ok, detail = screenshots_ok(traj)
    judge.check("screenshots_decode", ok, detail)


def check_trajectory_identity(judge, traj, task_id):
    check_package(judge, traj, task_id)


def visited_path(traj, pattern):
    rx = re.compile(pattern)
    return any(rx.search(u) for u in trajectory_urls(traj))


def check_visited_path(judge, traj, name, pattern):
    hit = visited_path(traj, pattern)
    judge.check(name, hit, f"required path ~{pattern}"
                + ("" if hit else f" — visited: {[u.split('localhost')[-1] for u in trajectory_urls(traj)][:12]}"))


# ---------------------------------------------------------------- answer checks
def check_answer_phrase(judge, answer, name, phrase, case_sensitive=False):
    hay = answer if case_sensitive else answer.casefold()
    needle = phrase if case_sensitive else phrase.casefold()
    judge.check(name, needle in hay, f"answer must mention {phrase!r}")


def _norm_num(s):
    s = re.sub(r"[,\s]", "", str(s)).strip(".,")
    return s.lower()


def check_answer_number(judge, answer, name, value, label=None):
    """The answer must contain the number (comma-formatted or plain)."""
    target = _norm_num(value)
    tokens = re.findall(NUM_TOKEN_RX, answer)
    found = any(_norm_num(tok) == target for tok in tokens)
    label_suffix = f" ({label})" if label else ""
    judge.check(name, found,
                f"answer must contain the number {value}{label_suffix}; "
                f"found tokens={tokens[:14]}")


SIGNED_NUM_TOKEN_RX = r"(?<![0-9])-?[0-9]+(?:[.,][0-9]+)?"


def check_answer_signed_number(judge, answer, name, value, label=None):
    """The answer must contain the (possibly negative) number as a standalone
    token. A minus only binds to a following number when not itself preceded by
    a digit, so ranges like '5-6 mm' do NOT satisfy a check for -6."""
    target = _norm_num(value)
    tokens = re.findall(SIGNED_NUM_TOKEN_RX, answer)
    found = any(_norm_num(tok) == target for tok in tokens)
    label_suffix = f" ({label})" if label else ""
    judge.check(name, found,
                f"answer must contain the number {value}{label_suffix}; "
                f"found tokens={tokens[:14]}")


def check_answer_any(judge, answer, name, variants, label=""):
    hay = answer.casefold()
    hit = any(_norm_num(v) in hay or str(v).casefold() in hay for v in variants)
    judge.check(name, hit, f"answer must mention one of {variants} {label}")


def check_answer_absent(judge, answer, name, phrases, label=""):
    """The answer must NOT contain any of the negation phrases."""
    hay = answer.casefold()
    hit = [p for p in phrases if p.casefold() in hay]
    judge.check(name, not hit,
                f"answer must not contain any of {phrases} {label}; found {hit}")


def check_answer_count_at_least(judge, answer, name, tokens, minimum, label=""):
    """At least `minimum` distinct tokens from `tokens` must appear."""
    hit = sum(1 for t in tokens if t.casefold() in answer.casefold())
    judge.check(name, hit >= minimum,
                f"answer must mention at least {minimum} of {label or tokens}; found {hit}")


# ---------------------------------------------------------------- sqlite state
def fetch_db(container, src, dest):
    dest = Path(dest)
    if dest.is_file():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["docker", "cp", f"{container}:{src}", str(dest)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"docker cp failed: {r.stderr[:200]}")
    return dest


def acquire_seed(cache=None, container=None):
    cache = Path(cache or os.environ.get("TWN_TEST_SEED_DB")
                 or Path("/tmp/twn_verify_seed.db"))
    if cache.is_file():
        return cache
    return fetch_db(container or DEFAULT_CONTAINER,
                    f"/opt/WebSyn/{SITE}/instance_seed/{SITE}.db", cache)


def acquire_instance(container=None):
    container = container or DEFAULT_CONTAINER
    out = Path("/tmp") / f"twn_verify_instance_{container}.db"
    if out.is_file():
        out.unlink()
    return fetch_db(container, f"/opt/WebSyn/{SITE}/instance/{SITE}.db", out)


def load_db(path):
    db = sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def schema_digest(db):
    h = hashlib.sha256()
    for r in db.execute("SELECT type, name, tbl_name, sql FROM sqlite_master "
                        "ORDER BY type, name"):
        h.update(("\x1f".join(str(x) for x in tuple(r))).encode())
    return h.hexdigest()


def rows_digest(db, tables=TABLES):
    h = hashlib.sha256()
    for t in tables:
        cols = [c[1] for c in db.execute(f"PRAGMA table_info({t})")]
        order = ", ".join(f'"{c}"' for c in cols)
        for r in db.execute(f'SELECT * FROM "{t}" ORDER BY {order}'):
            vals = []
            for v in tuple(r):
                if v is None:
                    vals.append("\x00")
                elif isinstance(v, bytes):
                    vals.append("b:" + hashlib.sha256(v).hexdigest())
                else:
                    vals.append(str(v))
            h.update((t + "\x1f" + "\x1f".join(vals)).encode())
    return h.hexdigest()


def table_counts(db, tables=TABLES):
    return {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}


def table_diff(initial_db, after_db, table):
    """Return (added, removed, changed) row-id maps for one table."""
    def snap(db):
        cols = [c[1] for c in db.execute(f"PRAGMA table_info({table})")]
        pk = [c[1] for c in db.execute(f"PRAGMA table_info({table})") if c[5]] or cols[:1]
        out = {}
        for r in db.execute(f'SELECT * FROM "{table}"'):
            row = {c: r[c] for c in cols}
            out[tuple(row[k] for k in pk)] = row
        return out
    a, b = snap(initial_db), snap(after_db)
    added = {k: v for k, v in b.items() if k not in a}
    removed = {k: v for k, v in a.items() if k not in b}
    changed = {}
    for k in set(a) & set(b):
        if a[k] != b[k]:
            changed[k] = (a[k], b[k])
    return added, removed, changed


def check_seed_initial(judge, initial_db):
    """The initial state must be the frozen seed (schema + rows + counts)."""
    judge.check("initial_is_seed_schema", schema_digest(initial_db) == SCHEMA_SHA256,
                "initial_db schema digest must match the frozen seed")
    judge.check("initial_is_seed_rows", rows_digest(initial_db) == SEED_ROWS_SHA256,
                "initial_db row digest must match the frozen seed")
    judge.check("initial_is_seed_counts", table_counts(initial_db) == SEED_COUNTS,
                "initial_db table counts must match the frozen seed")


def check_read_only(judge, initial_db, after_db):
    """Read-only contract: after-state rows identical to the frozen seed."""
    check_seed_initial(judge, initial_db)
    judge.check("after_rows_unchanged", rows_digest(after_db) == SEED_ROWS_SHA256,
                "read-only task: after_db rows must equal the seed rows")


def check_only_tables_changed(judge, initial_db, after_db, allowed):
    """Every table outside `allowed` must be row-identical; allowed tables are
    checked by the task verifier with exact deltas."""
    check_seed_initial(judge, initial_db)
    for t in TABLES:
        if t in allowed:
            continue
        added, removed, changed = table_diff(initial_db, after_db, t)
        judge.check(f"table_{t}_untouched",
                    not (added or removed or changed),
                    f"added={list(added)[:3]} removed={list(removed)[:3]} changed={list(changed)[:3]}")


def check_saved_location_delta(judge, initial_db, after_db, user_email,
                               added_path=None, removed_path=None, final_count=None):
    """Saved-locations contract on (user_id, loc_id): after vs initial must
    differ by exactly the expected added pair (and optionally the removed
    pair); optionally the final row count for that user must match."""
    uid = SEED_USERS[user_email][0] if user_email in SEED_USERS else None
    if uid is None:
        row = after_db.execute("SELECT id FROM users WHERE email = ?", (user_email,)).fetchone()
        uid = row["id"] if row else -1

    def loc_id(db, path):
        row = db.execute("SELECT id FROM locations WHERE url_path = ?", (path,)).fetchone()
        return row["id"] if row else None

    def pairs(db):
        return {(r["user_id"], r["loc_id"])
                for r in db.execute("SELECT user_id, loc_id FROM saved_locations")}
    before_set, after_set = pairs(initial_db), pairs(after_db)
    added = after_set - before_set
    removed = before_set - after_set
    if added_path is not None:
        judge.check("saved_added",
                    added == {(uid, loc_id(after_db, added_path))},
                    f"expected +({uid}, {added_path}); got +{added}")
    else:
        judge.check("saved_no_additions", not added, f"unexpected additions {added}")
    if removed_path is not None:
        judge.check("saved_removed",
                    removed == {(uid, loc_id(initial_db, removed_path))},
                    f"expected -({uid}, {removed_path}); got -{removed}")
    else:
        judge.check("saved_no_removals", not removed, f"unexpected removals {removed}")
    if final_count is not None:
        n = after_db.execute("SELECT COUNT(*) FROM saved_locations WHERE user_id = ?",
                             (uid,)).fetchone()[0]
        judge.check("saved_final_count", n == final_count,
                    f"expected {final_count} saved locations for {user_email}; got {n}")


def check_user_created(judge, initial_db, after_db, username):
    """Exactly one user row added with the expected username (T14)."""
    a_add, a_rem, a_chg = table_diff(initial_db, after_db, "users")
    adds = list(a_add.values())
    ok = (len(adds) == 1 and not a_rem and not a_chg
          and adds[0]["username"] == username)
    judge.check("user_created", ok,
                f"expected +1 user (username {username!r}); got {adds[:2]}")
    return adds[0]["id"] if ok else None


# ---------------------------------------------------------------- location-choice helpers
def visited_location_slug(traj, channel, channel_url=None):
    """Resolve the Alberta location slug the agent opened on a forecast tab.

    Returns the url_path (e.g. 'ca/alberta/banff-sunshine') when the
    trajectory visited /en/<channel_url>/<cc>/<prov>/<slug>/<tab>, else None.
    """
    channel_url = channel_url or channel
    rx = re.compile(rf"/en/{channel_url}/(ca/alberta/[a-z0-9-]+)/(current|hourly|7-days|14-days|weekend|monthly)")
    for u in trajectory_urls(traj):
        m = rx.search(u)
        if m:
            return m.group(1)
    return None


def daily_rows(db, url_path, channel, start="2026-09-26", end="2026-10-10"):
    row = db.execute("SELECT id FROM locations WHERE url_path = ? AND channel = ?",
                     (url_path, channel)).fetchone()
    if not row:
        return []
    return db.execute(
        "SELECT date_local, day_temp, day_pop, pop, day_snow, night_snow, day_text "
        "FROM daily_forecasts WHERE loc_id = ? AND date_local >= ? AND date_local <= ? "
        "ORDER BY date_local", (row["id"], start + "T00:00", end + "T23:59")).fetchall()


# ---------------------------------------------------------------- runner
def run_verifier(task_id, verify_module_main, argv=None):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_dir", required=True)
    parser.add_argument("--initial_db")
    parser.add_argument("--after_db")
    parser.add_argument("--container", default=DEFAULT_CONTAINER)
    parser.add_argument("--seed_cache")
    args = parser.parse_args(argv)

    traj = load_run(args.run_dir)
    initial = Path(args.initial_db) if args.initial_db else None
    after = Path(args.after_db) if args.after_db else None
    if initial is None:
        cand = Path(args.run_dir) / "initial.db"
        initial = cand if cand.is_file() else acquire_seed(args.seed_cache, args.container)
    if after is None:
        cand = Path(args.run_dir) / "after.db"
        after = cand if cand.is_file() else acquire_instance(args.container)
    judge = Judge(task_id)
    try:
        verify_module_main(judge, traj, load_db(initial), load_db(after))
    except sqlite3.Error as e:
        judge.check("db_readable", False, f"sqlite error: {e}")
    result = judge.verdict
    print(json.dumps(result, indent=1))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit("import this module from verify_N.py")
