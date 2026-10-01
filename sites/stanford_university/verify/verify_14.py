#!/usr/bin/env python3
"""Deterministic verifier for Stanford University--14.

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-stanford-review, seed
sha256 40897e025003956e34f418eb213d7ea786775d342cabcbeba560b5767059d65c, with
every hardcoded fact cross-checked against the frozen seed database) — never
read from tasks.jsonl.
Usage: python3 verify_14.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Stanford University--14"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Signup Jordan Vale -> neuroscience search -> BIO102 (ROP grading, Winter
    # term) -> add -> Principles of Economics search -> ECON1 -> add ->
    # planner 2 courses, 9 units.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/signup",
        r"/courses\?q=introduction",
        r"/courses/BIO102",
        r"/courses\?q=Principles",
        r"/courses/ECON1",
        r"/planner",
    ])
    check_answer_phrase(judge, answer, "bio102_grading", "ROP - Letter or Credit/No Credit")
    check_answer_phrase(judge, answer, "bio102_terms", "Winter")
    check_answer_number(judge, answer, "jordan_planner_count", 2)
    check_answer_number(judge, answer, "jordan_planner_total", 9)
    check_only_tables_changed(judge, initial, after, {"users", "planned_courses"})
    check_rows_added(judge, initial, after, "users",
                     [[None, "Jordan Vale", "jordan.vale@test.com", "rx:.+", None]],
                     "signup_jordan_vale")
    check_rows_added(judge, initial, after, "planned_courses",
                     [[None, None, "BIO102", None, None],
                      [None, None, "ECON1", None, None]], "planner_jordan_courses")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
