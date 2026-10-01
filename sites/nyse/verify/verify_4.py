#!/usr/bin/env python3
"""Deterministic verifier for NYSE--4 (nyse).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the r2 review container wh-nyse-r2, seed md5
b7c3bbfa3a7a64b8d09b4e7fb3323fd9, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_4.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "NYSE--4"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # ETFs SPY search/quote/options exp2, Indices Auspice ABCERI,
    # Stocks NIO quote + 1Y. Read-only.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/listings_directory/etf\?q=SPY",
        r"/quote/ARCX:SPY",
        r"/quote/ARCX:SPY\?exp=2",
        r"/listings_directory/index\?q=Auspice",
        r"/quote/index/ABCERI",
        r"/listings_directory/stock\?q=NIO",
        r"/quote/XNYS:NIO(\?zoom=1Y)?",
        r"/quote/XNYS:NIO\?zoom=1Y",
    ])
    check_answer_number(judge, answer, "spy_matches", 21)
    check_answer_price(judge, answer, "SPY_last", 764.20)
    check_answer_price(judge, answer, "SPY_wh52", 779.37)
    check_answer_price(judge, answer, "SPY_exp2_highest", 950.00)
    check_answer_price(judge, answer, "SPY_pc_ratio", 1.97)
    check_answer_phrase(judge, answer, "ABCERI_name", "Auspice Broad Commodity Excess Return Index")
    check_answer_price(judge, answer, "ABCERI_last", "4,955.41")
    check_answer_phrase(judge, answer, "NIO_sector", "Consumer Discretionary")
    check_answer_regex(judge, answer, "NIO_volume", r"706[,，]?930")
    check_answer_any(judge, answer, "NIO_1y_last", ["2026/09/29", "2026-09-29", "September 29, 2026"])
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
