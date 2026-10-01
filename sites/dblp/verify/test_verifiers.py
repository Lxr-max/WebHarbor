#!/usr/bin/env python3
"""test_verifiers.py — adversarial contract tests for the dblp verifier suite.

The r2 fix re-froze the verifiers for the 14 rewritten tasks (1, 2, 3, 4, 5,
6, 7, 10, 13, 14, 15, 16, 17, 18) from the contributor's honest Playwright
walks of the new task texts on the fix container wh-dblp-fix; the six
untouched verifiers (0, 8, 9, 11, 12, 19) stay frozen from the reviewer's
contract at orch/review/dblp @ 8348a8c2. The r3 fix repairs the mirror's
search-history dedup (a kind page reached from the combined results page
for the same query is the same search action and is not recorded twice;
every other search action records — even one whose text coincides with an
earlier history row), re-anchors verify_1/3/4/17 to exactly the values the
task texts ask the agent to report, syncs the two judge rubrics that
contradicted their task texts, and re-walks the six frozen tasks' honest
fixtures on the r3 fix container (their r1-code fixtures predate the
history-recording change and masked the t12 contract break). Seed identity
is the frozen logical contract (table counts + schema sha256 + rows
sha256); the raw seed file md5 is informational only and not file-level
deterministic across rebuilds.

Guarantees (run with pytest):
  * each honest fixture (the r2 fix-walk fixtures for the 14 re-frozen
    tasks, the r3 re-walk fixtures for the six frozen tasks) PASSES its
    verify_<n>.py;
  * every adversarial negative FAILS (zero false positives):
      - no-op trajectories (20),
      - answer-only shortcuts with no navigation (20),
      - wrong-answer trajectories (20, fabricated per task),
      - stale-DB trajectories (all 8 stateful tasks),
      - read-only violations (unexpected DB writes on read-only tasks),
      - tampered packages (wrong task_id / off-site URL / cross-port /
        not-terminated / empty answer / bad PNG / pre-mutated seed),
      - task-specific confusions (swapped counts / wrong titles).
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest

VERIFY = Path(__file__).resolve().parent
FIX_EV = Path("/data/zhaoyang-user-projects/websyn/wh-dblp-fix-evidence")
R3_EV = Path("/data/zhaoyang-user-projects/websyn/wh-dblp-fix-r3-evidence")
# tasks re-frozen for the r2 fixes: honest fixtures from the fix walks on
# the r2 fix container (the r3 code fix provably does not change these
# walks — the stateful ones contain no combined->kind chains and no
# re-searches, so the recorded history deltas are identical)
AFFECTED = {1, 2, 3, 4, 5, 6, 7, 10, 13, 14, 15, 16, 17, 18}
# the six contract-frozen tasks: honest fixtures re-walked on the r3 fix
# container with the repaired history recording
R3_RWALKED = {0, 8, 9, 11, 12, 19}
TMP = R3_EV / "verify_runs" / "_pytest_tmp"


def fixture_dir(n):
    return (FIX_EV if n in AFFECTED else R3_EV) / "runs" / str(n)
PY = sys.executable

TASK_IDS = [f"dblp--{n}" for n in range(20)]
STATEFUL = [8, 9, 10, 11, 12, 13, 14, 18]
READ_ONLY = [n for n in range(20) if n not in STATEFUL]


def run_verifier(n: int, run_dir: Path):
    proc = subprocess.run(
        [PY, str(VERIFY / f"verify_{n}.py"), "--run_dir", str(run_dir)],
        capture_output=True, text=True, timeout=180)
    try:
        verdict = json.loads(proc.stdout)
    except json.JSONDecodeError:
        verdict = {"pass": False, "reason": proc.stdout[-300:] or proc.stderr[-300:],
                   "evidence": []}
    return verdict


def clone(n: int, tag: str) -> Path:
    dst = TMP / f"{n}_{tag}"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(fixture_dir(n), dst)
    return dst


def set_traj(run_dir: Path, **changes):
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    traj.update(changes)
    p.write_text(json.dumps(traj, indent=2))


def mutate_answer(run_dir: Path, new_answer: str):
    set_traj(run_dir, final_answer=new_answer)


def mutate_db(run_dir: Path, which: str, sql: str):
    db = sqlite3.connect(run_dir / which)
    db.execute(sql)
    db.commit()
    db.close()


def drop_nav(run_dir: Path):
    """Strip all step URLs down to the bare start page (no tool navigation)."""
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    start = traj["start_url"]
    for step in traj.get("steps", []):
        step["url"] = start
        step["url_after"] = start
    p.write_text(json.dumps(traj, indent=2))


# ---------------------------------------------------------------- happy path
@pytest.mark.parametrize("n", range(20))
def test_honest_fixture_passes(n):
    verdict = run_verifier(n, fixture_dir(n))
    assert verdict["pass"], verdict["reason"]


# ---------------------------------------------------------------- no-op
@pytest.mark.parametrize("n", range(20))
def test_noop_fails(n):
    run_dir = clone(n, "noop")
    set_traj(run_dir, steps=[], final_answer="", terminated=False,
             termination_reason="max_steps")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]


# ---------------------------------------------------------------- shortcuts
@pytest.mark.parametrize("n", range(20))
def test_answer_only_shortcut_fails(n):
    run_dir = clone(n, "shortcut")
    drop_nav(run_dir)
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any("nav_" in e or "check" not in e
               for e in verdict["evidence"] if e.startswith("FAIL"))


# ---------------------------------------------------------------- wrong answers
def _wrong_answer(n: int, facts: dict, answer: str) -> str:
    """Fabricate a near-miss answer per task: keep the shape, corrupt values."""
    import re
    out = answer
    # bump/lower every number token by 1 in a copy — deterministic per task
    def bump(m):
        v = m.group(0)
        return str(int(v.replace(",", "")) + (1 if n % 2 else -1)) if v.isdigit() else v
    out = re.sub(r"\b\d+\b", bump, out)
    # swap two title-like phrases (first two long phrases)
    phrases = re.findall(r"[A-Z][^:\n]{25,}\.", out)
    if len(phrases) >= 2:
        out = out.replace(phrases[0], "@@SWAP@@", 1)
        out = out.replace(phrases[1], phrases[0], 1)
        out = out.replace("@@SWAP@@", phrases[1], 1)
    return out


@pytest.mark.parametrize("n", range(20))
def test_wrong_answer_fails(n):
    run_dir = clone(n, "wrong")
    traj = json.loads((run_dir / "trajectory.json").read_text())
    facts = json.loads((run_dir / "facts.json").read_text())
    mutate_answer(run_dir, _wrong_answer(n, facts, traj["final_answer"]))
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any(e.startswith("FAIL") for e in verdict["evidence"])


# ---------------------------------------------------------------- stale DB
@pytest.mark.parametrize("n", STATEFUL)
def test_stale_db_fails(n):
    """Grade a stateful task against an after.db that is just the seed:
    the required row delta is absent -> FAIL."""
    run_dir = clone(n, "stale")
    shutil.copy(run_dir / "initial.db", run_dir / "after.db")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]


# ---------------------------------------------------------------- read-only violation
@pytest.mark.parametrize("n", READ_ONLY)
def test_readonly_violation_fails(n):
    run_dir = clone(n, "write")
    mutate_db(run_dir, "after.db",
              "INSERT INTO saved_papers (user_id, publication_id, collection, "
              "note, saved_at) VALUES (1, 1, 'rogue', NULL, '2026-09-30')")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]


# ---------------------------------------------------------------- tampered packages
@pytest.mark.parametrize("n", [0])
def test_wrong_task_id_fails(n):
    run_dir = clone(n, "tid")
    set_traj(run_dir, task_id="dblp--19")
    assert not run_verifier(n, run_dir)["pass"]


@pytest.mark.parametrize("n", [0])
def test_offsite_url_fails(n):
    run_dir = clone(n, "offsite")
    set_traj(run_dir, start_url="https://dblp.org/")
    assert not run_verifier(n, run_dir)["pass"]


@pytest.mark.parametrize("n", [0])
def test_cross_port_url_fails(n):
    run_dir = clone(n, "xport")
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    port = urlparse(traj["start_url"]).port
    bad = f":{port + 1000}"
    for step in traj["steps"]:
        step["url"] = step["url"].replace(f":{port}", bad)
        step["url_after"] = step["url_after"].replace(f":{port}", bad)
    p.write_text(json.dumps(traj, indent=2))
    assert not run_verifier(n, run_dir)["pass"]


@pytest.mark.parametrize("n", [0])
def test_not_terminated_fails(n):
    run_dir = clone(n, "term")
    set_traj(run_dir, terminated=False, termination_reason="max_steps")
    assert not run_verifier(n, run_dir)["pass"]


@pytest.mark.parametrize("n", [0])
def test_empty_answer_fails(n):
    run_dir = clone(n, "empty")
    mutate_answer(run_dir, "")
    assert not run_verifier(n, run_dir)["pass"]


@pytest.mark.parametrize("n", [0])
def test_bad_png_fails(n):
    run_dir = clone(n, "png")
    shots = sorted((run_dir / "screenshots").glob("step_*.png"))
    shots[0].write_bytes(b"not a png")
    assert not run_verifier(n, run_dir)["pass"]


@pytest.mark.parametrize("n", [0])
def test_pre_mutated_seed_fails(n):
    run_dir = clone(n, "seedmut")
    mutate_db(run_dir, "initial.db",
              "INSERT INTO saved_papers (user_id, publication_id, collection, "
              "note, saved_at) VALUES (1, 1, 'rogue', NULL, '2026-09-30')")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any("seed" in e for e in verdict["evidence"] if e.startswith("FAIL"))


# ---------------------------------------------------------------- confusions
def test_t0_wrong_year_count_fails():
    run_dir = clone(0, "yc")
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    answer = traj["final_answer"].replace("year_count: 58", "year_count: 57")
    mutate_answer(run_dir, answer)
    verdict = run_verifier(0, run_dir)
    assert not verdict["pass"]


def test_t1_wrong_coauthor_fails():
    run_dir = clone(1, "co")
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    answer = traj["final_answer"].replace("Bowen Jin", "Jiawei Han 0002")
    mutate_answer(run_dir, answer)
    assert not run_verifier(1, run_dir)["pass"]


def test_t2_wrong_sigmod_records_fails():
    run_dir = clone(2, "sr")
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    answer = traj["final_answer"].replace("sigmod_records: 726",
                                          "sigmod_records: 725")
    mutate_answer(run_dir, answer)
    assert not run_verifier(2, run_dir)["pass"]


def test_t3_wrong_bibtex_key_fails():
    run_dir = clone(3, "bk")
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    answer = traj["final_answer"].replace("DBLP:conf/nips/AamandCDMNSX25",
                                           "DBLP:conf/nips/AamandCDMNSX24")
    mutate_answer(run_dir, answer)
    assert not run_verifier(3, run_dir)["pass"]


def test_t5_swapped_venue_counts_fails():
    run_dir = clone(5, "svc")
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    answer = traj["final_answer"].replace("tods_records: 84", "tods_records: 693") \
                                  .replace("tois_records: 693", "tois_records: 84")
    mutate_answer(run_dir, answer)
    assert not run_verifier(5, run_dir)["pass"]


def test_t8_wrong_remaining_fails():
    run_dir = clone(8, "rem")
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    answer = traj["final_answer"].replace("Security reading", "My Library")
    mutate_answer(run_dir, answer)
    assert not run_verifier(8, run_dir)["pass"]


def test_t13_wrong_final_history_fails():
    run_dir = clone(13, "fh")
    mutate_db(run_dir, "after.db",
              "INSERT INTO search_history (user_id, query, search_type, hits, "
              "ran_at) VALUES (4, 'extra query', 'publ', 1, '2026-09-30 00:00')")
    assert not run_verifier(13, run_dir)["pass"]


def test_t14_unrestored_affiliation_fails():
    run_dir = clone(14, "aff")
    mutate_db(run_dir, "after.db",
             "UPDATE users SET affiliation='MIT CSAIL' WHERE id=1")
    verdict = run_verifier(14, run_dir)
    assert not verdict["pass"]
