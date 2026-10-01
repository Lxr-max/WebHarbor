#!/usr/bin/env python3
"""Deterministic verifier for University of Michigan--15 (university_of_michigan).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-umich-review, seed md5
3f5e930aa820d1b62309ec3feeb4536b, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_15.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "University of Michigan--15"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Athletic category (23); museum search (2); Museum of Natural History
    # (1105 N University Ave., Library/Museum); Housing category (24); carol
    # login; Request Information as High School Student about nursing tours;
    # confirmation.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/map\?[^ ]*category=Athletic",
        r"/map\?q=museum",
        r"/map/building/museum-of-natural-history-1",
        r"/map\?[^ ]*category=Housing",
        r"/login",
        r"/admissions/request-info",
        r"/admissions/request-info/thanks",
    ])
    check_answer_number(judge, answer, "athletic_count", 23)
    check_answer_number(judge, answer, "museum_count", 2)
    check_answer_phrase(judge, answer, "mnh_address", "1105 N University")
    check_answer_phrase(judge, answer, "mnh_category", "Library/Museum")
    check_answer_number(judge, answer, "housing_count", 24)
    check_answer_phrase(judge, answer, "confirmation_thanks", "Thank you")
    check_answer_phrase(judge, answer, "confirmation_received", "has been received")
    check_only_tables_changed(judge, initial, after, {"info_requests"})
    check_rows_added(judge, initial, after, "info_requests",
                     [[None, None, "carol.d@test.com", "High School Student",
                       "rx:nursing", None]], "info_request_carol_hs")
    check_rows_removed(judge, initial, after, "info_requests", [],
                     "no_rows_removed_info_requests")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
