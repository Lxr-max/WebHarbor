#!/usr/bin/env python3
"""Deterministic verifier for Trader Joe's--3 (trader_joes).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright r2 rounds on the review container tj-review-r2-container
built over the fix commit fb73dbfa, seed md5
34e1af0cc66a317223e889081c2381b4, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_3.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_number, check_answer_number_absent, check_answer_number_any,
    check_answer_ordered, check_answer_phrase, check_answer_price,
    check_answer_regex, check_answer_zero_or_phrase, check_read_only,
    check_rows_added, check_rows_removed, check_rows_changed,
    check_only_tables_changed, check_screenshots, check_seed_contract,
    check_trajectory_identity, check_visited_all, check_visited_any,
    check_visited_path, final_answer, run_verifier,
)

TASK_ID = "Trader Joe's--3"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Stores near 98052; closest store facts; My Store; second store; 10mi; Oregon.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/login",
        r"/home/store-search\?q=98052&radius=5",
        r"/home/store-search/store/140",
        r"/home/store-search/store/131",
        r"/home/store-search\?q=98052&radius=10",
        r"/home/store-search\?.*state=OR",
    ])
    check_answer_number(judge, answer, "count_5mi", 3)
    check_answer_phrase(judge, answer, "closest_store", "Redmond (140)")
    check_answer_phrase(judge, answer, "closest_phone", "425-883-1624")
    check_answer_regex(judge, answer, "monday_hours", r"09:00\s*[–-]\s*21:00")
    check_answer_phrase(judge, answer, "header_mystore", "Redmond (140)")
    check_answer_phrase(judge, answer, "second_phone", "425-641-5069")
    check_answer_number(judge, answer, "count_10mi", 10)
    check_answer_number(judge, answer, "oregon_count", 16)

    check_only_tables_changed(judge, initial, after, {"user_stores"})
    check_rows_changed(judge, initial, after, "user_stores",
                       [[2, "140"]], "bob_mystore_redmond")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
