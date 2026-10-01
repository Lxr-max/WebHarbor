#!/usr/bin/env python3
"""Deterministic verifier for Trader Joe's--2 (trader_joes).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright r2 rounds on the review container tj-review-r2-container
built over the fix commit fb73dbfa, seed md5
34e1af0cc66a317223e889081c2381b4, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_2.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Trader Joe's--2"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Panini recipe facts; bread product; prosciutto bites; bob list ops.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/home/search\?q=panini",
        r"/home/recipes/bacon-apple-brie-panini",
        r"/home/products/pdp/096399",
        r"/home/search\?q=prosciutto\+melon\+bites",
        r"/home/recipes/prosciutto-melon-bites",
        r"/login",
        r"/home/shopping-list",
    ])
    check_answer_phrase(judge, answer, "panini_serves", "1-2")
    check_answer_regex(judge, answer, "panini_time", r"15\s*mins\s*-\s*25\s*mins")
    check_answer_regex(judge, answer, "panini_4th_ingredient", r"8 slices of your favorite TJ.s Apple")
    check_answer_price(judge, answer, "bread_price", 1.49)
    check_answer_phrase(judge, answer, "bread_size", "6.2 Oz")
    check_answer_phrase(judge, answer, "prosciutto_serves", "4-8")
    check_answer_number(judge, answer, "new_total", 7)
    check_answer_number(judge, answer, "moc_qty", 2)
    check_answer_number(judge, answer, "final_total", 6)
    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
