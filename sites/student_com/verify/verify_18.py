#!/usr/bin/env python3
"""Verify Student.com--18 against the reviewed task and saved browser state."""
from verify_lib import (check_answer_absent, check_answer_any,
                        check_answer_count_at_least, check_answer_number,
                        check_answer_phrase, check_bookmark_delta, check_enquiry_created,
                        check_only_tables_changed, check_read_only,
                        check_trajectory_identity, check_user_created,
                        check_views_added, check_views_only, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Student.com--18"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_catalyst", r"/us/ga/atlanta/p/catalyst-s7m7fb")
    check_visited_path(judge, traj, "visited_budget_calculator", r"/budget-calculator")
    check_answer_phrase(judge, answer, "answer_contact_email", 'catalystmidtown@crm-living.com')
    check_answer_phrase(judge, answer, "answer_phone", '677-3286')
    check_answer_phrase(judge, answer, "answer_website", 'catalystmidtown.com')
    check_answer_number(judge, answer, "answer_rent_target", 660)
    check_answer_number(judge, answer, "answer_cheapest_room", 1099)
    check_answer_phrase(judge, answer, "answer_conclusion", 'not')

    check_views_only(judge, initial_db, after_db, ["catalyst-s7m7fb"])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
