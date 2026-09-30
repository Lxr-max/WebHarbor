#!/usr/bin/env python3
"""Deterministic verifier for Disney--11 (disney).

Audit-redesigned chain (100-word task): Sale count -> Mickey Mouse count ->
top-rated price+rating -> add one -> full Sale price_low cheapest price ->
Accessories Bags & Wallets count -> first result price+review count -> add ->
new bag total -> Keychains & Bag Charms count. Measured 18 honest atomic
steps by the audit's own Playwright walk (footer-direct collection opens;
the Add-to-Bag redirect lands on /bag so no extra navigation exists).

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

TASK_ID = "Disney--11"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "sale", r"""/shop/sale($|\?)""")
    check_visited_path(judge, traj, "sale_mickey", r"""/shop/sale\?[^\" ]*character=Mickey\+Mouse""")
    check_visited_path(judge, traj, "sale_mickey_sorted", r"""/shop/sale\?[^\" ]*character=Mickey\+Mouse[^\" ]*sort=rating|/shop/sale\?[^\" ]*sort=rating[^\" ]*character=Mickey\+Mouse""")
    check_visited_path(judge, traj, "top_detail", r"""/shop/products/415130694607""")
    check_visited_path(judge, traj, "sale_price_low", r"""/shop/sale\?[^\" ]*sort=price_low""")
    check_visited_path(judge, traj, "accessories_bags", r"""/shop/accessories\?[^\" ]*category=Bags""")
    check_visited_path(judge, traj, "first_bag_detail", r"""/shop/products/442111075919""")
    check_visited_path(judge, traj, "bag", r"""/bag""")
    check_visited_path(judge, traj, "keychains", r"""/shop/accessories\?[^\" ]*category=Keychains""")
    # -- answer ground truth (audit walk on wh-disney-audit, reset per task) --
    check_answer_number(judge, answer, "sale_count", 6)
    check_answer_number(judge, answer, "sale_mickey_count", 3)
    check_answer_phrase(judge, answer, "top_rated", "Mickey Mouse Halloween 2026 Plush")
    check_answer_money(judge, answer, "top_price", 29.99)
    check_answer_number(judge, answer, "top_rating", 5.0)
    check_answer_phrase(judge, answer, "cheapest_sale", "Mickey Mouse Jack-o'-Lantern Treat Bucket")
    check_answer_money(judge, answer, "cheapest_price", 24.99)
    check_answer_number(judge, answer, "bags_wallets_count", 17)
    check_answer_phrase(judge, answer, "first_bag", "Mickey Mouse Tote by Harveys")
    check_answer_money(judge, answer, "first_bag_price", 198.00)
    check_answer_number(judge, answer, "first_bag_reviews", 7)
    check_answer_money(judge, answer, "new_bag_total", 227.99)
    check_answer_number(judge, answer, "keychains_count", 15)

    check_only_tables_changed(judge, initial, after, {"cart_items"})
    check_rows_added(judge, initial, after, "cart_items", 2)
    check_row_matches(judge, after,
        "SELECT 1 FROM cart_items WHERE product_pid='415130694607' AND qty=1",
        (), "bag_row_plush")
    check_row_matches(judge, after,
        "SELECT 1 FROM cart_items WHERE product_pid='442111075919' AND qty=1",
        (), "bag_row_tote")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
