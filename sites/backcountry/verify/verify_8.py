#!/usr/bin/env python3
"""Deterministic verifier for Backcountry--8 (backcountry).

Ground truth below is HARDCODED (frozen from the two independent honest-step
rounds on the dev container wh-backcountry-dev, image
webharbor:backcountry-dev, seed md5 44da2a3fc213b3ac5e76ba11453baee2 — both
rounds measured identical step counts and identical answers) — never read
from tasks.jsonl.
Usage: python3 verify_8.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Backcountry--8"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_login", r"/login")
    check_visited_path(judge, traj, "nav_cat", r"/cat/hike-camp")
    check_visited_path(judge, traj, "nav_blue", r"/cat/hike-camp/color/blue")
    check_visited_path(judge, traj, "nav_price", r"price-min=100")
    check_visited_path(judge, traj, "nav_pdp_cheap", r"seniq-everform-all-season-merino-ls-baselayer-top-womens")
    check_visited_path(judge, traj, "nav_pdp_expensive", r"patagonia-textured-fleece-pullover-womens")
    check_visited_path(judge, traj, "nav_cart", r"/cart")
    check_answer_number(judge, answer, "upstream", 8408)
    check_answer_number(judge, answer, "blue_count", 7)
    check_answer_phrase(judge, answer, "cheapest", "Everform All Season Merino LS Baselayer Top - Women's")
    check_answer_money(judge, answer, "cheapest_price", 108.0)
    check_answer_phrase(judge, answer, "expensive", "Textured Fleece Pullover - Women's")
    check_answer_money(judge, answer, "expensive_price", 155.0)
    check_answer_money(judge, answer, "subtotal", 845.0)
    check_only_tables_changed(judge, initial, after, {"cart_items"})
    check_rows_added(judge, initial, after, "cart_items",
                      [[None, 1, None, "SIQ000H-CAB-XL", 2, "2026-09-30"]], "everform_cart_row")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
