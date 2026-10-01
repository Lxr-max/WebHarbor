#!/usr/bin/env python3
"""test_verifiers.py — adversarial contract tests for the fox_sports
verifier suite.

Guarantees (run with pytest):
  * each honest fixture (transcribed from the reviewer's two independent
    Playwright walkthrough rounds of the review container wh-fox-review,
    runs_round1/ + runs_round2/ — identical step counts and facts) PASSES
    its verify_<n>.py;
  * every adversarial negative FAILS (no false positives):
      - no-op trajectories (20) — homepage only, empty answer, clean DBs;
      - answer-only shortcuts — honest answer, navigation stripped;
      - wrong-answer trajectories — one ground-truth token mutated per task;
      - stale-DB trajectories — stateful tasks missing their writes;
      - rogue-write trajectories — an extra favorite on a task whose
        contract does not allow it;
      - super 6 score forgery — an entry whose stored score disagrees
        with its picks;
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
EV = Path("/data/zhaoyang-user-projects/websyn/wh-fox-sports-review-evidence")
FIXTURES = EV / "r2runs_round0"
TMP = EV / "verify_runs" / "_pytest_tmp_r2"
PY = sys.executable

TASK_IDS = [f"FOX Sports--{n}" for n in range(20)]
PORT = "46123"  # the review container's site port (40130 -> host 46123)


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
        s["params"] = {}
        if "screenshot_after" not in s:
            s["screenshot_after"] = s.get("screenshot_before", "step_000.png")
    traj["steps"] = steps
    traj["final_url"] = start
    p.write_text(json.dumps(traj, indent=2))


# --------------------------------------------------------------- honest pass --

@pytest.mark.parametrize("n", range(20))
def test_honest_fixture_passes(n):
    v = run_verifier(n, FIXTURES / f"task{n}")
    assert v["pass"], f"honest fixture FOX Sports--{n} must PASS: {v.get('reason')}"


@pytest.mark.parametrize("n", range(20))
def test_second_round_fixture_passes(n):
    v = run_verifier(n, EV / "r2runs_round1" / f"task{n}")
    assert v["pass"], f"round-2 fixture FOX Sports--{n} must PASS: {v.get('reason')}"


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
    d.text((40, 40), f"fox--{n} no-op homepage", fill=(240, 240, 240))
    im.save(shots / "step_000.png")
    im.save(shots / "step_001.png")
    traj = {
        "task": json.loads(
            (VERIFY.parent / "tasks.jsonl").read_text().splitlines()[n]
        )["ques"],
        "task_id": f"FOX Sports--{n}",
        "start_url": f"http://localhost:{PORT}/",
        "model": "noop", "max_steps": 80,
        "steps": [{"step": 0, "url": f"http://localhost:{PORT}/",
                   "title": "FOX Sports", "thought": "open home",
                   "action": "navigate", "params": {},
                   "observed_text": "home", "screenshot_before":
                   "step_000.png", "screenshot_after": "step_001.png",
                   "url_after": f"http://localhost:{PORT}/"}],
        "terminated": True, "termination_reason": "agent_done",
        "final_answer": "", "judge_rubric": "", "verifier_path": "",
    }
    (dst / "trajectory.json").write_text(json.dumps(traj, indent=2))
    return dst


@pytest.mark.parametrize("n", range(20))
def test_noop_fails(n):
    v = run_verifier(n, noop_fixture(n))
    assert not v["pass"], f"no-op FOX Sports--{n} must FAIL"


# ------------------------------------------------------- answer-only shortcut --

@pytest.mark.parametrize("n", range(20))
def test_answer_only_shortcut_fails(n):
    dst = clone(n, "shortcut")
    strip_nav(dst)
    v = run_verifier(n, dst)
    assert not v["pass"], f"answer-only shortcut FOX Sports--{n} must FAIL"


# ------------------------------------------------------------- wrong answers --

# Each mutation changes a character INSIDE a ground-truth token so the
# corresponding claim regex can no longer match (an appended suffix would
# still substring-match).
WRONG_ANSWERS = {
    0: ("Ethan Driskell", "Ethan Droskell"), 1: ("59216", "59217"),
    2: ("Darnell Washington", "Darnell Woshington"),
    3: ("Reliant Stadium", "Reliant Stadiun"), 4: ("Bryce Young", "Bryce Ynoug"),
    5: ("sporting boot", "sporting boat"), 6: ("Truist Park", "Truist Pork"),
    7: ("Jordan Hicks", "Jordan Hocks"), 8: ("Clemson", "Clamson"),
    9: ("Kenan Stadium", "Kenan Stadiun"),
    10: ("underdelivering", "underdelivesing"),
    11: ("Announcer", "Annoincer"), 12: ("Jahmyr Gibbs", "Jahmyr Gabbs"),
    13: ("Chicago Bears", "Chicago Baars"),
    14: ("Nissan Stadium", "Nissan Stadiun"),
    15: ("98-64", "97-64"), 16: ("Kyle Larson", "Kyle Larzon"),
    17: ("South Point 400", "South Point 401"), 18: ("Meatball Sub", "Meatball Seb"),
    19: ("Citizens Bank Park", "Citizens Bonk Park"),
}


@pytest.mark.parametrize("n", range(20))
def test_wrong_answer_fails(n):
    dst = clone(n, "wrong")
    old, new = WRONG_ANSWERS[n]
    traj = json.loads((dst / "trajectory.json").read_text())
    answer = traj["final_answer"]
    assert old in answer, f"fixture FOX Sports--{n} must contain {old!r}"
    mutate_answer(dst, answer.replace(old, new))
    v = run_verifier(n, dst)
    assert not v["pass"], f"wrong answer FOX Sports--{n} must FAIL"


# ------------------------------------------------------------------ stale DB --

@pytest.mark.parametrize("n", range(20))
def test_stale_db_fails(n):
    dst = clone(n, "stale")
    shutil.copyfile(dst / "initial.db", dst / "after.db")
    v = run_verifier(n, dst)
    assert not v["pass"], f"stale-DB FOX Sports--{n} must FAIL"


# --------------------------------------------------------------- rogue writes --

@pytest.mark.parametrize("n", range(20))
def test_rogue_write_fails(n):
    """An extra favorite the contract does not allow must FAIL."""
    dst = clone(n, "rogue")
    mutate_db(dst, "after.db",
              "INSERT INTO favorites (user_id, item_type, item_key, added_at) "
              "VALUES (1, 'team', 'oakland-athletics', '2026-09-30')")
    v = run_verifier(n, dst)
    assert not v["pass"], f"rogue-write FOX Sports--{n} must FAIL"


def test_super6_score_forgery_fails():
    """A stored score that disagrees with the saved picks must FAIL."""
    dst = clone(13, "forged")
    mutate_db(dst, "after.db",
              "UPDATE super6_entries SET score = 2 WHERE user_id = 1")
    v = run_verifier(13, dst)
    assert not v["pass"], "super-6 score forgery must FAIL"


def test_super6_wrong_picks_fails():
    """T14 requires the exact home/away pick pattern (Q3 home =
    tennessee-titans); the r1-style mis-pick (chicago-bears at Q3) or
    any swap must FAIL."""
    dst = clone(14, "swapped")
    mutate_db(dst, "after.db",
              "UPDATE super6_entries SET picks = 'green-bay-packers|"
              "miami-dolphins|chicago-bears|cincinnati-bengals|"
              "indianapolis-colts|houston-texans', score = 3 "
              "WHERE user_id = 4")
    v = run_verifier(14, dst)
    assert not v["pass"], "wrong super-6 picks must FAIL"


# --------------------------------------------------------------- tamper cases --

def test_wrong_task_id_fails():
    dst = clone(0, "taskid")
    set_traj(dst, task_id="FOX Sports--1")
    v = run_verifier(0, dst)
    assert not v["pass"]


def test_offsite_url_fails():
    dst = clone(0, "offsite")
    set_traj(dst, start_url="http://example.com:46123/")
    v = run_verifier(0, dst)
    assert not v["pass"]


def test_cross_port_fails():
    dst = clone(0, "crossport")
    traj = json.loads((dst / "trajectory.json").read_text())
    for s in traj["steps"]:
        for k in ("url", "url_before", "url_after"):
            if s.get(k):
                s[k] = s[k].replace(f":{PORT}/", ":40099/")
    # the navigation targets recorded in params stay on the honest port,
    # so the tampered origin contradicts the browser evidence
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
              "INSERT INTO favorites (user_id, item_type, item_key, added_at) "
              "VALUES (1, 'team', 'oakland-athletics', '2026-09-30')")
    shutil.copyfile(dst / "initial.db", dst / "after.db")
    v = run_verifier(0, dst)
    assert not v["pass"]


def test_broken_screenshot_fails():
    dst = clone(0, "badpng")
    traj = json.loads((dst / "trajectory.json").read_text())
    name = traj["steps"][-1]["screenshot_after"]
    (dst / "screenshots" / name).write_bytes(b"not a png")
    v = run_verifier(0, dst)
    assert not v["pass"]
