#!/usr/bin/env python3
"""Deterministic verifier for Backcountry--11 (backcountry).

Ground truth below is HARDCODED (frozen from the two independent honest-step
rounds on the dev container wh-backcountry-dev, image
webharbor:backcountry-dev, seed md5 44da2a3fc213b3ac5e76ba11453baee2 — both
rounds measured identical step counts and identical answers) — never read
from tasks.jsonl.
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

TASK_ID = "Backcountry--11"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_login", r"/login")
    check_visited_path(judge, traj, "nav_orders", r"/account")
    check_visited_path(judge, traj, "nav_order_detail", r"/account/orders/8004193147")
    check_visited_path(judge, traj, "nav_addresses", r"/account/addresses")
    check_answer_number(judge, answer, "order", 8004193147)
    check_answer_phrase(judge, answer, "status", 'Shipped')
    check_answer_money(judge, answer, "total", 115.0)
    check_answer_phrase(judge, answer, "items", "Classic Thermal Merino Crew Baselayer - Women's")
    check_answer_number(judge, answer, "after_add", 3)
    check_answer_number(judge, answer, "final", 2)
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
