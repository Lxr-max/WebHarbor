#!/usr/bin/env python3
"""Deterministic verifier for NYSE--11 (nyse).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the r2 review container wh-nyse-r2, seed md5
b7c3bbfa3a7a64b8d09b4e7fb3323fd9, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_11.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "NYSE--11"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Stocks TECHNOLOGIES count; Name-desc first listing; first REIT quote
    # (sector, 52w-high date, 1Y last); Realty count + first result volume;
    # Backlog, Pricing Stats, Markets American rows. Read-only.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/listings_directory/stock\?q=TECHNOLOGIES",
        r"/listings_directory/stock\?[^ ]*sort=name[^ ]*order=desc",
        r"/listings_directory/reit",
        r"/quote/XNYS:AAT",
        r"/quote/XNYS:AAT\?zoom=1Y",
        r"/listings_directory/reit\?q=Realty",
        r"/ipo-center/backlog",
        r"/ipo-center/ipo-pricing-stats",
        r"/markets",
    ])
    check_answer_number(judge, answer, "tech_matches", 132)
    check_answer_phrase(judge, answer, "first_name_desc", "Zymeworks")
    check_answer_phrase(judge, answer, "first_reit_sector", "Real Estate & REITs")
    check_answer_phrase(judge, answer, "first_reit_wh52date", "Thursday, July 16, 2026")
    check_answer_any(judge, answer, "first_reit_1y_last", ["2026/09/29", "2026-09-29", "September 29, 2026"])
    check_answer_number(judge, answer, "realty_matches", 24)
    check_answer_number(judge, answer, "first_realty_volume", 843)
    check_answer_phrase(judge, answer, "backlog_top", "Technology")
    check_answer_phrase(judge, answer, "stats_top", "Healthcare")
    check_answer_number(judge, answer, "american_rows", 10)
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
