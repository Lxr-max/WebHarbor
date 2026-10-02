#!/usr/bin/env python3
"""Verify Student.com--2 against the reviewed task and saved browser state."""
from verify_lib import (check_answer_absent, check_answer_any,
                        check_answer_count_at_least, check_answer_number,
                        check_answer_phrase, check_bookmark_delta, check_enquiry_created,
                        check_only_tables_changed, check_read_only,
                        check_trajectory_identity, check_user_created,
                        check_views_added, check_views_only, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Student.com--2"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_ut_srp", r"/us/tx/austin/u/the-university-of-texas-at-austin")
    check_visited_path(judge, traj, "visited_littlefield", r"/us/tx/austin/p/littlefield-hall-kutkl0")
    check_visited_path(judge, traj, "visited_ut_srp_dorm_filtered", r"/us/tx/austin/u/the-university-of-texas-at-austin\?.*type=Dorm")
    check_visited_path(judge, traj, "visited_my_inquiries", r"/profile/inquiries")
    check_answer_phrase(judge, answer, "answer_name", 'Littlefield Hall')
    check_answer_phrase(judge, answer, "answer_address", '2503 Whitis Ave')
    check_answer_phrase(judge, answer, "answer_reference", 'INQ-000005')
    check_answer_number(judge, answer, "answer_dorm_count", 8)
    check_answer_number(judge, answer, "answer_price", 935)
    check_answer_count_at_least(judge, answer, "answer_amenity", ['Air Conditioning', 'Entertainment Area / Lounge'], 1)
    check_answer_phrase(judge, answer, "answer_inquiry_date", 'September 26, 2026')
    check_answer_number(judge, answer, "answer_total_inquiries", 2)

    check_only_tables_changed(judge, initial_db, after_db,
                               {"enquiries", "property_views"})
    check_enquiry_created(judge, initial_db, after_db, "bob.c@test.com", "littlefield-hall-kutkl0", "INQ-000005")
    check_views_added(judge, initial_db, after_db, ["littlefield-hall-kutkl0"])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
