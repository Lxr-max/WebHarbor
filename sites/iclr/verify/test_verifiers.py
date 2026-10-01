#!/usr/bin/env python3
"""test_verifiers.py — adversarial contract tests for the iclr verifier suite.

Guarantees (run with pytest):
  * each honest fixture (transcribed from the reviewer's real Playwright
    walkthroughs of the review container wh-iclr-review, runs_round1/) PASSES
    its verify_<n>.py;
  * every adversarial negative FAILS (no false positives):
      - no-op trajectories (20) — homepage only, empty answer, clean DBs;
      - answer-only shortcuts — honest answer, navigation stripped;
      - wrong-answer trajectories — one ground-truth fact mutated per task;
      - stale-DB trajectories — stateful tasks missing their writes;
      - read-only violations — rogue rows on read-only tasks;
      - tampered packages — wrong task_id / off-site URL / cross-port /
        not-terminated / empty answer / pre-mutated seed / broken screenshot.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

VERIFY = Path(__file__).resolve().parent
EV = Path("/data/zhaoyang-user-projects/websyn/wh-iclr-rereview-evidence")
FIXTURES = EV / "runs_round1"
TMP = EV / "verify_runs" / "_pytest_tmp"
PY = sys.executable

TASK_IDS = [f"iclr--{n}" for n in range(20)]
READ_ONLY = [n for n in range(20) if n not in
             (0, 1, 2, 3, 4, 5, 7, 9, 10, 11, 14, 15, 17, 18, 19)]
STATEFUL = [n for n in range(20) if n not in READ_ONLY]


def run_verifier(n: int, run_dir: Path):
    proc = subprocess.run(
        [PY, str(VERIFY / f"verify_{n}.py"), "--run_dir", str(run_dir)],
        capture_output=True, text=True, timeout=180)
    try:
        verdict = json.loads(proc.stdout)
    except json.JSONDecodeError:
        verdict = {"pass": False,
                   "reason": (proc.stdout[-300:] or proc.stderr[-300:])}
    return verdict


def clone(n: int, tag: str) -> Path:
    dst = TMP / f"{n}_{tag}"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(FIXTURES / f"task{n}", dst)
    return dst


def set_traj(run_dir: Path, **changes):
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    traj.update(changes)
    p.write_text(json.dumps(traj, indent=2))


def mutate_answer(run_dir: Path, new_answer: str):
    set_traj(run_dir, final_answer=new_answer)


def mutate_db(run_dir: Path, which: str, sql: str):
    db = sqlite3.connect(run_dir / which)
    db.execute(sql)
    db.commit()
    db.close()


def strip_nav(run_dir: Path):
    """Reduce the trajectory to the bare start page (no tool navigation)."""
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    start = traj["start_url"]
    steps = [s for s in traj["steps"] if s.get("url") == start][:1]
    for s in steps:
        s["url_after"] = start
        if "screenshot_after" not in s:
            s["screenshot_after"] = s.get("screenshot_before", "step_000.png")
    traj["steps"] = steps
    traj["final_url"] = start
    p.write_text(json.dumps(traj, indent=2))


# --------------------------------------------------------------- honest pass --

@pytest.mark.parametrize("n", range(20))
def test_honest_fixture_passes(n):
    v = run_verifier(n, FIXTURES / f"task{n}")
    assert v["pass"], f"honest fixture iclr--{n} must PASS: {v.get('reason')}"


# ------------------------------------------------------------------- no-op --

def noop_fixture(n: int) -> Path:
    dst = clone(n, "noop")
    shots = dst / "screenshots"
    shutil.rmtree(shots)
    shots.mkdir()
    # a single homepage screenshot, valid but boring: draw text on gray
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (1440, 960), (120, 120, 130))
    d = ImageDraw.Draw(im)
    d.text((40, 40), f"iclr--{n} no-op homepage", fill=(240, 240, 240))
    im.save(shots / "step_000.png")
    im.save(shots / "step_001.png")
    traj = {
        "task": json.loads(
            (VERIFY.parent / "tasks.jsonl").read_text().splitlines()[n]
        )["ques"],
        "task_id": f"iclr--{n}",
        "start_url": f"http://localhost:40133/",
        "model": "noop", "max_steps": 80,
        "steps": [{"step": 0, "url": "http://localhost:40133/",
                   "title": "ICLR 2026", "thought": "open home",
                   "action": "navigate", "params": {},
                   "observed_text": "home", "screenshot_before":
                   "step_000.png", "screenshot_after": "step_001.png",
                   "url_after": "http://localhost:40133/"}],
        "terminated": True, "termination_reason": "agent_done",
        "final_answer": "", "judge_rubric": "", "verifier_path": "",
    }
    (dst / "trajectory.json").write_text(json.dumps(traj, indent=2))
    return dst


@pytest.mark.parametrize("n", range(20))
def test_noop_fails(n):
    v = run_verifier(n, noop_fixture(n))
    assert not v["pass"], f"no-op iclr--{n} must FAIL"


# ------------------------------------------------------- answer-only shortcut --

@pytest.mark.parametrize("n", READ_ONLY)
def test_answer_only_shortcut_fails(n):
    dst = clone(n, "shortcut")
    strip_nav(dst)
    v = run_verifier(n, dst)
    assert not v["pass"], f"answer-only shortcut iclr--{n} must FAIL"


# ------------------------------------------------------------- wrong answers --

# Each mutation changes a character INSIDE a ground-truth token so the
# corresponding claim regex can no longer match (an appended suffix would
# still substring-match).
WRONG_ANSWERS = {
    0: ("406", "407"), 1: ("495", "496"), 2: ("432", "433"),
    3: ("Amphitheater", "Bmphitheater"), 4: ("18 schedule items",
                                              "19 schedule items"),
    5: ("Katherine Bouman", "Katherine Boumon"), 6: ("Amazon", "Amazoh"),
    7: ("Carl Vondrick", "Carl Xondrick"), 8: ("Gautam Kamath",
                                                "Gautam Xamath"),
    9: ("$100", "$101"), 10: ("Poster Session 4 Pavilion 4",
                              "Poster Session 5 Pavilion 4"),
    11: ("7am-5:30pm", "7am-5:31pm"), 12: ("Double Diamond",
                                           "Double Xiamond"),
    13: ("Double Diamond", "Double Xiamond"), 14: ("Celine Lee",
                                                    "Celine Xee"),
    15: ("Jinan University", "Jinan Xniversity"), 16: ("P3-#1505",
                                                        "P3-#1506"),
    17: ("Marin: Open Development of Frontier AI",
          "Marin: Open Development of Xrontier AI"),
    18: ("$50", "$51"), 19: ("P4-#4003", "P4-#4004"),
}


@pytest.mark.parametrize("n", range(20))
def test_wrong_answer_fails(n):
    dst = clone(n, "wrong")
    old, new = WRONG_ANSWERS[n]
    traj = json.loads((dst / "trajectory.json").read_text())
    answer = traj["final_answer"]
    assert old in answer, f"fixture iclr--{n} must contain {old!r}"
    mutate_answer(dst, answer.replace(old, new))
    v = run_verifier(n, dst)
    assert not v["pass"], f"wrong answer iclr--{n} must FAIL"


# ------------------------------------------------------------------ stale DB --

@pytest.mark.parametrize("n", STATEFUL)
def test_stale_db_fails(n):
    dst = clone(n, "stale")
    shutil.copyfile(dst / "initial.db", dst / "after.db")
    v = run_verifier(n, dst)
    assert not v["pass"], f"stale-DB iclr--{n} must FAIL"


# --------------------------------------------------------- read-only violated --

@pytest.mark.parametrize("n", READ_ONLY)
def test_read_only_violation_fails(n):
    dst = clone(n, "rogue")
    mutate_db(dst, "after.db",
              "INSERT INTO bookmarks (user_id, paper_id, added_at) "
              "VALUES (1, 10006831, '2026-09-30')")
    v = run_verifier(n, dst)
    assert not v["pass"], f"read-only violation iclr--{n} must FAIL"


# --------------------------------------------------------------- tamper cases --

def test_wrong_task_id_fails():
    dst = clone(0, "taskid")
    set_traj(dst, task_id="iclr--1")
    v = run_verifier(0, dst)
    assert not v["pass"]


def test_offsite_url_fails():
    dst = clone(0, "offsite")
    set_traj(dst, start_url="http://example.com:40133/")
    v = run_verifier(0, dst)
    assert not v["pass"]


def test_cross_port_fails():
    dst = clone(0, "crossport")
    traj = json.loads((dst / "trajectory.json").read_text())
    for s in traj["steps"]:
        for k in ("url", "url_before", "url_after"):
            if s.get(k):
                s[k] = s[k].replace(":40133/", ":40099/")
    set_traj(dst, start_url="http://localhost:40099/", steps=traj["steps"])
    v = run_verifier(0, dst)
    assert not v["pass"]


def test_not_terminated_fails():
    dst = clone(0, "unterminated")
    set_traj(dst, terminated=False, termination_reason=None)
    v = run_verifier(0, dst)
    assert not v["pass"]


def test_empty_answer_fails():
    dst = clone(0, "empty")
    set_traj(dst, final_answer="")
    v = run_verifier(0, dst)
    assert not v["pass"]


def test_premutated_seed_fails():
    dst = clone(0, "preseed")
    mutate_db(dst, "initial.db",
              "INSERT INTO bookmarks (user_id, paper_id, added_at) "
              "VALUES (1, 10006831, '2026-09-30')")
    shutil.copyfile(dst / "initial.db", dst / "after.db")
    v = run_verifier(0, dst)
    assert not v["pass"]


def test_broken_screenshot_fails():
    dst = clone(0, "badpng")
    # corrupt a screenshot the trajectory actually references
    traj = json.loads((dst / "trajectory.json").read_text())
    name = traj["steps"][-1]["screenshot_after"]
    (dst / "screenshots" / name).write_bytes(b"not a png")
    v = run_verifier(0, dst)
    assert not v["pass"]
