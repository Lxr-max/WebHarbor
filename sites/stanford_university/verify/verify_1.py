#!/usr/bin/env python3
"""Deterministic verifier for Stanford University--1.

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-stanford-review, seed
sha256 40897e025003956e34f418eb213d7ea786775d342cabcbeba560b5767059d65c, with
every hardcoded fact cross-checked against the frozen seed database) — never
read from tasks.jsonl.
Usage: python3 verify_1.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Stanford University--1"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Engineering filter (14) -> Aeronautics dept (AA) -> AA-BS (100) ->
    # compare AA-MS (45, diff 55) -> MSE dept (MS&E) -> catalog link
    # (MS&E103 Fundamentals of Agentic Systems, 3) -> back (5 programs).
    check_visited_all(judge, traj, "nav_surfaces", [
        r"school=engineering",
        r"/departments/AEROASTRO",
        r"/programs/AA-BS",
        r"/programs/AA-BS\?compare=AA-MS",
        r"/departments/MGMTSCI",
        r"/courses\?dept=MGMTSCI",
        r"/programs/MGTSC-MS",
    ])
    check_answer_number(judge, answer, "eng_dept_count", 14)
    check_answer_phrase(judge, answer, "aa_subject_code", "AA")
    check_answer_number(judge, answer, "aa_bs_min_units", 100)
    check_answer_number_any(judge, answer, "aa_ms_min_units", [45])
    check_answer_number(judge, answer, "aa_bs_ms_diff", 55)
    check_answer_phrase(judge, answer, "mse_subject_code", "MS&E")
    check_answer_phrase(judge, answer, "mse_first_course_code", "MS&E103")
    check_answer_phrase(judge, answer, "mse_first_course_title", "Fundamentals of Agentic Systems")
    check_answer_number(judge, answer, "mse_first_units", 3)
    check_answer_number(judge, answer, "mse_program_count", 5)
    check_answer_number(judge, answer, "mse_ms_req_groups", 2)
    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
