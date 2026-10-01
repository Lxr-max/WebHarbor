#!/usr/bin/env python3
"""Deterministic verifier for Stanford University--17.

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-stanford-review, seed
sha256 40897e025003956e34f418eb213d7ea786775d342cabcbeba560b5767059d65c, with
every hardcoded fact cross-checked against the frozen seed database) — never
read from tasks.jsonl.
Usage: python3 verify_17.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Stanford University--17"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # FR WAYS filter (90) -> +CS subject (11) -> lowest course number CS103
    # (Mathematical Foundations of Computing, 3-5, ROP) -> carol login via
    # in-page link -> add CS103 -> planner (CS103, 3-5) -> remove ->
    # empty planner. Honest end state: row-identical to the seed.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"ways=Formal",
        r"subject=CS&career=&term=&ways=Formal",
        r"term=Winter",
        r"/courses/CS103",
        r"/login",
        r"/planner",
    ])
    check_answer_number(judge, answer, "fr_count", 90)
    check_answer_number(judge, answer, "fr_cs_count", 11)
    check_answer_phrase(judge, answer, "cs103_title", "Mathematical Foundations of Computing")
    check_answer_phrase(judge, answer, "cs103_units", "3-5")
    check_answer_phrase(judge, answer, "cs103_grading", "ROP - Letter or Credit/No Credit")
    check_answer_phrase(judge, answer, "carol_planner_cs103", "CS103")
    check_answer_range(judge, answer, "carol_planner_total", 3, 5)
    check_answer_any(judge, answer, "carol_planner_after_remove",
                    ["empty", "no courses", "0 courses", "planner is empty"])
    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
