#!/usr/bin/env python3
"""Deterministic verifier for Backcountry--13 (backcountry).

Ground truth below is HARDCODED (frozen from the two independent honest-step
rounds on the dev container wh-backcountry-dev, image
webharbor:backcountry-dev, seed md5 44da2a3fc213b3ac5e76ba11453baee2 — both
rounds measured identical step counts and identical answers) — never read
from tasks.jsonl.
Usage: python3 verify_13.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Backcountry--13"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_search", r"/search\?q=goggles")
    check_visited_path(judge, traj, "nav_pdp", r"smith-i-o-mag-xl-chromapop-goggles")
    check_visited_path(judge, traj, "nav_review_sort", r"review-sort=lowest")
    check_visited_path(judge, traj, "nav_login", r"/login")
    check_visited_path(judge, traj, "nav_cart", r"/cart")
    check_answer_phrase(judge, answer, "rating", '4.5')
    check_answer_number(judge, answer, "reviews", 348)
    check_answer_number(judge, answer, "one_star", 21)
    check_answer_number(judge, answer, "five_star", 264)
    check_answer_phrase(judge, answer, "lowest_title", 'Disappointed')
    check_answer_number(judge, answer, "lowest_rating", 2)
    check_answer_money(judge, answer, "subtotal", 799.99)
    check_answer_phrase(judge, answer, "lens_answer", 'two lenses')
    # deepened: open the first related product from the PDP rail and report
    # its title; then remove the goggles and report the empty-cart message
    check_visited_path(judge, traj, "nav_related", r"elan-ripstick-88-ski-2026-womens")
    check_answer_phrase(judge, answer, "related_title", "Ripstick 88 Ski - 2026 - Women's")
    check_answer_phrase(judge, answer, "empty_cart", 'Your cart is currently empty')
    # deepened task ends with both seeded cart rows removed (goggles + binding),
    # leaving the cart empty; the qty-2 state is evidenced by the $799.99
    # subtotal answer check above
    check_only_tables_changed(judge, initial, after, {"cart_items"})
    check_rows_removed(judge, initial, after, "cart_items",
                       [[None, 4, None, "SMIZ9HR-BLCHEVBLMI-ONESIZ", 1, "2026-09-30"],
                        [None, 4, None, "MRKZ04O-BLA-S110", 1, "2026-09-30"]], "seeded_cart_removed")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
