#!/usr/bin/env python3
"""Verify Student.com--5 against the reviewed task and saved browser state."""
from verify_lib import (check_answer_absent, check_answer_any,
                        check_answer_count_at_least, check_answer_number,
                        check_answer_phrase, check_bookmark_delta, check_enquiry_created,
                        check_only_tables_changed, check_read_only,
                        check_trajectory_identity, check_user_created,
                        check_views_added, check_views_only, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Student.com--5"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    for city, region in [('gainesville','fl'),('austin','tx')]:
        check_visited_path(judge, traj, city+'_jobs', rf'/us/{region}/{city}/internships\?type=part-time')
    for label, value in [('gainesville_count',1),('austin_count',15)]:
        check_answer_number(judge, answer, label, value)
    for value in ['Part-Time Assistant Manager - Level 2','Boxlunch','Gainesville','Operations Associate (Part-Time) - Domain Austin','Sales Associate (Part-Time) - Domain Austin','Aloyoga','The Domain']:
        check_answer_phrase(judge, answer, value, value)
    check_answer_any(judge, answer, "gainesville_date", ['2018-01-03','January 3, 2018','3 January 2018'])
    check_answer_any(judge, answer, "austin_date", ['2026-08-18','August 18, 2026','18 August 2026'])

    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
