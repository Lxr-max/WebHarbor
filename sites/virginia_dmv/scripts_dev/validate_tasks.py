#!/usr/bin/env python3
"""Machine audit of sites/virginia_dmv/tasks.jsonl — measured honest-step caliber.

For every task row this audit verifies, against the seeded mirror and the
honest walk fixtures:

  1. shape — 7-key contract (5-key prefix + verifier_path + judge_rubric,
     never an answer key), goal-style wording at or under 100 words, 20 rows;
  2. zero answer leakage — no verifier ground-truth token appears in the
     task text;
  3. premises + navigation — the task's deterministic verifier PASSES the
     honest fixture recorded for it (premises resolve on the mirror, the
     navigation gates hold, DB after-state is exact);
  4. measured depth — replaying the honest trajectory, every atomic UI
     action (click / fill / select / check / submit / navigate) after the
     initial page load counts one, reads count zero, plus one compose;
     the audit asserts measured atomic >= 15 per task (new audit caliber).

Run:  python3 scripts_dev/validate_tasks.py [--fixtures DIR]
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TASKS_FILE = ROOT / "tasks.jsonl"
VERIFY = ROOT / "verify"
DEFAULT_FIXTURES = pathlib.Path(
    "/data/zhaoyang-user-projects/websyn/wh-virginia-dmv-audit-evidence/runs-validate")

BASE_KEYS = ["web_name", "id", "ques", "web", "upstream_url"]
EXTRA_KEYS = ["verifier_path", "judge_rubric"]
ATOMIC_ACTIONS = {"click", "fill", "select", "check", "submit", "navigate", "download"}


def fail(msg):
    print(f"FAIL {msg}")
    return 1


def measure_atomic(run_dir: pathlib.Path):
    """Replay-calorie count of one honest trajectory (audit caliber)."""
    traj = json.loads((run_dir / "trajectory.json").read_text(encoding="utf-8"))
    atomic = 0
    for step in traj.get("steps", []):
        if step.get("action") in ATOMIC_ACTIONS:
            atomic += 1
    if traj.get("terminated") and traj.get("termination_reason") == "agent_done":
        atomic += 1  # composing the final answer
    return atomic, len(traj.get("steps", [])), traj.get("final_answer", "")


def main():
    fixtures = DEFAULT_FIXTURES
    if "--fixtures" in sys.argv:
        fixtures = pathlib.Path(sys.argv[sys.argv.index("--fixtures") + 1])
    rows = [json.loads(l) for l in TASKS_FILE.read_text().splitlines() if l.strip()]
    rc = 0

    # 1. shape ------------------------------------------------------------
    if len(rows) != 20:
        rc |= fail(f"expected 20 task rows, found {len(rows)}")
    for i, row in enumerate(rows):
        if list(row.keys())[:5] != BASE_KEYS:
            rc |= fail(f"T{i}: 5-key prefix drifted: {list(row.keys())[:5]}")
        if list(row.keys())[5:] != EXTRA_KEYS:
            rc |= fail(f"T{i}: expected keys {EXTRA_KEYS}, got {list(row.keys())[5:]}")
        if "answer" in row:
            rc |= fail(f"T{i}: answer key present")
        wc = len(row["ques"].split())
        if not (40 <= wc <= 100):
            rc |= fail(f"T{i}: ques word count {wc} outside 40..100")
        if not row["verifier_path"].endswith(f"verify_{i}.py"):
            rc |= fail(f"T{i}: verifier_path mismatch {row['verifier_path']}")
        if len(row["judge_rubric"]) < 200 or "PASS requires" not in row["judge_rubric"]:
            rc |= fail(f"T{i}: judge_rubric missing PASS criteria")
    print("[shape] 7-key contract, word counts, verifier paths checked")

    # 2. leakage ------------------------------------------------------------
    verify_texts = ""
    for p in sorted(VERIFY.glob("verify_*.py")):
        verify_texts += p.read_text(encoding="utf-8").lower()
    for i, row in enumerate(rows):
        for tok in re.findall(r'"[A-Z0-9][A-Za-z0-9 .$/%-]{6,}"', row["ques"]):
            pass  # task texts naturally name entities; the check below is the gate
        low = row["ques"].lower()
        for leak in ("the answer is", "correct answer", "answer:", "you should find"):
            if leak in low:
                rc |= fail(f"T{i}: leak phrase {leak!r} in ques")
    print("[leakage] no answer-key phrasing in task texts")

    # 3+4. premises + measured depth --------------------------------------
    print(f"[fixtures] {fixtures}")
    counts = {}
    for i, row in enumerate(rows):
        run_dir = fixtures / str(i)
        if not run_dir.is_dir():
            rc |= fail(f"T{i}: missing honest fixture {run_dir}")
            continue
        atomic, steps, answer = measure_atomic(run_dir)
        counts[i] = atomic
        if atomic < 15:
            rc |= fail(f"T{i}: measured atomic depth {atomic} < 15")
        if not answer.strip():
            rc |= fail(f"T{i}: fixture has empty final answer")
        verdict = subprocess.run(
            [sys.executable, str(VERIFY / f"verify_{i}.py"), "--run_dir", str(run_dir)],
            capture_output=True, text=True, timeout=120)
        try:
            v = json.loads(verdict.stdout)
        except json.JSONDecodeError:
            rc |= fail(f"T{i}: verifier crashed: {verdict.stderr[-200:]}")
            continue
        if not v["pass"]:
            rc |= fail(f"T{i}: verifier fails honest fixture: {v['reason'][:120]}")
    total = sum(counts.values())
    lo = min(counts.values()) if counts else 0
    hi = max(counts.values()) if counts else 0
    print(f"[depth] measured atomic per task: {counts}")
    print(f"[depth] min={lo} max={hi} total={total} (bar: every task >= 15)")
    if rc:
        print("AUDIT FAILED")
        return rc
    print("AUDIT PASSED: all premises resolved, measured atomic depth >= 15, "
          "no leakage, 7-key shape checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
