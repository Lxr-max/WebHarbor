#!/usr/bin/env python3
"""Verify SpotHero--16: I need covered, shuttle-served parking at Chicago O'Hare for four days starting October 3 at noon. Before booking, check the airport FAQs for payment timing and accessible parking, and read the cheapest eligible lot's arrival directions. Reserve it as ord.trip@example.com, then explain the policies, first arrival instruction, total and parking pass type."""
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

TASK_ID = "SpotHero--16"


def main(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_package(judge, traj, TASK_ID)
    check_seed_contract(judge, initial_db)
    check_visited_path(judge, traj, "ord_airport_page", r"/airport/chicago-ord-parking|/airport-code/ORD")
    check_visited_path(judge, traj, "ord_search", r"/search\?kind=airport.*airport=ORD")
    check_visited_path(judge, traj, "covered_filter", r"/search\?.*covered=1")
    check_visited_path(judge, traj, "cheapest_facility_page", r"/facility/106017")
    check_visited_path(judge, traj, "checkout", r"/purchase/hourly\?facility=106017")
    check_visited_path(judge, traj, "confirmation", r"/purchase/confirmation/SH-")
    check_answer_phrase(judge, answer, "pay_timing_faq", 'It depends')
    check_answer_phrase(judge, answer, "accessible_faq", 'first-come, first-serve')
    check_answer_phrase(judge, answer, "facility_named", 'Hyatt Regency')
    check_answer_phrase(judge, answer, "first_instruction", 'Enter this location at 9300 W Bryn Mawr')
    check_answer_number(judge, answer, "total", '82.68')
    check_answer_phrase(judge, answer, "pass_type", 'Scan In/Out')
    check_reservations_delta(judge, initial_db, after_db, answer,
                             expect_added={'facility_id': 106017, 'kind': 'airport', 'total': 82.68, 'email': 'ord.trip@example.com', 'starts': '2026-10-03T12:00', 'ends': '2026-10-07T12:00', 'promo': '', 'user_id': None, 'status': 'upcoming', 'parking_pass': 'Scan In/Out'},
                             expect_updated=None)
    check_only_tables_changed(judge, initial_db, after_db, ('reservations',))
    return judge


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, main))
