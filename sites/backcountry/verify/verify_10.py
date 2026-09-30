#!/usr/bin/env python3
"""Deterministic verifier for Backcountry--10 (backcountry).

Ground truth below is HARDCODED (frozen from the two independent honest-step
rounds on the dev container wh-backcountry-dev, image
webharbor:backcountry-dev, seed md5 44da2a3fc213b3ac5e76ba11453baee2 — both
rounds measured identical step counts and identical answers) — never read
from tasks.jsonl.
Usage: python3 verify_10.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_money, check_answer_number, check_answer_number_absent,
    check_answer_ordered, check_answer_phrase, check_answer_regex,
    check_read_only, check_rows_added, check_rows_changed, check_rows_removed,
    check_only_tables_changed, check_screenshots, check_seed_contract,
    check_trajectory_identity, check_visited_all, check_visited_any,
    check_visited_path, final_answer, run_verifier,
)

TASK_ID = "Backcountry--10"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_register", r"/register")
    check_visited_path(judge, traj, "nav_search", r"/search\?q=down%20jacket|/search\?q=down\+jacket")
    check_visited_path(judge, traj, "nav_pdp", r"rab-microlight-alpine-down-jacket-mens")
    check_visited_path(judge, traj, "nav_second_color", r"rab-microlight-alpine-down-jacket-mens\?color=BLA")
    check_visited_path(judge, traj, "nav_review_posted", r"rab-microlight-alpine-down-jacket-mens\?review-posted=1|rab-microlight")
    check_answer_phrase(judge, answer, "title", "Microlight Alpine Down Jacket - Men's")
    check_answer_money(judge, answer, "price", 221.25)
    check_answer_phrase(judge, answer, "second_color", 'Black')
    check_answer_number(judge, answer, "after", 29)
    check_only_tables_changed(judge, initial, after, {"users", "reviews"})
    check_rows_added(judge, initial, after, "users",
                      [[None, "fresh.trail@example.com", "Trail Tester", "rx:^\\$2b\\$12\\$", 0, "2026-09-30"]], "new_user_row")
    check_rows_added(judge, initial, after, "reviews",
                      [[None, None, "RABZ06I", 5, "Trail Tester", "Warmth for days", "Below freezing at camp and I stayed toasty all night.", 4, "rx:2026-09-30", "I've used it once or twice", None, None, "[]", 0, None, 0, 0]], "review_row")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
