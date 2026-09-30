#!/usr/bin/env python3
"""Verify Ticketmaster--19.

I can no longer attend the Karol G show I bought tickets for. Log in with the demo account (david.k@test.com / TestPass123!) to confirm the order is in my history, then find the numbered steps Ticketmaster gives for selling tickets, the page in my account where the listing starts, and explain what happens after a buyer purchases the listing.
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

TASK_ID = "Ticketmaster--19"


# Frozen ground truth (reviewer r2 honest walk 2026-09-27, seed md5
# b03a154d...): david's Karol G order is TM2609274105 (KAROL G - VIAJANDO
# POR EL MUNDO TROPITOUR, 3 tickets). The sell page gives the numbered steps
# 1. List / 2. Sell / 3. Get paid, and listings start from My Account; the
# contact-us help article gives the phone number 1-800-745-3000 for ordering
# tickets by phone. The task wording pins the phone number to "this site's
# help centre", so a world-knowledge recall without visiting /help/contact-us
# is a navigation-gate FAIL.


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "signin", r"/signin")
    check_input_action(judge, traj, "demo email", r"david\.k@test\.com")
    check_visited_path(judge, traj, "orders list", r"/member/orders")
    check_visited_path(judge, traj, "the Karol G order", r"/member/orders/TM2609274105")
    check_visited_path(judge, traj, "the sell page", r"/sell")
    check_answer_phrase(judge, answer, "sell step 1", "list")
    check_answer_phrase(judge, answer, "sell step 3", "get paid")
    check_answer_phrase(judge, answer, "where the listing starts", "my account")
    check_answer_phrase(judge, answer, "sell step 2", "sell")
    check_answer_phrase(judge, answer, "ticket transfer", "transfer")
    check_answer_phrase(judge, answer, "buyer", "buyer")
    check_answer_phrase(judge, answer, "payout destination", "bank")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, run_checks))
