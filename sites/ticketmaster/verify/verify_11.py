#!/usr/bin/env python3
"""Verify Ticketmaster--11.

I don't have a Ticketmaster account. As a guest, buy 2 of the cheapest available Standard Admission tickets for the Boston Bruins vs. Winnipeg Jets game at TD Garden using my email sports.fan@example.com, and report the order number, the seats (section and row), and the total charged.
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

TASK_ID = "Ticketmaster--11"


# Frozen ground truth: Bruins vs Jets @ TD Garden (event 010064EDC5277AB0);
# cheapest Standard Admission Sec BALC Row I, $81.18 incl fees per ticket,
# $162.36 for 2 (listing 15685, qty 5 -> 3). Guest purchase with
# sports.fan@example.com.
EVENT_ID = "010064EDC5277AB0"
CANDIDATES = [
    (15685, "BALC", "I", 81.18, 162.36, 3),
]


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "bruins search", r"/search\?q=bruins")
    check_visited_path(judge, traj, "the Bruins event page", rf"/event/{EVENT_ID}")
    check_visited_path(judge, traj, "ticket selection", rf"/event/{EVENT_ID}/tickets\?listing=")
    check_visited_path(judge, traj, "checkout", r"/checkout")
    check_input_action(judge, traj, "guest email", r"sports\.fan@example\.com")
    check_visited_path(judge, traj, "order confirmation", r"/order-confirmation/")
    check_answer_phrase(judge, answer, "seats section", "BALC")
    check_answer_phrase(judge, answer, "seats row", "Row I")
    check_answer_money(judge, answer, "total charged", 162.36)
    check_only_tables_changed(judge, initial_db, after_db,
                              {"orders", "ticket_listings"})
    check_purchase_order(judge, initial_db, after_db, answer, dict(
        event_id=EVENT_ID, qty=2, guest_email="sports.fan@example.com",
        listings=CANDIDATES))


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, run_checks))
