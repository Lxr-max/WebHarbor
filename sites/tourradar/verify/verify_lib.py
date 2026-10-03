#!/usr/bin/env python3
"""verify_lib.py — deterministic verification utilities for TourRadar tasks.

Philosophy: DETERMINISTIC FIRST, zero LLM.
  1. Trajectory identity + navigation gates (anti knowledge-shortcut): the
     agent MUST have opened the on-site pages the task requires; a correct
     answer with no matching navigation is a memory-recall shortcut = FAIL.
  2. Answer checks: token / amount containment against frozen ground truth
     (hardcoded in the per-task verifiers — never in tasks.jsonl).
  3. DB after-state checks (stateful tasks): query the SQLite instance DB
     directly — the strongest deterministic signal (booking rows, wishlist
     deltas, Q&A rows, published reviews, cancellation flips).
  4. Seed snapshot contract: initial_db must be the frozen deterministic seed
     (schema sha + per-table counts + rows sha) so tampered snapshots fail.

Input signature (per task):
  --run_dir DIR      agent run dir: trajectory.json + screenshots/step_NNN.png
  --initial_db PATH  initial-state SQLite DB (default: <run_dir>/initial.db,
                     else docker-copied from the container's instance_seed)
  --after_db PATH    after-state  SQLite DB (default: <run_dir>/after.db,
                     else docker-copied from the container's live instance)
  --container NAME   docker container to fetch DBs from
                     (default: $WH_CONTAINER or wh-tourradar-review)
Output: JSON {task_id, pass, reason, evidence[]} on stdout; exit 0 PASS / 1 FAIL.
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

SITE = "tourradar"
DEFAULT_CONTAINER = os.environ.get("WH_CONTAINER", "wh-tourradar-review")

# ---------------------------------------------------------------- frozen seed contract
TABLES = ("bookings", "departures", "destinations", "moments", "operators",
          "platform_reviews", "promo_codes", "reviews", "tour_qa", "tours",
          "users", "wishlist_items")
SEED_COUNTS = {"bookings": 6, "departures": 9559, "destinations": 99,
               "moments": 331, "operators": 127, "platform_reviews": 0,
               "promo_codes": 2, "reviews": 2105, "tour_qa": 819, "tours": 213,
               "users": 4, "wishlist_items": 11}
# sha256 over sqlite_master (type, name, tbl_name, sql) of instance_seed/tourradar.db.
SCHEMA_SHA256 = "31fc91ccf2d7f37932a381db2f74f77b4437cb0fc24ac3ce23686b49d6d397fe"
# sha256 over every seed row (table-canonical, ORDER BY all columns). The seed
# is built deterministically at image build time (PYTHONHASHSEED=0) and
# reproduces byte-for-byte on every build; md5 of the seed file itself is
# d481eb7cd2003f201c8f78099436a044 (re-frozen 2026-09-28 after the day-block
# data fix: 31 tours' itinerary titles restored + 8 tours' day descriptions
# and cities re-joined by data-id; table counts and schema unchanged).
SEED_ROWS_SHA256 = "b4d658dab90aa1ed647bf6a9dac828e9402992df0dfcde535d63394c600e0785"
SEED_USERS = {  # email -> (id, display_name); identity columns never change
    "alice.j@test.com": (1, "Alice Johnson"),
    "bob.c@test.com": (2, "Bob Chen"),
    "carol.d@test.com": (3, "Carol Davis"),
    "david.k@test.com": (4, "David Kim"),
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


def navigated_booking_confirmation(traj):
    return any(re.search(r"/booking/TR-\d+", u) for u in trajectory_urls(traj))


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
    """Decode every referenced screenshot; a PNG signature alone is insufficient."""
    from PIL import Image
    shots = traj.get("_shots", {})
    referenced = {step[key] for step in traj.get("steps", [])
                  for key in ("screenshot", "screenshot_before", "screenshot_after")
                  if step.get(key)}
    if not referenced:
        return False, "no referenced screenshots"
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
    """The answer must state the given amount, tolerating US$/$/comma forms.

    '359.80', 'US$359.80', '$359.80', '359.8', '359.80 today' all match 359.8.
    """
    text = str(final or "")
    pat = re.compile(r"(?:us)?\$\s*([\d,]+(?:\.\d+)?)", re.I)
    for m in pat.finditer(text):
        try:
            val = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        if abs(val - float(amount)) <= tol:
            return True
    # bare-number fallback (e.g. "charged 359.80 today")
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
        raise ValueError("initial_db is not the frozen tourradar seed "
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
def changed_tables(initial_db, after_db, tables=None):
    """Tables whose row content differs between the two snapshots."""
    changed = []
    for t in (tables or TABLES):
        a = rows_sha_for(initial_db, t)
        b = rows_sha_for(after_db, t)
        if a != b:
            changed.append(t)
    return tuple(changed)


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


def added_rows(after_db, initial_db, table, id_col="id"):
    before = {r[id_col] for r in db_query(initial_db, f'SELECT "{id_col}" FROM "{table}"')}
    after = {r[id_col] for r in db_query(after_db, f'SELECT "{id_col}" FROM "{table}"')}
    new_ids = sorted(after - before)
    return [r for r in db_query(after_db, f'SELECT * FROM "{table}"')
            if r[id_col] in new_ids]


def removed_rows(after_db, initial_db, table, id_col="id"):
    before = {r[id_col] for r in db_query(initial_db, f'SELECT "{id_col}" FROM "{table}"')}
    after = {r[id_col] for r in db_query(after_db, f'SELECT "{id_col}" FROM "{table}"')}
    gone = sorted(before - after)
    return [r for r in db_query(initial_db, f'SELECT * FROM "{table}"')
            if r[id_col] in gone]


def added_bookings(after_db, initial_db):
    return added_rows(after_db, initial_db, "bookings", "ref")


def booking_travelers(row):
    try:
        return len(json.loads(row.get("travelers") or "[]"))
    except Exception:
        return 0


def user_by_email(db, email):
    rows = db_query(db, "SELECT id, email, display_name FROM users WHERE email=?",
                    (email.lower(),))
    return rows[0] if rows else None


def wishlist_tour_ids(db, email):
    rows = db_query(db,
        "SELECT w.tour_id FROM wishlist_items w JOIN users u ON u.id=w.user_id "
        "WHERE u.email=? ORDER BY w.tour_id", (email.lower(),))
    return [r["tour_id"] for r in rows]


def tour_qa_for_tour(db, tour_id):
    return db_query(db, "SELECT * FROM tour_qa WHERE tour_id=? ORDER BY id",
                    (tour_id,))


def reviews_for_tour(db, tour_id):
    return db_query(db, "SELECT * FROM reviews WHERE tour_id=? ORDER BY id",
                    (tour_id,))


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
    judge.check("visited_login_page", navigated_to_path(traj, "/login"),
                "required_path=/login")
    judge.check("entered_expected_account_identity",
                entered_identity(traj, email),
                f"expected {email!r} in an input step; "
                f"observed_inputs={input_texts(traj)[:8]!r}")


def check_booking_row(judge, after_db, initial_db, *, tour_id, travelers,
                      room_type, insurance, schedule=None, total=None,
                      due_today=None, lead_email=None, departure_date=None,
                      promo_code=None):
    """Exactly one new booking row matching every frozen field."""
    added = added_bookings(after_db, initial_db)
    judge.check("one_booking_added", len(added) == 1,
                f"added_booking_refs={[r['ref'] for r in added]!r}")
    if not added:
        return None
    b = added[0]
    judge.check("booked_tour", b["tour_id"] == tour_id,
                f"tour_id={b['tour_id']!r}, expected {tour_id}")
    judge.check("booked_travelers", booking_travelers(b) == travelers,
                f"travelers={booking_travelers(b)!r}, expected {travelers}")
    judge.check("booked_room", (b["room_type"] or "") == room_type,
                f"room_type={b['room_type']!r}, expected {room_type!r}")
    judge.check("booked_insurance", b["insurance"] == insurance,
                f"insurance={b['insurance']!r}, expected {insurance!r}")
    if schedule is not None:
        judge.check("booked_schedule", b["payment_schedule"] == schedule,
                    f"schedule={b['payment_schedule']!r}, expected {schedule!r}")
    if total is not None:
        judge.check("booked_total", abs((b["total"] or 0) - total) < 0.005,
                    f"total={b['total']!r}, expected {total}")
    if due_today is not None:
        judge.check("booked_due_today",
                    abs((b["due_today"] or 0) - due_today) < 0.005,
                    f"due_today={b['due_today']!r}, expected {due_today}")
    if lead_email is not None:
        judge.check("booked_email",
                    (b["lead_email"] or "").lower() == lead_email.lower(),
                    f"lead_email={b['lead_email']!r}, expected {lead_email!r}")
    if departure_date is not None:
        judge.check("booked_departure", b["departure_date"] == departure_date,
                    f"departure_date={b['departure_date']!r}, expected {departure_date}")
    if promo_code is not None:
        judge.check("booked_promo", (b["promo_code"] or "") == promo_code,
                    f"promo_code={b['promo_code']!r}, expected {promo_code!r}")
    judge.check("booking_status_confirmed", b["status"] == "confirmed",
                f"status={b['status']!r}")
    return b


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
        from reviewed_answers import check_answer
        check_answer(judge, traj, int(task_id.split("--")[-1]))
        from reviewed_state import check_state
        check_state(judge, task_id, initial_db, after_db)
    except Exception as exc:  # noqa: BLE001 — any verifier error fails closed
        fail_closed(task_id, "verifier_error", f"{type(exc).__name__}: {exc}")
    judge.emit()
