#!/usr/bin/env python3
"""Deterministic verifier for Trader Joe's--15 (trader_joes).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright r2 rounds on the review container tj-review-r2-container
built over the fix commit fb73dbfa, seed md5
34e1af0cc66a317223e889081c2381b4, with every hardcoded fact cross-checked
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
    check_rows_added, check_rows_removed, check_rows_changed,
    check_only_tables_changed, check_screenshots, check_seed_contract,
    check_trajectory_identity, check_visited_all, check_visited_any,
    check_visited_path, final_answer, run_verifier,
)

TASK_ID = "Trader Joe's--15"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Cheese search; Just Here for the Cheese guide; newest story; bob add.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/home/search\?q=cheese",
        r"/home/discover/guides/just-here-for-cheese",
        r"/home/products/pdp/052381",
        r"/home/discover/stories",
        r"/login",
        r"/home/shopping-list",
    ])
    check_answer_number(judge, answer, "cheese_products", 128)
    check_answer_number(judge, answer, "cheese_everything_else", 37)
    check_answer_phrase(judge, answer, "guide_date", "2024-01-29")
    check_answer_phrase(judge, answer, "featured_product", "Cheddar Cheese with Caramelized Onions")
    check_answer_price(judge, answer, "product_price", 11.99)
    check_answer_phrase(judge, answer, "product_category", "Wedges, Wheels, Loaves, Logs")
    # r2: the two upstream-404 capture artifacts are gone; the newest story
    # is the real one (was "Oops!" in r1)
    check_answer_phrase(judge, answer, "newest_story", "A Cider to Crow About")
    check_answer_phrase(judge, answer, "newest_story_date", "2026-09-25")
    check_answer_number(judge, answer, "new_total", 7)
    check_answer_number(judge, answer, "cups_qty", 1)
    check_only_tables_changed(judge, initial, after, {"shopping_items"})
    check_rows_added(judge, initial, after, "shopping_items",
                     [[None, 2, "052381", 1, None]], "bob_adds_caramelized_onion_cheddar")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
