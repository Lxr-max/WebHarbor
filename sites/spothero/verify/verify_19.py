#!/usr/bin/env python3
"""Verify SpotHero--19: I need monthly parking for a Denver employee starting November 1. Compare the two cheapest options by rate and access hours, then reserve either of them if their rates tie, using denver.office@example.com. Report the selected facility, monthly rate, access hours and reservation code."""
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

TASK_ID = "SpotHero--19"


def main(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_package(judge, traj, TASK_ID)
    check_seed_contract(judge, initial_db)
    check_visited_path(judge, traj, "monthly_search", r"/search\?kind=monthly.*search_string=Denver|/search\?kind=monthly.*Denver")
    check_visited_path(judge, traj, "cheapest_facility_page", r"/facility/15104|/facility/98430")
    check_visited_path(judge, traj, "second_facility_page", r"/facility/15104|/facility/98430")
    check_visited_path(judge, traj, "checkout", r"/purchase/hourly\?facility=15104&.*kind=monthly|/purchase/hourly\?facility=98430&.*kind=monthly")
    check_visited_path(judge, traj, "confirmation", r"/purchase/confirmation/SH-")
    check_answer_any(judge, answer, "cheapest_named", ['1536 Cleveland Pl', '437 13th St', '1248 Delaware St', '1442 Tremont', '1401 Court Pl', '1424 Tremont'])
    check_answer_phrase(judge, answer, "tie_note_or_hours", '5.99')
    check_answer_phrase(judge, answer, "access_hours", '24/7')
    check_any_new_reservation(judge, initial_db, after_db, answer,
                              facility_ids=[15104, 98430, 133999, 161586, 161588, 161660], kind='monthly',
                              total=6.98, email='denver.office@example.com',
                              starts='2026-11-01')
    check_only_tables_changed(judge, initial_db, after_db, ('reservations',))
    return judge


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, main))
