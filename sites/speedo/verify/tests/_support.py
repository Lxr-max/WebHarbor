"""Shared fixtures for the speedo verifier tests.

Snapshots are copies of the real deterministic seed (instance_seed/speedo.db,
built at image time with PYTHONHASHSEED=0, md5 5561ace9…) with the per-task
stateful mutations applied through sqlite, and trajectories are written in
the agent_demo/agent.py shape from the frozen SPECS (extracted from the
reviewer's honest live runs). No LLM.

The seed DB resolves from the review container (wh-speedo-review); the
SPEEDO_TEST_SEED_DB env var overrides the location. Run with plain
python3 + pytest:

    python3 -m pytest sites/speedo/verify/tests -q
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
CONTAINER = os.environ.get("WH_CONTAINER", "wh-speedo-review")
CACHE = Path(os.environ.get("SPEEDO_TEST_SEED_DB") or
             str(Path("/tmp") / "speedo_verify_tests_seed.db"))
TASKS_FILE = SITE_DIR / "tasks.jsonl"
PASSWORD = "TestPass123!"


def acquire_seed() -> Path:
    seed = Path(os.environ["SPEEDO_TEST_SEED_DB"]) if os.environ.get("SPEEDO_TEST_SEED_DB") else SITE_DIR / "instance_seed/speedo.db"
    if not seed.is_file():
        raise RuntimeError("Build the site seed before running verifier tests")
    return seed

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

    def __init__(self, root: Path, task_id: str, start_path: str = "/"):
        self.root = root
        self.shots_dir = root / "screenshots"
        self.shots_dir.mkdir(parents=True, exist_ok=True)
        self.task_id = task_id
        self.start_path = start_path
        self.steps = []

    def add_step(self, action: str, url_after: str, params: dict | None = None,
                 shot: str | None = None) -> None:
        name = f"step_{len(self.steps) + 1:03d}.png"
        (self.shots_dir / name).write_bytes(PNG)
        base = BASE if not self.start_path.startswith("http") else self.start_path
        self.steps.append({
            "step": len(self.steps),
            "url": base if not self.steps else self.steps[-1]["url_after"],
            "title": "Speedo",
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
            "start_url": BASE if not self.start_path.startswith("http") else self.start_path,
            "model": "reviewer-fixture",
            "max_steps": 40,
            "steps": self.steps,
            "terminated": terminated,
            "termination_reason": reason if terminated else None,
            "final_answer": answer,
            "judge_rubric": "",
            "verifier_path": "",
            "final_url": self.steps[-1]["url_after"] if self.steps else BASE,
            "final_observed_text": "",
        }
        (self.root / "trajectory.json").write_text(json.dumps(traj, indent=1))
        return traj


# ------------------------------------------------------------------ db helpers
def copy_db(tmp_path: Path, name: str = "after.db") -> Path:
    dest = tmp_path / name
    shutil.copyfile(acquire_seed(), dest)
    return dest


def exec_sql(db_path: Path, statements) -> None:
    db = sqlite3.connect(db_path)
    for q in statements:
        db.execute(q)
    db.commit()
    db.close()


# ------------------------------------------------------------------ run shapes
def honest_run(tmp_path: Path, task_no: int) -> Path:
    spec = SPECS[task_no]
    run = tmp_path / f"honest_{task_no}"
    run.mkdir(parents=True)
    b = RunBuilder(run, f"Speedo--{task_no}")
    urls = spec["urls"]
    for i, u in enumerate(urls):
        action = "navigate" if i == 0 else "click"
        b.add_step(action, BASE + u.lstrip('/'))
    b.finish(spec["answer"])
    return run


def noop_run(tmp_path: Path, task_no: int) -> Path:
    """Homepage only, empty answer, clean DB — must FAIL every verifier."""
    run = tmp_path / f"noop_{task_no}"
    run.mkdir(parents=True)
    b = RunBuilder(run, f"Speedo--{task_no}")
    b.add_step("navigate", BASE)
    b.finish("")
    return run


def shortcut_run(tmp_path: Path, task_no: int) -> Path:
    """Correct answer + correct DB delta but homepage-only navigation —
    a memory-recall shortcut must FAIL."""
    spec = SPECS[task_no]
    run = tmp_path / f"shortcut_{task_no}"
    run.mkdir(parents=True)
    b = RunBuilder(run, f"Speedo--{task_no}")
    b.add_step("navigate", BASE)
    b.finish(spec["answer"])
    return run


def wrong_answer_run(tmp_path: Path, task_no: int, wrong: str) -> Path:
    """Honest navigation + honest DB delta but a wrong final answer."""
    spec = SPECS[task_no]
    run = tmp_path / f"wrong_{task_no}"
    run.mkdir(parents=True)
    b = RunBuilder(run, f"Speedo--{task_no}")
    for i, u in enumerate(spec["urls"]):
        b.add_step("navigate" if i == 0 else "click", BASE + u)
    b.finish(wrong)
    return run


def state_mismatch_run(tmp_path: Path, task_no: int) -> Path:
    """Agent self-reports success but the DB is untouched (seed copy)."""
    spec = SPECS[task_no]
    run = tmp_path / f"mismatch_{task_no}"
    run.mkdir(parents=True)
    b = RunBuilder(run, f"Speedo--{task_no}")
    for i, u in enumerate(spec["urls"]):
        b.add_step("navigate" if i == 0 else "click", BASE + u)
    b.finish(spec["answer"])
    return run


def run_verifier(task_no: int, run_dir: Path, after_db: Path,
                 initial_db: Path | None = None) -> tuple[int, dict]:
    verifier = VERIFY_DIR / f"verify_{task_no}.py"
    cmd = [sys.executable, str(verifier), "--run_dir", str(run_dir),
           "--after_db", str(after_db)]
    cmd += ["--initial_db", str(initial_db if initial_db is not None else acquire_seed())]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(VERIFY_DIR))
    try:
        verdict = json.loads(r.stdout)
    except json.JSONDecodeError:
        verdict = {"task_id": f"Speedo--{task_no}", "pass": False,
                   "reason": f"unreadable output: {r.stdout[:200]} {r.stderr[:200]}"}
    return r.returncode, verdict


def mutate_after_db(tmp_path: Path, task_no: int, name: str = "after.db") -> Path:
    """Seed copy + the task's frozen honest delta (the expected after-DB)."""
    db = copy_db(tmp_path, name)
    exec_sql(db, SPECS[task_no]["sql"])
    return db
