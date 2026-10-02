#!/usr/bin/env python3
"""Verify Ticketmaster--13.

The Power to the People Festival at Merriweather Post Pavilion in Columbia, Maryland says prices include fees. If I buy 3 Standard Admission tickets in section 202, row G, what portion of my total is face value and what portion is service fees? Report both amounts and the order total. Also, what would the total and the service-fee portion be for just 1 ticket in that row, and how much per ticket is the cheapest Standard Admission ticket in section 118?
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

TASK_ID = "Ticketmaster--13"


# Frozen ground truth (reviewer r2 honest walk 2026-09-27, seed md5
# b03a154d...): Power to the People Festival @ Merriweather Post Pavilion
# (event 150064B8F802C6F9), Sec 202 Row G (listing 1189, $46.00 face,
# $63.30 incl fees). Ticket-selection breakdown for qty 3: Face Value x3
# $138.00, Service Fee x3 $51.90, Total $189.90. For qty 1: Service Fee
# $17.30, Total $63.30. Cheapest Standard Admission in section 118:
# Row F at $97.01 incl fees per ticket. The search for the festival now
# returns 10 near-name events (The High Kings / The Casualties / Hiss
# Golden Messenger tours), so the venue+city disambiguation is real.
EVENT_ID = "150064B8F802C6F9"
LISTING_ID = "1189"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "power to the people search", r"/search\?q=power")
    check_visited_path(judge, traj, "the festival event page", rf"/event/{EVENT_ID}")
    check_visited_path(judge, traj, "ticket selection for Sec 202 Row G",
                       rf"/event/{EVENT_ID}/tickets\?listing={LISTING_ID}")
    check_answer_money(judge, answer, "face value portion (qty 3)", 138.00)
    check_answer_money(judge, answer, "service fee portion (qty 3)", 51.90)
    check_answer_money(judge, answer, "order total (qty 3)", 189.90)
    check_answer_money(judge, answer, "order total (qty 1)", 63.30)
    check_answer_money(judge, answer, "service fee portion (qty 1)", 17.30)
    check_answer_money(judge, answer, "cheapest Standard in section 118", 97.01)
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, run_checks))
