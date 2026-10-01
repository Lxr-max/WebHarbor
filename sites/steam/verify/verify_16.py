#!/usr/bin/env python3
"""Deterministic verifier for Steam--16 (steam).

Ground truth below is HARDCODED from the reviewer's two independent honest
Playwright rounds on the review container wh-steam-review (image
webharbor:steam-review, built independently by the reviewer from the
contribution tree baaf57f9; seed md5 b9a24e716aa09b3702ab3a0b38d8c4de /
sha256 e6d0805e..., reproduced byte-identically; every hardcoded fact
cross-checked against the frozen seed database) — never read from
tasks.jsonl.
Usage: python3 verify_16.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Steam--16"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_search_resident", r"/search/\\?[^ ]*term=resident")
    check_visited_path(judge, traj, "nav_search_action", r"/search/\\?[^ ]*term=resident[^ ]*genre=Action|/search/\\?[^ ]*genre=Action[^ ]*term=resident")
    check_visited_path(judge, traj, "nav_re2", r"/app/883710")
    check_visited_path(judge, traj, "nav_village", r"/app/1196590")
    check_visited_path(judge, traj, "nav_re4", r"/app/2050650")
    check_visited_path(judge, traj, "nav_re4_reviews", r"/app/2050650/reviews")
    check_visited_path(judge, traj, "nav_re4_news", r"/news/2050650")
    check_visited_path(judge, traj, "nav_login", r"/account/login")
    check_visited_path(judge, traj, "nav_wishlist", r"/wishlist")
    check_answer_number(judge, answer, "resident_count", 3)
    check_answer_count_at_least(judge, answer, "resident_names", ["Resident Evil 2", "Resident Evil Village", "Resident Evil 4"], 3)
    check_answer_number(judge, answer, "action_count", 3)
    check_answer_money(judge, answer, "re2_price", 39.99)
    check_answer_phrase(judge, answer, "re2_release", "Jan 24, 2019")
    check_answer_money(judge, answer, "village_price", 39.99)
    check_answer_phrase(judge, answer, "village_release", "May 6, 2021")
    check_answer_money(judge, answer, "re4_price", 39.99)
    check_answer_phrase(judge, answer, "re4_release", "Mar 23, 2023")
    check_answer_phrase(judge, answer, "newest_name", "Resident Evil 4")
    check_answer_phrase(judge, answer, "newest_summary", "Overwhelmingly Positive")
    check_answer_regex(judge, answer, "newest_news", r"[Сс]разу шесть игр|Resident Evil")
    check_answer_number(judge, answer, "wishlist_count", 4)
    check_rows_added(judge, initial, after, "wishlist_items",
                     [[None, 3, 92, "rx:^20"]], "db_wishlist_add")
    check_only_tables_changed(judge, initial, after, {"wishlist_items"})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
