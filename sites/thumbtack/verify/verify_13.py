#!/usr/bin/env python3
"""Verify Thumbtack--13.

Log in with the demo account (email: alice.j@test.com, password: TestPass123!). Read my existing message thread about cleaning supplies and tell me exactly what the pro said they bring. Then ask a different house cleaner the same question, follow up with them about Sunday availability, and ask the first cleaner the Sunday question too. Tell me how the two cleaners' answers compare.
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

TASK_ID = "Thumbtack--13"

# frozen ground truth (reviewer honest walk 2026-09-27, seed md5 0c1320fd…)
FIRST_CLEANER = "Ipanema Cleaning Service"
SECOND_CLEANER = "Empire Cleaning Services"
SECOND_PRO_ID = 65
SUPPLIES_REPLY = "we bring all of our own supplies and equipment"
SUNDAY_REPLY = "happy to work around your schedule"



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "login page", r"/login")
    check_visited_path(judge, traj, "existing supplies thread", r"/account/messages/1")
    check_visited_path(judge, traj, "house cleaning category sorted", r"/k/house-cleaning/near-me\?sort=highest_rated")
    check_visited_path(judge, traj, "second cleaner profile", r"/wa/kirkland/house-cleaning/empire-cleaning-services/service/476683242989297681")
    check_visited_path(judge, traj, "second cleaner thread", r"/account/messages/2")
    check_visited_path(judge, traj, "first cleaner Sunday question", r"/account/messages/1")
    check_answer_phrase(judge, answer, "first cleaner", FIRST_CLEANER)
    check_answer_phrase(judge, answer, "second cleaner", SECOND_CLEANER)
    check_answer_phrase(judge, answer, "supplies replies", SUPPLIES_REPLY)
    check_answer_phrase(judge, answer, "Sunday replies", SUNDAY_REPLY)
    check_only_tables_changed(judge, initial_db, after_db, {"threads", "messages"})
    check_row_updated(judge, initial_db, after_db, "threads", "id = 1",
                      "updated_at", "2026-09-26 12:32:00.000000")
    check_table_added(judge, initial_db, after_db, "threads",
                      [(2, 1, SECOND_PRO_ID, None, None)])
    check_table_added(judge, initial_db, after_db, "messages",
                      [(3, 2, "user", None, None),
                       (4, 2, "pro", None, None),
                       (5, 2, "user", None, None),
                       (6, 2, "pro", None, None),
                       (7, 1, "user", None, None),
                       (8, 1, "pro", None, None)])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
