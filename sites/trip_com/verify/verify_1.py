#!/usr/bin/env python3
"""Verify Trip.com--1.

Two friends each recommend a Las Vegas hotel under $150 a night with free cancellation. Compare the two best-rated of those by guest score, then book the cheaper one's lowest-priced room for 11-12 October. Guest details: Dana Reyes, dana.reyes@example.com, +1 555 013 3444, card 4242 4242 4242 4242. Tell me which hotel you picked, its guest score, and the total you paid.
"""
from verify_lib import (check_answer_any, check_answer_count_at_least,
                        check_answer_money, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_read_only,
                        check_rows_added, check_rows_changed, check_seed_contract,
                        check_set_delta, check_screenshots, check_trajectory_identity,
                        check_visited_any, check_visited_path, final_answer, run_verifier)

TASK_ID = "Trip.com--1"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_visited_path(judge, traj, "visited_hotel_list", r"/hotels/list\?")
    check_visited_path(judge, traj, "visited_hotel_detail", r"/hotels/detail/733224")
    check_visited_path(judge, traj, "visited_book_form", r"/hotels/book/38")
    check_visited_path(judge, traj, "visited_confirmation", r"/hotels/confirmation/")
    check_answer_phrase(judge, answer, "answer_picked_hotel", 'Planet Hollywood Resort & Casino')
    check_answer_number(judge, answer, "answer_guest_score", '8.5')
    check_answer_money(judge, answer, "answer_total", 82.0)
    check_rows_added(judge, initial_db, after_db, 'hotel_bookings',
                      [['rx:^TH', 733224, 38, None, 'Dana', 'Reyes', 'dana.reyes@example.com', 'rx:\\+1 555 013 3444', '2026-10-11', '2026-10-12', 1, 2, 0, 72.0, 10.0, 82.0, 0, '', 'confirmed', None]], 'hotel_booking_created')
    check_only_tables_changed(judge, initial_db, after_db, {'hotel_bookings'})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
