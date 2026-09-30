#!/usr/bin/env python3
"""Deterministic verifier for Disney--10 (disney).

Ground truth below is HARDCODED from the reviewer's independent Playwright
honest-path walk on the r2 review container (wh-disney-r2-review, seed md5
9f231a5a…) — never read from tasks.jsonl.

Usage: python3 verify_10.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Disney--10"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "toys_sorted", r"""/shop/toys\?[^\" ]*sort=price_high"""),
    check_visited_path(judge, traj, "top_detail", r"""/shop/products/416120689757"""),
    check_visited_path(judge, traj, "bag", r"""/bag"""),
    check_visited_path(judge, traj, "checkout", r"""/checkout"""),
    check_visited_path(judge, traj, "order_confirmed", r"""/order/DS"""),
    check_visited_path(judge, traj, "action_figures", r"""/shop/toys\?[^\" ]*category=Action\+Figures"""),
    # -- answer ground truth --
    check_answer_number(judge, answer, "toys_count", 48)
    check_answer_phrase(judge, answer, "most_expensive", "Disney Princess Classic Doll Collection Gift Set")
    check_answer_money(judge, answer, "price", 149.99)
    check_answer_number(judge, answer, "rating", 1.0)
    check_answer_money(judge, answer, "bag_line_2x", 299.98)
    check_answer_money(judge, answer, "bag_line_1x", 149.99)
    check_answer_money(judge, answer, "order_total", 149.99)
    check_answer_regex(judge, answer, "confirmation", r"DS[0-9A-F]{7}")
    check_answer_number(judge, answer, "action_figures_count", 15)

    check_only_tables_changed(judge, initial, after, {"cart_items", "shop_orders"})
    check_rows_added(judge, initial, after, "shop_orders", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM shop_orders WHERE email='toy.buyer@example.com' AND total=149.99",
        (), "order_row")
    check_rows_added(judge, initial, after, "cart_items", 0)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
