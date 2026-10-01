#!/usr/bin/env python3
"""Deterministic verifier for Trader Joe's--18 (trader_joes).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright r2 rounds on the review container tj-review-r2-container
built over the fix commit fb73dbfa, seed md5
34e1af0cc66a317223e889081c2381b4, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_18.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Trader Joe's--18"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # What's New; first product; bob add + increase chicken; second product price.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/home/products/category/products-2\?filters=.*areNewProducts",
        r"/home/products/pdp/085369",
        r"/login",
        r"/home/shopping-list",
        r"/home/search\?q=.*",
    ])
    check_answer_number(judge, answer, "whats_new_count", 25)
    check_answer_price(judge, answer, "first_price", 8.99)
    check_answer_phrase(judge, answer, "first_size", "1 Each")
    check_answer_regex(judge, answer, "first_limited", r"(?i)yes|limited")
    check_answer_number(judge, answer, "new_total", 7)
    check_answer_number(judge, answer, "moc_qty", 2)
    check_answer_number(judge, answer, "total_after_increase", 8)
    check_answer_price(judge, answer, "second_price", 1.99)
    check_answer_number(judge, answer, "search_count", 1)

    check_only_tables_changed(judge, initial, after, {"shopping_items"})
    check_rows_added(judge, initial, after, "shopping_items",
                     [[None, 2, "085369", 1, None]], "bob_adds_bare_bones")
    check_rows_changed(judge, initial, after, "shopping_items",
                       [[6, 2, "066563", 3, None]], "increase_mandarin_chicken")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
