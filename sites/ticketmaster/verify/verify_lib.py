#!/usr/bin/env python3
"""verify_lib.py — deterministic verifier utilities for ticketmaster task
verification (review track, orch/review/ticketmaster).

Philosophy: DETERMINISTIC FIRST — same contract as the hardened reviewer
suites (sites/statista, sites/thumbtack). No LLM call is load-bearing; every
check is regex / token / SQLite after-state.

  1. Package identity (fail-closed): task_id matches, ``terminated`` with
     ``agent_done``, non-empty final answer, every recorded URL on the same
     loopback origin AND port as ``start_url``, every referenced screenshot a
     decodable PNG.
  2. Navigation gates (anti knowledge-shortcut): the agent MUST have opened
     the on-site surfaces the task names (search, event pages with the
     required filters, ticket selection, checkout, order confirmation, the
     member area, venue/artist pages, help centre, gift cards). A correct
     answer with no matching navigation is a memory-recall shortcut = FAIL.
  3. Answer check: affirmative token / phrase / number matching against
     frozen ground truth HARDCODED in each ``verify_N.py`` (never in
     tasks.jsonl). For purchase tasks the runtime order number must match the
     row actually written to the after-state DB.
  4. DB after-state: initial (seed) vs after (instance) SQLite snapshots.
     Read-only tasks require every table row-identical to the seed; purchase
     tasks require exactly one new orders row (event/listing/qty/price
     fields frozen) plus the matching ticket_listings qty decrement and
     nothing else; card-management and favorites tasks require the exact
     allowed deltas. The seed contract is pinned to the review container's
     deterministic build (PYTHONHASHSEED=0 seed build, md5 b03a154d…).

The "cheapest" anchors are pinned by the task wording to Standard Admission
(and, for T17, to the cheapest Standard option with >=4 seats together);
seed_data._detie_minimums makes every (event, ticket type) minimum all-in
price unique on both the all-listings and the 4+ seats together cuts, so each
purchase task has exactly one acceptable listing. T17's former Sec 202 Row F
price tie was broken in the seed (202 F is no longer at the minimum).

Input signature (per task):
  --run_dir DIR        agent trajectory dir: trajectory.json + screenshots/step_NNN.png
  --initial_db PATH    initial-state SQLite DB (default: <run_dir>/initial.db, else
                       instance_seed from the container)
  --after_db PATH      after-state  SQLite DB (default: <run_dir>/after.db, else live
                       instance DB from the container)
  --container NAME     docker container to fetch DBs from (default: $WH_CONTAINER or
                       wh-tm-rereview)
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
from pathlib import Path
from urllib.parse import urlparse

SITE = "ticketmaster"
DEFAULT_CONTAINER = os.environ.get("WH_CONTAINER", "wh-tm-rereview")

# ---------------------------------------------------------------- frozen seed contract
# Review container wh-tm-rereview, image webharbor:tm-rereview (built from
# the contributor fix commit 73b29ac8), ticketmaster seed built in-image
# with PYTHONHASHSEED=0; instance == instance_seed, md5 b03a154d…,
# byte-reproducible (two independent --no-cache builds agree).
TABLES = ("content_records", "users", "artists", "venues", "events", "ticket_listings",
          "orders", "payment_methods", "favorites", "presales")
SEED_COUNTS = {"content_records": 1, "users": 4, "artists": 130, "venues": 171, "events": 621,
               "ticket_listings": 37507, "orders": 6, "payment_methods": 6,
               "favorites": 15, "presales": 337}
SEED_DB_MD5 = "b03a154d8eccfbac2be5ac4bd8a59ff8"
SEED_USERS = {  # email -> id; identity columns never change
    "alice.j@test.com": 1,
    "bob.c@test.com": 2,
    "carol.d@test.com": 3,
    "david.k@test.com": 4,
}
DEMO_PASSWORD = "TestPass123!"
BCRYPT_RX = re.compile(r"^\$2[aby]\$12\$[./A-Za-z0-9]{53}$")
ORDER_NO_RX = re.compile(r"^[A-Z0-9]{14}$")

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


def decode_png(path):
    try:
        from PIL import Image
        with Image.open(path) as image:
            image.load()
            valid = image.format == "PNG" and image.width > 0 and image.height > 0
        return (valid, "decoded PNG")
    except (OSError, ValueError) as exc:
        return (False, str(exc))


def check_trajectory_identity(judge, traj, task_id):
    if traj.get("task_id") != task_id:
        judge.fail(f"task_id mismatch: {traj.get('task_id')!r} != {task_id!r}")
        return
    judge.evidence(f"task_id matches: {task_id}")
    if not traj.get("terminated"):
        judge.fail("trajectory not terminated")
    elif traj.get("termination_reason") != "agent_done":
        judge.fail(f"termination_reason is {traj.get('termination_reason')!r}, expected 'agent_done'")
    else:
        judge.evidence("terminated with agent_done")
    answer = final_answer(traj)
    if not answer:
        judge.fail("empty final_answer")
    else:
        judge.evidence(f"final answer present ({len(answer)} chars)")
    urls = trajectory_urls(traj)
    if not urls:
        judge.fail("no urls recorded in trajectory")
        return
    if not is_site_url(urls[0]):
        judge.fail(f"start_url is not a loopback site url: {urls[0]!r}")
        return
    first = urlparse(urls[0])
    for u in urls[1:]:
        p = urlparse(u)
        if (p.scheme, p.hostname, p.port) != (first.scheme, first.hostname, first.port):
            judge.fail(f"off-origin url in trajectory: {u!r} (start {urls[0]!r})")
            return
    judge.evidence(f"all {len(urls)} recorded urls on origin {first.scheme}://{first.hostname}:{first.port}")
    shots = traj.get("_shots") or {}
    if not shots:
        judge.fail("no step screenshots found in run dir")
        return
    referenced = []
    for step in traj.get("steps") or []:
        if not isinstance(step, dict):
            continue
        for key in ("screenshot_before", "screenshot_after"):
            if step.get(key):
                referenced.append(str(step[key]))
    bad = []
    for name in referenced:
        if name not in shots:
            bad.append(f"{name}: missing from run dir")
            continue
        ok, detail = decode_png(shots[name])
        if not ok:
            bad.append(f"{name}: {detail}")
    if bad:
        judge.fail("screenshot integrity broken: " + "; ".join(bad[:3]))
    else:
        judge.evidence(f"{len(referenced)} referenced screenshots present and decodable")


def check_visited_path(judge, traj, label, pattern):
    rx = re.compile(pattern)
    for u in trajectory_urls(traj):
        if rx.search(u):
            judge.evidence(f"visited {label}: {u}")
            return
    judge.fail(f"never visited {label} (no url matches {pattern!r})")


def check_input_action(judge, traj, label, pattern):
    """The agent must have typed text matching pattern (fill/input action)."""
    rx = re.compile(pattern)
    for step in traj.get("steps") or []:
        if not isinstance(step, dict):
            continue
        action = str(step.get("action") or "")
        params = step.get("params") or {}
        if action in ("input", "type", "fill", "input_text", "type_text"):
            text = str(params.get("text") or params.get("value") or "")
            if rx.search(text):
                judge.evidence(f"typed {label}: {text!r}")
                return
    judge.fail(f"never typed {label} (no input text matches {pattern!r})")


# ---------------------------------------------------------------- answers
def _norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def check_answer_phrase(judge, answer, label, phrase):
    if _norm(phrase) in _norm(answer):
        judge.evidence(f"answer mentions {label}: {phrase!r}")
    else:
        judge.fail(f"answer does not mention {label} (expected phrase {phrase!r})")


def check_answer_any(judge, answer, label, phrases):
    for ph in phrases:
        if _norm(ph) in _norm(answer):
            judge.evidence(f"answer mentions {label}: {ph!r}")
            return
    judge.fail(f"answer does not mention {label} (expected any of {phrases!r})")


def check_answer_number(judge, answer, label, number, context=None):
    from answer_bindings import BINDINGS, number_bound, _number_pattern, _affirmed, _assertions
    task_no = int(getattr(judge, 'task_id', '--0').split('--')[-1])
    groups = BINDINGS.get(task_no, {}).get(label)
    value = str(number)
    if groups:
        hit = number_bound(answer, value, groups)
    else:
        hit = any(_affirmed(segment, m.start()) for segment in _assertions(answer)
                  for m in _number_pattern(value).finditer(segment))
    if hit: judge.evidence(f"{label}: {value}")
    else: judge.fail(f"{label}: missing or incorrectly associated value {value}")


def check_answer_money(judge, answer, label, amount):
    from answer_bindings import BINDINGS, number_bound, _number_pattern, _affirmed, _assertions
    task_no = int(getattr(judge, 'task_id', '--0').split('--')[-1])
    groups = BINDINGS.get(task_no, {}).get(label)
    value = str(amount)
    if groups:
        hit = number_bound(answer, value, groups)
    else:
        hit = any(_affirmed(segment, m.start()) for segment in _assertions(answer)
                  for m in _number_pattern(value).finditer(segment))
    if hit: judge.evidence(f"{label}: {value}")
    else: judge.fail(f"{label}: missing or incorrectly associated value {value}")


# ---------------------------------------------------------------- db helpers
def _connect(path):
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def fetch_counts(path):
    db = _connect(path)
    try:
        return {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}
    finally:
        db.close()


def table_rows(path, table):
    db = _connect(path)
    try:
        cols = [r[1] for r in db.execute(f"PRAGMA table_info({table})")]
        order = ", ".join(f'"{c}"' for c in cols)
        rows = [tuple(r) for r in db.execute(f"SELECT * FROM {table} ORDER BY {order}")]
        return cols, rows
    finally:
        db.close()


def check_read_only(judge, initial_db, after_db):
    """Every table must be row-identical between initial and after snapshots."""
    for table in TABLES:
        _, rows_i = table_rows(initial_db, table)
        _, rows_a = table_rows(after_db, table)
        if rows_i != rows_a:
            judge.fail(f"read-only task but table {table!r} changed "
                       f"({len(rows_i)} -> {len(rows_a)} rows)")
            return
    judge.evidence(f"read-only verified: all {len(TABLES)} tables row-identical to the seed")


def _diff_rows(initial_db, after_db, table):
    """Key-aware diff: a changed row is an UPDATE, not add+remove."""
    cols, rows_i = table_rows(initial_db, table)
    _, rows_a = table_rows(after_db, table)
    key = cols.index("id") if "id" in cols else 0
    ids_i = {r[key] for r in rows_i}
    ids_a = {r[key] for r in rows_a}
    added = [r for r in rows_a if r[key] not in ids_i]
    removed = [r for r in rows_i if r[key] not in ids_a]
    return added, removed


def _updated_rows(initial_db, after_db, table):
    """Rows whose id exists on both sides but whose content differs."""
    cols, rows_i = table_rows(initial_db, table)
    _, rows_a = table_rows(after_db, table)
    key = cols.index("id") if "id" in cols else 0
    by_id_i = {r[key]: r for r in rows_i}
    by_id_a = {r[key]: r for r in rows_a}
    updated = [by_id_a[k] for k in by_id_a
               if k in by_id_i and by_id_a[k] != by_id_i[k]]
    return updated


def check_only_tables_changed(judge, initial_db, after_db, allowed):
    """Only the allowed tables may differ (added/removed/updated rows);
    every other table must be row-identical."""
    for table in TABLES:
        added, removed = _diff_rows(initial_db, after_db, table)
        updated = _updated_rows(initial_db, after_db, table)
        changed = bool(added or removed or updated)
        if table in allowed:
            if changed:
                judge.evidence(f"table {table!r} changed as allowed "
                               f"(+{len(added)} -{len(removed)} ~{len(updated)})")
            else:
                judge.fail(f"table {table!r} is in the allowed set but did not change")
        elif changed:
            judge.fail(f"unexpected change in table {table!r} "
                       f"(+{len(added)} -{len(removed)} ~{len(updated)} rows)")


def check_purchase_order(judge, initial_db, after_db, answer, expect):
    """Verify a completed purchase against the after-state DB.

    expect: dict with event_id, qty, and one or more candidate listings:
      listings = [(listing_id, section, row, unit_price, total, qty_after), ...]
      user_id (int) or guest_email (str) selects the buyer identity.
    Exactly one orders row must be added, matching one candidate listing on
    section/row/qty/unit/total/identity; that listing's qty_available must
    have been decremented by qty; the runtime order number must appear in
    the agent's final answer.
    """
    added, removed = _diff_rows(initial_db, after_db, "orders")
    if removed:
        judge.fail(f"unexpected orders row removal: {removed[:1]}")
        return
    if len(added) != 1:
        judge.fail(f"orders: expected exactly 1 added row, got {len(added)}")
        return
    o = added[0]
    # orders columns: id, order_no, user_id, event_id, listing_id, section,
    # section_desc, row, qty, unit_price, face_total, fee_total, total,
    # delivery, card_last4, card_brand, status, guest_email, created_at, placed_at
    order_no, user_id, event_id, listing_id = o[1], o[2], o[3], o[4]
    section, row, qty, unit_price, total = o[5], o[7], o[8], o[9], o[12]
    guest_email = o[17]
    if not ORDER_NO_RX.match(order_no or ""):
        judge.fail(f"new order number {order_no!r} is not the runtime 14-char format")
        return
    if event_id != expect["event_id"]:
        judge.fail(f"purchased event {event_id!r} != expected {expect['event_id']!r}")
        return
    if qty != expect["qty"]:
        judge.fail(f"purchased qty {qty!r} != expected {expect['qty']!r}")
        return
    if expect.get("user_id") is not None and user_id != expect["user_id"]:
        judge.fail(f"purchasing user id {user_id!r} != expected {expect['user_id']!r}")
        return
    if expect.get("guest_email"):
        if (guest_email or "") != expect["guest_email"]:
            judge.fail(f"guest email {guest_email!r} != expected {expect['guest_email']!r}")
            return
    matched = None
    for cand in expect["listings"]:
        lid, csec, crow, cunit, ctotal, cqty_after = cand
        if (listing_id == lid and section == csec and row == crow
                and abs(unit_price - cunit) < 0.005 and abs(total - ctotal) < 0.005):
            matched = cand
            break
    if matched is None:
        judge.fail(f"purchased listing (id={listing_id}, Sec {section} Row {row}, "
                   f"unit {unit_price}, total {total}) matches none of the "
                   f"expected candidates {expect['listings']!r}")
        return
    judge.evidence(f"orders: +1 row {order_no} for event {event_id} "
                   f"Sec {section} Row {row} x{qty} total {total} (listing {matched[0]})")
    # the bought listing must be the ONLY ticket_listings change, qty decremented
    updated = _updated_rows(initial_db, after_db, "ticket_listings")
    lid, csec, crow, cunit, ctotal, cqty_after = matched
    ok_update = [u for u in updated if u[0] == lid]
    if len(updated) != 1 or not ok_update:
        judge.fail(f"ticket_listings: expected exactly 1 updated row (listing {lid}), "
                   f"got {[u[0] for u in updated]!r}")
        return
    if updated[0][5] != cqty_after:
        judge.fail(f"listing {lid} qty_available is {updated[0][5]!r}, "
                   f"expected {cqty_after!r} after buying {expect['qty']}")
        return
    judge.evidence(f"ticket_listings: listing {lid} qty_available -> {cqty_after} as expected")
    # the runtime order number must be reported in the answer
    if order_no not in (answer or ""):
        judge.fail(f"answer does not report the order number {order_no!r}")
        return
    judge.evidence(f"answer reports the runtime order number {order_no}")


def check_row_added(judge, initial_db, after_db, table, expect_row, label):
    """Exactly one row must be added to `table`, matching expect_row on the
    non-None positions."""
    added, removed = _diff_rows(initial_db, after_db, table)
    if removed:
        judge.fail(f"unexpected removal from {table!r}: {removed[:1]}")
        return
    if len(added) != 1:
        judge.fail(f"{table!r}: expected exactly 1 added row, got {len(added)}")
        return
    got = added[0]
    for g, e in zip(got, expect_row):
        if e is not None and g != e:
            judge.fail(f"{label}: added row {tuple(got)!r} does not match expected "
                       f"{expect_row!r} at position of {e!r}")
            return
    judge.evidence(f"{label}: added row verified {tuple(got)!r}")


def check_row_removed(judge, initial_db, after_db, table, expect_row, label):
    """Exactly one row must be removed from `table`, matching expect_row on
    the non-None positions."""
    added, removed = _diff_rows(initial_db, after_db, table)
    if added:
        judge.fail(f"unexpected addition to {table!r}: {added[:1]}")
        return
    matching = [r for r in removed
                if all(e is None or g == e for g, e in zip(r, expect_row))]
    if len(matching) != 1:
        judge.fail(f"{label}: expected exactly 1 removed row matching {expect_row!r}, "
                   f"got {len(matching)} (removed={[tuple(r)[:4] for r in removed][:4]})")
        return
    judge.evidence(f"{label}: removed row verified {tuple(matching[0])!r}")


def check_row_swap(judge, initial_db, after_db, table, added_row, removed_row,
                   label):
    """For tasks that both add and remove a row in the same table: exactly one
    row matching added_row must be added AND exactly one row matching
    removed_row must be removed; nothing else may change in the table."""
    added, removed = _diff_rows(initial_db, after_db, table)
    matching_added = [r for r in added
                      if all(e is None or g == e for g, e in zip(r, added_row))]
    matching_removed = [r for r in removed
                        if all(e is None or g == e for g, e in zip(r, removed_row))]
    if len(added) != 1 or len(matching_added) != 1:
        judge.fail(f"{label}: expected exactly 1 added row matching {added_row!r}, "
                   f"got {len(matching_added)} (added={[tuple(r)[:4] for r in added][:4]})")
        return
    if len(removed) != 1 or len(matching_removed) != 1:
        judge.fail(f"{label}: expected exactly 1 removed row matching {removed_row!r}, "
                   f"got {len(matching_removed)} (removed={[tuple(r)[:4] for r in removed][:4]})")
        return
    judge.evidence(f"{label}: added row verified {tuple(matching_added[0])!r}")
    judge.evidence(f"{label}: removed row verified {tuple(matching_removed[0])!r}")


def check_seed_contract(judge, db_path):
    if logical_digest(db_path) != "e25d1f6eed2a4a530d0747cf446a5bbdec97cd456a6f6f9b89cb4fee6bbe8f34":
        judge.fail("initial database differs from reviewed seed schema or rows")
        return
    counts = fetch_counts(db_path)
    for table, count in SEED_COUNTS.items():
        if counts.get(table) != count:
            judge.fail(f"seed contract broken: {table} has {counts.get(table)} rows, "
                       f"expected {count}")
            return
    judge.evidence(f"seed contract verified (md5 {SEED_DB_MD5}, "
                   f"{sum(SEED_COUNTS.values())} rows over {len(TABLES)} tables)")


# ---------------------------------------------------------------- runner
class Judge:
    def __init__(self):
        self.passed = True
        self.reason = ""
        self.evidence_list = []

    def evidence(self, msg):
        self.evidence_list.append(msg)

    def fail(self, msg):
        self.passed = False
        if not self.reason:
            self.reason = msg
        self.evidence_list.append("FAIL: " + msg)


def acquire_dbs(run_dir, initial_arg, after_arg, container):
    run_dir = Path(run_dir)
    initial = Path(initial_arg) if initial_arg else run_dir / "initial.db"
    after = Path(after_arg) if after_arg else run_dir / "after.db"
    if not initial.is_file():
        subprocess.run(["docker", "cp",
                        f"{container}:/opt/WebSyn/{SITE}/instance_seed/{SITE}.db",
                        str(initial)], check=True)
    if not after.is_file():
        subprocess.run(["docker", "cp",
                        f"{container}:/opt/WebSyn/{SITE}/instance/{SITE}.db",
                        str(after)], check=True)
    return initial, after


def run_verifier(task_id, run_checks):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--run_dir", required=True)
    ap.add_argument("--initial_db", default=None)
    ap.add_argument("--after_db", default=None)
    ap.add_argument("--container", default=DEFAULT_CONTAINER)
    args = ap.parse_args()
    judge = Judge()
    judge.task_id = task_id
    result = {"task_id": task_id, "pass": False, "reason": "", "evidence": []}
    try:
        traj = load_run(args.run_dir)
        initial, after = acquire_dbs(args.run_dir, args.initial_db,
                                     args.after_db, args.container)
        check_seed_contract(judge, initial)
        check_trajectory_identity(judge, traj, task_id)
        if judge.passed:
            run_checks(judge, traj, initial, after)
    except Exception as e:  # fail closed on any verifier error
        judge.fail(f"verifier error: {type(e).__name__}: {e}")
    result["pass"] = judge.passed
    result["reason"] = judge.reason or ("all checks passed" if judge.passed else "failed")
    result["evidence"] = judge.evidence_list
    print(json.dumps(result, indent=1))
    return 0 if judge.passed else 1


def logical_digest(path):
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as con:
        schema = list(con.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"))
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        rows = {t: sorted([list(r) for r in con.execute('SELECT * FROM "'+t+'"')], key=repr) for t in tables}
    return hashlib.sha256(json.dumps([schema, rows], default=str).encode()).hexdigest()
