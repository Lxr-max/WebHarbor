#!/usr/bin/env python3
"""Verify Ticketmaster--6.

I received three Ticketmaster gift cards (HOLIDAY-CHEER-99, SUMMER-JAM-55 and SPRING-FLING-77) and want to put them toward the Boston Bruins vs. Winnipeg Jets game at TD Garden. Check each card's balance on the gift cards page and tell me the balance on each and what they add up to. Would that cover 2 of the cheapest Standard Admission tickets for the game? Also, as stated on this site, what is the maximum amount a single gift card can carry?
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

TASK_ID = "Ticketmaster--6"


# Frozen ground truth (reviewer r2 honest walk 2026-09-27, seed md5
# b03a154d...): gift card balances (deterministic sha1 site hash):
# HOLIDAY-CHEER-99 $500, SUMMER-JAM-55 $75, SPRING-FLING-77 $150 - $725
# combined. 2 of the cheapest Standard Admission tickets for Bruins vs.
# Jets (event 010064EDC5277AB0, Sec BALC Row I, $81.18 each) come to
# $162.36, so the cards cover it. The gift cards page states cards are
# available "in any amount from $25 to $1000" - the site-stated maximum.
EVENT_ID = "010064EDC5277AB0"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "gift cards page", r"/giftcards")
    check_input_action(judge, traj, "first gift card number", r"HOLIDAY-CHEER-99")
    check_input_action(judge, traj, "second gift card number", r"SUMMER-JAM-55")
    check_input_action(judge, traj, "third gift card number", r"SPRING-FLING-77")
    check_visited_path(judge, traj, "Bruins vs Jets event page", rf"/event/{EVENT_ID}")
    check_answer_number(judge, answer, "HOLIDAY-CHEER-99 balance", 500,
                        ["holiday", "balance", "500"])
    check_answer_number(judge, answer, "SUMMER-JAM-55 balance", 75,
                        ["summer", "75"])
    check_answer_number(judge, answer, "SPRING-FLING-77 balance", 150,
                        ["spring", "150"])
    check_answer_number(judge, answer, "combined balance", 725,
                        ["725", "combined", "add up", "total"])
    check_answer_money(judge, answer, "2 cheapest Standard tickets", 162.36)
    if "cover" in answer.lower() and not ("cannot cover" in answer.lower()
                                          or "does not cover" in answer.lower()
                                          or "would not cover" in answer.lower()):
        judge.evidence("answer says the cards cover the 2 cheapest Standard "
                      "Admission tickets")
    else:
        judge.fail("answer does not state that the combined balance covers 2 "
                   "of the cheapest Standard Admission tickets")
    check_answer_number(judge, answer, "maximum single-card amount (site-stated)",
                        1000, ["max", "1000", "up to"])
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, run_checks))
