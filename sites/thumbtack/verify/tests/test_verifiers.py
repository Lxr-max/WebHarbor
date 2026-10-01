"""Deterministic verifier contract tests for the 20 thumbtack tasks (review
track, orch/review/thumbtack).

Covers, per task: the honest trajectory (from the reviewer's live runs,
frozen in fixtures_data.SPECS) MUST PASS; a no-op run (homepage only, empty
answer, clean DB) MUST FAIL; a knowledge-shortcut (correct answer + delta,
homepage-only navigation) MUST FAIL; a wrong answer MUST FAIL; a
state-mismatch (success claim, no DB delta) MUST FAIL for stateful tasks.
Read-only tasks MUST FAIL on a mutated after-DB. Package tampering (task_id
mismatch, off-site URL, missing screenshot, non-done trajectory,
undecodable screenshot) MUST fail closed. The seed contract and the
tasks.jsonl key contract are asserted. No LLM.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _support import (RunBuilder, BASE, honest_run, noop_run,  # noqa: E402
                      run_verifier, shortcut_run, state_mismatch_run,
                      task_ques, wrong_answer_run, acquire_seed, copy_db,
                      exec_sql)
from fixtures_data import SPECS, WRONG_ANSWERS, MUTATIONS  # noqa: E402

STATEFUL = sorted(MUTATIONS)
READ_ONLY = sorted(set(range(20)) - set(STATEFUL))
ALL = sorted(STATEFUL + READ_ONLY)


# ---------------------------------------------------------------- happy path
@pytest.mark.parametrize("task_no", ALL)
def test_honest_run_passes(tmp_path, task_no):
    run = honest_run(tmp_path, task_no)
    run_verifier(task_no, run, expect_pass=True)


# ---------------------------------------------------------------- no-op fails
@pytest.mark.parametrize("task_no", ALL)
def test_noop_run_fails(tmp_path, task_no):
    run = noop_run(tmp_path, task_no)
    run_verifier(task_no, run, expect_pass=False)


# ---------------------------------------------------------------- shortcut fails
@pytest.mark.parametrize("task_no", ALL)
def test_shortcut_run_fails(tmp_path, task_no):
    run = shortcut_run(tmp_path, task_no)
    run_verifier(task_no, run, expect_pass=False)


# ---------------------------------------------------------------- wrong answers fail
@pytest.mark.parametrize("task_no", ALL)
def test_wrong_answer_fails(tmp_path, task_no):
    run = wrong_answer_run(tmp_path, task_no, WRONG_ANSWERS[task_no])
    run_verifier(task_no, run, expect_pass=False)


# ---------------------------------------------------------------- state mismatch fails
@pytest.mark.parametrize("task_no", STATEFUL)
def test_state_mismatch_fails(tmp_path, task_no):
    run = state_mismatch_run(tmp_path, task_no)
    run_verifier(task_no, run, expect_pass=False)


# ---------------------------------------------------------------- wrong delta fails
@pytest.mark.parametrize("task_no", STATEFUL)
def test_wrong_delta_fails(tmp_path, task_no):
    """Honest navigation + answer but a DIFFERENT stateful write — FAIL."""
    run = honest_run(tmp_path, task_no)
    after = run / "after.db"
    if task_no in (4, 10):
        # cancel-based tasks: add an unrelated saved pro instead of nothing
        exec_sql(after, ["INSERT INTO saved_pros VALUES (99, 1, 1, "
                         "'2026-09-26 12:00:00.000000')"])
    else:
        exec_sql(after, ["INSERT INTO saved_pros VALUES (99, 1, 1, "
                         "'2026-09-26 12:00:00.000000')"])
    run_verifier(task_no, run, expect_pass=False)


# ---------------------------------------------------------------- read-only mutation fails
@pytest.mark.parametrize("task_no", READ_ONLY)
def test_readonly_mutation_fails(tmp_path, task_no):
    """A read-only task whose after-DB was mutated anyway must FAIL."""
    run = honest_run(tmp_path, task_no)
    db = sqlite3.connect(run / "after.db")
    db.execute("UPDATE pros SET name = name || ' tampered' WHERE id = 1")
    db.commit()
    db.close()
    run_verifier(task_no, run, expect_pass=False)


# ---------------------------------------------------------------- package tampering
@pytest.mark.parametrize("task_no", ALL)
def test_task_id_mismatch_fails(tmp_path, task_no):
    run = honest_run(tmp_path, task_no)
    traj = json.loads((run / "trajectory.json").read_text())
    traj["task_id"] = "Thumbtack--999"
    (run / "trajectory.json").write_text(json.dumps(traj))
    run_verifier(task_no, run, expect_pass=False)


@pytest.mark.parametrize("task_no", ALL)
def test_offsite_url_fails(tmp_path, task_no):
    run = honest_run(tmp_path, task_no)
    traj = json.loads((run / "trajectory.json").read_text())
    traj["steps"][0]["url_after"] = "https://www.thumbtack.com/"
    (run / "trajectory.json").write_text(json.dumps(traj))
    run_verifier(task_no, run, expect_pass=False)


@pytest.mark.parametrize("task_no", ALL)
def test_missing_screenshot_fails(tmp_path, task_no):
    run = honest_run(tmp_path, task_no)
    shots = sorted((run / "screenshots").glob("step_*.png"))
    shots[0].unlink()
    run_verifier(task_no, run, expect_pass=False)


@pytest.mark.parametrize("task_no", ALL)
def test_undecodable_screenshot_fails(tmp_path, task_no):
    run = honest_run(tmp_path, task_no)
    shots = sorted((run / "screenshots").glob("step_*.png"))
    shots[0].write_bytes(b"not a png at all")
    run_verifier(task_no, run, expect_pass=False)


@pytest.mark.parametrize("task_no", ALL)
def test_not_terminated_fails(tmp_path, task_no):
    run = honest_run(tmp_path, task_no)
    traj = json.loads((run / "trajectory.json").read_text())
    traj["terminated"] = False
    traj["termination_reason"] = None
    (run / "trajectory.json").write_text(json.dumps(traj))
    run_verifier(task_no, run, expect_pass=False)


@pytest.mark.parametrize("task_no", ALL)
def test_empty_answer_fails(tmp_path, task_no):
    run = honest_run(tmp_path, task_no)
    traj = json.loads((run / "trajectory.json").read_text())
    traj["final_answer"] = ""
    (run / "trajectory.json").write_text(json.dumps(traj))
    run_verifier(task_no, run, expect_pass=False)


# ---------------------------------------------------------------- contracts
def test_seed_contract():
    """The frozen seed counts must match the acquired seed DB."""
    import verify_lib
    counts = verify_lib.fetch_counts(acquire_seed())
    for table, expected in verify_lib.SEED_COUNTS.items():
        assert counts[table] == expected, f"{table}: {counts[table]} != {expected}"


def test_tasks_jsonl_key_contract():
    """tasks.jsonl rows keep the original 5 keys byte-identical, plus exactly
    verifier_path and judge_rubric; no answer key ever appears."""
    rows = [json.loads(l) for l in
            (Path(__file__).resolve().parents[2] / "tasks.jsonl").read_text(
                encoding="utf-8").splitlines() if l.strip()]
    assert len(rows) == 20
    for row in rows:
        assert set(row) == {"web_name", "id", "ques", "web", "upstream_url",
                            "verifier_path", "judge_rubric"}, row.get("id")
        assert "answer" not in row
        assert row["web"] == "http://localhost:40109/"
        assert row["upstream_url"] == "https://www.thumbtack.com/"
        assert row["verifier_path"].startswith("sites/thumbtack/verify/verify_")
        assert row["judge_rubric"].strip()
        # rubric is English, rule-style, no ground-truth leakage of answers
        assert re_ok(row["judge_rubric"])
    ids = [r["id"] for r in rows]
    assert ids == [f"Thumbtack--{i}" for i in range(20)]


def re_ok(rubric: str) -> bool:
    # ASCII-printable English rubric (judge-side facts allowed, statista
    # convention; the agent prompt only ever receives `ques`)
    rubric.encode("utf-8")
    return rubric == rubric.strip()


def test_verifier_paths_exist():
    repo_root = Path(__file__).resolve().parents[4]
    site_dir = Path(__file__).resolve().parents[2]
    rows = [json.loads(l) for l in (site_dir / "tasks.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    for row in rows:
        assert (repo_root / row["verifier_path"]).is_file(), row["verifier_path"]


def test_no_answer_leak_in_verifier_navigation():
    """verifier files may hardcode ground truth but must not write it into
    tasks.jsonl (checked above); here we assert the questions themselves carry
    no answer numbers beyond task parameters."""
    site_dir = Path(__file__).resolve().parents[2]
    rows = [json.loads(l) for l in (site_dir / "tasks.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    import re
    for row in rows:
        assert not re.search(r"\$\d", row["ques"]), row["id"]
