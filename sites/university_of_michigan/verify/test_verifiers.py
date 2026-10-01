#!/usr/bin/env python3
"""test_verifiers.py — adversarial contract tests for the university_of_michigan
verifier suite (r2 re-freeze; review branch orch/review/university_of_michigan,
contributor base orch/contribute/university_of_michigan @ 8fed65a6, the fix
round for review fd6adbe1).

Guarantees (run with pytest):
  * each honest fixture (from the reviewer's two independent r2 Playwright
    rounds on the review container wh-umich-review-r2, seed md5
    0492574f8c28ddc5b923294839d99cc0 — one deadlines row restored verbatim
    from upstream relative to the r1 seed) PASSES its verify_<n>.py;
  * every adversarial negative FAILS (zero false positives):
      - no-op trajectories (20),
      - answer-only shortcuts with no navigation (20),
      - wrong-answer trajectories (20, fabricated per question point),
      - stale-DB trajectories (all 10 stateful tasks: the DB delta is undone
        while the answer claims success),
      - read-only violations (all 10 read-only tasks get an injected write),
      - tampered packages (wrong task_id / off-site URL / cross-port URL /
        not-terminated / empty answer / pre-mutated seed),
      - task-specific confusions (T3/T10 seeded-section toggled OFF,
        T3 wrong section added, T16 single toggle / un-removed add, T17
        different program saved, T5/T15 wrong audience, T0/T7/T13 wrong
        section added, T1/T6/T11/T18 wrong event saved, T8/T9 wrong program
        saved, T2 FAFSA deadline confusion, T9 a-f-retained bio count, T4
        wrong funding foundation, T7 wrong LSA subject count, T13 wrong MATH
        course count, T14 wrong El Niño figure, T12 wrong binding plan).
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
EV = Path("/data/zhaoyang-user-projects/websyn/wh-umich-review-evidence")
FIXTURES = EV / "fixtures"
TMP = EV / "verify_runs" / "_pytest_tmp"
PY = sys.executable

TASK_IDS = [f"University of Michigan--{n}" for n in range(20)]
# stateful: the honest walk leaves a DB delta (r2: T3 adds Stark's second
# section 10712, T10 adds the ECON 102 first section 10942 — both
# re-anchored outside every seeded Backpack)
STATEFUL = [0, 1, 3, 5, 6, 7, 8, 9, 10, 11, 13, 15, 18]
# read-only: the honest walk leaves the DB byte-identical (incl. T16, whose
# re-anchored add+remove of the STATS 250 first section restores the seed,
# and T17, whose re-save of the already-saved Nursing program is a no-op)
READ_ONLY = [n for n in range(20) if n not in STATEFUL]


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
    """Replace the whole trajectory with a homepage-only no-op walk."""
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    base = traj.get("start_url", "http://localhost:46132/")
    step = {"idx": 0, "action": "navigate", "thought": "look around",
            "params": {}, "url": base, "url_after": base,
            "extracted_content": ""}
    for s in traj.get("steps", []):
        for key in ("screenshot_before", "screenshot_after"):
            s.pop(key, None)
    traj["steps"] = [step]
    p.write_text(json.dumps(traj, indent=2))


# ---------------------------------------------------------------- honest PASS --

@pytest.mark.parametrize("n", range(20))
def test_honest_fixture_passes(n):
    verdict = run_verifier(n, FIXTURES / str(n))
    assert verdict["pass"], f"University of Michigan--{n} honest fixture must PASS: {verdict['reason']}"


# ---------------------------------------------------------------- no-op FAIL --

@pytest.mark.parametrize("n", range(20))
def test_noop_fails(n):
    run_dir = clone(n, "noop")
    drop_nav(run_dir)
    mutate_answer(run_dir, "")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"University of Michigan--{n} no-op must FAIL"


# ------------------------------------------------- answer-only shortcut FAIL --

SHORTCUT_ANSWER = {
    0: "16 programs match 'Engineering'; the College of Engineering's first program "
       "alphabetically is Aerospace Engineering, offered by the College of Engineering. AEROSP "
       "lists 38 courses for Fall 2026. Alice's Backpack shows 3 classes.",
    1: "32 records match Great Lakes; 8 remain as Articles; the first Article alphabetically "
       "has first author Yeo, A. J. and issue year 2024-09. The first climate Article's Deep "
       "Blue handle is 2027.42/163954. Bob has 2 saved events in total.",
    2: "Winter 2026 classes begin Wednesday, Jan. 7 and the MLK Day entry is Monday, Jan. 19. "
       "Fall 2026 Backpack opens Wednesday, March 18 and the undergraduate registration window "
       "starts Monday, March 30. Spring/Summer 2026 lists 17 registration-deadline entries. "
       "The Michigan resident lower-division total budget is $40,194 and the FAFSA becomes "
       "available Oct. 1. Carol has 2 saved programs.",
    3: "2 instructors match Stark: Alexander Stark (Literature, Science, and the Arts) and "
       "Irina Aristarkhova (Art & Design). Alexander Stark teaches 6 sections for Fall 2026, "
       "the first subject CHEM. 239 instructors teach CHEM. Alice's Backpack has 3 classes "
       "after adding Stark's second section (10712).",
    4: "5 stories are tagged health and 4 arts-culture. The first arts-culture story is "
       "'Arts taking center stage at U-M throughout October' published 2026-09-25; the most "
       "recent health story is the same title. The foundation named among the $10M "
       "histotripsy center's funding sources is the Li Ka Shing Foundation. 4 Well-being "
       "events are listed and Lunchtime Yoga starts 2026-09-18. Dana has 1 saved event and "
       "1 saved program.",
    5: "1 building matches 'Union' (Student Life) and the Michigan Union's address is 530 "
       "STATE ST. 1 building matches 'league' and the Michigan League's address is 911 N. "
       "UNIVERSITY AVE. The Library/Museum category lists 14 buildings; the natural history "
       "museum is the Museum of Natural History, zip 48109. Confirmation: Thank you! Your "
       "information request has been received.",
    6: "15 Workshop / Seminar events match. The meditation events are Heartfulness Meditation "
       "and Learn to Meditate in 3 days. Heartfulness Meditation is at Virtual, presented by "
       "Information and Technology Services (ITS). 9 records match genomics. Carol has 2 "
       "saved events and 1 class in her Backpack.",
    7: "27 courses match 'writing'; 19 remain after narrowing to Literature, Science, and the "
       "Arts. ENGLISH 125 is 'Writing&Academic Inq' with 102 sections; the first section's class "
       "number is 11009 and instructor Margarita Maria Rodriguez Morales. Dana has 2 classes "
       "afterwards, and the LSA school page lists 16 course subjects.",
    8: "21 schools & colleges are listed, 19 on the Ann Arbor campus. Ross lists 2 programs, "
       "first Business; Stamps lists 2, first Art and Design; SMTD lists 16, first Composition "
       "— SMTD lists the most. Alice has 2 saved programs.",
    9: "The a-f tab shows 60 programs. After clearing the tab back to a-z, 15 programs match "
       "'bio'. Biopsychology, Cognition, and Neuroscience is offered by the College of "
       "Literature, Science, and the Arts (LSA), which lists 100 programs. 2 programs match "
       "psychology. Carol has 3 saved programs.",
    10: "23 records match machine learning; 13 remain as Theses; the first Thesis "
        "alphabetically is 'An Energy-Efficient CMOS Image Sensor with Embedded Machine "
        "Learning Algorithm' (2019). 23 records match jazz and the first jazz record's type "
        "is Thesis. Bob has 3 classes in his Backpack after adding the ECON 102 first "
        "section (10942).",
    11: "42 events are listed in total. 7 are Performances, including Holly Bowling (starts "
        "2026-10-02 20:00 at ARK Reserved). The Sporting Events are Ice Hockey vs Bowling "
        "Green and Field Hockey vs Iowa. Dana has 2 saved events in total.",
    12: "Fall 2026 classes begin Monday, Aug. 31; Thanksgiving break is Wednesday, Nov. 25 - "
        "Friday, Nov. 27; Commencement is Sunday, Dec. 20. Backpack opens Wednesday, March 18. "
        "Winter 2027 lists 9 academic-calendar entries and classes begin Wednesday, Jan. 13. "
        "Early Decision deadline Nov. 1 (decision By Dec. 24); Regular Decision deadline "
        "Feb. 1; Early Decision is binding. Bob has 2 classes in his Backpack.",
    13: "215 instructors teach MATH. The Saha match is Archishman Saha, who teaches 2 "
        "sections; the first section is MATH 115 'Calculus I', status Closed. Alice's "
        "Backpack has 3 classes afterwards, and the MATH subject lists 87 courses.",
    14: "The most recent story is 'Abuse and disability trap: 90% of incarcerated Michigan "
        "youth suffered prior abuse'. arts-culture lists 4 stories. 'Arts taking center "
        "stage' was published 2026-09-25 and the Michigan Arts Festival kicks off in October. "
        "El Niño variability has become nearly 40% stronger. The most recent health story is "
        "'Arts taking center stage at U-M throughout October'. Bob's first Backpack class is "
        "ECON 101 'Principles Econ I' taught by Adam Stevenson.",
    15: "23 buildings match the Athletic category. 2 buildings match 'museum'. The Museum of "
        "Natural History's address is 1105 N University Ave. and its category is "
        "Library/Museum. 24 buildings match Housing. Confirmation: Thank you! Your information "
        "request has been received.",
    16: "32 courses match 'data'. STATS 250 is 'Intr Stat&Data Anlys' with 66 sections; the "
        "first section's class number is 13492 and instructor Alicia Romero. 9 courses match "
        "psychology. After adding and removing the STATS 250 first section Dana has 1 class "
        "remaining.",
    17: "156 programs are listed in total. 1 program matches nursing, offered by the School "
        "of Nursing, which lists 1 program. 1 program matches pharmaceutical (Pharmaceutical "
        "Sciences). Carol has 2 saved programs in My U-M.",
    18: "The yoga search matches Lunchtime Yoga. It is a Well-being event starting "
        "2026-09-18 12:00, presented by Kinesiology Community Programs. The Sporting Events "
        "are Ice Hockey vs Bowling Green (location Ann Arbor, Mich.) and Field Hockey vs "
        "Iowa. Bob has 2 saved events in total.",
    19: "Fall 2025 classes begin Monday, Aug. 25 and the fall study break is Monday, Oct. 13 "
        "- Tuesday, Oct. 14. Winter 2026 classes begin Wednesday, Jan. 7. Winter 2027 has 9 "
        "academic-calendar entries. Michigan resident upper-division tuition & fees are "
        "$21,268 and the nonresident lower-division total budget is $88,394. Alice's first "
        "Backpack class is CHEM 125 'Gen Chem Lab I' taught by Alexander Stark, and she has "
        "1 saved event.",
}


@pytest.mark.parametrize("n", range(20))
def test_answer_only_shortcut_fails(n):
    """Correct answer, but the agent never navigated anywhere (memory recall)."""
    run_dir = clone(n, "shortcut")
    drop_nav(run_dir)
    mutate_answer(run_dir, SHORTCUT_ANSWER[n])
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"University of Michigan--{n} answer-only shortcut must FAIL"


# ------------------------------------------------------------ wrong answers --

WRONG_ANSWERS = {
    0: "12 programs match 'Engineering'; the College of Engineering's first program is "
       "Biomedical Engineering, offered by the School of Kinesiology. AEROSP lists 31 courses. "
       "Alice's Backpack shows 4 classes.",
    1: "28 records match Great Lakes; 5 Articles remain; the first Article's author is "
       "Anderson, E. J. (2023). The climate handle is 2027.42/999999. Bob has 3 saved events.",
    2: "Winter 2026 classes begin Monday, Jan. 12; MLK is Monday, Jan. 26. Fall 2026 Backpack "
       "opens Wednesday, March 25; the undergraduate window starts Monday, April 6. "
       "Spring/Summer 2026 lists 15 entries. The lower-division total is $38,000 and the "
       "FAFSA becomes available March 1. Carol has 3 saved programs.",
    3: "1 instructor matches Stark: Alexander Stark (Engineering). He teaches 4 sections, "
       "first subject PHYS. 300 instructors teach CHEM. Alice's Backpack has 2 classes after "
       "adding Stark's second section.",
    4: "6 health stories and 3 arts-culture. The first arts story is 'Bird-friendly mural "
       "takes flight' (2026-09-02). The foundation named among the histotripsy center's "
       "funding sources is the Gates Foundation. 3 Well-being events; Lunchtime Yoga starts "
       "2026-10-02. Dana has 2 saved events and 2 saved programs.",
    5: "2 buildings match 'Union' (Academic); the Michigan Union is at 900 SAINT STATE ST. "
       "2 buildings match 'league'; the Michigan League is at 511 N. UNIVERSITY AVE. The "
       "Library/Museum category lists 12 buildings and the natural history museum's zip is "
       "48104. Confirmation: your request was noted.",
    6: "12 Workshop / Seminar events. Only Heartfulness Meditation matches meditat. It is "
       "at the Michigan Union, presented by SMTD. 7 records match genomics. Carol has 3 "
       "saved events and 2 classes.",
    7: "25 courses match 'writing'; 17 in LSA. ENGLISH 125 is 'College Writing' with 98 "
       "sections; the first section is class 11223 taught by Thomas Walker. Dana ends with "
       "3 classes, and the LSA school page lists 14 course subjects.",
    8: "19 schools & colleges, 17 on the Ann Arbor campus. Ross lists 3 programs, first "
       "Integrated Business and Engineering; Stamps lists 3, first Interarts Performance; "
       "SMTD lists 12, first Jazz & Contemporary Improvisation — Stamps lists the most. "
       "Alice has 3 saved programs.",
    9: "The a-f tab shows 58 programs. 20 programs match 'bio'. BCN is offered by the College "
       "of Engineering, which lists 42 programs. 4 programs match psychology. Carol has 4 "
       "saved programs.",
    10: "20 records match machine learning; 10 Theses; the first is 'Machine Learning for "
        "Climate Science' (2021). 19 records match jazz; the first is an Article. Bob has "
        "4 classes after adding the ECON 102 first section.",
    11: "40 events in total; 5 Performances; Holly Bowling starts 2026-10-03 at Hill "
        "Auditorium. The Sporting Events are Ice Hockey vs Bowling Green and Michigan "
        "Stadium Tours. Dana has 3 saved events.",
    12: "Fall 2026 classes begin Wednesday, Aug. 26; Thanksgiving Nov. 24-26; Commencement "
        "Saturday, Dec. 19. Backpack opens Monday, March 23. Winter 2027 lists 11 entries; "
        "classes begin Monday, Jan. 18. ED deadline Nov. 15 (decision By Jan. 15); RD "
        "deadline March 1; Early Action is binding. Bob has 3 classes.",
    13: "212 instructors teach MATH. The Saha match is Bishal Saha with 6 sections; the "
        "first section is CHEM 260, status Open. Alice's Backpack has 4 classes, and the "
        "MATH subject lists 85 courses.",
    14: "The most recent story is 'Arts taking center stage'. arts-culture lists 6 stories. "
        "The arts story was published 2026-10-01 and the festival kicks off in November. "
        "El Niño variability has become nearly 60% stronger. Health's most recent is "
        "'Beyond hunger'. Bob's first Backpack class is EECS 183 taught by Monica Verma.",
    15: "20 Athletic buildings; 4 match 'museum'; the Museum of Natural History is at 1109 "
        "Geddes Ave., category Academic; 20 Housing buildings. Confirmation: request "
        "submitted.",
    16: "28 courses match 'data'. STATS 250 is 'Introduction to Statistics' with 60 "
        "sections; the first section is class 13001 taught by Elia Brenner. 12 courses "
        "match psychology. Dana has 0 classes remaining.",
    17: "150 programs total; 2 match nursing; the School of Nursing lists 3 programs; "
        "2 programs match pharmaceutical. Carol has 3 saved programs.",
    18: "2 yoga events: Lunchtime Yoga and Morning Yoga. Lunchtime Yoga is a Workshop / "
        "Seminar starting 2026-10-05, presented by URec. The Sporting Events are Ice Hockey "
        "vs Bowling Green at Yost Ice Arena and Field Hockey vs Iowa. Bob has 3 saved "
        "events.",
    19: "Fall 2025 classes begin Monday, Aug. 18; study break is Monday, Oct. 6 - Tuesday, "
        "Oct. 7. Winter 2026 classes begin Wednesday, Jan. 14. Winter 2027 has 11 academic "
        "entries. Upper-division tuition is $23,000; nonresident lower total is $85,000. "
        "Alice's first Backpack class is MATH 115 taught by Kenneth Ma, and she has 2 "
        "saved events.",
}


@pytest.mark.parametrize("n", range(20))
def test_wrong_answer_fails(n):
    run_dir = clone(n, "wrong")
    mutate_answer(run_dir, WRONG_ANSWERS[n])
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"University of Michigan--{n} wrong answer must FAIL"


# ------------------------------------------------------------------ stale DB --

@pytest.mark.parametrize("n", STATEFUL)
def test_stale_db_fails(n):
    """Stateful task: the DB delta is undone but the answer claims success."""
    run_dir = clone(n, "stale")
    shutil.copy(run_dir / "initial.db", run_dir / "after.db")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"University of Michigan--{n} stale DB must FAIL"


# -------------------------------------------------------- read-only violation --

@pytest.mark.parametrize("n", READ_ONLY)
def test_readonly_violation_fails(n):
    """Read-only task: an injected write in the after-state FAILs."""
    run_dir = clone(n, "dirty")
    mutate_db(run_dir, "after.db",
              "INSERT INTO saved_events (user_id, event_id, added_at) "
              "VALUES (1, (SELECT id FROM event_items LIMIT 1), '2026-09-30')")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"University of Michigan--{n} read-only violation must FAIL"


# ----------------------------------------------------------- tampered packages --

@pytest.mark.parametrize("n", range(20))
def test_wrong_task_id_fails(n):
    run_dir = clone(n, "wrongid")
    set_traj(run_dir, task_id="University of Michigan--99")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"University of Michigan--{n} wrong task_id must FAIL"


@pytest.mark.parametrize("n", range(20))
def test_offsite_url_fails(n):
    run_dir = clone(n, "offsite")
    set_traj(run_dir, start_url="https://umich.edu/")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"University of Michigan--{n} off-site start_url must FAIL"


@pytest.mark.parametrize("n", range(20))
def test_cross_port_url_fails(n):
    run_dir = clone(n, "crossport")
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    for s in traj.get("steps", []):
        if s.get("url_after", "").startswith("http://localhost:46132"):
            s["url_after"] = s["url_after"].replace("46132", "48132")
    p.write_text(json.dumps(traj, indent=2))
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"University of Michigan--{n} cross-port URL must FAIL"


@pytest.mark.parametrize("n", range(20))
def test_not_terminated_fails(n):
    run_dir = clone(n, "unterminated")
    set_traj(run_dir, terminated=False, termination_reason="max_steps")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"University of Michigan--{n} unterminated run must FAIL"


@pytest.mark.parametrize("n", range(20))
def test_empty_answer_fails(n):
    run_dir = clone(n, "emptyans")
    mutate_answer(run_dir, "")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"University of Michigan--{n} empty answer must FAIL"


@pytest.mark.parametrize("n", range(20))
def test_premutated_seed_fails(n):
    run_dir = clone(n, "badseed")
    mutate_db(run_dir, "initial.db",
              "INSERT INTO users (email, name, password_hash, joined) "
              "VALUES ('x@y.com', 'X', 'h', '2026-09-30')")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"University of Michigan--{n} pre-mutated seed must FAIL"


# ------------------------------------------------- task-specific confusions --

def test_t3_seeded_section_toggled_off_fails():
    """Agent toggles Alice's seeded CHEM 125-100 row off instead of adding the
    second section (leaves a -1 delta next to no allowed add)."""
    run_dir = clone(3, "toggleoff")
    mutate_db(run_dir, "after.db",
              "DELETE FROM backpack_items WHERE user_id=1 AND section_id="
              "(SELECT s.id FROM sections s JOIN courses c ON s.course_id=c.id "
              "WHERE c.subject='CHEM' AND c.number='125' AND s.section='100')")
    verdict = run_verifier(3, run_dir)
    assert not verdict["pass"], "T3 toggle-off must FAIL"


def test_t3_wrong_section_added_fails():
    """Agent adds Stark's first (seed-adjacent) section 10699 instead of the
    second section 10712: wrong row added."""
    run_dir = clone(3, "wrongsec")
    mutate_db(run_dir, "after.db",
              "UPDATE backpack_items SET section_id=866 WHERE user_id=1")
    verdict = run_verifier(3, run_dir)
    assert not verdict["pass"], "T3 wrong section added must FAIL"


def test_t10_seeded_section_toggled_off_fails():
    """Agent toggles Bob's seeded ECON 101-100 row off (wrong target)."""
    run_dir = clone(10, "toggleoff")
    mutate_db(run_dir, "after.db",
              "DELETE FROM backpack_items WHERE user_id=2 AND section_id="
              "(SELECT s.id FROM sections s JOIN courses c ON s.course_id=c.id "
              "WHERE c.subject='ECON' AND c.number='101' AND s.section='100')")
    verdict = run_verifier(10, run_dir)
    assert not verdict["pass"], "T10 toggle-off must FAIL"


def test_t16_wrong_entry_removed_fails():
    """Agent removes Dana's seeded SI 110 row (wrong entry) while claiming the
    add+remove flow — a -1 delta means the honest flow was not followed."""
    run_dir = clone(16, "sitetoggle")
    mutate_db(run_dir, "after.db",
              "DELETE FROM backpack_items WHERE user_id=4 AND section_id=4886")
    verdict = run_verifier(16, run_dir)
    assert not verdict["pass"], "T16 wrong-entry removal must FAIL"


def test_t16_unremoved_add_fails():
    """Agent adds the STATS 250 first section but never removes it (+1 delta)."""
    run_dir = clone(16, "unremoved")
    mutate_db(run_dir, "after.db",
              "INSERT INTO backpack_items (user_id, section_id, added_at) "
              "VALUES (4, 5418, '2026-09-30')")
    verdict = run_verifier(16, run_dir)
    assert not verdict["pass"], "T16 un-removed add must FAIL"


def test_t16_zero_answer_fails():
    run_dir = clone(16, "zeroans")
    mutate_answer(run_dir, SHORTCUT_ANSWER[16].replace(
        "Dana has 1 class remaining", "Dana has 0 classes remaining"))
    verdict = run_verifier(16, run_dir)
    assert not verdict["pass"], "T16 wrong remainder must FAIL"


def test_t17_different_program_saved_fails():
    run_dir = clone(17, "wrongprog")
    mutate_db(run_dir, "after.db",
              "INSERT INTO saved_programs (user_id, program_id, added_at) "
              "VALUES (3, (SELECT id FROM programs WHERE name='Biology'), '2026-09-30')")
    verdict = run_verifier(17, run_dir)
    assert not verdict["pass"], "T17 saving a different program must FAIL"


def test_t5_wrong_audience_fails():
    run_dir = clone(5, "wrongaud")
    mutate_db(run_dir, "after.db",
              "UPDATE info_requests SET audience='High School Student' "
              "WHERE email='alice.j@test.com'")
    verdict = run_verifier(5, run_dir)
    assert not verdict["pass"], "T5 wrong audience must FAIL"


def test_t15_wrong_audience_fails():
    run_dir = clone(15, "wrongaud")
    mutate_db(run_dir, "after.db",
              "UPDATE info_requests SET audience='Parent or Guardian' "
              "WHERE email='carol.d@test.com'")
    verdict = run_verifier(15, run_dir)
    assert not verdict["pass"], "T15 wrong audience must FAIL"


def test_t0_wrong_section_added_fails():
    run_dir = clone(0, "wrongsec")
    mutate_db(run_dir, "after.db",
              "UPDATE backpack_items SET section_id=105 WHERE user_id=1")
    verdict = run_verifier(0, run_dir)
    assert not verdict["pass"], "T0 wrong section added must FAIL"


def test_t4_wrong_foundation_fails():
    run_dir = clone(4, "wrongfound")
    mutate_answer(run_dir, SHORTCUT_ANSWER[4].replace("Li Ka Shing Foundation",
                                                      "Gates Foundation"))
    verdict = run_verifier(4, run_dir)
    assert not verdict["pass"], "T4 wrong funding foundation must FAIL"


def test_t7_wrong_lsa_subjects_fails():
    run_dir = clone(7, "wrongsub")
    mutate_answer(run_dir, SHORTCUT_ANSWER[7].replace("lists 16 course subjects",
                                                       "lists 14 course subjects"))
    verdict = run_verifier(7, run_dir)
    assert not verdict["pass"], "T7 wrong LSA subject count must FAIL"


def test_t13_wrong_math_courses_fails():
    run_dir = clone(13, "wrongmath")
    mutate_answer(run_dir, SHORTCUT_ANSWER[13].replace("MATH subject lists 87 courses",
                                                       "MATH subject lists 85 courses"))
    verdict = run_verifier(13, run_dir)
    assert not verdict["pass"], "T13 wrong MATH course count must FAIL"


def test_t9_bio_count_ambiguous_retained_tab_fails():
    """The old ambiguity: reporting the a-f-retained count (10) now FAILs —
    the re-anchored task uniquely expects 15 after clearing the tab."""
    run_dir = clone(9, "biorretained")
    mutate_answer(run_dir, SHORTCUT_ANSWER[9].replace("15 programs match",
                                                      "10 programs match"))
    verdict = run_verifier(9, run_dir)
    assert not verdict["pass"], "T9 a-f-retained bio count must FAIL"



def test_t7_wrong_section_added_fails():
    run_dir = clone(7, "wrongsec")
    mutate_db(run_dir, "after.db",
              "UPDATE backpack_items SET section_id=2231 WHERE user_id=4")
    verdict = run_verifier(7, run_dir)
    assert not verdict["pass"], "T7 wrong section added must FAIL"


def test_t13_wrong_section_added_fails():
    run_dir = clone(13, "wrongsec")
    mutate_db(run_dir, "after.db",
              "UPDATE backpack_items SET section_id=3175 WHERE user_id=1")
    verdict = run_verifier(13, run_dir)
    assert not verdict["pass"], "T13 wrong section added must FAIL"


def test_t1_wrong_event_saved_fails():
    run_dir = clone(1, "wrongevent")
    mutate_db(run_dir, "after.db",
              "UPDATE saved_events SET event_id=33 WHERE user_id=2")
    verdict = run_verifier(1, run_dir)
    assert not verdict["pass"], "T1 wrong event saved must FAIL"


def test_t6_wrong_event_saved_fails():
    run_dir = clone(6, "wrongevent")
    mutate_db(run_dir, "after.db",
              "UPDATE saved_events SET event_id=24 WHERE user_id=3")
    verdict = run_verifier(6, run_dir)
    assert not verdict["pass"], "T6 wrong event saved must FAIL"


def test_t11_wrong_event_saved_fails():
    run_dir = clone(11, "wrongevent")
    mutate_db(run_dir, "after.db",
              "UPDATE saved_events SET event_id=19 WHERE user_id=4")
    verdict = run_verifier(11, run_dir)
    assert not verdict["pass"], "T11 wrong event saved must FAIL"


def test_t18_wrong_event_saved_fails():
    run_dir = clone(18, "wrongevent")
    mutate_db(run_dir, "after.db",
              "UPDATE saved_events SET event_id=24 WHERE user_id=2")
    verdict = run_verifier(18, run_dir)
    assert not verdict["pass"], "T18 wrong event saved must FAIL"


def test_t8_wrong_program_saved_fails():
    run_dir = clone(8, "wrongprog")
    mutate_db(run_dir, "after.db",
              "UPDATE saved_programs SET program_id=74 WHERE user_id=1")
    verdict = run_verifier(8, run_dir)
    assert not verdict["pass"], "T8 wrong program saved must FAIL"


def test_t9_wrong_program_saved_fails():
    run_dir = clone(9, "wrongprog")
    mutate_db(run_dir, "after.db",
              "UPDATE saved_programs SET program_id=16 WHERE user_id=3")
    verdict = run_verifier(9, run_dir)
    assert not verdict["pass"], "T9 wrong program saved must FAIL"


def test_t2_fafsa_deadline_confusion_fails():
    """Answering 'March 1' (the FAFSA receipt deadline) is NOT the availability date."""
    run_dir = clone(2, "fafsaconf")
    mutate_answer(run_dir, SHORTCUT_ANSWER[2].replace(
        "the FAFSA becomes available Oct. 1", "the FAFSA becomes available March 1"))
    verdict = run_verifier(2, run_dir)
    assert not verdict["pass"], "T2 FAFSA deadline confusion must FAIL"


def test_t9_wrong_bio_count_fails():
    run_dir = clone(9, "biocount")
    mutate_answer(run_dir, SHORTCUT_ANSWER[9].replace("15 programs match 'bio'",
                                                      "20 programs match 'bio'"))
    verdict = run_verifier(9, run_dir)
    assert not verdict["pass"], "T9 wrong bio count must FAIL"


def test_t14_wrong_el_nino_figure_fails():
    run_dir = clone(14, "elnino")
    mutate_answer(run_dir, SHORTCUT_ANSWER[14].replace("nearly 40% stronger",
                                                       "nearly 60% stronger"))
    verdict = run_verifier(14, run_dir)
    assert not verdict["pass"], "T14 wrong El Niño figure must FAIL"


def test_t12_wrong_binding_plan_fails():
    run_dir = clone(12, "binding")
    mutate_answer(run_dir, SHORTCUT_ANSWER[12].replace("Early Decision is binding",
                                                       "Early Action is binding"))
    verdict = run_verifier(12, run_dir)
    assert not verdict["pass"], "T12 wrong binding plan must FAIL"
