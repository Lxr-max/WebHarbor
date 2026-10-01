#!/usr/bin/env python3
"""Deterministic verifier for Steam--12 (steam).

Ground truth below is HARDCODED from the reviewer's two independent honest
Playwright rounds on the review container wh-steam-review (image
webharbor:steam-review, built independently by the reviewer from the
contribution tree baaf57f9; seed md5 b9a24e716aa09b3702ab3a0b38d8c4de /
sha256 e6d0805e..., reproduced byte-identically; every hardcoded fact
cross-checked against the frozen seed database) — never read from
tasks.jsonl.
Usage: python3 verify_12.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Steam--12"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_login", r"/account/login")
    check_visited_path(judge, traj, "nav_account", r"/account")
    check_visited_path(judge, traj, "nav_search_l4d2", r"/search/\\?[^ ]*term=Left")
    check_visited_path(judge, traj, "nav_l4d2", r"/app/550")
    check_visited_path(judge, traj, "nav_cart", r"/cart")
    check_visited_path(judge, traj, "nav_checkout", r"/checkout")
    check_visited_path(judge, traj, "nav_order", r"/order/ST-1004")
    check_answer_phrase(judge, answer, "existing_order", "ST-1001")
    check_answer_money(judge, answer, "existing_total", 19.98)
    check_answer_phrase(judge, answer, "new_order", "ST-1004")
    check_answer_money(judge, answer, "new_total", 9.99)
    check_answer_number(judge, answer, "orders_after", 2)
    check_answer_phrase(judge, answer, "payment", "Visa")
    check_rows_added(judge, initial, after, "orders",
                     [[None, "ST-1004", 1, "alice.j@test.com", "Alice Johnson",
                       "42 Pipeline Way", "Bellevue", "WA", "98004", "Visa",
                       999, 0, 999, "rx:^20"]], "db_order")
    check_rows_added(judge, initial, after, "order_items",
                     [[None, None, "game", 15, None, "Left 4 Dead 2", 999, 1]],
                     "db_order_items")
    check_only_tables_changed(judge, initial, after, {"orders", "order_items"})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
