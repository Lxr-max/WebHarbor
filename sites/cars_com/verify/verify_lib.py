#!/usr/bin/env python3
"""verify_lib.py — deterministic verification utilities for cars_com tasks.

Philosophy: DETERMINISTIC FIRST, zero LLM.
  1. Trajectory identity + navigation gates (anti knowledge-shortcut): the
     agent MUST have opened the on-site pages the task requires; a correct
     answer with no matching navigation is a memory-recall shortcut = FAIL.
  2. Answer checks: token / price / count containment against frozen ground
     truth (hardcoded in the per-task verifiers — never in tasks.jsonl).
  3. DB after-state checks (stateful tasks): query the SQLite instance DB
     directly — the strongest deterministic signal (saved-car rows, saved
     searches, offer requests, registered users).
  4. Seed snapshot contract: initial_db must be the frozen deterministic seed
     (schema sha + per-table counts + rows sha) so tampered snapshots fail.

NOTE ON GROUND TRUTH: the counts and prices frozen below were transcribed from
the reviewer's independent two-round Playwright walkthrough (2026-09-30) and
cross-checked against the frozen seed DB. The SERP result counts assume the
filter-form fix (see the review report: `_listing_filters` was missing the
empty-value guard on exterior_color_slugs / fuel_slugs / transmission_slugs /
drivetrain_slugs, and the model-page links emitted `models=` instead of
`models[]`); the frozen values are the post-fix semantics — they equal what
the sort-form URL (which carries only non-empty params) renders today.

Input signature (per task):
  --run_dir DIR      agent run dir: trajectory.json + screenshots/step_NNN.png
  --initial_db PATH  initial-state SQLite DB (default: <run_dir>/initial.db,
                     else docker-copied from the container's instance_seed)
  --after_db PATH    after-state  SQLite DB (default: <run_dir>/after.db,
                     else docker-copied from the container's live instance)
  --container NAME   docker container to fetch DBs from
                     (default: $WH_CONTAINER or wh-cars-com-review-r1)
Output: JSON {task_id, pass, reason, evidence[]} to stdout; exit 0 PASS / 1 FAIL.
"""
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
import ipaddress

SITE = "cars_com"
DEFAULT_CONTAINER = os.environ.get("WH_CONTAINER", "wh-cars-com-review-r1")

# ---------------------------------------------------------------- frozen seed contract
TABLES = ("users", "dealers", "model_pages", "compare_pairs",
          "valuation_vehicles", "listings", "saved_cars", "saved_searches",
          "offer_requests")
SEED_COUNTS = {"users": 4, "dealers": 190, "model_pages": 23, "compare_pairs": 9,
               "valuation_vehicles": 8, "listings": 736, "saved_cars": 10,
               "saved_searches": 5, "offer_requests": 0}
# sha256 over sqlite_master (type, name, tbl_name, sql) of instance_seed/cars_com.db.
SCHEMA_SHA256 = "29d2fcfc17ebe231321b203507e3939d8e67f655ba40fee59060c9e2a2ddec76"
# sha256 over every seed row (table-canonical, ORDER BY all columns). The seed
# is built deterministically at image build time (PYTHONHASHSEED=0) and
# reproduces byte-identically on every build; md5 of the seed file itself is
# 140ef39cbf144d035e593016ea0d5e87 (independently re-built twice by the
# reviewer: two no-cache docker builds produced the same md5).
SEED_ROWS_SHA256 = "f04bba1affb80ec0bdc07c8fa7bd7cea0bd5e2b34473b9fc5e185c27afca4454"
SEED_USERS = {  # email -> (id, display_name); identity columns never change
    "alice.j@test.com": (1, "Alice Johnson"),
    "bob.c@test.com": (2, "Bob Chen"),
    "carol.d@test.com": (3, "Carol Davis"),
    "dana.k@test.com": (4, "Dana Kim"),
}
DEMO_PASSWORD = "TestPass123!"


# ---------------------------------------------------------------- trajectory
def load_run(run_dir):
    d = Path(run_dir)
    traj = json.loads((d / "trajectory.json").read_text(encoding="utf-8"))
    if not isinstance(traj, dict):
        raise ValueError("trajectory.json must contain a JSON object")
    traj["_run_dir"] = d
    shots_dir = d / "screenshots"
    traj["_shots"] = ({p.name: p for p in sorted(shots_dir.glob("step_*.png"))}
                      if shots_dir.is_dir() else {})
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
    host = parsed.hostname.casefold()
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _same_local_origin(url, start_url):
    observed, start = urlparse(str(url or "")), urlparse(str(start_url or ""))
    return (observed.scheme == "http" and start.scheme == "http"
            and observed.hostname is not None and start.hostname is not None
            and not observed.username and not observed.password
            and not start.username and not start.password
            and observed.hostname.casefold() == start.hostname.casefold())


def navigated_to(traj, substr, times=1):
    return sum(1 for u in trajectory_urls(traj) if substr in u) >= times


def navigated_to_path(traj, expected_path):
    for u in trajectory_urls(traj):
        try:
            p = urlparse(u)
        except ValueError:
            continue
        if p.path == expected_path:
            return True
    return False


def input_texts(traj):
    """All text the agent typed into form fields (fill/type actions)."""
    out = []
    for step in traj.get("steps") or []:
        if not isinstance(step, dict):
            continue
        action = str(step.get("action") or "").lower()
        if action not in {"input", "type", "fill", "input_text", "type_text",
                          "check", "select"}:
            continue
        params = step.get("params") or {}
        for v in params.values():
            if isinstance(v, str):
                out.append(v)
        for k in ("observed_text", "observed_text_after"):
            txt = step.get(k)
            if isinstance(txt, str):
                out.append(txt)
    return out


def entered_identity(traj, email):
    texts = " ".join(input_texts(traj))
    return email.lower() in texts.lower()


def screenshots_decode(traj):
    """Decode every referenced screenshot; a PNG signature alone is insufficient.

    Prefers a full Pillow decode (the agent_demo env ships Pillow); if Pillow
    is unavailable in the calling interpreter, falls back to strict PNG
    framing checks (magic + IHDR presence + IEND trailer) so a missing or
    truncated capture still fails while healthy PNGs pass.
    """
    shots = traj.get("_shots", {})
    referenced = {step[key] for step in traj.get("steps", [])
                  for key in ("screenshot", "screenshot_before", "screenshot_after")
                  if step.get(key)}
    if not referenced:
        return False, "no referenced screenshots"
    try:
        from PIL import Image
    except ImportError:
        bad = []
        for name in referenced:
            path = shots.get(name)
            try:
                if path is None:
                    raise ValueError("missing screenshot")
                data = Path(path).read_bytes()
                if not (data[:8] == b"\x89PNG\r\n\x1a\n" and b"IHDR" in data[:33]
                        and data.rstrip().endswith(b"IEND\xaeB`\x82")):
                    raise ValueError("not a well-framed PNG")
            except (OSError, ValueError):
                bad.append(name)
        return not bad, (f"{len(referenced)} PNGs framing-checked (Pillow unavailable)"
                         if not bad else f"bad framing/missing: {bad[:4]}")
    bad = []
    for name in referenced:
        path = shots.get(name)
        try:
            if path is None:
                raise ValueError("missing screenshot")
            with Image.open(path) as image:
                if image.format != "PNG":
                    raise ValueError("not PNG")
                image.verify()
            with Image.open(path) as image:
                image.load()
        except (OSError, ValueError, SyntaxError):
            bad.append(name)
    return not bad, (f"{len(referenced)} PNGs decoded" if not bad else f"undecodable/missing: {bad[:4]}")


# ---------------------------------------------------------------- answer matching
def norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().casefold()


def contains_all(final, tokens):
    f = norm(final)
    return all(norm(t) in f for t in tokens)


def contains_any(final, tokens):
    f = norm(final)
    return any(norm(t) in f for t in tokens)


def contains_amount(final, amount, tol=0.01):
    """The answer must state the given amount, tolerating US$/$/comma forms."""
    text = str(final or "")
    pat = re.compile(r"(?:us)?\$\s*([\d,]+(?:\.\d+)?)", re.I)
    for m in pat.finditer(text):
        try:
            val = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        if abs(val - float(amount)) <= tol:
            return True
    for m in re.finditer(r"\b(\d[\d,]*\.\d{1,2})\b", text):
        try:
            val = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        if abs(val - float(amount)) <= tol:
            return True
    return False


def contains_int(final, value):
    """The answer must state the integer (word-boundary, comma-tolerant)."""
    text = str(final or "")
    v = str(int(value))
    for m in re.finditer(r"\b\d[\d,]*\b", text):
        if m.group(0).replace(",", "") == v:
            return True
    words = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
             6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
             11: "eleven", 12: "twelve"}
    if value in words and re.search(rf"\b{words[value]}\b", text, re.I):
        return True
    return False


def contains_price(final, value):
    """The answer must state the given price as a $ amount (comma-tolerant)."""
    text = str(final or "")
    v = str(int(value))
    for m in re.finditer(r"(?:us)?\$\s*([\d,]+)", text, re.I):
        if m.group(1).replace(",", "") == v:
            return True
    return False


def observed_text(traj):
    """Concatenated observed page text across steps (for on-page fact gates)."""
    parts = []
    for step in traj.get("steps") or []:
        if not isinstance(step, dict):
            continue
        for k in ("observed_text", "observed_text_after", "page_text"):
            txt = step.get(k)
            if isinstance(txt, str):
                parts.append(txt)
    for k in ("final_observed_text",):
        txt = traj.get(k)
        if isinstance(txt, str):
            parts.append(txt)
    return "\n".join(parts)


def page_showed(traj, tokens):
    """Some observed page in the trajectory visibly contained every token."""
    hay = norm(observed_text(traj))
    return all(norm(t) in hay for t in tokens)


# ---------------------------------------------------------------- DB plumbing
def db_query(db_path, sql, params=()):
    if not db_path:
        return []
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(sql, params)]
    finally:
        con.close()


def schema_sha(db_path):
    con = sqlite3.connect(str(db_path))
    try:
        h = hashlib.sha256()
        for r in con.execute("SELECT type, name, tbl_name, sql FROM sqlite_master "
                             "ORDER BY type, name"):
            h.update(("\x1f".join(str(x) for x in r)).encode())
        return h.hexdigest()
    finally:
        con.close()


def table_counts(db_path):
    con = sqlite3.connect(str(db_path))
    try:
        return {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                for t in TABLES}
    finally:
        con.close()


def rows_sha(db_path):
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        h = hashlib.sha256()
        for t in TABLES:
            cols = [c[1] for c in con.execute(f'PRAGMA table_info("{t}")')]
            order = ", ".join(f'"{c}"' for c in cols)
            for r in con.execute(f'SELECT * FROM "{t}" ORDER BY {order}'):
                h.update((t + "\x1f" + "\x1f".join(repr(x) for x in tuple(r))
                          + "\x1e").encode())
        return h.hexdigest()
    finally:
        con.close()


def validate_snapshot_contract(initial_db):
    if schema_sha(initial_db) != SCHEMA_SHA256:
        raise ValueError(f"initial_db schema sha mismatch: {schema_sha(initial_db)}")
    counts = table_counts(initial_db)
    if counts != SEED_COUNTS:
        raise ValueError(f"initial_db table counts mismatch: {counts!r}")
    if rows_sha(initial_db) != SEED_ROWS_SHA256:
        raise ValueError("initial_db is not the frozen cars_com seed "
                         "(rows sha mismatch)")


def fetch_db(container, kind):
    """kind: 'instance' (after-state) or 'instance_seed' (initial-state)."""
    src = f"{container}:/opt/WebSyn/{SITE}/{kind}/{SITE}.db"
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    r = subprocess.run(["docker", "cp", src, path], capture_output=True, text=True)
    if r.returncode != 0:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise RuntimeError(f"docker cp {src} failed: {r.stderr.strip()[:200]}")
    return path


def resolve_snapshots(args, task_id):
    run_dir = Path(args.run_dir)
    initial = args.initial_db or str(run_dir / "initial.db")
    if not Path(initial).exists():
        initial = fetch_db(args.container, "instance_seed")
    after = args.after_db or str(run_dir / "after.db")
    if not Path(after).exists():
        after = fetch_db(args.container, "instance")
    validate_snapshot_contract(initial)
    return initial, after


# ---------------------------------------------------------------- deltas
def rows_sha_for(db_path, table):
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        cols = [c[1] for c in con.execute(f'PRAGMA table_info("{table}")')]
        order = ", ".join(f'"{c}"' for c in cols)
        h = hashlib.sha256()
        for r in con.execute(f'SELECT * FROM "{table}" ORDER BY {order}'):
            h.update(("\x1f".join(repr(x) for x in tuple(r)) + "\x1e").encode())
        return h.hexdigest()
    finally:
        con.close()


def changed_tables(initial_db, after_db, tables=None):
    changed = []
    for t in (tables or TABLES):
        if rows_sha_for(initial_db, t) != rows_sha_for(after_db, t):
            changed.append(t)
    return tuple(changed)


# ---------------------------------------------------------------- domain helpers
def user_by_email(db, email):
    rows = db_query(db, "SELECT id, email, display_name, is_benchmark FROM "
                        "users WHERE email=?", (email.lower(),))
    return rows[0] if rows else None


def saved_car_ids(db, email):
    rows = db_query(db,
        "SELECT sc.listing_id FROM saved_cars sc JOIN users u ON u.id=sc.user_id "
        "WHERE u.email=? ORDER BY sc.id", (email.lower(),))
    return [r["listing_id"] for r in rows]


def saved_searches_for(db, email):
    return db_query(db,
        "SELECT ss.name, ss.alert_frequency, ss.query_string FROM saved_searches ss "
        "JOIN users u ON u.id=ss.user_id WHERE u.email=? ORDER BY ss.id",
        (email.lower(),))


def offer_requests_for(db, email):
    return db_query(db,
        "SELECT o.* FROM offer_requests o JOIN users u ON u.id=o.user_id "
        "WHERE u.email=? ORDER BY o.id", (email.lower(),))


def new_users(initial_db, after_db):
    """Non-benchmark users present after but not in the seed."""
    before = {r["email"] for r in db_query(initial_db, "SELECT email FROM users")}
    rows = db_query(after_db, "SELECT id, email, display_name, is_benchmark "
                              "FROM users")
    return [r for r in rows if r["email"] not in before
            and not r.get("is_benchmark")]


# ---------------------------------------------------------------- judge harness
class Judge:
    def __init__(self, task_id, no_llm=False):
        self.task_id = task_id
        self.ok = True
        self.reason = ""
        self.evidence = []

    def check(self, name, cond, evidence=""):
        if cond:
            self.evidence.append(f"[PASS] {name}: {evidence}")
        else:
            self.ok = False
            if not self.reason:
                self.reason = name
            self.evidence.append(f"[FAIL] {name}: {evidence}")
        return bool(cond)

    def emit(self):
        print(json.dumps({"task_id": self.task_id, "pass": self.ok,
                          "reason": self.reason, "evidence": self.evidence},
                         indent=2))
        sys.exit(0 if self.ok else 1)


def fail_closed(task_id, reason, detail=""):
    print(json.dumps({"task_id": task_id, "pass": False, "reason": reason,
                      "evidence": [f"[FAIL] {reason}: {detail}"]}, indent=2))
    sys.exit(1)


# ---------------------------------------------------------------- shared checks
def check_trajectory_identity(judge, traj, task_id, require_answer=True):
    answer = final_answer(traj)
    if require_answer:
        judge.check("final_answer_nonempty", bool(answer),
                    f"final_answer={answer[:80]!r}")
    judge.check("trajectory_task_matches",
                str(traj.get("task_id") or "").strip() == task_id,
                f"expected_task_id={task_id!r}, observed_task_id={traj.get('task_id')!r}")
    judge.check("trajectory_completed",
                traj.get("terminated") is True
                and traj.get("termination_reason") == "agent_done",
                f"terminated={traj.get('terminated')!r}, "
                f"reason={traj.get('termination_reason')!r}")
    steps = traj.get("steps")
    judge.check("trajectory_has_steps", isinstance(steps, list) and bool(steps),
                f"steps={len(steps) if isinstance(steps, list) else 'invalid'}")
    recorded = trajectory_urls(traj)
    judge.check("all_urls_match_local_origin",
                bool(recorded) and all(_same_local_origin(u, traj.get("start_url", ""))
                                       for u in recorded),
                f"start_url={traj.get('start_url')!r}, n_urls={len(recorded)}")
    ok, evidence = screenshots_decode(traj)
    judge.check("screenshots_decode", ok, evidence)


def check_read_only(judge, initial_db, after_db):
    changed = changed_tables(initial_db, after_db)
    return judge.check("read_only_db_unchanged", not changed,
                       f"changed_tables={changed!r}")


def check_only_tables_changed(judge, initial_db, after_db, allowed):
    others = tuple(t for t in TABLES if t not in set(allowed))
    changed = changed_tables(initial_db, after_db, others)
    return judge.check("no_collateral_writes", not changed,
                       f"tables_outside_allowed={list(others)!r}, changed={changed!r}")


def check_signed_in_as(judge, traj, email):
    judge.check("visited_login_or_register",
                navigated_to_path(traj, "/authn/login")
                or navigated_to_path(traj, "/authn/register"),
                "required_path=/authn/login or /authn/register")
    judge.check("entered_expected_account_identity",
                entered_identity(traj, email),
                f"expected {email!r} in an input step; "
                f"observed_inputs={input_texts(traj)[:8]!r}")


def check_saved_car(judge, after_db, email, listing_id, exactly=None):
    ids = saved_car_ids(after_db, email)
    judge.check(f"saved_car_present_{listing_id[:8]}", listing_id in ids,
                f"saved_cars={[i[:8] for i in ids]!r}")
    if exactly is not None:
        judge.check(f"saved_car_count_{email.split('@')[0]}", len(ids) == exactly,
                    f"count={len(ids)}, expected {exactly}")


def check_saved_car_absent(judge, after_db, email, listing_id):
    ids = saved_car_ids(after_db, email)
    judge.check(f"saved_car_absent_{listing_id[:8]}", listing_id not in ids,
                f"saved_cars={[i[:8] for i in ids]!r}")


def check_saved_search(judge, after_db, email, name, frequency):
    rows = saved_searches_for(after_db, email)
    match = [r for r in rows if r["name"].strip().casefold() == name.casefold()]
    judge.check(f"saved_search_{name!r}", bool(match),
                f"searches={[(r['name'], r['alert_frequency']) for r in rows]!r}")
    if match:
        judge.check(f"saved_search_freq_{name!r}",
                    match[0]["alert_frequency"] == frequency,
                    f"freq={match[0]['alert_frequency']!r}, expected {frequency!r}")
    return match


# ---------------------------------------------------------------- CLI plumbing
@dataclass
class VerifyArgs:
    run_dir: str = ""
    initial_db: str = ""
    after_db: str = ""
    container: str = DEFAULT_CONTAINER
    no_llm: bool = False

    def post_process(self):
        if not self.run_dir:
            raise SystemExit("--run_dir is required")


def parse_args():
    try:
        import simpleArgParser as sap  # the agent_demo env; boolean flags take a value
        return sap.parse_args(VerifyArgs)
    except ImportError:  # plain python3 fallback with the same flags
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--run_dir", required=True)
        parser.add_argument("--initial_db", default="")
        parser.add_argument("--after_db", default="")
        parser.add_argument("--container", default=DEFAULT_CONTAINER)
        parser.add_argument("--no_llm", nargs="?", const="True", default="False")
        ns = parser.parse_args()
        args = VerifyArgs(ns.run_dir, ns.initial_db, ns.after_db, ns.container,
                          str(ns.no_llm).strip().lower() in {"1", "true", "yes"})
        args.post_process()
        return args


def run_verifier(task_id, run_checks):
    """Standard main(): load the run, resolve + validate snapshots, run the
    task checks, fail closed on any error."""
    args = parse_args()
    try:
        traj = load_run(args.run_dir)
    except (OSError, ValueError) as exc:
        fail_closed(task_id, "trajectory_unavailable", str(exc))
    try:
        initial_db, after_db = resolve_snapshots(args, task_id)
    except Exception as exc:  # noqa: BLE001 — snapshot problems fail closed
        fail_closed(task_id, "snapshot_unavailable", f"{type(exc).__name__}: {exc}")
    judge = Judge(task_id)
    try:
        run_checks(judge, traj, initial_db, after_db)
    except Exception as exc:  # noqa: BLE001 — any verifier error fails closed
        fail_closed(task_id, "verifier_error", f"{type(exc).__name__}: {exc}")
    judge.emit()


if __name__ == "__main__":
    fail_closed("cars_com", "not_a_task_verifier",
                "import verify_<N>.py and run it against --run_dir")
