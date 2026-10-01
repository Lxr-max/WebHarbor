#!/usr/bin/env python3
"""Deterministic verifier for University of Michigan--3 (university_of_michigan).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-umich-review-r2, seed md5
0492574f8c28ddc5b923294839d99cc0, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_3.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "University of Michigan--3"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Stark search (2: Alexander Stark LSA, Irina Aristarkhova Art & Design),
    # Stark profile (6 sections, first subject CHEM), CHEM filter (239),
    # alice login, Stark's SECOND section (CHEM 125-200, class 10712 — r2
    # re-anchor: outside every seeded Backpack) added to the Backpack, My U-M.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/faculty\?q=Stark",
        r"/faculty/89\b",
        r"/faculty\?[^ ]*subject=CHEM",
        r"/login",
        r"/courses/class/10712",
        r"/myumich",
    ])
    check_answer_number(judge, answer, "stark_matches", 2)
    check_answer_count_at_least(judge, answer, "stark_names",
                                 ["Alexander Stark", "Irina Aristarkhova"], 1)
    check_answer_count_at_least(judge, answer, "stark_schools",
                                 ["Literature, Science, and the Arts", "LSA",
                                  "Art & Design", "Art and Design"], 2)
    check_answer_number(judge, answer, "stark_sections", 6)
    check_answer_phrase(judge, answer, "stark_first_subject", "CHEM")
    check_answer_number(judge, answer, "chem_instructors", 239)
    check_answer_number(judge, answer, "alice_backpack_total", 3)
    check_only_tables_changed(judge, initial, after, {"backpack_items"})
    check_rows_added(judge, initial, after, "backpack_items",
                     [[None, 1, 888, "2026-09-30"]], "backpack_add_alice_stark_10712")
    check_rows_removed(judge, initial, after, "backpack_items", [],
                     "no_rows_removed_backpack_items")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
