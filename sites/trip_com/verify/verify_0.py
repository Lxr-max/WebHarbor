#!/usr/bin/env python3
"""Verify Trip.com--0.

I'm taking my partner to Las Vegas for our anniversary, checking in Sunday 4 October and out Monday 5 October. Find a 5-star hotel on the Strip under $250 a night with an outdoor pool, and book its cheapest king-bed room. First check the deals page for the new-user hotel promo code and use it at checkout. Pay as a guest: Jordan Blake, jordan.blake@example.com, +1 555 017 2222, Visa 4242 4242 4242 4242. Report the booking reference and the total charged.
"""
from verify_lib import (check_answer_any, check_answer_count_at_least,
                        check_answer_money, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_read_only,
                        check_rows_added, check_rows_changed, check_seed_contract,
                        check_set_delta, check_screenshots, check_trajectory_identity,
                        check_visited_any, check_visited_path, final_answer, run_verifier)

TASK_ID = "Trip.com--0"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_visited_path(judge, traj, "visited_deals", r"/deals/")
    check_visited_path(judge, traj, "visited_hotel_list", r"/hotels/list\?")
    check_visited_path(judge, traj, "visited_hotel_detail", r"/hotels/detail/737533")
    check_visited_path(judge, traj, "visited_book_form", r"/hotels/book/54")
    check_visited_path(judge, traj, "visited_confirmation", r"/hotels/confirmation/")
    check_answer_phrase(judge, answer, "answer_hotel", 'Trump International Hotel Las Vegas')
    check_answer_phrase(judge, answer, "answer_king_room", 'Superior King Room')
    check_answer_phrase(judge, answer, "answer_promo_code", 'TRIPNEW20')
    check_answer_money(judge, answer, "answer_total", 216.0)
    check_rows_added(judge, initial_db, after_db, 'hotel_bookings',
                      [['rx:^TH', 737533, 54, None, 'Jordan', 'Blake', 'jordan.blake@example.com', 'rx:\\+1 555 017 2222', '2026-10-04', '2026-10-05', 1, 2, 0, 238.0, 32.0, 216.0, 2, 'TRIPNEW20', 'confirmed', None]], 'hotel_booking_created')
    check_only_tables_changed(judge, initial_db, after_db, {'hotel_bookings'})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
