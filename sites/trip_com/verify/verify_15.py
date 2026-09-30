#!/usr/bin/env python3
"""Verify Trip.com--15.

Sign in as David Kim (david.k@test.com, password TestPass123!). I may repeat my Las Vegas hotel stay on 18–20 November 2026. Find my existing hotel reservation and report its hotel, dates and total. Check that hotel's guest score, location and check-in time, then compare its two cheapest rooms for the new dates, including their names, bed types and totals including taxes. Tell me how much either option would save compared with my existing booking. Don't make or cancel any bookings.
"""
from verify_lib import (check_answer_any, check_answer_count_at_least,
                        check_answer_money, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_read_only,
                        check_rows_added, check_rows_changed, check_seed_contract,
                        check_set_delta, check_screenshots, check_trajectory_identity,
                        check_visited_any, check_visited_path, final_answer, run_verifier)

TASK_ID = "Trip.com--15"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_visited_path(judge, traj, "visited_sign_in", r"/sign-in/")
    check_visited_path(judge, traj, "visited_account", r"/account/")
    check_visited_path(judge, traj, "visited_bookings", r"/account/bookings")
    check_visited_path(judge, traj, "visited_hotel_page", r"/hotels/detail/718690")
    check_visited_path(judge, traj, "visited_repeat_form", r"/hotels/book/1")
    check_answer_phrase(judge, answer, "answer_hotel_booking", 'Harrah')
    check_answer_phrase(judge, answer, "answer_hotel_dates", 'Nov 1')
    check_answer_money(judge, answer, "answer_hotel_total", 136.0)
    check_answer_phrase(judge, answer, "answer_area", 'Las Vegas Strip')
    check_answer_phrase(judge, answer, "answer_cheapest_room", 'Room Type Assigned On Arrival')
    check_answer_number(judge, answer, "answer_room_price", '56')
    check_answer_phrase(judge, answer, "answer_checkin_time", '16:00')
    check_answer_money(judge, answer, "answer_repeat_total", 128.0)
    check_visited_path(judge, traj, "second_room", r"/hotels/book/2")
    check_answer_phrase(judge, answer, "second_room_name", "Mountain Deluxe Queen")
    check_answer_money(judge, answer, "second_total", 132)
    check_answer_money(judge, answer, "first_saving", 8)
    check_answer_money(judge, answer, "second_saving", 4)
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
