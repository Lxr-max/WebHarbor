#!/usr/bin/env python3
"""Verify Thumbtack--15.

Log in with the demo account (email: alice.j@test.com, password: TestPass123!). Using the Kirkland city page, find the house cleaner with the most reviews, message them asking whether they bring their own supplies, and then request a quote from them for a standard cleaning of my 3-bedroom home.
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

TASK_ID = "Thumbtack--15"

# frozen ground truth (reviewer honest walk 2026-09-27, seed md5 0c1320fd…)
TARGET_PRO = "Empire Cleaning Services"
TARGET_PRO_ID = 65
SUPPLIES_REPLY = "we bring all of our own supplies and equipment"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "login page", r"/login")
    check_visited_path(judge, traj, "Kirkland city page", r"/wa/kirkland")
    check_visited_path(judge, traj, "target profile",
                       r"/wa/kirkland/house-cleaning/empire-cleaning-services/service/476683242989297681")
    check_visited_path(judge, traj, "message flow",
                       r"/message/476683242989297681|/account/messages/")
    check_visited_path(judge, traj, "quote wizard", r"/projects/new\?category=house-cleaning")
    check_visited_path(judge, traj, "project page", r"/projects/6")
    check_answer_phrase(judge, answer, "target pro name", TARGET_PRO)
    check_answer_any(judge, answer, "message sent",
                     ["messaged", "message", "asked", "sent", "reached out"])
    check_answer_any(judge, answer, "quote requested",
                     ["quote", "estimate", "request"])
    check_only_tables_changed(judge, initial_db, after_db,
                              {"threads", "messages", "projects", "project_matches"})
    check_table_added(judge, initial_db, after_db, "threads",
                      [(2, 1, TARGET_PRO_ID, None, None)])
    check_table_added(judge, initial_db, after_db, "messages",
                      [(3, 2, "user", None, None),
                       (4, 2, "pro", None, None)])
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 1, 1, None, None, None, None, "matched", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 73, 1, 191, None, None, 0),
                       (27, 6, 66, 1, 184, None, None, 0),
                       (28, 6, 76, 1, 244, None, None, 0),
                       (29, 6, 67, 1, 245, None, None, 0),
                       (30, 6, 65, 1, 227, None, None, 0)])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
