#!/usr/bin/env python3
"""verify_lib.py — deterministic verifier utilities for speedo task verification.

Philosophy: DETERMINISTIC FIRST — same contract as the hardened reviewer suites
(``sites/soundcloud/verify/verify_lib.py``, ``sites/ryanair/verify/verify_lib.py``).
No LLM call is load-bearing; every check is regex / token / SQLite after-state.

  1. Package identity (fail-closed): task_id matches, ``terminated`` with
     ``agent_done``, non-empty final answer, every recorded URL on the same
     loopback origin AND port as ``start_url``, every referenced screenshot a
     decodable PNG.
  2. Navigation gates (anti knowledge-shortcut): the agent MUST have opened the
     on-site surfaces the task names (quiz pages, collections with facets,
     product pages, account pages, size guides, blog/FAQ pages, contact form).
     A correct answer with no matching navigation is a memory-recall
     shortcut = FAIL.
  3. Answer check: affirmative token / phrase / number matching against frozen
     ground truth HARDCODED in each ``verify_N.py`` (never in tasks.jsonl).
  4. DB after-state: initial (seed) vs after (instance) SQLite snapshots.
     Read-only tasks require every table row-identical to the seed; stateful
     tasks require the exact allowed row delta and nothing else (a new order
     with its order_items and the cart clear-down, a wishlist row swap, a
     contact case row, a newsletter signup, a registered user, an address /
     card / profile mutation).

Input signature (per task):
  --run_dir DIR        agent trajectory dir: trajectory.json + screenshots/step_NNN.png
  --initial_db PATH    initial-state SQLite DB (default: <run_dir>/initial.db, else
                       instance_seed from the container)
  --after_db PATH      after-state  SQLite DB (default: <run_dir>/after.db, else live
                       instance DB from the container)
  --container NAME     docker container to fetch DBs from (default: $WH_CONTAINER or
                       wh-speedo-review)
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

SITE = "speedo"
DEFAULT_CONTAINER = os.environ.get("WH_CONTAINER", "wh-speedo-review")

# ---------------------------------------------------------------- frozen seed contract
TABLES = ("users", "departments", "nav_groups", "collections", "products",
          "discount_codes", "athletes", "articles", "content_pages",
          "faq_entries", "newsletter_signups", "addresses", "payment_cards",
          "nav_links", "collection_memberships", "product_sizes", "cart_items",
          "wishlist_items", "orders", "contact_messages", "quiz_responses",
          "order_items")
SEED_COUNTS = {"users": 4, "departments": 5, "nav_groups": 24, "collections": 111,
               "products": 1280, "discount_codes": 1, "athletes": 12,
               "articles": 10, "content_pages": 25, "faq_entries": 10,
               "newsletter_signups": 0, "addresses": 6, "payment_cards": 5,
               "nav_links": 148, "collection_memberships": 3858,
               "product_sizes": 7799, "cart_items": 11, "wishlist_items": 18,
               "orders": 7, "contact_messages": 0, "quiz_responses": 0,
               "order_items": 11}
# sha256 over sqlite_master (type, name, tbl_name, sql) of instance_seed/speedo.db.
SCHEMA_SHA256 = "4178a12753ddaab090eb6af12458c970f13b7a67a5cc887ad04870f4001389d1"
# sha256 over every seed row (table-canonical, ORDER BY all columns). The seed is
# built deterministically at image build time (PYTHONHASHSEED=0, no secondary
# indexes) and reproduces byte-for-byte on every build (md5 5561ace9…).
SEED_ROWS_SHA256 = "4186ce79663fcc44ee5d7bdfd530ac34da2bf01fcd08f48b42f746679e770720"
SEED_USERS = {  # email -> (id, name); identity columns never change
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


def check_visited_path(judge, traj, name, pattern):
    hit = visited_path(traj, pattern)
    judge.check(name, hit, f"required path ~{pattern}"
                + ("" if hit else f" — visited: {[u.split('localhost')[-1] for u in trajectory_urls(traj)][:12]}"))


def check_not_visited_path(judge, traj, name, pattern):
    hit = visited_path(traj, pattern)
    judge.check(name, not hit, f"path ~{pattern} must NOT appear in the trajectory")


def _affirmative(text, match):
    prefix = re.split(r"[;.!?\n]|\b(?:but|however)\b", text[:match.start()], flags=re.I)[-1]
    return not re.search(r"\b(?:not|never|isn't|isnt)\b(?:\W+\w+){0,3}\W*$", prefix, re.I)


def check_answer_phrase(judge, answer, name, phrase, case_sensitive=False):
    hay = answer if case_sensitive else answer.casefold()
    needle = phrase if case_sensitive else phrase.casefold()
    judge.check(name, any(_affirmative(hay, m) for m in re.finditer(re.escape(needle), hay)), f"answer must mention {phrase!r}")


def _norm_num(s):
    from decimal import Decimal, InvalidOperation
    value = re.sub(r"[,\s]", "", str(s)).strip(".,")
    try:
        return Decimal(value)
    except InvalidOperation:
        return value.casefold()


def check_answer_number(judge, answer, name, value, label=None):
    target = _norm_num(value)
    words = {0:"zero",1:"one",2:"two",3:"three",4:"four",5:"five",6:"six",7:"seven",8:"eight",9:"nine",10:"ten"}
    if target in words:
        answer = re.sub(r"\b"+words[target]+r"\b", str(target), answer, flags=re.I)
    found = any(_norm_num(m.group()) == target and _affirmative(answer, m)
                for m in re.finditer(r"(?<![\w.])[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?(?!\w|\.\d)", answer))
    judge.check(name, found, f"answer must affirm {value} ({label or name})")


def check_answer_any(judge, answer, name, variants, label=""):
    hay = answer.casefold()
    hit = any(str(_norm_num(v)) in hay or str(v).casefold() in hay for v in variants)
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


def acquire_seed(cache=None):
    cache = Path(cache or os.environ.get("SPEEDO_TEST_SEED_DB")
                 or Path("/tmp/speedo_verify_seed.db"))
    if cache.is_file():
        return cache
    return fetch_db(DEFAULT_CONTAINER,
                    f"/opt/WebSyn/{SITE}/instance_seed/{SITE}.db", cache)


def acquire_instance(container=None):
    container = container or DEFAULT_CONTAINER
    out = Path("/tmp") / f"speedo_verify_instance_{container}.db"
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


def check_new_order(judge, initial_db, after_db, *, email, subtotal, discount,
                    discount_code, shipping_method, shipping, total, card_last4,
                    items, allowed_extra=("cart_items", "order_items", "orders")):
    """Exactly one new order row with the frozen values + its order_items;
    the buyer's cart (if logged-in) cleared. `items` = list of
    (product_name, size, qty, unit_price) tuples."""
    added, removed, changed = table_diff(initial_db, after_db, "orders")
    judge.check("existing_orders_preserved", not changed)
    judge.check("one_order_added", len(added) == 1 and len(removed) == 0,
                f"added={list(added.values())!r} removed={list(removed.values())!r}")
    if not added:
        return
    row = list(added.values())[0]
    judge.check("order_number", row["order_number"] == "SP100008",
                f"order_number={row['order_number']!r}")
    judge.check("order_email", (row["email"] == email if email else bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", row["email"]))), f"email={row['email']!r}")
    owner = initial_db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone() if email else None
    judge.check("order_owner", row["user_id"] == (owner[0] if owner else None))
    judge.check("order_status", row["status"] == "Processing")
    judge.check("order_subtotal", abs(row["subtotal"] - subtotal) < 0.005,
                f"subtotal={row['subtotal']} expected {subtotal}")
    judge.check("order_discount", abs(row["discount"] - discount) < 0.005,
                f"discount={row['discount']} expected {discount}")
    judge.check("order_discount_code", row["discount_code"] == discount_code,
                f"discount_code={row['discount_code']!r}")
    judge.check("order_shipping_method", row["shipping_method"] == shipping_method,
                f"shipping_method={row['shipping_method']!r}")
    judge.check("order_shipping", abs(row["shipping"] - shipping) < 0.005,
                f"shipping={row['shipping']} expected {shipping}")
    judge.check("order_total", abs(row["total"] - total) < 0.005,
                f"total={row['total']} expected {total}")
    if card_last4 is not None:
        judge.check("order_card_last4", row["card_last4"] == card_last4,
                    f"card_last4={row['card_last4']!r}")
    a, r, c = table_diff(initial_db, after_db, "order_items")
    judge.check("existing_items_preserved", not c)
    judge.check("items_belong_to_order", all(x["order_id"] == row["id"] for x in a.values()))
    for x in a.values():
        product = initial_db.execute("SELECT name, slug FROM products WHERE id = ?", (x["product_id"],)).fetchone()
        judge.check("item_product_identity", product is not None and tuple(product) == (x["product_name"], x["product_slug"]))
    judge.check("order_items_added", len(a) == len(items) and len(r) == 0,
                f"added={[(e['product_name'], e['size']) for e in a.values()]!r}")
    got = sorted((e["product_name"], e["size"], e["qty"], e["unit_price"])
                 for e in a.values())
    judge.check("order_items_exact", got == sorted(items),
                f"got={got} expected={sorted(items)}")


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


def check_order_recipient(judge, initial_db, after_db, name, line1, city, postcode, line2=""):
    a, _, _ = table_diff(initial_db, after_db, "orders")
    judge.check("one_order_for_recipient", len(a) == 1)
    if len(a) == 1:
        row = next(iter(a.values()))
        expected = dict(ship_name=name, ship_line1=line1, ship_line2=line2, ship_city=city,
                        ship_postcode=postcode, ship_country="United Kingdom")
        judge.check("delivery_address", all(row[k].casefold().strip() == v.casefold().strip() for k, v in expected.items()))
