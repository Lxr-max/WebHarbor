#!/usr/bin/env python3
"""Verify Ticketmaster--17.

Get 4 tickets together for the WEEZER: The Gathering show at Barclays Center in Brooklyn using the demo account (alice.j@test.com / TestPass123!). Pick the cheapest Standard Admission option that still has at least 4 seats together, complete the purchase, then confirm the order shows up in My Account and report the order number, the section and row, and the total.
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

TASK_ID = "Ticketmaster--17"


# Frozen ground truth (reviewer r2 honest walk 2026-09-27, seed md5
# b03a154d...): WEEZER: The Gathering @ Barclays Center 2026-09-30 (event
# 3000646DEDC399B4). Cheapest Standard Admission with >=4 seats together:
# Sec 201 Row H at $78.43 incl fees per ticket (listing 34930, qty 6 -> 2),
# $313.72 for 4. The former tie at the minimum was broken in the seed
# (_detie_minimums): Sec 202 Row F now sits at $78.45, so 201 H is the
# unique cheapest qualifying option - no alternate listing is accepted.
EVENT_ID = "3000646DEDC399B4"
CANDIDATES = [
    (34930, "201", "H", 78.43, 313.72, 2),
]


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "signin", r"/signin")
    check_input_action(judge, traj, "demo email", r"alice\.j@test\.com")
    check_visited_path(judge, traj, "weezer search", r"/search\?q=weezer")
    check_visited_path(judge, traj, "the Barclays event page with qty=4 filter",
                       rf"/event/{EVENT_ID}\?.*qty=4")
    check_visited_path(judge, traj, "ticket selection", rf"/event/{EVENT_ID}/tickets\?listing=")
    check_visited_path(judge, traj, "checkout", r"/checkout")
    check_visited_path(judge, traj, "order confirmation", r"/order-confirmation/")
    check_visited_path(judge, traj, "My Account orders", r"/member/orders")
    check_answer_phrase(judge, answer, "seats section", "201")
    check_answer_phrase(judge, answer, "seats row", "Row H")
    check_answer_money(judge, answer, "total", 313.72)
    check_only_tables_changed(judge, initial_db, after_db,
                              {"orders", "ticket_listings"})
    check_purchase_order(judge, initial_db, after_db, answer, dict(
        event_id=EVENT_ID, qty=4, user_id=1, listings=CANDIDATES))


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, run_checks))
