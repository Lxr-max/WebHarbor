#!/usr/bin/env python3
"""Verify StubHub--12.

Create a new StubHub account with a realistic name and email and a password of your choice. Then buy the cheapest available single ticket to the October 11 49ers at Seahawks game with instant download delivery, paying with any valid test card. Report the order reference and final total, and confirm the order appears in the new account's purchase history.
"""
from verify_lib import (Judge, check_answer_any, check_answer_number, check_answer_phrase,
                        check_answer_regex, check_answer_one_of, check_read_only,
                        check_only_tables_changed, check_table_deltas, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier)

TASK_ID = "StubHub--12"

from verify_lib import table_diff


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_register", r"/secure/register")
    check_visited_path(judge, traj, "visited_49ers_event", r"/seattle-seahawks-seattle-tickets-10-11-2026/event/160436498")
    check_visited_path(judge, traj, "checkout_review", r"/secure/checkout/review")
    check_visited_path(judge, traj, "checkout_payment", r"/secure/checkout/payment")
    check_visited_path(judge, traj, "checkout_confirmation", r"/secure/checkout/confirmation/")
    check_visited_path(judge, traj, "purchase_history", r"/secure/myaccount/purchases")
    from purchase_checks import purchase
    purchase(judge, traj, initial_db, after_db, 12)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
