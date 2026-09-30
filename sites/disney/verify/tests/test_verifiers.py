"""test_verifiers.py — adversarial contract tests for the disney reviewer
verifier set (verify_0.py .. verify_19.py).

  * every honest fixture MUST PASS its verifier (20 runs transcribed from
    the r2 reviewer's independent Playwright walks on wh-disney-r2-review);
  * the no-op / knowledge-shortcut / wrong-answer / read-only-tamper /
    package-tamper / stale-state / task-confusion negatives MUST FAIL
    (zero false positives).

Seed source: the r2 review container (wh-disney-r2-review) or an explicit
frozen seed DB via WH_DISNEY_SEED_DB.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _support
import fixtures_data

HERE = Path(__file__).resolve().parent
VERIFY_DIR = HERE.parent
SEED_ENV = "WH_DISNEY_SEED_DB"
CONTAINER = "wh-disney-r2-review"
BASE = fixtures_data.B


def seed_source(tmp_path) -> Path:
    if os.environ.get(SEED_ENV):
        return Path(os.environ[SEED_ENV])
    out = tmp_path / "seed.db"
    src = f"{CONTAINER}:/opt/WebSyn/disney/instance_seed/disney.db"
    proc = subprocess.run(["docker", "cp", src, str(out)],
                          capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, f"docker cp seed failed: {proc.stderr[:200]}"
    return out


def run_verifier(n, run_dir, task_id=None):
    proc = subprocess.run(
        [sys.executable, str(VERIFY_DIR / f"verify_{n}.py"),
         "--run_dir", str(run_dir)],
        capture_output=True, text=True, timeout=180)
    try:
        verdict = json.loads(proc.stdout)
    except json.JSONDecodeError:
        verdict = {"pass": False, "reason": proc.stdout + proc.stderr}
    return verdict


def falsify(answer: str) -> str:
    """Falsify every number token in an honest answer."""
    def bump(m):
        v = m.group(0)
        if "." in v:
            return f"{float(v.replace(',', '')) * 2 + 1:.2f}"
        iv = int(v.replace(",", "")) + 3
        return f"{iv:,}" if "," in v else str(iv)
    return re.sub(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?", bump, answer)


def honest_run(tmp_path, n, seed):
    spec = fixtures_data.SPECS[str(n)]
    initial = _support.seed_db(tmp_path / f"h{n}-init", seed)
    after = tmp_path / f"h{n}-init" / "after.db"
    shutil.copyfile(initial, after)
    if spec.get("sql"):
        _support.apply_sql(after, spec["sql"])
    return _support.build_run(tmp_path / f"h{n}", f"Disney--{n}",
                              spec["urls"], spec["answer"], initial, after)


@pytest.fixture(scope="session")
def seed(tmp_path_factory):
    return seed_source(tmp_path_factory.mktemp("seed"))


# ------------------------------------------------------------------ honest --
@pytest.mark.parametrize("n", range(20))
def test_honest_fixture_passes(tmp_path, seed, n):
    run = honest_run(tmp_path, n, seed)
    verdict = run_verifier(n, run)
    assert verdict["pass"], f"honest Disney--{n} must PASS: {verdict['reason']}"


# -------------------------------------------------------------------- no-op --
@pytest.mark.parametrize("n", range(20))
def test_noop_run_fails(tmp_path, seed, n):
    initial = _support.seed_db(tmp_path / f"no{n}-init", seed)
    after = tmp_path / f"no{n}-init" / "after.db"
    shutil.copyfile(initial, after)
    run = _support.build_run(tmp_path / f"no{n}", f"Disney--{n}",
                             [], "I looked at the site.", initial, after,
                             no_steps=True, shots=0)
    verdict = run_verifier(n, run)
    assert not verdict["pass"], f"no-op Disney--{n} must FAIL"


# -------------------------------------------------------- knowledge shortcut --
@pytest.mark.parametrize("n", range(20))
def test_answer_only_shortcut_fails(tmp_path, seed, n):
    spec = fixtures_data.SPECS[str(n)]
    initial = _support.seed_db(tmp_path / f"sc{n}-init", seed)
    after = tmp_path / f"sc{n}-init" / "after.db"
    shutil.copyfile(initial, after)
    if spec.get("sql"):
        _support.apply_sql(after, spec["sql"])
    run = _support.build_run(tmp_path / f"sc{n}", f"Disney--{n}",
                             [spec["urls"][0]], spec["answer"], initial, after,
                             no_steps=True, shots=0)
    verdict = run_verifier(n, run)
    assert not verdict["pass"], "pure-answer shortcut must FAIL (navigation gates)"


# ------------------------------------------------------------- wrong answer --
@pytest.mark.parametrize("n", range(20))
def test_wrong_answer_fails(tmp_path, seed, n):
    run = honest_run(tmp_path, n, seed)
    traj = json.loads((run / "trajectory.json").read_text())
    traj["final_answer"] = falsify(traj["final_answer"])
    (run / "trajectory.json").write_text(json.dumps(traj))
    verdict = run_verifier(n, run)
    assert not verdict["pass"], f"falsified-answer Disney--{n} must FAIL"


# ------------------------------------------------------- read-only tampering --
@pytest.mark.parametrize("n", [2, 6, 8])
def test_readonly_write_tamper_fails(tmp_path, seed, n):
    spec = fixtures_data.SPECS[str(n)]
    assert spec.get("sql") is None
    initial = _support.seed_db(tmp_path / f"ro{n}-init", seed)
    after = tmp_path / f"ro{n}-init" / "after.db"
    shutil.copyfile(initial, after)
    _support.apply_sql(after, "INSERT INTO favorites (user_id, item_type, item_key, added_at) "
                              "VALUES (1, 'movie', 'moana-2', '2026-09-29');")
    run = _support.build_run(tmp_path / f"ro{n}", f"Disney--{n}",
                            spec["urls"], spec["answer"], initial, after)
    verdict = run_verifier(n, run)
    assert not verdict["pass"], "read-only task with a mutated DB must FAIL"


# ----------------------------------------------------------- stale DB state --
@pytest.mark.parametrize("n", [0, 10, 14])
def test_stale_state_run_fails(tmp_path, seed, n):
    """Stateful task where the agent claims success but the DB is unchanged."""
    spec = fixtures_data.SPECS[str(n)]
    assert spec.get("sql")
    initial = _support.seed_db(tmp_path / f"st{n}-init", seed)
    after = tmp_path / f"st{n}-init" / "after.db"
    shutil.copyfile(initial, after)
    run = _support.build_run(tmp_path / f"st{n}", f"Disney--{n}",
                            spec["urls"], spec["answer"], initial, after)
    verdict = run_verifier(n, run)
    assert not verdict["pass"], "stale-state run (no DB delta) must FAIL"


# --------------------------------------------------------- package identity --
def test_wrong_task_id_fails(tmp_path, seed):
    run = honest_run(tmp_path, 0, seed)
    traj = json.loads((run / "trajectory.json").read_text())
    traj["task_id"] = "Disney--19"
    (run / "trajectory.json").write_text(json.dumps(traj))
    verdict = run_verifier(0, run)
    assert not verdict["pass"], "task_id mismatch must FAIL"


def test_unterminated_run_fails(tmp_path, seed):
    run = honest_run(tmp_path, 1, seed)
    traj = json.loads((run / "trajectory.json").read_text())
    traj["terminated"] = False
    traj["agent_done"] = False
    (run / "trajectory.json").write_text(json.dumps(traj))
    verdict = run_verifier(1, run)
    assert not verdict["pass"], "unterminated run must FAIL"


def test_empty_answer_fails(tmp_path, seed):
    run = honest_run(tmp_path, 2, seed)
    traj = json.loads((run / "trajectory.json").read_text())
    traj["final_answer"] = ""
    (run / "trajectory.json").write_text(json.dumps(traj))
    verdict = run_verifier(2, run)
    assert not verdict["pass"], "empty answer must FAIL"


def test_offsite_url_fails(tmp_path, seed):
    spec = fixtures_data.SPECS["3"]
    initial = _support.seed_db(tmp_path / "off3-init", seed)
    after = tmp_path / "off3-init" / "after.db"
    shutil.copyfile(initial, after)
    _support.apply_sql(after, spec["sql"])
    urls = spec["urls"] + ["https://www.disney.com/shows/ducktales"]
    run = _support.build_run(tmp_path / "off3", "Disney--3", urls,
                             spec["answer"], initial, after)
    verdict = run_verifier(3, run)
    assert not verdict["pass"], "off-origin URL must FAIL"


def test_corrupt_screenshot_fails(tmp_path, seed):
    run = honest_run(tmp_path, 4, seed)
    (run / "screenshots" / "step_000.png").write_bytes(b"not a png")
    verdict = run_verifier(4, run)
    assert not verdict["pass"], "corrupt screenshot must FAIL"


def test_premutated_seed_fails(tmp_path, seed):
    """The initial DB is not the frozen seed — the run must fail-closed."""
    mutated = tmp_path / "mutated-seed.db"
    shutil.copyfile(seed, mutated)
    _support.apply_sql(mutated, "INSERT INTO favorites (user_id, item_type, item_key, added_at) "
                                "VALUES (1, 'movie', 'moana-2', '2026-09-29');")
    spec = fixtures_data.SPECS["0"]
    run = _support.build_run(tmp_path / "mut0", "Disney--0",
                            spec["urls"], spec["answer"], mutated, mutated)
    verdict = run_verifier(0, run)
    assert not verdict["pass"], "pre-mutated initial DB must FAIL"


# ---------------------------------------------------------- task confusion --
@pytest.mark.parametrize("n,m", [(10, 13), (14, 16)])
def test_task_confusion_fails(tmp_path, seed, n, m):
    """Honest run for task n graded by task m's verifier must FAIL."""
    run = honest_run(tmp_path, n, seed)
    traj = json.loads((run / "trajectory.json").read_text())
    traj["task_id"] = f"Disney--{m}"
    (run / "trajectory.json").write_text(json.dumps(traj))
    verdict = run_verifier(m, run)
    assert not verdict["pass"], f"Disney--{n} run graded as Disney--{m} must FAIL"

# ------------------------------------------------- audit hardening pins --
def test_truncated_screenshot_fails(tmp_path, seed):
    """A PNG truncated after the magic (payload cut) must FAIL the gate."""
    run = honest_run(tmp_path, 16, seed)
    shot = sorted((run / "screenshots").glob("step_*.png"))[0]
    data = shot.read_bytes()
    shot.write_bytes(data[:8] + data[8:len(data) // 3])
    verdict = run_verifier(16, run)
    assert not verdict["pass"], "truncated PNG (magic kept) must FAIL"


def test_magic_only_png_stub_fails(tmp_path, seed):
    run = honest_run(tmp_path, 16, seed)
    shot = sorted((run / "screenshots").glob("step_*.png"))[0]
    shot.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    verdict = run_verifier(16, run)
    assert not verdict["pass"], "magic-only PNG stub must FAIL"


def test_money_boundary_drift_fails(tmp_path, seed):
    """"$170.00" must NOT satisfy the $70.00 gate (substring hole)."""
    run = honest_run(tmp_path, 16, seed)
    traj = json.loads((run / "trajectory.json").read_text())
    traj["final_answer"] = traj["final_answer"].replace("70.00", "170.00")
    (run / "trajectory.json").write_text(json.dumps(traj))
    verdict = run_verifier(16, run)
    assert not verdict["pass"], "money substring drift must FAIL"


def test_money_cents_drift_fails(tmp_path, seed):
    run = honest_run(tmp_path, 16, seed)
    traj = json.loads((run / "trajectory.json").read_text())
    traj["final_answer"] = traj["final_answer"].replace("70.00", "70.01")
    (run / "trajectory.json").write_text(json.dumps(traj))
    verdict = run_verifier(16, run)
    assert not verdict["pass"], "money cents drift must FAIL"
