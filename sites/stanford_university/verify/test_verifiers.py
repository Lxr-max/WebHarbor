#!/usr/bin/env python3
"""test_verifiers.py — adversarial contract tests for the stanford_university
verifier suite (review branch orch/review/stanford_university, r2 fix base
orch/contribute/stanford_university @ 77e3fa7e, r1 contract 43eef816).

Guarantees (run with pytest):
  * each honest fixture (from the reviewer's two independent Playwright rounds
    on the r2 review container wh-stanford-r2, seed sha256
    65c57cd498ee5b4af55a81ee07dd15c131e5d2b94252cfb5ffdddab13aa71dd1, md5
    c44be3f0be7aafde9e627bf408e6dc49) PASSES its verify_<n>.py — both
    rounds (40 fixtures);
  * every adversarial negative FAILS (zero false positives):
      - no-op trajectories (20): homepage only, empty answer, clean DB;
      - answer-only shortcuts (20): the full correct answer with NO navigation
        (memory-recall shortcut);
      - wrong-answer trajectories (20): honest navigation, fabricated answers
        per question point;
      - stale-DB trajectories (9 stateful tasks): the DB delta is undone while
        the answer claims success;
      - read-only violations (11 read-only tasks): an injected planner write;
      - tampered packages: wrong task_id / off-site URL / cross-port URL /
        not-terminated / empty answer / pre-mutated seed;
      - task-specific confusions: T0 wrong count, T2 wrong first course,
        T3 wrong ADL leader, T9 wrong removal, T13 wrong final planner,
        T17 leftover planner row, T18 wrong save set.
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
EV = Path("/data/zhaoyang-user-projects/websyn/wh-stanford-review-evidence")
FIXTURES_R1 = EV / "runs_r2a"
FIXTURES_R2 = EV / "runs_r2b"
TMP = EV / "verify_runs" / "_pytest_tmp"
PY = sys.executable

TASK_IDS = [f"Stanford University--{n}" for n in range(20)]
# stateful: the honest walk leaves a DB delta
STATEFUL = [0, 9, 10, 12, 13, 14, 16, 18, 19]
# read-only: the honest walk leaves the DB row-identical (T17 adds CS103 and
# removes it again, so its honest end state is also row-identical)
READ_ONLY = [1, 2, 3, 4, 5, 6, 7, 8, 11, 15, 17]


def run_verifier(n: int, run_dir: Path):
    proc = subprocess.run(
        [PY, str(VERIFY / f"verify_{n}.py"), "--run_dir", str(run_dir)],
        capture_output=True, text=True, timeout=180)
    try:
        verdict = json.loads(proc.stdout)
    except json.JSONDecodeError:
        verdict = {"pass": False, "reason": proc.stdout[-300:] or proc.stderr[-300:]}
    return verdict


# ─────────────────────────────────────────────────────────── helpers ──────

def clone(run_dir: Path, dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(run_dir, dest)
    return dest


def edit_trajectory(run_dir: Path, **changes):
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    traj.update(changes)
    p.write_text(json.dumps(traj, indent=1))


def set_answer(run_dir: Path, answer: str):
    edit_trajectory(run_dir, final_answer=answer)


def strip_navigation(run_dir: Path):
    """Keep only the homepage step (answer-only shortcut)."""
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    steps = [s for s in traj.get("steps", [])
             if str(s.get("url", "")).endswith("/")
             and s.get("action") == "navigate"]
    traj["steps"] = steps
    p.write_text(json.dumps(traj, indent=1))


def db_path(run_dir: Path, which: str) -> Path:
    return run_dir / f"{which}.db"


def mutate_db(run_dir: Path, which: str, sql: str, args=()):
    p = db_path(run_dir, which)
    con = sqlite3.connect(p)
    con.execute(sql, args)
    con.commit()
    con.close()


# ──────────────────────────────────────────────────── honest fixtures ─────

@pytest.mark.parametrize("n", range(20))
def test_honest_r1(n):
    verdict = run_verifier(n, FIXTURES_R1 / str(n))
    assert verdict["pass"], verdict["reason"]


@pytest.mark.parametrize("n", range(20))
def test_honest_r2(n):
    verdict = run_verifier(n, FIXTURES_R2 / str(n))
    assert verdict["pass"], verdict["reason"]


# ────────────────────────────────────────────────────────── negatives ─────

HONEST_ANSWERS = {
    0: ("CS229 Machine Learning: units 3-4; grading basis ROP - Letter or "
        "Credit/No Credit; terms Autumn, Spring, Summer, Winter. CS Graduate "
        "filter: 40 courses. Planner: 4 courses (CS106A, MATH51, PHYSICS41, "
        "CS229), total 15.0–18.0 units."),
    1: ("School of Engineering lists 14 departments. Aeronautics and "
        "Astronautics subject code AA; BS minimum units 100; MS minimum units "
        "45; difference 55. Management Science and Engineering subject code "
        "MS&E; first course MS&E103 Fundamentals of Agentic Systems, 3 units; "
        "5 degree programs; MS program lists 2 requirement groups."),
    2: ("EE Graduate Winter: 6 courses; first course EE214B Advanced "
        "Integrated Circuit Design, 3 units. CS106A Programming Methodology "
        "satisfies WAYS Formal Reasoning (FR), grading ROP - Letter or "
        "Credit/No Credit. Mathematics + FR: 28 courses match."),
    3: ("Fei-Fei Li: Sequoia Capital Professor; department Computer Science; "
        "research interest Machine Learning. Mathematics: 58 profiles; first "
        "Mohammed Abouzaid, Professor of Mathematics. ADL search returned 1 "
        "profile: Juan Alonso, Coffman Professor. Psychology: 54 profiles."),
    4: ("Economics BA: offered by Economics; minimum units 80; first sentence "
        "Develop a foundational understanding of the economic aspects. "
        "Department subject code ECON; MA minimum units 45. CS Minor minimum "
        "units 26. PhD Minor type: 41 match; first Aeronautics & Astro (PMn)."),
    5: ("CS BS minimum units 93 with 8 requirement groups; CS MS 45; "
        "difference 48. CS Minor 26 vs CS PhD 135; difference 109. CS "
        "department lists 5 degree programs; CS PhD minimum units 135; "
        "CS MS lists 8 requirement groups."),
    6: ("University News category: 43 stories. MacArthur search: 3 stories. "
        "Song Lin, Chemistry, award $800,000 over five years, September 29, "
        "2026, writer Adam Hadhazy. Health & Medicine topic: 22 stories; "
        "newest Why changing California's school menus may be difficult, "
        "September 28, 2026, Erin Digitale. Siebel Scholars: 18 Stanford "
        "students named Siebel Scholars, September 21, 2026, writer Alex "
        "Kekauoha, main topic Awards & Honors."),
    7: ("R&S + Health & Medicine: 20 stories; newest Why changing California's "
        "school menus may be difficult, September 28, 2026, Erin Digitale. "
        "Newest overall: Stanford chemist Song Lin receives MacArthur "
        "Fellowship, September 29, 2026. Democracy search: 10; newest Lara "
        "Tiedens appointed as CASBS director, Institutional News. On Campus: "
        "42; newest President Levin and student leaders on the year ahead, "
        "main topic Events. Student Experience category lists 32 stories."),
    8: ("Lecture search: 29 events. Hoover Institution George P. Shultz "
        "Memorial Lecture Series: 2026-10-01, Hoover Institution - George P. "
        "Shultz Building, Ticketed. November 2026: 60 events; first Stanford "
        "Energy Seminar at Shriram Center. Upcoming + seminar: 91 events; "
        "first one dated 2026-10-01. Concert search: 36 events; first "
        "Stanford Medicine Orchestra with violinist Stella Chen., address "
        "471 Lagunita Drive, Stanford, CA 94305."),
    9: ("Saved events: Trust and Safety Research Conference. December 2026: "
        "60 events; first Salvatierra Lecture. After saving: 2 saved events. "
        "After removing the research conference: 1, Salvatierra Lecture."),
    10: ("Autumn: instruction begins September 22 (Tue); Preliminary Study "
         "List deadline September 22 (Tue, 5 p.m.), late fee $200. Winter "
         "first day January 4 (Mon). Dana planner: BIO102, 4.0 units; after "
         "the swap: MATH51, 5.0 units."),
    11: ("Robin Li and Melissa Ma Science Library: (650) 723-1528, 376 Lomita "
         "Drive. Green Library: Sunday 12p-12a, Friday 8a-12a, (650) 723-1493. "
         "Music Library: 650-723-1211. East Asia Library: Lathrop Library, "
         "Chinese studies. Philosophy search: 1 match; Tanner Memorial "
         "Library of Philosophy, location Main Quad, first floor of Building "
         "90, Room 91F."),
    12: ("REA standard deadline November 1; RD January 5; fee $100; midyear "
         "transcript due February 15. Estimator 120000/2: No tuition "
         "responsibility; Room and board responsibility applies. Sam Rivera "
         "planner: 1 course, 5.0 units."),
    13: ("Bob planner: ECON1 5 units, PSYCH1 5 units, total 10.0. After the "
         "neuroscience swap: 2 courses, 9.0. Final planner: BIO102 and "
         "PHYSICS41, total 8.0."),
    14: ("BIO102: grading ROP - Letter or Credit/No Credit, offered Winter. "
         "Jordan Vale planner: 2 courses, total 9.0 units."),
    15: ("Chemistry subject code CHEM; catalog lists 42 courses. CHEM263 "
         "Machine Learning for Chemical and Dynamical Data: 3 units, "
         "Graduate. Chemistry faculty: 51; first Ayatollahi Mehrgardi, "
         "Physical Science Research Scientist. Chemistry PhD: 135 units."),
    16: ("Newest story: Stanford chemist Song Lin receives MacArthur "
         "Fellowship, featured unit Stanford School of Humanities & Sciences, "
         "main topic Awards & Honors. First upcoming event: Climber Coffee, "
         "2026-10-01, Arrillaga Outdoor Education & Recreation Center. Saved "
         "list shows 2 events. Autumn instruction begins September 22 (Tue). "
         "Summer: 44 entries. Libraries classics search: 1 match, Classics "
         "Library, (650) 723-0479."),
    17: ("FR WAYS: 90 courses; with CS subject: 11. Lowest course number "
         "CS103 Mathematical Foundations of Computing, 3-5 units, ROP. Carol "
         "planner: CS103, 3.0–5.0 units; after removal the planner is empty. "
         "FR + CS + Winter: 8 matches; first course CS103."),
    18: ("Carol saved event: Lunchtime Curator Talk | JANE!, 2026-10-01. "
         "After saving the Multifaith Dinner: 2. After removing the curator "
         "talk: 1, Multifaith Dinner. Final count: 2."),
    19: ("CS faculty: 144 profiles; first Sara Achour, Assistant Professor of "
         "Computer Science and of Electrical Engineering. Alice planner: "
         "CS106A 3-5, MATH51 5, PHYSICS41 4, total 12.0–14.0. After adding: "
         "total 15.0–19.0."),
}

WRONG_ANSWERS = {
    0: "CS229 units 1-2, grading S/NC, terms Autumn only, CS Graduate count 77, planner 3 courses total 11.0.",
    1: "Engineering has 20 departments, AA subject code AERO, BS 120 units, MS 60, difference 60, MSE subject code MGMT, first course MS&E100 Introduction, 4 units, 7 programs, MS has 5 requirement groups.",
    2: "EE count 12, first course EE101A Circuits I 4 units, CS106A satisfies AQR with RSN grading, MATH+FR 12 courses.",
    3: "Fei-Fei Li is a Consulting Professor in Biology interested in quantum computing; Mathematics has 40 profiles, first Ravi Vakil; ADL search found 4 profiles and the leader is Mykel Kochenderfer; Psychology has 30.",
    4: "Economics BA 90 units from the Political Science department, code POLS; MA 50; CS Minor 20; PhD Minor 30 matches, first Anthropology (PMn).",
    5: "CS BS 100 units with 5 requirement groups, CS MS 50 difference 50, CS Minor 20 vs CS PhD 150 difference 130, CS department lists 8 programs, CS PhD 120 units, CS MS has 5 requirement groups.",
    6: "University News: 50 stories. MacArthur search found 5 stories. Song Lin, Biology, award $500,000 over three years, October 1 2026, writer Jill Watson. H&M topic: 15 stories, newest dated October 5 by Bob Smith. Siebel story dated October 5, writer Jane Doe, topic Research.",
    7: "R&S + H&M: 15 stories, newest about solar panels October 1, writer Bob Smith; newest overall a football story October 10; democracy search 5, newest about elections; On Campus 30, newest about dining halls, topic Research; Student Experience lists 20 stories.",
    8: "Lecture search: 15 events. Hoover lecture on 2026-11-01 at Green Library, Free. November 2026: 40 events, first a poetry reading at the Music building. Upcoming seminar: 50 events, first dated 2026-11-15. Concert search: 10 events, first event at 450 Serra Mall.",
    9: "Saved events: Rock Concert. December: 30 events, first Winter Gala. After saving: 3 saved. After removing: 0 saved.",
    10: "Autumn instruction begins October 1 (Thu); Preliminary Study List October 5, late fee $100. Winter first day February 1. Dana planner had MATH51 at 5 units; final: BIO102 at 4 units.",
    11: "Robin Li library: (650) 723-9999 at 450 Serra Mall. Green: Sunday 9a-5p, Friday closed, phone (650) 555-1212. Music: 650-999-9999. East Asia at Green Library, subject French studies. Philosophy search: 2 matches; the library is at 450 Serra Mall Building 110.",
    12: "REA deadline December 15; RD February 15; fee $90; midyear due March 1. Estimator: full tuition responsibility, no room responsibility. Planner: 2 courses, 10 units.",
    13: "Bob planner: ECON1 4 units, PSYCH1 3 units, total 7.0. After swap: 3 courses 12.0. Final: BIO102 and PSYCH1, total 9.0.",
    14: "BIO102 grading S/NC offered Spring. Planner: 3 courses total 12.0.",
    15: "Chemistry code CHM; catalog 50 courses. CHEM263: 4 units, Undergraduate. Chemistry faculty 40; first John Smith, Professor. PhD 120 units.",
    16: "Newest story features the School of Engineering, topic Research. First upcoming event: Faculty Senate, 2026-11-01, at Green Library. Saved list shows 3 events. Autumn begins October 1. Summer: 30 entries. Classics search: 5 matches, first phone (650) 555-1234.",
    17: "FR WAYS 60 courses, CS 9 of them. Lowest CS369, 4 units, S/NC grading. Carol planner keeps CS103 with 6 units. FR+CS+Winter: 5 matches, first CS106A.",
    18: "Carol saved the Multifaith Dinner on 2026-11-02. After saves: 3 events. After removal: 2 events, Multifaith Dinner and curator talk. Final count: 1.",
    19: "CS faculty: 120; first John Mitchell, Professor. Alice planner: CS106A, MATH51, total 10.0. New total: 13.0.",
}


@pytest.fixture(scope="session", autouse=True)
def _tmpdir():
    TMP.mkdir(parents=True, exist_ok=True)
    yield
    shutil.rmtree(TMP, ignore_errors=True)


@pytest.mark.parametrize("n", range(20))
def test_noop_fails(n):
    d = clone(FIXTURES_R1 / str(n), TMP / f"noop_{n}")
    edit_trajectory(d, steps=[], final_answer="")
    verdict = run_verifier(n, d)
    assert not verdict["pass"]


@pytest.mark.parametrize("n", range(20))
def test_answer_only_shortcut_fails(n):
    d = clone(FIXTURES_R1 / str(n), TMP / f"shortcut_{n}")
    strip_navigation(d)
    set_answer(d, HONEST_ANSWERS[n])
    verdict = run_verifier(n, d)
    assert not verdict["pass"], "correct answer with no navigation must FAIL"


@pytest.mark.parametrize("n", range(20))
def test_wrong_answer_fails(n):
    d = clone(FIXTURES_R1 / str(n), TMP / f"wrong_{n}")
    set_answer(d, WRONG_ANSWERS[n])
    verdict = run_verifier(n, d)
    assert not verdict["pass"]


@pytest.mark.parametrize("n", STATEFUL)
def test_stale_db_fails(n):
    d = clone(FIXTURES_R1 / str(n), TMP / f"stale_{n}")
    # undo the DB delta while the answer claims success
    shutil.copy(d / "initial.db", d / "after.db")
    verdict = run_verifier(n, d)
    assert not verdict["pass"], "self-reported success with unchanged DB must FAIL"


@pytest.mark.parametrize("n", READ_ONLY)
def test_readonly_violation_fails(n):
    d = clone(FIXTURES_R1 / str(n), TMP / f"readonly_{n}")
    mutate_db(d, "after",
              "INSERT INTO planned_courses (user_id, course_code, position, added_at) "
              "VALUES (1, 'CS106A', 99, '2026-09-30')")
    verdict = run_verifier(n, d)
    assert not verdict["pass"], "read-only task with an injected write must FAIL"


@pytest.mark.parametrize("n", range(20))
def test_tampered_task_id_fails(n):
    d = clone(FIXTURES_R1 / str(n), TMP / f"tid_{n}")
    edit_trajectory(d, task_id="Stanford University--99")
    verdict = run_verifier(n, d)
    assert not verdict["pass"]


@pytest.mark.parametrize("n", range(20))
def test_offsite_url_fails(n):
    d = clone(FIXTURES_R1 / str(n), TMP / f"offsite_{n}")
    traj = json.loads((d / "trajectory.json").read_text())
    traj["steps"][0]["url"] = "https://example.org/"
    traj["steps"][0]["url_after"] = "https://example.org/"
    (d / "trajectory.json").write_text(json.dumps(traj, indent=1))
    verdict = run_verifier(n, d)
    assert not verdict["pass"]


@pytest.mark.parametrize("n", range(20))
def test_cross_port_url_fails(n):
    d = clone(FIXTURES_R1 / str(n), TMP / f"crossport_{n}")
    traj = json.loads((d / "trajectory.json").read_text())
    traj["steps"][0]["url"] = "http://localhost:48133/"
    traj["steps"][0]["url_after"] = "http://localhost:48133/"
    (d / "trajectory.json").write_text(json.dumps(traj, indent=1))
    verdict = run_verifier(n, d)
    assert not verdict["pass"]


@pytest.mark.parametrize("n", range(20))
def test_unterminated_fails(n):
    d = clone(FIXTURES_R1 / str(n), TMP / f"unterm_{n}")
    edit_trajectory(d, terminated=False, termination_reason="")
    verdict = run_verifier(n, d)
    assert not verdict["pass"]


@pytest.mark.parametrize("n", range(20))
def test_premutated_seed_fails(n):
    d = clone(FIXTURES_R1 / str(n), TMP / f"premut_{n}")
    mutate_db(d, "initial",
              "INSERT INTO planned_courses (user_id, course_code, position, added_at) "
              "VALUES (3, 'CS103', 7, '2026-01-01')")
    mutate_db(d, "after",
              "INSERT INTO planned_courses (user_id, course_code, position, added_at) "
              "VALUES (3, 'CS103', 7, '2026-01-01')")
    verdict = run_verifier(n, d)
    assert not verdict["pass"], "run graded against a pre-mutated seed must FAIL"


# ──────────────────────────────────────────── task-specific confusions ─────

def test_t0_wrong_grad_count_fails():
    d = clone(FIXTURES_R1 / "0", TMP / "conf0")
    # the r1 substring-filter count (77) must now FAIL: exact match lists 40
    set_answer(d, HONEST_ANSWERS[0].replace("40 courses", "77 courses"))
    verdict = run_verifier(0, d)
    assert not verdict["pass"]


def test_t0_wrong_planner_total_fails():
    d = clone(FIXTURES_R1 / "0", TMP / "conf0b")
    set_answer(d, HONEST_ANSWERS[0].replace("15.0–18.0", "12.0–14.0"))
    verdict = run_verifier(0, d)
    assert not verdict["pass"]


def test_t2_wrong_first_course_fails():
    d = clone(FIXTURES_R1 / "2", TMP / "conf2")
    # the r1 substring-filter first row (EE101A, an undergraduate course)
    # must now FAIL: the exact-match first graduate course is EE214B
    set_answer(d, HONEST_ANSWERS[2].replace("EE214B Advanced Integrated Circuit Design",
                                           "EE101A Circuits I"))
    verdict = run_verifier(2, d)
    assert not verdict["pass"]


def test_t2_math_fr_wrong_count_fails():
    d = clone(FIXTURES_R1 / "2", TMP / "conf2b")
    set_answer(d, HONEST_ANSWERS[2].replace("28 courses match", "12 courses match"))
    verdict = run_verifier(2, d)
    assert not verdict["pass"]


def test_t3_wrong_adl_leader_fails():
    d = clone(FIXTURES_R1 / "3", TMP / "conf3")
    set_answer(d, HONEST_ANSWERS[3].replace("Juan Alonso", "Mykel Kochenderfer"))
    verdict = run_verifier(3, d)
    assert not verdict["pass"]


def test_t9_wrong_removal_fails():
    d = clone(FIXTURES_R1 / "9", TMP / "conf9")
    set_answer(d, HONEST_ANSWERS[9].replace("1, Salvatierra Lecture", "2, both events"))
    verdict = run_verifier(9, d)
    assert not verdict["pass"]


def test_t9_removed_wrong_event_db_fails():
    d = clone(FIXTURES_R1 / "9", TMP / "conf9b")
    # DB claims the Salvatierra (not the conference) was removed
    mutate_db(d, "after", "DELETE FROM saved_events WHERE event_eid = 53728866418041")
    verdict = run_verifier(9, d)
    assert not verdict["pass"]


def test_t13_wrong_final_planner_fails():
    d = clone(FIXTURES_R1 / "13", TMP / "conf13")
    set_answer(d, HONEST_ANSWERS[13].replace("BIO102 and PHYSICS41", "PSYCH1 and ECON1"))
    verdict = run_verifier(13, d)
    assert not verdict["pass"]


def test_t17_leftover_planner_row_fails():
    d = clone(FIXTURES_R1 / "17", TMP / "conf17")
    # the honest end state is row-identical; a leftover CS103 row must FAIL
    mutate_db(d, "after",
              "INSERT INTO planned_courses (user_id, course_code, position, added_at) "
              "VALUES (3, 'CS103', 1, '2026-09-30')")
    verdict = run_verifier(17, d)
    assert not verdict["pass"]


def test_t18_wrong_save_set_fails():
    d = clone(FIXTURES_R1 / "18", TMP / "conf18")
    # a confused run that saves/removes the wrong set: no "2" token anywhere
    set_answer(d, "Carol saved event: Lunchtime Curator Talk | JANE!, 2026-10-01. "
                  "Multifaith Dinner saved; after saving there are 3 saved events. "
                  "After removing the curator talk: 1 remains, Multifaith Dinner. "
                  "Final count of saved events: 1.")
    verdict = run_verifier(18, d)
    assert not verdict["pass"]


def test_t18_missing_third_save_fails():
    d = clone(FIXTURES_R1 / "18", TMP / "conf18b")
    mutate_db(d, "after", "DELETE FROM saved_events WHERE event_eid = 53870497268780")
    verdict = run_verifier(18, d)
    assert not verdict["pass"]


def test_t11_philosophy_wrong_location_fails():
    d = clone(FIXTURES_R1 / "11", TMP / "conf11")
    set_answer(d, HONEST_ANSWERS[11].replace(
        "Main Quad, first floor of Building 90, Room 91F.",
        "450 Serra Mall, Building 110."))
    verdict = run_verifier(11, d)
    assert not verdict["pass"], "a wrong location for the Tanner record must FAIL"
