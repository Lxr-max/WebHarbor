"""Shared fixtures for the cars_com verifier tests.

Snapshots are copies of the real deterministic seed (instance_seed/cars_com.db,
built at image time with PYTHONHASHSEED=0) with the per-task stateful mutations
applied through sqlite, and trajectories are written in the agent_demo/agent.py
shape from the frozen SPECS (extracted from the reviewer's honest live runs).
No LLM.

The seed DB resolves from (in order): the CARS_COM_TEST_SEED_DB env var,
sites/cars_com/instance_seed/cars_com.db, or a docker cp from the review
container. Run with plain python3 + pytest:

    python3 -m pytest sites/cars_com/verify/tests -q
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
from typing import Any

BASE = "http://localhost:49118"

VERIFY_DIR = Path(__file__).resolve().parents[1]
SITE_DIR = VERIFY_DIR.parent
CONTAINER = os.environ.get("WH_CONTAINER", "wh-cars-com-review-r1")
CACHE = Path(os.environ.get("CARS_COM_TEST_SEED_DB")
             or str(SITE_DIR / "instance_seed" / "cars_com.db"))
TASKS_FILE = SITE_DIR / "tasks.jsonl"
SPECS = json.loads((Path(__file__).parent / "reviewed_fixtures.json").read_text())
STATEFUL = {1, 4, 5, 6, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18}
READ_ONLY = {0, 2, 3, 7, 8}
ALL = sorted(STATEFUL | READ_ONLY)


def acquire_seed() -> Path:
    if CACHE.is_file():
        return CACHE
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["docker", "cp",
                        f"{CONTAINER}:/opt/WebSyn/cars_com/instance_seed/cars_com.db",
                        str(CACHE)], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"cannot acquire the seed DB (docker cp failed): "
                           f"{r.stderr[:200]}")
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

    ihdr = width.to_bytes(4, "big") + height.to_bytes(4, "big") \
        + b"\x08\x02\x00\x00\x00"
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
        (self.shots_dir / "step_000.png").write_bytes(PNG)
        self.steps: list[dict[str, Any]] = []
        self.task_id = task_id
        self.start_url = BASE + start_path
        self.final_answer = ""
        self.final_path = start_path

    def step(self, path: str, action: str = "click", params: dict | None = None,
             url: str | None = None, thought: str = ""):
        i = len(self.steps)
        before = f"step_{i:03d}.png"
        after = f"step_{i + 1:03d}.png"
        (self.shots_dir / after).write_bytes(PNG)
        self.steps.append({
            "step": i,
            "url": url if url is not None else (BASE + path if path.startswith("/") else path),
            "title": "Cars.com",
            "thought": thought or f"fixture step on {path}",
            "action": action,
            "params": params or {},
            "observed_text": "fixture",
            "observed_text_before": "fixture",
            "screenshot_before": before,
            "screenshot_after": after,
            "url_after": BASE + path if path.startswith("/") else path,
        })
        return self.steps[-1]

    def build(self, answer: str, final_path: str | None = None) -> Path:
        traj = {
            "task": task_ques(self.task_id),
            "task_id": self.task_id,
            "start_url": self.start_url,
            "terminated": True,
            "termination_reason": "agent_done",
            "final_answer": answer,
            "success_self_report": True,
            "final_url": BASE + (final_path or self.final_path),
            "steps": self.steps,
        }
        (self.root / "trajectory.json").write_text(json.dumps(traj, indent=1),
                                                    encoding="utf-8")
        return self.root


# ------------------------------------------------------------------ db plumbing
def copy_db(tmp: Path, name: str = "after.db") -> Path:
    dest = tmp / name
    shutil.copy(acquire_seed(), dest)
    return dest


def exec_sql(db_path: Path, statements: list[str]) -> None:
    con = sqlite3.connect(str(db_path))
    try:
        for stmt in statements:
            con.execute(stmt)
        con.commit()
    finally:
        con.close()


def run_verifier(task_no: int, run_dir: Path, expect_pass: bool) -> dict:
    """Run verify_<task_no>.py against run_dir; assert the verdict."""
    script = VERIFY_DIR / f"verify_{task_no}.py"
    cmd = [sys.executable, str(script), "--run_dir", str(run_dir),
           "--initial_db", str(acquire_seed())]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(VERIFY_DIR))
    try:
        verdict = json.loads(r.stdout)
    except json.JSONDecodeError:
        raise AssertionError(f"verifier {task_no} crashed: {r.stderr[-400:]}")
    assert verdict["pass"] is expect_pass, (
        f"task {task_no}: expected pass={expect_pass}, got pass={verdict['pass']}, "
        f"reason={verdict.get('reason')}, evidence={verdict.get('evidence', [])[:6]}")
    return verdict


# ------------------------------------------------------------------ fixture builders
def honest_run(tmp: Path, task_no: int) -> Path:
    """The reviewer's frozen honest live run: full navigation, correct answer,
    real after-DB delta."""
    spec = SPECS[str(task_no)]
    root = tmp / f"honest_{task_no:02d}"
    root.mkdir(parents=True)
    builder = RunBuilder(root, f"Cars.com--{task_no}")
    for st in spec["steps"]:
        builder.step(st["path"], st["action"], st.get("params"),
                     url=st.get("url") or (BASE + st["path"]), thought=st.get("thought", ""))
    builder.build(spec["final_answer"], final_path=spec["final_path"])
    after = copy_db(root, "after.db")
    exec_sql(after, spec.get("db_sql", []))
    return root


def noop_run(tmp: Path, task_no: int, answer: str = "") -> Path:
    """The agent opens the homepage, does nothing, answers nothing; clean DB."""
    root = tmp / f"noop_{task_no:02d}"
    root.mkdir(parents=True)
    builder = RunBuilder(root, f"Cars.com--{task_no}")
    builder.step("/", "navigate")
    builder.build(answer, final_path="/")
    copy_db(root, "after.db")
    return root


def shortcut_run(tmp: Path, task_no: int) -> Path:
    """Correct answer + correct DB delta, but homepage-only navigation:
    a knowledge/recall shortcut must FAIL."""
    spec = SPECS[str(task_no)]
    root = tmp / f"shortcut_{task_no:02d}"
    root.mkdir(parents=True)
    builder = RunBuilder(root, f"Cars.com--{task_no}")
    builder.step("/", "navigate")
    builder.build(spec["final_answer"], final_path="/")
    after = copy_db(root, "after.db")
    exec_sql(after, spec.get("db_sql", []))
    return root


def wrong_answer_run(tmp: Path, task_no: int, answer: str) -> Path:
    """Honest navigation, plausible but wrong answer; must FAIL."""
    spec = SPECS[str(task_no)]
    root = tmp / f"wrong_{task_no:02d}"
    root.mkdir(parents=True)
    builder = RunBuilder(root, f"Cars.com--{task_no}")
    for st in spec["steps"]:
        builder.step(st["path"], st["action"], st.get("params"),
                     url=st.get("url") or (BASE + st["path"]), thought=st.get("thought", ""))
    builder.build(answer, final_path=spec["final_path"])
    after = copy_db(root, "after.db")
    exec_sql(after, spec.get("db_sql", []))
    return root


def state_mismatch_run(tmp: Path, task_no: int) -> Path:
    """Correct answer + honest navigation, but the DB is unchanged:
    a self-reported success without the state change must FAIL."""
    spec = SPECS[str(task_no)]
    root = tmp / f"mismatch_{task_no:02d}"
    root.mkdir(parents=True)
    builder = RunBuilder(root, f"Cars.com--{task_no}")
    for st in spec["steps"]:
        builder.step(st["path"], st["action"], st.get("params"),
                     url=st.get("url") or (BASE + st["path"]), thought=st.get("thought", ""))
    builder.build(spec["final_answer"], final_path=spec["final_path"])
    copy_db(root, "after.db")
    return root


def readonly_mutation_run(tmp: Path, task_no: int) -> Path:
    """Honest read-only run, but the after-DB carries a rogue write: FAIL."""
    spec = SPECS[str(task_no)]
    root = tmp / f"rogue_{task_no:02d}"
    root.mkdir(parents=True)
    builder = RunBuilder(root, f"Cars.com--{task_no}")
    for st in spec["steps"]:
        builder.step(st["path"], st["action"], st.get("params"),
                     url=st.get("url") or (BASE + st["path"]), thought=st.get("thought", ""))
    builder.build(spec["final_answer"], final_path=spec["final_path"])
    after = copy_db(root, "after.db")
    exec_sql(after, ["INSERT INTO saved_cars (user_id, listing_id, saved_at) "
                     "VALUES (1, '353e2646-07ab-4cf3-9811-eb919af85867', '2026-10-13')"])
    return root


def offsite_run(tmp: Path, task_no: int) -> Path:
    """Honest answer, but every URL points off-site: FAIL closed."""
    spec = SPECS[str(task_no)]
    root = tmp / f"offsite_{task_no:02d}"
    root.mkdir(parents=True)
    builder = RunBuilder(root, f"Cars.com--{task_no}")
    for st in spec["steps"]:
        builder.step(st["path"], st["action"], st.get("params"),
                     url="https://example.com" + st["path"],
                     thought=st.get("thought", ""))
    traj = {
        "task": task_ques(builder.task_id),
        "task_id": builder.task_id,
        "start_url": "https://example.com/",
        "terminated": True,
        "termination_reason": "agent_done",
        "final_answer": spec["final_answer"],
        "success_self_report": True,
        "final_url": "https://example.com" + spec["final_path"],
        "steps": builder.steps,
    }
    (root / "trajectory.json").write_text(json.dumps(traj, indent=1),
                                          encoding="utf-8")
    after = copy_db(root, "after.db")
    exec_sql(after, spec.get("db_sql", []))
    return root


def tampered_task_id_run(tmp: Path, task_no: int) -> Path:
    """Honest run whose trajectory carries a different task_id: FAIL."""
    spec = SPECS[str(task_no)]
    root = tmp / f"tampered_{task_no:02d}"
    root.mkdir(parents=True)
    builder = RunBuilder(root, f"Cars.com--{task_no}")
    for st in spec["steps"]:
        builder.step(st["path"], st["action"], st.get("params"),
                     url=st.get("url") or (BASE + st["path"]), thought=st.get("thought", ""))
    root2 = builder.build(spec["final_answer"], final_path=spec["final_path"])
    traj = json.loads((root2 / "trajectory.json").read_text())
    traj["task_id"] = f"Cars.com--{(task_no + 1) % 19}"
    (root2 / "trajectory.json").write_text(json.dumps(traj, indent=1))
    after = copy_db(root, "after.db")
    exec_sql(after, spec.get("db_sql", []))
    return root


def noop_with_pasted_answer_run(tmp: Path, task_no: int) -> Path:
    """No-op navigation (homepage only) with the honest answer pasted in and
    the honest DB delta applied: the shortcut must still FAIL."""
    return shortcut_run(tmp, task_no)
