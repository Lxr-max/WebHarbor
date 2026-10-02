#!/usr/bin/env python3
"""Verify Student.com--15 against the reviewed task and saved browser state."""
from verify_lib import (check_answer_absent, check_answer_any,
                        check_answer_count_at_least, check_answer_number,
                        check_answer_phrase, check_bookmark_delta, check_enquiry_created,
                        check_only_tables_changed, check_read_only,
                        check_trajectory_identity, check_user_created,
                        check_views_added, check_views_only, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Student.com--15"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_moontower", r"/us/tx/austin/p/moontower-69d81c")
    check_visited_path(judge, traj, "visited_villas", r"/us/tx/austin/p/villas-on-rio-8639e0")
    check_answer_number(judge, answer, "answer_min_price", 700)
    check_answer_number(judge, answer, "answer_max_price", 6475)
    check_answer_number(judge, answer, "answer_photos", 10)
    check_answer_number(judge, answer, "answer_rating", '3.5')
    check_answer_number(judge, answer, "answer_reviews", 178)
    check_answer_number(judge, answer, "answer_villas_min", 989)
    check_answer_number(judge, answer, "answer_villas_rating", '4.3')
    check_answer_phrase(judge, answer, "answer_cheaper", 'Moontower')
    check_answer_phrase(judge, answer, "answer_moontower_address", '2204 San Antonio St')
    check_answer_count_at_least(judge, answer, "answer_moontower_amenity", ['Gym', 'Rooftop Terrace', 'Entertainment Area / Lounge', 'Yoga Studio'], 1)
    check_answer_number(judge, answer, "answer_villas_reviews", 456)
    check_answer_count_at_least(judge, answer, "answer_villas_amenity", ['Washer / Dryer', 'Yoga Studio', 'Gym', 'Library / Study Area', 'Rooftop Terrace'], 1)
    check_answer_number(judge, answer, "answer_villas_distance", '0.1')
    check_answer_number(judge, answer, "answer_moontower_distance", '0.4')

    check_views_only(judge, initial_db, after_db, ["moontower-69d81c", "villas-on-rio-8639e0"])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
