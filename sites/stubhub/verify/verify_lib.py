#!/usr/bin/env python3
"""verify_lib.py — deterministic verifier utilities for stubhub task verification.

Philosophy: DETERMINISTIC FIRST — same contract as the hardened reviewer suites
(``sites/soundcloud/verify/verify_lib.py``, ``sites/ryanair/verify/verify_lib.py``).
No LLM call is load-bearing; every check is regex / token / SQLite after-state.

  1. Package identity (fail-closed): task_id matches, ``terminated`` with
     ``agent_done``, non-empty final answer, every recorded URL on the same
     loopback origin AND port as ``start_url``, every referenced screenshot a
     decodable PNG.
  2. Navigation gates (anti knowledge-shortcut): the agent MUST have opened the
     on-site surfaces the task names (performer pages, event pages, listing
     detail, checkout steps, account pages, gift cards, search). A correct
     answer with no matching navigation is a memory-recall shortcut = FAIL.
  3. Answer check: affirmative token / phrase / number matching against frozen
     ground truth HARDCODED in each ``verify_N.py`` (never in tasks.jsonl).
  4. DB after-state: initial (seed) vs after (instance) SQLite snapshots.
     Read-only tasks require every table row-identical to the seed; stateful
     tasks require the exact allowed row delta and nothing else.

Input signature (per task):
  --run_dir DIR        agent trajectory dir: trajectory.json + screenshots/step_NNN.png
  --initial_db PATH    initial-state SQLite DB (default: <run_dir>/initial.db, else
                       instance_seed from the container)
  --after_db PATH      after-state  SQLite DB (default: <run_dir>/after.db, else live
                       instance DB from the container)
  --container NAME     docker container to fetch DBs from (default: $WH_CONTAINER or
                       wh-stubhub-review)
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

SITE = "stubhub"
DEFAULT_CONTAINER = os.environ.get("WH_CONTAINER", "wh-stubhub-review")

# ---------------------------------------------------------------- frozen seed contract
TABLES = ("category_nodes", "events", "favorites", "gift_card_orders", "listings",
          "metros", "notifications", "orders", "payment_cards", "performers",
          "sales", "users", "venues")
SEED_COUNTS = {"category_nodes": 35, "events": 1268, "favorites": 13,
               "gift_card_orders": 4, "listings": 20885, "metros": 6,
               "notifications": 8, "orders": 8, "payment_cards": 7,
               "performers": 699, "sales": 3, "users": 4, "venues": 335}
# sha256 over sqlite_master (type, name, tbl_name, sql) of instance_seed/stubhub.db.
SCHEMA_SHA256 = "74e0fe8e25b4f4327c9777b042ac31b25197867de8113496ed07f16afe12fe7d"
# sha256 over every seed row (table-canonical, ORDER BY all columns). The seed is
# built deterministically at image build time (PYTHONHASHSEED=0; md5 c71165b3…).
# r2 sync (2026-09-26): the F1/F5/F10 fix commit changed performers.image_file /
# hero_file / node_id (602/699 imagery, 699/699 nodes), 9 events' listing_count /
# min_price and 4 notification date strings, so the row digest moved from the
# r1 value f3f087c8… to 4cd4a215… (schema digest and row counts unchanged).
SEED_ROWS_SHA256 = "0f811c69b26ca2538470fd512fdc4eec0d6819d3da87841a0471c4d46a4fad47"
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
    """Decode the entire pixel stream, not merely its PNG chunk wrappers."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            im.load()
            return im.format == "PNG" and im.width > 0 and im.height > 0, "decoded PNG"
    except (OSError, ValueError, ImportError) as exc:
        return False, str(exc)


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


def typed_search_term(traj, term):
    """True when the trajectory typed `term` into the search box (the
    autocomplete path added by the F7 fix, fed by
    /secure/search/getSuggestedSearches). Accepts the agent_demo input
    action shape (params: {index, text}) and the reviewer walker shape
    (params: {selector, text}); when a selector is recorded it must be the
    search box, so typing the term into an unrelated field does not count."""
    needle = str(term).casefold()
    for step in traj.get("steps") or []:
        if not isinstance(step, dict):
            continue
        action = str(step.get("action") or "").casefold()
        if action not in {"input", "fill", "type", "input_text", "type_text"}:
            continue
        params = step.get("params") or {}
        text = str(params.get("text") or "").casefold()
        if needle not in text:
            continue
        selector = str(params.get("selector") or "").casefold()
        if selector and "search" not in selector:
            continue
        return True
    return False


def check_search_suggestions(judge, traj, name, term):
    """The agent must have consulted the suggestion service for `term`:
    either the raw endpoint URL appears in the trajectory (direct call) or the
    term was typed into the site search box (autocomplete dropdown path)."""
    endpoint = visited_path(traj, rf"/secure/search/getSuggestedSearches\?q={term}")
    typed = typed_search_term(traj, term)
    judge.check(name, endpoint or typed,
                f"suggestion service used for {term!r}: endpoint={endpoint} typed={typed}")
    return endpoint or typed


def check_visited_path(judge, traj, name, pattern):
    hit = visited_path(traj, pattern)
    judge.check(name, hit, f"required path ~{pattern}"
                + ("" if hit else f" — visited: {[u.split('localhost')[-1] for u in trajectory_urls(traj)][:14]}"))


def _affirmative(text, match):
    prefix = re.split(r"[;.!?\n]|\b(?:but|however)\b", text[:match.start()], flags=re.I)[-1]
    return not re.search(r"\b(?:not|never|incorrect|wrong|isn't|isnt)\b(?:\W+\w+){0,3}\W*$", prefix, re.I)


def check_answer_phrase(judge, answer, name, phrase, case_sensitive=False):
    hay = answer if case_sensitive else answer.casefold()
    needle = phrase if case_sensitive else phrase.casefold()
    judge.check(name, any(_affirmative(hay, m) for m in re.finditer(re.escape(needle), hay)), f"answer must mention {phrase!r}")


def check_answer_regex(judge, answer, name, pattern, label=""):
    judge.check(name, bool(re.search(pattern, answer, re.I)),
                f"answer must match {label or pattern!r}")


def _norm_num(s):
    from decimal import Decimal, InvalidOperation
    value = re.sub(r"[,\s]", "", str(s)).strip(".,")
    try:
        return Decimal(value)
    except InvalidOperation:
        return value.casefold()


def check_answer_number(judge, answer, name, value, label=None):
    target = _norm_num(value)
    found = any(_norm_num(m.group()) == target and _affirmative(answer, m)
                for m in re.finditer(r"(?<![\w.])[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?(?!\w|\.\d)", answer))
    judge.check(name, found, f"answer must affirm {value} ({label or name})")


def check_answer_any(judge, answer, name, variants, label=""):
    hay = answer.casefold()
    hit = any(str(_norm_num(v)) in hay or str(v).casefold() in hay for v in variants)
    judge.check(name, hit, f"answer must mention one of {variants} {label}")


def check_answer_one_of(judge, answer, name, variants, label=""):
    """Exactly the disjunction matters (e.g. tie cases): any variant passes."""
    hay = answer.casefold()
    hits = [v for v in variants if str(v).casefold() in hay]
    judge.check(name, bool(hits), f"answer must mention one of {variants} {label}; "
                f"found={hits[:4]}")


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


def acquire_seed(cache=None):
    cache = Path(cache or os.environ.get("STUBHUB_TEST_SEED_DB")
                 or Path("/tmp/stubhub_verify_seed.db"))
    if cache.is_file():
        return cache
    return fetch_db(DEFAULT_CONTAINER,
                    f"/opt/WebSyn/{SITE}/instance_seed/{SITE}.db", cache)


def acquire_instance(container=None):
    container = container or DEFAULT_CONTAINER
    out = Path("/tmp") / f"stubhub_verify_instance_{container}.db"
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


def check_read_only(judge, initial_db, after_db):
    """Read-only contract: after-state rows identical to the frozen seed."""
    judge.check("initial_is_seed_schema", schema_digest(initial_db) == SCHEMA_SHA256,
                "initial_db schema digest must match the frozen seed")
    judge.check("initial_is_seed_rows", rows_digest(initial_db) == SEED_ROWS_SHA256,
                "initial_db row digest must match the frozen seed")
    judge.check("after_schema_unchanged", schema_digest(after_db) == schema_digest(initial_db))
    judge.check("after_rows_unchanged", rows_digest(after_db) == SEED_ROWS_SHA256,
                "read-only task: after_db rows must equal the seed rows")


def check_only_tables_changed(judge, initial_db, after_db, allowed):
    """Every table outside `allowed` must be row-identical; allowed tables are
    checked by the task verifier with exact deltas."""
    judge.check("initial_is_seed_schema", schema_digest(initial_db) == SCHEMA_SHA256)
    judge.check("initial_is_seed_rows", rows_digest(initial_db) == SEED_ROWS_SHA256)
    judge.check("after_schema_unchanged", schema_digest(after_db) == schema_digest(initial_db))
    for t in TABLES:
        if t in allowed:
            continue
        added, removed, changed = table_diff(initial_db, after_db, t)
        judge.check(f"table_{t}_untouched",
                    not (added or removed or changed),
                    f"added={list(added)[:3]} removed={list(removed)[:3]} changed={list(changed)[:3]}")


def check_table_deltas(judge, initial_db, after_db, expected):
    """Exact-delta contract per table:
      expected = {table: {"added": [pk-tuples], "removed": [pk-tuples],
                          "changed": {pk: {field: (before, after)}},
                          "added_count": int}}
    Unlisted keys default to "no rows". pk-tuples compare with the table's
    primary key (or first column when the table has no explicit pk).
    """
    for table, exp in expected.items():
        added, removed, changed = table_diff(initial_db, after_db, table)
        exp_removed = set(exp.get("removed", ()))
        judge.check(f"{table}_removed_exact",
                    set(removed) == exp_removed,
                    f"removed={sorted(removed)} expected={sorted(exp_removed)}")
        if "added" in exp:
            judge.check(f"{table}_added_exact",
                        set(added) == set(exp["added"]),
                        f"added={sorted(added)} expected={sorted(exp['added'])}")
        if "added_count" in exp:
            judge.check(f"{table}_added_count", len(added) == exp["added_count"],
                        f"added_count={len(added)} expected={exp['added_count']}")
        exp_changed = exp.get("changed", {})
        judge.check(f"{table}_changed_keys",
                    set(changed) == set(exp_changed),
                    f"changed={sorted(changed)} expected={sorted(exp_changed)}")
        for pk, fields in exp_changed.items():
            if pk not in changed:
                continue
            before, after = changed[pk]
            for field, (want_before, want_after) in fields.items():
                judge.check(f"{table}_{pk}_{field}_delta",
                            before[field] == want_before and after[field] == want_after,
                            f"{field}: {before[field]!r} -> {after[field]!r}, "
                            f"expected {want_before!r} -> {want_after!r}")


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
        initial = cand if cand.is_file() else acquire_seed(args.seed_cache)
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
