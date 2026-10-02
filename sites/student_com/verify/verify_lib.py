#!/usr/bin/env python3
"""verify_lib.py — deterministic verifier utilities for student_com task verification.

Philosophy: DETERMINISTIC FIRST — same contract as the hardened reviewer suites
(``sites/sourceforge/verify/verify_lib.py``). No LLM call is load-bearing; every
check is regex / token / SQLite after-state.

  1. Package identity (fail-closed): task_id matches, ``terminated`` with
     ``agent_done``, non-empty final answer, every recorded URL on the same
     loopback origin AND port as ``start_url``, every referenced screenshot a
     decodable PNG.
  2. Navigation gates (anti knowledge-shortcut): the agent MUST have opened the
     on-site surfaces the task names (university SRPs with the exact filter
     query strings, property pages, profile pages, budget calculator, jobs
     pages, the scams guide). A correct answer with no matching navigation is a
     memory-recall shortcut = FAIL.
  3. Answer check: affirmative token / phrase / number matching against frozen
     ground truth HARDCODED in each ``verify_N.py`` (never in tasks.jsonl).
  4. DB after-state: initial (seed) vs after (instance) SQLite snapshots.
     Read-only tasks require every table row-identical to the seed; browsing
     tasks may add exactly the expected ``property_views`` rows (opening a
     property page records a view — including on the 18 pages that currently
     crash with HTTP 500, because ``record_view()`` commits before render);
     stateful tasks require the exact allowed row delta and nothing else (a
     bookmark added/removed, an enquiry row with the deterministic reference,
     a registered user).

Seed reproducibility note (review finding): the student_com seed BUILD is not
byte-reproducible at the SQLite file level (four clean rebuilds produced four
different file md5s — physical page layout varies), but the LOGICAL content is
stable: schema digest and row digest reproduce exactly across rebuilds. The
contract therefore freezes the logical digests, NOT a file md5.

Input signature (per task):
  --run_dir DIR        agent trajectory dir: trajectory.json + screenshots/step_NNN.png
  --initial_db PATH    initial-state SQLite DB (default: <run_dir>/initial.db, else
                       instance_seed from the container)
  --after_db PATH      after-state  SQLite DB (default: <run_dir>/after.db, else live
                       instance DB from the container)
  --container NAME     docker container to fetch DBs from (default: $WH_CONTAINER or
                       wh-student-com-review)
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

SITE = "student_com"
DEFAULT_CONTAINER = os.environ.get("WH_CONTAINER", "wh-student-com-review")

# ---------------------------------------------------------------- frozen seed contract
TABLES = ("bookmarks", "cities", "contact_messages", "enquiries", "jobs",
          "newsletter_signups", "properties", "property_universities",
          "property_views", "universities", "users")
SEED_COUNTS = {"bookmarks": 12, "cities": 19, "contact_messages": 0,
               "enquiries": 4, "jobs": 113, "newsletter_signups": 0,
               "properties": 414, "property_universities": 414,
               "property_views": 12, "universities": 269, "users": 4}
# sha256 over sqlite_master (type, name, tbl_name, sql) of instance_seed/student_com.db.
SCHEMA_SHA256 = "690443d78ed89c96f4eaf9b9829089ef5063470034d4f9bc329fd7691cdfa4ad"
# sha256 over every seed row (table-canonical, ORDER BY all columns). The logical
# content reproduces on every PYTHONHASHSEED=0 rebuild even though the raw file
# md5 does not (SQLite physical layout varies run to run).
SEED_ROWS_SHA256 = "68f0c7c066e7a1e4c1f55f9d64b35e1aaa832b870e82b265d66fdf505f665e7e"
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
    try:
        from PIL import Image
        with Image.open(path) as image:
            image.load()
            return image.format == "PNG" and image.width > 0 and image.height > 0, "decoded PNG"
    except (OSError, ValueError) as exc:
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
    judge.trajectory = traj
    check_package(judge, traj, task_id)


def check_visited_path(judge, traj, name, pattern):
    hit = visited_path(traj, pattern)
    judge.check(name, hit, f"required path ~{pattern}"
                + ("" if hit else f" — visited: {[u.split('localhost')[-1] for u in trajectory_urls(traj)][:12]}"))


def check_answer_phrase(judge, answer, name, phrase, case_sensitive=False):
    hay = answer if case_sensitive else answer.casefold()
    needle = phrase if case_sensitive else phrase.casefold()
    aliases = {
        'report anything suspicious': r'report.{0,35}(?:suspicious|student\.com)',
        'trace the paperwork': r'(?:save|keep|retain).{0,45}(?:evidence|records|screenshots|emails)',
        'external authorities': r'(?:contact|notify|report to).{0,30}(?:authorities|ic3|ftc)',
        'ghost': r'(?:ghost|absent|away|cannot (?:meet|show)|refus.{0,20}view)',
    }
    ok = needle in hay or (needle in aliases and bool(re.search(aliases[needle], hay)))
    judge.check(name, ok, f"answer must state {phrase!r} or its equivalent")


def _norm_num(s):
    s = re.sub(r"[,\s]", "", str(s)).strip(".,")
    return s.lower()


def check_answer_number(judge, answer, name, value, label=None):
    from answer_bindings import BINDINGS, number_bound, _number_pattern, _affirmed, _assertions
    task_no = int(judge.task_id.split('--')[-1])
    groups = BINDINGS.get(task_no, {}).get(name)
    if groups:
        found = number_bound(answer, str(value), groups)
    else:
        found = any(_affirmed(segment, m.start()) for segment in _assertions(answer)
                    for m in _number_pattern(str(value)).finditer(segment))
    judge.check(name, found, f"answer must accurately state {value} for {label or name}")


def check_answer_any(judge, answer, name, variants, label=""):
    hay = answer.casefold()
    hit = any(_norm_num(v) in hay or str(v).casefold() in hay for v in variants)
    judge.check(name, hit, f"answer must mention one of {variants} {label}")


def check_answer_absent(judge, answer, name, phrases, label=""):
    """The answer must NOT contain any of the negation phrases (e.g. a task
    asking whether items appear must not be passable with 'do not appear')."""
    hay = answer.casefold()
    hit = [p for p in phrases if p.casefold() in hay]
    judge.check(name, not hit,
                f"answer must not contain any of {phrases} {label}; found {hit}")


def check_answer_count_at_least(judge, answer, name, tokens, minimum, label=""):
    """At least `minimum` distinct tokens from `tokens` must appear (e.g. two
    amenities, three vibe labels)."""
    hit = sum(1 for t in tokens if t.casefold() in answer.casefold())
    judge.check(name, hit >= minimum,
                f"answer must mention at least {minimum} of {label or tokens}; found {hit}")


# ---------------------------------------------------------------- navigation
def visited_path(traj, pattern):
    rx = re.compile(pattern)
    return any(rx.search(u) for u in trajectory_urls(traj))


def visited_all(traj, patterns):
    return all(visited_path(traj, p) for p in patterns)


def count_input_actions(traj):
    n = 0
    for step in traj.get("steps") or []:
        if isinstance(step, dict) and step.get("action") in INPUT_ACTIONS:
            n += 1
    return n


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
    cache = Path(cache or os.environ.get("STUDENT_COM_TEST_SEED_DB")
                 or Path("/tmp/student_com_verify_seed.db"))
    if cache.is_file():
        return cache
    return fetch_db(container or DEFAULT_CONTAINER,
                    f"/opt/WebSyn/{SITE}/instance_seed/{SITE}.db", cache)


def acquire_instance(container=None):
    container = container or DEFAULT_CONTAINER
    out = Path("/tmp") / f"student_com_verify_instance_{container}.db"
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
    judge.check("after_schema_unchanged", schema_digest(after_db) == schema_digest(initial_db))
    judge.check("after_rows_unchanged", rows_digest(after_db) == SEED_ROWS_SHA256,
                "read-only task: after_db rows must equal the seed rows")


def check_views_only(judge, initial_db, after_db, expected_slugs):
    """Browsing contract: only property_views may grow, by exactly the expected
    property pages (opening a property page records a view)."""
    check_seed_initial(judge, initial_db)
    judge.check("after_schema_unchanged", schema_digest(after_db) == schema_digest(initial_db))
    for t in TABLES:
        if t == "property_views":
            continue
        added, removed, changed = table_diff(initial_db, after_db, t)
        judge.check(f"table_{t}_untouched",
                    not (added or removed or changed),
                    f"added={list(added)[:3]} removed={list(removed)[:3]} changed={list(changed)[:3]}")
    added, removed, changed = table_diff(initial_db, after_db, "property_views")
    added_slugs = sorted({row["property_slug"] for row in added.values()})
    judge.check("views_only_added",
                not removed and not changed and set(expected_slugs).issubset(added_slugs) and all(any("/p/" + slug in u for u in trajectory_urls(getattr(judge, "trajectory", {}))) for slug in added_slugs),
                f"expected new views {sorted(set(expected_slugs))}, "
                f"got added={added_slugs} removed={len(removed)} changed={len(changed)}")


def check_only_tables_changed(judge, initial_db, after_db, allowed):
    """Every table outside `allowed` must be row-identical; allowed tables are
    checked by the task verifier with exact deltas."""
    check_seed_initial(judge, initial_db)
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


def check_views_added(judge, initial_db, after_db, expected_slugs):
    """Stateful-task companion: property_views must gain exactly the expected
    property-page views (opening a property page records a view) and nothing
    else may change inside that table."""
    added, removed, changed = table_diff(initial_db, after_db, "property_views")
    added_slugs = sorted({row["property_slug"] for row in added.values()})
    judge.check("views_added",
                not removed and not changed and set(expected_slugs).issubset(added_slugs) and all(any("/p/" + slug in u for u in trajectory_urls(getattr(judge, "trajectory", {}))) for slug in added_slugs),
                f"expected new views {sorted(set(expected_slugs))}, "
                f"got added={added_slugs} removed={len(removed)} changed={len(changed)}")


def check_bookmark_delta(judge, initial_db, after_db, user_email, added_slug, removed_slug):
    """Set semantics on (user_id, property_slug): after vs initial must differ by
    exactly the expected added pair (and optionally the removed pair). Rowid
    reuse (SQLite assigns max(id)+1, so remove-then-add can rewrite the same
    row id) is irrelevant at this level."""
    uid = SEED_USERS[user_email][0] if user_email in SEED_USERS else None
    if uid is None:
        # newly registered user: resolve the id from the after state
        row = after_db.execute("SELECT id FROM users WHERE email = ?", (user_email,)).fetchone()
        uid = row["id"] if row else -1

    def pairs(db):
        return {(r["user_id"], r["property_slug"])
                for r in db.execute("SELECT user_id, property_slug FROM bookmarks")}
    before_set, after_set = pairs(initial_db), pairs(after_db)
    added = after_set - before_set
    removed = before_set - after_set
    judge.check("bookmark_added", added == {(uid, added_slug)},
                f"expected +({uid}, {added_slug}); got +{added}")
    if removed_slug is not None:
        judge.check("bookmark_removed", removed == {(uid, removed_slug)},
                    f"expected -({uid}, {removed_slug}); got -{removed}")
    else:
        judge.check("bookmark_no_removals", not removed, f"unexpected removals {removed}")


def check_enquiry_created(judge, initial_db, after_db, user_email, property_slug, reference):
    """Exactly one enquiry row added with the deterministic reference (the
    reference is derived: INQ-<id:06d>; the seed carries enquiries id 1-4, so a
    fresh-state inquiry is id 5 -> INQ-000005)."""
    uid = SEED_USERS[user_email][0] if user_email in SEED_USERS else None
    if uid is None:
        row = after_db.execute("SELECT id FROM users WHERE email = ?", (user_email,)).fetchone()
        uid = row["id"] if row else -1
    a_add, a_rem, a_chg = table_diff(initial_db, after_db, "enquiries")
    adds = list(a_add.values())
    ok = (len(adds) == 1 and not a_rem and not a_chg
          and adds[0]["user_id"] == uid
          and adds[0]["property_slug"] == property_slug
          and f"INQ-{adds[0]['id']:06d}" == reference)
    judge.check("enquiry_created", ok,
                f"expected +1 enquiry ({user_email}, {property_slug}, {reference}); got {adds[:2]}")

    if len(adds) == 1:
        row = adds[0]
        judge.check("inquiry_contact_email", row["email"].casefold() == user_email.casefold())
        judge.check("inquiry_contact_name", bool(row["first_name"].strip()) and bool(row["last_name"].strip()))
        judge.check("inquiry_phone", len(re.sub(r"\D", "", row["phone"])) >= 7)
        message = row["message"].casefold()
        terms = {"littlefield-hall-kutkl0": ["fall", "available"],
                 "the-butler-olmq6o": ["spring", "available"],
                 "villas-on-rio-8639e0": ["available", "move"],
                 "moontower-69d81c": ["studio", "private bathroom", "fall", "available"]}.get(property_slug, [])
        judge.check("inquiry_request", all(term in message or (term == "available" and "availability" in message) for term in terms))


def check_user_created(judge, initial_db, after_db, email, first_name, last_name):
    a_add, a_rem, a_chg = table_diff(initial_db, after_db, "users")
    adds = list(a_add.values())
    ok = (len(adds) == 1 and not a_rem and not a_chg
          and adds[0]["email"] == email
          and adds[0]["first_name"] == first_name
          and adds[0]["last_name"] == last_name)
    judge.check("user_created", ok,
                f"expected +1 user ({first_name} {last_name} <{email}>); got {adds[:2]}")


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
