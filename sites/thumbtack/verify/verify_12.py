#!/usr/bin/env python3
"""Verify Thumbtack--12.

Log in with the demo account (email: alice.j@test.com, password: TestPass123!). My house cleaning project is finished but I never left a review. Open the project, note the hired pro's price and their response note, and check their profile's current reviews. Then leave them a 5-star review saying they were thorough, including the word "spotless". Reopen their profile to confirm your review is the most recent one, and message them asking whether they could return for a move-out clean next month — follow up asking whether they'd bring their own supplies. Report both replies.
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

TASK_ID = "Thumbtack--12"

# frozen ground truth (reviewer honest walk 2026-09-27, seed md5 0c1320fd…)
HIRED_PRO = "Empire Cleaning Services"
HIRED_PRO_ID = 65
HIRED_PRICE = 244
RESPONSE_NOTE = "adjust after an on-site visit"
MOVEOUT_REPLY = "3-4 hours"
SUPPLIES_REPLY = "we bring all of our own supplies"



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "login page", r"/login")
    check_visited_path(judge, traj, "finished project", r"/projects/1")
    check_visited_path(judge, traj, "hired pro profile", r"/wa/kirkland/house-cleaning/empire-cleaning-services/service/476683242989297681")
    check_visited_path(judge, traj, "review form", r"/projects/1/review")
    check_visited_path(judge, traj, "move-out message flow", r"/message/476683242989297681|/account/messages/2")
    check_answer_phrase(judge, answer, "hired pro name", HIRED_PRO)
    check_answer_number(judge, answer, "hired price", HIRED_PRICE,
                        ["price", "hired", "quoted"])
    check_answer_phrase(judge, answer, "response note", RESPONSE_NOTE)
    check_answer_any(judge, answer, "spotless review", ["spotless"])
    check_answer_phrase(judge, answer, "move-out reply", MOVEOUT_REPLY)
    check_answer_phrase(judge, answer, "supplies reply", SUPPLIES_REPLY)
    check_only_tables_changed(judge, initial_db, after_db,
                              {"reviews", "threads", "messages"})
    check_table_added(judge, initial_db, after_db, "reviews",
                      [(857, HIRED_PRO_ID, "Alice Johnson", "Sep 26, 2026", 5,
                        None, "project:1", 1, "user")])
    check_table_added(judge, initial_db, after_db, "threads",
                      [(2, 1, HIRED_PRO_ID, None, None)])
    check_table_added(judge, initial_db, after_db, "messages",
                      [(3, 2, "user", None, None),
                       (4, 2, "pro", None, None),
                       (5, 2, "user", None, None),
                       (6, 2, "pro", None, None)])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
