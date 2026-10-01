#!/usr/bin/env python3
"""Deterministic verifier for NYSE--1 (nyse).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the r2 review container wh-nyse-r2, seed md5
b7c3bbfa3a7a64b8d09b4e7fb3323fd9, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_1.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "NYSE--1"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Jordan Vale signup; Markets highest-volume NYSE mover (NOK) quote;
    # logout/relogin; watch NOK; IPO recent + 90d + backlog.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/signup",
        r"/markets",
        r"/quote/XNYS:NOK",
        r"/login",
        r"/watchlist",
        r"/ipo-center/recent-ipo(\?window=90)?",
        r"/ipo-center/recent-ipo\?window=90",
        r"/ipo-center/backlog",
    ])
    check_answer_phrase(judge, answer, "top_volume_symbol", "NOK")
    check_answer_phrase(judge, answer, "NOK_sector", "Technology")
    check_answer_phrase(judge, answer, "NOK_ceo", "Justin Hotard")
    check_answer_phrase(judge, answer, "NOK_wh52date", "Wednesday, June 03, 2026")
    check_answer_number(judge, answer, "jordan_watch_count", 1)
    check_answer_phrase(judge, answer, "first_priced_issuer", "Accelevation")
    check_answer_price(judge, answer, "first_priced_price", 18.00)
    check_answer_phrase(judge, answer, "largest90_top", "Csquare")
    check_answer_any(judge, answer, "largest90_proceeds", ["1.21B", "1,207,479,000", "1207479000", "1.21b"])
    check_answer_phrase(judge, answer, "backlog_top", "Technology")
    check_only_tables_changed(judge, initial, after, {"users", "watch_items"})
    check_rows_added(judge, initial, after, "users", [
        [None, "jordan.vale@test.com", "Jordan Vale", "rx:^\$2[aby]\$12\$", "2026-09-29"],
    ], "user_row_added")
    check_rows_added(judge, initial, after, "watch_items", [
        [None, None, "NOK", "2026-09-29"],
    ], "watch_row_added")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
