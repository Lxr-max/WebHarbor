"""Shared fixtures for the ryanair verifier tests.

Snapshots are copies of the real deterministic seed (instance_seed/ryanair.db,
built at image time with PYTHONHASHSEED=0) with the per-task stateful mutations
applied through sqlite, and trajectories are written in the agent_demo/agent.py
shape from the frozen SPECS (extracted from the reviewer's honest live runs).
No LLM.

The seed DB resolves from the review container (wh-ry-review); the
RYANAIR_TEST_SEED_DB env var overrides the location. Run with plain
python3 + pytest:

    python3 -m pytest sites/ryanair/verify/tests -q
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

BASE = "http://localhost:40098"

VERIFY_DIR = Path(__file__).resolve().parents[1]
SITE_DIR = VERIFY_DIR.parent
CONTAINER = os.environ.get("WH_CONTAINER", "wh-ry-review")
CACHE = Path(os.environ.get("RYANAIR_TEST_SEED_DB") or
             str(SITE_DIR / "instance_seed/ryanair.db"))
TASKS_FILE = SITE_DIR / "tasks.jsonl"
PASSWORD = "TestPass123!"


def acquire_seed() -> Path:
    if CACHE.is_file():
        return CACHE
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["docker", "cp", f"{CONTAINER}:/opt/WebSyn/ryanair/"
                       f"instance_seed/ryanair.db", str(CACHE)],
                       capture_output=True, text=True)
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

    def __init__(self, root: Path, task_id: str, start_path: str = "/gb/en"):
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
            "title": "Ryanair",
            "thought": thought or f"fixture step on {path}",
            "action": action,
            "params": params or {},
            "observed_text": "fixture",
            "observed_text_before": "fixture",
            "screenshot_before": before,
            "screenshot_after": after,
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
            "success_self_report": "done",
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
    # after.db inside the run dir is picked up automatically
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(VERIFY_DIR))
    try:
        verdict = json.loads(r.stdout)
    except json.JSONDecodeError:
        raise AssertionError(f"verifier {task_no} crashed: {r.stderr[-400:]}")
    assert verdict["pass"] is expect_pass, (
        f"task {task_no}: expected pass={expect_pass}, got pass={verdict['pass']}, "
        f"reason={verdict.get('reason')}")
    return verdict


# ------------------------------------------------------------------ fixture builders
# login + profile input steps the account tasks require (the honest runs typed
# these into the real forms; the fixture trajectories must show them too)
INPUT_STEPS = {
    8: [("fill", "input[name='email']", "alice.j@test.com"),
        ("fill", "input[name='password']", "TestPass123!"),
        ("fill", "input[name='phone']", "+44 7700 900777"),
        ("fill", "input[name='address1']", "2 Test Lane"),
        ("fill", "input[name='cardNumber']", "5555 5555 5555 4444")],
    10: [("fill", "input[name='email']", "david.k@test.com"),
         ("fill", "input[name='password']", "TestPass123!"),
         ("fill", "input[name='phone']", "+44 7700 900456")],
    11: [("fill", "input[name='email']", "bob.c@test.com"),
         ("fill", "input[name='password']", "TestPass123!")],
    18: [("fill", "input[name='email']", "carol.d@test.com"),
         ("fill", "input[name='password']", "TestPass123!"),
         ("fill", "input[name='phone']", "+353 85 012 9999")],
}

# action URLs the honest runs followed by link click (the redirect target hides
# them from the URL list, so the fixtures state them explicitly)
EXTRA_URLS = {8: ["/gb/en/myryanair/logout"]}


def honest_run(tmp: Path, task_no: int) -> Path:
    """Synthetic unit fixture derived from the final browser replay."""
    spec = json.loads((Path(__file__).parent / 'reviewed_fixtures.json').read_text())[str(task_no)]
    root = tmp / f'honest_{task_no:02d}'
    (root / 'screenshots').mkdir(parents=True)
    (root / 'screenshots/step_000.png').write_bytes(PNG)
    after = copy_db(root, 'after.db')
    with sqlite3.connect(after) as con:
        for table, rows in spec['tables_after'].items():
            con.execute(f'DELETE FROM "{table}"')
            for row in rows:
                columns = ','.join('"'+k+'"' for k in row)
                placeholders = ','.join('?' for _ in row)
                con.execute(f'INSERT INTO "{table}" ({columns}) VALUES ({placeholders})', list(row.values()))
    for step in spec['steps']:
        step.update(screenshot_before='step_000.png', screenshot_after='step_000.png')
    trajectory = dict(task_id=f'Ryanair--{task_no}', start_url=spec['start_url'],
                      final_url=spec['final_url'], final_answer=spec['answer'], steps=spec['steps'],
                      terminated=True, termination_reason='agent_done')
    (root / 'trajectory.json').write_text(json.dumps(trajectory))
    return root


def noop_run(tmp: Path, task_no: int) -> Path:
    """FAIL fixture: homepage only, empty answer, clean DB."""
    root = tmp / f"noop_{task_no:02d}"
    root.mkdir(parents=True)
    b = RunBuilder(root, f"Ryanair--{task_no}")
    b.step("/gb/en", action="goto", thought="opened the homepage")
    copy_db(root, "after.db")
    return b.build("", final_path="/gb/en")


def shortcut_run(tmp: Path, task_no: int) -> Path:
    root = honest_run(tmp, task_no)
    p = root / 'trajectory.json'; t = json.loads(p.read_text())
    t['steps'] = [dict(t['steps'][0], action='goto', url=t['start_url'], url_before=t['start_url'], url_after=t['start_url'])]
    t['final_url'] = t['start_url']; p.write_text(json.dumps(t))
    return root


def wrong_answer_run(tmp: Path, task_no: int, answer: str) -> Path:
    root = honest_run(tmp, task_no)
    p = root / 'trajectory.json'; t = json.loads(p.read_text()); t['final_answer'] = answer
    p.write_text(json.dumps(t)); return root


def state_mismatch_run(tmp: Path, task_no: int) -> Path:
    root = honest_run(tmp, task_no)
    shutil.copyfile(acquire_seed(), root / 'after.db')
    return root
