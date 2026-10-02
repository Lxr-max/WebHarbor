#!/usr/bin/env python3
"""Verify Student.com--14 against the reviewed task and saved browser state."""
from verify_lib import (check_answer_absent, check_answer_any,
                        check_answer_count_at_least, check_answer_number,
                        check_answer_phrase, check_bookmark_delta, check_enquiry_created,
                        check_only_tables_changed, check_read_only,
                        check_trajectory_identity, check_user_created,
                        check_views_added, check_views_only, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Student.com--14"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_uga_srp", r"/us/ga/athens/u/university-of-georgia")
    check_visited_path(judge, traj, "visited_butler", r"/us/ga/athens/p/the-butler-olmq6o")
    check_answer_phrase(judge, answer, "answer_name", 'The Butler')
    check_answer_phrase(judge, answer, "answer_reference", 'INQ-000005')

    check_only_tables_changed(judge, initial_db, after_db,
                               {"users", "bookmarks", "enquiries", "property_views"})
    check_user_created(judge, initial_db, after_db, "mia.torres@test.com", "Mia", "Torres")
    check_bookmark_delta(judge, initial_db, after_db, "mia.torres@test.com", "the-butler-olmq6o", None)
    check_enquiry_created(judge, initial_db, after_db, "mia.torres@test.com", "the-butler-olmq6o", "INQ-000005")
    check_views_added(judge, initial_db, after_db, ["the-butler-olmq6o"])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
