#!/usr/bin/env python3
"""Deterministic verifier for NYSE--0 (nyse).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the r2 review container wh-nyse-r2, seed md5
b7c3bbfa3a7a64b8d09b4e7fb3323fd9, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl. Re-anchored
in the r2 re-freeze: the task's final leg now creates an A price alert
(below 170, note "Lab spinout") and reports its status plus Alice's alert
total.
Usage: python3 verify_0.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "NYSE--0"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Listings Directory Stocks search AGILENT -> A quote; options exp=3;
    # alice login; watch A; watchlist report; r2 leg: create an A alert
    # below 170 with note "Lab spinout" and report status + Alice's totals.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/listings_directory/stock\?q=AGILENT",
        r"/quote/XNYS:A(\?exp=3)?",
        r"/quote/XNYS:A\?exp=3",
        r"/login",
        r"/watchlist",
        r"/alerts",
    ])
    check_answer_phrase(judge, answer, "A_sector", "Healthcare")
    check_answer_phrase(judge, answer, "A_ceo", "Padraig McDonnell")
    check_answer_price(judge, answer, "A_exp3_lowest_strike", 60.00)
    check_answer_price(judge, answer, "A_pc_ratio", 0.75)
    check_answer_number(judge, answer, "alice_total", 4)
    check_answer_count_at_least(judge, answer, "alice_last_prices",
        ["86.84", "105.41", "35.84", "175.03"], 4)
    check_answer_phrase(judge, answer, "A_alert_status", "Pending")
    check_answer_number(judge, answer, "alice_alert_total", 2)
    check_only_tables_changed(judge, initial, after, {"watch_items", "price_alerts"})
    check_rows_added(judge, initial, after, "watch_items", [
        [None, 1, "A", "2026-09-29"],
    ], "watch_row_added")
    check_rows_added(judge, initial, after, "price_alerts", [
        [None, 1, "A", "below", 170.0, "Lab spinout", "2026-09-29"],
    ], "alert_row_added")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
