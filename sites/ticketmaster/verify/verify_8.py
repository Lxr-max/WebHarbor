#!/usr/bin/env python3
"""Verify Ticketmaster--8.

Log in with the demo account (bob.c@test.com / TestPass123!). I need the details of my three-person Kehlani outing. Look through my order history and report: which event did he buy 3 tickets for, in which section and row are those seats, at which venue is that event, and what was the total charged? Confirm the order number so I can identify the booking.
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

TASK_ID = "Ticketmaster--8"


# Frozen ground truth: bob's 3-ticket order is TM2609274103 — THE KEHLANI
# WORLD TOUR: North America at Shoreline Amphitheatre, Sec BALCR Row I,
# total $187.83. Bob's two saved EVENT favorites: "Gorillaz - The Mountain
# Tour" and "Teddy Swims: The UGLY Tour".


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "signin", r"/signin")
    check_input_action(judge, traj, "demo email", r"bob\.c@test\.com")
    check_visited_path(judge, traj, "orders list", r"/member/orders")
    check_visited_path(judge, traj, "the 3-ticket order detail", r"/member/orders/TM2609274103")
    check_answer_phrase(judge, answer, "3-ticket event", "KEHLANI")
    check_answer_phrase(judge, answer, "venue", "Shoreline")
    check_answer_phrase(judge, answer, "seats section", "BALCR")
    check_answer_phrase(judge, answer, "seats row", "Row I")
    check_answer_money(judge, answer, "total charged", 187.83)
    check_answer_phrase(judge, answer, "order number", "TM2609274103")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, run_checks))
