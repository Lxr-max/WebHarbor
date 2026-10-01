#!/usr/bin/env python3
"""Deterministic verifier for Steam--8 (steam).

Ground truth below is HARDCODED from the reviewer's two independent honest
Playwright rounds on the review container wh-steam-review (image
webharbor:steam-review, built independently by the reviewer from the
contribution tree baaf57f9; seed md5 b9a24e716aa09b3702ab3a0b38d8c4de /
sha256 e6d0805e..., reproduced byte-identically; every hardcoded fact
cross-checked against the frozen seed database) — never read from
tasks.jsonl.
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

TASK_ID = "Steam--8"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_cs2", r"/app/730")
    check_visited_path(judge, traj, "nav_cs2_news", r"/news/730")
    check_visited_path(judge, traj, "nav_cs2_post", r"/news/item/")
    check_visited_path(judge, traj, "nav_search_dota", r"/search/\\?[^ ]*term=Dota")
    check_visited_path(judge, traj, "nav_dota_news", r"/news/570")
    check_visited_path(judge, traj, "nav_login", r"/account/login")
    check_visited_path(judge, traj, "nav_wishlist", r"/wishlist")
    check_answer_phrase(judge, answer, "cs2_news_title", "Counter-Strike 2 Update")
    check_answer_phrase(judge, answer, "cs2_news_feed", "Community Announcements")
    check_answer_phrase(judge, answer, "cs2_news_date", "September 30, 2026")
    check_answer_phrase(judge, answer, "cs2_post_feed", "Community Announcements")
    check_answer_phrase(judge, answer, "dota_news_title", "7.41f Gameplay Patch")
    check_answer_phrase(judge, answer, "dota_news_feed", "Community Announcements")
    check_answer_phrase(judge, answer, "dota_news_date", "September 15, 2026")
    check_answer_phrase(judge, answer, "more_recent", "Counter-Strike 2")
    check_answer_phrase(judge, answer, "cs2_price", "Free To Play")
    check_answer_phrase(judge, answer, "cs2_summary", "Very Positive")
    check_answer_number(judge, answer, "wishlist_count", 4)
    check_rows_added(judge, initial, after, "wishlist_items",
                     [[None, 3, 16, "rx:^20"]], "db_wishlist_add")
    check_only_tables_changed(judge, initial, after, {"wishlist_items"})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
