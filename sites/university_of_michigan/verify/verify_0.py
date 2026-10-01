#!/usr/bin/env python3
"""Deterministic verifier for University of Michigan--0 (university_of_michigan).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-umich-review, seed md5
3f5e930aa820d1b62309ec3feeb4536b, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_0.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_number, check_answer_number_absent, check_answer_number_any,
    check_answer_ordered, check_answer_phrase, check_answer_price,
    check_answer_regex, check_answer_zero_or_phrase, check_read_only,
    check_rows_added, check_rows_removed, check_only_tables_changed,
    check_screenshots, check_seed_contract, check_trajectory_identity,
    check_visited_all, check_visited_any, check_visited_path, final_answer,
    run_verifier,
)

TASK_ID = "University of Michigan--0"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Programs 'Engineering' search (16), CoE narrow (first: Aerospace
    # Engineering), school page, AEROSP subject (38 courses), alice login,
    # first section (AEROSP 200-001, class 24649) added to Backpack, My U-M.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/programs\?q=Engineering",
        r"/programs\?q=Engineering&school=College",
        r"/programs/2\b",
        r"/schools-colleges/engineering",
        r"/courses/subject/AEROSP",
        r"/login",
        r"/courses/class/24649",
        r"/myumich",
    ])
    check_answer_number(judge, answer, "eng_programs", 16)
    check_answer_phrase(judge, answer, "coe_first_program", "Aerospace Engineering")
    check_answer_phrase(judge, answer, "school_full_name", "College of Engineering")
    check_answer_number(judge, answer, "aerosp_courses", 38)
    check_answer_number(judge, answer, "alice_backpack_total", 3)
    check_only_tables_changed(judge, initial, after, {"backpack_items"})
    check_rows_added(judge, initial, after, "backpack_items",
                     [[None, 1, 104, "2026-09-30"]], "backpack_add_alice_aerosp200")
    check_rows_removed(judge, initial, after, "backpack_items", [],
                     "no_rows_removed_backpack_items")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
