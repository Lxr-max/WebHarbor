#!/usr/bin/env python3
"""Deterministic verifier for NYSE--16 (nyse).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the r2 review container wh-nyse-r2, seed md5
b7c3bbfa3a7a64b8d09b4e7fb3323fd9, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_16.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "NYSE--16"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # DIS quote (sector, 52w low, dividend yield); alice watchlist count;
    # DIS alert above 200 note Media momentum; bob alerts total + symbols.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/listings_directory/stock\?q=Disney",
        r"/quote/XNYS:DIS",
        r"/login",
        r"/watchlist",
        r"/alerts",
        r"/login",
        r"/alerts",
    ])
    check_answer_phrase(judge, answer, "DIS_sector", "Media & Communications")
    check_answer_price(judge, answer, "DIS_wl52", 92.19)
    check_answer_price(judge, answer, "DIS_divyield", 1.42)
    check_answer_number(judge, answer, "alice_symbols", 3)
    check_answer_number(judge, answer, "bob_alert_total", 2)
    check_answer_count_at_least(judge, answer, "bob_alert_symbols", ["AAPL", "TSLA"], 2)
    check_only_tables_changed(judge, initial, after, {"price_alerts"})
    check_rows_added(judge, initial, after, "price_alerts", [
        [None, 1, "DIS", "above", 200.0, "Media momentum", "2026-09-29"],
    ], "alert_row_added")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
