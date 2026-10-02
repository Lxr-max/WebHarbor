#!/usr/bin/env python3
"""Verify Ticketmaster--7.

My friend can no longer join me for a show and I'd like to give her my ticket. Log in with the demo account (alice.j@test.com / TestPass123!), find the order for Aladdin - The Musical, and report its order number, how many tickets it covers, the seats, and the card charged. Then, based on the help centre's guidance: from which page does a ticket transfer start, what does the recipient need to do, what happens to the original ticket once she accepts it, and when do mobile tickets usually arrive?
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

TASK_ID = "Ticketmaster--7"


# Frozen ground truth (reviewer r2 honest walk 2026-09-27, seed md5
# b03a154d...): alice's Aladdin order is TM2609274100 - 2 tickets, Sec
# BALCR Row F, charged to Visa •••• 4242 (order detail page). Help centre
# transfer-tickets: transfer starts from the order page in your account -
# open the order, select the tickets, enter the recipient's email; the
# recipient accepts into her own account and the original barcode is
# invalidated. Mobile-tickets article: mobile tickets are usually
# transferred within 24-72 hours of the event.


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "signin", r"/signin")
    check_input_action(judge, traj, "demo email", r"alice\.j@test\.com")
    check_visited_path(judge, traj, "the Aladdin order", r"/member/orders/TM2609274100")
    check_visited_path(judge, traj, "transfer help article", r"/help/transfer-tickets")
    check_visited_path(judge, traj, "mobile tickets help article", r"/help/mobile-tickets")
    check_answer_phrase(judge, answer, "order number", "TM2609274100")
    check_answer_number(judge, answer, "tickets in the order", 2,
                        ["2", "two", "tickets"])
    check_answer_phrase(judge, answer, "seats section", "BALCR")
    check_answer_phrase(judge, answer, "seats row", "Row F")
    ok_card = "4242" in answer
    if ok_card:
        judge.evidence("answer reports the card charged (Visa ending 4242)")
    else:
        judge.fail("answer does not report the card charged (Visa ending 4242)")
    check_answer_phrase(judge, answer, "where the transfer starts", "order")
    check_answer_phrase(judge, answer, "recipient detail", "email")
    check_answer_any(judge, answer, "what happens to the original ticket",
                     ["invalidated", "invalid", "no longer valid", "voided"])
    ok_arrival = ("24-72" in answer) or ("24 to 72" in answer) or ("24–72" in answer)
    if ok_arrival:
        judge.evidence("answer reports the mobile-ticket arrival window "
                      "(within 24-72 hours of the event)")
    else:
        judge.fail("answer does not report when mobile tickets usually arrive "
                   "(within 24-72 hours of the event)")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, run_checks))
