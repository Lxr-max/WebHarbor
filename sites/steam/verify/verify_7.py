#!/usr/bin/env python3
"""Deterministic verifier for Steam--7 (steam).

Ground truth below is HARDCODED from the reviewer's two independent honest
Playwright rounds on the review container wh-steam-review (image
webharbor:steam-review, built independently by the reviewer from the
contribution tree baaf57f9; seed md5 b9a24e716aa09b3702ab3a0b38d8c4de /
sha256 e6d0805e..., reproduced byte-identically; every hardcoded fact
cross-checked against the frozen seed database) — never read from
tasks.jsonl.
Usage: python3 verify_7.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Steam--7"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_cs2", r"/app/730")
    check_visited_path(judge, traj, "nav_developer_valve", r"/developer/valve")
    check_visited_path(judge, traj, "nav_dota2", r"/app/570")
    check_visited_path(judge, traj, "nav_tf2", r"/app/440")
    check_visited_path(judge, traj, "nav_alyx", r"/app/546560")
    check_visited_path(judge, traj, "nav_cart", r"/cart")
    check_visited_path(judge, traj, "nav_publisher_valve", r"/publisher/valve")
    check_visited_path(judge, traj, "nav_login", r"/account/login")
    check_visited_path(judge, traj, "nav_wishlist", r"/wishlist")
    check_answer_number(judge, answer, "dev_games", 17)
    check_answer_phrase(judge, answer, "most_expensive_name", "Half-Life: Alyx")
    check_answer_money(judge, answer, "most_expensive_price", 59.99)
    check_answer_count_at_least(judge, answer, "free_games", ["Counter-Strike 2", "Dota 2", "Team Fortress 2"], 3)
    check_answer_phrase(judge, answer, "cs2_release", "Aug 21, 2012")
    check_answer_phrase(judge, answer, "cs2_summary", "Very Positive")
    check_answer_phrase(judge, answer, "dota_release", "Jul 9, 2013")
    check_answer_phrase(judge, answer, "dota_summary", "Very Positive")
    check_answer_phrase(judge, answer, "tf2_release", "Oct 10, 2007")
    check_answer_phrase(judge, answer, "tf2_summary", "Very Positive")
    check_answer_phrase(judge, answer, "me_release", "Mar 23, 2020")
    check_answer_phrase(judge, answer, "me_summary", "Overwhelmingly Positive")
    check_answer_money(judge, answer, "subtotal", 59.99)
    check_answer_number(judge, answer, "pub_games", 19)
    check_answer_number(judge, answer, "wishlist_count", 2)
    check_rows_added(judge, initial, after, "wishlist_items",
                     [[None, 4, 44, "rx:^20"]], "db_wishlist_add")
    check_only_tables_changed(judge, initial, after, {"wishlist_items"})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
