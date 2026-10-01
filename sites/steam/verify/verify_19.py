#!/usr/bin/env python3
"""Deterministic verifier for Steam--19 (steam).

Ground truth below is HARDCODED from the reviewer's two independent honest
Playwright rounds on the review container wh-steam-review (image
webharbor:steam-review, built independently by the reviewer from the
contribution tree baaf57f9; seed md5 b9a24e716aa09b3702ab3a0b38d8c4de /
sha256 e6d0805e..., reproduced byte-identically; every hardcoded fact
cross-checked against the frozen seed database) — never read from
tasks.jsonl.
Usage: python3 verify_19.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Steam--19"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_search_cyberpunk", r"/search/\\?[^ ]*term=Cyberpunk")
    check_visited_path(judge, traj, "nav_cyberpunk", r"/app/1091500")
    check_visited_path(judge, traj, "nav_search_elden", r"/search/\\?[^ ]*term=ELDEN")
    check_visited_path(judge, traj, "nav_elden", r"/app/1245620")
    check_visited_path(judge, traj, "nav_cp_reviews", r"/app/1091500/reviews")
    check_visited_path(judge, traj, "nav_cart", r"/cart")
    check_visited_path(judge, traj, "nav_login", r"/account/login")
    check_visited_path(judge, traj, "nav_wishlist", r"/wishlist")
    check_answer_phrase(judge, answer, "cp_min_ram", "12 GB RAM")
    check_answer_phrase(judge, answer, "cp_rec_ram", "16 GB RAM")
    check_answer_regex(judge, answer, "cp_gpu", r"geforce gtx 1060 6gb")
    check_answer_phrase(judge, answer, "cp_storage", "70 GB available space")
    check_answer_phrase(judge, answer, "er_min_ram", "12 GB RAM")
    check_answer_phrase(judge, answer, "er_rec_ram", "16 GB RAM")
    check_answer_regex(judge, answer, "er_gpu", r"gtx 1060 3 gb")
    check_answer_phrase(judge, answer, "er_storage", "60 GB available space")
    check_answer_phrase(judge, answer, "more_storage", "Cyberpunk 2077 needs more storage")
    check_answer_phrase(judge, answer, "macos", "supports macOS")
    check_answer_money(judge, answer, "er_price", 59.99)
    check_answer_phrase(judge, answer, "er_summary", "Very Positive")
    check_answer_phrase(judge, answer, "cp_reviews_summary", "Very Positive")
    check_answer_number(judge, answer, "cp_reviews_shown", 10)
    check_answer_money(judge, answer, "subtotal", 59.99)
    check_answer_number(judge, answer, "wishlist_count", 2)
    check_rows_added(judge, initial, after, "wishlist_items",
                     [[None, 4, 72, "rx:^20"]], "db_wishlist_add")
    check_only_tables_changed(judge, initial, after, {"wishlist_items"})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
