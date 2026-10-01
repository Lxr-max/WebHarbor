#!/usr/bin/env python3
"""Deterministic verifier for Stanford University--5.

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-stanford-review, seed
sha256 40897e025003956e34f418eb213d7ea786775d342cabcbeba560b5767059d65c, with
every hardcoded fact cross-checked against the frozen seed database) — never
read from tasks.jsonl.
Usage: python3 verify_5.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Stanford University--5"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # CS-BS (93, 8 requirement groups) -> compare CS-MS (45, diff 48) ->
    # CS-MIN (26) -> compare CS-PHD (135, diff 109) -> CS dept page (5 programs).
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/programs\?q=Computer",
        r"/programs/CS-BS",
        r"/programs/CS-BS\?compare=CS-MS",
        r"/programs/CS-MIN",
        r"/programs/CS-MIN\?compare=CS-PHD",
        r"/departments/COMPUTSCI",
        r"/programs/CS-PHD(?!\?compare)",
        r"/programs/CS-MS(?!\?compare)",
    ])
    check_answer_number(judge, answer, "cs_bs_min_units", 93)
    check_answer_number(judge, answer, "cs_bs_req_groups", 8)
    check_answer_number(judge, answer, "cs_ms_min_units", 45)
    check_answer_number(judge, answer, "cs_bs_ms_diff", 48)
    check_answer_number(judge, answer, "cs_minor_min_units", 26)
    check_answer_number(judge, answer, "cs_phd_min_units", 135)
    check_answer_number(judge, answer, "cs_min_phd_diff", 109)
    check_answer_number(judge, answer, "cs_dept_program_count", 5)
    check_answer_number(judge, answer, "cs_phd_min_units_detail", 135)
    check_answer_number(judge, answer, "cs_ms_req_groups", 8)
    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
