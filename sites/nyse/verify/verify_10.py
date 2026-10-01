#!/usr/bin/env python3
"""Deterministic verifier for NYSE--10 (nyse).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the r2 review container wh-nyse-r2, seed md5
b7c3bbfa3a7a64b8d09b4e7fb3323fd9, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_10.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "NYSE--10"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Priya Nair signup; header search gold; AAAU quote (last, exchange
    # heading); watch AAAU; add NIO; remove the gold stock; report remainder.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/signup",
        r"/search\?q=gold",
        r"/quote/BATS:AAAU",
        r"/listings_directory/stock\?q=NIO",
        r"/quote/XNYS:NIO",
        r"/watchlist",
    ])
    check_answer_number(judge, answer, "gold_matches", 13)
    check_answer_price(judge, answer, "AAAU_last", 41.16)
    check_answer_any(judge, answer, "AAAU_exchange", ["Cboe BZX", "BATS", "Cboe"])
    check_answer_number(judge, answer, "remaining_count", 1)
    check_answer_phrase(judge, answer, "remaining_symbol", "NIO")
    check_only_tables_changed(judge, initial, after, {"users", "watch_items"})
    check_rows_added(judge, initial, after, "users", [
        [None, "priya.nair@test.com", "Priya Nair", "rx:^\$2[aby]\$12\$", "2026-09-29"],
    ], "user_row_added")
    check_rows_added(judge, initial, after, "watch_items", [
        [None, None, "NIO", "2026-09-29"],
    ], "watch_row_added")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
