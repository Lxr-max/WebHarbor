#!/usr/bin/env python3
"""Deterministic verifier for Backcountry--6 (backcountry).

Ground truth below is HARDCODED (frozen from the two independent honest-step
rounds on the dev container wh-backcountry-dev, image
webharbor:backcountry-dev, seed md5 44da2a3fc213b3ac5e76ba11453baee2 — both
rounds measured identical step counts and identical answers) — never read
from tasks.jsonl.
Usage: python3 verify_6.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Backcountry--6"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_brands", r"/shop-all-brands")
    check_visited_path(judge, traj, "nav_letter", r"#letter-T")
    check_visited_path(judge, traj, "nav_brand", r"/brand/the-north-face")
    check_visited_path(judge, traj, "nav_sorted", r"/brand/the-north-face\?sort=-rating")
    check_visited_path(judge, traj, "nav_pdp", r"the-north-face-1996-retro-nuptse-jacket-womens")
    check_visited_path(judge, traj, "nav_second_color", r"the-north-face-1996-retro-nuptse-jacket-womens\?color=DARCHE")
    check_visited_path(judge, traj, "nav_login", r"/login")
    check_visited_path(judge, traj, "nav_wishlist", r"/wish-list")
    check_answer_number(judge, answer, "upstream", 1080)
    check_answer_phrase(judge, answer, "title", "1996 Retro Nuptse Jacket - Women's")
    check_answer_phrase(judge, answer, "rating", '5.0')
    check_answer_number(judge, answer, "reviews", 1797)
    check_answer_money(judge, answer, "price", 198.0)
    check_answer_phrase(judge, answer, "second_color", 'Dark Chestnut')
    check_answer_phrase(judge, answer, "wishlist_final", 'Copper Spur UL2 Tent')
    # deepened: open the Copper Spur tent from the wish list and report price
    check_visited_path(judge, traj, "nav_tent_pdp", r"big-agnes-copper-spur-ul2-tent-2-person-3-season")
    check_answer_money(judge, answer, "tent_price", 599.95)
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
