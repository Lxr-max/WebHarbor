#!/usr/bin/env python3
"""Verify Student.com--10 against the reviewed task and saved browser state."""
from verify_lib import (check_answer_absent, check_answer_any,
                        check_answer_count_at_least, check_answer_number,
                        check_answer_phrase, check_bookmark_delta, check_enquiry_created,
                        check_only_tables_changed, check_read_only,
                        check_trajectory_identity, check_user_created,
                        check_views_added, check_views_only, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Student.com--10"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_tx_finder_tamu", r"/us/tx/u\?q=TAMU")
    check_visited_path(judge, traj, "visited_tamu_srp", r"/us/tx/college-station/u/texas-am-university")
    check_visited_path(judge, traj, "visited_100park", r"/us/tx/college-station/p/100-park-554186")
    check_answer_phrase(judge, answer, "answer_university", 'Texas A&M University')
    check_answer_phrase(judge, answer, "answer_name", '100 Park')
    check_answer_number(judge, answer, "answer_price", 1539)
    check_answer_any(judge, answer, "answer_distance", ['0.3', '0.26'])
    check_answer_phrase(judge, answer, "answer_gym", 'Gym')
    check_answer_number(judge, answer, "answer_rating", '4.1')
    check_answer_number(judge, answer, "answer_reviews", 63)

    check_views_only(judge, initial_db, after_db, ["100-park-554186"])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
