#!/usr/bin/env python3
"""Deterministic verifier for University of Michigan--13 (university_of_michigan).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-umich-review-r2, seed md5
0492574f8c28ddc5b923294839d99cc0, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_13.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "University of Michigan--13"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # MATH filter (215), Saha within MATH (Archishman Saha), profile (2
    # sections), first section class detail (MATH 115-008 'Calculus I',
    # Closed), alice login + add, My U-M total, then (r2 deepening) the MATH
    # subject course count in the course catalog (87).
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/faculty\?[^ ]*subject=MATH",
        r"/faculty\?q=Saha[^ ]*subject=MATH",
        r"/faculty/241\b",
        r"/courses/class/20116",
        r"/login",
        r"/myumich",
        r"/courses/subject/MATH",
    ])
    check_answer_number(judge, answer, "math_instructors", 215)
    check_answer_phrase(judge, answer, "saha_name", "Archishman Saha")
    check_answer_number(judge, answer, "saha_sections", 2)
    check_answer_phrase(judge, answer, "saha_first_title", "Calculus I")
    check_answer_phrase(judge, answer, "saha_first_status", "Closed")
    check_answer_number(judge, answer, "alice_backpack_total", 3)
    check_answer_number(judge, answer, "math_courses", 87)
    check_only_tables_changed(judge, initial, after, {"backpack_items"})
    check_rows_added(judge, initial, after, "backpack_items",
                     [[None, 1, 3174, "2026-09-30"]], "backpack_add_alice_math115_008")
    check_rows_removed(judge, initial, after, "backpack_items", [],
                     "no_rows_removed_backpack_items")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
