#!/usr/bin/env python3
"""Verify Trip.com--10.

Read the Orlando theme-park planning guide to find how many days most travellers need per major park, then browse Orlando activities and book the cheapest city pass for two people for 6 October. Lead traveller: Mel Wu, mel.wu@example.com. Report the guide's advice, the pass you booked and the total paid.
"""
from verify_lib import (check_answer_any, check_answer_count_at_least,
                        check_answer_money, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_read_only,
                        check_rows_added, check_rows_changed, check_seed_contract,
                        check_set_delta, check_screenshots, check_trajectory_identity,
                        check_visited_any, check_visited_path, final_answer, run_verifier)

TASK_ID = "Trip.com--10"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_visited_path(judge, traj, "visited_guide", r"/guide/orlando-theme-park-planning")
    check_visited_path(judge, traj, "visited_orlando_list", r"/things-to-do/experiences/orlando")
    check_visited_path(judge, traj, "visited_pass_detail", r"/things-to-do/detail/110625321")
    check_visited_path(judge, traj, "visited_book_form", r"/things-to-do/book/2")
    check_visited_path(judge, traj, "visited_confirmation", r"/things-to-do/confirmation/")
    check_answer_phrase(judge, answer, "answer_guide_days", '2 days per major park')
    check_answer_phrase(judge, answer, "answer_pass", 'Go City Explorer Pass')
    check_answer_money(judge, answer, "answer_total", 121.68)
    check_rows_added(judge, initial_db, after_db, 'attraction_bookings',
                      [['rx:^TA', 110625321, 2, None, '2026-10-06', 2, 'Mel', 'Wu', 'mel.wu@example.com', 121.68, 'confirmed', None]], 'attraction_booking_created')
    check_only_tables_changed(judge, initial_db, after_db, {'attraction_bookings'})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
