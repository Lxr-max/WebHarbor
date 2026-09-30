#!/usr/bin/env python3
"""Deterministic verifier for Backcountry--1 (backcountry).

Ground truth below is HARDCODED (frozen from the two independent honest-step
rounds on the dev container wh-backcountry-dev, image
webharbor:backcountry-dev, seed md5 44da2a3fc213b3ac5e76ba11453baee2 — both
rounds measured identical step counts and identical answers) — never read
from tasks.jsonl.
Usage: python3 verify_1.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Backcountry--1"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_cat", r"/cat/ski")
    check_visited_path(judge, traj, "nav_black", r"/cat/ski.*color=black")
    check_visited_path(judge, traj, "nav_sort_low", r"color=black.*sort=price|sort=price.*color=black")
    check_visited_path(judge, traj, "nav_pdp_cheap", r"smartwool-merino-250-baselayer-crew-womens")
    check_visited_path(judge, traj, "nav_pdp_expensive", r"the-north-face-summit-verbier-gtx-jacket-mens")
    check_visited_path(judge, traj, "nav_login", r"/login")
    # header sign-in lands on /account; the PDP sign-in link carries ?next=
    # and auto-returns to the product — either is honest evidence of login
    check_visited_any(judge, traj, "nav_signed_in", [r"/account", r"/login\?next="])
    check_visited_path(judge, traj, "nav_cart", r"/cart")
    check_answer_number(judge, answer, "upstream", 4771)
    check_answer_number(judge, answer, "black_count", 8)
    check_answer_phrase(judge, answer, "cheapest", "Classic Thermal Merino Crew Baselayer - Women's")
    check_answer_money(judge, answer, "cheapest_price", 57.5)
    check_answer_phrase(judge, answer, "most_expensive", "Summit Verbier GTX Jacket - Men's")
    check_answer_money(judge, answer, "subtotal", 1004.0)
    check_only_tables_changed(judge, initial, after, {"cart_items"})
    check_rows_added(judge, initial, after, "cart_items",
                      [[None, 1, None, "SWLZ8BY-CHAVIOHEA-XS", 3, "2026-09-30"]], "new_xs_cart_row")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
