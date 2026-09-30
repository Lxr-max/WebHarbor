#!/usr/bin/env python3
"""Verify SpotHero--9: I need the cheapest parking near Union Square in San Francisco on October 3, 9 AM–5 PM, but my plans may change. Check the cancellation deadline, when payment is taken and the guarantee if no spot is available. Explain those terms, then reserve the cheapest option as policy.check@example.com and report the facility and total."""
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

TASK_ID = "SpotHero--9"


def main(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_package(judge, traj, TASK_ID)
    check_seed_contract(judge, initial_db)
    check_visited_path(judge, traj, "faq_page", r"/faq")
    check_visited_path(judge, traj, "guarantee_page", r"/about/parking-guarantee")
    check_visited_path(judge, traj, "search_results", r"/search\?.*search_string=Union")
    check_visited_path(judge, traj, "price_sort", r"/search\?.*sort=price")
    check_visited_path(judge, traj, "cheapest_facility_page", r"/facility/8467")
    check_visited_path(judge, traj, "checkout", r"/purchase/hourly\?facility=8467")
    check_visited_path(judge, traj, "confirmation", r"/purchase/confirmation/SH-")
    check_answer_phrase(judge, answer, "cancellation_policy", 'minute before they begin')
    check_answer_phrase(judge, answer, "card_charge_timing", 'pay and reserve')
    check_answer_phrase(judge, answer, "guarantee_promise", 'money back')
    check_answer_phrase(judge, answer, "booked_facility", '495 Mission Rock')
    check_answer_number(judge, answer, "total", '7.88')
    check_reservations_delta(judge, initial_db, after_db, answer,
                             expect_added={'facility_id': 8467, 'kind': 'hourly', 'total': 7.88, 'email': 'policy.check@example.com', 'starts': '2026-10-03T09:00', 'ends': '2026-10-03T17:00', 'promo': '', 'user_id': None, 'status': 'upcoming'},
                             expect_updated=None)
    check_only_tables_changed(judge, initial_db, after_db, ('reservations',))
    return judge


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, main))
