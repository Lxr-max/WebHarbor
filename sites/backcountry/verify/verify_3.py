#!/usr/bin/env python3
"""Deterministic verifier for Backcountry--3 (backcountry).

Ground truth below is HARDCODED (frozen from the two independent honest-step
rounds on the dev container wh-backcountry-dev, image
webharbor:backcountry-dev, seed md5 44da2a3fc213b3ac5e76ba11453baee2 — both
rounds measured identical step counts and identical answers) — never read
from tasks.jsonl.
Usage: python3 verify_3.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Backcountry--3"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_search", r"/search\?q=headlamp")
    check_visited_path(judge, traj, "nav_pdp", r"black-diamond-cosmo-350-headlamp")
    check_visited_path(judge, traj, "nav_login", r"/login")
    check_visited_path(judge, traj, "nav_pdp_again", r"black-diamond-cosmo-350-headlamp\?question-posted=1|black-diamond-cosmo-350-headlamp")
    check_visited_path(judge, traj, "nav_cart", r"/cart")
    check_answer_phrase(judge, answer, "title", 'Cosmo 350 Headlamp')
    check_answer_money(judge, answer, "price", 25.97)
    check_answer_phrase(judge, answer, "rating", '4.5')
    # the PDP renders 49 reviews for the Cosmo 350 (both the (49) badge and
    # the "based on 49 ratings" summary); 21 was a cross-task contamination
    check_answer_number(judge, answer, "reviews", 49)
    check_answer_phrase(judge, answer, "first_q", 'Does this come with the rechargeable battery?')
    check_answer_phrase(judge, answer, "first_a", 'does not come with the rechargeable BD 1500 battery')
    check_answer_phrase(judge, answer, "confirmation", 'Thanks! Your question has been posted.')
    check_answer_money(judge, answer, "subtotal", 51.94)
    check_answer_money(judge, answer, "shipping", 6.95)
    # deepened: search headlamps again, open the Cosmo 350-R, report price
    check_visited_path(judge, traj, "nav_search_again", r"/search\?q=headlamp")
    check_visited_path(judge, traj, "nav_350r", r"black-diamond-cosmo-350-r-headlamp")
    check_answer_money(judge, answer, "cosmo_350r_price", 38.97)
    check_only_tables_changed(judge, initial, after, {"cart_items", "questions"})
    check_rows_added(judge, initial, after, "cart_items",
                      [[None, 2, None, "BLDZ9ID-OCT-ONESIZ", 2, "2026-09-30"]], "headlamp_cart_row")
    check_rows_added(judge, initial, after, "questions",
                      [[None, None, "BLDZ9ID", "Bob Chen",
                        "Does it float in water?", "rx:2026-09-30"]], "question_row")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
