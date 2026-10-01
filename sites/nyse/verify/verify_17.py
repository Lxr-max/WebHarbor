#!/usr/bin/env python3
"""Deterministic verifier for NYSE--17 (nyse).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the r2 review container wh-nyse-r2, seed md5
b7c3bbfa3a7a64b8d09b4e7fb3323fd9, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_17.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "NYSE--17"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Header search Vanguard (listings + bell counts); bell calendar Vanguard
    # description first sentence; KO quote div yield + beta; alice alert
    # below 80 (Pending) + total; first NYSE American mover last price.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/search\?q=Vanguard",
        r"/bell/calendar\?q=Vanguard",
        r"/listings_directory/stock\?q=KO",
        r"/quote/XNYS:KO",
        r"/login",
        r"/alerts",
        r"/markets",
    ])
    check_answer_number(judge, answer, "listings_matches", 5)
    check_answer_number(judge, answer, "bell_matches", 2)
    check_answer_phrase(judge, answer, "vanguard_desc_first",
        "The New York Stock Exchange welcomes Vanguard in celebration of 25 years of Vanguard ETFs")
    check_answer_price(judge, answer, "KO_divyield", 2.44)
    check_answer_price(judge, answer, "KO_beta", 0.34)
    check_answer_phrase(judge, answer, "alert_status", "Pending")
    check_answer_number(judge, answer, "alice_alert_total", 2)
    check_answer_price(judge, answer, "first_american_last", 3.27)
    check_only_tables_changed(judge, initial, after, {"price_alerts"})
    check_rows_added(judge, initial, after, "price_alerts", [
        [None, 1, "KO", "below", 80.0, None, "2026-09-29"],
    ], "alert_row_added")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
