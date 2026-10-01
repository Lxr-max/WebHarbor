#!/usr/bin/env python3
"""Deterministic verifier for Trader Joe's--14 (trader_joes).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright r2 rounds on the review container tj-review-r2-container
built over the fix commit fb73dbfa, seed md5
34e1af0cc66a317223e889081c2381b4, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_14.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Trader Joe's--14"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Carol list ops: remove crispbread, decrease fusilli, add 2 products.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/login",
        r"/home/shopping-list",
        r"/home/search\?q=.*White\+Sandwich\+Bread|/home/products/pdp/054292",
        r"/home/products/pdp/054292",
        r"/home/products/pdp/071651",
    ])
    check_answer_number(judge, answer, "initial_total", 4)
    check_answer_count_at_least(judge, answer, "initial_items", [
        "Organic Brown Rice & Quinoa Fusilli Pasta",
        "Gluten Free Norwegian Crispbread",
        "Gluten Free Multigrain Bread"], 3)
    check_answer_number(judge, answer, "total_after_remove", 2)
    check_answer_number(judge, answer, "running_total", 1)
    check_answer_number(judge, answer, "total_after_add1", 2)
    check_answer_number(judge, answer, "final_count", 3)
    check_answer_count_at_least(judge, answer, "final_items", [
        "Gluten Free Multigrain Bread",
        "Gluten Free White Sandwich Bread",
        "Gluten Free Breaded Shrimp"], 3)

    check_only_tables_changed(judge, initial, after, {"shopping_items"})
    check_rows_removed(judge, initial, after, "shopping_items", [
        [None, 3, "051524", 1, None],
        [None, 3, "059721", 2, None],
    ], "remove_fusilli_and_crispbread")
    check_rows_added(judge, initial, after, "shopping_items", [
        [None, 3, "054292", 1, None],
        [None, 3, "071651", 1, None],
    ], "add_white_bread_and_shrimp")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
