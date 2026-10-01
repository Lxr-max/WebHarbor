#!/usr/bin/env python3
"""Deterministic verifier for NYSE--18 (nyse).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the r2 review container wh-nyse-r2, seed md5
b7c3bbfa3a7a64b8d09b4e7fb3323fd9, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_18.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "NYSE--18"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Stocks page 3 first linked row (ABT) last+volume; UNITED count; dana
    # login; ABT to watchlist (total 4); remove NIO (total 3); Markets first
    # NYSE mover (NU) sector.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/listings_directory/stock\?[^ ]*page=3",
        r"/quote/XNYS:ABT",
        r"/listings_directory/stock\?q=UNITED",
        r"/login",
        r"/quote/XNYS:ABT",
        r"/watchlist",
        r"/markets",
        r"/quote/XNYS:NU",
    ])
    check_answer_price(judge, answer, "ABT_last", 100.95)
    check_answer_regex(judge, answer, "ABT_volume", r"1[,，]?462")
    check_answer_number(judge, answer, "united_matches", 22)
    check_answer_number(judge, answer, "dana_total", 4)
    check_answer_number(judge, answer, "dana_new_total", 3)
    check_answer_phrase(judge, answer, "NU_sector", "Financials")
    check_only_tables_changed(judge, initial, after, {"watch_items"})
    check_rows_added(judge, initial, after, "watch_items", [
        [None, 4, "ABT", "2026-09-29"],
    ], "watch_row_added")
    check_rows_removed(judge, initial, after, "watch_items", [
        [None, 4, "NIO", "2026-09-29"],
    ], "watch_row_removed")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
