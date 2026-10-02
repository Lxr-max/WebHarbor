#!/usr/bin/env python3
"""Verify Student.com--13 against the reviewed task and saved browser state."""
from verify_lib import (check_answer_absent, check_answer_any,
                        check_answer_count_at_least, check_answer_number,
                        check_answer_phrase, check_bookmark_delta, check_enquiry_created,
                        check_only_tables_changed, check_read_only,
                        check_trajectory_identity, check_user_created,
                        check_views_added, check_views_only, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Student.com--13"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_scams_guide", r"/guides/avoid-scams-and-fraud")
    check_visited_path(judge, traj, "visited_contact_page", r"/contact")
    check_visited_path(judge, traj, "visited_ut_srp", r"/us/tx/austin/u/the-university-of-texas-at-austin")
    check_answer_phrase(judge, answer, "answer_redflag_wire", 'Off-Platform Payments')
    check_answer_phrase(judge, answer, "answer_redflag_ghost_1", 'Ghost')
    check_answer_phrase(judge, answer, "answer_redflag_ghost_2", 'Landlord')
    check_answer_phrase(judge, answer, "answer_step1", 'Report anything suspicious')
    check_answer_phrase(judge, answer, "answer_step2", 'Trace the Paperwork')
    check_answer_phrase(judge, answer, "answer_step3", 'External Authorities')
    check_answer_phrase(judge, answer, "answer_phone", '+44 800 316 2918')
    check_answer_phrase(judge, answer, "answer_email", 'contact@student.com')
    check_answer_phrase(judge, answer, "answer_cheapest_name", 'College House Nueces')
    check_answer_number(judge, answer, "answer_cheapest_price", 532)

    check_visited_path(judge, traj, "city_guide", r"/us/tx/austin(?:$|[?#])")
    check_answer_number(judge, answer, "range_low", 1000)
    check_answer_number(judge, answer, "range_high", 1600)
    check_answer_any(judge, answer, "safety_conclusion", ['not safe', 'does not make', 'still suspicious', 'still unsafe'])
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
