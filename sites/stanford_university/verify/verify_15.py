#!/usr/bin/env python3
"""Deterministic verifier for Stanford University--15.

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-stanford-review, seed
sha256 40897e025003956e34f418eb213d7ea786775d342cabcbeba560b5767059d65c, with
every hardcoded fact cross-checked against the frozen seed database) — never
read from tasks.jsonl.
Usage: python3 verify_15.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_number, check_answer_number_absent, check_answer_number_any,
    check_answer_ordered, check_answer_phrase, check_answer_price,
    check_answer_range, check_answer_regex, check_answer_zero_or_phrase,
    check_read_only, check_rows_added, check_rows_changed, check_rows_removed,
    check_only_tables_changed, check_screenshots, check_seed_contract,
    check_trajectory_identity, check_visited_all, check_visited_any,
    check_visited_path, final_answer, run_verifier,
)

TASK_ID = "Stanford University--15"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Chemistry dept (subject CHEM) -> catalog link (42 Chemistry courses)
    # -> machine learning for chemical search -> CHEM263 (3 units, Graduate)
    # -> Chemistry faculty (51, first alphabetically Masoud Ayatollahi
    # Mehrgardi, Physical Science Research Scientist, Chemistry) ->
    # Chemistry PhD program (135 units).
    check_visited_all(judge, traj, "nav_surfaces", [
        r"q=Chemistry&school=",
        r"/departments/CHEMISTRY",
        r"/courses\?dept=CHEMISTRY",
        r"q=machine\+learning\+for\+chemical",
        r"/courses/CHEM263",
        r"dept=Chemistry",
        r"/programs/CHEM-PHD",
    ])
    check_answer_phrase(judge, answer, "chem_subject_code", "CHEM")
    check_answer_number(judge, answer, "chem_course_count", 42)
    check_answer_phrase(judge, answer, "chem263_code", "CHEM263")
    check_answer_number(judge, answer, "chem263_units", 3)
    check_answer_phrase(judge, answer, "chem263_career", "Graduate")
    check_answer_number(judge, answer, "chem_faculty_count", 51)
    check_answer_phrase(judge, answer, "chem_first_name", "Ayatollahi Mehrgardi")
    check_answer_phrase(judge, answer, "chem_first_title", "Physical Science Research Scientist")
    check_answer_number(judge, answer, "chem_phd_min_units", 135)
    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
