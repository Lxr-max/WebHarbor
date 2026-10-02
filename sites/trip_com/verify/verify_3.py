#!/usr/bin/env python3
"""Verify Trip.com--3.

Use the deals page to compare the six cheap flight deals, then book the cheapest route as a round trip departing 20 October and returning 27 October for one adult in economy. Filter the results to nonstop flights only and pick the cheapest combination. Passenger: Alex Moore, alex.moore@example.com, +1 555 016 6677, card 4242 4242 4242 4242. Report the route, the airlines, the total and the booking reference.
"""
from verify_lib import (check_answer_any, check_answer_count_at_least,
                        check_answer_money, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_read_only,
                        check_rows_added, check_rows_changed, check_seed_contract,
                        check_set_delta, check_screenshots, check_trajectory_identity,
                        check_visited_any, check_visited_path, final_answer, run_verifier)

TASK_ID = "Trip.com--3"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_visited_path(judge, traj, "visited_deals", r"/deals/")
    check_visited_path(judge, traj, "visited_flight_list", r"/flights/list\?")
    check_visited_path(judge, traj, "visited_return_select", r"/flights/select/")
    check_visited_path(judge, traj, "visited_book_form", r"/flights/book\?")
    check_visited_path(judge, traj, "visited_confirmation", r"/flights/confirmation/")
    check_answer_any(judge, answer, "answer_route", ['San Francisco', 'SFO'])
    check_answer_phrase(judge, answer, "answer_airlines", 'Frontier')
    check_answer_phrase(judge, answer, "answer_airlines2", 'Southwest')
    check_answer_money(judge, answer, "answer_total", 114.0)
    check_rows_added(judge, initial_db, after_db, 'flight_bookings',
                      [['rx:^TF', 859, 891, None, 'Alex', 'Moore', 'alex.moore@example.com', 'rx:\\+1 555 016 6677', 'Economy', 'rt', 114.0, '', 'confirmed', None, '2026-10-20', '2026-10-27']], 'flight_booking_created')
    check_only_tables_changed(judge, initial_db, after_db, {'flight_bookings'})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
