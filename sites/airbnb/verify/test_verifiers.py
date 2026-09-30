#!/usr/bin/env python3
"""test_verifiers.py — adversarial contract tests for the airbnb verifier suite.

Guarantees (run with pytest):
  * each honest fixture PASSES its verify_<n>.py — the fixtures are the
    REVIEWER's independent real Playwright rounds (T10 re-walked on the
    reviewer's r3 container for the 3-guests depth re-anchor, the other
    19 carried over from the reviewer's r2 rounds; fresh reset + fresh
    context per task; every review blocker B1-B4/H1-H3 and the r2
    residuals are fixed, so no intended-path substitutes are needed),
    seed sha256 recorded in verify_lib.py;
  * every adversarial negative FAILS (zero false positives):
      - no-op trajectories (20),
      - answer-only shortcuts with no navigation (20),
      - wrong-answer trajectories (20, fabricated per question point),
      - stale-DB trajectories (booking removed / wishlist save missing),
      - unexpected-writes trajectories (read-only tasks with a stray row),
      - tampered packages (wrong task_id / off-site URL / cross-port /
        not-terminated / empty answer / bad PNG / pre-mutated seed),
      - task-confusion (verifier N run against fixture M).
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
EV = Path("/data/zhaoyang-user-projects/websyn/wh-airbnb-review-evidence/r3")
REAL = EV / "verify_fixture_set"  # the reviewer's independent Playwright rounds:
                            # T10 re-walked on wh-airbnb-r3review for the
                            # 3-guests depth re-anchor (two rounds, 15/15);
                            # the other 19 fixtures carry over from the
                            # reviewer's r2 rounds (the r3 code changes are
                            # render-layer only; a 5-task regression sample
                            # re-walked on the r3 container confirmed identical
                            # behaviour, and all 20 verifiers pass)
INTENDED = EV / "intended_runs"  # reserved: empty in the r3 round (no UI blocks)
TMP = EV / "verify_runs" / "_pytest_tmp"
PY = sys.executable

REAL_FIXTURES = list(range(20))
INTENDED_FIXTURES = []
ALL = REAL_FIXTURES + INTENDED_FIXTURES

STATEFUL = [1, 2, 4, 9, 10, 11, 13, 14, 16, 17, 18, 19]  # DB delta expected
READ_ONLY = [n for n in range(20) if n not in STATEFUL]


def fixture_dir(n: int) -> Path:
    return (REAL if n in REAL_FIXTURES else INTENDED) / str(n)


def run_verifier(n: int, run_dir: Path):
    proc = subprocess.run(
        [PY, str(VERIFY / f"verify_{n}.py"), "--run_dir", str(run_dir)],
        capture_output=True, text=True, timeout=180)
    try:
        verdict = json.loads(proc.stdout)
    except json.JSONDecodeError:
        verdict = {"pass": False, "reason": proc.stdout[-300:] or proc.stderr[-300:]}
    return verdict


def clone(n: int, tag: str) -> Path:
    dst = TMP / f"{n}_{tag}"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(fixture_dir(n), dst)
    return dst


def set_traj(run_dir: Path, **changes):
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    traj.update(changes)
    p.write_text(json.dumps(traj, indent=2))


def drop_nav(run_dir: Path):
    """Strip all step URLs down to the bare start page (no tool navigation)."""
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    start = traj["start_url"]
    for step in traj.get("steps", []):
        step["url"] = start
        step["url_after"] = start
    p.write_text(json.dumps(traj, indent=2))


def mutate_db(run_dir: Path, which: str, sql: str):
    db = sqlite3.connect(run_dir / which)
    db.execute(sql)
    db.commit()
    db.close()


# ---------------------------------------------------------------- happy path
@pytest.mark.parametrize("n", ALL)
def test_honest_fixture_passes(n):
    verdict = run_verifier(n, fixture_dir(n))
    assert verdict["pass"], verdict["reason"]


# ---------------------------------------------------------------- no-op
@pytest.mark.parametrize("n", range(20))
def test_noop_fails(n):
    run_dir = clone(n, "noop")
    set_traj(run_dir, steps=[], final_answer="", terminated=False,
             termination_reason="max_steps")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]


# ---------------------------------------------------------------- shortcuts
@pytest.mark.parametrize("n", range(20))
def test_answer_only_shortcut_fails(n):
    run_dir = clone(n, "shortcut")
    drop_nav(run_dir)
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    fails = [e for e in verdict["evidence"] if e.startswith("FAIL")]
    assert any("nav_" in e for e in fails), verdict["reason"]


# ---------------------------------------------------------------- wrong answers
WRONG = {
    0: "19 Guest favorites under $1600; the cheapest is 'Bear's Walk - Less than 2-Miles to Heavenly Lodge' (rating 5.0); 12 remain with a hot tub; the first hot-tub result costs $585 per night with 4 amenity groups; the 7-night trip total is $4,095.00.",
    1: "Booked 'The Iceberg Tahoe' for 5 nights: code HMSEED001, total $999.00; after cancelling the status is confirmed.",
    2: "Saved 'Provident Doral At The Blue, Blue king suite' and 'The 27 Wynwood, Studio queen' to the wishlist 'Miami trip' — 3 saved items.",
    3: "The top-reviewed Asheville listing is 'Skyscraper Treehouse at Raven Rock Mountain' with 483 reviews; first reviewer Kate; top tag 'Value (295)'; 12 hot-tub listings; the saved listing's nightly rate is $119.60.",
    4: "3 Cooking experiences in Austin; 'Epic Downtown Sunset Kayak w 1 Million Bats' costs $55 per guest, min age 18, 2 agenda stops; booked for 2 guests: total $110.00; Austin lists 12 experiences.",
    5: "12 Guest favorites in Nashville, 9 with a pool; the first is 'Riverview Condo - Walk to Downtown + Free Parking' at $178.70 per night; the most expensive listing is 'Walkable To Broadway' ($818.00) hosted by Amy; the cheapest has 5 reviews.",
    6: "Dana has 3 wishlists: 'Winter cabins', 'NYC weekend' and 'Saved'; the first Winter cabins listing is 'South Tahoe Bungalow' at $230.80 (rating 4.96); the second offers a hot tub with top tag 'Location (183)'; NYC weekend has 4 items.",
    7: "The cheapest New York Guest favorite is 'Bunk pod' at $99 per night, captured trip price $495.00; the new window totals $693.00; booked with code HMSEED004.",
    8: "Los Angeles lists 12 experiences; the most expensive is 'Giant Glow Paddleboard Downtown at Sunset w/ Bats' ($65 per guest, rating 4.93), agenda stop 'Sunset'; min age any; the second is 'Tube Downtown Austin's Springs to Party Island' at $65; Bob's wishlist 'Favorites'; Bob has 3 trips.",
    9: "12 Guest favorites in Lake Tahoe; the first result costs $585 per night; the 5-night trip total is $2,925.00; confirmation code HMSEED001.",
    10: "4 saved items before; 3 after removing the Lake Tahoe listing; Trips: HMSEED003 confirmed and HMSEED004 cancelled; the Scottsdale stay's top tag is 'Location (9)'; rebooked for 2 guests with code HMSEED002 for $306.00.",
    11: "Booked 'South Beach King Room | Boutique Hotel' for 5 nights: code HMSEED001, total $500.00; saved to wishlist 'My trips' with 2 items.",
    12: "4 Superhost listings in Nashville; the first is 'Hotel in Downtown Nashville' hosted by Sarah (12 years hosting, check-in after 2:00 PM); top tag 'Cleanliness (12)'; the pool-filtered first is 'Modern Condo & Private Terrace' at $163.60 with first reviewer Brad.",
    13: "12 Asheville listings have a hot tub; the first is 'Cottage in the Trees- Walk Downtown AVL- Hot Tub' with 4 amenity groups and top tag 'Location (476)'; Bob booked it: code HMSEED003, dates 2026-10-04, total $1,154.00; Bob now has 3 bookings.",
    14: "The first NYC Cultural tour is 'Bike Tour: Radical & Weird History of NYC' at $48 per guest (105 ratings); the second is 'Hamilton & Washington's New York with a historian' at $48; booked for 3 guests: total $144.00, code HMSEED002.",
    15: "The most expensive Scottsdale Guest favorite is 'Scottsdale Home OldTown w 3bth & 3bdrm heated pool' (trip price $1,278.00, 219 reviews); amenity groups: Kitchen, Bedroom, Bathroom; top tag 'Location (219)'; first reviewer Maria; the second is 'Casita Bonita' at $131 per night with first reviewer Lee.",
    16: "12 Los Angeles listings have a hot tub; the cheapest is 'Best location | 1b1b Hollywood sign +balcony' at $105 per night; booked: code HMSEED001, total $525.00; final status confirmed; the default wishlist has 3 items.",
    17: "19 Guest favorites in Lake Tahoe; the second listing is 'Al Tahoe Oasis' (rating 4.99); explore: Mammoth Lakes and Sacramento; top tag 'View (13)'; first reviewer from Boise, Idaho; the default wishlist has 4 items.",
    18: "4 Instant Book listings in Austin allow pets; the first is 'Downtown Condo' at $210.50 per night, max 8 guests; booked for 3 guests: code HMSEED002, total $1,052.50.",
    19: "Miami lists 12 Water sports experiences; the cheapest is 'Walk Raccoon Island and Swim the Bay' at $70 (rating 4.91); the second cheapest is 'Biscayne Bay jet ski adventure in Miami' at $50; booked for 4 guests: total $280.00, code HMSEED003; Alice now has 6 trips.",
}


@pytest.mark.parametrize("n", range(20))
def test_wrong_answer_fails(n):
    run_dir = clone(n, "wrong")
    mutate_answer(run_dir, WRONG[n])
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    fails = [e for e in verdict["evidence"] if e.startswith("FAIL")]
    assert fails, "expected at least one answer/DB failure"


def mutate_answer(run_dir: Path, new_answer: str):
    set_traj(run_dir, final_answer=new_answer)


# ---------------------------------------------------------------- stale DB
@pytest.mark.parametrize("n", [1, 9, 10, 11, 13, 14, 16, 18, 19])
def test_stale_db_fails(n):
    """The trajectory claims the booking, but the after-DB lacks it."""
    run_dir = clone(n, "stale")
    mutate_db(run_dir, "after.db",
             "DELETE FROM bookings WHERE code NOT LIKE 'HMSEED%'")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]


@pytest.mark.parametrize("n", [2, 17])
def test_stale_wishlist_fails(n):
    """The trajectory claims the save, but the after-DB lacks it."""
    run_dir = clone(n, "stale_wl")
    mutate_db(run_dir, "after.db",
              "DELETE FROM wishlist_items WHERE listing_id IS NOT NULL OR experience_id IS NOT NULL")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]


@pytest.mark.parametrize("n", [4, 8])
def test_stale_exp_save_fails(n):
    run_dir = clone(n, "stale_exp")
    mutate_db(run_dir, "after.db",
              "DELETE FROM wishlist_items WHERE experience_id IS NOT NULL")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]


# ---------------------------------------------------------------- stray writes
@pytest.mark.parametrize("n", READ_ONLY)
def test_read_only_violation_fails(n):
    run_dir = clone(n, "write")
    mutate_db(run_dir, "after.db",
              "INSERT INTO wishlist_items (wishlist_id, listing_id, added_at) "
              "VALUES (1, '13434357', '2026-09-30')")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]


# ---------------------------------------------------------------- tampered packages
def test_wrong_task_id_fails():
    run_dir = clone(7, "taskid")
    set_traj(run_dir, task_id="Airbnb--17")
    verdict = run_verifier(7, run_dir)
    assert not verdict["pass"]


def test_offsite_url_fails():
    run_dir = clone(4, "offsite")
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    traj["steps"][2]["url_after"] = "https://www.airbnb.com/s/experiences"
    p.write_text(json.dumps(traj, indent=2))
    verdict = run_verifier(4, run_dir)
    assert not verdict["pass"]


def test_cross_port_fails():
    run_dir = clone(9, "xport")
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    traj["steps"][1]["url_after"] = "http://localhost:48116/s/lake-tahoe/homes"
    p.write_text(json.dumps(traj, indent=2))
    verdict = run_verifier(9, run_dir)
    assert not verdict["pass"]


def test_not_terminated_fails():
    run_dir = clone(11, "noterm")
    set_traj(run_dir, terminated=False, termination_reason="max_steps")
    verdict = run_verifier(11, run_dir)
    assert not verdict["pass"]


def test_empty_answer_fails():
    run_dir = clone(15, "empty")
    set_traj(run_dir, final_answer="")
    verdict = run_verifier(15, run_dir)
    assert not verdict["pass"]


def test_bad_png_fails():
    run_dir = clone(17, "badpng")
    traj = json.loads((run_dir / "trajectory.json").read_text())
    referenced = [s["screenshot_before"] for s in traj["steps"][:5]
                  if s.get("screenshot_before")]
    target = run_dir / "screenshots" / referenced[0]
    target.write_bytes(b"not a png")
    verdict = run_verifier(17, run_dir)
    assert not verdict["pass"]
    assert any("screenshots_decode" in e for e in verdict["evidence"]
               if e.startswith("FAIL"))


def test_premutated_seed_fails():
    """A run graded against a pre-mutated database fails the seed gate."""
    run_dir = clone(6, "badseed")
    mutate_db(run_dir, "initial.db",
              "UPDATE listings SET name = name || ' tampered' WHERE id = '13434357'")
    verdict = run_verifier(6, run_dir)
    assert not verdict["pass"]
    assert any("seed_" in e for e in verdict["evidence"] if e.startswith("FAIL"))


@pytest.mark.parametrize("pair", [(0, 9), (7, 17), (14, 4), (19, 8)])
def test_task_confusion_fails(pair):
    """Verifier N run against the trajectory of a different task M."""
    n, m = pair
    run_dir = clone(m, f"confused_{n}")
    set_traj(run_dir, task_id=f"Airbnb--{n}")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
