#!/usr/bin/env python3
"""Verify Speedo--5.

My training partner needs a fitness jammer for daily squad sessions. Find the
most expensive in-stock men's fitness jammer under £50 that is available in
size 34, and buy it with Express Delivery to Sam Whitfield, 7 Quay Street,
Southampton, SO14 2AB, paying with Visa 4111111111111111 exp 09/27, CVC 789.
Report the product name, order number and total.
"""
from verify_lib import (Judge, check_answer_number, check_answer_phrase,
                        check_new_order, check_only_tables_changed,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Speedo--5"

# most expensive in-stock men's fitness jammer under £50 with size 34 in stock:
# Men's Hyperboom Splice Mid Jammer Navy/Green £35.00 (Navy colourway sold out in 34)
PRODUCT_NAME = "Men's Hyperboom Splice Mid Jammer Navy/Green"
UNIT_PRICE = 35.0
SHIPPING = 8.99            # Express Delivery
TOTAL = 43.99


def run_checks(judge, traj, initial_db, after_db):
    from verify_lib import check_order_recipient
    check_order_recipient(judge, initial_db, after_db, 'Sam Whitfield', '7 Quay Street', 'Southampton', 'SO14 2AB')
    from state_review import check_existing_state
    check_existing_state(judge, initial_db, after_db, TASK_ID)
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_men_fitness",
                       r"/collections/men-fitness")
    check_visited_path(judge, traj, "visited_splice_mid_pdp",
                       r"/products/mens-hyperboom-splice-mid-jammer-navy")
    check_visited_path(judge, traj, "visited_checkout", r"/checkout")
    check_visited_path(judge, traj, "visited_confirmation", r"/order/confirmation/SP100008")
    check_answer_phrase(judge, answer, "mentions_product", "Splice Mid Jammer")
    check_answer_phrase(judge, answer, "order_number", "SP100008")
    check_answer_number(judge, answer, "total", "43.99", "order total")

    check_only_tables_changed(judge, initial_db, after_db,
                              allowed={"orders", "order_items"})
    check_new_order(judge, initial_db, after_db,
                    email=None, subtotal=UNIT_PRICE,
                    discount=0.0, discount_code="", shipping_method="Express Delivery",
                    shipping=SHIPPING, total=TOTAL, card_last4="1111",
                    items=[(PRODUCT_NAME, "34", 1, UNIT_PRICE)])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
