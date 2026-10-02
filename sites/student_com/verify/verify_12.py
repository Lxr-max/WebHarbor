#!/usr/bin/env python3
"""Verify Student.com--12 against the reviewed task and saved browser state."""
from verify_lib import (check_answer_absent, check_answer_any,
                        check_answer_count_at_least, check_answer_number,
                        check_answer_phrase, check_bookmark_delta, check_enquiry_created,
                        check_only_tables_changed, check_read_only,
                        check_trajectory_identity, check_user_created,
                        check_views_added, check_views_only, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Student.com--12"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_seminoles_search", r"/search\?q=Seminoles")
    check_visited_path(judge, traj, "visited_fsu_srp", r"/us/fl/tallahassee/u/florida-state-university")
    check_visited_path(judge, traj, "visited_southgate", r"/us/fl/tallahassee/p/southgate-campus-centre-13694141")
    check_answer_phrase(judge, answer, "answer_university", 'Florida State University')
    check_answer_phrase(judge, answer, "answer_city", 'Tallahassee')
    check_answer_phrase(judge, answer, "answer_name", 'Southgate Campus Centre')
    check_answer_number(judge, answer, "answer_price", 455)
    check_answer_number(judge, answer, "answer_rating", '4.3')
    check_answer_any(judge, answer, "answer_distance", ['0.3', '0.32'])
    check_answer_phrase(judge, answer, "answer_address", '675 W Jefferson St')
    check_answer_count_at_least(judge, answer, "answer_amenity", ['Pet Friendly', 'Entertainment Area / Lounge', 'Furnishing Option', 'Elevators', 'Gym', 'Swimming Pool', 'Air Conditioning'], 2)

    check_views_only(judge, initial_db, after_db, ["southgate-campus-centre-13694141"])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
