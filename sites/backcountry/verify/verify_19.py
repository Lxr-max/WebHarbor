#!/usr/bin/env python3
"""Deterministic verifier for Backcountry--19 (backcountry).

Ground truth below is HARDCODED (frozen from the two independent honest-step
rounds on the dev container wh-backcountry-dev, image
webharbor:backcountry-dev, seed md5 44da2a3fc213b3ac5e76ba11453baee2 — both
rounds measured identical step counts and identical answers) — never read
from tasks.jsonl.
Usage: python3 verify_19.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Backcountry--19"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_login", r"/login")
    check_visited_path(judge, traj, "nav_wishlist", r"/wish-list")
    check_visited_path(judge, traj, "nav_pdp", r"black-diamond-momentum-climbing-shoe-mens")
    check_visited_path(judge, traj, "nav_review_posted", r"black-diamond-momentum-climbing-shoe-mens\?review-posted=1|black-diamond-momentum")
    check_answer_phrase(judge, answer, "wishlist_fleece", "Textured Fleece Pullover - Women's")
    check_answer_phrase(judge, answer, "wishlist_momentum", "Momentum Climbing Shoe - Men's")
    check_answer_phrase(judge, answer, "wishlist_tent", 'Copper Spur UL2 Tent: 2-Person 3-Season')
    check_answer_phrase(judge, answer, "fleece_date", '2026-09-27')
    check_answer_phrase(judge, answer, "momentum_date", '2026-09-24')
    check_answer_phrase(judge, answer, "tent_date", '2026-09-21')
    check_answer_money(judge, answer, "sale", 69.97)
    check_answer_phrase(judge, answer, "rating", '4.5')
    check_answer_number(judge, answer, "reviews", 244)
    check_answer_number(judge, answer, "after", 245)
    check_answer_phrase(judge, answer, "remaining", "Momentum Climbing Shoe - Men's")
    check_only_tables_changed(judge, initial, after, {"reviews", "wishlist_items"})
    check_rows_added(judge, initial, after, "reviews",
                      [[None, None, "BLD00QS", 1, "Alice Johnson", "Sticks like glue", "Edging on tiny granite nubs felt solid from day one.", 5, "rx:2026-09-30", "I've used it several times", None, None, "[]", 0, None, 0, 0]], "review_row")
    check_rows_removed(judge, initial, after, "wishlist_items",
                      [[1, 1, "BAGZ2GN", "2026-09-21"], [3, 1, "PATZBF8", "2026-09-27"]], "two_wishlist_removals")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
