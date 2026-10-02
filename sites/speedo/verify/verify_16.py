#!/usr/bin/env python3
"""Verify Speedo--16.

My son is 9 with a 66cm waist and needs squad jammers. Using the kids' size
guide, work out his Speedo size and age band, then buy the cheapest in-stock
Boys' Endurance+ Jammer in that age band with Standard Delivery to Hannah
Cole, 44 Bramble Road, Exeter, EX2 5TA, paying with Mastercard 5412751234567890
exp 09/28, CVC 333. Report the size band, order number and total.
"""
from verify_lib import (Judge, check_answer_number, check_answer_phrase,
                        check_new_order, check_only_tables_changed,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Speedo--16"

# kids' cm table: waist 66cm -> Speedo size 28 = 9-10 Yrs band.
BAND = "9-10"
PRODUCT_NAME = "Boys' Endurance+ Jammer Black"
UNIT_PRICE = 14.63
SHIPPING = 5.99            # Standard Delivery
TOTAL = 20.62


def run_checks(judge, traj, initial_db, after_db):
    from verify_lib import check_order_recipient
    check_order_recipient(judge, initial_db, after_db, 'Hannah Cole', '44 Bramble Road', 'Exeter', 'EX2 5TA')
    from state_review import check_existing_state
    check_existing_state(judge, initial_db, after_db, TASK_ID)
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_size_guide", r"/pages/size-guides")
    check_visited_path(judge, traj, "visited_jammer_pdp",
                       r"/products/boys-endurance-jammer-black")
    check_visited_path(judge, traj, "visited_checkout", r"/checkout")
    check_visited_path(judge, traj, "visited_confirmation", r"/order/confirmation/SP100008")
    check_answer_phrase(judge, answer, "mentions_band", "9-10")
    check_answer_phrase(judge, answer, "order_number", "SP100008")
    check_answer_number(judge, answer, "total", "20.62", "order total")

    check_only_tables_changed(judge, initial_db, after_db,
                              allowed={"orders", "order_items"})
    check_new_order(judge, initial_db, after_db,
                    email=None, subtotal=UNIT_PRICE,
                    discount=0.0, discount_code="", shipping_method="Standard Delivery",
                    shipping=SHIPPING, total=TOTAL, card_last4="7890",
                    items=[(PRODUCT_NAME, BAND, 1, UNIT_PRICE)])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
