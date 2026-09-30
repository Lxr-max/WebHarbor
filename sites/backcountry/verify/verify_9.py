#!/usr/bin/env python3
"""Deterministic verifier for Backcountry--9 (backcountry).

Ground truth below is HARDCODED (frozen from the two independent honest-step
rounds on the dev container wh-backcountry-dev, image
webharbor:backcountry-dev, seed md5 44da2a3fc213b3ac5e76ba11453baee2 — both
rounds measured identical step counts and identical answers) — never read
from tasks.jsonl.
Usage: python3 verify_9.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Backcountry--9"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_cat", r"/cat/bike")
    check_visited_path(judge, traj, "nav_sale", r"sale=30")
    check_visited_path(judge, traj, "nav_sorted", r"sale=30.*sort=-discount|sort=-discount.*sale=30")
    check_visited_path(judge, traj, "nav_pdp_pants", r"backcountry-slickrock-pant-mens")
    check_visited_path(judge, traj, "nav_pdp_tights", r"gorewear-swiftride-thermo-bib-tights\+-mens|gorewear-swiftride")
    check_visited_path(judge, traj, "nav_cart", r"/cart")
    check_answer_phrase(judge, answer, "title", "BGA Slickrock Pant - Men's")
    check_answer_money(judge, answer, "sale", 64.5)
    check_answer_money(judge, answer, "list", 129.0)
    check_answer_phrase(judge, answer, "pct", '50% off')
    check_answer_money(judge, answer, "subtotal", 207.0)
    check_answer_money(judge, answer, "savings", 181.0)
    check_only_tables_changed(judge, initial, after, {"cart_items"})
    check_rows_added(judge, initial, after, "cart_items",
                      [[None, 2, None, "BCCZ2QX-MIDBLU-L", 2, "2026-09-30"], [None, 2, None, "GWRG0BX-BLA-L", 1, "2026-09-30"]], "two_cart_rows")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
