#!/usr/bin/env python3
"""Verify SpotHero--4: Sign in as Alice Johnson (alice.j@test.com, TestPass123!) and adjust her Chicago outing: compare the end times of her two upcoming reservations, extend the earlier-ending reservation by two hours, and cancel the later reservation because she is no longer attending the evening event. Confirm the revised end time, additional charge and cancellation refund terms."""
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

TASK_ID = "SpotHero--4"


def main(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_package(judge, traj, TASK_ID)
    check_seed_contract(judge, initial_db)
    check_visited_path(judge, traj, "login", r"/auth/login")
    check_visited_path(judge, traj, "account", r"/account$")
    check_visited_path(judge, traj, "first_reservation", r"/account/reservations/SH-7K2M4Q")
    check_visited_path(judge, traj, "second_reservation", r"/account/reservations/SH-9W5XN8")
    check_answer_phrase(judge, answer, "sooner_reservation", 'SH-7K2M4Q')
    check_answer_phrase(judge, answer, "sooner_end", '5:00 PM')
    check_answer_number(judge, answer, "extension_charge", '1.85')
    check_answer_phrase(judge, answer, "refund_message", '5-10 business days')
    check_reservations_delta(judge, initial_db, after_db, answer,
                             expect_added=None,
                             expect_updated={'SH-7K2M4Q': {'ends': '2026-09-28T19:00', 'subtotal': 16.58, 'total': 17.57}, 'SH-9W5XN8': {'status': 'cancelled'}})
    check_only_tables_changed(judge, initial_db, after_db, ('reservations',))
    return judge


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, main))
