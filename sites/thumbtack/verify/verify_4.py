#!/usr/bin/env python3
"""Verify Thumbtack--4.

Log in with the demo account (email: alice.j@test.com, password: TestPass123!). My TV mounting project is on hold — cancel it, but first tell me which pro had quoted the lowest price and how many quotes the project had received in total. Then start a replacement request in zip 98033 for a handyman to hang a heavy mirror, describe the job in the quote request, and report the cheapest quote the new request received.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (Judge, check_answer_any, check_answer_number,
                        check_answer_phrase, check_input_action,
                        check_new_user, check_only_tables_changed,
                        check_read_only, check_row_updated,
                        check_table_added, check_table_removed,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Thumbtack--4"

# frozen ground truth (reviewer honest walk 2026-09-27, seed md5 0c1320fd…)
LOWEST_PRO = "Wa Pro Builders"
LOWEST_QUOTE = 121
TOTAL_QUOTES = 5
REPLACEMENT_CAT = 4  # handyman


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "login page", r"/login")
    check_visited_path(judge, traj, "TV mounting project page", r"/projects/2")
    check_visited_path(judge, traj, "handyman category", r"/k/handyman/near-me")
    check_visited_path(judge, traj, "replacement wizard", r"/projects/new\?category=handyman")
    check_visited_path(judge, traj, "replacement project page", r"/projects/6")
    check_answer_number(judge, answer, "lowest quote", LOWEST_QUOTE,
                        ["lowest", "quote", "wa pro", "cheapest"])
    check_answer_phrase(judge, answer, "lowest pro name", "Wa Pro Builders")
    check_answer_number(judge, answer, "total quotes", TOTAL_QUOTES, "quote")
    check_answer_any(judge, answer, "cancelled", ["cancel"])
    check_only_tables_changed(judge, initial_db, after_db,
                              {"projects", "project_matches"})
    check_row_updated(judge, initial_db, after_db, "projects", "id = 2",
                      "status", "cancelled")
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 1, REPLACEMENT_CAT, "98033", None, None, None,
                        "matched", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 61, 1, 80, None, None, 0),
                       (27, 6, 55, 1, 68, None, None, 0),
                       (28, 6, 63, 1, 77, None, None, 0),
                       (29, 6, 54, 1, 75, None, None, 0),
                       (30, 6, 59, 1, 62, None, None, 0)])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
