#!/usr/bin/env python3
"""Deterministic verifier for University of Michigan--1 (university_of_michigan).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-umich-review, seed md5
3f5e930aa820d1b62309ec3feeb4536b, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_1.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_number, check_answer_number_absent, check_answer_number_any,
    check_answer_ordered, check_answer_phrase, check_answer_price,
    check_answer_regex, check_answer_zero_or_phrase, check_read_only,
    check_rows_added, check_rows_removed, check_only_tables_changed,
    check_screenshots, check_seed_contract, check_trajectory_identity,
    check_visited_all, check_visited_any, check_visited_path, final_answer,
    run_verifier,
)

TASK_ID = "University of Michigan--1"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Bob login; Great Lakes (32 records, 8 Articles), first Article author
    # Yeo + year 2024-09; climate Article handle 2027.42/163954; Susan Werner
    # saved; My U-M totals.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/login",
        r"/library\?q=Great\+Lakes",
        r"/library\?q=Great\+Lakes&type=Article",
        r"/library/item/ff908be4",
        r"/library\?q=climate&type=Article",
        r"/library/item/d0486a4a",
        r"/events\?q=Susan\+Werner",
        r"/events/146112",
        r"/myumich",
    ])
    check_answer_number(judge, answer, "great_lakes_records", 32)
    check_answer_number(judge, answer, "great_lakes_articles", 8)
    check_answer_phrase(judge, answer, "first_author", "Yeo, A. J.")
    check_answer_number(judge, answer, "issue_year", 2024)
    check_answer_phrase(judge, answer, "climate_handle", "2027.42/163954")
    check_answer_number(judge, answer, "bob_saved_events", 2)
    check_only_tables_changed(judge, initial, after, {"saved_events"})
    check_rows_added(judge, initial, after, "saved_events",
                     [[None, 2, 24, "2026-09-30"]], "saved_event_bob_susan_werner")
    check_rows_removed(judge, initial, after, "saved_events", [],
                     "no_rows_removed_saved_events")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
