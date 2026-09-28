#!/usr/bin/env python3
"""verify_lib.py — deterministic verifier utilities for sourceforge task verification.

Philosophy: DETERMINISTIC FIRST — same contract as the hardened reviewer suites
(``sites/soundcloud/verify/verify_lib.py``, ``sites/ryanair/verify/verify_lib.py``).
No LLM call is load-bearing; every check is regex / token / SQLite after-state.

  1. Package identity (fail-closed): task_id matches, ``terminated`` with
     ``agent_done``, non-empty final answer, every recorded URL on the same
     loopback origin AND port as ``start_url``, every referenced screenshot a
     decodable PNG.
  2. Navigation gates (anti knowledge-shortcut): the agent MUST have opened the
     on-site surfaces the task names (directory search, project pages, reviews,
     trackers, forums, file browser, stats pages, business directory, auth /
     account pages). A correct answer with no matching navigation is a
     memory-recall shortcut = FAIL.
  3. Answer check: affirmative token / phrase / number matching against frozen
     ground truth HARDCODED in each ``verify_N.py`` (never in tasks.jsonl).
  4. DB after-state: initial (seed) vs after (instance) SQLite snapshots.
     Read-only tasks require every table row-identical to the seed; stateful
     tasks require the exact allowed row delta and nothing else (a new bookmark
     pair, a new review row with the projects histogram counters bumped, a new
     user with the profile country set).

Input signature (per task):
  --run_dir DIR        agent trajectory dir: trajectory.json + screenshots/step_NNN.png
  --initial_db PATH    initial-state SQLite DB (default: <run_dir>/initial.db, else
                       instance_seed from the container)
  --after_db PATH      after-state  SQLite DB (default: <run_dir>/after.db, else live
                       instance DB from the container)
  --container NAME     docker container to fetch DBs from (default: $WH_CONTAINER or
                       wh-sf-review)
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

SITE = "sourceforge"
DEFAULT_CONTAINER = os.environ.get("WH_CONTAINER", "wh-sf-review")

# ---------------------------------------------------------------- frozen seed contract
TABLES = ("activity_events", "bookmarks", "business_products", "country_stats",
          "download_stats", "forum_threads", "forums", "news_posts", "os_stats",
          "project_facets", "project_files", "projects", "reviews", "screenshots",
          "site_content", "thread_posts", "ticket_posts", "tickets", "users",
          "wiki_pages")
SEED_COUNTS = {"activity_events": 15, "bookmarks": 5, "business_products": 24,
               "country_stats": 12, "download_stats": 20, "forum_threads": 50,
               "forums": 2, "news_posts": 2, "os_stats": 6, "project_facets": 5201,
               "project_files": 34, "projects": 411, "reviews": 218,
               "screenshots": 703, "site_content": 11, "thread_posts": 8,
               "ticket_posts": 5, "tickets": 35, "users": 1994, "wiki_pages": 1}
# sha256 over sqlite_master (type, name, tbl_name, sql) of instance_seed/sourceforge.db.
SCHEMA_SHA256 = "aa61b172cfdf1d690836fd7618d98e9ae9735feb72e420c7a238a5d57549ecbd"
# sha256 over every seed row (table-canonical, ORDER BY all columns). The seed is
# built deterministically at image build time (PYTHONHASHSEED=0 + fixed index
# creation order) and reproduces byte-for-byte on every build (md5 523b5904…).
# r2 sync (c67fb235): 7-Zip/26.03 + 26.02 folder weekly counts seeded (29,589 /
# 21,750) and four new site_content rows (podcast/articles/case-studies/blog).
SEED_ROWS_SHA256 = "520501acb77f8ce6104960ea69f6fafca7e9977c6f9ae937c657c0a70d57f5f4"
SEED_USERS = {  # email -> (id, display); identity columns never change
    "alice.j@test.com": (1991, "Alice Johnson"),
    "bob.c@test.com": (1992, "Bob Chen"),
    "carol.d@test.com": (1993, "Carol Davis"),
    "david.k@test.com": (1994, "David Kim"),
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


def check_visited_path(judge, traj, name, pattern):
    hit = visited_path(traj, pattern)
    judge.check(name, hit, f"required path ~{pattern}"
                + ("" if hit else f" — visited: {[u.split('localhost')[-1] for u in trajectory_urls(traj)][:12]}"))


def check_answer_phrase(judge, answer, name, phrase, case_sensitive=False):
    if _is_plain_number(phrase):
        # A numeric phrase is a standalone token. "10" must not match inside
        # "109,095" and "25" must not match inside "2025".
        found = bool(number_spans(answer, phrase))
    else:
        hay = answer if case_sensitive else answer.casefold()
        needle = phrase if case_sensitive else phrase.casefold()
        found = needle in hay
    judge.check(name, found, f"answer must mention {phrase!r}")


def _norm_num(s):
    s = re.sub(r"[,\s]", "", str(s)).strip(".,")
    return s.lower()


_PLAIN_NUMBER_RE = re.compile(r"\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?")
_NUMBER_SPAN_RE = re.compile(
    # Sentence punctuation may follow a number ("4.8." / "27."). A dot that
    # continues a version ("4.8.1") does not end the token.
    r"(?<![A-Za-z0-9.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?(?!(?:\.\d)|[A-Za-z0-9])"
)
# Following-subject window is short so the next sentence's subject does not
# steal the previous sentence's number.
_FOLLOWING_WINDOW = 48


def _is_plain_number(value):
    return bool(re.fullmatch(_PLAIN_NUMBER_RE, str(value).strip()))


def _number_matches(whole_raw, frac, wanted):
    """Standalone numeric equality. Leading-zero tokens (date fragments like
    ``04``) are not the integer 4. ``2.0`` is not the integer 2."""
    whole = str(whole_raw).replace(",", "")
    raw = _norm_num(wanted)
    if not re.fullmatch(r"\d+(?:\.\d+)?", raw):
        return False
    if "." in raw:
        w_whole, w_frac = raw.split(".", 1)
    else:
        w_whole, w_frac = raw, None
    if len(whole) > 1 and whole[0] == "0":
        return False
    try:
        if int(whole) != int(w_whole):
            return False
    except ValueError:
        return False
    if (w_frac is None) != (frac is None):
        return False
    if w_frac is None:
        return True
    return frac.rstrip("0") == w_frac.rstrip("0")


def number_spans(answer, value):
    """(start, end) of standalone occurrences of ``value`` (comma or plain)."""
    spans = []
    for match in _NUMBER_SPAN_RE.finditer(str(answer)):
        if _number_matches(match.group(1), match.group(2), value):
            spans.append((match.start(), match.end()))
    return spans


def _phrase_spans(text, phrase):
    """Literal phrase hits that are not glued to a longer alphanumeric token.
    ``3.3B`` does not match inside ``13.3B``; ``10`` does not match inside ``109``.
    """
    hay = str(text).casefold()
    needle = str(phrase).casefold()
    if not needle:
        return []
    spans = []
    start = 0
    while True:
        index = hay.find(needle, start)
        if index < 0:
            break
        before = hay[index - 1] if index else " "
        after_at = index + len(needle)
        after = hay[after_at] if after_at < len(hay) else " "
        if before.isalnum() or after.isalnum():
            start = index + 1
            continue
        spans.append((index, after_at))
        start = after_at
    return spans


def _boundary_positions(text, needle):
    if not needle:
        return []
    hay = str(text).casefold()
    pattern = re.compile(
        r"(?<![a-z0-9])" + re.escape(str(needle).casefold()) + r"(?![a-z0-9])"
    )
    return [match.start() for match in pattern.finditer(hay)]


def _span_owner(text, start, end, candidates, window):
    """The subject that owns a span.

    Prefer the nearest preceding candidate. An immediately following label
    wins only when it is closer and no sentence break (period or semicolon)
    sits between the span and that label — so ``#2670 'CVE-...'`` binds to
    the CVE, while ``171 reviews. AutoClicker`` stays with the previous project.
    """
    preceding = []
    following = []
    for name in candidates:
        if not name:
            continue
        for pos in _boundary_positions(text, name):
            if pos <= start:
                dist = start - pos
                if dist <= window:
                    preceding.append((dist, name))
            else:
                dist = pos - end
                if dist <= window:
                    following.append((dist, name))
    preceding.sort()
    following.sort()
    if preceding and following:
        pdist, pname = preceding[0]
        fdist, fname = following[0]
        between = text[end:end + fdist]
        # Only an immediately attached label ("#2670 'CVE-...'") may outrank
        # a farther preceding subject. The next list item ("1,150), EspoCRM",
        # "priority 7, #2670") must not.
        attached_label = re.fullmatch(r"[\s'\"#(/)]*", between) is not None
        if attached_label and fdist <= 24 and fdist + 8 < pdist:
            return fname
        return pname
    if preceding:
        return preceding[0][1]
    if following and following[0][0] <= _FOLLOWING_WINDOW:
        return following[0][1]
    return None


def _near_ok(text, start, end, near, near_window):
    if not near:
        return True
    segment = text[max(0, start - near_window):min(len(text), end + near_window)]
    return re.search(near, segment, re.IGNORECASE) is not None


def _context_ok(text, start, end, context, context_window):
    if not context:
        return True
    segment = text[max(0, start - context_window):min(len(text), end + context_window)]
    return any(re.search(pattern, segment, re.IGNORECASE) for pattern in context)


def bound_to_subject(answer, spans, subject, competitors=(), window=420,
                     near=None, near_window=70, context=None, context_window=80):
    """True when some span is owned by ``subject`` (not a competitor) and any
    local ``near`` / ``context`` constraint holds for that same span."""
    if not spans or not subject:
        return False
    candidates = [subject, *(competitors or ())]
    for start, end in spans:
        if _span_owner(answer, start, end, candidates, window) != subject:
            continue
        if not _near_ok(answer, start, end, near, near_window):
            continue
        if not _context_ok(answer, start, end, context, context_window):
            continue
        return True
    return False


def number_bound_to_subject(answer, value, subject, competitors=(), window=420,
                            near=None, near_window=70, context=None,
                            context_window=80):
    return bound_to_subject(
        answer, number_spans(answer, value), subject, competitors, window,
        near, near_window, context, context_window,
    )


def phrase_bound_to_subject(answer, phrase, subject, competitors=(), window=420,
                            near=None, near_window=70, context=None,
                            context_window=80):
    spans = number_spans(answer, phrase) if _is_plain_number(phrase) else _phrase_spans(answer, phrase)
    return bound_to_subject(
        answer, spans, subject, competitors, window, near, near_window,
        context, context_window,
    )


def _binding_detail(value, label, subject, competitors, near):
    bits = [f"value {value!r} bound to {subject!r}"]
    if competitors:
        bits.append(f"not {list(competitors)!r}")
    if near:
        bits.append(f"near /{near}/")
    if label:
        bits.append(str(label))
    return "; ".join(bits)


def check_answer_number(judge, answer, name, value, label=None, *,
                        subject, competitors=(), window=420,
                        near=None, near_window=70, context=None,
                        context_window=80):
    """The number must be a standalone token owned by ``subject``.

    A correct integer elsewhere in the answer (another project's weekly
    count, a date fragment, a digit inside a longer id) does not count.
    """
    found = number_bound_to_subject(
        answer, value, subject, competitors, window, near, near_window,
        context, context_window,
    )
    judge.check(name, found, _binding_detail(value, label, subject, competitors, near))


def check_answer_phrase_near(judge, answer, name, phrase, *,
                             subject, competitors=(), window=420,
                             near=None, near_window=70, label=None):
    """A phrase (date, license, abbreviated total) owned by ``subject``."""
    found = phrase_bound_to_subject(
        answer, phrase, subject, competitors, window, near, near_window,
    )
    judge.check(name, found, _binding_detail(phrase, label, subject, competitors, near))


def check_answer_any(judge, answer, name, variants, label="", *,
                     subject, competitors=(), window=420,
                     near=None, near_window=70):
    """One of ``variants`` must be standalone and owned by ``subject``.

    Numeric variants use standalone number tokens. Abbreviated forms
    (``430M``) use boundary-aware phrase spans. Neither is a raw substring.
    """
    hit = False
    for variant in variants:
        if _is_plain_number(variant):
            if number_bound_to_subject(
                answer, variant, subject, competitors, window, near, near_window,
            ):
                hit = True
                break
        elif phrase_bound_to_subject(
            answer, variant, subject, competitors, window, near, near_window,
        ):
            hit = True
            break
    judge.check(
        name, hit,
        _binding_detail(list(variants), label, subject, competitors, near),
    )


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
    cache = Path(cache or os.environ.get("SOURCEFORGE_TEST_SEED_DB")
                 or Path("/tmp/sourceforge_verify_seed.db"))
    if cache.is_file():
        return cache
    return fetch_db(container or DEFAULT_CONTAINER,
                    f"/opt/WebSyn/{SITE}/instance_seed/{SITE}.db", cache)


def acquire_instance(container=None):
    container = container or DEFAULT_CONTAINER
    out = Path("/tmp") / f"sourceforge_verify_instance_{container}.db"
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
    judge.check("after_rows_unchanged", rows_digest(after_db) == SEED_ROWS_SHA256,
                "read-only task: after_db rows must equal the seed rows")


def check_only_tables_changed(judge, initial_db, after_db, allowed):
    """Every table outside `allowed` must be row-identical; allowed tables are
    checked by the task verifier with exact deltas."""
    for t in TABLES:
        if t in allowed:
            continue
        added, removed, changed = table_diff(initial_db, after_db, t)
        judge.check(f"table_{t}_untouched",
                    not (added or removed or changed),
                    f"added={list(added)[:3]} removed={list(removed)[:3]} changed={list(changed)[:3]}")


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
