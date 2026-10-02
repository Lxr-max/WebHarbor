#!/usr/bin/env python3
"""Verify Ticketmaster--4.

I'm planning to attend the Boston Bruins vs. Winnipeg Jets game at TD Garden. Compare the cheapest Standard Admission option with the next-cheapest Standard Admission option, including section, row, face value, service fee and all-in price per ticket for each. Tell me the extra cost for two people to choose the second option, and the venue's street address.
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

TASK_ID = "Ticketmaster--4"


# Frozen ground truth (reviewer r2 honest walk 2026-09-27, seed md5
# b03a154d...): Sphere venue page (155762) lists 20 upcoming events, TD
# Garden (8337) lists 18, so TD Garden has fewer. TD Garden street address
# "100 Legends Way, Boston, MA 02114". Cheapest Standard Admission ticket
# for Bruins vs. Winnipeg Jets (event 010064EDC5277AB0): $81.18 incl fees
# (Sec BALC Row I, listing 15685). The task pins Standard Admission, so the
# cheaper Accessible listing ($47.83) is not an acceptable answer.
SPHERE_ID = "155762"
TDG_ID = "8337"
EVENT_ID = "010064EDC5277AB0"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "TD Garden venue page", rf"/venue/{TDG_ID}")
    check_visited_path(judge, traj, "Bruins vs Jets event page", rf"/event/{EVENT_ID}")
    check_answer_phrase(judge, answer, "TD Garden street address", "100 Legends Way")
    check_answer_money(judge, answer, "cheapest Standard Admission ticket", 81.18)
    check_answer_money(judge, answer, "second Standard Admission price", 82.56)
    check_answer_money(judge, answer, "two-person upgrade", 2.76)
    check_answer_phrase(judge, answer, "first row", "row I")
    check_answer_phrase(judge, answer, "second row", "row H")
    check_visited_path(judge, traj, "ticket cost breakdown", rf"/event/{EVENT_ID}/tickets")
    check_answer_money(judge, answer, "first face value", 59)
    check_answer_money(judge, answer, "first service fee", 22.18)
    check_answer_money(judge, answer, "second face value", 60)
    check_answer_money(judge, answer, "second service fee", 22.56)
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, run_checks))
