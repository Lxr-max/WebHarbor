#!/usr/bin/env python3
"""Deterministic verifier for Steam--3 (steam).

Ground truth below is HARDCODED from the reviewer's two independent honest
Playwright rounds on the review container wh-steam-review (image
webharbor:steam-review, built independently by the reviewer from the
contribution tree baaf57f9; seed md5 b9a24e716aa09b3702ab3a0b38d8c4de /
sha256 e6d0805e..., reproduced byte-identically; every hardcoded fact
cross-checked against the frozen seed database) — never read from
tasks.jsonl.
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

TASK_ID = "Steam--3"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_login", r"/account/login")
    check_visited_path(judge, traj, "nav_wishlist", r"/wishlist")
    check_visited_path(judge, traj, "nav_search_hades2", r"/search/\\?[^ ]*term=Hades")
    check_visited_path(judge, traj, "nav_hades2", r"/app/1145350")
    check_visited_path(judge, traj, "nav_search_casual", r"/search/\\?[^ ]*genre=Casual[^ ]*maxprice=10|/search/\\?[^ ]*maxprice=10[^ ]*genre=Casual")
    check_visited_path(judge, traj, "nav_casual_game", r"/app/1794680")
    check_answer_money(judge, answer, "hades2_price", 20.99)
    check_answer_number(judge, answer, "hades2_discount", 30)
    check_answer_money(judge, answer, "hades2_original", 29.99)
    check_answer_phrase(judge, answer, "hades2_release", "Sep 25, 2025")
    check_answer_phrase(judge, answer, "casual_name", "Vampire Survivors")
    check_answer_money(judge, answer, "casual_price", 4.99)
    check_answer_number(judge, answer, "wishlist_count", 4)
    check_rows_removed(judge, initial, after, "wishlist_items",
                       [[None, 3, 19, "2026-09-11T12:00:00Z"]], "db_wishlist_remove")
    check_rows_added(judge, initial, after, "wishlist_items",
                     [[None, 3, 65, "rx:^20"], [None, 3, 85, "rx:^20"]],
                     "db_wishlist_add")
    check_only_tables_changed(judge, initial, after, {"wishlist_items"})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
