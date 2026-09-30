#!/usr/bin/env python3
"""Verify StubHub--3.

Sign in as bob.c@test.com (TestPass123!). Buy exactly two tickets to the November 8 Cardinals at Seahawks game in any section under $250 per ticket, delivered by UPS. Pay with a new Visa test card in Bob's name with a future expiry and a three-digit code. Report the order reference, the delivery fee, the processing fee, and the final total from the confirmation page.
"""
from verify_lib import (Judge, check_answer_any, check_answer_number, check_answer_phrase,
                        check_answer_regex, check_answer_one_of, check_read_only,
                        check_only_tables_changed, check_table_deltas, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier)

TASK_ID = "StubHub--3"



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_cardinals_event", r"/seattle-seahawks-seattle-tickets-11-8-2026/event/160436506")
    check_visited_path(judge, traj, "checkout_review", r"/secure/checkout/review")
    check_visited_path(judge, traj, "checkout_payment", r"/secure/checkout/payment")
    check_visited_path(judge, traj, "checkout_confirmation", r"/secure/checkout/confirmation/")
    from purchase_checks import purchase
    purchase(judge, traj, initial_db, after_db, 3)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
