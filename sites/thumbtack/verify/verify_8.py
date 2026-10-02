#!/usr/bin/env python3
"""Verify Thumbtack--8.

Log in with the demo account (email: alice.j@test.com, password: TestPass123!). I can only be home on Sundays. Find two handymen whose business hours include Sunday, compare their reviews, and message the one with more reviews to confirm they can do a Sunday visit. Follow up in the same thread asking which Sunday time slots they have open, then save that handyman to my saved pros. Report both replies.
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

TASK_ID = "Thumbtack--8"

# frozen ground truth (reviewer honest walk 2026-09-27, seed md5 0c1320fd…)
SUNDAY_ONE = "Evergreen Home Assist"
SUNDAY_ONE_ID = 54
SUNDAY_TWO = "I.d. Handyman"
SUNDAY_TWO_ID = 55
SUNDAY_TWO_REVIEWS = 56
SLOTS_REPLY = "We do have openings"



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "login page", r"/login")
    check_visited_path(judge, traj, "handyman category", r"/k/handyman/near-me")
    check_visited_path(judge, traj, "first Sunday handyman profile", r"/wa/mountlake-terrace/handyman/evergreen-home-assist-llc/service/559530045965762575")
    check_visited_path(judge, traj, "second Sunday handyman profile", r"/wa/lynnwood/handyman/id-handyman/service/557383931483373571")
    check_visited_path(judge, traj, "Sunday message flow", r"/message/557383931483373571|/account/messages/2")
    check_visited_path(judge, traj, "saved list", r"/account/saved")
    check_answer_phrase(judge, answer, "Sunday handyman one", SUNDAY_ONE)
    check_answer_phrase(judge, answer, "Sunday handyman two", SUNDAY_TWO)
    check_answer_number(judge, answer, "more-reviewed handyman reviews",
                        SUNDAY_TWO_REVIEWS, "review")
    check_answer_phrase(judge, answer, "Sunday slots replies", SLOTS_REPLY)
    check_answer_any(judge, answer, "removal from saved",
                     ["removed", "remove"])
    check_only_tables_changed(judge, initial_db, after_db,
                              {"saved_pros", "threads", "messages"})
    check_table_added(judge, initial_db, after_db, "saved_pros",
                      [(15, 1, SUNDAY_TWO_ID, None)])
    check_table_added(judge, initial_db, after_db, "threads",
                      [(2, 1, SUNDAY_TWO_ID, None, None)])
    check_table_added(judge, initial_db, after_db, "messages",
                      [(3, 2, "user", None, None),
                       (4, 2, "pro", None, None),
                       (5, 2, "user", None, None),
                       (6, 2, "pro", None, None)])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
