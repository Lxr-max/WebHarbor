#!/usr/bin/env python3
"""Deterministic verifier for NYSE--12 (nyse).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the r2 review container wh-nyse-r2, seed md5
b7c3bbfa3a7a64b8d09b4e7fb3323fd9, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_12.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "NYSE--12"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # bob login; watchlist 2nd symbol (TSLA) beta/RSI; 1st (AAPL) 52w high;
    # TSLA alert below 150; relogin; delete AAPL alert; report remainder.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/login",
        r"/watchlist",
        r"/quote/XNGS:TSLA",
        r"/quote/XNGS:AAPL",
        r"/alerts",
        r"/login",
        r"/alerts",
    ])
    check_answer_count_at_least(judge, answer, "bob_symbols", ["AAPL", "TSLA"], 2)
    check_answer_price(judge, answer, "TSLA_beta", 1.84)
    check_answer_price(judge, answer, "TSLA_rsi", 44.80)
    check_answer_price(judge, answer, "AAPL_wh52", 345.34)
    check_answer_number(judge, answer, "alerts_before", 3)
    check_answer_number(judge, answer, "alerts_after", 2)
    check_answer_phrase(judge, answer, "new_alert_status", "Pending")
    check_only_tables_changed(judge, initial, after, {"price_alerts"})
    check_rows_added(judge, initial, after, "price_alerts", [
        [None, 2, "TSLA", "below", 150.0, None, "2026-09-29"],
    ], "alert_row_added")
    check_rows_removed(judge, initial, after, "price_alerts", [
        [None, 2, "AAPL", "below", 300.0, None, "2026-09-29"],
    ], "alert_row_removed")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
