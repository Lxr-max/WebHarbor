#!/usr/bin/env python3
"""Deterministic verifier for NYSE--19 (nyse).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the r2 review container wh-nyse-r2, seed md5
b7c3bbfa3a7a64b8d09b4e7fb3323fd9, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.

r2 re-anchor: the AERO CEO question (whose honest answer was N/A as the
upstream API reports) is replaced by AERO's 52-week low plus the lowest
strike in the second options expiry tab, and the task's final leg creates an
AERO price alert above 16 and reports the status plus Carol's alert total.
Usage: python3 verify_19.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "NYSE--19"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Recent IPOs first Priced ticker/industry + 180d rows; Grupo Aeromexico
    # (AERO) quote sector + 52-week low + 1Y first + exp2 lowest strike;
    # carol watch AERO; total; r2 leg: AERO alert above 16 + status + total.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/ipo-center/recent-ipo(\?window=180)?",
        r"/ipo-center/recent-ipo\?window=180",
        r"/listings_directory/stock\?q=Grupo",
        r"/quote/XNYS:AERO",
        r"/quote/XNYS:AERO\?zoom=1Y",
        r"/quote/XNYS:AERO\?exp=2",
        r"/login",
        r"/watchlist",
        r"/alerts",
    ])
    check_answer_phrase(judge, answer, "first_priced_ticker", "ACCV")
    check_answer_phrase(judge, answer, "first_priced_industry", "Technology")
    check_answer_number(judge, answer, "rows_180", 10)
    check_answer_phrase(judge, answer, "AERO_sector", "Industrials")
    check_answer_price(judge, answer, "AERO_wl52", 12.26)
    check_answer_any(judge, answer, "AERO_1y_first", ["2025/11/06", "2025-11-06", "November 06, 2025", "November 6, 2025"])
    check_answer_price(judge, answer, "AERO_exp2_lowest", 5.00)
    check_answer_number(judge, answer, "carol_total", 2)
    check_answer_phrase(judge, answer, "AERO_alert_status", "Pending")
    check_answer_number(judge, answer, "carol_alert_total", 1)
    check_only_tables_changed(judge, initial, after, {"watch_items", "price_alerts"})
    check_rows_added(judge, initial, after, "watch_items", [
        [None, 3, "AERO", "2026-09-29"],
    ], "watch_row_added")
    check_rows_added(judge, initial, after, "price_alerts", [
        [None, 3, "AERO", "above", 16.0, None, "2026-09-29"],
    ], "alert_row_added")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
