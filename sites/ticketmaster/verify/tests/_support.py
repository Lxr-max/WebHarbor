"""Shared fixtures for the ticketmaster verifier tests (review track).

Snapshots are copies of the deterministic seed (instance_seed/ticketmaster.db,
built in-image with PYTHONHASHSEED=0, md5 b03a154d…) with the per-task
stateful mutations from fixtures_data.MUTATIONS applied through sqlite.
Trajectories are written in the agent_demo/agent.py shape from the frozen
SPECS (extracted from the reviewer's honest live walks). No LLM.

The seed DB resolves from the review container (wh-tm-rereview); the
TICKETMASTER_TEST_SEED_DB env var overrides the location. Run with pytest:

    python3 -m pytest sites/ticketmaster/verify/tests -q
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

from fixtures_data import BASE, SPECS, MUTATIONS, WRONG_ANSWERS  # noqa: E402

VERIFY_DIR = Path(__file__).resolve().parents[1]
SITE_DIR = VERIFY_DIR.parent
CONTAINER = os.environ.get("WH_CONTAINER", "wh-tm-rereview")
CACHE = Path(os.environ.get("TICKETMASTER_TEST_SEED_DB")
             or str(SITE_DIR / "instance_seed" / "ticketmaster.db"))
TASKS_FILE = SITE_DIR / "tasks.jsonl"


def acquire_seed() -> Path:
    if CACHE.is_file():
        return CACHE
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    local = Path(__file__).resolve().parents[2] / "instance_seed" / "ticketmaster.db"
    if local.is_file():  # running inside the container tree
        shutil.copyfile(local, CACHE)
        return CACHE
    r = subprocess.run(["docker", "cp",
                        f"{CONTAINER}:/opt/WebSyn/ticketmaster/instance_seed/ticketmaster.db",
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
                 shot: bytes | None = None) -> None:
        name = f"step_{len(self.steps) + 1:03d}.png"
        (self.shots_dir / name).write_bytes(PNG if shot is None else shot)
        self.steps.append({
            "step": len(self.steps),
            "url": BASE + self.start_path if not self.steps else self.steps[-1]["url_after"],
            "title": "Ticketmaster",
            "thought": f"{action} {url_after}",
            "action": action,
            "params": params or {},
            "observed_text": f"page text for {url_after}",
            "screenshot_before": self.steps[-1]["screenshot_after"] if self.steps else name,
            "screenshot_after": name,
            "url_after": url_after,
        })

    def add_input(self, text: str) -> None:
        """A typed-input step (fill action) — stays on the current page."""
        name = f"step_{len(self.steps) + 1:03d}.png"
        (self.shots_dir / name).write_bytes(PNG)
        cur = (self.steps[-1]["url_after"] if self.steps
               else BASE + self.start_path)
        self.steps.append({
            "step": len(self.steps),
            "url": cur,
            "title": "Ticketmaster",
            "thought": f"type {text!r}",
            "action": "fill",
            "params": {"text": text},
            "observed_text": "page text",
            "screenshot_before": self.steps[-1]["screenshot_after"] if self.steps else name,
            "screenshot_after": name,
            "url_after": cur,
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
            "max_steps": 100,
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


# ------------------------------------------------------------------ db helpers
def copy_db(tmp_path: Path, name: str = "after.db") -> Path:
    dest = tmp_path / name
    shutil.copyfile(acquire_seed(), dest)
    return dest


def exec_sql(db_path: Path, statements: list[str]) -> None:
    db = sqlite3.connect(db_path)
    for stmt in statements:
        db.execute(stmt)
    db.commit()
    db.close()


# ------------------------------------------------------------------ run flavours
def _task_no(task_id: str) -> int:
    return int(task_id.split("--")[1])


def build_spec_traj(b: RunBuilder, spec: dict, answer: str,
                    terminated: bool = True, reason: str = "agent_done") -> dict:
    """Navigate spec['urls'], typing spec['inputs'] = [(url_index, text), …]
    right after the matching navigation. If an input lands on the final URL,
    the page is re-navigated so finish() puts 'done' on a navigate step."""
    pending = {}
    for idx, text in spec.get("inputs", ()):
        pending.setdefault(idx, []).append(text)
    urls = spec["urls"]
    n = len(urls)
    for i, u in enumerate(urls):
        b.add_step("navigate", BASE.rstrip("/") + u if u.startswith("/") else u)
        texts = pending.get(i, ())
        for text in texts:
            b.add_input(text)
        if i == n - 1 and texts:
            b.add_step("navigate", BASE.rstrip("/") + urls[-1] if urls[-1].startswith("/") else urls[-1])
    return b.finish(answer, terminated=terminated, reason=reason)


def honest_run(tmp_path: Path, task_no: int) -> Path:
    """Honest trajectory + exact stateful delta (when the task is stateful)."""
    root = tmp_path / f"honest_{task_no}"
    root.mkdir(parents=True)
    tid = f"Ticketmaster--{task_no}"
    spec = SPECS[task_no]
    b = RunBuilder(root, tid)
    build_spec_traj(b, spec, spec["answer"])
    after = copy_db(root, "after.db")
    if task_no in MUTATIONS:
        exec_sql(after, MUTATIONS[task_no])
    initial = copy_db(root, "initial.db")
    return root


def noop_run(tmp_path: Path, task_no: int) -> Path:
    """Homepage only, empty answer, clean DB — must FAIL."""
    root = tmp_path / f"noop_{task_no}"
    root.mkdir(parents=True)
    tid = f"Ticketmaster--{task_no}"
    b = RunBuilder(root, tid)
    b.add_step("observe", BASE + "/")
    b.finish("I could not complete this task.")
    copy_db(root, "after.db")
    copy_db(root, "initial.db")
    return root


def shortcut_run(tmp_path: Path, task_no: int) -> Path:
    """Correct answer + correct delta but homepage-only navigation — FAIL."""
    root = tmp_path / f"shortcut_{task_no}"
    root.mkdir(parents=True)
    tid = f"Ticketmaster--{task_no}"
    b = RunBuilder(root, tid)
    b.add_step("observe", BASE + "/")
    b.finish(SPECS[task_no]["answer"])
    after = copy_db(root, "after.db")
    if task_no in MUTATIONS:
        exec_sql(after, MUTATIONS[task_no])
    copy_db(root, "initial.db")
    return root


def wrong_answer_run(tmp_path: Path, task_no: int, wrong: str) -> Path:
    """Honest navigation + honest delta but a wrong answer — FAIL."""
    root = tmp_path / f"wrong_{task_no}"
    root.mkdir(parents=True)
    tid = f"Ticketmaster--{task_no}"
    spec = SPECS[task_no]
    b = RunBuilder(root, tid)
    build_spec_traj(b, spec, wrong)
    after = copy_db(root, "after.db")
    if task_no in MUTATIONS:
        exec_sql(after, MUTATIONS[task_no])
    copy_db(root, "initial.db")
    return root


def state_mismatch_run(tmp_path: Path, task_no: int) -> Path:
    """Success answer + honest navigation but NO db delta — FAIL (stateful)."""
    root = tmp_path / f"mismatch_{task_no}"
    root.mkdir(parents=True)
    tid = f"Ticketmaster--{task_no}"
    spec = SPECS[task_no]
    b = RunBuilder(root, tid)
    build_spec_traj(b, spec, spec["answer"])
    copy_db(root, "after.db")
    copy_db(root, "initial.db")
    return root


def read_only_mutation_run(tmp_path: Path, task_no: int) -> Path:
    """Honest read-only navigation + answer but a MUTATED after-DB — FAIL."""
    root = tmp_path / f"romut_{task_no}"
    root.mkdir(parents=True)
    tid = f"Ticketmaster--{task_no}"
    spec = SPECS[task_no]
    b = RunBuilder(root, tid)
    build_spec_traj(b, spec, spec["answer"])
    after = copy_db(root, "after.db")
    exec_sql(after, ["UPDATE ticket_listings SET qty_available = qty_available - 1 "
                     "WHERE id = 1"])
    copy_db(root, "initial.db")
    return root


def run_verifier(task_no: int, run_dir: Path, expect_pass: bool) -> dict:
    """Run verify_<task_no>.py against run_dir; assert the expected outcome."""
    mod_path = VERIFY_DIR / f"verify_{task_no}.py"
    proc = subprocess.run(
        [sys.executable, str(mod_path), "--run_dir", str(run_dir)],
        capture_output=True, text=True, cwd=str(VERIFY_DIR))
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise AssertionError(f"verifier did not emit JSON:\n{proc.stdout[-800:]}\n"
                            f"{proc.stderr[-800:]}")
    assert result["pass"] is expect_pass, (
        f"expected pass={expect_pass} for task {task_no}, got:\n"
        f"{json.dumps(result, indent=1)[:1200]}")
    return result
