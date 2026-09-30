#!/usr/bin/env python3
"""Verify Student.com--4 against the reviewed task and saved browser state."""
from verify_lib import (check_answer_absent, check_answer_any,
                        check_answer_count_at_least, check_answer_number,
                        check_answer_phrase, check_bookmark_delta, check_enquiry_created,
                        check_only_tables_changed, check_read_only,
                        check_trajectory_identity, check_user_created,
                        check_views_added, check_views_only, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Student.com--4"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_history", r"/profile/history")
    check_visited_path(judge, traj, "visited_eighth", r"/us/ga/atlanta/p/eighth-street-apartments-z0rz15")
    check_answer_phrase(judge, answer, "answer_name", 'Eighth Street Apartments')
    check_answer_number(judge, answer, "answer_price", 1411)
    check_answer_number(judge, answer, "answer_reviews", 36)
    check_answer_phrase(judge, answer, "answer_street_address", '555 8th St NW')
    check_answer_number(judge, answer, "answer_rating", '4.2')

    check_views_only(judge, initial_db, after_db, ["eighth-street-apartments-z0rz15"])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
