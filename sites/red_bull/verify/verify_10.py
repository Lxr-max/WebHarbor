#!/usr/bin/env python3
"""Deterministic verifier for Red Bull--10 (red_bull).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-red-bull-review, seed md5
2e3f7d1ce9c852f434d394942fe9fa57, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_10.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Red Bull--10"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_all(judge, traj, "nav_surfaces", [
        r"/account/login$",
        r"/account$",
        r"/shop\?[^ ]*category=headwear[^ ]*vendor=Oracle\+Red\+Bull\+Racing[^ ]*sort=price_asc",
        r"/shop/oracle-red-bull-racing-monobranded-9forty-orbr-cap$",
        r"/cart$",
        r"/shop/checkout$",
        r"/shop/orders/RB-\d+",
    ])
    check_answer_phrase(judge, answer, "cheap_title", "Monobranded 9Forty ORBR Cap")
    check_answer_money(judge, answer, "cheap_price", 33.95)
    check_answer_regex(judge, answer, "order_number", r"RB-\d{6}")
    check_answer_money(judge, answer, "order_total", 67.90)
    check_only_tables_changed(judge, initial, after, {"shop_orders", "shop_order_lines"})
    check_rows_added(judge, initial, after, "shop_orders", [
        [None, "rx:^RB-\d{6}$", 1, "confirmed", None, 67.90, "Alice Johnson", "alice.j@test.com"],
    ], "order_row")
    check_rows_added(judge, initial, after, "shop_order_lines", [
        [None, None, 161, "Oracle Red Bull Racing Monobranded 9Forty ORBR Cap",
         None, "rx:.*", 33.95, 2],
    ], "order_line_row")
    import re as _re
    nums = [r[0] for r in after.execute("SELECT order_number FROM shop_orders WHERE user_id=1")]
    fresh = [n for n in nums if n != "RB-100234"]
    if fresh and _re.search(rf"{fresh[0]}", answer):
        judge.ok("answer_order_matches_db", fresh[0])
    else:
        judge.fail("answer_order_matches_db", f"answer lacks DB order number {fresh}")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
