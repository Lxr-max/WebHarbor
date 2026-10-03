#!/usr/bin/env python3
"""Verify Student.com--3 against the reviewed task and saved browser state."""
from verify_lib import (check_answer_absent, check_answer_any,
                        check_answer_count_at_least, check_answer_number,
                        check_answer_phrase, check_bookmark_delta, check_enquiry_created,
                        check_only_tables_changed, check_read_only,
                        check_trajectory_identity, check_user_created,
                        check_views_added, check_views_only, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Student.com--3"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_gt_srp", r"/us/ga/atlanta/u/georgia-institute-of-technology")
    check_visited_path(judge, traj, "visited_gsu_srp", r"/us/ga/atlanta/u/georgia-state-university")
    check_visited_path(judge, traj, "visited_freeman", r"/us/ga/atlanta/p/freeman-ford-lofts-5bc863")
    check_answer_phrase(judge, answer, "answer_gt1_name", 'International House')
    check_answer_number(judge, answer, "answer_gt1_price", 950)
    check_answer_phrase(judge, answer, "answer_gt2_name", 'Eighth Street Apartments')
    check_answer_number(judge, answer, "answer_gt2_price", 1411)
    check_answer_phrase(judge, answer, "answer_gsu1_name", 'Piedmont Pad Apartments')
    check_answer_number(judge, answer, "answer_gsu1_price", 500)
    check_answer_phrase(judge, answer, "answer_gsu2_name", 'Freeman Ford Lofts')
    check_answer_number(judge, answer, "answer_gsu2_price", 1850)
    check_answer_number(judge, answer, "answer_rating", '4.7')
    check_answer_number(judge, answer, "answer_reviews", 36)

    check_views_only(judge, initial_db, after_db, ["freeman-ford-lofts-5bc863"])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
