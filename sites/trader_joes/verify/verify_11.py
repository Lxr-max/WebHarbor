#!/usr/bin/env python3
"""Deterministic verifier for Trader Joe's--11 (trader_joes).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright r2 rounds on the review container tj-review-r2-container
built over the fix commit fb73dbfa, seed md5
34e1af0cc66a317223e889081c2381b4, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_11.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Trader Joe's--11"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # One Seasoning Wonder guide facts; What's New; alice add first product.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/home/discover/guides",
        r"/home/discover/guides/one-seasoning-wonder",
        r"/home/recipes/polenta-veggie-stacks",
        r"/home/products/category/products-2\?filters=.*areNewProducts",
        r"/login",
        r"/home/products/pdp/085369",
        r"/home/shopping-list",
    ])
    check_answer_phrase(judge, answer, "guide_date", "2026-09-16")
    check_answer_count_at_least(judge, answer, "showcase_recipes", [
        "Polenta & Veggie Stacks", "Umami Parm Popcorn",
        "Roasted Pork Tenderloin & Potatoes with Honey Umami Butter"], 3)
    check_answer_phrase(judge, answer, "featured_product",
                        "Mushroom & Company Multipurpose Umami Seasoning Blend")
    check_answer_number(judge, answer, "recipe_serves", 4)
    check_answer_regex(judge, answer, "recipe_time", r"30\s*mins\s*-\s*35\s*mins")
    check_answer_number(judge, answer, "whats_new_count", 25)
    check_answer_phrase(judge, answer, "whats_new_first", "Bare Bones Succulent Garden")
    check_answer_number(judge, answer, "new_total", 9)

    check_only_tables_changed(judge, initial, after, {"shopping_items"})
    check_rows_added(judge, initial, after, "shopping_items",
                     [[None, 1, "085369", 1, None]], "alice_adds_bare_bones")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
