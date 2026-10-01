#!/usr/bin/env python3
"""Deterministic verifier for NYSE--5 (nyse).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the r2 review container wh-nyse-r2, seed md5
b7c3bbfa3a7a64b8d09b4e7fb3323fd9, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_5.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "NYSE--5"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # REITs tab total, second REIT (ABR) quote, carol watchlist swap
    # AAT -> ABR, relogin, final report.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/listings_directory/reit",
        r"/quote/XNYS:ABR",
        r"/login",
        r"/watchlist",
        r"/quote/XNYS:ABR",
    ])
    check_answer_number(judge, answer, "reit_total", 144)
    check_answer_phrase(judge, answer, "ABR_symbol", "ABR")
    check_answer_phrase(judge, answer, "ABR_sector", "Financials")
    check_answer_price(judge, answer, "ABR_last", 3.97)
    check_answer_phrase(judge, answer, "ABR_board_first", "Caryn Effron")
    check_answer_any(judge, answer, "ABR_board_term", ["term 5", "5-year", "5 year", "(5)"])
    check_answer_number(judge, answer, "carol_final_count", 1)
    check_answer_phrase(judge, answer, "carol_final_symbols", "ABR")
    check_answer_absent(judge, answer, "carol_no_AAT_left", "watchlist: AAT")
    check_only_tables_changed(judge, initial, after, {"watch_items"})
    check_rows_added(judge, initial, after, "watch_items", [
        [None, 3, "ABR", "2026-09-29"],
    ], "watch_row_added")
    check_rows_removed(judge, initial, after, "watch_items", [
        [None, 3, "AAT", "2026-09-29"],
    ], "watch_row_removed")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
