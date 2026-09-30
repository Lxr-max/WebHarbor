#!/usr/bin/env python3
"""Verify Trip.com--4.

I need a one-way economy flight from Chicago to Miami on Thursday 22 October, one adult. Show only nonstop flights and book the cheapest one that departs before noon. Pay as a guest: Sam Patel, sam.patel@example.com, +1 555 018 8888, card 4242 4242 4242 4242. Report the airline, the departure time, the price and the booking reference.
"""
from verify_lib import (check_answer_any, check_answer_count_at_least,
                        check_answer_money, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_read_only,
                        check_rows_added, check_rows_changed, check_seed_contract,
                        check_set_delta, check_screenshots, check_trajectory_identity,
                        check_visited_any, check_visited_path, final_answer, run_verifier)

TASK_ID = "Trip.com--4"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_visited_path(judge, traj, "visited_flight_list", r"/flights/list\?")
    check_visited_path(judge, traj, "visited_book_form", r"/flights/book\?")
    check_visited_path(judge, traj, "visited_confirmation", r"/flights/confirmation/")
    check_answer_phrase(judge, answer, "answer_airline", 'American')
    check_answer_phrase(judge, answer, "answer_departure", '08:43')
    check_answer_money(judge, answer, "answer_price", 169.0)
    check_rows_added(judge, initial_db, after_db, 'flight_bookings',
                      [['rx:^TF', 624, None, None, 'Sam', 'Patel', 'sam.patel@example.com', 'rx:\\+1 555 018 8888', 'Economy', 'ow', 169.0, '', 'confirmed', None, '2026-10-22', None]], 'flight_booking_created')
    check_only_tables_changed(judge, initial_db, after_db, {'flight_bookings'})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
