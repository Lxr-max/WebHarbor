#!/usr/bin/env python3
"""Deterministic verifier for Steam--5 (steam).

Ground truth below is HARDCODED from the reviewer's two independent honest
Playwright rounds on the review container wh-steam-review (image
webharbor:steam-review, built independently by the reviewer from the
contribution tree baaf57f9; seed md5 b9a24e716aa09b3702ab3a0b38d8c4de /
sha256 e6d0805e..., reproduced byte-identically; every hardcoded fact
cross-checked against the frozen seed database) — never read from
tasks.jsonl.
Usage: python3 verify_5.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Steam--5"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_specials", r"/specials")
    check_visited_path(judge, traj, "nav_cheaper_game", r"/app/582660")
    check_visited_path(judge, traj, "nav_specials_indie", r"/specials/\\?[^ ]*genre=Indie")
    check_visited_path(judge, traj, "nav_specials_mac", r"/specials/\\?[^ ]*os=mac")
    check_visited_path(judge, traj, "nav_specials_sort_asc", r"/specials/\\?[^ ]*sort=Price_ASC")
    check_visited_path(judge, traj, "nav_specials_sort_desc", r"/specials/\\?[^ ]*sort=Price_DESC")
    check_visited_path(judge, traj, "nav_expensive_special", r"/app/1145350")
    check_visited_path(judge, traj, "nav_login", r"/account/login")
    check_visited_path(judge, traj, "nav_wishlist", r"/wishlist")
    check_answer_number(judge, answer, "specials_total", 24)
    check_answer_phrase(judge, answer, "top1_name", "Black Desert")
    check_answer_number(judge, answer, "top1_discount", 90)
    check_answer_money(judge, answer, "top1_original", 9.99)
    check_answer_money(judge, answer, "top1_current", 0.99)
    check_answer_money(judge, answer, "top1_savings", 9.00)
    check_answer_phrase(judge, answer, "top2_name", "The Division")
    check_answer_number(judge, answer, "top2_discount", 90)
    check_answer_money(judge, answer, "top2_original", 29.99)
    check_answer_money(judge, answer, "top2_current", 2.99)
    check_answer_money(judge, answer, "top2_savings", 27.00)
    check_answer_phrase(judge, answer, "cheaper_name", "Black Desert")
    check_answer_phrase(judge, answer, "cheaper_summary", "Mostly Positive")
    check_answer_phrase(judge, answer, "cheaper_release", "May 24, 2017")
    check_answer_number(judge, answer, "indie_specials", 6)
    check_answer_number(judge, answer, "mac_specials", 4)
    check_answer_phrase(judge, answer, "cheapest_special_name", "American Truck Simulator")
    check_answer_money(judge, answer, "cheapest_special_price", 4.99)
    check_answer_money(judge, answer, "expensive_special_price", 29.99)
    check_answer_phrase(judge, answer, "expensive_special_summary", "Overwhelmingly Positive")
    check_answer_number(judge, answer, "wishlist_count", 4)
    check_rows_added(judge, initial, after, "wishlist_items",
                     [[None, 3, 48, "rx:^20"]], "db_wishlist_add")
    check_only_tables_changed(judge, initial, after, {"wishlist_items"})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
