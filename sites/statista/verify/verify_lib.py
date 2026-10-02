#!/usr/bin/env python3
"""verify_lib.py — deterministic verifier utilities for statista task
verification (review track, orch/review/statista).

Philosophy: DETERMINISTIC FIRST — same contract as the hardened reviewer
suites (``sites/sourceforge/verify/verify_lib.py``). No LLM call is
load-bearing; every check is regex / token / SQLite after-state.

  1. Package identity (fail-closed): task_id matches, ``terminated`` with
     ``agent_done``, non-empty final answer, every recorded URL on the same
     loopback origin AND port as ``start_url``, every referenced screenshot a
     decodable PNG.
  2. Navigation gates (anti knowledge-shortcut): the agent MUST have opened
     the on-site surfaces the task names (search results, statistic detail
     with the required chart/citation view, topic / report / outlook /
     industry / pricing pages, login / register, account favorites /
     downloads). A correct answer with no matching navigation is a
     memory-recall shortcut = FAIL.
  3. Answer check: affirmative token / phrase / number matching against
     frozen ground truth HARDCODED in each ``verify_N.py`` (never in
     tasks.jsonl).
  4. DB after-state: initial (seed) vs after (instance) SQLite snapshots.
     Read-only tasks require every table row-identical to the seed; stateful
     tasks require the exact allowed row delta and nothing else (a new
     registered user with a bcrypt hash, a favorite added / removed, a
     download event). The seed contract is pinned to the review container's
     deterministic build (PYTHONHASHSEED=0 app bootstrap, md5 d6302969…).

Input signature (per task):
  --run_dir DIR        agent trajectory dir: trajectory.json + screenshots/step_NNN.png
  --initial_db PATH    initial-state SQLite DB (default: <run_dir>/initial.db, else
                       instance_seed from the container)
  --after_db PATH      after-state  SQLite DB (default: <run_dir>/after.db, else live
                       instance DB from the container)
  --container NAME     docker container to fetch DBs from (default: $WH_CONTAINER or
                       wh-statista-review)
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

SITE = "statista"
DEFAULT_CONTAINER = os.environ.get("WH_CONTAINER", "wh-statista-review")

# ---------------------------------------------------------------- frozen seed contract
# Review container wh-statista-review, image webharbor:statista-review,
# seed built from the committed tree via the app bootstrap (PYTHONHASHSEED=0),
# md5 d630296967f55a225f98ad788bf26665, byte-reproducible across rebuilds.
TABLES = ("download_events", "favorites", "industries", "inquiries", "outlook_markets",
          "reports", "statistics", "topics", "users")
SEED_COUNTS = {"download_events": 12, "favorites": 15, "industries": 22,
               "inquiries": 0, "outlook_markets": 155, "reports": 11,
               "statistics": 459, "topics": 10, "users": 4}
# sha256 over sqlite_master (type, name, tbl_name, sql) of instance_seed/statista.db
# after the reviewer seed rebuild (regional chart recovery + inquiries table).
SCHEMA_SHA256 = "e3571669825df78e1748d07ee5e3f66184ad0f9d0d277a3e85693dcaa9c139a8"
# sha256 over every seed row (table-canonical, ORDER BY all columns).
SEED_ROWS_SHA256 = "3c51c0f27279fa9ec79dee96a42dcc2d3904dd5a973751dfc6ce1e8c0a899e71"
SEED_USERS = {  # email -> (id, display); identity columns never change
    "alice.j@test.com": (1, "Alice Johnson"),
    "bob.c@test.com": (2, "Bob Chen"),
    "carol.d@test.com": (3, "Carol Davis"),
    "david.k@test.com": (4, "David Kim"),
}
DEMO_PASSWORD = "TestPass123!"
BCRYPT_RX = re.compile(r"^\$2[aby]\$12\$[./A-Za-z0-9]{53}$")
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
    check_package(judge, traj, task_id)


def check_visited_path(judge, traj, name, pattern):
    hit = visited_path(traj, pattern)
    judge.check(name, hit, f"required path ~{pattern}"
                + ("" if hit else f" — visited: {[u.split('localhost')[-1] for u in trajectory_urls(traj)][:12]}"))


def check_answer_phrase(judge, answer, name, phrase, case_sensitive=False):
    hay = answer if case_sensitive else answer.casefold()
    needle = phrase if case_sensitive else phrase.casefold()
    hit = needle in hay
    import datetime
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            date = datetime.datetime.strptime(phrase, fmt)
        except ValueError:
            continue
        variants = [date.strftime(f) for f in ("%b %d, %Y", "%B %d, %Y", "%d %B %Y", "%Y-%m-%d", "%d/%m/%Y")]
        hit = hit or any(v.casefold() in hay or v.replace(" 0", " ").casefold() in hay for v in variants)
    judge.check(name, hit, f"answer must mention {phrase!r} or an equivalent date")


def _norm_num(s):
    s = re.sub(r"[,\s]", "", str(s)).strip(".,")
    return s.lower()


def _number_pattern(value):
    """Standalone number. ``3.2`` does not match ``13.2``, ``3.22``, or ``32.38``,
    and ``3`` does not match ``67.3`` or ``2025``. Thousands commas are optional."""
    canon = _norm_num(value)
    if "." in canon:
        whole, frac = canon.split(".", 1)
    else:
        whole, frac = canon, None
    if not whole or not re.fullmatch(r"\d+", whole):
        raise ValueError(f"not a number: {value!r}")
    groups = []
    rest = whole
    while rest:
        groups.append(rest[-3:])
        rest = rest[:-3]
    groups.reverse()
    body = groups[0] + "".join(f",?{part}" for part in groups[1:])
    if frac is not None:
        if not re.fullmatch(r"\d+", frac):
            raise ValueError(f"not a number: {value!r}")
        body += r"\." + frac
    # A sentence-final period is not another decimal place. ``3.2.`` still
    # matches 3.2; ``3.22`` and ``3.2.5`` do not.
    return re.compile(rf"(?<![\d.]){body}(?!\d)(?!\.\d)")


def _term_pattern(label):
    return re.compile(rf"(?<![A-Za-z0-9]){re.escape(label)}(?![A-Za-z0-9])", re.I)


def _spans(text, labels):
    found = []
    for label in labels or []:
        if not label:
            continue
        for match in _term_pattern(label).finditer(text):
            found.append((match.start(), match.end()))
    return found


def _gap(left, right):
    a0, a1 = left
    b0, b1 = right
    if a1 <= b0:
        return b0 - a1
    if b1 <= a0:
        return a0 - b1
    return 0


def _nearest_is_subject(origin, subjects, competitors, window):
    anchors = [(span, True) for span in subjects] + [(span, False) for span in competitors]
    if not anchors:
        return False
    distances = [(_gap(origin, span), is_subject) for span, is_subject in anchors]
    best = min(dist for dist, _ in distances)
    if best > window:
        return False
    return all(is_subject for dist, is_subject in distances if dist == best)


def _assertions(text):
    return re.split(r";|\n|(?<!\d)\.(?=\s|$)|(?<=\d)\.(?=\s+[A-Z])", text)


def _affirmed(text, start):
    prefix = text[:start]
    return not re.search(r"\b(?:not|never|incorrect|wrong|isn't|isnt)\b(?:\W+\w+){0,3}\W*$", prefix, re.I)


def number_bound(text, value, groups, window=220):
    pattern = _number_pattern(value)
    for segment in _assertions(text):
        for match in pattern.finditer(segment):
            origin = (match.start(), match.end())
            if _affirmed(segment, match.start()) and all(
                _nearest_is_subject(origin, _spans(segment, subjects), _spans(segment, competitors), window)
                for subjects, competitors in groups):
                return True
    return False


def phrase_bound(text, phrase, groups, window=220):
    for segment in _assertions(text):
        for match in _term_pattern(phrase).finditer(segment):
            origin = (match.start(), match.end())
            if _affirmed(segment, match.start()) and all(
                _nearest_is_subject(origin, _spans(segment, subjects), _spans(segment, competitors), window)
                for subjects, competitors in groups):
                return True
    return False


def context_window(text, anchor, must, must_not, window=80):
    for match in re.finditer(re.escape(anchor), text, re.I):
        segment = text[max(0, match.start() - window):match.end() + window]
        if all(_term_pattern(term).search(segment) for term in must) and all(
                not _term_pattern(term).search(segment) for term in must_not):
            return True
    return False


def check_answer_number(judge, answer, name, value, label=None, subjects=None,
                        competitors=None, groups=None, window=220):
    """Standalone number. When subjects/groups are set, the number must be
    nearer those subjects than the competing subjects."""
    if groups is None and subjects:
        groups = [(list(subjects), list(competitors or []))]
    if groups:
        found = number_bound(answer, value, groups, window=window)
        detail = f"answer must bind {value} to {groups}"
    else:
        found = bool(_number_pattern(value).search(answer))
        detail = f"answer must contain the standalone number {value}"
    if label:
        detail += f" ({label})"
    judge.check(name, found, detail)


def check_answer_any(judge, answer, name, variants, label=""):
    """Phrase variants use word boundaries. Numeric variants must be standalone
    tokens, so ``3`` does not match ``67.3`` or ``2025``."""
    hit = False
    for variant in variants:
        text = str(variant)
        if re.fullmatch(r"[0-9][0-9,]*(?:\.[0-9]+)?", text):
            hit = bool(_number_pattern(text).search(answer))
        else:
            hit = bool(_term_pattern(text).search(answer))
        if hit:
            break
    judge.check(name, hit, f"answer must mention one of {variants} {label}")


def check_bound_number(judge, answer, name, value, groups, window=220):
    judge.check(name, number_bound(answer, value, groups, window=window),
                f"answer must bind {value} to {groups}")


def check_bound_any_number(judge, answer, name, values, groups, window=220):
    found = any(number_bound(answer, value, groups, window=window) for value in values)
    judge.check(name, found, f"answer must bind one of {values} to {groups}")


def check_bound_phrase(judge, answer, name, phrase, groups, window=220):
    judge.check(name, phrase_bound(answer, phrase, groups, window=window),
                f"answer must bind {phrase!r} to {groups}")


def check_context_window(judge, answer, name, anchor, must, must_not, window=80):
    judge.check(name, context_window(answer, anchor, must, must_not, window=window),
                f"near {anchor!r} need {must} and not {must_not}")


# ---------------------------------------------------------------- navigation
def visited_path(traj, pattern):
    rx = re.compile(pattern, re.I)
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
    cache = Path(cache or os.environ.get("STATISTA_TEST_SEED_DB")
                 or Path("/tmp/statista_verify_seed.db"))
    if cache.is_file():
        return cache
    return fetch_db(container or DEFAULT_CONTAINER,
                    f"/opt/WebSyn/{SITE}/instance_seed/{SITE}.db", cache)


def acquire_instance(container=None):
    container = container or DEFAULT_CONTAINER
    out = Path("/tmp") / f"statista_verify_instance_{container}.db"
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


# ------------------------------------------------------- stateful delta helpers
def check_new_user(judge, initial_db, after_db, email, username, display,
                   account_type="Basic", created_at="2026-09-26 12:00:00"):
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
    judge.check("new_user_display", row["display_name"] == display,
                f"display={row['display_name']!r}")
    judge.check("new_user_account_type", row["account_type"] == account_type,
                f"account_type={row['account_type']!r}")
    created = str(row["created_at"]).split(".")[0]
    judge.check("new_user_created_at", created == created_at,
                f"created_at={row['created_at']!r}")
    judge.check("new_user_bcrypt_format", bool(BCRYPT_RX.match(pw or "")),
                f"password_hash format={str(pw)[:12]!r}…")
    return row["id"]


def check_favorites_delta(judge, initial_db, after_db, expect_added,
                          expect_removed):
    """expect_added / expect_removed: lists of (user_id, stat_id, report_id)."""
    added, removed, changed = table_diff(initial_db, after_db, "favorites")
    judge.check("favorites_no_mutation", not changed, f"changed={list(changed)[:3]}")
    norm = lambda rows: {(r["user_id"], r["stat_id"], r["report_id"])
                         for r in rows.values()}
    judge.check("favorites_added_exact",
                norm(added) == set(expect_added),
                f"added={norm(added)} expected={set(expect_added)}")
    judge.check("favorites_removed_exact",
                norm(removed) == set(expect_removed),
                f"removed={norm(removed)} expected={set(expect_removed)}")


def check_download_added(judge, initial_db, after_db, user_id, stat_id=None,
                         report_id=None, fmt=None):
    added, removed, changed = table_diff(initial_db, after_db, "download_events")
    judge.check("downloads_no_removal", not removed, f"removed={list(removed)[:3]}")
    judge.check("downloads_no_mutation", not changed, f"changed={list(changed)[:3]}")
    judge.check("downloads_one_added", len(added) == 1,
                f"added={[dict(r) for r in added.values()][:2]}")
    if len(added) != 1:
        return
    row = next(iter(added.values()))
    judge.check("download_user", row["user_id"] == user_id, f"user_id={row['user_id']}")
    if stat_id is not None:
        judge.check("download_stat", row["stat_id"] == stat_id, f"stat_id={row['stat_id']}")
    if report_id is not None:
        judge.check("download_report", row["report_id"] == report_id,
                    f"report_id={row['report_id']}")
    if fmt is not None:
        judge.check("download_fmt", row["fmt"] == fmt, f"fmt={row['fmt']!r}")
    judge.check("download_created_at",
                str(row["created_at"]).split(".")[0] == "2026-09-26 12:00:00",
                f"created_at={row['created_at']!r}")


def _row_user_id(initial_db, email):
    row = initial_db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    return None if row is None else row["id"]


def check_account_delta(judge, initial_db, after_db, spec):
    """Stateful account contract.

    ``require_new_user`` pins a new Basic account (email + username).
    ``allow_new_user`` accepts either that new account or an existing seed
    user. Favorite and download rows must belong to the acting user.
    ``fav_del`` is a list of (user_id, stat_id, report_id). ``fav_add`` is a
    list of (stat_id, report_id) for the acting user. ``download`` is
    {stat_id, report_id, fmt}.
    """
    email = spec.get("email")
    username = spec.get("username")
    require_new = spec.get("require_new_user", False)
    allow_new = spec.get("allow_new_user", False) or require_new
    fav_add = spec.get("fav_add")
    fav_del = spec.get("fav_del")
    download = spec.get("download")
    allowed = set()
    if allow_new:
        allowed.add("users")
    if fav_add is not None or fav_del is not None:
        allowed.add("favorites")
    if download is not None:
        allowed.add("download_events")
    check_only_tables_changed(judge, initial_db, after_db, allowed)

    added, removed, changed = table_diff(initial_db, after_db, "users")
    judge.check("users_no_removal", not removed, f"removed={list(removed)[:3]}")
    judge.check("users_no_mutation", not changed, f"changed={list(changed)[:3]}")
    actor_id = None
    if require_new:
        judge.check("users_one_added", len(added) == 1, f"added={len(added)}")
    elif not allow_new:
        judge.check("users_unchanged", len(added) == 0, f"added={len(added)}")
    else:
        judge.check("users_at_most_one_added", len(added) <= 1, f"added={len(added)}")
    if len(added) == 1:
        row = next(iter(added.values()))
        pw = row["password_hash"]
        if isinstance(pw, bytes):
            pw = pw.decode("utf-8", "replace")
        if email:
            judge.check("new_user_email", row["email"] == email, f"email={row['email']!r}")
        else:
            judge.check("new_user_email_present", bool(row["email"]), "email empty")
        if username:
            judge.check("new_user_username", row["username"] == username,
                        f"username={row['username']!r}")
        judge.check("new_user_account_type", row["account_type"] == "Basic",
                    f"account_type={row['account_type']!r}")
        created = str(row["created_at"]).split(".")[0]
        judge.check("new_user_created_at", created == "2026-09-26 12:00:00",
                    f"created_at={row['created_at']!r}")
        judge.check("new_user_bcrypt_format", bool(BCRYPT_RX.match(pw or "")),
                    f"password_hash format={str(pw)[:12]!r}…")
        judge.check("new_user_display_present", bool(str(row["display_name"] or "").strip()),
                    "display name empty")
        actor_id = row["id"]
    elif email and not require_new:
        actor_id = _row_user_id(initial_db, email)
        judge.check("actor_exists", actor_id is not None, f"email={email}")

    if fav_add is not None or fav_del is not None:
        f_added, f_removed, f_changed = table_diff(initial_db, after_db, "favorites")
        judge.check("favorites_no_mutation", not f_changed, f"changed={list(f_changed)[:3]}")
        norm = lambda rows: {(r["user_id"], r["stat_id"], r["report_id"]) for r in rows.values()}
        if fav_del is not None:
            judge.check("favorites_removed_exact", norm(f_removed) == set(map(tuple, fav_del)),
                        f"removed={norm(f_removed)} expected={set(map(tuple, fav_del))}")
        else:
            judge.check("favorites_no_removal", not f_removed, f"removed={norm(f_removed)}")
        if fav_add is not None:
            if actor_id is None and len(f_added) == 1 and not require_new and not email:
                only = next(iter(f_added.values()))
                actor_id = only["user_id"]
                judge.check("actor_is_seed_user",
                            _row_user_id_exists(initial_db, actor_id),
                            f"user_id={actor_id}")
            expected = {(actor_id, stat_id, report_id) for stat_id, report_id in fav_add}
            judge.check("favorites_added_exact", norm(f_added) == expected,
                        f"added={norm(f_added)} expected={expected}")
        else:
            judge.check("favorites_no_addition", not f_added, f"added={norm(f_added)}")

    if download is not None:
        if actor_id is None:
            d_added, _, _ = table_diff(initial_db, after_db, "download_events")
            if len(d_added) == 1 and not require_new and not email:
                actor_id = next(iter(d_added.values()))["user_id"]
        check_download_added(
            judge, initial_db, after_db,
            user_id=actor_id,
            stat_id=download.get("stat_id"),
            report_id=download.get("report_id"),
            fmt=download.get("fmt"))


def _row_user_id_exists(initial_db, user_id):
    row = initial_db.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    return row is not None


def check_inquiry(judge, initial_db, after_db, name, email, needles):
    check_only_tables_changed(judge, initial_db, after_db, {"inquiries"})
    added, removed, changed = table_diff(initial_db, after_db, "inquiries")
    judge.check("inquiries_no_removal", not removed, f"removed={list(removed)[:2]}")
    judge.check("inquiries_no_mutation", not changed, f"changed={list(changed)[:2]}")
    judge.check("inquiries_one_added", len(added) == 1, f"added={len(added)}")
    if len(added) != 1:
        return
    row = next(iter(added.values()))
    judge.check("inquiry_name", row["name"] == name, f"name={row['name']!r}")
    judge.check("inquiry_email", str(row["email"]).casefold() == email.casefold(),
                f"email={row['email']!r}")
    message = str(row["message"] or "").casefold()
    for needle in needles:
        judge.check(f"inquiry_message_{needle}", needle.casefold() in message,
                    f"message must mention {needle!r}")
    judge.check("inquiry_created_at",
                str(row["created_at"]).split(".")[0] == "2026-09-26 12:00:00",
                f"created_at={row['created_at']!r}")


def apply_spec(judge, traj, initial_db, after_db, spec, task_id):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, task_id)
    for name, pattern in spec.get("gates") or []:
        check_visited_path(judge, traj, name, pattern)
    for check in spec.get("answers") or []:
        kind = check[0]
        if kind == "phrase":
            check_answer_phrase(judge, answer, check[1], check[2])
        elif kind == "any_phrase":
            check_answer_any(judge, answer, check[1], check[2])
        elif kind == "bound":
            check_bound_number(judge, answer, check[1], check[2], check[3])
        elif kind == "bound_any":
            check_bound_any_number(judge, answer, check[1], check[2], check[3])
        elif kind == "bound_phrase":
            check_bound_phrase(judge, answer, check[1], check[2], check[3])
        elif kind == "window":
            anchor, must, must_not = check[2], check[3], check[4]
            window = check[5] if len(check) > 5 else 80
            check_context_window(judge, answer, check[1], anchor, must, must_not, window)
        else:
            judge.check(f"known_check_{kind}", False, f"unknown answer check {kind}")
    state = spec.get("state")
    if state is None:
        check_read_only(judge, initial_db, after_db)
    elif state.get("inquiry"):
        info = state["inquiry"]
        check_inquiry(judge, initial_db, after_db, info["name"], info["email"], info["needles"])
    else:
        check_account_delta(judge, initial_db, after_db, state)


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
