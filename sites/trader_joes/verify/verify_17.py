#!/usr/bin/env python3
"""Deterministic verifier for Trader Joe's--17 (trader_joes).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright r2 rounds on the review container tj-review-r2-container
built over the fix commit fb73dbfa, seed md5
34e1af0cc66a317223e889081c2381b4, with every hardcoded fact cross-checked
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
    check_rows_added, check_rows_removed, check_rows_changed,
    check_only_tables_changed, check_screenshots, check_seed_contract,
    check_trajectory_identity, check_visited_all, check_visited_any,
    check_visited_path, final_answer, run_verifier,
)

TASK_ID = "Trader Joe's--17"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Shredded Unexpected Cheddar facts; American Heritage cream cheese; bob ops.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/home/products/pdp/065191",
        r"/home/products/pdp/086001",
        r"/login",
        r"/home/shopping-list",
    ])
    check_answer_price(judge, answer, "cheddar_price", 4.99)
    check_answer_phrase(judge, answer, "cheddar_size", "8 Oz")
    check_answer_phrase(judge, answer, "cheddar_origin", "Product of United States")
    check_answer_phrase(judge, answer, "cheddar_first_ingredient", "CHEDDAR CHEESE")
    check_answer_phrase(judge, answer, "cheddar_allergen", "CONTAINS MILK")
    check_answer_phrase(judge, answer, "cc_badge", "Kosher")
    check_answer_price(judge, answer, "cc_price", 2.79)
    check_answer_phrase(judge, answer, "cc_size", "8 Oz")
    check_answer_phrase(judge, answer, "more_expensive", "shredded cheddar")
    check_answer_number(judge, answer, "cheddar_qty", 2)
    check_answer_number(judge, answer, "final_total", 8)
    check_only_tables_changed(judge, initial, after, {"shopping_items"})
    check_rows_added(judge, initial, after, "shopping_items",
                     [[None, 2, "086001", 1, None]], "bob_adds_cream_cheese")
    check_rows_changed(judge, initial, after, "shopping_items",
                       [[8, 2, "065191", 3, None]], "increase_shredded_cheddar")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
