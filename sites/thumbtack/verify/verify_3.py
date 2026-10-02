#!/usr/bin/env python3
"""Verify Thumbtack--3.

Log in with the demo account (email: alice.j@test.com, password: TestPass123!). On Paty House Cleaning's profile, find the word customers mention most often in their reviews and check whether that theme also appears in the newest review. Message Paty asking whether they bring their own cleaning supplies. Then ask a second house cleaner the same question, and follow up with Paty asking whether they could come on a Sunday. Report all three replies.
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

TASK_ID = "Thumbtack--3"

# frozen ground truth (reviewer honest walk 2026-09-27, seed md5 0c1320fd…)
MOST_MENTIONED = "clean"
PATY_PRO_ID = 71
SECOND_CLEANER = "Empire Cleaning Services"
SECOND_PRO_ID = 65
SUPPLIES_REPLY = "we bring all of our own supplies and equipment"
SUNDAY_REPLY = "happy to work around your schedule"



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "login page", r"/login")
    check_visited_path(judge, traj, "Paty profile", r"/wa/lynnwood/house-cleaning/paty-house-cleaning/service/491085485275881476")
    check_visited_path(judge, traj, "Paty message flow", r"/message/491085485275881476|/account/messages/2")
    check_visited_path(judge, traj, "house cleaning category sorted", r"/k/house-cleaning/near-me\?sort=highest_rated")
    check_visited_path(judge, traj, "second cleaner profile", r"/wa/kirkland/house-cleaning/empire-cleaning-services/service/476683242989297681")
    check_visited_path(judge, traj, "second cleaner thread", r"/account/messages/3")
    check_visited_path(judge, traj, "Paty Sunday follow-up", r"/account/messages/2")
    check_answer_phrase(judge, answer, "most-mentioned word", MOST_MENTIONED)
    check_answer_phrase(judge, answer, "second cleaner", SECOND_CLEANER)
    check_answer_phrase(judge, answer, "supplies reply", SUPPLIES_REPLY)
    check_answer_phrase(judge, answer, "Sunday reply", SUNDAY_REPLY)
    check_only_tables_changed(judge, initial_db, after_db, {"threads", "messages"})
    check_table_added(judge, initial_db, after_db, "threads",
                      [(2, 1, PATY_PRO_ID, None, None),
                       (3, 1, SECOND_PRO_ID, None, None)])
    check_table_added(judge, initial_db, after_db, "messages",
                      [(3, 2, "user", None, None),
                       (4, 2, "pro", None, None),
                       (5, 3, "user", None, None),
                       (6, 3, "pro", None, None),
                       (7, 2, "user", None, None),
                       (8, 2, "pro", None, None)])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
