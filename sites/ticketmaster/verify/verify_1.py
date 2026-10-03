#!/usr/bin/env python3
"""Verify Ticketmaster--1.

I'm flexible on dates and want the cheapest way to see Metallica at Sphere in Las Vegas — any listed date works, but I need regular seats (Standard Admission), and 2 tickets together. Compare the dates, then complete the purchase as a guest (email metallica.fan@example.com) and report the event date, the section and row you picked, and the total charged.
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

TASK_ID = "Ticketmaster--1"


# Frozen ground truth: cheapest Standard Admission across the Metallica at
# Sphere dates is Oct 22 (event 17006455FF52D572), Sec BALC Row J, $80.50 per
# ticket incl fees, $161.00 for 2 (listing 10900, qty 5 -> 3). Guest purchase
# with metallica.fan@example.com.
EVENT_ID = "17006455FF52D572"
CANDIDATES = [
    (10900, "BALC", "J", 80.50, 161.00, 3),
]


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "metallica search", r"/search\?q=metallica")
    check_visited_path(judge, traj, "date comparison surface (discover price sort)",
                       r"/discover/concerts\?.*(city=Las%20Vegas|city=Las\+Vegas).*sort=price")
    check_visited_path(judge, traj, "Nov 05 candidate date compared", r"/event/170064550782E86E")
    check_visited_path(judge, traj, "Oct 22 candidate date compared", rf"/event/{EVENT_ID}")
    check_visited_path(judge, traj, "Nov 07 candidate date compared", r"/event/170064550782E874")
    check_visited_path(judge, traj, "ticket selection", rf"/event/{EVENT_ID}/tickets\?listing=")
    check_visited_path(judge, traj, "checkout", r"/checkout")
    check_input_action(judge, traj, "guest email", r"metallica\.fan@example\.com")
    check_visited_path(judge, traj, "order confirmation", r"/order-confirmation/")
    check_answer_phrase(judge, answer, "chosen date", "Oct 22")
    check_answer_phrase(judge, answer, "seats section", "BALC")
    check_answer_phrase(judge, answer, "seats row", "Row J")
    check_answer_money(judge, answer, "total charged", 161.00)
    check_only_tables_changed(judge, initial_db, after_db,
                              {"orders", "ticket_listings"})
    check_purchase_order(judge, initial_db, after_db, answer, dict(
        event_id=EVENT_ID, qty=2, guest_email="metallica.fan@example.com",
        listings=CANDIDATES))


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, run_checks))
