#!/usr/bin/env python3
"""Verify Student.com--8 against the reviewed task and saved browser state."""
from verify_lib import (check_answer_absent, check_answer_any,
                        check_answer_count_at_least, check_answer_number,
                        check_answer_phrase, check_bookmark_delta, check_enquiry_created,
                        check_only_tables_changed, check_read_only,
                        check_trajectory_identity, check_user_created,
                        check_views_added, check_views_only, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Student.com--8"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_ucf_srp_ai_filtered", r"/us/fl/orlando/u/university-of-central-florida\?.*max_price=800.*type=Apartment")
    check_visited_path(judge, traj, "visited_hub", r"/us/fl/orlando/p/hub-on-campus-orlando-4df3abc0")
    check_answer_number(judge, answer, "answer_result_count", 5)
    check_answer_phrase(judge, answer, "answer_name", 'Hub On Campus Orlando')
    check_answer_number(judge, answer, "answer_rating", '4.0')
    check_answer_phrase(judge, answer, "answer_address", '11012 Hub Plz')
    check_answer_number(judge, answer, "answer_pre_total", 25)
    check_answer_phrase(judge, answer, "answer_ai_filter_type", 'Apartment')
    check_answer_number(judge, answer, "answer_ai_filter_max", 800)
    check_answer_number(judge, answer, "answer_price", 500)
    check_answer_number(judge, answer, "answer_reviews", 1034)
    check_answer_any(judge, answer, "answer_distance", ['2.4', '2.3786'])

    check_views_only(judge, initial_db, after_db, ["hub-on-campus-orlando-4df3abc0"])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
