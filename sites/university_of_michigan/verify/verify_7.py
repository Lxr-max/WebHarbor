#!/usr/bin/env python3
"""Deterministic verifier for University of Michigan--7 (university_of_michigan).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-umich-review-r2, seed md5
0492574f8c28ddc5b923294839d99cc0, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_7.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "University of Michigan--7"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Courses 'writing' (27), LSA narrow (19), ENGLISH subject (ENGLISH 125
    # 'Writing&Academic Inq', 102 sections), first section class detail
    # (11009, Margarita Maria Rodriguez Morales), dana login + add, My U-M,
    # then (r2 deepening) the LSA school page course-subject count (16).
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/courses\?q=writing",
        r"/courses\?q=writing[^ ]*school=Literature",
        r"/courses/subject/ENGLISH",
        r"/courses/class/11009",
        r"/login",
        r"/myumich",
        r"/schools-colleges/lsa",
    ])
    check_answer_number(judge, answer, "writing_courses", 27)
    check_answer_number(judge, answer, "writing_lsa", 19)
    check_answer_phrase(judge, answer, "english125_title", "Writing&Academic Inq")
    check_answer_number(judge, answer, "english125_sections", 102)
    check_answer_number(judge, answer, "first_class_nbr", 11009)
    check_answer_phrase(judge, answer, "first_instructor", "Margarita Maria Rodriguez Morales")
    check_answer_number(judge, answer, "dana_backpack_total", 2)
    check_answer_number(judge, answer, "lsa_subjects", 16)
    check_only_tables_changed(judge, initial, after, {"backpack_items"})
    check_rows_added(judge, initial, after, "backpack_items",
                     [[None, 4, 2230, "2026-09-30"]], "backpack_add_dana_english125")
    check_rows_removed(judge, initial, after, "backpack_items", [],
                     "no_rows_removed_backpack_items")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
