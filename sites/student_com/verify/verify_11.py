#!/usr/bin/env python3
"""Verify Student.com--11 against the reviewed task and saved browser state."""
from verify_lib import (check_answer_absent, check_answer_any,
                        check_answer_count_at_least, check_answer_number,
                        check_answer_phrase, check_bookmark_delta, check_enquiry_created,
                        check_only_tables_changed, check_read_only,
                        check_trajectory_identity, check_user_created,
                        check_views_added, check_views_only, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Student.com--11"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_villas", r"/us/tx/austin/p/villas-on-rio-8639e0")
    check_answer_phrase(judge, answer, "answer_reference", 'INQ-000005')

    check_only_tables_changed(judge, initial_db, after_db,
                               {"enquiries", "property_views"})
    check_enquiry_created(judge, initial_db, after_db, "alice.j@test.com", "villas-on-rio-8639e0", "INQ-000005")
    check_views_added(judge, initial_db, after_db, ["villas-on-rio-8639e0"])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
