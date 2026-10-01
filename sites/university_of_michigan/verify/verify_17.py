#!/usr/bin/env python3
"""Deterministic verifier for University of Michigan--17 (university_of_michigan).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-umich-review-r2, seed md5
0492574f8c28ddc5b923294839d99cc0, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_17.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "University of Michigan--17"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Programs total (156); nursing (1, School of Nursing); Nursing school
    # page (1 program); r2 re-anchor: pharmaceutical search (1 real match:
    # Pharmaceutical Sciences) instead of the degenerate 0-match pharmacy
    # query; carol login; saving the already-saved Nursing program is an
    # idempotent no-op, so the honest end state is UNCHANGED (a delta means
    # the agent saved something else and FAILS here); reported total 2.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/programs\b",
        r"/programs\?q=nursing",
        r"/programs/112\b",
        r"/schools-colleges/nursing",
        r"/programs\?q=pharmaceutical",
        r"/login",
        r"/myumich",
    ])
    check_answer_number(judge, answer, "programs_total", 156)
    check_answer_number(judge, answer, "nursing_count", 1)
    check_answer_phrase(judge, answer, "nursing_school_full", "School of Nursing")
    check_answer_number(judge, answer, "nursing_school_programs", 1)
    check_answer_number(judge, answer, "pharmaceutical_count", 1)
    check_answer_number(judge, answer, "carol_saved_programs", 2)
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
