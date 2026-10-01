#!/usr/bin/env python3
"""Deterministic verifier for Stanford University--0.

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-stanford-review, seed
sha256 40897e025003956e34f418eb213d7ea786775d342cabcbeba560b5767059d65c, with
every hardcoded fact cross-checked against the frozen seed database) — never
read from tasks.jsonl.
Usage: python3 verify_0.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Stanford University--0"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Catalog ML search -> CS229 detail -> CS+Graduate filter (40, exact
    # career match) -> alice login via in-page link -> add CS229 -> planner.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/courses\?q=machine\+learning",
        r"/courses/CS229",
        r"subject=CS&career=Graduate",
        r"/login",
        r"/planner",
    ])
    check_answer_phrase(judge, answer, "ml_units_range", "3-4")
    check_answer_phrase(judge, answer, "ml_grading", "ROP - Letter or Credit/No Credit")
    check_answer_phrase(judge, answer, "ml_terms_autumn", "Autumn")
    check_answer_phrase(judge, answer, "ml_terms_winter", "Winter")
    check_answer_number(judge, answer, "cs_grad_count", 40)
    check_answer_number_absent(judge, answer, "cs_grad_count_trip_77", 77)
    check_answer_phrase(judge, answer, "planner_has_cs229", "CS229")
    check_answer_count_at_least(judge, answer, "planner_seeded_courses",
                                ["CS106A", "MATH51", "PHYSICS41"], 3)
    check_answer_number(judge, answer, "planner_course_count", 4)
    check_answer_range(judge, answer, "planner_total_units", 15, 18)
    check_only_tables_changed(judge, initial, after, {"planned_courses"})
    check_rows_added(judge, initial, after, "planned_courses",
                     [[None, 1, "CS229", None, None]], "planner_add_alice_cs229")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
