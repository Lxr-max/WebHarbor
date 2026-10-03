#!/usr/bin/env python3
"""Verify Trip.com--18.

I'll be in Shanghai on 12 October 2026 with two friends. Find the highest-rated experience in the Activities category, using the most reviews to break a rating tie. Check what the experience includes, its review count, booked count and package validity, then book it for all three of us. Lead traveller: Wei Chen, wei.chen@example.com. Report the activity's name, rating, highlights and total paid.
"""
from verify_lib import (check_answer_any, check_answer_count_at_least,
                        check_answer_money, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_read_only,
                        check_rows_added, check_rows_changed, check_seed_contract,
                        check_set_delta, check_screenshots, check_trajectory_identity,
                        check_visited_any, check_visited_path, final_answer, run_verifier)

TASK_ID = "Trip.com--18"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_visited_path(judge, traj, "visited_shanghai_list", r"/things-to-do/experiences/shanghai")
    check_visited_path(judge, traj, "visited_activity_detail", r"/things-to-do/detail/99290859")
    check_visited_path(judge, traj, "visited_book_form", r"/things-to-do/book/110")
    check_visited_path(judge, traj, "visited_confirmation", r"/things-to-do/confirmation/")
    check_answer_phrase(judge, answer, "answer_activity", 'Shanghai imperial banquet')
    check_answer_number(judge, answer, "answer_rating", '5.0')
    check_answer_phrase(judge, answer, "answer_highlight_1", 'Shuyanfu')
    check_answer_phrase(judge, answer, "answer_highlight_2", 'taste buds')
    check_answer_money(judge, answer, "answer_total_paid", 48.27)
    check_answer_number(judge, answer, "answer_review_count", '36')
    check_answer_number(judge, answer, "answer_booked_count", '652')
    check_answer_phrase(judge, answer, "answer_validity", '90 days')
    check_rows_added(judge, initial_db, after_db, 'attraction_bookings',
                      [['rx:^TA', 99290859, 110, None, '2026-10-12', 3, 'Wei', 'Chen', 'wei.chen@example.com', 'rx:^48\\.2(69|7)', 'confirmed', None]], 'attraction_booking_created')
    check_only_tables_changed(judge, initial_db, after_db, {'attraction_bookings'})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
