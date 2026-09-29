#!/usr/bin/env python3
"""Verify Trip.com--13.

I want to stay in Las Vegas but away from the Strip crowds. Using the area filter, find the best-rated bookable hotel under $120 a night that is not on the Las Vegas Strip for 13-14 October, and report its name, area, guest score, star rating and nightly price, plus the cancellation deadline shown on its cheapest room. Open that room's booking form for those nights and report the grand total. Then find the best-rated bookable Strip hotel under $120 and report its name, guest score, nightly price and cheapest room's name. Don't book anything.
"""
from verify_lib import (check_answer_any, check_answer_count_at_least,
                        check_answer_money, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_read_only,
                        check_rows_added, check_rows_changed, check_seed_contract,
                        check_set_delta, check_screenshots, check_trajectory_identity,
                        check_visited_any, check_visited_path, final_answer, run_verifier)

TASK_ID = "Trip.com--13"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_visited_path(judge, traj, "visited_hotel_list", r"/hotels/list\?")
    check_visited_path(judge, traj, "visited_hotel_detail", r"/hotels/detail/718623")
    check_visited_path(judge, traj, "visited_book_form", r"/hotels/book/30")
    check_visited_path(judge, traj, "visited_strip_detail", r"/hotels/detail/733224")
    check_answer_phrase(judge, answer, "answer_hotel", 'Four Queens Hotel and Casino')
    check_answer_phrase(judge, answer, "answer_area", 'Downtown - Fremont Street')
    check_answer_number(judge, answer, "answer_score", '8.7')
    check_answer_number(judge, answer, "answer_price", '104')
    check_answer_number(judge, answer, "answer_stars", '3')
    check_answer_phrase(judge, answer, "answer_cancel_deadline", '11:59 PM, Oct 1')
    check_answer_money(judge, answer, "answer_grand_total", 73.0)
    check_answer_phrase(judge, answer, "answer_strip_hotel", 'Planet Hollywood')
    check_answer_number(judge, answer, "answer_strip_score", '8.5')
    check_answer_money(judge, answer, "answer_strip_price", 72.0)
    check_answer_phrase(judge, answer, "answer_strip_room", 'Room Type Assigned On Arrival')
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
