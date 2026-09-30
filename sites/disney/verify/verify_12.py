#!/usr/bin/env python3
"""Deterministic verifier for Disney--12 (disney).

Audit-redesigned chain (98-word task): Clothes Adults count -> T-Shirts
count -> price_low first result (price + rating + one bare-necessities
bullet) -> set qty 3 + add -> Toys count -> Plush count -> price_low
cheapest plush -> add 1 -> combined bag total. Measured 17 honest atomic
steps by the audit's own Playwright walk ("the first result" wording
kills the $36.99 tie ambiguity between the two cheapest adult T-shirts).

Ground truth below is HARDCODED from the audit's independent Playwright
honest-path walk on the audit container (seed md5 9f231a5a…) — never read
from tasks.jsonl.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_money,
    check_answer_number,
    check_answer_any,
    check_answer_phrase,
    check_only_tables_changed,
    check_row_matches,
    check_rows_added,
    check_screenshots,
    check_seed_contract,
    check_trajectory_identity,
    check_visited_path,
    run_verifier
)

TASK_ID = "Disney--12"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "clothes_adults", r"""/shop/clothing\?[^\" ]*target_age=Adults""")
    check_visited_path(judge, traj, "clothes_tshirts", r"""/shop/clothing\?[^\" ]*category=T-Shirts""")
    check_visited_path(judge, traj, "clothes_price_low", r"""/shop/clothing\?[^\" ]*sort=price_low""")
    check_visited_path(judge, traj, "first_detail", r"""/shop/products/5106057431232m""")
    check_visited_path(judge, traj, "toys", r"""/shop/toys($|\?)""")
    check_visited_path(judge, traj, "toys_plush", r"""/shop/toys\?[^\" ]*category=Plush""")
    check_visited_path(judge, traj, "toys_price_low", r"""/shop/toys\?[^\" ]*sort=price_low""")
    check_visited_path(judge, traj, "plush_detail", r"""/shop/products/463521109001""")
    check_visited_path(judge, traj, "bag", r"""/bag""")
    # -- answer ground truth (audit walk on wh-disney-audit, reset per task) --
    check_answer_number(judge, answer, "adults_count", 25)
    check_answer_number(judge, answer, "tshirts_count", 3)
    check_answer_phrase(judge, answer, "first_result", "Mickey and Minnie Mouse Cutie Ghost T-Shirt for Women")
    check_answer_money(judge, answer, "price", 36.99)
    check_answer_number(judge, answer, "rating", 3.5)
    check_answer_any(judge, answer, "bare_necessity", ["60% cotton / 40% polyester", "Imported"])
    check_answer_number(judge, answer, "toys_count", 48)
    check_answer_number(judge, answer, "plush_count", 13)
    check_answer_phrase(judge, answer, "cheapest_plush", "Mickey Mouse Mini Plush Magnet")
    check_answer_money(judge, answer, "plush_price", 16.99)
    check_answer_number(judge, answer, "combined_total", 127.96)

    check_only_tables_changed(judge, initial, after, {"cart_items"})
    check_rows_added(judge, initial, after, "cart_items", 2)
    check_row_matches(judge, after,
        "SELECT 1 FROM cart_items WHERE product_pid='5106057431232m' AND qty=3",
        (), "bag_row_tshirt")
    check_row_matches(judge, after,
        "SELECT 1 FROM cart_items WHERE product_pid='463521109001' AND qty=1",
        (), "bag_row_plush")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
