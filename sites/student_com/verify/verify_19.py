#!/usr/bin/env python3
"""Verify Student.com--19 against the reviewed task and saved browser state."""
from verify_lib import (check_answer_absent, check_answer_any,
                        check_answer_count_at_least, check_answer_number,
                        check_answer_phrase, check_bookmark_delta, check_enquiry_created,
                        check_only_tables_changed, check_read_only,
                        check_trajectory_identity, check_user_created,
                        check_views_added, check_views_only, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Student.com--19"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_inquiries", r"/profile/inquiries")
    check_answer_phrase(judge, answer, "answer_reference", 'INQ-000001')
    check_answer_phrase(judge, answer, "answer_property", 'Moontower')
    check_answer_any(judge, answer, "answer_date", ['September 20, 2026', 'September 20', '2026-09-20'])
    check_answer_phrase(judge, answer, "answer_message", 'studio with a private bathroom')

    check_answer_phrase(judge, answer, "new_reference", 'INQ-000005')
    check_only_tables_changed(judge, initial_db, after_db, {"enquiries", "property_views"})
    check_enquiry_created(judge, initial_db, after_db, "alice.j@test.com", "moontower-69d81c", "INQ-000005")
    check_views_added(judge, initial_db, after_db, ["moontower-69d81c"])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
