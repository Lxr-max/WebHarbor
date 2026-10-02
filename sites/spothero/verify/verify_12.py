#!/usr/bin/env python3
"""Verify SpotHero--12: I need parking for a Soldier Field outing in Chicago on October 4, noon–6 PM. Find the cheapest lot, check whether I can leave and re-enter during the reservation, and book it as bears.tailgate@example.com. Report the facility, in-and-out policy and total."""
import sys

from verify_lib import (Judge, check_package, check_seed_contract,
                        check_visited_path, check_visited_path_count,
                        check_answer_phrase,
                        check_answer_number, check_answer_any_number,
                        check_answer_any, check_only_tables_changed,
                        check_reservations_delta, check_any_new_reservation,
                        check_payment_methods_delta, check_profile_delta,
                        check_favorites_delta, check_new_user, final_answer,
                        run_verifier)

TASK_ID = "SpotHero--12"


def main(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_package(judge, traj, TASK_ID)
    check_seed_contract(judge, initial_db)
    check_visited_path(judge, traj, "soldier_field_search", r"/search\?.*search_string=Soldier")
    check_visited_path(judge, traj, "price_sort", r"/search\?.*sort=price")
    check_visited_path(judge, traj, "cheapest_facility_page", r"/facility/957")
    check_visited_path(judge, traj, "checkout", r"/purchase/hourly\?facility=957")
    check_visited_path(judge, traj, "confirmation", r"/purchase/confirmation/SH-")
    check_answer_phrase(judge, answer, "facility_named", '1212 S Michigan')
    check_answer_phrase(judge, answer, "in_out_finding", 'not allow')
    check_answer_number(judge, answer, "total", '10.19')
    check_reservations_delta(judge, initial_db, after_db, answer,
                             expect_added={'facility_id': 957, 'kind': 'hourly', 'total': 10.19, 'email': 'bears.tailgate@example.com', 'starts': '2026-10-04T12:00', 'ends': '2026-10-04T18:00', 'promo': '', 'user_id': None, 'status': 'upcoming'},
                             expect_updated=None)
    check_only_tables_changed(judge, initial_db, after_db, ('reservations',))
    return judge


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, main))
