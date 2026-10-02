#!/usr/bin/env python3
"""Verify Trip.com--14.

Book the cheapest round trip from Miami to New York, departing 24 October and returning 31 October, economy, one adult, using the flight promo code from the deals page. Passenger: Jamie Lee, jamie.lee@example.com, +1 555 015 5566, card 4242 4242 4242 4242. Report the promo discount, the total paid and the booking reference.
"""
from verify_lib import (check_answer_any, check_answer_count_at_least,
                        check_answer_money, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_read_only,
                        check_rows_added, check_rows_changed, check_seed_contract,
                        check_set_delta, check_screenshots, check_trajectory_identity,
                        check_visited_any, check_visited_path, final_answer, run_verifier)

TASK_ID = "Trip.com--14"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_visited_path(judge, traj, "visited_deals", r"/deals/")
    check_visited_path(judge, traj, "visited_flight_list", r"/flights/list\?")
    check_visited_path(judge, traj, "visited_return_select", r"/flights/select/")
    check_visited_path(judge, traj, "visited_book_form", r"/flights/book\?")
    check_visited_path(judge, traj, "visited_confirmation", r"/flights/confirmation/")
    check_answer_phrase(judge, answer, "answer_promo", 'FLYTRIP10')
    check_answer_money(judge, answer, "answer_discount", 21.1)
    check_answer_money(judge, answer, "answer_total", 189.9)
    check_rows_added(judge, initial_db, after_db, 'flight_bookings',
                      [['rx:^TF', 783, 852, None, 'Jamie', 'Lee', 'jamie.lee@example.com', 'rx:\\+1 555 015 5566', 'Economy', 'rt', 189.9, 'FLYTRIP10', 'confirmed', None, '2026-10-24', '2026-10-31']], 'flight_booking_created')
    check_only_tables_changed(judge, initial_db, after_db, {'flight_bookings'})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
