#!/usr/bin/env python3
"""Verify Trip.com--12.

My company is sending me to both Las Vegas and New York for one night each, 4-5 October. Find the cheapest hotel with available rooms in each city, open each hotel's page to check how many room choices it offers, and report which city's hotel is cheaper and by how much. Include each hotel's name, guest score, nightly price and room-choice count.
"""
from verify_lib import (check_answer_any, check_answer_count_at_least,
                        check_answer_money, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_read_only,
                        check_rows_added, check_rows_changed, check_seed_contract,
                        check_set_delta, check_screenshots, check_trajectory_identity,
                        check_visited_any, check_visited_path, final_answer, run_verifier)

TASK_ID = "Trip.com--12"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_visited_any(judge, traj, "visited_vegas_list", ['/hotels/list\\?city=Las%20Vegas', '/hotels/list\\?city=Las\\+Vegas'])
    check_visited_path(judge, traj, "visited_vegas_detail", r"/hotels/detail/718690")
    check_visited_any(judge, traj, "visited_ny_list", ['/hotels/list\\?city=New%20York', '/hotels/list\\?city=New\\+York'])
    check_visited_path(judge, traj, "visited_ny_detail", r"/hotels/detail/2092657")
    check_answer_phrase(judge, answer, "answer_vegas_hotel", 'Harrah')
    check_answer_number(judge, answer, "answer_vegas_price", '56')
    check_answer_number(judge, answer, "answer_vegas_score", '8.4')
    check_answer_number(judge, answer, "answer_vegas_rooms", '5')
    check_answer_phrase(judge, answer, "answer_ny_hotel", 'HI New York City Hostel')
    check_answer_number(judge, answer, "answer_ny_price", '104')
    check_answer_number(judge, answer, "answer_ny_score", '9.0')
    check_answer_number(judge, answer, "answer_ny_rooms", '2')
    check_answer_phrase(judge, answer, "answer_cheaper_city", 'Vegas')
    check_answer_number(judge, answer, "answer_difference", '48')
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
