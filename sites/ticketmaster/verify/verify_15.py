#!/usr/bin/env python3
"""Verify Ticketmaster--15.

I'm taking my kids to a Family show in February 2027 but want to spend under $50 per ticket. Using the discovery filters, find the Family event with the lowest starting price that month, report the event name, the city, the date and the starting all-in price, then open that event and tell me the section and row of its cheapest Standard Admission option.
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

TASK_ID = "Ticketmaster--15"


# Frozen ground truth (reviewer r2 honest walk 2026-09-27, seed md5
# b03a154d...): the February 2027 Family events under $50 sorted by lowest
# price are led by Bluey's Big Play at DPAC, Durham, NC on Sun, Feb 28,
# 2027 (event 2D0064F6A84FD696), card price band "$24 - $96" so the
# starting all-in price is $24. Its cheapest Standard Admission option is
# Sec BALC Row G at $41.97 incl fees (listing 6045). The task pins the
# cheapest Standard Admission option, so the cheaper Accessible listing
# (BALC W, $24.26) is not an acceptable answer.
EVENT_ID = "2D0064F6A84FD696"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "discover Family with Feb 2027 + price filters",
                       r"/discover/family\?.*date_from=2027-02")
    check_visited_path(judge, traj, "the Bluey event page", rf"/event/{EVENT_ID}")
    check_answer_phrase(judge, answer, "event name", "Bluey")
    check_answer_phrase(judge, answer, "city", "Durham")
    check_answer_any(judge, answer, "date",
                     ["Feb 28", "February 28", "02-28", "2/28", "2027-02-28"])
    ok_price = ("$24" in answer) or ("24 " in answer) or ("24.26" in answer)
    if ok_price:
        judge.evidence("answer reports the starting all-in price (from $24)")
    else:
        judge.fail("answer does not report the starting all-in price (~$24)")
    check_answer_phrase(judge, answer, "cheapest Standard section", "BALC")
    check_answer_phrase(judge, answer, "cheapest Standard row", "Row G")
    check_answer_money(judge, answer, "cheapest Standard per-ticket price", 41.97)
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, run_checks))
