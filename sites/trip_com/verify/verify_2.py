#!/usr/bin/env python3
"""Verify Trip.com--2.

I need round-trip flights from San Francisco to New York, leaving Tuesday 20 October and returning Tuesday 27 October, economy, one adult. We only fly Delta and only nonstop. Book the cheapest qualifying round trip for passenger Maria Santos, maria.santos@example.com, +1 555 014 4555, card 4242 4242 4242 4242. Report both flights' departure times, the total paid and the booking reference.
"""
from verify_lib import (check_answer_any, check_answer_count_at_least,
                        check_answer_money, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_read_only,
                        check_rows_added, check_rows_changed, check_seed_contract,
                        check_set_delta, check_screenshots, check_trajectory_identity,
                        check_visited_any, check_visited_path, final_answer, run_verifier)

TASK_ID = "Trip.com--2"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_visited_path(judge, traj, "visited_flight_list", r"/flights/list\?")
    check_visited_path(judge, traj, "visited_return_select", r"/flights/select/")
    check_visited_path(judge, traj, "visited_book_form", r"/flights/book\?")
    check_visited_path(judge, traj, "visited_confirmation", r"/flights/confirmation/")
    check_answer_phrase(judge, answer, "answer_airline", 'Delta')
    check_answer_any(judge, answer, "answer_out_departure", ['07:00', '16:15', '22:15'])
    check_answer_phrase(judge, answer, "answer_return_departure", '07:00')
    check_answer_money(judge, answer, "answer_total", 441.0)
    check_rows_added(judge, initial_db, after_db, 'flight_bookings',
                      [['rx:^TF', {1, 5, 15}, 149, None, 'Maria', 'Santos', 'maria.santos@example.com', 'rx:\\+1 555 014 4555', 'Economy', 'rt', 441.0, '', 'confirmed', None, '2026-10-20', '2026-10-27']], 'flight_booking_created')
    check_only_tables_changed(judge, initial_db, after_db, {'flight_bookings'})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
