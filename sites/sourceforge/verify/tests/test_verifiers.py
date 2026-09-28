"""Deterministic verifier contract tests for the 21 sourceforge tasks.

Covers, per task: the honest trajectory (from the reviewer's live runs, frozen
in fixtures_data.SPECS) MUST PASS; a no-op run (homepage only, empty answer,
clean DB) MUST FAIL; a knowledge-shortcut (correct answer + delta, homepage-only
navigation) MUST FAIL; a wrong answer MUST FAIL; a state-mismatch (success
claim, no DB delta) MUST FAIL for stateful tasks. Read-only tasks MUST FAIL on
a mutated after-DB. Package tampering (task_id mismatch, off-site URL, missing
screenshot, non-done trajectory, undecodable screenshot) MUST fail closed.

No LLM: snapshots are seed copies mutated through sqlite, trajectories are
written in the agent_demo/agent.py shape.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from _support import (BASE, RunBuilder, copy_db, exec_sql, honest_run,  # noqa: E402
                       noop_run, run_verifier, shortcut_run, state_mismatch_run,
                       task_ques, wrong_answer_run, acquire_seed)
from fixtures_data import SPECS, WRONG_ANSWERS  # noqa: E402

STATEFUL = {7, 13, 18}
READ_ONLY = set(range(21)) - STATEFUL
ALL = sorted(STATEFUL | READ_ONLY)


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
@pytest.mark.parametrize("task_no", sorted(STATEFUL))
def test_state_mismatch_fails(tmp_path, task_no):
    run = state_mismatch_run(tmp_path, task_no)
    run_verifier(task_no, run, expect_pass=False)


# ---------------------------------------------------------------- read-only mutation fails
@pytest.mark.parametrize("task_no", sorted(READ_ONLY))
def test_readonly_mutation_fails(tmp_path, task_no):
    """A read-only task whose after-DB was mutated anyway must FAIL."""
    run = honest_run(tmp_path, task_no)
    db = sqlite3.connect(run / "after.db")
    db.execute("UPDATE projects SET name = name || ' tampered' WHERE id = 1")
    db.commit()
    db.close()
    run_verifier(task_no, run, expect_pass=False)


# ---------------------------------------------------------------- package tampering
@pytest.mark.parametrize("task_no", ALL)
def test_task_id_mismatch_fails(tmp_path, task_no):
    run = honest_run(tmp_path, task_no)
    traj = json.loads((run / "trajectory.json").read_text())
    traj["task_id"] = "SourceForge--999"
    (run / "trajectory.json").write_text(json.dumps(traj))
    run_verifier(task_no, run, expect_pass=False)


@pytest.mark.parametrize("task_no", ALL)
def test_offsite_url_fails(tmp_path, task_no):
    run = honest_run(tmp_path, task_no)
    traj = json.loads((run / "trajectory.json").read_text())
    traj["steps"][0]["url_after"] = "https://example.org/"
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


# ---------------------------------------------------------------- subject binding
# Swapping two subjects' numbers keeps every integer in the answer. A loose
# substring / anywhere-match would still PASS. Subject binding must FAIL.
_SWAPS = {
    0: [("3,600,000", "768,800"), ("4.6", "4.9")],
    1: [("29,589", "21,750"), ("6,001", "90,456")],
    2: [("765", "567"), ("4.8", "4.9")],
    3: [("priority 5", "priority 7")],
    4: [("3,206", "9,620"), ("4 posts", "18 posts")],
    5: [("3,000,000", "3,600,000"), ("4.1", "4.6")],
    6: [("3,120", "1,150")],
    8: [("40,718", "90,456")],
    9: [("14,848", "9,044"), ("4.7", "4.5")],
    10: [("422,400", "205,800"), ("765", "27")],
    11: [("weekly 37", "weekly 9,572")],
    12: [("lists 3 reviews", "lists 6 reviews")],
    16: [("5,494", "1,210")],
    17: [("205,800", "23,587"), ("4.9", "4.8")],
    19: [("6,035", "61,049")],
    20: [("4,100", "940"), ("4.3", "4.2")],
}


def _swap_pairs(text, pairs):
    out = text
    for left, right in pairs:
        token = "\ue000SWAP\ue001"
        if left not in out or right not in out:
            raise AssertionError(f"swap anchors missing: {left!r} / {right!r}")
        out = out.replace(left, token, 1).replace(right, left, 1).replace(token, right, 1)
    return out


@pytest.mark.parametrize("task_no", sorted(_SWAPS))
def test_swapped_subject_fails(tmp_path, task_no):
    run = honest_run(tmp_path, task_no)
    traj = json.loads((run / "trajectory.json").read_text())
    traj["final_answer"] = _swap_pairs(traj["final_answer"], _SWAPS[task_no])
    (run / "trajectory.json").write_text(json.dumps(traj))
    run_verifier(task_no, run, expect_pass=False)


def test_password_safe_count_not_credited_to_another_project(tmp_path):
    """Task 7 has a single weekly count. Moving it onto KeePass must fail."""
    run = honest_run(tmp_path, 7)
    traj = json.loads((run / "trajectory.json").read_text())
    traj["final_answer"] = traj["final_answer"].replace(
        "Password Safe download | SourceForge.net with 1,788 weekly",
        "Password Safe download | SourceForge.net with 999 weekly",
    ) + " KeePass has 1,788 weekly downloads."
    (run / "trajectory.json").write_text(json.dumps(traj))
    run_verifier(7, run, expect_pass=False)


def test_alltime_rank_is_not_a_substring_of_another_count(tmp_path):
    """'#10' must not be satisfied by the digits inside 109,095."""
    run = honest_run(tmp_path, 5)
    traj = json.loads((run / "trajectory.json").read_text())
    assert "109,095" in traj["final_answer"]
    traj["final_answer"] = traj["final_answer"].replace("#10", "#4")
    (run / "trajectory.json").write_text(json.dumps(traj))
    run_verifier(5, run, expect_pass=False)


def test_help_topic_count_not_satisfied_by_a_date(tmp_path):
    """Standalone 25 inside 2010-11-25 is not the Help forum topic count."""
    run = honest_run(tmp_path, 14)
    traj = json.loads((run / "trajectory.json").read_text())
    assert "2010-11-25" in traj["final_answer"]
    traj["final_answer"] = traj["final_answer"].replace("25 topics", "40 topics")
    (run / "trajectory.json").write_text(json.dumps(traj))
    run_verifier(14, run, expect_pass=False)


def test_one_priority_does_not_cover_two_tickets(tmp_path):
    """A single 'priority 7' cannot satisfy both CVE tickets."""
    run = honest_run(tmp_path, 15)
    traj = json.loads((run / "trajectory.json").read_text())
    traj["final_answer"] = traj["final_answer"].replace(
        "#2670 CVE-2026-48102 (open, priority 7)",
        "#2670 CVE-2026-48102 (open, priority 4)",
    )
    (run / "trajectory.json").write_text(json.dumps(traj))
    run_verifier(15, run, expect_pass=False)


# ---------------------------------------------------------------- seed contract
def test_seed_digests_match_frozen_contract():
    db_path = acquire_seed()
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    sys.path.insert(0, str(Path(__file__).parents[1]))
    import verify_lib
    assert verify_lib.schema_digest(db) == verify_lib.SCHEMA_SHA256
    assert verify_lib.rows_digest(db) == verify_lib.SEED_ROWS_SHA256
    counts = verify_lib.table_counts(db)
    assert counts == verify_lib.SEED_COUNTS


def test_tasks_jsonl_has_no_answer_key():
    for line in (Path(__file__).parents[2] / "tasks.jsonl").read_text().splitlines():
        row = json.loads(line)
        assert "answer" not in row
        assert "verifier_path" in row and "judge_rubric" in row
        assert set(row) == {"id", "ques", "upstream_url", "web", "web_name",
                            "verifier_path", "judge_rubric"}


# Distinctive ground-truth tokens from the frozen answers. None of these
# appear in the task questions, so a rubric that contains one is an answer leak.
_RUBRIC_LEAK_TOKENS = (
    "3,600,000", "768,800", "29,589", "21,750", "90,456", "6,001",
    "itreet-raking5", "Harry Stein", "Carlos Nunes", "kb0000001",
    "Igor Pavlov", "Logan Abbott", "Roger Sheppard", "1320 Columbia",
    "MinGW", "AutoClicker", "WinSCP", "Password Safe", "DOSBox",
    "Neko Void", "PortableApps", "Dolibarr", "Pipedrive", "SuiteCRM",
    "EspoCRM", "Odoo", "PSeInt", "TrueType", "Notepad++", "p7zip",
    "7-max", "7-Far", "ipavlov", "CVE-2026", "Ventoy", "Next Player",
    "Video.js", "Shotcut", "FastField", "2000-02-09", "2026-09-04",
    "2026-09-19", "#2701", "#2681", "#2670", "#2669", "GPLv3", "LGPLv2",
)


def test_judge_rubrics_do_not_leak_ground_truth():
    tasks = Path(__file__).parents[2] / "tasks.jsonl"
    for line in tasks.read_text().splitlines():
        row = json.loads(line)
        rubric = row["judge_rubric"]
        ques = row["ques"]
        for token in _RUBRIC_LEAK_TOKENS:
            if token in ques:
                continue
            assert token not in rubric, f"{row['id']} rubric leaks {token!r}"
        assert "answer" not in rubric.lower() or "empty answer" in rubric.lower()
