#!/usr/bin/env python3
"""Deterministic verifier for Trader Joe's--1 (trader_joes).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright r2 rounds on the review container tj-review-r2-container
built over the fix commit fb73dbfa, seed md5
34e1af0cc66a317223e889081c2381b4, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_1.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_number, check_answer_number_absent, check_answer_number_any,
    check_answer_ordered, check_answer_phrase, check_answer_price,
    check_answer_regex, check_answer_zero_or_phrase, check_read_only,
    check_rows_added, check_rows_removed, check_rows_changed,
    check_only_tables_changed, check_screenshots, check_seed_contract,
    check_trajectory_identity, check_visited_all, check_visited_any,
    check_visited_path, final_answer, run_verifier,
)

TASK_ID = "Trader Joe's--1"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Jordan Vale signup; What's New count; 3 rail products added; list ops.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/signup",
        r"/home/products/category/products-2\?filters=.*areNewProducts",
        r"/home/shopping-list",
        r"/login",
    ])
    check_answer_number(judge, answer, "whats_new_count", 25)
    check_answer_number(judge, answer, "total_items", 3)
    check_answer_count_at_least(judge, answer, "item_prices", [
        "$3.49/12 Oz", "$2.79/8 Oz", "$4.99/12 Oz"], 3)
    check_answer_number(judge, answer, "cereal_new_qty", 2)
    check_answer_number(judge, answer, "new_total", 4)
    check_answer_number(judge, answer, "persisted_total", 4)

    check_only_tables_changed(judge, initial, after, {"shopping_items", "users"})
    check_rows_added(judge, initial, after, "users",
                     [[None, "jordan.vale@test.com", "Jordan Vale", r"rx:\$2b\$12\$", None]],
                     "signup_jordan_vale")
    check_rows_added(judge, initial, after, "shopping_items", [
        [None, 5, "053711", 2, None],
        [None, 5, "051533", 1, None],
        [None, 5, "083507", 1, None],
    ], "jordan_three_products")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
