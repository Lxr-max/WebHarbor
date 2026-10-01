#!/usr/bin/env python3
"""Deterministic verifier for Steam--11 (steam).

Ground truth below is HARDCODED from the reviewer's two independent honest
Playwright rounds on the review container wh-steam-review (image
webharbor:steam-review, built independently by the reviewer from the
contribution tree baaf57f9; seed md5 b9a24e716aa09b3702ab3a0b38d8c4de /
sha256 e6d0805e..., reproduced byte-identically; every hardcoded fact
cross-checked against the frozen seed database) — never read from
tasks.jsonl.
Usage: python3 verify_11.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Steam--11"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_genre_indie", r"/genre/indie")
    check_visited_path(judge, traj, "nav_sort_released", r"/genre/indie/\\?[^ ]*sort=Released_DESC")
    check_visited_path(judge, traj, "nav_sort_price_desc", r"/genre/indie/\\?[^ ]*sort=Price_DESC")
    check_visited_path(judge, traj, "nav_expensive_game", r"/app/250760")
    check_visited_path(judge, traj, "nav_under15", r"/genre/indie/\\?[^ ]*maxprice=15")
    check_visited_path(judge, traj, "nav_newest_game", r"/app/1867240")
    check_visited_path(judge, traj, "nav_newest_reviews", r"/app/1867240/reviews")
    check_visited_path(judge, traj, "nav_login", r"/account/login")
    check_visited_path(judge, traj, "nav_wishlist", r"/wishlist")
    check_answer_number(judge, answer, "indie_total", 31)
    check_answer_phrase(judge, answer, "newest_name", "WARDOGS")
    check_answer_money(judge, answer, "newest_price", 39.99)
    check_answer_any(judge, answer, "newest_discounted", ["not discounted", "no discount"])
    check_answer_phrase(judge, answer, "expensive_name", "Shovel Knight: Treasure Trove")
    check_answer_money(judge, answer, "expensive_price", 39.99)
    check_answer_phrase(judge, answer, "expensive_release", "Jun 26, 2014")
    check_answer_number(judge, answer, "under15", 10)
    check_answer_phrase(judge, answer, "newest_summary", "Very Positive")
    check_answer_phrase(judge, answer, "newest_reviews_summary", "Very Positive")
    check_answer_number(judge, answer, "wishlist_count", 2)
    check_rows_added(judge, initial, after, "wishlist_items",
                     [[None, 4, 86, "rx:^20"]], "db_wishlist_add")
    check_only_tables_changed(judge, initial, after, {"wishlist_items"})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
