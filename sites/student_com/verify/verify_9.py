#!/usr/bin/env python3
"""Verify Student.com--9 against the reviewed task and saved browser state."""
from verify_lib import (check_answer_absent, check_answer_any,
                        check_answer_count_at_least, check_answer_number,
                        check_answer_phrase, check_bookmark_delta, check_enquiry_created,
                        check_only_tables_changed, check_read_only,
                        check_trajectory_identity, check_user_created,
                        check_views_added, check_views_only, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Student.com--9"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_cwru_srp", r"/us/oh/cleveland/u/case-western-reserve-university")
    check_visited_path(judge, traj, "visited_parkside", r"/us/oh/cleveland/p/parkside-dwellings-fex58u")
    check_answer_phrase(judge, answer, "answer_name", 'Parkside Dwellings')
    check_answer_number(judge, answer, "answer_price", 1360)
    check_answer_number(judge, answer, "answer_rating", '4.3')
    check_answer_phrase(judge, answer, "answer_address", '2040 Stearns Rd')
    check_answer_number(judge, answer, "answer_srp_total", 20)
    check_answer_number(judge, answer, "answer_reviews", 15)
    check_answer_count_at_least(judge, answer, "answer_amenities", ['Gym', 'Swimming Pool', 'Pet Friendly', 'Furnishing Option', 'Washer / Dryer', 'Air Conditioning', 'Rooftop Terrace', 'Entertainment Area / Lounge', 'Library / Study Area'], 2)
    check_answer_phrase(judge, answer, "answer_second_name", 'Skyline on Stokes')
    check_answer_number(judge, answer, "answer_second_price", 1380)

    check_views_only(judge, initial_db, after_db, ["parkside-dwellings-fex58u"])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
