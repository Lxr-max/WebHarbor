#!/usr/bin/env python3
"""Verify Trip.com--6.

Sign in as Alice Johnson (alice.j@test.com, password TestPass123!). I'm reconsidering the flight for my upcoming New York trip. Find my confirmed round-trip flight booking and report its reference, route, departure times and total. Compare it with the cheapest nonstop round trip on the same route for 20–27 October 2026, including both airlines, departure times and the all-in total. Cancel my existing flight booking, without making a replacement booking or changing my hotel reservation, and confirm the final statuses of both reservations.
"""
from verify_lib import (check_answer_any, check_answer_count_at_least,
                        check_answer_money, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_read_only,
                        check_rows_added, check_rows_changed, check_seed_contract,
                        check_set_delta, check_screenshots, check_trajectory_identity,
                        check_visited_any, check_visited_path, final_answer, run_verifier)

TASK_ID = "Trip.com--6"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_visited_path(judge, traj, "visited_sign_in", r"/sign-in/")
    check_visited_path(judge, traj, "visited_account", r"/account/")
    check_visited_path(judge, traj, "visited_bookings", r"/account/bookings")
    check_visited_any(judge, traj, "visited_cancel", ['/bookings/cancel/flight/TFALICE1', '/account/bookings'])
    check_answer_any(judge, answer, "answer_route", ['SFO', 'San Francisco'])
    check_answer_phrase(judge, answer, "answer_outbound_time", '22:15')
    check_answer_phrase(judge, answer, "answer_cancelled_ref", 'TFALICE1')
    check_answer_phrase(judge, answer, "answer_flight_status", 'cancelled')
    check_answer_phrase(judge, answer, "answer_hotel_status", 'confirmed')
    check_answer_money(judge, answer, "answer_rebook_total", 433.0)
    check_rows_changed(judge, initial_db, after_db, 'flight_bookings',
                       [['TFALICE1', 1, 2, 1, 'Alice', 'Johnson', 'alice.j@test.com', 'rx:\\+1 555 010 0000', 'Economy', 'rt', 422.0, '', 'cancelled', None, None, None]], 'flight_cancelled')
    check_visited_path(judge, traj, "replacement_flights", r"/flights/select/")
    check_answer_phrase(judge, answer, "return_time", "11:35")
    check_answer_money(judge, answer, "existing_total", 422)
    check_answer_phrase(judge, answer, "replacement_airline", "Jetblue")
    check_answer_phrase(judge, answer, "replacement_departure", "06:00")
    check_answer_phrase(judge, answer, "replacement_return_airline", "Delta")
    check_answer_phrase(judge, answer, "replacement_return_departure", "07:00")
    check_answer_money(judge, answer, "replacement_outbound_price", 205)
    check_answer_money(judge, answer, "replacement_return_price", 228)
    check_only_tables_changed(judge, initial_db, after_db, {'flight_bookings'})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
