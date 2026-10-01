#!/usr/bin/env python3
"""Deterministic verifier for Red Bull--11 (red_bull).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-red-bull-review, seed md5
2e3f7d1ce9c852f434d394942fe9fa57, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_11.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Red Bull--11"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_all(judge, traj, "nav_surfaces", [
        r"/shop\?[^ ]*vendor=Oracle\+Red\+Bull\+Racing",
        r"/shop/oracle-red-bull-racing-classic-longsleeve-polo-copy$",
        r"/shop\?[^ ]*sort=price_asc",
        r"/shop/rb-leipzig-3d-sticker$",
        r"/shop\?[^ ]*category=headwear",
        r"/shop\?[^ ]*vendor=Red\+Bull\+Rampage",
        r"/shop\?[^ ]*category=bags",
    ])
    check_answer_phrase(judge, answer, "hoodie_material", "soft cotton blend")
    check_answer_money(judge, answer, "hoodie_xs_price", 114.95)
    check_answer_any(judge, answer, "hoodie_category", ["tops", "Tops"])
    check_answer_phrase(judge, answer, "cheapest_title", "RB Leipzig 3D Sticker")
    check_answer_money(judge, answer, "cheapest_price", 4.50)
    check_answer_any(judge, answer, "cheapest_category", ["accessories", "Accessories"])
    check_answer_number(judge, answer, "headwear_count", 57)
    check_answer_number(judge, answer, "rampage_count", 22)
    check_answer_number(judge, answer, "bags_count", 19)
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
