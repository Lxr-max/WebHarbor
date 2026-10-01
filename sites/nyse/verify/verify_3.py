#!/usr/bin/env python3
"""Deterministic verifier for NYSE--3 (nyse).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the r2 review container wh-nyse-r2, seed md5
b7c3bbfa3a7a64b8d09b4e7fb3323fd9, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_3.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "NYSE--3"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # KO quote (last, 52w-high date, 5Y axis), AA 52w low, bob login,
    # KO alert above 100 with note, bob alert total.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/listings_directory/stock\?q=Coca-Cola",
        r"/quote/XNYS:KO(\?zoom=1Y)?",
        r"/quote/XNYS:KO\?zoom=1Y",
        r"/quote/XNYS:KO\?zoom=5Y",
        r"/listings_directory/stock\?q=Alcoa",
        r"/quote/XNYS:AA",
        r"/login",
        r"/quote/XNYS:KO",
        r"/alerts",
    ])
    check_answer_price(judge, answer, "KO_last", 86.84)
    check_answer_phrase(judge, answer, "KO_wh52date", "Monday, August 24, 2026")
    check_answer_any(judge, answer, "KO_5y_first", ["2021/09/30", "2021-09-30", "September 30, 2021"])
    check_answer_price(judge, answer, "AA_wl52", 32.85)
    check_answer_number(judge, answer, "bob_alert_total", 3)
    check_only_tables_changed(judge, initial, after, {"price_alerts"})
    check_rows_added(judge, initial, after, "price_alerts", [
        [None, 2, "KO", "above", 100.0, "Blue-chip entry", "2026-09-29"],
    ], "alert_row_added")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
