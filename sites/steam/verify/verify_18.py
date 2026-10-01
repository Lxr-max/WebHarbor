#!/usr/bin/env python3
"""Deterministic verifier for Steam--18 (steam).

Ground truth below is HARDCODED from the reviewer's two independent honest
Playwright rounds on the review container wh-steam-review (image
webharbor:steam-review, built independently by the reviewer from the
contribution tree baaf57f9; seed md5 b9a24e716aa09b3702ab3a0b38d8c4de /
sha256 e6d0805e..., reproduced byte-identically; every hardcoded fact
cross-checked against the frozen seed database) — never read from
tasks.jsonl.
Usage: python3 verify_18.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Steam--18"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_specials", r"/specials")
    check_visited_path(judge, traj, "nav_ff7r", r"/app/1462040")
    check_visited_path(judge, traj, "nav_hades", r"/app/1145360")
    check_visited_path(judge, traj, "nav_cart", r"/cart")
    check_visited_path(judge, traj, "nav_login", r"/account/login")
    check_visited_path(judge, traj, "nav_checkout", r"/checkout")
    check_visited_path(judge, traj, "nav_order", r"/order/ST-1004")
    check_answer_number(judge, answer, "ff7r_discount", 75)
    check_answer_money(judge, answer, "ff7r_original", 39.99)
    check_answer_money(judge, answer, "ff7r_current", 9.99)
    check_answer_money(judge, answer, "ff7r_savings", 30.00)
    check_answer_number(judge, answer, "hades_discount", 75)
    check_answer_money(judge, answer, "hades_original", 24.99)
    check_answer_money(judge, answer, "hades_current", 6.24)
    check_answer_money(judge, answer, "hades_savings", 18.75)
    check_answer_money(judge, answer, "subtotal", 16.23)
    check_answer_phrase(judge, answer, "order_no", "ST-1004")
    check_answer_money(judge, answer, "order_total", 16.23)
    check_answer_phrase(judge, answer, "line_item1", "Hades")
    check_answer_phrase(judge, answer, "line_item2", "FINAL FANTASY VII REMAKE INTERGRADE")
    check_answer_phrase(judge, answer, "payment", "PayPal")
    check_rows_added(judge, initial, after, "orders",
                     [[None, "ST-1004", 4, "dana.k@test.com", "Dana Kim",
                       "88 Neon Street", "Seattle", "WA", "98101", "PayPal",
                       1623, 0, 1623, "rx:^20"]], "db_order")
    check_rows_added(judge, initial, after, "order_items",
                     [[None, None, "game", 66, None, "Hades", 624, 1],
                      [None, None, "game", 77, None, "FINAL FANTASY VII REMAKE INTERGRADE", 999, 1]],
                     "db_order_items")
    check_only_tables_changed(judge, initial, after, {"orders", "order_items"})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
