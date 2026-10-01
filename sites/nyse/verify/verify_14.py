#!/usr/bin/env python3
"""Deterministic verifier for NYSE--14 (nyse).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the r2 review container wh-nyse-r2, seed md5
b7c3bbfa3a7a64b8d09b4e7fb3323fd9, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.

r2 re-anchor: the fix round gap-fills IBM's company facts + board of directors
(the r1 capture came back null upstream-side), so the task now also reports
IBM's sector, CEO and board member count, and its final leg creates an IBM
price alert below 200 and reports the status plus Alice's alert total. The
r1 first-expiry reads (lowest strike + call OI) are dropped; the second
expiry's highest strike stays.
Usage: python3 verify_14.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "NYSE--14"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # IBM quote (last, avg volume, sector, CEO, board count, 1M/5Y axis,
    # exp2 highest strike); alice watch IBM; watchlist total; r2 leg: create
    # an IBM alert below 200 and report status + Alice's alert total.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/listings_directory/stock\?q=IBM",
        r"/quote/XNYS:IBM(\?zoom=1M)?",
        r"/quote/XNYS:IBM\?zoom=1M",
        r"/quote/XNYS:IBM\?zoom=5Y",
        r"/quote/XNYS:IBM\?exp=2",
        r"/login",
        r"/watchlist",
        r"/alerts",
    ])
    check_answer_price(judge, answer, "IBM_last", 219.99)
    check_answer_regex(judge, answer, "IBM_avevol", r"5[,，]?653[,，]?953")
    check_answer_phrase(judge, answer, "IBM_sector", "Technology")
    check_answer_phrase(judge, answer, "IBM_ceo", "Arvind Krishna")
    check_answer_number(judge, answer, "IBM_board_count", 13)
    check_answer_any(judge, answer, "IBM_1m_last", ["2026/09/29", "2026-09-29", "September 29, 2026"])
    check_answer_any(judge, answer, "IBM_5y_first", ["2021/09/30", "2021-09-30", "September 30, 2021"])
    check_answer_price(judge, answer, "IBM_exp2_highest", 310.00)
    check_answer_number(judge, answer, "alice_total", 4)
    check_answer_phrase(judge, answer, "IBM_alert_status", "Pending")
    check_answer_number(judge, answer, "alice_alert_total", 2)
    check_only_tables_changed(judge, initial, after, {"watch_items", "price_alerts"})
    check_rows_added(judge, initial, after, "watch_items", [
        [None, 1, "IBM", "2026-09-29"],
    ], "watch_row_added")
    check_rows_added(judge, initial, after, "price_alerts", [
        [None, 1, "IBM", "below", 200.0, None, "2026-09-29"],
    ], "alert_row_added")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
