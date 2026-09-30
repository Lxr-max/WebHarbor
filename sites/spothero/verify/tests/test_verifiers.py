"""Contract tests for the spothero deterministic verifiers (review track).

21 honest fixtures (from the reviewer's live walks on wh-spothero-review)
must PASS; the adversarial controls must all FAIL: no-op runs, wrong answers,
homepage-only shortcuts, missing state deltas, wrong deltas, read-only
catalog tampering and package tampering (task_id mismatch, off-site URLs,
missing/undecodable screenshots, non-done trajectories). The frozen seed
contract and the tasks.jsonl key/prefix contracts are asserted too.

Run from the repository root:
    python3 -m pytest sites/spothero/verify/tests -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _support as sup  # noqa: E402
from fixtures_data import SPECS, WRONG_ANSWERS, MUTATIONS  # noqa: E402

TASK_NOS = sorted(SPECS)
STATEFUL = sorted(MUTATIONS)          # every task writes something here
BOOKING = [n for n in TASK_NOS if n not in (4, 13, 14, 15)]


# ------------------------------------------------------------------ honest
@pytest.mark.parametrize("task_no", TASK_NOS)
def test_honest_walkthrough_passes(tmp_path, task_no):
    run = sup.honest_run(tmp_path, task_no)
    result = sup.run_verifier(task_no, run, expect_pass=True)
    assert result["pass"] is True


# ------------------------------------------------------------------ no-op
@pytest.mark.parametrize("task_no", TASK_NOS)
def test_noop_fails(tmp_path, task_no):
    run = sup.noop_run(tmp_path, task_no)
    sup.run_verifier(task_no, run, expect_pass=False)


# ------------------------------------------------------------------ shortcut
@pytest.mark.parametrize("task_no", TASK_NOS)
def test_homepage_shortcut_fails(tmp_path, task_no):
    run = sup.shortcut_run(tmp_path, task_no)
    sup.run_verifier(task_no, run, expect_pass=False)


# ------------------------------------------------------------------ wrong answer
@pytest.mark.parametrize("task_no", TASK_NOS)
def test_wrong_answer_fails(tmp_path, task_no):
    run = sup.wrong_answer_run(tmp_path, task_no)
    sup.run_verifier(task_no, run, expect_pass=False)


# ------------------------------------------------------------------ state mismatch
@pytest.mark.parametrize("task_no", STATEFUL)
def test_missing_state_delta_fails(tmp_path, task_no):
    run = sup.state_mismatch_run(tmp_path, task_no)
    sup.run_verifier(task_no, run, expect_pass=False)


# ------------------------------------------------------------------ wrong delta
@pytest.mark.parametrize("task_no", STATEFUL)
def test_wrong_delta_fails(tmp_path, task_no):
    run = sup.wrong_delta_run(tmp_path, task_no)
    sup.run_verifier(task_no, run, expect_pass=False)


# ------------------------------------------------------------------ catalog tamper
@pytest.mark.parametrize("task_no", [0, 7, 13, 17])
def test_readonly_catalog_tamper_fails(tmp_path, task_no):
    run = sup.readonly_tamper_run(tmp_path, task_no)
    sup.run_verifier(task_no, run, expect_pass=False)


# ------------------------------------------------------------------ package tamper
def _pkg_run(tmp_path, task_no, mutate):
    root = tmp_path / f"pkg_{task_no}"
    root.mkdir(parents=True)
    tid = f"SpotHero--{task_no}"
    spec = SPECS[task_no]
    b = sup.RunBuilder(root, tid)
    for u in spec["urls"]:
        b.add_step("navigate", u)
    traj = b.finish(spec["answer"])
    after = sup.copy_db(root, "after.db")
    if task_no in MUTATIONS:
        sup.exec_sql(after, MUTATIONS[task_no])
    sup.copy_db(root, "initial.db")
    mutate(traj, root)
    (root / "trajectory.json").write_text(json.dumps(traj, indent=1))
    return root


def test_task_id_mismatch_fails(tmp_path):
    def mutate(traj, root):
        traj["task_id"] = "SpotHero--20"
    run = _pkg_run(tmp_path, 0, mutate)
    sup.run_verifier(0, run, expect_pass=False)


def test_offsite_url_fails(tmp_path):
    def mutate(traj, root):
        traj["steps"][2]["url_after"] = "https://example.com/search"
    run = _pkg_run(tmp_path, 1, mutate)
    sup.run_verifier(1, run, expect_pass=False)


def test_missing_screenshot_fails(tmp_path):
    def mutate(traj, root):
        (root / "screenshots" / "step_003.png").unlink()
    run = _pkg_run(tmp_path, 2, mutate)
    sup.run_verifier(2, run, expect_pass=False)


def test_undecodable_screenshot_fails(tmp_path):
    def mutate(traj, root):
        (root / "screenshots" / "step_003.png").write_bytes(b"not a png")
    run = _pkg_run(tmp_path, 3, mutate)
    sup.run_verifier(3, run, expect_pass=False)


def test_not_terminated_fails(tmp_path):
    def mutate(traj, root):
        traj["terminated"] = False
        traj["termination_reason"] = None
    run = _pkg_run(tmp_path, 5, mutate)
    sup.run_verifier(5, run, expect_pass=False)


def test_empty_answer_fails(tmp_path):
    def mutate(traj, root):
        traj["final_answer"] = "no"
    run = _pkg_run(tmp_path, 6, mutate)
    sup.run_verifier(6, run, expect_pass=False)


# ------------------------------------------------------------------ seed contract
def test_seed_digests():
    sys.path.insert(0, str(sup.VERIFY_DIR))
    import verify_lib as vl
    db = vl.load_db(sup.acquire_seed())
    assert vl.schema_digest(db) == vl.SCHEMA_SHA256
    assert vl.rows_digest(db) == vl.SEED_ROWS_SHA256
    assert vl.table_counts(db) == vl.SEED_COUNTS


def test_seed_md5():
    import hashlib
    md5 = hashlib.md5(sup.acquire_seed().read_bytes()).hexdigest()
    sys.path.insert(0, str(sup.VERIFY_DIR))
    import verify_lib as vl
    assert md5 == vl.SEED_MD5


# ------------------------------------------------------------------ tasks.jsonl contract
def test_tasks_jsonl_contract():
    lines = sup.TASKS_FILE.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 21
    for i, line in enumerate(lines):
        row = json.loads(line)
        assert row["id"] == f"SpotHero--{i}"
        assert sorted(row.keys()) == sorted(
            ["web_name", "id", "ques", "web", "upstream_url",
             "verifier_path", "judge_rubric"]), row.keys()
        assert "answer" not in row
        assert row["verifier_path"] == f"sites/spothero/verify/verify_{i}.py"
        assert (sup.SITE_DIR.parent.parent / row["verifier_path"]).is_file()
        assert len(row["judge_rubric"]) > 80
        assert row["web"] == "http://localhost:40106/"
        assert row["upstream_url"] == "https://spothero.com/"


def test_tasks_jsonl_five_key_prefix():
    """The original 5-key serialization stays a literal prefix of each row."""
    lines = sup.TASKS_FILE.read_text(encoding="utf-8").splitlines()
    for line in lines:
        row = json.loads(line)
        five = {k: row[k] for k in ("web_name", "id", "ques", "web",
                                    "upstream_url")}
        prefix = json.dumps(five)
        assert line.startswith(prefix[:-1]), line[:120]


# ------------------------------------------------------------------ verifier wiring
def test_verifiers_exist_and_declare_task_ids():
    for n in TASK_NOS:
        path = sup.VERIFY_DIR / f"verify_{n}.py"
        assert path.is_file()
        text = path.read_text()
        assert f'TASK_ID = "SpotHero--{n}"' in text
        assert "check_package" in text
        assert "check_seed_contract" in text
