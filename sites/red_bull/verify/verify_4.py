#!/usr/bin/env python3
"""Deterministic verifier for Red Bull--4 (red_bull).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-red-bull-review, seed md5
2e3f7d1ce9c852f434d394942fe9fa57, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_4.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Red Bull--4"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_all(judge, traj, "nav_surfaces", [
        r"/events\?[^ ]*discipline=Basketball",
        r"/events/red-bull-rapid-release$",
        r"/events/red-bull-rapid-release/faqs",
        r"/events/red-bull-rapid-release/schedule",
        r"/events/red-bull-rapid-release/register$",
        r"/events/red-bull-rapid-release/register/confirmation/RB[A-Z0-9]+",
    ])
    check_answer_number(judge, answer, "teams", 50)
    check_answer_phrase(judge, answer, "checkin", "6:00 - 7:15 PM")
    # r2 re-anchor: the registration form no longer carries HTML5 required/
    # type=email, so the three server-side errors are reachable through an
    # honest browser interaction and must be confirmed in the answer
    check_answer_phrase(judge, answer, "error_names", "first and last name")
    check_answer_phrase(judge, answer, "error_email", "valid email address")
    check_answer_phrase(judge, answer, "error_ticket", "choose a ticket type")
    check_answer_regex(judge, answer, "reg_code", r"RB[A-Z0-9]{8}")
    check_answer_any(judge, answer, "fee", ["free"])
    check_only_tables_changed(judge, initial, after, {"event_registrations"})
    check_rows_added(judge, initial, after, "event_registrations", [
        [None, "rx:^RB[A-Z0-9]{8}$", None, 13, "Red Bull Rapid Release",
         "Dana", "Kim", "dana.k@example.com", None, None, "confirmed", None],
    ], "registration_row")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
