"""Shared fixtures for the_weather_network verifier tests.

Snapshots are copies of the real seed (instance_seed/the_weather_network.db
from the review container wh-twn-review) with the per-task stateful mutations
applied through sqlite, and trajectories are written in the agent_demo/agent.py
shape from the frozen SPECS (extracted from the reviewer's honest live runs).
No LLM.

The seed DB resolves from the review container (wh-twn-review); the
TWN_TEST_SEED_DB env var overrides the location. Run with plain python3 +
pytest:

    python3 -m pytest sites/the_weather_network/verify/tests -q
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import zlib
from pathlib import Path

from fixtures_data import BASE, SPECS  # noqa: E402  (same directory)

VERIFY_DIR = Path(__file__).resolve().parents[1]
SITE_DIR = VERIFY_DIR.parent
CONTAINER = os.environ.get("WH_CONTAINER", "wh-twn-review")
CACHE = Path(os.environ.get("TWN_TEST_SEED_DB") or str(SITE_DIR / "instance_seed" / "the_weather_network.db"))
TASKS_FILE = SITE_DIR / "tasks.jsonl"
PASSWORD = "TestPass123!"

sys.path.insert(0, str(VERIFY_DIR))


def acquire_seed() -> Path:
    if CACHE.is_file():
        return CACHE
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["docker", "cp",
                        f"{CONTAINER}:/opt/WebSyn/the_weather_network/instance_seed/the_weather_network.db",
                        str(CACHE)], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"cannot acquire the seed DB (docker cp failed): {r.stderr[:200]}")
    return CACHE


def task_ques(task_id: str) -> str:
    for line in TASKS_FILE.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["id"] == task_id:
            return row["ques"]
    raise KeyError(task_id)


# ------------------------------------------------------------------ tiny valid PNG
def tiny_png(width: int = 4, height: int = 4) -> bytes:
    raw = b"".join(b"\x00" + b"\x40\x90\xd0" * width for _ in range(height))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (len(data).to_bytes(4, "big") + tag + data
                + zlib.crc32(tag + data).to_bytes(4, "big"))

    ihdr = width.to_bytes(4, "big") + height.to_bytes(4, "big") + b"\x08\x02\x00\x00\x00"
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


PNG = tiny_png()


# ------------------------------------------------------------------ run-dir builder
class RunBuilder:
    """Writes an agent_demo-shaped run directory: trajectory.json + screenshots/."""

    def __init__(self, root: Path, task_id: str, start_path: str = "/en"):
        self.root = root
        self.shots_dir = root / "screenshots"
        self.shots_dir.mkdir(parents=True, exist_ok=True)
        self.task_id = task_id
        self.start_path = start_path
        self.steps = []

    def add_step(self, action: str, url_after: str, params: dict | None = None) -> None:
        if url_after.startswith("/"):
            url_after = BASE + url_after
        name = f"step_{len(self.steps) + 1:03d}.png"
        (self.shots_dir / name).write_bytes(PNG)
        self.steps.append({
            "step": len(self.steps),
            "url": BASE + self.start_path if not self.steps else self.steps[-1]["url_after"],
            "title": "The Weather Network",
            "thought": f"{action} {url_after}",
            "action": action,
            "params": params or {},
            "observed_text": f"page text for {url_after}",
            "screenshot_before": self.steps[-1]["screenshot_after"] if self.steps else name,
            "screenshot_after": name,
            "url_after": url_after,
        })

    def finish(self, answer: str, terminated: bool = True,
               reason: str = "agent_done") -> dict:
        if self.steps:
            self.steps[-1]["action"] = "done"
            self.steps[-1]["params"] = {"text": answer, "success": True}
        traj = {
            "task": task_ques(self.task_id),
            "task_id": self.task_id,
            "start_url": BASE + self.start_path,
            "model": "reviewer-fixture",
            "max_steps": 60,
            "steps": self.steps,
            "terminated": terminated,
            "termination_reason": reason if terminated else None,
            "final_answer": answer,
            "judge_rubric": "",
            "verifier_path": "",
            "final_url": self.steps[-1]["url_after"] if self.steps else BASE + self.start_path,
            "final_observed_text": "",
        }
        (self.root / "trajectory.json").write_text(json.dumps(traj, indent=1))
        return traj


def copy_db(src: Path, dest: Path) -> Path:
    shutil.copyfile(src, dest)
    return dest


def exec_sql(db_path: Path, statements: list[str]) -> None:
    con = sqlite3.connect(db_path)
    for stmt in statements:
        con.execute(stmt)
    con.commit()
    con.close()


def build_run(tmp_path: Path, task_no: int, *, apply_sql: bool = True,
              answer_override: str | None = None, steps_override=None,
              mutate_after_sql: str | None = None) -> Path:
    """Materialise run_dir + initial.db + after.db for one fixture task."""
    spec = SPECS[task_no]
    run_dir = tmp_path / f"run{task_no}"
    run_dir.mkdir(parents=True, exist_ok=True)
    seed = acquire_seed()
    initial = copy_db(seed, run_dir / "initial.db")
    after = copy_db(seed, run_dir / "after.db")
    if apply_sql:
        exec_sql(after, spec["sql"])
    if mutate_after_sql:
        exec_sql(after, [mutate_after_sql])
    rb = RunBuilder(run_dir, f"The Weather Network--{task_no}")
    steps = steps_override if steps_override is not None else spec["steps"]
    for action, url in steps:
        rb.add_step(action, url)
    rb.finish(answer_override if answer_override is not None else spec["answer"])
    return run_dir


def honest_run(tmp_path: Path, task_no: int) -> Path:
    return build_run(tmp_path, task_no, apply_sql=True)


def noop_run(tmp_path: Path, task_no: int) -> Path:
    """Homepage only, empty answer, clean DB."""
    seed = acquire_seed()
    run_dir = tmp_path / f"noop{task_no}"
    run_dir.mkdir(parents=True, exist_ok=True)
    copy_db(seed, run_dir / "initial.db")
    copy_db(seed, run_dir / "after.db")
    rb = RunBuilder(run_dir, f"The Weather Network--{task_no}")
    rb.add_step("observe", "/en")
    rb.finish("I looked at the homepage but did not complete the task.")
    return run_dir


def shortcut_run(tmp_path: Path, task_no: int) -> Path:
    """Correct answer + correct DB delta, but homepage-only navigation."""
    spec = SPECS[task_no]
    return build_run(tmp_path, task_no, apply_sql=True,
                      steps_override=[("observe", "/en")],
                      answer_override=spec["answer"])


def wrong_answer_run(tmp_path: Path, task_no: int, wrong: str) -> Path:
    return build_run(tmp_path, task_no, apply_sql=True, answer_override=wrong)


def state_mismatch_run(tmp_path: Path, task_no: int) -> Path:
    """Honest navigation + success claim, but the DB is unchanged."""
    return build_run(tmp_path, task_no, apply_sql=False)


def run_verifier(task_no: int, run_dir: Path, expect_pass: bool) -> dict:
    module = __import__(f"verify_{task_no}")
    import argparse as ap
    argv = ["--run_dir", str(run_dir)]
    # keep stdout clean: capture the JSON verdict
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = module.run_verifier(module.TASK_ID, module.run_checks, argv)
    verdict = json.loads(buf.getvalue())
    if expect_pass:
        assert verdict["pass"] is True, f"expected PASS, got {verdict['reason']}"
        assert code == 0
    else:
        assert verdict["pass"] is False, f"expected FAIL, got PASS for {verdict['task_id']}"
        assert code == 1
    return verdict
