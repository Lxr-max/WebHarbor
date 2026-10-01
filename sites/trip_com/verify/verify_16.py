#!/usr/bin/env python3
"""Verify Trip.com--16.

Search for Paris Las Vegas and work out what a two-night stay starting 5 October in its cheapest room would cost: the nightly rate before tax, taxes and fees per night, and grand total. Open that room's booking form for 5-7 October to confirm, reporting its name, bed type, how many guests it sleeps and its free-cancellation deadline. The second-cheapest room: report its name and grand total for the same nights. Also report the cheapest room's one-night total for 5-6 October, the hotel's guest score and review count.
"""
from verify_lib import (check_answer_any, check_answer_count_at_least,
                        check_answer_money, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_read_only,
                        check_rows_added, check_rows_changed, check_seed_contract,
                        check_set_delta, check_screenshots, check_trajectory_identity,
                        check_visited_any, check_visited_path, final_answer, run_verifier)

TASK_ID = "Trip.com--16"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_visited_path(judge, traj, "visited_search", r"/search\?")
    check_visited_path(judge, traj, "visited_hotel_detail", r"/hotels/detail/733090")
    check_visited_path(judge, traj, "visited_book_form", r"/hotels/book/(22|24)")
    check_answer_money(judge, answer, "answer_nightly", 167.0)
    check_answer_money(judge, answer, "answer_taxes_per_night", 22.0)
    check_answer_money(judge, answer, "answer_grand_total", 378.0)
    check_answer_phrase(judge, answer, "answer_room", 'Room Type Assigned On Arrival')
    check_answer_phrase(judge, answer, "answer_bed", '1 king bed or 2 queen beds')
    check_answer_number(judge, answer, "answer_sleeps", '2')
    check_answer_phrase(judge, answer, "answer_cancel_deadline", '11:59 PM, Oct 1')
    check_answer_phrase(judge, answer, "answer_second_room", 'Bordeaux Room King')
    check_answer_money(judge, answer, "answer_second_total", 388.0)
    check_answer_money(judge, answer, "answer_onenight_total", 189.0)
    check_answer_number(judge, answer, "answer_score", '8.6')
    check_answer_number(judge, answer, "answer_reviews", '805')
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
