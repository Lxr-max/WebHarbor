#!/usr/bin/env python3
"""Verify Ticketmaster--18.

For my anniversary I want the VIP treatment at Harry Styles: Together, Together at Madison Square Garden on September 30. How many VIP package tickets are available for that show, and what would 2 of them cost all-in? Report the section and row for those VIP seats, how much of the 2-ticket all-in amount is service fees, and how much more 2 VIP tickets cost than 2 of the cheapest Standard Admission seats at the same show.
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

TASK_ID = "Ticketmaster--18"


# Frozen ground truth (reviewer r2 honest walk 2026-09-27, seed md5
# b03a154d...): Harry Styles: Together, Together @ MSG 2026-09-30 (event
# 3B00643505768283): exactly 3 VIP Package tickets available (the qty
# stepper's + disables at 3), Sec GA Row A (listing 21328), $179.35 incl
# fees each. 2-ticket all-in $358.70, of which service fees are $98.02
# (Face Value x2 $260.68). The 2 cheapest Standard Admission seats at the
# same show come to $152.74, so 2 VIP tickets cost $205.96 more.
EVENT_ID = "3B00643505768283"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "harry styles search", r"/search\?q=harry")
    check_visited_path(judge, traj, "the Sep 30 MSG event page", rf"/event/{EVENT_ID}")
    check_visited_path(judge, traj, "the VIP ticket selection page",
                       rf"/event/{EVENT_ID}/tickets\?listing=")
    check_answer_number(judge, answer, "VIP tickets available", 3, ["vip", "3"])
    check_answer_phrase(judge, answer, "VIP section", "GA")
    check_answer_phrase(judge, answer, "VIP row", "Row A")
    check_answer_money(judge, answer, "all-in cost for 2", 358.70)
    check_answer_money(judge, answer, "service fee portion for 2", 98.02)
    check_answer_money(judge, answer, "VIP vs cheapest Standard difference", 205.96)
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, run_checks))
