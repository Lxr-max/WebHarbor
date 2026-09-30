#!/usr/bin/env python3
"""Adversarial contract tests for the coinmarketcap verifier suite.

For each of the 23 CoinMarketCap--* tasks this suite proves, against the
reviewer's honest-walk fixtures (runs/ produced on wh-coinmarketcap-review):

  PASS case     the honest walk package (real Playwright trajectory + real
                walked answer + real initial/after DB snapshots) PASSES
                (fixtures re-frozen from the r2-fix round-2 walks; the six
                deepened tasks were walked twice with identical step
                counts).
  no-op case    an agent that opens the homepage, does nothing else and
                answers nothing FAILS (fail-closed identity gate).
  shortcut case the full correct answer text but NO on-site navigation
                FAILS (anti knowledge-shortcut navigation gates).
  wrong-answer  the real honest trajectory with every ground-truth value
                corrupted in the final answer FAILS.
  stale-DB     (stateful tasks 6/7/8/21) the honest trajectory + answer
                against an UNCHANGED database FAILS (after-state gates).
  extra-writes  (stateful tasks) the honest answer with one extra
                watchlist row in the after DB FAILS.
  confusion     running verifier N against task M's package FAILS.

Exit code 0 = every case behaved as designed.
"""
from __future__ import annotations

import json
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

VERIFY_DIR = Path(__file__).resolve().parent
SITE = "coinmarketcap"
# Honest-walk fixture roots: the contributor's two independent Playwright
# rounds on the r2-fix container (wh-coinmarketcap-fix2, image seed md5
# 990af4a5…). Round 2 is the frozen fixture set; round 1 lives alongside it
# as the depth-reproduction round.
RUNS = Path("/data/zhaoyang-user-projects/websyn/wh-coinmarketcap-fix2-evidence/runs_round2")
STATEFUL = {6, 7, 8, 21}

PY = sys.executable


def run_verifier(n: int, run_dir: Path, expect_pass: bool) -> tuple[bool, str]:
    r = subprocess.run(
        [PY, str(VERIFY_DIR / f"verify_{n}.py"), "--run_dir", str(run_dir)],
        capture_output=True, text=True, timeout=300)
    try:
        out = json.loads(r.stdout)
        passed = bool(out.get("pass"))
        reason = out.get("reason", "")[:160]
    except json.JSONDecodeError:
        passed = False
        reason = (r.stderr or r.stdout or "")[-200:]
    ok = (passed == expect_pass)
    return ok, reason


def copy_pkg(src: Path, dst: Path) -> Path:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
    return dst


def mutate_traj(pkg: Path, fn) -> None:
    p = pkg / "trajectory.json"
    traj = json.loads(p.read_text())
    fn(traj)
    p.write_text(json.dumps(traj, indent=1))


def fresh_tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix=f"{SITE}-contract-"))


def main() -> int:
    failures = []
    tmp = fresh_tmp()
    for n in range(23):
        src = RUNS / str(n)
        if not (src / "trajectory.json").is_file():
            failures.append(f"T{n}: missing honest fixture {src}")
            continue
        # 1. honest PASS
        ok, why = run_verifier(n, src, expect_pass=True)
        if not ok:
            failures.append(f"T{n}: honest walk should PASS but FAILED ({why})")
        # 2. no-op (homepage only, empty answer, pristine DB)
        pkg = copy_pkg(src, tmp / f"noop-{n}")
        def noop(t):
            t["steps"] = [t["steps"][0]] if t.get("steps") else []
            t["final_answer"] = ""
        mutate_traj(pkg, noop)
        ok, why = run_verifier(n, pkg, expect_pass=False)
        if not ok:
            failures.append(f"T{n}: no-op should FAIL but PASSED")
        # 3. shortcut: correct answer, no navigation beyond the homepage
        pkg = copy_pkg(src, tmp / f"shortcut-{n}")
        def shortcut(t):
            start = t.get("start_url", "http://localhost:47120/")
            for s in t.get("steps", []):
                s["url"] = start
                s["url_after"] = start
        mutate_traj(pkg, shortcut)
        ok, why = run_verifier(n, pkg, expect_pass=False)
        if not ok:
            failures.append(f"T{n}: shortcut (answer-only, no navigation) should FAIL but PASSED")
        # 4. wrong answer: corrupt every ground-truth number in the answer
        pkg = copy_pkg(src, tmp / f"wrong-{n}")
        def corrupt(t):
            ans = t.get("final_answer", "")

            def bump(m):
                head = m.group(1) or ""
                return head + str(int(m.group(2).replace(",", "")) + 7)

            out = re.sub(r"([$,])(\d[\d,]*)", bump, ans)
            # letter-level corruption so phrase gates trip too
            out = out.replace("o", "0").replace("O", "0")
            t["final_answer"] = out
        mutate_traj(pkg, corrupt)
        ok, why = run_verifier(n, pkg, expect_pass=False)
        if not ok:
            failures.append(f"T{n}: wrong-answer should FAIL but PASSED")
        # 5. confusion: verify with another task's package
        m = (n + 1) % 23
        ok, why = run_verifier(n, RUNS / str(m), expect_pass=False)
        if not ok:
            failures.append(f"T{n}: task-confusion package should FAIL but PASSED")
        # 6. stateful DB gates
        if n in STATEFUL:
            # stale DB: after == initial
            pkg = copy_pkg(src, tmp / f"stale-{n}")
            shutil.copy(pkg / "initial.db", pkg / "after.db")
            ok, why = run_verifier(n, pkg, expect_pass=False)
            if not ok:
                failures.append(f"T{n}: stale-DB should FAIL but PASSED")
            # extra writes: inject one extra watchlist row into after.db
            pkg = copy_pkg(src, tmp / f"extra-{n}")
            db = sqlite3.connect(pkg / "after.db")
            try:
                cols = [r[1] for r in db.execute("PRAGMA table_info(watchlist_items)")]
                assert cols, "watchlist_items missing"
                db.execute("INSERT INTO watchlist_items (user_id, coin_id, added_at) "
                           "VALUES (3, 39920, '2026-09-29')")
                db.commit()
            finally:
                db.close()
            ok, why = run_verifier(n, pkg, expect_pass=False)
            if not ok:
                failures.append(f"T{n}: extra-writes should FAIL but PASSED")

    shutil.rmtree(tmp, ignore_errors=True)
    total = 23
    adversarial = (23 * 4) + len(STATEFUL) * 2
    if failures:
        print(f"CONTRACT FAILURES ({len(failures)}):")
        for f in failures:
            print("  -", f)
        return 1
    print(f"contract OK: {total} honest PASS + {total} no-op FAIL + {total} shortcut FAIL "
          f"+ {total} wrong-answer FAIL + {total} confusion FAIL "
          f"+ {len(STATEFUL)} stale-DB FAIL + {len(STATEFUL)} extra-writes FAIL "
          f"= zero false positives")
    return 0


def test_contract_all_tasks():
    """Pytest entry: the full honest+adversarial matrix must be green."""
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
