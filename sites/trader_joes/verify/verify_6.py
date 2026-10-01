#!/usr/bin/env python3
"""Deterministic verifier for Trader Joe's--6 (trader_joes).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright r2 rounds on the review container tj-review-r2-container
built over the fix commit fb73dbfa, seed md5
34e1af0cc66a317223e889081c2381b4, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_6.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Trader Joe's--6"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Freezer High-to-Low; vegan filter; dana add/increase/remove; What's New count.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/home/products/category/from-the-freezer-95\?.*sortBy=Price\+High\+to\+Low",
        r"/home/products/category/from-the-freezer-95\?.*Vegan",
        r"/home/products/pdp/072949",
        r"/login",
        r"/home/products/pdp/077515",
        r"/home/shopping-list",
        r"/home/products/category/products-2\?filters=.*areNewProducts",
    ])
    check_answer_phrase(judge, answer, "most_expensive", "Korean Style Beef Short Ribs")
    check_answer_price(judge, answer, "most_expensive_price", 14.99)
    check_answer_phrase(judge, answer, "second_most_expensive", "Beef Bulgogi")
    check_answer_number(judge, answer, "vegan_count", 38)
    check_answer_phrase(judge, answer, "first_vegan", "Jumeokbap")
    check_answer_price(judge, answer, "second_vegan_price", 4.99)
    check_answer_number(judge, answer, "total_after_add", 1)
    check_answer_number(judge, answer, "total_after_increase", 2)
    check_answer_zero_or_phrase(judge, answer, "final_count",
                                ["empty", "no items", "not added any items"])
    check_answer_number(judge, answer, "whats_new_count", 25)
    check_read_only(judge, initial, after)

    check_only_tables_changed(judge, initial, after, set())


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
