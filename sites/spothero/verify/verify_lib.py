#!/usr/bin/env python3
"""verify_lib.py — deterministic verifier utilities for spothero task
verification (review track, orch/review/spothero).

Philosophy: DETERMINISTIC FIRST — same contract as the hardened reviewer
suites (statista/sourceforge). No LLM call is load-bearing; every check is
regex / token / SQLite after-state.

  1. Package identity (fail-closed): task_id matches, ``terminated`` with
     ``agent_done``, non-empty final answer, every recorded URL on the same
     loopback origin AND port as ``start_url``, every referenced screenshot a
     decodable PNG.
  2. Navigation gates (anti knowledge-shortcut): the agent MUST have opened
     the on-site surfaces the task names (search results with the required
     filters, facility pages, airport/city/destination/stadium/monthly/FAQ
     surfaces, login/signup, the account area). A correct answer with no
     matching navigation is a memory-recall shortcut = FAIL.
  3. Answer check: affirmative token / phrase / number matching against
     frozen ground truth HARDCODED in each ``verify_N.py`` (never in
     tasks.jsonl).
  4. DB after-state: initial (seed) vs after (instance) SQLite snapshots.
     Catalog tables must stay row-identical; the four mutable tables
     (users / reservations / payment_methods / favorites) must show the
     exact allowed row delta and nothing else. The seed contract is pinned
     to the review container's deterministic build (md5 482fb61d…).

Input signature (per task):
  --run_dir DIR        agent trajectory dir: trajectory.json + screenshots/step_NNN.png
  --initial_db PATH    initial-state SQLite DB (default: <run_dir>/initial.db, else
                       instance_seed from the container)
  --after_db PATH      after-state  SQLite DB (default: <run_dir>/after.db, else live
                       instance DB from the container)
  --container NAME     docker container to fetch DBs from (default: $WH_CONTAINER or
                       wh-spothero-review)
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

SITE = "spothero"
DEFAULT_CONTAINER = os.environ.get("WH_CONTAINER", "wh-spothero-review")

# ---------------------------------------------------------------- frozen seed contract
# Review container wh-spothero-review, image webharbor:spothero-review,
# seed built from the committed tree (PYTHONHASHSEED=0 deterministic bootstrap),
# md5 482fb61de5ce11dab0955c90c68c1ebc, byte-reproducible across rebuilds.
TABLES = ("airports", "cities", "contact_messages", "destinations", "events",
          "facilities", "faqs", "favorites", "payment_methods", "promo_codes",
          "reservations", "reviews", "stadiums", "static_pages", "users")
SEED_COUNTS = {"airports": 15, "cities": 15, "contact_messages": 0,
               "destinations": 37, "events": 1242, "facilities": 708,
               "faqs": 72, "favorites": 9, "payment_methods": 6,
               "promo_codes": 1, "reservations": 8, "reviews": 4248,
               "stadiums": 120, "static_pages": 16, "users": 4}
SEED_MD5 = "5164e94e6790d8cf8245e8c524ee765f"
# sha256 over sqlite_master (type, name, tbl_name, sql) of instance_seed/spothero.db.
SCHEMA_SHA256 = "18c5a3323fe4aff1588fd5e4da12c22661341f384ac453359eb74d645278db77"
# sha256 over every seed row (table-canonical, ORDER BY all columns).
SEED_ROWS_SHA256 = "35cf29da0d473d93807d4ebf93ef42b5b6c8843c36633a9009ae6e762687abd3"
SEED_USERS = {  # email -> (id, name); identity columns never change
    "alice.j@test.com": (1, "Alice Johnson"),
    "bob.c@test.com": (2, "Bob Chen"),
    "carol.d@test.com": (3, "Carol Davis"),
    "david.k@test.com": (4, "David Kim"),
}
DEMO_PASSWORD = "TestPass123!"
BCRYPT_RX = re.compile(r"^\$2[aby]\$12\$[./A-Za-z0-9]{53}$")
INPUT_ACTIONS = {"input", "type", "fill", "input_text", "type_text", "check",
                 "select_dropdown"}
NUM_TOKEN_RX = r"[0-9][0-9,.]*"
RES_CODE_RX = re.compile(r"\bSH-[A-Z0-9]{6}\b")
MUTABLE = ("users", "reservations", "payment_methods", "favorites")

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


def check_visited_path(judge, traj, name, pattern):
    hit = visited_path(traj, pattern)
    judge.check(name, hit, f"required path ~{pattern}"
                + ("" if hit else f" — visited: "
                   f"{[u.split('localhost')[-1] for u in trajectory_urls(traj)][:12]}"))


def check_visited_path_count(judge, traj, name, pattern, min_count):
    rx = re.compile(pattern)
    n = sum(1 for u in trajectory_urls(traj) if rx.search(u))
    judge.check(name, n >= min_count,
                f"required >= {min_count} visits of ~{pattern}, found {n}")


def check_answer_phrase(judge, answer, name, phrase, case_sensitive=False):
    hay = answer if case_sensitive else answer.casefold()
    needle = phrase if case_sensitive else phrase.casefold()
    judge.check(name, needle in hay, f"answer must mention {phrase!r}")


def _num_tokens(answer):
    return re.findall(r"(?<![\w.])[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?(?!\w|\.\d)", answer)


def _fnum(tok):
    try:
        return float(str(tok).replace(",", "").rstrip(".,"))
    except ValueError:
        return None


def check_answer_number(judge, answer, name, value, label=None):
    """The answer must contain the numeric value (float-equal, any formatting)."""
    target = float(value)
    hit = any(_fnum(t) == target for t in _num_tokens(answer))
    label_suffix = f" ({label})" if label else ""
    judge.check(name, hit,
                f"answer must contain the number {value}{label_suffix}; "
                f"found tokens={_num_tokens(answer)[:14]}")


def check_answer_any_number(judge, answer, name, variants, label=""):
    toks = [_fnum(t) for t in _num_tokens(answer)]
    hit = any(any(v == t for t in toks) for v in (float(x) for x in variants))
    judge.check(name, hit, f"answer must mention one of {variants} {label}")


def check_answer_any(judge, answer, name, variants, label=""):
    hay = answer.casefold()
    hit = any(str(v).casefold() in hay for v in variants)
    judge.check(name, hit, f"answer must mention one of {variants} {label}")


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
    cache = Path(cache or os.environ.get("SPOTHERO_TEST_SEED_DB")
                 or Path("/tmp/spothero_verify_seed.db"))
    if cache.is_file():
        return cache
    return fetch_db(container or DEFAULT_CONTAINER,
                    f"/opt/WebSyn/{SITE}/instance_seed/{SITE}.db", cache)


def acquire_instance(container=None):
    container = container or DEFAULT_CONTAINER
    out = Path("/tmp") / f"spothero_verify_instance_{container}.db"
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
        pk = [c[1] for c in db.execute(f"PRAGMA table_info({table})") if c[5]] \
            or cols[:1]
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


def check_seed_contract(judge, initial_db):
    judge.check("initial_is_seed_schema", schema_digest(initial_db) == SCHEMA_SHA256,
                "initial_db schema digest must match the frozen seed")
    judge.check("initial_is_seed_rows", rows_digest(initial_db) == SEED_ROWS_SHA256,
                "initial_db row digest must match the frozen seed")


def check_only_tables_changed(judge, initial_db, after_db, allowed):
    """Every table outside `allowed` must be row-identical; allowed tables are
    checked by the task verifier with exact deltas."""
    check_seed_contract(judge, initial_db)
    judge.check("after_schema_unchanged", schema_digest(after_db) == schema_digest(initial_db))
    for t in TABLES:
        if t in allowed:
            continue
        added, removed, changed = table_diff(initial_db, after_db, t)
        judge.check(f"table_{t}_untouched",
                    not (added or removed or changed),
                    f"added={list(added)[:3]} removed={list(removed)[:3]} "
                    f"changed={list(changed)[:3]}")


# ------------------------------------------------------- stateful delta helpers
def check_reservations_delta(judge, initial_db, after_db, answer,
                            expect_added=None, expect_updated=None):
    """Unified reservations after-state check.

    expect_added: None (no new rows) or a dict of pinned fields for the single
      new row: facility_id, kind, total, email, starts, ends, promo, user_id,
      parking_pass, status. The answer's reservation code must equal the new
      row's code.
    expect_updated: {code: {field: expected_value}} — exactly these rows may
      change, each with exactly these fields changing to these values.
    """
    expect_updated = expect_updated or {}
    added, removed, changed = table_diff(initial_db, after_db, "reservations")
    judge.check("reservations_no_removal", not removed, f"removed={list(removed)[:3]}")
    judge.check("reservations_added_exact",
                len(added) == (0 if expect_added is None else 1),
                f"added={[dict(r) for r in added.values()][:2]}")
    if expect_added is not None:
        codes = RES_CODE_RX.findall(answer or "")
        judge.check("answer_has_reservation_code", bool(codes),
                    f"codes found in answer: {codes}")
        if len(added) == 1 and codes:
            row = next(iter(added.values()))
            judge.check("new_res_code_matches_answer", row["code"] in codes,
                        f"row code={row['code']!r} answer codes={codes}")
            spec = expect_added
            for key, want in spec.items():
                if key == "total":
                    judge.check("new_res_total",
                                abs((row["total"] or 0) - want) < 0.005,
                                f"total={row['total']} expected {want}")
                elif key == "starts":
                    judge.check("new_res_starts", str(row["starts"]).startswith(want),
                                f"starts={row['starts']!r} expected prefix {want!r}")
                elif key == "ends":
                    judge.check("new_res_ends", str(row["ends"]).startswith(want),
                                f"ends={row['ends']!r} expected prefix {want!r}")
                elif key == "promo":
                    judge.check("new_res_promo",
                                (row["promo_code"] or "") == want,
                                f"promo_code={row['promo_code']!r} "
                                f"expected {want!r}")
                elif key == "user_id":
                    judge.check("new_res_user", row["user_id"] == want,
                                f"user_id={row['user_id']!r} expected {want!r}")
                else:
                    judge.check(f"new_res_{key}", row[key] == want,
                                f"{key}={row[key]!r} expected {want!r}")
    # updated rows: exact codes and exact changed-field maps
    changed_by_code = {}
    for k, (before, after) in changed.items():
        changed_by_code[before["code"]] = (before, after)
    judge.check("reservations_updated_codes",
                set(changed_by_code) == set(expect_updated),
                f"updated={sorted(changed_by_code)} expected={sorted(expect_updated)}")
    for code, fields in expect_updated.items():
        if code not in changed_by_code:
            continue
        before, after = changed_by_code[code]
        got = {c for c in before if before[c] != after[c]}
        judge.check(f"res_{code}_fields_exact", got == set(fields),
                    f"changed fields {sorted(got)} expected {sorted(fields)}")
        for f, want in fields.items():
            judge.check(f"res_{code}_{f}", after[f] == want,
                        f"{f}: {before[f]!r} -> {after[f]!r} expected {want!r}")


def check_any_new_reservation(judge, initial_db, after_db, answer,
                              facility_ids, kind, total, email, starts=None,
                              ends=None):
    """Like check_reservations_delta's added path but the new row's facility
    may be any of `facility_ids` (tied-cheapest ambiguity)."""
    added, removed, changed = table_diff(initial_db, after_db, "reservations")
    judge.check("reservations_no_removal", not removed, f"removed={list(removed)[:3]}")
    judge.check("reservations_no_mutation", not changed, f"changed={list(changed)[:3]}")
    judge.check("reservations_one_added", len(added) == 1,
                f"added={[dict(r) for r in added.values()][:2]}")
    codes = RES_CODE_RX.findall(answer or "")
    judge.check("answer_has_reservation_code", bool(codes),
                f"codes found in answer: {codes}")
    if len(added) != 1 or not codes:
        return None
    row = next(iter(added.values()))
    judge.check("new_res_code_matches_answer", row["code"] in codes,
                f"row code={row['code']!r} answer codes={codes}")
    judge.check("new_res_facility_in_tied_set", row["facility_id"] in facility_ids,
                f"facility_id={row['facility_id']} expected one of {facility_ids}")
    judge.check("new_res_kind", row["kind"] == kind, f"kind={row['kind']!r}")
    judge.check("new_res_total", abs((row["total"] or 0) - total) < 0.005,
                f"total={row['total']} expected {total}")
    judge.check("new_res_email", row["email"] == email, f"email={row['email']!r}")
    if starts is not None:
        judge.check("new_res_starts", str(row["starts"]).startswith(starts),
                    f"starts={row['starts']!r}")
    if ends is not None:
        judge.check("new_res_ends", str(row["ends"]).startswith(ends),
                    f"ends={row['ends']!r}")
    judge.check("new_res_status", row["status"] == "upcoming")
    judge.check("new_res_guest", row["user_id"] is None,
                f"user_id={row['user_id']!r}")
    return row["code"]


def check_payment_methods_delta(judge, initial_db, after_db,
                                added_spec, removed_last4, default_last4):
    """payment_methods: exactly one added card matching `added_spec`
    (user_id, brand, last4, exp_month, exp_year, label), the card ending in
    `removed_last4` for that user deleted, and the new card is the default."""
    added, removed, changed = table_diff(initial_db, after_db, "payment_methods")
    judge.check("pm_one_added", len(added) == 1,
                f"added={[dict(r) for r in added.values()][:2]}")
    judge.check("pm_removed_exact",
                {r["last4"] for r in removed.values()} == {removed_last4},
                f"removed={[r['last4'] for r in removed.values()]} "
                f"expected [{removed_last4}]")
    if len(added) != 1:
        return
    row = next(iter(added.values()))
    for key, want in added_spec.items():
        judge.check(f"pm_new_{key}", row[key] == want,
                    f"{key}={row[key]!r} expected {want!r}")
    judge.check("pm_removal_owner", len(removed) == 1 and all(r["user_id"] == added_spec["user_id"] for r in removed.values()))
    judge.check("pm_preserves_other_users", all(b["user_id"] == added_spec["user_id"] and a["is_default"] == 0 for b, a in changed.values()))
    # exactly two changed rows: the old default loses default, the removed one is gone
    judge.check("pm_changed_only_default_flags",
                all(set(c for c in b if b[c] != a[c]) <= {"is_default"}
                    for b, a in changed.values()),
                f"changed: {[{c: (b[c], a[c]) for c in b if b[c] != a[c]} for b, a in changed.values()]}")
    defaults_after = [dict(r) for r in after_db.execute(
        "SELECT * FROM payment_methods WHERE user_id=? AND is_default=1",
        (added_spec["user_id"],))]
    judge.check("pm_single_default",
                len(defaults_after) == 1 and defaults_after[0]["last4"] == default_last4,
                f"defaults after: {defaults_after}")


def check_profile_delta(judge, initial_db, after_db, user_id, fields):
    """users: exactly one row changed, only the named profile fields."""
    added, removed, changed = table_diff(initial_db, after_db, "users")
    judge.check("users_no_removal", not removed, f"removed={list(removed)[:3]}")
    judge.check("users_no_addition", not added, f"added={list(added)[:3]}")
    judge.check("users_one_changed", len(changed) == 1,
                f"changed={list(changed)[:3]}")
    if len(changed) != 1:
        return
    before, after = next(iter(changed.values()))
    judge.check("profile_user", before["id"] == user_id, f"user id={before['id']}")
    diff_fields = {c for c in before if before[c] != after[c]}
    judge.check("profile_only_named_fields", diff_fields == set(fields),
                f"changed fields: {diff_fields} expected {set(fields)}")
    for f, want in fields.items():
        judge.check(f"profile_{f}", after[f] == want,
                    f"{f}: {before[f]!r} -> {after[f]!r} expected {want!r}")


def check_favorites_delta(judge, initial_db, after_db, user_id,
                          expect_pairs, allow_readd=()):
    """favorites for `user_id`: the after-state must contain exactly
    `expect_pairs` (user_id, facility_id) — rows may be re-added with new ids
    (the save button toggles), so membership is compared, not row ids."""
    added, removed, changed = table_diff(initial_db, after_db, "favorites")
    judge.check("favorites_no_mutation", not changed, f"changed={list(changed)[:3]}")
    seed_pairs = {(r["user_id"], r["facility_id"])
                  for r in initial_db.execute(
                      "SELECT * FROM favorites WHERE user_id=?", (user_id,))}
    after_pairs = {(r["user_id"], r["facility_id"])
                   for r in after_db.execute(
                       "SELECT * FROM favorites WHERE user_id=?", (user_id,))}
    want = set(expect_pairs)
    judge.check("favorites_exact_membership", after_pairs == want,
                f"after={sorted(after_pairs)} expected={sorted(want)} "
                f"(seed had {sorted(seed_pairs)})")
    readded = {k: v for k, v in added.items()
               if (v["user_id"], v["facility_id"]) in seed_pairs}
    fresh = {k: v for k, v in added.items()
             if (v["user_id"], v["facility_id"]) not in seed_pairs}
    judge.check("favorites_readd_only_known",
                all((v["user_id"], v["facility_id"]) in allow_readd
                    for v in readded.values()),
                f"re-added pairs={[(v['user_id'], v['facility_id']) for v in readded.values()]}")
    return fresh


def check_new_user(judge, initial_db, after_db, email, username,
                   first_name, last_name):
    """Exactly one new users row with the expected identity; bcrypt hash is
    salted per run so only its format is pinned."""
    added, removed, changed = table_diff(initial_db, after_db, "users")
    judge.check("users_no_removal", not removed, f"removed={list(removed)[:3]}")
    judge.check("users_no_mutation", not changed, f"changed={list(changed)[:3]}")
    judge.check("users_one_added", len(added) == 1,
                f"added={[dict(r) for r in added.values()][:2]}")
    if len(added) != 1:
        return None
    row = next(iter(added.values()))
    pw = row["password_hash"]
    if isinstance(pw, bytes):
        pw = pw.decode("utf-8", "replace")
    judge.check("new_user_email", row["email"] == email, f"email={row['email']!r}")
    judge.check("new_user_username", row["username"] == username,
                f"username={row['username']!r}")
    judge.check("new_user_name", (row["first_name"], row["last_name"]) ==
                (first_name, last_name),
                f"name={row['first_name']!r} {row['last_name']!r}")
    judge.check("new_user_bcrypt_format", bool(BCRYPT_RX.match(pw or "")),
                f"password_hash format={str(pw)[:12]!r}…")
    return row["id"]


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
    sys.exit("import this module from verify_<task>.py (see make_verifiers.py)")
