#!/usr/bin/env python3
"""Deterministic verifier for Backcountry--2 (backcountry).

Ground truth below is HARDCODED (frozen from the two independent honest-step
rounds on the dev container wh-backcountry-dev, image
webharbor:backcountry-dev, seed md5 44da2a3fc213b3ac5e76ba11453baee2 — both
rounds measured identical step counts and identical answers) — never read
from tasks.jsonl.
Usage: python3 verify_2.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Backcountry--2"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_brands", r"/shop-all-brands")
    check_visited_path(judge, traj, "nav_letter", r"#letter-F")
    check_visited_path(judge, traj, "nav_brand", r"/brand/fjallraven")
    check_visited_path(judge, traj, "nav_filter", r"/brand/fjallraven/cat/mens-clothing")
    check_visited_path(judge, traj, "nav_sorted", r"/brand/fjallraven.*sort=-rating|sort=-rating")
    check_visited_path(judge, traj, "nav_pdp", r"fjallraven-vardag-g-1000-pile-jacket-mens")
    check_visited_path(judge, traj, "nav_login", r"/login")
    check_visited_path(judge, traj, "nav_wishlist", r"/wish-list")
    check_answer_number(judge, answer, "upstream", 346)
    check_answer_number(judge, answer, "mens_count", 3)
    check_answer_phrase(judge, answer, "title", "Vardag G-1000 Pile Jacket - Men's")
    check_answer_phrase(judge, answer, "rating", '5.0')
    check_answer_number(judge, answer, "reviews", 1)
    check_answer_money(judge, answer, "price", 294.95)
    check_answer_phrase(judge, answer, "wishlist_after", 'Vardag G-1000 Pile Jacket')
    check_answer_phrase(judge, answer, "wishlist_final", "Pro Team Training Jersey")
    check_answer_count_at_least(judge, answer, "wishlist_after_add", ["Vardag G-1000 Pile Jacket - Men's", "Pro Team Training Jersey - Men's"], 2)
    # deepened: open the remaining wish list item (Pro Team Training Jersey)
    # from the wish list and report its price
    check_visited_path(judge, traj, "nav_jersey_pdp", r"rapha-pro-team-jersey-mens-rfad056")
    check_answer_money(judge, answer, "jersey_price", 87.50)
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
