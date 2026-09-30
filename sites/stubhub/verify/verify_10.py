#!/usr/bin/env python3
"""Verify StubHub--10.

Sign in as alice.j@test.com (TestPass123!). From her account pages, report every purchase with event name, order date, delivery method, and total, including each order's current status. Then report her completed sales with event and payout, and her active ticket listings with section, row, and asking price. Which purchase has the largest total, and how many payment cards does she have on file?
"""
from verify_lib import (Judge, check_answer_any, check_answer_number, check_answer_phrase,
                        check_answer_regex, check_answer_one_of, check_read_only,
                        check_only_tables_changed, check_table_deltas, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier)

TASK_ID = "StubHub--10"



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_purchases", r"/secure/myaccount/purchases")
    check_visited_path(judge, traj, "visited_order_detail", r"/secure/myaccount/purchases/41810907|/secure/myaccount/purchases/41811044")
    check_visited_path(judge, traj, "visited_sales", r"/secure/myaccount/sales")
    check_visited_path(judge, traj, "visited_listings", r"/secure/myaccount/listings")
    check_visited_path(judge, traj, "visited_payments", r"/secure/myaccount/payments")
    
    check_answer_number(judge, answer, "order_metallica_ref", 41810907)
    check_answer_number(judge, answer, "order_metallica_total", "2,572.95")
    check_answer_phrase(judge, answer, "order_metallica_delivery", "Instant download")
    check_answer_phrase(judge, answer, "order_metallica_status", "Confirmed")
    check_answer_number(judge, answer, "order_rush_ref", 41811044)
    check_answer_number(judge, answer, "order_rush_total", "1,106.95")
    check_answer_phrase(judge, answer, "order_rush_delivery", "Mobile transfer")
    check_answer_phrase(judge, answer, "order_rush_status", "Delivered")
    judge.check("largest_purchase",
                "2,572.95" in answer or "Metallica" in answer,
                "answer must identify the Metallica 2-day-pass order as the largest total")
    check_answer_number(judge, answer, "sale_payout", "118.40")
    check_answer_phrase(judge, answer, "sale_status", "Paid")
    check_answer_number(judge, answer, "active_listing_price", 89)
    check_answer_number(judge, answer, "cards_on_file", 2)
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
