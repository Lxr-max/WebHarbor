#!/usr/bin/env python3
"""Verify Ticketmaster--0.

Two of us want to see the New York Knicks take on the Detroit Pistons at Madison Square Garden without overspending. Using the demo account (alice.j@test.com / TestPass123!), complete the purchase of the two cheapest available Standard Admission tickets, then confirm the order in My Account and report the order number, the seats (section and row), and the all-in total.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (Judge, check_answer_any, check_answer_money,
                        check_answer_number, check_answer_phrase,
                        check_input_action, check_only_tables_changed,
                        check_purchase_order, check_read_only,
                        check_row_added, check_row_removed,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Ticketmaster--0"


# Frozen ground truth (reviewer r2 honest walk 2026-09-27, seed md5
# b03a154d...): Knicks vs Pistons @ MSG, event 3B006511E91D862B. The
# task pins "cheapest available Standard Admission": Sec BALC Row I at
# $286.90 incl fees (listing 7053, qty 4 -> 2), $573.80 all-in for 2.
# The cheapest Standard minimum is unique on the event page (next Standard
# listing is $291.71); the cheaper Accessible listing (BALC W, $166.59) is
# NOT an acceptable purchase under the pinned wording.
EVENT_ID = "3B006511E91D862B"
CANDIDATES = [
    (7053, "BALC", "I", 286.90, 573.80, 2),   # Standard, qty 4 -> 2
]


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "signin", r"/signin")
    check_input_action(judge, traj, "demo email", r"alice\.j@test\.com")
    check_visited_path(judge, traj, "knicks search", r"/search\?q=knicks")
    check_visited_path(judge, traj, "the Knicks event page", rf"/event/{EVENT_ID}")
    check_visited_path(judge, traj, "ticket selection", rf"/event/{EVENT_ID}/tickets\?listing=")
    check_visited_path(judge, traj, "checkout", r"/checkout")
    check_visited_path(judge, traj, "order confirmation", r"/order-confirmation/")
    check_visited_path(judge, traj, "My Account orders", r"/member/orders")
    check_answer_phrase(judge, answer, "seats section", "BALC")
    check_answer_phrase(judge, answer, "seats row", "Row I")
    ok_total = ("573.80" in answer) or ("573.8" in answer)
    if ok_total:
        judge.evidence("answer reports the all-in total for the two cheapest "
                      "Standard Admission tickets ($573.80)")
    else:
        judge.fail("answer does not report the $573.80 all-in total for the two "
                   "cheapest Standard Admission tickets")
    check_only_tables_changed(judge, initial_db, after_db,
                              {"orders", "ticket_listings"})
    check_purchase_order(judge, initial_db, after_db, answer, dict(
        event_id=EVENT_ID, qty=2, user_id=1, listings=CANDIDATES))


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, run_checks))
