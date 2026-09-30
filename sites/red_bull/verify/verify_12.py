#!/usr/bin/env python3
"""Deterministic verifier for Red Bull--12 (red_bull).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-red-bull-review, seed md5
2e3f7d1ce9c852f434d394942fe9fa57, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
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

TASK_ID = "Red Bull--12"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_all(judge, traj, "nav_surfaces", [
        r"/shop\?[^ ]*vendor=FC\+Red\+Bull\+Salzburg",
        r"/shop/fc-red-bull-salzburg-trazom-tote-bag$",
        r"/cart$",
        r"/shop/fc-red-bull-salzburg-trazom-t-shirt-i",
    ])
    check_answer_number(judge, answer, "salz_count", 10)
    check_answer_money(judge, answer, "salz_lowest", 14.95)
    check_answer_phrase(judge, answer, "bag_title", "Trazom Tote Bag")
    check_answer_money(judge, answer, "subtotal1", 14.95)
    check_answer_money(judge, answer, "subtotal2", 44.90)
    # r2 re-anchor: the second item's quantity is updated to 2
    check_answer_money(judge, answer, "subtotal3", 74.85)
    check_answer_any(judge, answer, "second_title", ["Trazom T-Shirt"])
    check_answer_any(judge, answer, "tshirt_remains", ["yes", "still in cart", "still"])
    check_answer_absent(judge, answer, "tote_removed", "Trazom Tote Bag remains")
    check_only_tables_changed(judge, initial, after, {"cart_items"})
    # the second-cheapest Salzburg product is one of the two $29.95 Trazom t-shirts;
    # after the quantity update + removal of the tote bag the cart holds exactly
    # that t-shirt with quantity 2
    tshirt_variants = {r[0] for r in after.execute(
        "SELECT sv.id FROM shop_variants sv JOIN shop_products p ON sv.product_id=p.id "
        "WHERE p.handle LIKE 'fc-red-bull-salzburg-trazom-t-shirt-%'")}
    check_rows_added(judge, initial, after, "cart_items", [
        [None, "rx:^[0-9a-f]{32}$", tshirt_variants, 2, None],
    ], "cart_row_tshirt_qty2")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
