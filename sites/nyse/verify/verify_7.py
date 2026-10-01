#!/usr/bin/env python3
"""Deterministic verifier for NYSE--7 (nyse).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the r2 review container wh-nyse-r2, seed md5
b7c3bbfa3a7a64b8d09b4e7fb3323fd9, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_7.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_number, check_answer_number_absent, check_answer_ordered,
    check_answer_phrase, check_answer_price, check_answer_regex,
    check_answer_zero_or_phrase, check_read_only, check_rows_added,
    check_rows_removed, check_only_tables_changed, check_screenshots,
    check_seed_contract, check_trajectory_identity, check_visited_all,
    check_visited_any, check_visited_path, final_answer, run_verifier,
)

TASK_ID = "NYSE--7"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Markets NYSE American top-volume (SDEV) quote; dana login; alert above 5
    # (Pending), totals 2 -> 1 after delete; CCL 52w-high date. Read-only net
    # (the created alert is the one deleted; any other delta FAILS).
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/markets",
        r"/quote/XASE:SDEV",
        r"/login",
        r"/alerts",
        r"/listings_directory/stock\?q=Carnival",
        r"/quote/XNYS:CCL",
    ])
    check_answer_phrase(judge, answer, "top_am_symbol", "SDEV")
    check_answer_price(judge, answer, "SDEV_last", 3.27)
    check_answer_price(judge, answer, "SDEV_wl52", 0.78)
    check_answer_phrase(judge, answer, "alert_status", "Pending")
    check_answer_number(judge, answer, "dana_alert_total", 2)
    check_answer_number(judge, answer, "dana_new_total", 1)
    check_answer_phrase(judge, answer, "CCL_wh52date", "Friday, February 06, 2026")
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
