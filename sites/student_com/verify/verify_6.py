#!/usr/bin/env python3
"""Verify Student.com--6 against the reviewed task and saved browser state."""
from verify_lib import (check_answer_absent, check_answer_any,
                        check_answer_count_at_least, check_answer_number,
                        check_answer_phrase, check_bookmark_delta, check_enquiry_created,
                        check_only_tables_changed, check_read_only,
                        check_trajectory_identity, check_user_created,
                        check_views_added, check_views_only, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Student.com--6"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_austin_city", r"/us/tx/austin")
    check_visited_path(judge, traj, "visited_ut_srp", r"/us/tx/austin/u/the-university-of-texas-at-austin")
    check_answer_phrase(judge, answer, "answer_visa", 'F-1 visa')
    check_answer_number(judge, answer, "answer_range_low", 1000)
    check_answer_number(judge, answer, "answer_range_high", 1600)
    check_answer_phrase(judge, answer, "answer_top_rated_name", 'Carothers Residence Hall')
    check_answer_number(judge, answer, "answer_top_rated_price", 1560)
    check_answer_number(judge, answer, "answer_top_rated_rating", '4.7')

    check_answer_number(judge, answer, "budget_low", 1500)
    check_answer_number(judge, answer, "budget_high", 2500)
    check_answer_count_at_least(judge, answer, "amenities", ['Library / Study Area', 'Air Conditioning', 'Rooftop Terrace'], 2)
    check_visited_path(judge, traj, "property_details", r"/p/carothers-residence-hall")
    check_views_only(judge, initial_db, after_db, [r[0] for r in initial_db.execute("SELECT slug FROM properties WHERE name='Carothers Residence Hall'")])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
