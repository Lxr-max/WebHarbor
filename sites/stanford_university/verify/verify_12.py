#!/usr/bin/env python3
"""Deterministic verifier for Stanford University--12.

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-stanford-review, seed
sha256 40897e025003956e34f418eb213d7ea786775d342cabcbeba560b5767059d65c, with
every hardcoded fact cross-checked against the frozen seed database) — never
read from tasks.jsonl.
Usage: python3 verify_12.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Stanford University--12"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Admission (REA Nov 1, RD Jan 5, $100 fee, midyear Feb 15) -> aid
    # estimator 120000/2 (no tuition responsibility; room and board
    # responsibility applies) -> signup Sam Rivera -> add PSYCH1 -> planner
    # (1 course, 5 units).
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/admission(?!/)",
        r"/admission/aid\?income=120000",
        r"/signup",
        r"/courses\?q=Introduction",
        r"/courses/PSYCH1",
        r"/planner",
    ])
    check_answer_phrase(judge, answer, "rea_deadline", "November 1")
    check_answer_phrase(judge, answer, "rd_deadline", "January 5")
    check_answer_price(judge, answer, "app_fee", "100")
    check_answer_phrase(judge, answer, "midyear_due", "February 15")
    check_answer_phrase(judge, answer, "est_tuition", "No tuition responsibility")
    check_answer_phrase(judge, answer, "est_room", "Room and board responsibility applies")
    check_answer_number(judge, answer, "sam_planner_count", 1)
    check_answer_number(judge, answer, "sam_planner_total", 5)
    check_only_tables_changed(judge, initial, after, {"users", "planned_courses"})
    check_rows_added(judge, initial, after, "users",
                     [[None, "Sam Rivera", "sam.rivera@test.com", "rx:.+", None]],
                     "signup_sam_rivera")
    check_rows_added(judge, initial, after, "planned_courses",
                     [[None, None, "PSYCH1", None, None]], "planner_sam_psych1")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
