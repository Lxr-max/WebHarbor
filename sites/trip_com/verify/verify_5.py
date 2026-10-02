#!/usr/bin/env python3
"""Verify Trip.com--5.

I'll be in Orlando on 6 October with a friend and want a city pass under $70 per person. On the Orlando experiences page, filter to city passes and tell me how many are listed and which is cheapest, with its name and price. Then book the best-rated pass under $70 for two guests on 6 October. Report its rating, review count and booked count, the two most important things its highlights promise, and its validity window. Lead traveller: Pat Kim, pat.kim@example.com.
"""
from verify_lib import (check_answer_any, check_answer_count_at_least,
                        check_answer_money, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_read_only,
                        check_rows_added, check_rows_changed, check_seed_contract,
                        check_set_delta, check_screenshots, check_trajectory_identity,
                        check_visited_any, check_visited_path, final_answer, run_verifier)

TASK_ID = "Trip.com--5"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_visited_path(judge, traj, "visited_orlando_list", r"/things-to-do/experiences/orlando")
    check_visited_path(judge, traj, "visited_pass_detail", r"/things-to-do/detail/46680654")
    check_visited_path(judge, traj, "visited_book_form", r"/things-to-do/book/1")
    check_visited_path(judge, traj, "visited_confirmation", r"/things-to-do/confirmation/")
    check_answer_phrase(judge, answer, "answer_pass_name", 'Go City: Orlando Explorer Pass')
    check_answer_number(judge, answer, "answer_rating", '4.0')
    check_answer_number(judge, answer, "answer_review_count", '1')
    check_answer_phrase(judge, answer, "answer_highlight_1", 'Save up to 50%')
    check_answer_any(judge, answer, "answer_highlight_2", ['30 days validity', 'own pace'])
    check_answer_phrase(judge, answer, "answer_validity", '1 year')
    check_answer_money(judge, answer, "answer_total", 128.0)
    check_answer_number(judge, answer, "answer_passes_listed", '3')
    check_answer_phrase(judge, answer, "answer_cheapest_pass", 'Go City Explorer Pass')
    check_answer_money(judge, answer, "answer_cheapest_price", 60.84)
    check_rows_added(judge, initial_db, after_db, 'attraction_bookings',
                      [['rx:^TA', 46680654, 1, None, '2026-10-06', 2, 'Pat', 'Kim', 'pat.kim@example.com', 128.0, 'confirmed', None]], 'attraction_booking_created')
    check_only_tables_changed(judge, initial_db, after_db, {'attraction_bookings'})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
