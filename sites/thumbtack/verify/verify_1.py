#!/usr/bin/env python3
"""Verify Thumbtack--1.

Log in with the demo account (email: bob.c@test.com, password: TestPass123!). My 2-bedroom apartment in zip 98101 needs a deep cleaning before I move out next month. Request house cleaning quotes for a one-time deep clean of 2 bedrooms and 2 bathrooms, hire the cheapest pro who responded, and leave them a 5-star review that mentions "move-out".
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

TASK_ID = "Thumbtack--1"

# frozen ground truth (reviewer honest walk 2026-09-27, seed md5 0c1320fd…)
HIRED_PRO = "Ipanema Cleaning Service"
HIRED_PRO_ID = 66
LOWEST_QUOTE = 184
EXPECTED_QUOTES = (191, 184, 244, 245, 227)


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "login page", r"/login")
    check_visited_path(judge, traj, "house cleaning category", r"/k/house-cleaning/near-me")
    check_visited_path(judge, traj, "quote wizard", r"/projects/new\?category=house-cleaning")
    check_visited_path(judge, traj, "project page", r"/projects/6")
    check_visited_path(judge, traj, "review form", r"/projects/6/review")
    check_answer_phrase(judge, answer, "hired pro name", "Ipanema")
    check_answer_number(judge, answer, "cheapest quote", LOWEST_QUOTE,
                        ["quote", "cheapest", "lowest", "responder", "ipanema"])
    check_answer_any(judge, answer, "5-star review", ["5-star", "five-star", "5 star"])
    check_answer_any(judge, answer, "move-out mention", ["move-out", "move out", "moveout"])
    check_only_tables_changed(judge, initial_db, after_db,
                              {"projects", "project_matches", "reviews"})
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 2, 1, "98101", None, None, None, "completed", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 73, 1, 191, None, None, 0),
                       (27, 6, HIRED_PRO_ID, 1, 184, None, None, 1),
                       (28, 6, 76, 1, 244, None, None, 0),
                       (29, 6, 67, 1, 245, None, None, 0),
                       (30, 6, 65, 1, 227, None, None, 0)])
    check_table_added(judge, initial_db, after_db, "reviews",
                      [(857, HIRED_PRO_ID, "Bob Chen", "Sep 26, 2026", 5,
                        None, "project:6", 1, "user")])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
