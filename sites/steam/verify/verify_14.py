#!/usr/bin/env python3
"""Deterministic verifier for Steam--14 (steam).

Ground truth below is HARDCODED from the reviewer's two independent honest
Playwright rounds on the review container wh-steam-review (image
webharbor:steam-review, built independently by the reviewer from the
contribution tree baaf57f9; seed md5 b9a24e716aa09b3702ab3a0b38d8c4de /
sha256 e6d0805e..., reproduced byte-identically; every hardcoded fact
cross-checked against the frozen seed database) — never read from
tasks.jsonl.
Usage: python3 verify_14.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Steam--14"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_search_free", r"/search/\\?[^ ]*maxprice=free")
    check_visited_path(judge, traj, "nav_dota", r"/app/570")
    check_visited_path(judge, traj, "nav_cs2", r"/app/730")
    check_visited_path(judge, traj, "nav_tf2", r"/app/440")
    check_visited_path(judge, traj, "nav_login", r"/account/login")
    check_visited_path(judge, traj, "nav_wishlist", r"/wishlist")
    check_answer_number(judge, answer, "free_count", 14)
    check_answer_phrase(judge, answer, "dota_summary", "Very Positive")
    check_answer_number(judge, answer, "dota_pct", 88)
    check_answer_number(judge, answer, "dota_total", 840128)
    check_answer_phrase(judge, answer, "cs2_summary", "Very Positive")
    check_answer_number(judge, answer, "cs2_pct", 86)
    check_answer_number(judge, answer, "cs2_total", 2624184)
    check_answer_phrase(judge, answer, "higher_pct", "Dota 2")
    check_answer_phrase(judge, answer, "tf2_summary", "Very Positive")
    check_answer_number(judge, answer, "wishlist_count", 4)
    check_rows_added(judge, initial, after, "wishlist_items",
                     [[None, 4, 16, "rx:^20"], [None, 4, 18, "rx:^20"],
                      [None, 4, 13, "rx:^20"]], "db_wishlist_add")
    check_only_tables_changed(judge, initial, after, {"wishlist_items"})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
