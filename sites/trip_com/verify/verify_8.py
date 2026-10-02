#!/usr/bin/env python3
"""Verify Trip.com--8.

I heard Trip.com gives new users a hotel discount. Find the promo code that takes 20 percent off hotels and its minimum spend, then use it to book the cheapest room at Paris Las Vegas for 4-5 October. Guest: Robin Fox, robin.fox@example.com, +1 555 019 9900, card 4242 4242 4242 4242. Report the code's minimum spend, the discount you got and the final total.
"""
from verify_lib import (check_answer_any, check_answer_count_at_least,
                        check_answer_money, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_read_only,
                        check_rows_added, check_rows_changed, check_seed_contract,
                        check_set_delta, check_screenshots, check_trajectory_identity,
                        check_visited_any, check_visited_path, final_answer, run_verifier)

TASK_ID = "Trip.com--8"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_visited_path(judge, traj, "visited_deals", r"/deals/")
    check_visited_path(judge, traj, "visited_hotel_list", r"/hotels/list\?")
    check_visited_path(judge, traj, "visited_hotel_detail", r"/hotels/detail/733090")
    check_visited_path(judge, traj, "visited_book_form", r"/hotels/book/22")
    check_visited_path(judge, traj, "visited_confirmation", r"/hotels/confirmation/")
    check_answer_number(judge, answer, "answer_min_spend", '100')
    check_answer_phrase(judge, answer, "answer_room", 'Room Type Assigned On Arrival')
    check_answer_money(judge, answer, "answer_discount", 37.8)
    check_answer_money(judge, answer, "answer_total", 151.2)
    check_answer_phrase(judge, answer, "answer_promo", 'TRIPNEW20')
    check_rows_added(judge, initial_db, after_db, 'hotel_bookings',
                      [['rx:^TH', 733090, 22, None, 'Robin', 'Fox', 'robin.fox@example.com', 'rx:\\+1 555 019 9900', '2026-10-04', '2026-10-05', 1, 2, 0, 167.0, 22.0, 151.2, 1, 'TRIPNEW20', 'confirmed', None]], 'hotel_booking_created')
    check_only_tables_changed(judge, initial_db, after_db, {'hotel_bookings'})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
