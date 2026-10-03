#!/usr/bin/env python3
"""Verify Student.com--7 against the reviewed task and saved browser state."""
from verify_lib import (check_answer_absent, check_answer_any,
                        check_answer_count_at_least, check_answer_number,
                        check_answer_phrase, check_bookmark_delta, check_enquiry_created,
                        check_only_tables_changed, check_read_only,
                        check_trajectory_identity, check_user_created,
                        check_views_added, check_views_only, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Student.com--7"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_bookmarks", r"/profile/bookmarks")
    check_visited_path(judge, traj, "visited_osu_srp", r"/us/oh/columbus/u/the-ohio-state-university")
    check_visited_path(judge, traj, "visited_kenny", r"/us/oh/columbus/p/kenny-road-apartments-d68a14")
    check_answer_number(judge, answer, "answer_saved_count", 3)
    check_answer_phrase(judge, answer, "answer_added_name", 'Kenny Road Apartments')

    check_only_tables_changed(judge, initial_db, after_db,
                               {"bookmarks", "property_views"})
    check_bookmark_delta(judge, initial_db, after_db, "david.k@test.com", "kenny-road-apartments-d68a14", "the-standard-at-atlanta-vesb8v")
    check_views_added(judge, initial_db, after_db, ["kenny-road-apartments-d68a14"])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
