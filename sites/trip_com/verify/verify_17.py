#!/usr/bin/env python3
"""Verify Trip.com--17.

I'm choosing a popular Hong Kong experience for two people on 12 October 2026. Compare the two most-booked experiences, including their names, booked counts, prices, review counts and package validity. Book the more popular one for both of us, using lead traveller Leo Ng, leo.ng@example.com. Report the total paid and booking reference.
"""
from verify_lib import (check_answer_any, check_answer_count_at_least,
                        check_answer_money, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_read_only,
                        check_rows_added, check_rows_changed, check_seed_contract,
                        check_set_delta, check_screenshots, check_trajectory_identity,
                        check_visited_any, check_visited_path, final_answer, run_verifier)

TASK_ID = "Trip.com--17"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_visited_path(judge, traj, "visited_hk_list", r"/things-to-do/experiences/hong_kong")
    check_visited_path(judge, traj, "visited_tour_detail", r"/things-to-do/detail/94229569")
    check_visited_path(judge, traj, "visited_book_form", r"/things-to-do/book/41")
    check_visited_path(judge, traj, "visited_confirmation", r"/things-to-do/confirmation/")
    check_answer_phrase(judge, answer, "answer_most_booked", 'Top-Rated Hong Kong Tour')
    check_answer_number(judge, answer, "answer_reviews", '27')
    check_answer_number(judge, answer, "answer_booked_count", '610')
    check_answer_money(judge, answer, "answer_total_paid", 153.04)
    check_rows_added(judge, initial_db, after_db, 'attraction_bookings',
                      [['rx:^TA', 94229569, 41, None, '2026-10-12', 2, 'Leo', 'Ng', 'leo.ng@example.com', 153.04, 'confirmed', None]], 'attraction_booking_created')
    check_visited_path(judge, traj, "runnerup_experience", r"/things-to-do/detail/49800455")
    check_answer_phrase(judge, answer, "runnerup_name", "Victoria Harbour")
    check_answer_number(judge, answer, "runnerup_booked", 603)
    check_answer_money(judge, answer, "winner_price", 76.52)
    check_answer_money(judge, answer, "runnerup_price", 13.87)
    check_answer_number(judge, answer, "runnerup_reviews", 40)
    check_answer_number(judge, answer, "validity", 90)
    check_only_tables_changed(judge, initial_db, after_db, {'attraction_bookings'})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
