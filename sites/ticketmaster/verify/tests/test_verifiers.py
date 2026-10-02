"""Deterministic verifier contract tests for the 20 ticketmaster tasks
(review track, orch/review/ticketmaster).

Covers, per task: the honest trajectory (from the reviewer's live runs,
frozen in fixtures_data.SPECS) MUST PASS; a no-op run (homepage only, empty
answer, clean DB) MUST FAIL; a knowledge-shortcut (correct answer + delta,
homepage-only navigation) MUST FAIL; a wrong answer MUST FAIL; a
state-mismatch (success claim, no DB delta) MUST FAIL for stateful tasks.
Read-only tasks MUST FAIL on a mutated after-DB. Package tampering (task_id
mismatch, off-site URL, missing screenshot, non-done trajectory,
undecodable screenshot, empty answer) MUST fail closed. The seed contract
and the tasks.jsonl key contract are asserted. No LLM.
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
                      task_ques, wrong_answer_run, read_only_mutation_run,
                      acquire_seed, copy_db, exec_sql, PNG)
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


# ------------------------------------------------------- state mismatch fails (stateful)
@pytest.mark.parametrize("task_no", STATEFUL)
def test_state_mismatch_fails(tmp_path, task_no):
    run = state_mismatch_run(tmp_path, task_no)
    run_verifier(task_no, run, expect_pass=False)


# ------------------------------------------------------- mutated DB fails (read-only)
@pytest.mark.parametrize("task_no", READ_ONLY)
def test_read_only_mutation_fails(tmp_path, task_no):
    run = read_only_mutation_run(tmp_path, task_no)
    run_verifier(task_no, run, expect_pass=False)


# ---------------------------------------------------------------- tamper cases
@pytest.mark.parametrize("task_no", [0, 7, 13])
def test_task_id_mismatch_fails(tmp_path, task_no):
    root = tmp_path / f"tid_{task_no}"
    root.mkdir(parents=True)
    spec = SPECS[task_no]
    b = RunBuilder(root, f"Ticketmaster--{task_no}")
    for u in spec["urls"]:
        b.add_step("navigate", u)
    b.finish(spec["answer"])
    # tamper: wrong task_id in the package
    traj = json.loads((root / "trajectory.json").read_text())
    traj["task_id"] = "Ticketmaster--19"
    (root / "trajectory.json").write_text(json.dumps(traj))
    copy_db(root, "after.db")
    copy_db(root, "initial.db")
    if task_no in MUTATIONS:
        exec_sql(root / "after.db", MUTATIONS[task_no])
    run_verifier(task_no, root, expect_pass=False)


@pytest.mark.parametrize("task_no", [1, 9, 16])
def test_offsite_url_fails(tmp_path, task_no):
    root = tmp_path / f"offsite_{task_no}"
    root.mkdir(parents=True)
    spec = SPECS[task_no]
    b = RunBuilder(root, f"Ticketmaster--{task_no}")
    for u in spec["urls"]:
        b.add_step("navigate", u)
    b.add_step("navigate", "https://www.ticketmaster.com/event/123")
    b.finish(spec["answer"])
    copy_db(root, "after.db")
    copy_db(root, "initial.db")
    if task_no in MUTATIONS:
        exec_sql(root / "after.db", MUTATIONS[task_no])
    run_verifier(task_no, root, expect_pass=False)


@pytest.mark.parametrize("task_no", [3, 11, 18])
def test_missing_screenshot_fails(tmp_path, task_no):
    root = tmp_path / f"noshot_{task_no}"
    root.mkdir(parents=True)
    spec = SPECS[task_no]
    b = RunBuilder(root, f"Ticketmaster--{task_no}")
    for u in spec["urls"]:
        b.add_step("navigate", u)
    b.finish(spec["answer"])
    (root / "screenshots" / "step_002.png").unlink()
    copy_db(root, "after.db")
    copy_db(root, "initial.db")
    if task_no in MUTATIONS:
        exec_sql(root / "after.db", MUTATIONS[task_no])
    run_verifier(task_no, root, expect_pass=False)


@pytest.mark.parametrize("task_no", [2, 17])
def test_corrupt_screenshot_fails(tmp_path, task_no):
    root = tmp_path / f"badshot_{task_no}"
    root.mkdir(parents=True)
    spec = SPECS[task_no]
    b = RunBuilder(root, f"Ticketmaster--{task_no}")
    for u in spec["urls"]:
        b.add_step("navigate", u)
    b.finish(spec["answer"])
    (root / "screenshots" / "step_001.png").write_bytes(b"not a png")
    copy_db(root, "after.db")
    copy_db(root, "initial.db")
    if task_no in MUTATIONS:
        exec_sql(root / "after.db", MUTATIONS[task_no])
    run_verifier(task_no, root, expect_pass=False)


@pytest.mark.parametrize("task_no", [4, 10])
def test_not_terminated_fails(tmp_path, task_no):
    root = tmp_path / f"notterm_{task_no}"
    root.mkdir(parents=True)
    spec = SPECS[task_no]
    b = RunBuilder(root, f"Ticketmaster--{task_no}")
    for u in spec["urls"]:
        b.add_step("navigate", u)
    b.finish(spec["answer"], terminated=False, reason="max_steps")
    copy_db(root, "after.db")
    copy_db(root, "initial.db")
    if task_no in MUTATIONS:
        exec_sql(root / "after.db", MUTATIONS[task_no])
    run_verifier(task_no, root, expect_pass=False)


@pytest.mark.parametrize("task_no", [5, 14])
def test_empty_answer_fails(tmp_path, task_no):
    root = tmp_path / f"empty_{task_no}"
    root.mkdir(parents=True)
    spec = SPECS[task_no]
    b = RunBuilder(root, f"Ticketmaster--{task_no}")
    for u in spec["urls"]:
        b.add_step("navigate", u)
    b.finish("")
    copy_db(root, "after.db")
    copy_db(root, "initial.db")
    run_verifier(task_no, root, expect_pass=False)


# ---------------------------------------------------------------- contract checks
def test_seed_is_byte_stable_on_populated_startup():
    import subprocess, hashlib, shutil, tempfile
    seed = acquire_seed()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "site"
        shutil.copytree(Path(__file__).resolve().parents[2], root, ignore=shutil.ignore_patterns("instance", "__pycache__"))
        (root / "instance").mkdir()
        runtime = root / "instance" / seed.name
        shutil.copyfile(seed, runtime)
        before = hashlib.sha256(runtime.read_bytes()).hexdigest()
        subprocess.run([sys.executable, "-c", "import app"], cwd=root, check=True)
        assert hashlib.sha256(runtime.read_bytes()).hexdigest() == before


def test_tasks_jsonl_key_contract():
    lines = (Path(__file__).resolve().parents[2]
             / "tasks.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 20
    for line in lines:
        row = json.loads(line)
        assert sorted(row.keys()) == ["id", "judge_rubric", "ques", "upstream_url",
                                      "verifier_path", "web", "web_name"], row.keys()
        assert "answer" not in row
        assert row["web"] == "http://localhost:40110/"
        assert row["upstream_url"] == "https://www.ticketmaster.com/"
        assert row["verifier_path"].startswith("sites/ticketmaster/verify/verify_")
        assert (Path(__file__).resolve().parents[4]
                / row["verifier_path"]).is_file()
        assert row["judge_rubric"].strip()
        # no answer leakage in the task statement: the frozen numeric ground
        # truth must not appear in ques (task-given constraints like a $50
        # budget, the demo password, or a card last4 given by the task are fine)
        for banned in ("333.18", "573.80", "286.90", "161.00", "46.82",
                       "32.98", "187.83", "162.36", "313.72", "358.70",
                       "179.35", "98.02", "205.96", "152.74", "189.90",
                       "138.00", "51.90", "63.30", "17.30", "97.01",
                       "60.19", "101.82", "47.83", "81.18", "41.97",
                       "161.52", "269.70", "265.56", "132.78", "725.00",
                       "1-800-745-3000"):
            assert banned not in row["ques"], (row["id"], banned)


def test_rubrics_are_rules_not_answers():
    lines = (Path(__file__).resolve().parents[2]
             / "tasks.jsonl").read_text(encoding="utf-8").splitlines()
    for line in lines:
        row = json.loads(line)
        rubric = row["judge_rubric"].lower()
        # rubric must not carry the frozen numeric ground truth
        for banned in ("333.18", "573.80", "286.90", "161.00", "46.82",
                       "32.98", "187.83", "162.36", "313.72", "358.70",
                       "179.35", "98.02", "205.96", "152.74", "189.90",
                       "138.00", "51.90", "63.30", "17.30", "97.01",
                       "60.19", "101.82", "47.83", "81.18", "41.97",
                       "161.52", "269.70", "265.56", "132.78", "725.00",
                       "1-800-745-3000"):
            assert banned not in rubric, (row["id"], banned)


def test_contributor_suite_still_green_hint():
    """The 5 contributor keys are byte-identical to 73b29ac8 (checked by
    append_rubrics.py at merge time); here we assert the 5-key prefix of every
    line parses and carries the original fields."""
    lines = (Path(__file__).resolve().parents[2]
             / "tasks.jsonl").read_text(encoding="utf-8").splitlines()
    for line in lines:
        row = json.loads(line)
        for key in ("web_name", "id", "ques", "web", "upstream_url"):
            assert row.get(key), (row["id"], key)
