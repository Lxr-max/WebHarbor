#!/usr/bin/env python3
"""Verify Ticketmaster--14.

Wicked is going on tour and I want to catch the earliest possible performance I can. Find the first upcoming Wicked (Touring) stop and report the date, the venue and the city, plus how many stops the tour lists in total, when the last one is, and the act's average fan rating and review count. Then find the cheapest Standard Admission option for that first performance and tell me its section, row and all-in price per ticket, and how many tickets one order can contain.
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

TASK_ID = "Ticketmaster--14"


# Frozen ground truth (reviewer r2 honest walk 2026-09-27, seed md5
# b03a154d...): earliest Wicked (Touring) stop is Wed, Mar 31, 2027 at
# DPAC in Durham, NC (event 2D0064FDEC59E76F, artist 864373). The artist
# page lists 20 tour stops, the last on Apr 18, 2027; rating 4.7 out of 5
# based on 936 reviews. Cheapest Standard Admission for the first
# performance: Sec BALC Row J at $101.82 incl fees (listing 9532). Its
# event ticket limit is 8. The task pins Standard Admission, so the
# cheaper Accessible listing (BALC W, $60.19) is not an acceptable answer.
EVENT_ID = "2D0064FDEC59E76F"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "wicked search", r"/search\?q=wicked")
    check_visited_path(judge, traj, "the Wicked artist page", r"/artist/864373")
    check_visited_path(judge, traj, "the first tour stop event page", rf"/event/{EVENT_ID}")
    check_answer_any(judge, answer, "first stop date",
                     ["Mar 31", "March 31", "03-31", "3/31", "2027-03-31"])
    check_answer_phrase(judge, answer, "venue", "DPAC")
    check_answer_phrase(judge, answer, "city", "Durham")
    check_answer_number(judge, answer, "total tour stops", 20,
                        ["20", "stops", "tour"])
    check_answer_any(judge, answer, "last stop date",
                     ["Apr 18", "April 18", "04-18", "4/18", "2027-04-18"])
    check_answer_number(judge, answer, "average fan rating", 4.7,
                        ["4.7", "rating"])
    check_answer_number(judge, answer, "review count", 936, ["936", "review"])
    check_answer_phrase(judge, answer, "cheapest Standard section", "BALC")
    check_answer_phrase(judge, answer, "cheapest Standard row", "Row J")
    check_answer_money(judge, answer, "cheapest Standard per-ticket price", 101.82)
    check_answer_number(judge, answer, "per-order limit", 8,
                        ["8", "limit", "order"])
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, run_checks))
