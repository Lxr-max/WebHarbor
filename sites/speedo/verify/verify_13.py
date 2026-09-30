#!/usr/bin/env python3
"""Verify Speedo--13.

Without creating an account, buy the Adult Biofuse 2.0 Goggles in Black, One
Size, with Express Delivery to Jamie Okafor, 9 Old Wharf Lane, Plymouth, PL1
3LQ, paying with Visa 4000056655665556 exp 10/27, CVC 222, using email
jamie.okafor@example.com. Report the order number and the delivery time you
were quoted.
"""
from verify_lib import (Judge, check_answer_number, check_answer_phrase,
                        check_new_order, check_not_visited_path,
                        check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier)

TASK_ID = "Speedo--13"

# The catalogue name is "Biofuse 2.0 Goggles Black" (the adult model).
PRODUCT_NAME = "Biofuse 2.0 Goggles Black"
UNIT_PRICE = 25.0
SHIPPING = 8.99            # Express Delivery = next working day
TOTAL = 33.99


def run_checks(judge, traj, initial_db, after_db):
    from verify_lib import check_order_recipient
    check_order_recipient(judge, initial_db, after_db, 'Jamie Okafor', '9 Old Wharf Lane', 'Plymouth', 'PL1 3LQ')
    from state_review import check_existing_state
    check_existing_state(judge, initial_db, after_db, TASK_ID)
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_not_visited_path(judge, traj, "no_account_created", r"/register")
    check_visited_path(judge, traj, "visited_pdp",
                       r"/products/biofuse-2-0-goggles-black")
    check_visited_path(judge, traj, "visited_checkout", r"/checkout")
    check_visited_path(judge, traj, "visited_confirmation", r"/order/confirmation/SP100008")
    check_answer_phrase(judge, answer, "order_number", "SP100008")
    check_answer_phrase(judge, answer, "mentions_delivery", "express")

    check_only_tables_changed(judge, initial_db, after_db,
                              allowed={"orders", "order_items"})
    check_new_order(judge, initial_db, after_db,
                    email="jamie.okafor@example.com", subtotal=UNIT_PRICE,
                    discount=0.0, discount_code="", shipping_method="Express Delivery",
                    shipping=SHIPPING, total=TOTAL, card_last4="5556",
                    items=[(PRODUCT_NAME, "One Size", 1, UNIT_PRICE)])

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
