#!/usr/bin/env python3
"""Verify Student.com--17 against the reviewed task and saved browser state."""
from verify_lib import (check_answer_absent, check_answer_any,
                        check_answer_count_at_least, check_answer_number,
                        check_answer_phrase, check_bookmark_delta, check_enquiry_created,
                        check_only_tables_changed, check_read_only,
                        check_trajectory_identity, check_user_created,
                        check_views_added, check_views_only, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Student.com--17"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_ttu_srp", r"/us/tx/lubbock/u/texas-tech-university")
    check_visited_path(judge, traj, "visited_stangel", r"/us/tx/lubbock/p/stangel-hall-3-zooq")
    check_visited_path(judge, traj, "visited_murray", r"/us/tx/lubbock/p/murray-hall-gcf4nm")
    check_visited_path(judge, traj, "visited_murdough", r"/us/tx/lubbock/p/murdough-hall-mvhqyi")
    check_visited_path(judge, traj, "visited_history", r"/profile/history")
    check_answer_phrase(judge, answer, "answer_item1", 'Stangel Hall')
    check_answer_phrase(judge, answer, "answer_item2", 'Murray Hall')
    check_answer_phrase(judge, answer, "answer_item3", 'Murdough Hall')
    check_answer_phrase(judge, answer, "answer_appear", 'appear')
    check_answer_absent(judge, answer, "answer_appear_not_negated", ['not appear', 'do not appear', "don't appear", "didn't appear", 'did not appear', 'no longer appear'])

    check_views_only(judge, initial_db, after_db, ["stangel-hall-3-zooq", "murray-hall-gcf4nm", "murdough-hall-mvhqyi"])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
