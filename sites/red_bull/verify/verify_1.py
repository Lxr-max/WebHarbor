#!/usr/bin/env python3
"""Deterministic verifier for Red Bull--1 (red_bull).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-red-bull-review, seed md5
2e3f7d1ce9c852f434d394942fe9fa57, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_1.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_money, check_answer_number, check_answer_number_absent,
    check_answer_ordered, check_answer_phrase, check_answer_regex,
    check_read_only, check_rows_added, check_rows_changed, check_rows_removed,
    check_only_tables_changed, check_screenshots, check_seed_contract,
    check_trajectory_identity, check_visited_all, check_visited_any,
    check_visited_path, final_answer, run_verifier,
)

TASK_ID = "Red Bull--1"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_all(judge, traj, "nav_surfaces", [
        r"/events\?[^ ]*country=US[^ ]*status=upcoming",
        r"/events/red-bull-foam-wreckers-virginia-beach$",
        r"/events/red-bull-rapid-release$",
        r"/events/foam-wreckers-carolina-beach$",
        r"/events/foam-wreckers-carolina-beach/register$",
        r"/events/foam-wreckers-carolina-beach/register/confirmation/RB[A-Z0-9]+",
    ])
    check_answer_money(judge, answer, "vb_fee", 20)
    check_answer_any(judge, answer, "rr_fee", ["free"])
    check_answer_money(judge, answer, "cb_fee", 10)
    check_answer_phrase(judge, answer, "cb_venue", "Carolina Beach Boardwalk")
    check_answer_phrase(judge, answer, "cb_date", "October 24, 2026")
    check_answer_regex(judge, answer, "reg_code", r"RB[A-Z0-9]{8}")
    check_answer_number_absent(judge, answer, "not_sypher", 15)
    check_only_tables_changed(judge, initial, after, {"event_registrations"})
    check_rows_added(judge, initial, after, "event_registrations", [
        [None, "rx:^RB[A-Z0-9]{8}$", None, 39, "Red Bull Foam Wreckers - Carolina Beach",
         "Sam", "Porter", "sam.porter@example.com", 10.0, "USD", "confirmed", None],
    ], "registration_row")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
