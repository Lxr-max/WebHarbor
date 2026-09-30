#!/usr/bin/env python3
"""Deterministic verifier for Disney--13 (disney).

Ground truth below is HARDCODED from the reviewer's independent Playwright
honest-path walk on the r2 review container (wh-disney-r2-review, seed md5
9f231a5a…) — never read from tasks.jsonl.
    r2 note: the search now lists the full Shop result set (25 plush
    products, count == listed rows), and the task no longer asks for the
    first plush's review count (upstream has none for it).

Usage: python3 verify_13.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent,
    check_answer_any,
    check_answer_count_at_least,
    check_answer_number,
    check_answer_number_absent,
    check_answer_ordered,
    check_answer_money,
    check_answer_phrase,
    check_answer_regex,
    check_only_tables_changed,
    check_read_only,
    check_row_matches,
    check_rows_added,
    check_screenshots,
    check_seed_contract,
    check_trajectory_identity,
    check_visited_all,
    check_visited_any,
    check_visited_path,
    run_verifier
)

TASK_ID = "Disney--13"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "plush_search", r"""/search\?[^\" ]*q=plush"""),
    check_visited_path(judge, traj, "first_plush_detail", r"""/shop/products/194735352982"""),
    check_visited_path(judge, traj, "tote_search", r"""/search\?[^\" ]*q=tote"""),
    check_visited_path(judge, traj, "first_tote_detail", r"""/shop/products/442030853759"""),
    check_visited_path(judge, traj, "bag", r"""/bag"""),
    check_visited_path(judge, traj, "checkout", r"""/checkout"""),
    check_visited_path(judge, traj, "order_confirmed", r"""/order/DS"""),
    # -- answer ground truth --
    check_answer_number(judge, answer, "plush_count", 25)
    check_answer_phrase(judge, answer, "first_plush", "Blaze Manoukian's Pet Pig Plush with Sound by Mattel")
    check_answer_money(judge, answer, "first_plush_price", 32.99)
    check_answer_phrase(judge, answer, "first_tote", "Disneyland Canvas Tote")
    check_answer_money(judge, answer, "bag_total_before", 122.97)
    check_answer_money(judge, answer, "bag_total_after", 89.98)
    check_answer_number(judge, answer, "bag_items_after", 1)
    check_answer_money(judge, answer, "order_total", 89.98)
    check_answer_regex(judge, answer, "confirmation", r"DS[0-9A-F]{7}")

    check_only_tables_changed(judge, initial, after, {"cart_items", "shop_orders"})
    check_rows_added(judge, initial, after, "shop_orders", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM shop_orders WHERE email='shop.compare@example.com' AND total=89.98",
        (), "order_row")
    check_rows_added(judge, initial, after, "cart_items", 0)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
