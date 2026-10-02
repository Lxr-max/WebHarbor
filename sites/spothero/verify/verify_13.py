#!/usr/bin/env python3
"""Verify SpotHero--13: Sign in as Carol Davis (carol.d@test.com, TestPass123!) and replace her expiring payment method. Add a Visa ending in 4242, expiring September 2029, labelled Cubs Season; make it the default and remove the Mastercard ending in 6742. Reopen the payment-method list and report the remaining cards and which one is default."""
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

TASK_ID = "SpotHero--13"


def main(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_package(judge, traj, TASK_ID)
    check_seed_contract(judge, initial_db)
    check_visited_path(judge, traj, "login", r"/auth/login")
    check_visited_path(judge, traj, "payment_methods", r"/account/payment-methods")
    check_answer_phrase(judge, answer, "new_card", '4242')
    check_answer_phrase(judge, answer, "card_label", 'Cubs Season')
    check_answer_phrase(judge, answer, "remaining_card", '1881')
    check_payment_methods_delta(judge, initial_db, after_db,
                                added_spec={'user_id': 3, 'brand': 'Visa', 'last4': '4242', 'exp_month': 9, 'exp_year': 2029, 'label': 'Cubs Season'},
                                removed_last4='6742',
                                default_last4='4242')
    check_only_tables_changed(judge, initial_db, after_db, ('payment_methods',))
    return judge


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, main))
