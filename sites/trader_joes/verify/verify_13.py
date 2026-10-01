#!/usr/bin/env python3
"""Deterministic verifier for Trader Joe's--13 (trader_joes).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright r2 rounds on the review container tj-review-r2-container
built over the fix commit fb73dbfa, seed md5
34e1af0cc66a317223e889081c2381b4, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_13.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Trader Joe's--13"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Compare GF Multigrain Bread vs Organic Fusilli + Crispbread; carol list ops.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/home/products/pdp/062146",
        r"/home/products/pdp/051524",
        r"/home/products/pdp/059721",
        r"/login",
        r"/home/shopping-list",
    ])
    check_answer_price(judge, answer, "bread_price", 4.99)
    check_answer_phrase(judge, answer, "bread_size", "15.2 Oz")
    check_answer_phrase(judge, answer, "bread_category", "Sliced Bread")
    check_answer_phrase(judge, answer, "bread_first_ingredient", "WATER, STARCH AND FLOUR BLEND")
    check_answer_count_at_least(judge, answer, "bread_kosher", ["Kosher"], 1)
    check_answer_price(judge, answer, "pasta_price", 3.49)
    check_answer_phrase(judge, answer, "pasta_size", "16 Oz")
    check_answer_phrase(judge, answer, "pasta_category", "Pastas & Grains")
    check_answer_phrase(judge, answer, "pasta_first_ingredient", "ORGANIC BROWN RICE")
    check_answer_count_at_least(judge, answer, "pasta_kosher", ["Kosher"], 1)
    check_answer_price(judge, answer, "crispbread_price", 4.79)
    check_answer_phrase(judge, answer, "crispbread_size", "7.55 Oz")
    check_answer_number(judge, answer, "bread_qty", 1)
    check_answer_number(judge, answer, "list_total", 4)
    check_answer_number(judge, answer, "total_after_increase", 5)
    check_answer_number(judge, answer, "final_total", 3)
    check_only_tables_changed(judge, initial, after, {"shopping_items"})
    check_rows_removed(judge, initial, after, "shopping_items",
                        [[None, 3, "059721", 2, None]], "remove_crispbread")
    check_rows_changed(judge, initial, after, "shopping_items",
                       [[12, 3, "062146", 2, None]], "increase_multigrain_bread")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
