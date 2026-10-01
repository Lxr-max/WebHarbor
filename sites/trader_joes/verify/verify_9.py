#!/usr/bin/env python3
"""Deterministic verifier for Trader Joe's--9 (trader_joes).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright r2 rounds on the review container tj-review-r2-container
built over the fix commit fb73dbfa, seed md5
34e1af0cc66a317223e889081c2381b4, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_9.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Trader Joe's--9"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Desserts recipes; Let's Bake!; first recipes; description product; carol search+add.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/home/recipes\?categories=desserts",
        r"/home/recipes\?categories=desserts&funTags=Let%27s\+Bake!",
        r"/home/recipes/blueberry-corn-cake",
        r"/home/recipes/abj-banana-bark-boats",
        r"/home/products/pdp/073946",
        r"/login",
        r"/home/search\?q=.*",
        r"/home/shopping-list",
    ])
    check_answer_number(judge, answer, "desserts_count", 92)
    check_answer_number(judge, answer, "desserts_lb_count", 18)
    check_answer_phrase(judge, answer, "r1_title", "Blueberry Corn Cake")
    check_answer_number(judge, answer, "r1_serves", 9)
    check_answer_regex(judge, answer, "r1_time", r"55\s*mins")
    check_answer_phrase(judge, answer, "r1_first_ingredient", "Canola Oil")
    check_answer_phrase(judge, answer, "r2_title", "AB&J Banana Bark Boats")
    check_answer_number(judge, answer, "r2_serves", 4)
    check_answer_phrase(judge, answer, "desc_product", "Dark Chocolate Bark with Almond, Pretzel")
    check_answer_price(judge, answer, "desc_product_price", 5.99)
    check_answer_phrase(judge, answer, "desc_product_size", "10 Oz")
    check_answer_number(judge, answer, "search_total", 1)
    check_answer_number(judge, answer, "new_total", 5)
    check_only_tables_changed(judge, initial, after, {"shopping_items"})
    check_rows_added(judge, initial, after, "shopping_items",
                     [[None, 3, "073946", 1, None]], "carol_adds_chocolate_bark")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
