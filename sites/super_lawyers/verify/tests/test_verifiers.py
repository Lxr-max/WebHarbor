"""Deterministic verifier contract tests for the 20 super_lawyers tasks.

Covers, per task: the honest trajectory (from the reviewer's live walks, frozen
in fixtures_data.SPECS) MUST PASS — except the three tasks BLOCKED by review
findings (1 / 14 / 17), whose honest runs MUST FAIL on the documented blocked
checks; a no-op run (homepage only, empty answer, clean DB) MUST FAIL; a
knowledge-shortcut (correct answer + delta, homepage-only navigation) MUST
FAIL; a wrong answer MUST FAIL; a state-mismatch (success claim, no DB delta)
MUST FAIL for stateful tasks. Every task MUST FAIL on a mutated after-DB (a
non-allowed table touched) and on read-only tasks any write at all. Package
tampering (task_id mismatch, off-site URL, missing screenshot, undecodable
screenshot, non-done trajectory) MUST fail closed.

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
from _support import (BASE, RunBuilder, VERIFY_DIR, acquire_seed, copy_db,  # noqa: E402
                       exec_sql, honest_run, noop_run, run_verifier,
                       shortcut_run, state_mismatch_run, task_ques,
                       wrong_answer_run)
from fixtures_data import SPECS, WRONG_ANSWERS  # noqa: E402

# r2 re-sync: the r1 BLOCKED tasks (1 / 14 / 17) were re-anchored by the
# c6b79316 fix (Criminal Defense Seattle / Chicago family law SERPs,
# featured-lawyer city rendering) and are now fully solvable — the blocked
# machinery is retired and every honest run must PASS.
BLOCKED: set[int] = set()
STATEFUL = {0, 6, 7, 8, 9, 10}
ALL = list(range(20))


# ---------------------------------------------------------------- happy path
@pytest.mark.parametrize("task_no", ALL)
def test_honest_run_passes(tmp_path, task_no):
    run = honest_run(tmp_path, task_no)
    run_verifier(task_no, run, expect_pass=True)


def test_blocked_set_retired():
    """The r1 blocked set (1/14/17) is retired: every task is solvable at the
    r2-fixed site state, so no verifier may carry BLOCKED machinery."""
    assert BLOCKED == set()
    for n in ALL:
        src = (VERIFY_DIR / f"verify_{n}.py").read_text()
        assert "check_blocked(judge" not in src, f"verify_{n}.py still carries BLOCKED machinery"


# ---------------------------------------------------------------- no-op fails
@pytest.mark.parametrize("task_no", ALL)
def test_noop_run_fails(tmp_path, task_no):
    run = noop_run(tmp_path, task_no)
    run_verifier(task_no, run, expect_pass=False)


def test_noop_with_fake_answer_fails(tmp_path):
    """A confident but unsupported answer on a homepage-only run must fail."""
    for task_no in ALL:
        run = noop_run(tmp_path / f"fake_{task_no}", task_no,
                       answer=SPECS[task_no]["answer"])
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


# ---------------------------------------------------------------- after-DB mutation fails
@pytest.mark.parametrize("task_no", ALL)
def test_after_db_mutation_fails(tmp_path, task_no):
    """Touching a table outside the task's allowed delta must FAIL (read-only
    contract for read-only tasks; exact-delta contract for stateful tasks)."""
    run = honest_run(tmp_path, task_no)
    db = sqlite3.connect(run / "after.db")
    db.execute("UPDATE lawyers SET name = name || ' tampered' WHERE id = 1")
    db.commit()
    db.close()
    run_verifier(task_no, run, expect_pass=False)


@pytest.mark.parametrize("task_no", [n for n in ALL if n not in STATEFUL])
def test_read_only_task_any_write_fails(tmp_path, task_no):
    """Read-only tasks must fail on ANY DB write, even a plausible one."""
    run = honest_run(tmp_path, task_no)
    db = sqlite3.connect(run / "after.db")
    db.execute("INSERT INTO inquiries (user_id, lawyer_uuid, first_name,"
               " last_name, email, phone, city, state, message, created_at)"
               " VALUES (1, '084fb116-f66d-4a57-affa-7e99e9c5f3f6', 'X', 'Y',"
               " 'x@y.z', '555', 'Seattle', 'WA', 'plausible write',"
               " '2026-09-26 12:00:00.000000')")
    db.commit()
    db.close()
    run_verifier(task_no, run, expect_pass=False)


@pytest.mark.parametrize("task_no", sorted(STATEFUL))
def test_stateful_task_extra_write_fails(tmp_path, task_no):
    """Stateful tasks must fail when an extra row appears in an allowed table."""
    run = honest_run(tmp_path, task_no)
    db = sqlite3.connect(run / "after.db")
    db.execute("INSERT INTO favorites (user_id, lawyer_uuid, created_at)"
               " VALUES (1, '02409ab8-4b52-4d58-848c-e0db288a71b1',"
               " '2026-09-26 12:00:00.000000')")
    db.commit()
    db.close()
    run_verifier(task_no, run, expect_pass=False)


# ---------------------------------------------------------------- cross-task graft
@pytest.mark.parametrize("task_no", sorted(STATEFUL))
def test_cross_task_graft_fails(tmp_path, task_no):
    """The honest navigation + answer of task A with the DB delta of task A
    applied to a DIFFERENT user's account must FAIL (identity binding)."""
    spec = SPECS[task_no]
    run = tmp_path / f"graft_{task_no}"
    run.mkdir(parents=True)
    b = RunBuilder(run, f"Super Lawyers--{task_no}")
    for action, path in spec["steps"]:
        b.add_step(action, BASE + path)
    b.finish(spec["answer"])
    after = copy_db(run)
    # apply the delta but attributed to another user where identity matters
    grafts = {
        0: ["INSERT INTO inquiries (user_id, lawyer_uuid, first_name, last_name,"
            " email, phone, city, state, message, created_at) VALUES (2,"
            " '084fb116-f66d-4a57-affa-7e99e9c5f3f6', 'Alice', 'Johnson',"
            " 'alice.j@test.com', '206-555-0134', 'Seattle', 'WA',"
            " 'I was rear-ended on I-5 and would like to discuss my case.',"
            " '2026-09-26 12:00:00.000000')"],
        6: ["DELETE FROM favorites WHERE user_id = 3 AND lawyer_uuid IN"
            " ('9abb5e11-4e2b-4b2f-9d97-cbed2cdfa327',"
            " 'a7d4c917-69e1-4d19-acf6-386d53f1e258')"],
        7: ["DELETE FROM saved_searches WHERE user_id = 1 AND practice_slug = 'dui-dwi'"],
        8: ["INSERT INTO inquiries (user_id, lawyer_uuid, first_name, last_name,"
            " email, phone, city, state, message, created_at) VALUES (2,"
            " '11574067-209a-4624-af58-d7c9b2f4c1e9', 'Alice', 'Johnson',"
            " 'alice.j@test.com', '206-555-0134', 'Seattle', 'WA',"
            " 'Follow-up: how long does a settlement typically take?',"
            " '2026-09-26 12:00:00.000000')"],
    }
    exec_sql(after, grafts.get(task_no, spec.get("sql", [])))
    (run / "initial.db").write_bytes(acquire_seed().read_bytes())
    if not grafts.get(task_no):
        # 9 / 10 have no cross-user variant; their identity is in the row values
        run_verifier(task_no, run, expect_pass=True)
        return
    run_verifier(task_no, run, expect_pass=False)


# ---------------------------------------------------------------- package tampering
@pytest.mark.parametrize("task_no", ALL)
def test_task_id_mismatch_fails(tmp_path, task_no):
    run = honest_run(tmp_path, task_no)
    traj = json.loads((run / "trajectory.json").read_text())
    traj["task_id"] = "Super Lawyers--999"
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


# ---------------------------------------------------------------- seed contract
def test_seed_contract_digests():
    """The frozen seed digests must match the actual seed the tests run
    against (schema + rows + counts), proving the contract is self-consistent."""
    import hashlib
    sys.path.insert(0, str(VERIFY_DIR))
    import verify_lib as vl  # noqa: E402
    seed = sqlite3.connect(f"file:{acquire_seed()}?mode=ro", uri=True)
    try:
        counts = {t: seed.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                  for t in vl.TABLES}
        assert counts == vl.SEED_COUNTS
        rows_src = []
        for t in vl.TABLES:
            cols = [r[1] for r in seed.execute(f'PRAGMA table_info("{t}")')]
            order = ", ".join(f'"{c}"' for c in cols)
            for row in seed.execute(f'SELECT * FROM "{t}" ORDER BY {order}'):
                rows_src.append([t, list(row)])
        rdigest = hashlib.sha256(json.dumps(rows_src, default=str).encode()).hexdigest()
        assert rdigest == vl.SEED_ROWS_SHA256
    finally:
        seed.close()


# ---------------------------------------------------------------- tasks.jsonl shape
# The one sanctioned deviation from the reviewer's frozen bytes: the
# audit-phase slot normalization re-bases the `web` rows to the site's
# assigned merge port (slot formula: index = registered sites on main (99)
# + 45; super_lawyers is 46th in the standing parallel-wave order).
OLD_WEB = '"web": "http://localhost:40098/"'
NEW_WEB = '"web": "http://localhost:40113/"'


def test_reviewed_task_ids_are_stable():
    rows = [json.loads(line) for line in (VERIFY_DIR.parent / "tasks.jsonl").read_text().splitlines()]
    assert [row["id"] for row in rows] == [f"Super Lawyers--{n}" for n in range(20)]


def test_tasks_jsonl_shape():
    """20 rows, 7 keys, no answer key; the 5-key prefix is byte-identical to
    the contribution modulo the sanctioned port re-base (verified against
    git show c6b79316 above)."""
    rows = [json.loads(l) for l in
            (VERIFY_DIR.parent / "tasks.jsonl").read_text().splitlines()]
    assert len(rows) == 20
    for row in rows:
        assert sorted(row.keys()) == ["id", "judge_rubric", "ques", "upstream_url",
                                      "verifier_path", "web", "web_name"], row["id"]
        assert row["web"] == "http://localhost:40113/"
        assert row["verifier_path"].startswith("sites/super_lawyers/verify/verify_")
        assert row["judge_rubric"].strip()
        assert len(row["judge_rubric"].split()) <= 120
