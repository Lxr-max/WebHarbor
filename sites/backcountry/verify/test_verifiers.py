#!/usr/bin/env python3
"""test_verifiers.py — adversarial contract tests for the backcountry
verifier suite (reviewer-authored).

Guarantees (run with pytest):
  * each honest fixture — the reviewer's own minimal-honest-path Playwright
    walks of the review container (seed md5 44da2a3fc213b3ac5e76ba11453baee2,
    image webharbor:bc-review-dev built from this branch) — PASSES its
    verify_<n>.py, and its walked depth clears the 15-step floor;
  * every adversarial negative FAILS (zero false positives):
      - no-op trajectories (homepage only, non-answer, clean DB),
      - answer-only shortcuts (honest answers pasted, zero navigation),
      - wrong-answer trajectories (honest navigation, poisoned answer),
      - stale-DB trajectories (honest trajectory, pristine after.db) —
        except the net-zero tasks whose sanctioned writes cancel out by
        design (T2/T6 wish-list add+remove, T11 address add+delete), which
        the navigation + answer gates must still cover via the no-op,
        answer-only and wrong-answer negatives,
      - tampered packages (wrong task_id / off-site URL / not-terminated /
        bad PNG / pre-mutated seed),
      - foreign after.db (the snapshot of a different task).
Ground truth lives hardcoded in the verify_<n>.py files; this suite never
reads tasks.jsonl.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

VERIFY = Path(__file__).resolve().parent
EV = Path("/data/zhaoyang-user-projects/websyn/wh-backcountry-review-evidence")
FIXTURES = EV / "runs" / "minimal_r1"
TMP = EV / "verify_runs" / "_pytest_tmp"
PY = sys.executable

# tasks whose sanctioned DB writes cancel out (add + remove of the same
# row): a stale-DB cheat is indistinguishable from a genuine completion,
# so the stale negative is not asserted for them (documented limitation;
# the no-op / answer-only / wrong-answer negatives still gate them).
NET_ZERO = {2, 6, 11}
MIN_HONEST_STEPS = 15


def run_verifier(n: int, run_dir: Path):
    proc = subprocess.run(
        [PY, str(VERIFY / f"verify_{n}.py"), "--run_dir", str(run_dir)],
        capture_output=True, text=True, timeout=180)
    try:
        verdict = json.loads(proc.stdout)
    except json.JSONDecodeError:
        verdict = {"pass": False, "reason": proc.stdout[-300:] or proc.stderr[-300:]}
    return verdict


def clone(n: int, tag: str) -> Path:
    dst = TMP / f"{n}_{tag}"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(FIXTURES / f"task_{n}", dst)
    return dst


def set_traj(run_dir: Path, **changes):
    p = run_dir / "trajectory.json"
    t = json.loads(p.read_text())
    t.update(changes)
    p.write_text(json.dumps(t))


# ---------------------------------------------------------------- honest
@pytest.mark.parametrize("n", range(20))
def test_honest_walk_passes(n):
    v = run_verifier(n, FIXTURES / f"task_{n}")
    assert v["pass"], f"honest walk for task {n} must PASS: {v['reason']}"


@pytest.mark.parametrize("n", range(20))
def test_honest_depth_at_least_15(n):
    t = json.loads((FIXTURES / f"task_{n}" / "trajectory.json").read_text())
    # walked steps include the initial home nav the benchmark agent gets for
    # free; the composed answer is the +1 — net honest depth == len(steps)
    assert len(t["steps"]) >= MIN_HONEST_STEPS, (
        f"task {n} honest depth {len(t['steps'])} < {MIN_HONEST_STEPS}")


# ------------------------------------------------------------- negatives
@pytest.mark.parametrize("n", range(20))
def test_noop_fails(n):
    d = clone(n, "t_noop")
    first_shot = sorted((d / "screenshots").glob("step_*.png"))[0]
    set_traj(d, steps=[{"action": "open home", "url": json.loads(
        (d / "trajectory.json").read_text())["start_url"],
        "note": "open home", "screenshot": first_shot.name}],
        final_answer="I browsed the homepage but did not complete the task.")
    shutil.copy(d / "initial.db", d / "after.db")
    assert not run_verifier(n, d)["pass"], f"no-op must FAIL for task {n}"


@pytest.mark.parametrize("n", range(20))
def test_answer_only_fails(n):
    d = clone(n, "t_ansonly")
    set_traj(d, steps=[])
    assert not run_verifier(n, d)["pass"], (
        f"answer-only shortcut must FAIL for task {n}")


@pytest.mark.parametrize("n", range(20))
def test_wrong_answer_fails(n):
    d = clone(n, "t_wrong")
    set_traj(d, final_answer="The answer is 42 dollars, 7 reviews, product X, "
                             "order 12345, total 99.99.")
    assert not run_verifier(n, d)["pass"], (
        f"wrong answer must FAIL for task {n}")


@pytest.mark.parametrize("n", [x for x in range(20) if x not in NET_ZERO])
def test_stale_db_fails(n):
    d = clone(n, "t_stale")
    shutil.copy(d / "initial.db", d / "after.db")
    assert not run_verifier(n, d)["pass"], (
        f"stale DB (no sanctioned writes) must FAIL for task {n}")


@pytest.mark.parametrize("n", range(20))
def test_wrong_task_id_fails(n):
    d = clone(n, "t_wrongid")
    set_traj(d, task_id="Backcountry--999")
    assert not run_verifier(n, d)["pass"], f"wrong task_id must FAIL for {n}"


@pytest.mark.parametrize("n", range(20))
def test_offsite_url_fails(n):
    d = clone(n, "t_offsite")
    t = json.loads((d / "trajectory.json").read_text())
    t["steps"][0]["url"] = "https://example.com/leak"
    (d / "trajectory.json").write_text(json.dumps(t))
    assert not run_verifier(n, d)["pass"], f"off-site URL must FAIL for {n}"


@pytest.mark.parametrize("n", range(20))
def test_not_terminated_fails(n):
    d = clone(n, "t_notdone")
    set_traj(d, terminated=False, termination_reason="max_steps")
    assert not run_verifier(n, d)["pass"], (
        f"unterminated trajectory must FAIL for {n}")


@pytest.mark.parametrize("n", range(20))
def test_bad_png_fails(n):
    d = clone(n, "t_badpng")
    shots = sorted((d / "screenshots").glob("step_*.png"))
    shots[0].write_bytes(b"not a png at all")
    assert not run_verifier(n, d)["pass"], f"bad PNG must FAIL for {n}"


@pytest.mark.parametrize("n", range(20))
def test_premutated_seed_fails(n):
    d = clone(n, "t_badseed")
    con = sqlite3.connect(d / "initial.db")
    con.execute("UPDATE products SET review_count = review_count + 1 "
                "WHERE rowid = (SELECT MIN(rowid) FROM products)")
    con.commit()
    con.close()
    assert not run_verifier(n, d)["pass"], (
        f"pre-mutated seed must FAIL for {n}")


@pytest.mark.parametrize("n", range(20))
def test_foreign_after_db_fails(n):
    d = clone(n, "t_foreign")
    foreign = FIXTURES / f"task_{(n + 7) % 20}" / "after.db"
    shutil.copy(foreign, d / "after.db")
    assert not run_verifier(n, d)["pass"], (
        f"foreign after.db must FAIL for task {n}")


# ------------------------------------------------------- frozen constants
def test_frozen_seed_contract_constants():
    sys.path.insert(0, str(VERIFY))
    import verify_lib
    assert verify_lib.SEED_COUNTS["products"] == 207
    assert verify_lib.SEED_COUNTS["reviews"] == 1677
    assert verify_lib.SEED_COUNTS["questions"] == 99
    assert verify_lib.SEED_COUNTS["users"] == 4
    assert verify_lib.SEED_COUNTS["brands"] == 972
    assert verify_lib.SEED_FILE_MD5 == "44da2a3fc213b3ac5e76ba11453baee2"
    assert len(verify_lib.SEED_COUNTS) == 20


def test_rubrics_carry_no_answer_values():
    """judge_rubric rows must be pure rules: no parenthesised ground-truth
    fragments (the agent reads tasks.jsonl; answers live only in verifiers)."""
    import re
    site = VERIFY.parent
    for line in (site / "tasks.jsonl").read_text().splitlines():
        row = json.loads(line)
        rubric = row["judge_rubric"]
        assert rubric.startswith("FACT CHECKPOINTS:"), row["id"]
        assert not re.search(r"\(([^)]{2,60})\)", rubric), (
            f"{row['id']} rubric carries parenthesised fragments")
        assert "empty" in rubric.lower(), (
            f"{row['id']} rubric must state the empty-answer FAIL rule")
