#!/usr/bin/env python3
"""Deterministic verifier for Steam--0 (steam).

Ground truth below is HARDCODED from the reviewer's two independent honest
Playwright rounds on the review container wh-steam-review (image
webharbor:steam-review, built independently by the reviewer from the
contribution tree baaf57f9; seed md5 b9a24e716aa09b3702ab3a0b38d8c4de /
sha256 e6d0805e..., reproduced byte-identically; every hardcoded fact
cross-checked against the frozen seed database) — never read from
tasks.jsonl.
Usage: python3 verify_0.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Steam--0"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_search", r"/search/\\?[^ ]*genre=RPG")
    check_visited_path(judge, traj, "nav_search_price", r"/search/\\?[^ ]*maxprice=20")
    check_visited_path(judge, traj, "nav_search_discounted", r"/search/\\?[^ ]*specials=1")
    check_visited_path(judge, traj, "nav_search_sort_price", r"/search/\\?[^ ]*sort=Price_ASC")
    check_visited_path(judge, traj, "nav_game", r"/app/582660")
    check_visited_path(judge, traj, "nav_login", r"/account/login")
    check_visited_path(judge, traj, "nav_wishlist", r"/wishlist")
    check_answer_number(judge, answer, "rpg_under20", 15)
    check_answer_number(judge, answer, "rpg_discounted", 9)
    check_answer_phrase(judge, answer, "cheapest_name", "Black Desert")
    check_answer_money(judge, answer, "cheapest_price", 0.99)
    check_answer_phrase(judge, answer, "review_summary", "Mostly Positive")
    check_answer_phrase(judge, answer, "release_date", "May 24, 2017")
    check_answer_number(judge, answer, "total_reviews", 51519)
    check_answer_number(judge, answer, "wishlist_count", 3)
    check_rows_added(judge, initial, after, "wishlist_items",
                     [[None, 1, 48, "rx:^20"]], "db_wishlist_add")
    check_only_tables_changed(judge, initial, after, {"wishlist_items"})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
