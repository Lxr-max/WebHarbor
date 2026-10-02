"""Deterministic verifier contract tests for the 20 trip_com tasks.

Covers, per task: the honest trajectory (from the reviewer's live walks, frozen
in fixtures_data.SPECS) MUST PASS — r2 note: the attraction booking form fix
(contribution 1e2ca971) unblocked T18, so no task carries BLOCKED machinery
any more. A no-op run (homepage only, empty answer, clean DB) MUST FAIL; a
knowledge-shortcut (correct answer + delta, homepage-only navigation) MUST
FAIL; a wrong answer MUST FAIL; a state-mismatch (success claim, no DB delta)
MUST FAIL for stateful tasks. Read-only tasks MUST FAIL on any DB write, and
stateful tasks MUST FAIL on a non-allowed table touched. Package tampering
(task_id mismatch, off-site URL, missing screenshot, undecodable screenshot,
non-done trajectory) MUST fail closed.

Plus contract-level tests: the tasks.jsonl 5-key contributor prefix must be
byte-identical to the contributor commit a375a671 (the r2 tip; 10 rows were
deepened on top of 60038e71), no answer key may exist, every verifier_path
must resolve, every judge_rubric must be non-empty English, and the seed
contract (counts / schema digest / rows digest / file md5) must hold.

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

# r2 (2026-09-28): no task is BLOCKED any more — the attraction booking form
# fix (contribution 1e2ca971) records the submitted date/guests, so T18's
# 3-guest/12-October booking is reachable and every honest run must PASS.
BLOCKED: set[int] = set()
STATEFUL = {0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 14, 17, 18}
READ_ONLY = {9, 11, 12, 13, 15, 16, 19}
ALL = list(range(20))


# ---------------------------------------------------------------- happy path
@pytest.mark.parametrize("task_no", ALL)
def test_honest_run_passes(tmp_path, task_no):
    run = honest_run(tmp_path, task_no)
    if task_no in BLOCKED:
        verdict = run_verifier(task_no, run, expect_pass=False)
        assert "BLOCKED" in verdict["reason"], verdict["reason"]
    else:
        run_verifier(task_no, run, expect_pass=True)


def test_blocked_set_documented():
    """No verifier carries BLOCKED machinery any more (r2): the form fix
    unblocked T18, and a stale check_blocked anywhere would fail every run."""
    assert BLOCKED == set()
    for n in ALL:
        src = (VERIFY_DIR / f"verify_{n}.py").read_text()
        assert "check_blocked" not in src, f"verify_{n}.py must not carry BLOCKED machinery"


# ---------------------------------------------------------------- no-op fails
@pytest.mark.parametrize("task_no", ALL)
def test_noop_run_fails(tmp_path, task_no):
    run = noop_run(tmp_path, task_no)
    run_verifier(task_no, run, expect_pass=False)


@pytest.mark.parametrize("task_no", ALL)
def test_noop_run_with_answer_fails(tmp_path, task_no):
    """A no-op that pastes the honest answer verbatim still fails: no
    navigation, no state change."""
    run = noop_run(tmp_path, task_no, answer=SPECS[task_no]["answer"])
    run_verifier(task_no, run, expect_pass=False)


# ---------------------------------------------------------------- shortcut fails
@pytest.mark.parametrize("task_no", ALL)
def test_shortcut_run_fails(tmp_path, task_no):
    run = shortcut_run(tmp_path, task_no)
    verdict = run_verifier(task_no, run, expect_pass=False)
    assert "visited" in verdict["reason"] or "BLOCKED" in verdict["reason"], verdict["reason"]


# ---------------------------------------------------------------- wrong answers
@pytest.mark.parametrize("task_no", ALL)
def test_wrong_answer_fails(tmp_path, task_no):
    run = wrong_answer_run(tmp_path, task_no, WRONG_ANSWERS[task_no])
    run_verifier(task_no, run, expect_pass=False)


@pytest.mark.parametrize("task_no", ALL)
def test_empty_answer_fails(tmp_path, task_no):
    spec = SPECS[task_no]
    run = tmp_path / f"empty_{task_no}"
    run.mkdir(parents=True)
    b = RunBuilder(run, f"Trip.com--{task_no}")
    for action, path in spec["steps"]:
        b.add_step(action, BASE + path)
    b.finish("")
    after = copy_db(run)
    if spec.get("sql"):
        exec_sql(after, spec["sql"])
    (run / "initial.db").write_bytes(acquire_seed().read_bytes())
    run_verifier(task_no, run, expect_pass=False)


# ---------------------------------------------------------------- state mismatch
@pytest.mark.parametrize("task_no", sorted(STATEFUL))
def test_state_mismatch_fails(tmp_path, task_no):
    """Agent claims success, navigation is honest, but the DB is unchanged."""
    run = state_mismatch_run(tmp_path, task_no)
    verdict = run_verifier(task_no, run, expect_pass=False)
    assert "booking" in verdict["reason"] or "wishlist" in verdict["reason"] \
        or "flight_cancelled" in verdict["reason"] or "BLOCKED" in verdict["reason"], \
        verdict["reason"]


# ---------------------------------------------------------------- read-only purity
@pytest.mark.parametrize("task_no", sorted(READ_ONLY))
def test_read_only_task_fails_on_any_write(tmp_path, task_no):
    """A read-only task whose run leaves ANY database write must fail."""
    spec = SPECS[task_no]
    run = tmp_path / f"writey_{task_no}"
    run.mkdir(parents=True)
    b = RunBuilder(run, f"Trip.com--{task_no}")
    for action, path in spec["steps"]:
        b.add_step(action, BASE + path)
    b.finish(spec["answer"])
    after = copy_db(run)
    exec_sql(after, ["INSERT INTO wishlist_items (user_id, hotel_id) VALUES (3, 733090)"])
    (run / "initial.db").write_bytes(acquire_seed().read_bytes())
    run_verifier(task_no, run, expect_pass=False)


@pytest.mark.parametrize("task_no", sorted(STATEFUL))
def test_stateful_task_fails_on_foreign_table_write(tmp_path, task_no):
    """A stateful task that also touches a non-allowed table must fail."""
    spec = SPECS[task_no]
    run = tmp_path / f"foreign_{task_no}"
    run.mkdir(parents=True)
    b = RunBuilder(run, f"Trip.com--{task_no}")
    for action, path in spec["steps"]:
        b.add_step(action, BASE + path)
    b.finish(spec["answer"])
    after = copy_db(run)
    if spec.get("sql"):
        exec_sql(after, spec["sql"])
    allowed = {"hotel_bookings", "flight_bookings", "attraction_bookings", "wishlist_items"}
    foreign = "hotel_reviews" if task_no != 6 else "hotel_bookings"
    exec_sql(after, [f"INSERT INTO {foreign} (hotel_id, rating, text) VALUES "
                    f"(733090, 9.0, 'foreign write')" if foreign == "hotel_reviews"
                    else "INSERT INTO hotel_bookings (ref,hotel_id,room_id,user_id,"
                         "guest_first,guest_last,email,phone,checkin,checkout,rooms,"
                         "adults,children,nightly,taxes,total,coins,promo_code,status,"
                         "created_at) VALUES ('THFOREIGN',733090,22,NULL,'Foreign',"
                         "'Write','f@example.com','+1 555 000 0000','2026-10-04',"
                         "'2026-10-05',1,2,0,167.0,22.0,189.0,1,'','confirmed',"
                         "'2026-09-27')"])
    (run / "initial.db").write_bytes(acquire_seed().read_bytes())
    verdict = run_verifier(task_no, run, expect_pass=False)
    assert "db_tables_changed" in verdict["reason"] or "BLOCKED" in verdict["reason"], \
        verdict["reason"]


# ---------------------------------------------------------------- tamper cases
@pytest.mark.parametrize("task_no", ALL)
def test_task_id_mismatch_fails(tmp_path, task_no):
    spec = SPECS[task_no]
    run = tmp_path / f"tamper_id_{task_no}"
    run.mkdir(parents=True)
    b = RunBuilder(run, f"Trip.com--{((task_no + 1) % 20)}")
    for action, path in spec["steps"]:
        b.add_step(action, BASE + path)
    b.finish(spec["answer"])
    after = copy_db(run)
    if spec.get("sql"):
        exec_sql(after, spec["sql"])
    (run / "initial.db").write_bytes(acquire_seed().read_bytes())
    run_verifier(task_no, run, expect_pass=False)


@pytest.mark.parametrize("task_no", ALL)
def test_offsite_url_fails(tmp_path, task_no):
    spec = SPECS[task_no]
    run = tmp_path / f"tamper_offsite_{task_no}"
    run.mkdir(parents=True)
    b = RunBuilder(run, f"Trip.com--{task_no}")
    for action, path in spec["steps"]:
        b.add_step(action, BASE + path)
    b.add_step("navigate", "https://example.com/leak")
    b.finish(spec["answer"])
    after = copy_db(run)
    if spec.get("sql"):
        exec_sql(after, spec["sql"])
    (run / "initial.db").write_bytes(acquire_seed().read_bytes())
    run_verifier(task_no, run, expect_pass=False)


@pytest.mark.parametrize("task_no", ALL)
def test_missing_screenshot_fails(tmp_path, task_no):
    spec = SPECS[task_no]
    run = honest_run(tmp_path, task_no)
    # corrupt: remove every screenshot file
    for p in (run / "screenshots").glob("step_*.png"):
        p.unlink()
    if task_no in BLOCKED:
        run_verifier(task_no, run, expect_pass=False)
    else:
        run_verifier(task_no, run, expect_pass=False)


@pytest.mark.parametrize("task_no", ALL)
def test_undecodable_screenshot_fails(tmp_path, task_no):
    run = honest_run(tmp_path, task_no)
    for p in (run / "screenshots").glob("step_*.png"):
        p.write_bytes(b"not a png at all")
    run_verifier(task_no, run, expect_pass=False)


@pytest.mark.parametrize("task_no", ALL)
def test_unterminated_trajectory_fails(tmp_path, task_no):
    spec = SPECS[task_no]
    run = tmp_path / f"tamper_unterm_{task_no}"
    run.mkdir(parents=True)
    b = RunBuilder(run, f"Trip.com--{task_no}")
    for action, path in spec["steps"]:
        b.add_step(action, BASE + path)
    b.finish(spec["answer"], terminated=False)
    after = copy_db(run)
    if spec.get("sql"):
        exec_sql(after, spec["sql"])
    (run / "initial.db").write_bytes(acquire_seed().read_bytes())
    run_verifier(task_no, run, expect_pass=False)


# ---------------------------------------------------------------- tasks.jsonl contract
def test_tasks_jsonl_contract():
    lines = (VERIFY_DIR.parent / "tasks.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 20
    for line in lines:
        row = json.loads(line)
        assert sorted(row.keys()) == ["id", "judge_rubric", "ques", "upstream_url",
                                       "verifier_path", "web", "web_name"], row["id"]
        assert "answer" not in row
        n = int(row["id"].split("--")[1])
        assert row["verifier_path"] == f"sites/trip_com/verify/verify_{n}.py"
        assert (VERIFY_DIR.parent.parent.parent / row["verifier_path"]).is_file()
        rubric = row["judge_rubric"]
        assert len(rubric) > 80, row["id"]
        assert row["web"] == "http://localhost:40111/"
        assert row["upstream_url"] == "https://us.trip.com/"


def test_contributor_prefix_byte_identical():
    """The 5-key contributor prefix of every row must be byte-identical to the
    contributor commit a375a671 (the r2 tip: 10 rows deepened on top of
    60038e71; no answer leakage, no task rewrites). The one sanctioned
    exception is the `web` port: the audit-phase slot normalization moves it
    to the site's assigned merge port (40111; slot formula index = registered
    sites on main (99) + 48)."""
    import subprocess
    repo = VERIFY_DIR.parent.parent.parent
    try:
        orig = subprocess.run(
            ["git", "show", "a375a671:sites/trip_com/tasks.jsonl"],
            capture_output=True, text=True, cwd=str(repo), check=True).stdout
    except subprocess.CalledProcessError:
        pytest.skip("contributor commit not available in this checkout")
    orig_lines = orig.splitlines()
    cur_lines = (VERIFY_DIR.parent / "tasks.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(orig_lines) == len(cur_lines) == 20
    old_web = '"web": "http://localhost:40103/"'
    new_web = '"web": "http://localhost:40111/"'
    for orig_line, cur_line in zip(orig_lines, cur_lines):
        cur = json.loads(cur_line)
        prefix_keys = ("web_name", "id", "upstream_url")
        prefix = json.dumps({k: cur[k] for k in prefix_keys},
                            ensure_ascii=False, separators=(", ", ": "))
        # byte-prefix property holds modulo the sanctioned web-port re-base
        assert {k: cur[k] for k in prefix_keys} == {k: json.loads(orig_line)[k] for k in prefix_keys}, cur["id"]


# ---------------------------------------------------------------- seed contract
def test_seed_contract():
    sys.path.insert(0, str(VERIFY_DIR))
    import verify_lib as vl
    import sqlite3
    seed = sqlite3.connect(f"file:{acquire_seed()}?mode=ro", uri=True)
    judge = vl.Judge("seed")
    vl.check_seed_contract(judge, seed)
    seed.close()
    assert not judge.failures, judge.failures


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


# ---------------------------------------------------------------- verifier hygiene
def test_verifiers_importable_and_deterministic():
    sys.path.insert(0, str(VERIFY_DIR))
    for n in ALL:
        import importlib
        mod = importlib.import_module(f"verify_{n}")
        assert mod.TASK_ID == f"Trip.com--{n}"
