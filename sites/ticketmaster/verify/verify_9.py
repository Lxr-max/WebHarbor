#!/usr/bin/env python3
"""Verify Ticketmaster--9.

Log in as carol.d@test.com with password TestPass123!. Add a Discover card ending in 8901 (expiring July 2031, cardholder Carol Davis) to the account, confirm it now appears in Payment Options, then remove the card that was already on file, and tell me which card remains saved.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (Judge, check_answer_any, check_answer_money,
                        check_answer_number, check_answer_phrase,
                        check_input_action, check_only_tables_changed,
                        check_purchase_order, check_read_only,
                        check_row_added, check_row_removed, check_row_swap,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Ticketmaster--9"


# Frozen ground truth: carol (user 3) has one card on file (Visa 0341, row id
# 5). Adding the Discover card ending 8901 (exp 07/2031, holder Carol Davis)
# then removing the old card leaves exactly the Discover 8901.
# payment_methods columns: (id, user_id, brand, last4, exp_month, exp_year, holder)
ADDED_ROW = (None, 3, "Discover", "8901", 7, 2031, "Carol Davis")
REMOVED_ROW = (None, 3, "Visa", "0341", None, None, None)


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "signin", r"/signin")
    check_input_action(judge, traj, "demo email", r"carol\.d@test\.com")
    check_visited_path(judge, traj, "Payment Options", r"/member/payment")
    check_input_action(judge, traj, "new card number", r"\d*8901")
    check_answer_phrase(judge, answer, "remaining card brand", "Discover")
    check_answer_phrase(judge, answer, "remaining card last4", "8901")
    check_only_tables_changed(judge, initial_db, after_db, {"payment_methods"})
    check_row_swap(judge, initial_db, after_db, "payment_methods",
                   ADDED_ROW, REMOVED_ROW,
                   "Discover 8901 added and old Visa 0341 removed")


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, run_checks))
