#!/usr/bin/env python3
"""Deterministic verifier for Trader Joe's--16 (trader_joes).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright r2 rounds on the review container tj-review-r2-container
built over the fix commit fb73dbfa, seed md5
34e1af0cc66a317223e889081c2381b4, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_16.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Trader Joe's--16"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Washington stores; Bellingham James St; My Store; ZIP 98225 search + 10mi widen.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/login",
        r"/home/store-search\?.*state=WA",
        r"/home/store-search/store/151",
        r"/home/store-search\?q=98225&radius=5",
        r"/home/store-search\?q=98225&radius=10",
    ])
    check_answer_number(judge, answer, "wa_count", 33)
    check_answer_phrase(judge, answer, "bellingham_address", "2410 James St")
    check_answer_phrase(judge, answer, "bellingham_phone", "360-734-5166")
    check_answer_regex(judge, answer, "bellingham_saturday", r"08:00\s*\u2013\s*21:00|08:00\s*-\s*21:00")
    check_answer_phrase(judge, answer, "header_mystore", "Bellingham (151)")
    check_answer_number(judge, answer, "zip_count", 2)
    check_answer_phrase(judge, answer, "closest_phone", "360-734-5166")
    check_answer_regex(judge, answer, "closest_sunday", r"08:00\s*\u2013\s*21:00|08:00\s*-\s*21:00")
    check_answer_number(judge, answer, "count_10mi", 2)
    check_only_tables_changed(judge, initial, after, {"user_stores"})
    check_rows_changed(judge, initial, after, "user_stores",
                       [[4, "151"]], "dana_mystore_bellingham")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
