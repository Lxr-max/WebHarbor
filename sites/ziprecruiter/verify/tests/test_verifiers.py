"""test_verifiers.py — adversarial contract tests for the ziprecruiter
reviewer verifier set (verify_0.py .. verify_19.py).

  * every honest fixture MUST PASS its verifier (20 runs, two independent
    browser rounds produced identical facts);
  * the no-op / knowledge-shortcut / wrong-answer / stale-state /
    read-only-tamper / package-tamper / task-confusion negatives MUST FAIL
    (zero false positives).

Seed source: the re-review container (wh-ziprecruiter-rereview) or an explicit
frozen seed DB via WH_ZIP_SEED_DB.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _support
import fixtures_data

HERE = Path(__file__).resolve().parent
VERIFY_DIR = HERE.parent
SEED_ENV = "WH_ZIP_SEED_DB"
CONTAINER = "wh-ziprecruiter-rereview"


def seed_source(tmp_path) -> Path:
    explicit = Path(__file__).parent
    import os
    if os.environ.get(SEED_ENV):
        return Path(os.environ[SEED_ENV])
    out = tmp_path / "seed.db"
    src = f"{CONTAINER}:/opt/WebSyn/ziprecruiter/instance_seed/ziprecruiter.db"
    proc = subprocess.run(["docker", "cp", src, str(out)],
                          capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, f"docker cp seed failed: {proc.stderr[:200]}"
    return out


def run_verifier(n, run_dir):
    proc = subprocess.run(
        [sys.executable, str(VERIFY_DIR / f"verify_{n}.py"),
         "--run_dir", str(run_dir)],
        capture_output=True, text=True, timeout=120)
    try:
        verdict = json.loads(proc.stdout)
    except json.JSONDecodeError:
        verdict = {"pass": False, "reason": proc.stdout + proc.stderr}
    return verdict


def falsify(answer: str) -> str:
    """Falsify every number and money token in an honest answer."""
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
    return _support.build_run(tmp_path / f"h{n}", f"ZipRecruiter--{n}",
                              spec["urls"], spec["answer"], initial, after)


@pytest.fixture(scope="session")
def seed(tmp_path_factory):
    return seed_source(tmp_path_factory.mktemp("seed"))


# ------------------------------------------------------------------ honest --
@pytest.mark.parametrize("n", range(20))
def test_honest_fixture_passes(tmp_path, seed, n):
    run = honest_run(tmp_path, n, seed)
    verdict = run_verifier(n, run)
    assert verdict["pass"], f"honest ZipRecruiter--{n} must PASS: {verdict['reason']}"


# -------------------------------------------------------------------- no-op --
@pytest.mark.parametrize("n", range(20))
def test_noop_run_fails(tmp_path, seed, n):
    initial = _support.seed_db(tmp_path / f"no{n}-init", seed)
    after = tmp_path / f"no{n}-init" / "after.db"
    shutil.copyfile(initial, after)
    run = _support.build_run(tmp_path / f"no{n}", f"ZipRecruiter--{n}",
                             [], "I looked at the site.", initial, after,
                             no_steps=True, shots=0)
    verdict = run_verifier(n, run)
    assert not verdict["pass"], f"no-op ZipRecruiter--{n} must FAIL"


# -------------------------------------------------------- knowledge shortcut --
@pytest.mark.parametrize("n", range(20))
def test_answer_only_shortcut_fails(tmp_path, seed, n):
    spec = fixtures_data.SPECS[str(n)]
    initial = _support.seed_db(tmp_path / f"sc{n}-init", seed)
    after = tmp_path / f"sc{n}-init" / "after.db"
    shutil.copyfile(initial, after)
    run = _support.build_run(tmp_path / f"sc{n}", f"ZipRecruiter--{n}",
                             [spec["urls"][0]], spec["answer"], initial, after,
                             no_steps=True, shots=0)
    verdict = run_verifier(n, run)
    assert not verdict["pass"], "pure-answer shortcut must FAIL (navigation gates)"


# ------------------------------------------------------------ wrong answers --
@pytest.mark.parametrize("n", range(20))
def test_wrong_answers_fail(tmp_path, seed, n):
    spec = fixtures_data.SPECS[str(n)]
    initial = _support.seed_db(tmp_path / f"wa{n}-init", seed)
    after = tmp_path / f"wa{n}-init" / "after.db"
    shutil.copyfile(initial, after)
    if spec.get("sql"):
        _support.apply_sql(after, spec["sql"])
    wrong = falsify(spec["answer"])
    run = _support.build_run(tmp_path / f"wa{n}", f"ZipRecruiter--{n}",
                             spec["urls"], wrong, initial, after)
    verdict = run_verifier(n, run)
    assert not verdict["pass"], f"falsified answers on ZipRecruiter--{n} must FAIL"


# ------------------------------------------------------ read-only violations --
@pytest.mark.parametrize("n", [0, 5, 9, 13])
def test_readonly_tamper_fails(tmp_path, seed, n):
    spec = fixtures_data.SPECS[str(n)]
    initial = _support.seed_db(tmp_path / f"ro{n}-init", seed)
    after = tmp_path / f"ro{n}-init" / "after.db"
    shutil.copyfile(initial, after)
    # a stateful mutation on a read-only task
    _support.apply_sql(after, [
        "INSERT INTO job_alerts (user_id, term, location, frequency, created_at) "
        "VALUES (1, 'tamper', 'Nowhere', 'daily', '2026-09-29')"])
    run = _support.build_run(tmp_path / f"ro{n}", f"ZipRecruiter--{n}",
                             spec["urls"], spec["answer"], initial, after)
    verdict = run_verifier(n, run)
    assert not verdict["pass"], "read-only task with a state delta must FAIL"


# ------------------------------------------------- stateful stale after-DBs --
@pytest.mark.parametrize("n", [15, 16])
def test_stateful_stale_db_fails(tmp_path, seed, n):
    spec = fixtures_data.SPECS[str(n)]
    initial = _support.seed_db(tmp_path / f"st{n}-init", seed)
    after = tmp_path / f"st{n}-init" / "after.db"
    shutil.copyfile(initial, after)  # no state change at all
    run = _support.build_run(tmp_path / f"st{n}", f"ZipRecruiter--{n}",
                             spec["urls"], spec["answer"], initial, after)
    verdict = run_verifier(n, run)
    assert not verdict["pass"], "stateful task with a stale after-DB must FAIL"


# --------------------------------------------------------- package tampering --
def test_wrong_task_id_fails(tmp_path, seed):
    spec = fixtures_data.SPECS["0"]
    initial = _support.seed_db(tmp_path / "tid-init", seed)
    after = tmp_path / "tid-init" / "after.db"
    shutil.copyfile(initial, after)
    run = _support.build_run(tmp_path / "tid", "ZipRecruiter--19",
                             spec["urls"], spec["answer"], initial, after)
    verdict = run_verifier(0, run)
    assert not verdict["pass"], "wrong task_id must FAIL"


def test_offsite_url_fails(tmp_path, seed):
    spec = fixtures_data.SPECS["0"]
    initial = _support.seed_db(tmp_path / "off-init", seed)
    after = tmp_path / "off-init" / "after.db"
    shutil.copyfile(initial, after)
    run = _support.build_run(tmp_path / "off", "ZipRecruiter--0",
                             spec["urls"], spec["answer"], initial, after,
                             offsite_url="https://example.com/jobs")
    verdict = run_verifier(0, run)
    assert not verdict["pass"], "off-site navigation must FAIL"


def test_cross_port_fails(tmp_path, seed):
    spec = fixtures_data.SPECS["0"]
    initial = _support.seed_db(tmp_path / "xp-init", seed)
    after = tmp_path / "xp-init" / "after.db"
    shutil.copyfile(initial, after)
    run = _support.build_run(tmp_path / "xp", "ZipRecruiter--0",
                             spec["urls"], spec["answer"], initial, after,
                             start_url="http://localhost:51115/")
    verdict = run_verifier(0, run)
    assert not verdict["pass"], "cross-port URL must FAIL"


def test_unterminated_fails(tmp_path, seed):
    spec = fixtures_data.SPECS["1"]
    initial = _support.seed_db(tmp_path / "ut-init", seed)
    after = tmp_path / "ut-init" / "after.db"
    shutil.copyfile(initial, after)
    run = _support.build_run(tmp_path / "ut", "ZipRecruiter--1",
                             spec["urls"], spec["answer"], initial, after,
                             terminate=False)
    verdict = run_verifier(1, run)
    assert not verdict["pass"], "unterminated run must FAIL"


def test_empty_answer_fails(tmp_path, seed):
    spec = fixtures_data.SPECS["2"]
    initial = _support.seed_db(tmp_path / "ea-init", seed)
    after = tmp_path / "ea-init" / "after.db"
    shutil.copyfile(initial, after)
    run = _support.build_run(tmp_path / "ea", "ZipRecruiter--2",
                             spec["urls"], "  ", initial, after)
    verdict = run_verifier(2, run)
    assert not verdict["pass"], "empty final answer must FAIL"


def test_bad_png_fails(tmp_path, seed):
    spec = fixtures_data.SPECS["3"]
    initial = _support.seed_db(tmp_path / "bp-init", seed)
    after = tmp_path / "bp-init" / "after.db"
    shutil.copyfile(initial, after)
    run = _support.build_run(tmp_path / "bp", "ZipRecruiter--3",
                             spec["urls"], spec["answer"], initial, after,
                             bad_png=True)
    verdict = run_verifier(3, run)
    assert not verdict["pass"], "corrupt screenshot must FAIL"


def test_premutated_seed_fails(tmp_path, seed):
    spec = fixtures_data.SPECS["4"]
    initial = _support.seed_db(tmp_path / "pm-init", seed)
    _support.apply_sql(initial, [
        "INSERT INTO job_alerts (user_id, term, location, frequency, created_at) "
        "VALUES (1, 'premutated', 'Nowhere', 'daily', '2026-09-29')"])
    after = tmp_path / "pm-init" / "after.db"
    shutil.copyfile(initial, after)
    run = _support.build_run(tmp_path / "pm", "ZipRecruiter--4",
                             spec["urls"], spec["answer"], initial, after)
    verdict = run_verifier(4, run)
    assert not verdict["pass"], "pre-mutated seed must FAIL the seed gate"


# --------------------------------------------------------- task confusion ----
@pytest.mark.parametrize("pair", [(9, 7), (12, 2), (17, 18), (10, 19)])
def test_cross_task_answer_fails(tmp_path, seed, pair):
    run_ver, ans_task = pair
    spec = fixtures_data.SPECS[str(ans_task)]
    own = fixtures_data.SPECS[str(run_ver)]
    initial = _support.seed_db(tmp_path / f"cf{run_ver}-init", seed)
    after = tmp_path / f"cf{run_ver}-init" / "after.db"
    shutil.copyfile(initial, after)
    if own.get("sql"):
        _support.apply_sql(after, own["sql"])
    run = _support.build_run(tmp_path / f"cf{run_ver}", f"ZipRecruiter--{run_ver}",
                             own["urls"], spec["answer"], initial, after)
    verdict = run_verifier(run_ver, run)
    assert not verdict["pass"], f"ZipRecruiter--{ans_task} answers under ZipRecruiter--{run_ver} must FAIL"
