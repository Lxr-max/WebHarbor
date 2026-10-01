#!/usr/bin/env python3
"""Deterministic verifier for University of Michigan--10 (university_of_michigan).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-umich-review-r2, seed md5
0492574f8c28ddc5b923294839d99cc0, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_10.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "University of Michigan--10"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # machine learning (23), Thesis (13), first Thesis ('An Energy-Efficient
    # CMOS Image Sensor with Embedded Machine Learning Algorithm', 2019);
    # jazz (23, first record type Thesis); bob login; r2 re-anchor: the ECON
    # 102 first section (class 10942 — outside Bob's seeded Backpack) added,
    # My U-M total.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/library\?q=machine\+learning",
        r"/library\?q=machine\+learning[^ ]*type=Thesis",
        r"/library/item/4ce0f3e6",
        r"/library\?q=jazz",
        r"/library/item/4c5372dd",
        r"/login",
        r"/courses/subject/ECON",
        r"/courses/class/10942",
        r"/myumich",
    ])
    check_answer_number(judge, answer, "ml_count", 23)
    check_answer_number(judge, answer, "ml_thesis_count", 13)
    check_answer_phrase(judge, answer, "ml_thesis_title", "CMOS Image Sensor")
    check_answer_number(judge, answer, "ml_thesis_year", 2019)
    check_answer_number(judge, answer, "jazz_count", 23)
    check_answer_phrase(judge, answer, "jazz_type", "Thesis")
    check_answer_number(judge, answer, "bob_backpack_total", 3)
    check_only_tables_changed(judge, initial, after, {"backpack_items"})
    check_rows_added(judge, initial, after, "backpack_items",
                     [[None, 2, 1467, "2026-09-30"]], "backpack_add_bob_econ102_10942")
    check_rows_removed(judge, initial, after, "backpack_items", [],
                     "no_rows_removed_backpack_items")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
