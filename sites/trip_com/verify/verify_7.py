#!/usr/bin/env python3
"""Verify Trip.com--7.

Sign in as Bob Chen (bob.c@test.com, password TestPass123!). I am narrowing down hotels for a San Francisco and Las Vegas trip. Save the best-rated San Francisco hotel that costs less than $200 a night to my wishlist, then remove the more expensive of the two Las Vegas hotels already saved. List the hotels that remain on the wishlist with their nightly prices.
"""
from verify_lib import (check_answer_any, check_answer_count_at_least,
                        check_answer_money, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_read_only,
                        check_rows_added, check_rows_changed, check_seed_contract,
                        check_set_delta, check_screenshots, check_trajectory_identity,
                        check_visited_any, check_visited_path, final_answer, run_verifier)

TASK_ID = "Trip.com--7"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_visited_path(judge, traj, "visited_sign_in", r"/sign-in/")
    check_visited_path(judge, traj, "visited_wishlist", r"/account/wishlist")
    check_visited_path(judge, traj, "visited_sf_list", r"/hotels/list\?")
    check_visited_path(judge, traj, "visited_hotel_detail", r"/hotels/detail/715700")
    check_visited_any(judge, traj, "visited_wishlist_toggle", ['/wishlist/toggle/715700', '/hotels/detail/715700'])
    check_answer_phrase(judge, answer, "answer_fiona", 'Hotel Fiona')
    check_answer_number(judge, answer, "answer_fiona_price", '187')
    check_answer_phrase(judge, answer, "answer_32one", 'Hotel 32One')
    check_answer_number(judge, answer, "answer_32one_price", '212')
    check_answer_phrase(judge, answer, "answer_horseshoe", 'Horseshoe')
    check_answer_number(judge, answer, "answer_horseshoe_price", '56')
    check_set_delta(judge, initial_db, after_db, 'wishlist_items',
                    ['user_id', 'hotel_id'], [[2, 714958]], [[2, 715700]], 'wishlist_set_delta')
    check_only_tables_changed(judge, initial_db, after_db, {'wishlist_items'})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
