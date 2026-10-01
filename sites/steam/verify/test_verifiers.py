#!/usr/bin/env python3
"""test_verifiers.py — adversarial contract tests for the steam verifier suite.

Guarantees (run with pytest):
  * each honest fixture (from the reviewer's two independent r2 Playwright
    rounds on the r2 review container wh-steam-r2, image webharbor:steam-r2
    built independently from the fix tree e2ea4cb0, seed md5
    b9a24e716aa09b3702ab3a0b38d8c4de / sha256 e6d0805e… unchanged) PASSES
    its verify_<n>.py — both rounds, 40/40;
  * every adversarial negative FAILS (zero false positives):
      - no-op trajectories (20),
      - answer-only shortcuts with no navigation (20),
      - wrong-answer trajectories (20, fabricated per question point),
      - stale-DB trajectories (the 19 stateful tasks with the after-state
        rolled back to the seed),
      - read-only violations (unexpected DB writes, incl. on the one
        read-only task),
      - tampered packages (wrong task_id / off-site URL / cross-port /
        not-terminated / empty answer / bad PNG / pre-mutated seed),
      - task-confusion (swapped task packages and cross-task answers).
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
EV = Path("/data/zhaoyang-user-projects/websyn/wh-steam-review-evidence")
R1 = EV / "walks" / "r2a"
R2 = EV / "walks" / "r2b"
TMP = EV / "verify_runs" / "_pytest_tmp"
PY = sys.executable

TASK_IDS = [f"Steam--{n}" for n in range(20)]
# every task except 15 writes to the database (wishlist / orders / users)
STATEFUL = [n for n in range(20) if n != 15]
READ_ONLY = [15]


def run_verifier(n: int, run_dir: Path):
    proc = subprocess.run(
        [PY, str(VERIFY / f"verify_{n}.py"), "--run_dir", str(run_dir)],
        capture_output=True, text=True, timeout=180)
    try:
        verdict = json.loads(proc.stdout)
    except json.JSONDecodeError:
        verdict = {"pass": False, "reason": proc.stdout[-300:] or proc.stderr[-300:]}
    return verdict


def clone(round_dir: Path, n: int, tag: str) -> Path:
    dst = TMP / f"{n}_{tag}"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(round_dir / str(n), dst)
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


def drop_nav(run_dir: Path):
    """Strip all step URLs down to the bare start page (no tool navigation)."""
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    start = traj["start_url"]
    for step in traj.get("steps", []):
        step["url"] = start
        step["url_after"] = start
    p.write_text(json.dumps(traj, indent=2))


def kill_png(run_dir: Path):
    shots = sorted((run_dir / "screenshots").glob("step_*.png"))
    assert shots, "fixture must contain screenshots"
    # destroy the PNG magic itself (verify_lib decodes the 8-byte signature)
    shots[0].write_bytes(b"CORRUPTED_NOT_A_PNG" + b"\x00\xff" * 64)


# ---------------------------------------------------------------- happy path
@pytest.mark.parametrize("n", range(20))
def test_honest_fixture_r1_passes(n):
    verdict = run_verifier(n, R1 / str(n))
    assert verdict["pass"], verdict["reason"]


@pytest.mark.parametrize("n", range(20))
def test_honest_fixture_r2_passes(n):
    verdict = run_verifier(n, R2 / str(n))
    assert verdict["pass"], verdict["reason"]


# ---------------------------------------------------------------- no-op
@pytest.mark.parametrize("n", range(20))
def test_noop_fails(n):
    run_dir = clone(R1, n, "noop")
    set_traj(run_dir, steps=[], final_answer="", terminated=False,
             termination_reason="max_steps")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]


# ---------------------------------------------------------------- shortcuts
@pytest.mark.parametrize("n", range(20))
def test_answer_only_shortcut_fails(n):
    run_dir = clone(R1, n, "shortcut")
    drop_nav(run_dir)
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any(e.startswith("FAIL nav_") for e in verdict["evidence"])


# ---------------------------------------------------------------- wrong answers
WRONG = {
    0: ("Filtering the search to RPG games priced under $20 shows 14 results; "
        "narrowing to the discounted ones leaves 8 RPGs on sale. Sorted by price "
        "the cheapest game is Rift of the NecroDancer at $1.99. Its store page "
        "lists the review summary Very Positive, release date Apr 23, 2021, and "
        "40,000 user reviews. Alice's wishlist shows 2 items."),
    1: ("Filtering the search to Linux games that are currently discounted shows "
        "3 results. The most expensive is American Truck Simulator, full price "
        "$29.99, with a 90% discount (now $2.99). Its Windows minimum system "
        "requirements list Windows 11, and its review summary is Mixed. With the "
        "Linux filter cleared, the store has 25 discounted games. Bob's wishlist "
        "shows 4 items."),
    2: ("Counter-Strike 2 requires 4 GB RAM and was released Aug 21, 2013 with "
        "the review summary Mostly Positive; Dota 2 requires 8 GB RAM, so Dota 2 "
        "requires more minimum RAM. Dota 2's positive review filter shows 8 "
        "reviews and the most recent one is by Anttolin. The wishlist shows 5 items."),
    3: ("After removing Hades from Carol's wishlist, Hades II costs $29.99 and was "
        "released Sep 25, 2024. The cheapest Casual game under $10 is Peggle at "
        "$2.49. After adding both, Carol's wishlist has 5 items."),
    4: ("The Portal Bundle costs $19.98. With ELDEN RING's quantity changed to 2, "
        "the cart subtotal is $119.98. Checking out with Bob's address produced "
        "order ST-1005 with a total of $119.98."),
    5: ("Specials lists 25 discounted games. The two biggest discounts are 80% on "
        "Hades (originally $24.99, now $4.99, saving $20.00) and 80% on Stellaris. "
        "The cheaper one has the review summary Very Positive and was released "
        "May 9, 2016. Filtering the specials to Indie games leaves 5 on sale, and "
        "to macOS games 3. The cheapest is Hades at $6.24; the most expensive "
        "costs $49.99 with the review summary Mostly Positive. Carol's wishlist "
        "shows 5 items."),
    6: ("Stellaris costs $49.99 and its overall review summary is Mostly Positive "
        "with 90,000 total reviews. Filtering to negative reviews shows 5; the "
        "most recent is by Real Zakhar with 1697 hrs on record. Sorted by most "
        "helpful, the top review is by Anttolin. The newest news post is 'Stellaris "
        "4.4 released'. Bob's wishlist shows 4 items."),
    7: ("Valve's developer page lists 15 games. The most expensive is Half-Life 2 "
        "at $9.99; the free-to-play ones are Dota 2 and Team Fortress 2. "
        "Counter-Strike 2 was released Aug 21, 2013 (Mostly Positive); Dota 2 "
        "Jul 9, 2014 (Mixed); Team Fortress 2 Oct 10, 2007 (Mostly Positive); "
        "Half-Life 2 Nov 16, 2004 (Very Positive); the cart subtotal was $9.99. "
        "Valve's publisher page lists 18 games. Dana's wishlist shows 3 items."),
    8: ("Counter-Strike 2's newest news post is 'CS2 Patch Notes' on the Product "
        "Update feed, posted October 1, 2026. Dota 2's newest post is '7.41g "
        "Gameplay Patch' posted September 20, 2026, so Dota 2's newest post is "
        "the more recent. Counter-Strike 2 is priced $14.99 with the review "
        "summary Mostly Positive. Carol's wishlist shows 3 items."),
    9: ("The bundle including Portal 2 costs $19.98; its items bought separately "
        "would cost $29.98, saving $10.00. The cart subtotal was $19.98. Checking "
        "out with Alice's address produced order ST-1005 totaling $19.98; the "
        "confirmation lists the line items Portal Bundle and Portal 2."),
    10: ("There are 12 free games in the store. The first free Action game is "
         "Counter-Strike 2, with the review summary Mostly Positive and 500,000 "
         "total reviews. Frank's wishlist shows 2 items; after signing out and "
         "back in it shows 1 item."),
    11: ("The Indie genre page lists 29 games. Sorted by release date the newest "
         "is PEAK at $4.95, discounted 38%. The most expensive is Slay the Spire 2 "
         "at $24.99, released Mar 5, 2026. 8 Indie games are under $15. The newest "
         "game's review summary is Overwhelmingly Positive; its reviews page shows "
         "the summary Mostly Positive. Dana's wishlist shows 3 items."),
    12: ("Alice's existing order is ST-1002 totaling $59.99. After buying Left 4 "
         "Dead 2, the new order is ST-1005 totaling $19.98, and Alice has 3 "
         "orders in total."),
    13: ("Filtering Action games with Mixed reviews shows 3 results: Minecraft "
         "Dungeons II at $19.99 and Monster Hunter Wilds at $29.99. The cheapest "
         "requires Windows 11, a Ryzen 5 3600, and 16 GB RAM of memory, with "
         "10,000 total reviews of which 55% are positive. The more expensive one "
         "requires 32 GB RAM. Alice's wishlist shows 4 items."),
    14: ("The store's Free price filter lists 15 free games. Dota 2 shows the "
         "review summary Mostly Positive with 90% of 900,000 reviews positive; "
         "Counter-Strike 2 shows Very Positive with 95% of 3,000,000 positive, "
         "so Counter-Strike 2 has the higher positive percentage. Team Fortress "
         "2's review summary is Mixed. Dana's wishlist shows 5 items."),
    15: ("Dead Cells lists 5 DLC items; the first is Dead Cells: Fatal Falls at "
         "$3.99, released Feb 23, 2021. Adding it gave a subtotal of $3.99. Dead "
         "Cells itself costs $24.99 at -20%. The first bundle is Motion Twin's "
         "Mosh Pit Mayhem at $59.94 with 6 items; its subtotal was $59.94. Dead "
         "Cells with quantity 3 gave a subtotal of $59.97. The second bundle is "
         "Windblown + Dead Cells at $24.99."),
    16: ("Searching the store for resident returns 2 results: Resident Evil 2 "
         "and Resident Evil 4. With the Action filter 2 remain. Resident Evil 2 "
         "costs $49.99 and was released Jan 25, 2019; Resident Evil 4 costs "
         "$29.99 and was released March 24, 2023, making it the most recent. Its "
         "reviews page shows the overall summary Very Positive and its newest "
         "news post is 'Resident Evil 4 ships'. Carol's wishlist shows 3 items."),
    17: ("Searching for hades returns 3 results. Hades costs $24.99 (no "
         "discount), released Sep 17, 2021, review summary Very Positive. Hades "
         "II costs $29.99, released Sep 25, 2024, review summary Mostly "
         "Positive. Hades II is the cheaper one, and neither supports macOS. "
         "The most recent positive Hades II review is by Cobble K Stone. Adding "
         "Hades gave a subtotal of $24.99. Alice's wishlist shows 4 items."),
    18: ("FINAL FANTASY VII REMAKE INTERGRADE is -50% $49.99 $24.99 and Hades is "
         "-30% $29.99 $20.99. With both in the cart the subtotal is $45.98. "
         "Checking out with Dana's address produced order ST-1005 charging "
         "$45.98, with the line items Hades II and FINAL FANTASY VII REBIRTH."),
    19: ("Cyberpunk 2077 requires 16 GB RAM minimum, 32 GB recommended, the "
         "minimum graphics card RTX 3070 and 100 GB of storage. ELDEN RING "
         "requires 16 GB RAM minimum, 32 GB recommended, an RTX 4070 and 80 GB "
         "of storage, so ELDEN RING needs more storage and supports macOS. "
         "ELDEN RING costs $49.99 with the review summary Mostly Positive. "
         "Cyberpunk's reviews page shows the summary Mixed with 5 reviews shown. "
         "The cart subtotal was $49.99. Dana's wishlist shows 3 items."),
}


@pytest.mark.parametrize("n", range(20))
def test_wrong_answer_fails(n):
    run_dir = clone(R1, n, "wrong")
    mutate_answer(run_dir, WRONG[n])
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"wrong answer must fail: {WRONG[n][:60]}..."


# ---------------------------------------------------------------- stale DB
@pytest.mark.parametrize("n", STATEFUL)
def test_stale_db_fails(n):
    run_dir = clone(R1, n, "stale")
    shutil.copy(run_dir / "initial.db", run_dir / "after.db")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any("db_" in e for e in verdict["evidence"] if e.startswith("FAIL"))


# ---------------------------------------------------------------- read-only violation
@pytest.mark.parametrize("n", READ_ONLY)
def test_readonly_violation_fails(n):
    run_dir = clone(R1, n, "readonlyviol")
    mutate_db(run_dir, "after.db",
              "INSERT INTO wishlist_items (user_id, game_id, added_ts) "
              "VALUES (1, 1, '2026-10-01T00:00:00Z')")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any("db_read_only" in e for e in verdict["evidence"] if e.startswith("FAIL"))


@pytest.mark.parametrize("n", [0, 4, 12])
def test_stateful_extra_write_fails(n):
    run_dir = clone(R1, n, "extrawrite")
    mutate_db(run_dir, "after.db",
              "INSERT INTO cart_items (cart_key, kind, game_id, qty) "
              "VALUES ('rogue', 'game', 1, 1)")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any("db_" in e for e in verdict["evidence"] if e.startswith("FAIL"))


# ---------------------------------------------------------------- tampered packages
@pytest.mark.parametrize("n", [0, 7, 15])
def test_wrong_task_id_fails(n):
    run_dir = clone(R1, n, "wrongtid")
    set_traj(run_dir, task_id=f"Steam--{(n + 1) % 20}")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any(e.startswith("FAIL task_id") for e in verdict["evidence"])


@pytest.mark.parametrize("n", [1, 9, 18])
def test_offsite_url_fails(n):
    run_dir = clone(R1, n, "offsite")
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    for step in traj["steps"]:
        if step.get("url_after") and step["url_after"].startswith("http://localhost"):
            step["url_after"] = step["url_after"].replace(
                "http://localhost:46136", "https://store.steampowered.com")
            break
    p.write_text(json.dumps(traj, indent=2))
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any(e.startswith("FAIL urls_same_origin") for e in verdict["evidence"])


@pytest.mark.parametrize("n", [2, 11])
def test_cross_port_url_fails(n):
    run_dir = clone(R1, n, "crossport")
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    for step in traj["steps"]:
        if step.get("url_after"):
            step["url_after"] = step["url_after"].replace(":46136", ":48136")
            break
    p.write_text(json.dumps(traj, indent=2))
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any(e.startswith("FAIL urls_same_origin") for e in verdict["evidence"])


@pytest.mark.parametrize("n", [3, 6, 14])
def test_not_terminated_fails(n):
    run_dir = clone(R1, n, "notterm")
    set_traj(run_dir, terminated=False, termination_reason="max_steps")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any(e.startswith("FAIL terminated") for e in verdict["evidence"])


@pytest.mark.parametrize("n", [5, 10, 16])
def test_empty_answer_fails(n):
    run_dir = clone(R1, n, "emptyans")
    set_traj(run_dir, final_answer="")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any(e.startswith("FAIL final_answer") for e in verdict["evidence"])


@pytest.mark.parametrize("n", [8, 13, 19])
def test_bad_png_fails(n):
    run_dir = clone(R1, n, "badpng")
    kill_png(run_dir)
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any(e.startswith("FAIL screenshots") for e in verdict["evidence"])


@pytest.mark.parametrize("n", [0, 4, 15])
def test_pre_mutated_seed_fails(n):
    run_dir = clone(R1, n, "badseed")
    mutate_db(run_dir, "initial.db",
              "INSERT INTO cart_items (cart_key, kind, game_id, qty) "
              "VALUES ('pre', 'game', 1, 1)")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any(e.startswith("FAIL seed_") for e in verdict["evidence"])


# ---------------------------------------------------------------- task confusion
@pytest.mark.parametrize("n,m", [(0, 1), (4, 9), (10, 12), (15, 17), (16, 19), (5, 11)])
def test_swapped_task_package_fails(n, m):
    """Task n's verifier must reject task m's honest package."""
    run_dir = clone(R1, m, f"swapped_{n}_{m}")
    set_traj(run_dir, task_id=f"Steam--{n}")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]


@pytest.mark.parametrize("n,m", [(2, 14), (6, 17)])
def test_cross_task_answer_fails(n, m):
    """Task n's verifier must reject task m's honest final answer."""
    run_dir = clone(R1, n, f"crossans_{n}_{m}")
    other = json.loads((R1 / str(m) / "trajectory.json").read_text())
    mutate_answer(run_dir, other["final_answer"])
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]


# ---------------------------------------------------------------- wrong wishlist rows
@pytest.mark.parametrize("n", [1, 13])
def test_wrong_stateful_row_fails(n):
    """A stateful run that wrote the WRONG row must fail."""
    run_dir = clone(R1, n, "wrongrow")
    mutate_db(run_dir, "after.db",
              "DELETE FROM wishlist_items WHERE id > (SELECT MIN(id) FROM wishlist_items) "
              "AND user_id = (SELECT user_id FROM wishlist_items ORDER BY id DESC LIMIT 1) "
              "AND game_id = (SELECT game_id FROM wishlist_items ORDER BY id DESC LIMIT 1)")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any("db_" in e for e in verdict["evidence"] if e.startswith("FAIL"))
