#!/usr/bin/env python3
"""Deterministic verifier for University of Michigan--5 (university_of_michigan).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-umich-review, seed md5
3f5e930aa820d1b62309ec3feeb4536b, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_5.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "University of Michigan--5"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Map: Union (1, Student Life, 530 STATE ST), league (1, Michigan League,
    # 911 N. UNIVERSITY AVE), Library/Museum category (14; Museum of Natural
    # History zip 48109); alice login; Request Information as Parent or
    # Guardian asking about campus tours; confirmation message.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/map\?q=Union",
        r"/map/building/michigan-union",
        r"/map\?q=league",
        r"/map/building/michigan-league",
        r"/map\?[^ ]*category=Library",
        r"/map/building/museum-of-natural-history-1",
        r"/login",
        r"/admissions/request-info",
        r"/admissions/request-info/thanks",
    ])
    check_answer_number(judge, answer, "union_count", 1)
    check_answer_phrase(judge, answer, "union_category", "Student Life")
    check_answer_phrase(judge, answer, "union_address", "530 STATE ST")
    check_answer_number(judge, answer, "league_count", 1)
    check_answer_phrase(judge, answer, "league_address", "911 N. UNIVERSITY AVE")
    check_answer_number(judge, answer, "library_museum_count", 14)
    check_answer_phrase(judge, answer, "natural_history_museum", "Museum of Natural History")
    check_answer_phrase(judge, answer, "mnh_zip", "48109")
    check_answer_phrase(judge, answer, "confirmation_thanks", "Thank you")
    check_answer_phrase(judge, answer, "confirmation_received", "has been received")
    check_only_tables_changed(judge, initial, after, {"info_requests"})
    check_rows_added(judge, initial, after, "info_requests",
                     [[None, None, "alice.j@test.com", "Parent or Guardian",
                       "rx:campus tour", None]], "info_request_alice_parent")
    check_rows_removed(judge, initial, after, "info_requests", [],
                     "no_rows_removed_info_requests")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
