#!/usr/bin/env python3
"""test_verifiers.py — adversarial contract tests for the red_bull verifier suite
(r2 re-freeze against the fix branch @ 4f33f649).

Guarantees (run with pytest):
  * each honest fixture (from the reviewer's two independent Playwright rounds
    on the r2 review container wh-red-bull-review2, seed md5
    652c2f0fade475e6905194c6700b9923) PASSES its verify_<n>.py;
  * every adversarial negative FAILS (zero false positives):
      - no-op trajectories (20),
      - answer-only shortcuts with no navigation (20),
      - wrong-answer trajectories (20, fabricated per question point),
      - stale-DB trajectories (all 7 stateful tasks: the DB delta is undone
        while the answer claims success),
      - read-only violations (unexpected DB writes on read-only tasks),
      - tampered packages (wrong task_id / off-site URL / cross-port /
        not-terminated / empty answer / pre-mutated seed),
      - task-specific confusions (wrong-event registration, wrong badge,
        swapped flavor, letter-A lie, wrong save-target outcome).
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
EV = Path("/data/zhaoyang-user-projects/websyn/wh-red-bull-review-evidence/r2")
FIXTURES = EV / "fixtures"
TMP = EV / "verify_runs" / "_pytest_tmp"
PY = sys.executable

TASK_IDS = [f"Red Bull--{n}" for n in range(20)]
READ_ONLY = [n for n in range(20) if n not in (0, 1, 4, 10, 12, 13, 14)]
STATEFUL = [0, 1, 4, 10, 12, 13, 14]


def run_verifier(n: int, run_dir: Path):
    proc = subprocess.run(
        [PY, str(VERIFY / f"verify_{n}.py"), "--run_dir", str(run_dir)],
        capture_output=True, text=True, timeout=120)
    try:
        verdict = json.loads(proc.stdout)
    except json.JSONDecodeError:
        verdict = {"pass": False, "reason": proc.stdout[-300:] or proc.stderr[-300:]}
    return verdict


def clone(n: int, tag: str) -> Path:
    dst = TMP / f"{n}_{tag}"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(FIXTURES / str(n), dst)
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


# ---------------------------------------------------------------- happy path
@pytest.mark.parametrize("n", range(20))
def test_honest_fixture_passes(n):
    verdict = run_verifier(n, FIXTURES / str(n))
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
    assert any("nav_" in e or "screenshots" in e or "same_origin" in e
               for e in verdict["evidence"] if e.startswith("FAIL"))


# ---------------------------------------------------------------- wrong answers
WRONG = {
    0: "The FAQs say hardboards are required, spectators must buy tickets, check-in "
       "runs 2p - 3p, the entry fee is $50, my code is RB00000000, and the Rhode "
       "Island stop is at Narragansett Casino Pier. The series page lists the "
       "Long Beach Island stop last, on August 1, 2026.",
    1: "The only upcoming US event with open registrations is Sypher's Showdown at "
       "$15; I registered for it at the Omni Theater. My code is RB11111111.",
    2: "The Iowa motocross event is at Cedar Rapids MX Park and celebrates the "
       "1980s. DTM Nürburgring runs May 1-2 and Hockenheimring June 3-4. The "
       "esports event runs January 1 - March 3 with a Past event badge.",
    3: "The cliff diving series is about skydiving from 5m platforms with one stop "
       "in Paris, France. King of the Air has 7 stops and Foam Wreckers has 12.",
    4: "Rapid Release is capped at 10 teams of 5; check-in opens at 9:00 PM. No "
       "errors were shown. My code is RB22222222 and the entry fee is $75.",
    5: "The Summer Edition has 150mg caffeine and 40g sugars in 8.4 fl oz cans only. "
       "The Original has 60mg/10g. No Edition has a sugarfree variant; the Red "
       "Edition has a twin. Amber has 200mg/50g and Peach 5mg/1g. Red Bull "
       "Sugarfree is the one sweetened with monk fruit extract.",
    6: "There are 2 UK athletes: Gee Atherton (Surfing) and Sky Brown (Motocross). "
       "Career starts 1990 and 1995. The A-Z letter T shows Terry Adams right away; "
       "his discipline is Skateboard Street, he is from Australia, and he was born "
       "May 5, 1990.",
    7: "The newest film is 'Blue Crush' with subheading 'The rise of women's surfing' "
       "at 120 min. Snowboarding has 3 films (first: The Modus Mix), the single "
       "Cliff Diving film is 'The Stunt' at 90 min, Surfing has 2, esports has 40, "
       "and page 2 starts with 9191.",
    8: "Winter Heroes has 4 seasons and 60 episodes; its first three episodes are "
       "E1, E2, E3. There are 9 Snowboarding shows (first: Dual Focus). No Contest "
       "is Snowboarding with 5 episodes. Inside Pro Surfing has 1 season and 4 "
       "episodes. The second snowboarding show is Glimpse/ with 2 episodes.",
    9: "The USA final was held in Kansas City; the winner was Kidd The Monster (32), "
       "from Florida. The Games topic lists 3 stories. A GTA 6 fact: it launches in "
       "March. The rainbow jersey is green. The newest story is the GTA 6 soundtrack "
       "(topic Games); it says the soundtrack has 12 tracks.",
    10: "The cheapest ORBR headwear item is the 59Fifty Brazil GP Flat Cap at $63.95. "
        "My order number is RB-999999 and the total is $127.90 for quantity 2.",
    11: "The hoodie is crafted from pure polyester with a silk finish; XS costs "
        "$84.95 and its category is bags. The cheapest item overall is the Red Bull "
        "Glass at $11.95 (tops). headwear lists 12 products, Rampage has 3, bags 40.",
    12: "Salzburg lists 4 products with the lowest at $79.95. I added the Puma Home "
        "Jersey; subtotals were $114.95 and $229.90, and after the quantity update "
        "$300.00. After removing the jersey the cart still contains the tote bag.",
    13: "Bob's registration code is RB9C04D7 for the Foam Wreckers Virginia Beach "
        "event on October 3, 2026 with ticket type General Admission. I removed the "
        "Barn Find event from his favorites and saved Inside Pro Surfing instead; "
        "the venue is Rhythms of the Night. His favorited story topic is Games.",
    14: "Carol's existing favorites are the Barn Find Open event and the Blue Crush "
        "film. I saved the Wings Cup event (venue Cape Town) and it appears on her "
        "account page. The film Blue Crush runs 94 minutes and was saved.",
    15: "The calendar lists 4 German events with 3 upcoming. The finished ones are "
        "two Padel tournaments. The urban downhill race was in Munich where riders "
        "face a swimming pool. Sachsenring runs July 1-2, Oschersleben runs "
        "December 1-2, Fürstlich Drehna's venue is the Nürburgring and Gaildorf's "
        "venue is the Sachsenring, and the drifting venue is the Hockenheimring.",
    16: "There are 45 upcoming US events; the earliest is the Barn Find Open on "
        "October 17. The Wings Cup standfirst says 'Play FIFA 27' and its FAQs say "
        "there is a $99 entry fee. The Narragansett card shows a 'Registrations "
        "open' badge; its venue is 68th Street Ocean Beach. The Burbank basketball "
        "venue is Staples Center with a $20 entry fee.",
    17: "Coconut tastes like Blueberry, Apple like Pineapple, Sea Blue like Cherry. "
        "The Iced Edition Sugarfree has 200mg caffeine, the Pink Edition has 5g "
        "sugars, Sugarfree comes only in 8.4 fl oz, and the Summer Edition Sugarfree "
        "tastes of Mango with 150mg caffeine.",
    18: "The USA final was at Madison Square Garden on November 5, 2026. The related "
        "story says it was held in Chicago, won by Surge (25), from Texas. The world "
        "final is at Wembley on December 1. The BC One Cypher USA venue is Times "
        "Square. The BC One World Final Toronto is at Rogers Centre on December 25, "
        "2026 with standfirst 'A holiday special'. The Dance discipline lists 20 "
        "events.",
    19: "Eli Tomac is Canadian, born March 3, 1990, and grew up racing in Miami. "
        "The US BMX Flatland athlete (Courage Adams) was born in Madrid, Spain. The "
        "difference: supercross is raced indoors on oval dirt tracks with no jumps. "
        "There are 12 Skateboarding-topic stories.",
}


@pytest.mark.parametrize("n", range(20))
def test_wrong_answer_fails(n):
    run_dir = clone(n, "wrong")
    mutate_answer(run_dir, WRONG[n])
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any(e.startswith("FAIL") and not e.startswith("FAIL nav_")
               for e in verdict["evidence"])


# ---------------------------------------------------------------- stale DB
@pytest.mark.parametrize("n", STATEFUL)
def test_stale_db_fails(n):
    run_dir = clone(n, "stale")
    which = {0: ("after.db", "DELETE FROM event_registrations WHERE email='casey.rider@example.com'"),
             1: ("after.db", "DELETE FROM event_registrations WHERE email='sam.porter@example.com'"),
             4: ("after.db", "DELETE FROM event_registrations WHERE email='dana.k@example.com'"),
             10: ("after.db", "DELETE FROM shop_orders WHERE order_number != 'RB-100234'"),
             12: ("after.db", "DELETE FROM cart_items"),
             13: ("after.db", "DELETE FROM favorites WHERE user_id=2 AND kind='event' AND item_slug='red-bull-barn-find-open'"),
             14: ("after.db", "DELETE FROM favorites WHERE user_id=3 AND kind='event' AND item_slug='red-bull-barn-find-open'"),
             }[n]
    mutate_db(run_dir, which[0], which[1])
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any("db_" in e or "row" in e for e in verdict["evidence"] if e.startswith("FAIL"))


# ---------------------------------------------------------------- read-only violations
@pytest.mark.parametrize("n", READ_ONLY[:8])
def test_readonly_violation_fails(n):
    run_dir = clone(n, "dirty")
    mutate_db(run_dir, "after.db",
              "INSERT INTO favorites (user_id, kind, item_slug) VALUES (4, 'event', 'x')")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any("db_read_only" in e or "db_tables_changed" in e
               for e in verdict["evidence"] if e.startswith("FAIL"))


# ---------------------------------------------------------------- tampering
@pytest.mark.parametrize("n", [0, 9, 15])
def test_wrong_task_id_fails(n):
    run_dir = clone(n, "wrongid")
    set_traj(run_dir, task_id="Red Bull--99")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]


@pytest.mark.parametrize("n", [3, 11, 17])
def test_offsite_url_fails(n):
    run_dir = clone(n, "offsite")
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    traj["steps"][2]["url_after"] = "https://www.redbull.com/us-en/"
    p.write_text(json.dumps(traj, indent=2))
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any("same_origin" in e for e in verdict["evidence"] if e.startswith("FAIL"))


@pytest.mark.parametrize("n", [1, 8, 19])
def test_cross_port_url_fails(n):
    run_dir = clone(n, "crossport")
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    traj["steps"][2]["url_after"] = traj["steps"][2]["url_after"].replace(":46127", ":48127")
    p.write_text(json.dumps(traj, indent=2))
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any("same_origin" in e for e in verdict["evidence"] if e.startswith("FAIL"))


@pytest.mark.parametrize("n", [5, 12, 18])
def test_not_terminated_fails(n):
    run_dir = clone(n, "unterm")
    set_traj(run_dir, terminated=False, termination_reason="max_steps")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]


@pytest.mark.parametrize("n", [7, 14, 16])
def test_empty_answer_fails(n):
    run_dir = clone(n, "empty")
    mutate_answer(run_dir, "")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]


@pytest.mark.parametrize("n", [2, 6, 13])
def test_pre_mutated_seed_fails(n):
    run_dir = clone(n, "badseed")
    mutate_db(run_dir, "initial.db",
              "INSERT INTO favorites (user_id, kind, item_slug) VALUES (4, 'event', 'x')")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any("seed_" in e for e in verdict["evidence"] if e.startswith("FAIL"))


@pytest.mark.parametrize("n", [0, 10])
def test_bad_screenshot_fails(n):
    run_dir = clone(n, "badpng")
    shots = sorted((run_dir / "screenshots").glob("step_*.png"))
    (shots[0]).write_bytes(b"not a png")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"]
    assert any("screenshots" in e for e in verdict["evidence"] if e.startswith("FAIL"))


# ---------------------------------------------------------------- task confusions
def test_t1_wrong_event_registration_fails():
    """Register for the $15 Sypher event instead of the $10 Carolina Beach one."""
    run_dir = clone(1, "wrongsypher")
    mutate_answer(run_dir, "The upcoming US reg-open events are VA Beach ($20), Rapid "
                           "Release (free) and Carolina Beach ($10). I registered for "
                           "the cheapest with a fee: Carolina Beach Boardwalk, October "
                           "24, 2026, code " + "RBDEADBEEF" + ".")
    mutate_db(run_dir, "after.db",
              "UPDATE event_registrations SET event_id=41, price=15.0 WHERE email='sam.porter@example.com'")
    verdict = run_verifier(1, run_dir)
    assert not verdict["pass"]


def test_t16_wrong_badge_fails():
    """Claiming the Narragansett card shows a 'Registrations open' badge trips."""
    run_dir = clone(16, "wrongbadge")
    mutate_answer(run_dir, "There are 18 upcoming US events; earliest is Red Bull Foam "
                           "Wreckers - Virginia Beach, VA. Wings Cup standfirst not "
                           "rendered; fee not shown. The Narragansett card shows a "
                           "'Registrations open' badge and its venue is Narragansett "
                           "Town Beach. Burbank basketball venue: Walk-On's Sports "
                           "Bistreaux - Burbank Restaurant, fee Free.")
    verdict = run_verifier(16, run_dir)
    assert not verdict["pass"]
    assert any("narr_badge_negative" in e for e in verdict["evidence"] if e.startswith("FAIL"))


def test_t17_swapped_flavors_fails():
    run_dir = clone(17, "swap")
    mutate_answer(run_dir, "Coconut: Juneberry; Apple: Fuji Apple & Ginger; Sea "
                           "Blue: Coconut Berry. Iced Edition Sugarfree caffeine: "
                           "80 mg per 8.4 fl oz can. Pink Edition sugars: 26 g per "
                           "can. Red Bull Sugarfree sizes: 8.4 fl oz, 12 fl oz, "
                           "16 fl oz, 20 fl oz. Summer Edition Sugarfree: Sudachi "
                           "Lime, 80 mg caffeine per can.")
    verdict = run_verifier(17, run_dir)
    assert not verdict["pass"]
    assert any("coconut_flavor" in e or "seablue_flavor" in e
               for e in verdict["evidence"] if e.startswith("FAIL"))


def test_t6_letter_a_claim_fails():
    """Claiming letter A found Terry Adams (the A grid does not surface him) and
    lying about his date of birth."""
    run_dir = clone(6, "letterlie")
    mutate_answer(run_dir, "UK athletes (4): Gee Atherton (Mountainbike Downhill); "
                           "Rachel Atherton (Mountainbike Downhill); Sky Brown "
                           "(Surfing Competition / Skateboard Park); Zoe Backstedt "
                           "(Road Cycling). Career starts: Gee=2001, Rachel=2007, "
                           "Sky=2018, Zoe=—. Letter A shows Terry Adams: yes. Terry "
                           "Adams: BMX Flatland, United States, born May 5, 1990.")
    verdict = run_verifier(6, run_dir)
    assert not verdict["pass"]
    assert any("letter_a_claim" in e or "terry_dob" in e
               for e in verdict["evidence"] if e.startswith("FAIL"))


def test_t14_wrong_toggle_outcome_fails():
    """Claiming the Volare save removed a favorite (it must add one)."""
    run_dir = clone(14, "wrongtoggle")
    traj = json.loads((run_dir / "trajectory.json").read_text())
    answer = traj["final_answer"].replace("Added to your favorites",
                                         "Removed from your favorites")
    mutate_answer(run_dir, answer)
    verdict = run_verifier(14, run_dir)
    assert not verdict["pass"]
    assert any("film_toggle_outcome" in e
               for e in verdict["evidence"] if e.startswith("FAIL"))


def test_t2_era_lie_fails():
    """Claiming a fabricated era (the standfirst states the 90's/early 2000's)."""
    import re as _re
    run_dir = clone(2, "eralie")
    traj = json.loads((run_dir / "trajectory.json").read_text())
    answer = _re.sub(r"90[’']s and early 2000[’']?s[^.;]*", "1980s", traj["final_answer"])
    assert "1980s" in answer
    mutate_answer(run_dir, answer)
    verdict = run_verifier(2, run_dir)
    assert not verdict["pass"]
    assert any("era" in e for e in verdict["evidence"] if e.startswith("FAIL"))
