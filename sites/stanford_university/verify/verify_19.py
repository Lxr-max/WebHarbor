#!/usr/bin/env python3
"""Deterministic verifier for Stanford University--19.

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-stanford-review, seed
sha256 40897e025003956e34f418eb213d7ea786775d342cabcbeba560b5767059d65c, with
every hardcoded fact cross-checked against the frozen seed database) — never
read from tasks.jsonl.
Usage: python3 verify_19.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Stanford University--19"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # CS faculty filter (144, first alphabetically Sara Achour, Assistant
    # Professor of Computer Science and of Electrical Engineering) -> alice
    # login -> planner (CS106A 3-5, MATH51 5, PHYSICS41 4, total 12-14) ->
    # CS161 add -> new total 15-19.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"dept=Computer",
        r"/login",
        r"/planner",
        r"/courses\?q=Design",
        r"/courses/CS161",
    ])
    check_answer_number(judge, answer, "cs_faculty_count", 144)
    check_answer_phrase(judge, answer, "cs_first_name", "Sara Achour")
    check_answer_phrase(judge, answer, "cs_first_title", "Assistant Professor of Computer Science and of Electrical Engineering")
    check_answer_count_at_least(judge, answer, "alice_planner_seeded",
                                ["CS106A", "MATH51", "PHYSICS41"], 3)
    check_answer_range(judge, answer, "alice_total", 12, 14)
    check_answer_range(judge, answer, "alice_new_total", 15, 19)
    check_only_tables_changed(judge, initial, after, {"planned_courses"})
    check_rows_added(judge, initial, after, "planned_courses",
                     [[None, 1, "CS161", None, None]], "planner_add_alice_cs161")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
