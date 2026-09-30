#!/usr/bin/env python3
"""Verify Student.com--16 against the reviewed task and saved browser state."""
from verify_lib import (check_answer_absent, check_answer_any,
                        check_answer_count_at_least, check_answer_number,
                        check_answer_phrase, check_bookmark_delta, check_enquiry_created,
                        check_only_tables_changed, check_read_only,
                        check_trajectory_identity, check_user_created,
                        check_views_added, check_views_only, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Student.com--16"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_usf_srp_filtered", r"/us/fl/tampa/u/university-of-south-florida\?.*min_price=900.*max_price=1000.*type=Student")
    check_visited_path(judge, traj, "visited_retreat", r"/us/fl/miami/p/the-retreat-at-tampa")
    check_answer_number(judge, answer, "answer_match_count", 1)
    check_answer_phrase(judge, answer, "answer_name", 'The Retreat at Tampa')
    check_answer_number(judge, answer, "answer_price", 940)
    check_answer_phrase(judge, answer, "answer_address", '11326 N 46th St')
    check_answer_count_at_least(judge, answer, "answer_vibes", ['Coffee & food', 'Music & nightlife', 'Artsy & cultural'], 3)

    check_views_only(judge, initial_db, after_db, ["the-retreat-at-tampa"])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
