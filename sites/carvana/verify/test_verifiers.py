#!/usr/bin/env python3
"""test_verifiers.py — adversarial contract tests for the carvana r2
verifiers (reviewer contract, orch/review/carvana r2 sync @ 2045497d).

Every case besides the honest fixtures is adversarial and MUST FAIL the
corresponding verifier (zero false positives):

  A. honest fixtures ......... 21 real Playwright walks (runs_traj_r2) -> PASS
  B. no-op runs ............... zero steps + a canned answer -> FAIL
  C. answer-only shortcuts ... zero steps + the FULL correct answer
                               -> FAIL (navigation gates)
  D. wrong answers ........... honest navigation, every number anchor
                               falsified -> FAIL
  E. stale DB ................ honest run graded against a pre-mutated
                               initial DB -> FAIL (seed identity gate)
  F. write violations ........ honest read-only walk + an injected
                               favorite row in the after DB -> FAIL;
                               stateful walk graded against an after DB
                               missing its required state -> FAIL
  G. tampered packages ....... wrong task_id / off-site URL / not
                               terminated / empty answer / bad PNG -> FAIL
  H. r2 anchor regressions ... the OLD defective truths must FAIL:
                               T14 answer with the money-rendered
                               "$53,866" snapshot; T19 with the old
                               $28,043 financed figure; T8 with the
                               wrong-car (4751227) estimator values
                               $435/$374.
"""
from __future__ import annotations

import json
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
EV = Path("/data/zhaoyang-user-projects/websyn/wh-carvana-review-evidence")
HONEST = EV / "runs_traj_r2"
SEED_REF = Path("/tmp/carvana-seed-ref-r2.db")
PY = sys.executable

TASK_IDS = [f"Carvana--{n}" for n in range(21)]


def run_verifier(n, run_dir, extra=()):
    v = HERE / f"verify_{n}.py"
    out = subprocess.run([PY, str(v), "--run_dir", str(run_dir), "--no_llm", "true",
                          *extra], capture_output=True, text=True, timeout=120)
    try:
        payload = json.loads(out.stdout)
    except json.JSONDecodeError:
        payload = {"pass": False, "reason": out.stdout[-300:] + out.stderr[-300:]}
    return payload, out.returncode


def clone(run_src: Path, dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(run_src, dest)
    return dest


def falsify(answer: str) -> str:
    """Corrupt every integer token by appending a digit — every number
    anchor then misses (deterministic wrong-answer fixture)."""
    def bump(m):
        tok = m.group(0)
        head = tok.rstrip(",.")
        tail = tok[len(head):]
        return head + "7" + tail
    return re.sub(r"\d[\d,\.]*", bump, answer)


# ------------------------------------------------------------------ A. honest
@pytest.mark.parametrize("n", range(21))
def test_honest_fixture_passes(n):
    payload, code = run_verifier(n, HONEST / str(n))
    assert payload["pass"] is True, payload["reason"]
    assert code == 0


# ------------------------------------------------------------- B. no-op runs
@pytest.mark.parametrize("n", range(21))
def test_noop_run_fails(n, tmp_path):
    run = tmp_path / f"noop{n}"
    (run / "screenshots").mkdir(parents=True)
    shutil.copy2(SEED_REF, run / "initial.db")
    shutil.copy2(SEED_REF, run / "after.db")
    (run / "trajectory.json").write_text(json.dumps({
        "task_id": f"Carvana--{n}", "start_url": "http://localhost:46119/",
        "steps": [], "terminated": True, "termination_reason": "agent_done",
        "final_answer": "I know this site from memory: the answer follows "
                        "directly from my prior knowledge of the data.",
    }))
    payload, code = run_verifier(n, run)
    assert payload["pass"] is False
    assert code == 1


# ---------------------------------------------------- C. answer-only shortcut
@pytest.mark.parametrize("n", range(21))
def test_answer_only_shortcut_fails(n, tmp_path):
    """Full correct answer, zero navigation (knowledge shortcut)."""
    answer = json.loads((HONEST / str(n) / "trajectory.json").read_text())["final_answer"]
    run = tmp_path / f"shortcut{n}"
    (run / "screenshots").mkdir(parents=True)
    shutil.copy2(SEED_REF, run / "initial.db")
    shutil.copy2(SEED_REF, run / "after.db")
    (run / "trajectory.json").write_text(json.dumps({
        "task_id": f"Carvana--{n}", "start_url": "http://localhost:46119/",
        "steps": [], "terminated": True, "termination_reason": "agent_done",
        "final_answer": answer,
    }))
    payload, code = run_verifier(n, run)
    assert payload["pass"] is False
    assert code == 1


# ---------------------------------------------------- D. wrong answers
@pytest.mark.parametrize("n", range(21))
def test_wrong_answer_fails(n, tmp_path):
    """Honest navigation, every number anchor falsified -> FAIL."""
    run = clone(HONEST / str(n), tmp_path / f"wrong{n}")
    traj = json.loads((run / "trajectory.json").read_text())
    traj["final_answer"] = falsify(traj["final_answer"])
    (run / "trajectory.json").write_text(json.dumps(traj))
    payload, code = run_verifier(n, run)
    assert payload["pass"] is False
    assert code == 1


# ------------------------------------------------------------- E. stale DB
def test_stale_initial_db_fails(tmp_path):
    """Honest run graded against a pre-mutated initial DB -> seed gate."""
    run = clone(HONEST / "0", tmp_path / "stale0")
    con = sqlite3.connect(run / "initial.db")
    con.execute("INSERT INTO favorites(id, user_id, vehicle_id, saved_at) "
                "VALUES (99, 1, 1, '2026-09-29')")
    con.commit()
    con.close()
    payload, code = run_verifier(0, run)
    assert payload["pass"] is False
    assert code == 1
    assert "seed" in payload["reason"]


# ------------------------------------------------------ F. write violations
def test_readonly_write_violation_fails(tmp_path):
    """Honest read-only walk + an injected favorite row in the after DB."""
    run = clone(HONEST / "0", tmp_path / "dirty0")
    con = sqlite3.connect(run / "after.db")
    con.execute("INSERT INTO favorites(id, user_id, vehicle_id, saved_at) "
                "VALUES (99, 1, 1, '2026-09-29')")
    con.commit()
    con.close()
    payload, code = run_verifier(0, run)
    assert payload["pass"] is False
    assert code == 1
    assert "db_read_only" in payload["reason"]


def test_stateful_under_reach_fails(tmp_path):
    """Stateful checkout walk graded against an after DB missing its order."""
    run = clone(HONEST / "4", tmp_path / "under4")
    shutil.copy2(run / "initial.db", run / "after.db")
    payload, code = run_verifier(4, run)
    assert payload["pass"] is False
    assert code == 1


def test_stateful_wrong_field_fails(tmp_path):
    """The placed order must carry the exact financed terms."""
    run = clone(HONEST / "4", tmp_path / "badfield4")
    con = sqlite3.connect(run / "after.db")
    con.execute("UPDATE orders SET monthly_payment = 12345")
    con.commit()
    con.close()
    payload, code = run_verifier(4, run)
    assert payload["pass"] is False
    assert code == 1


def test_saved_state_missing_fails(tmp_path):
    """T5 without the Model Y favorite row in the after DB -> FAIL."""
    run = clone(HONEST / "5", tmp_path / "nosave5")
    con = sqlite3.connect(run / "after.db")
    con.execute("DELETE FROM favorites WHERE user_id = 1 "
                "AND vehicle_id = (SELECT id FROM vehicles WHERE vehicle_id = 4650840)")
    con.commit()
    con.close()
    payload, code = run_verifier(5, run)
    assert payload["pass"] is False
    assert code == 1


# ------------------------------------------------------- G. tampered packages
def test_wrong_task_id_fails(tmp_path):
    run = clone(HONEST / "0", tmp_path / "wid0")
    traj = json.loads((run / "trajectory.json").read_text())
    traj["task_id"] = "Carvana--1"
    (run / "trajectory.json").write_text(json.dumps(traj))
    payload, code = run_verifier(0, run)
    assert payload["pass"] is False
    assert code == 1
    assert "task_id" in payload["reason"]


def test_offsite_url_fails(tmp_path):
    run = clone(HONEST / "1", tmp_path / "offsite1")
    traj = json.loads((run / "trajectory.json").read_text())
    traj["steps"].append({"n": 99, "action": "navigate",
                         "url": "http://evil.example.com/cars",
                         "url_after": "http://evil.example.com/cars",
                         "params": {}, "screenshot_after": "step_001.png"})
    (run / "trajectory.json").write_text(json.dumps(traj))
    payload, code = run_verifier(1, run)
    assert payload["pass"] is False
    assert code == 1
    assert "same_origin" in payload["reason"]


def test_not_terminated_fails(tmp_path):
    run = clone(HONEST / "2", tmp_path / "term2")
    traj = json.loads((run / "trajectory.json").read_text())
    traj["terminated"] = False
    (run / "trajectory.json").write_text(json.dumps(traj))
    payload, code = run_verifier(2, run)
    assert payload["pass"] is False
    assert code == 1
    assert "terminated" in payload["reason"]


def test_empty_answer_fails(tmp_path):
    run = clone(HONEST / "3", tmp_path / "empty3")
    traj = json.loads((run / "trajectory.json").read_text())
    traj["final_answer"] = "   "
    (run / "trajectory.json").write_text(json.dumps(traj))
    payload, code = run_verifier(3, run)
    assert payload["pass"] is False
    assert code == 1
    assert "final_answer" in payload["reason"]


def test_bad_png_fails(tmp_path):
    run = clone(HONEST / "6", tmp_path / "png6")
    shot = run / "screenshots" / "step_002.png"
    shot.write_bytes(b"\x89PN\r\nX")  # not a decodable PNG
    payload, code = run_verifier(6, run)
    assert payload["pass"] is False
    assert code == 1
    assert "screenshots" in payload["reason"]


# ------------------------------------------- H. r2 anchor regressions (old truths must FAIL)
def test_t14_money_rendered_snapshot_fails(tmp_path):
    """The D5 defect's rendering ("$53,866 total cars") must FAIL — the
    honest fixture answer with the money form swapped back in."""
    run = clone(HONEST / "14", tmp_path / "money14")
    traj = json.loads((run / "trajectory.json").read_text())
    traj["final_answer"] = traj["final_answer"].replace(
        "the snapshot holds 53,866 total cars",
        "the snapshot holds $53,866 total cars")
    (run / "trajectory.json").write_text(json.dumps(traj))
    payload, code = run_verifier(14, run)
    assert payload["pass"] is False
    assert code == 1
    assert "snapshot_money_render" in payload["reason"]


def test_t19_old_financed_figure_fails(tmp_path):
    """The pre-fix financed figure ($28,043) must FAIL; only the page's
    $28,103 passes."""
    run = clone(HONEST / "19", tmp_path / "old19")
    traj = json.loads((run / "trajectory.json").read_text())
    traj["final_answer"] = traj["final_answer"].replace("28,103", "28,043")
    (run / "trajectory.json").write_text(json.dumps(traj))
    payload, code = run_verifier(19, run)
    assert payload["pass"] is False
    assert code == 1


def test_t8_wrong_car_estimator_fails(tmp_path):
    """The ambiguous-return trap: estimator values measured on the
    cheapest 2022 Telluride (4751227: $435/$374) instead of the task's
    referent (the first 2022 Telluride, 4255570: $487/$418) must FAIL."""
    run = clone(HONEST / "8", tmp_path / "trap8")
    traj = json.loads((run / "trajectory.json").read_text())
    traj["final_answer"] = traj["final_answer"].replace(
        "the monthly payment is $487; changing the "
        "term to 72 months: $418 per month.",
        "the monthly payment is $435; changing the "
        "term to 72 months: $374 per month.")
    (run / "trajectory.json").write_text(json.dumps(traj))
    payload, code = run_verifier(8, run)
    assert payload["pass"] is False
    assert code == 1
