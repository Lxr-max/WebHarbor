#!/usr/bin/env python3
"""Verify Speedo--10.

My training group wants matching printed suits. Compare all colourways of the
Women's Hyperboom Printed Medalist Swimsuit: report each colourway's current
price and which colourways are sold out in size 38, then buy the cheapest
colourway still available in size 38 with Standard Delivery to Freya
Lindqvist, 30 Mill Pond Way, Bristol, BS3 4QN, paying with Visa
4242424242424242 exp 12/28, CVC 123. Report the order number and total.
"""
from verify_lib import (Judge, check_answer_number, check_answer_phrase,
                        check_new_order, check_only_tables_changed,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Speedo--10"

# Colourways: Blue £33.00 (size 38 in stock), Blue/Green £26.40 (38 sold out),
# Blue/Pink £44.00 (38 sold out). Cheapest with size 38 available: Blue £33.00.
PRODUCT_NAME = "Women's Hyperboom Printed Medalist Swimsuit Blue"
UNIT_PRICE = 33.0
SHIPPING = 5.99            # Standard Delivery
TOTAL = 38.99


def run_checks(judge, traj, initial_db, after_db):
    from verify_lib import check_order_recipient
    check_order_recipient(judge, initial_db, after_db, 'Freya Lindqvist', '30 Mill Pond Way', 'Bristol', 'BS3 4QN')
    from state_review import check_existing_state
    check_existing_state(judge, initial_db, after_db, TASK_ID)
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_search", r"/search\?[^ ]*[Hh]yperboom")
    for slug in ("blue-8a000244006", "blue-green", "blue-pink"):
        check_visited_path(judge, traj, f"visited_{slug.replace('-', '_')}",
                           rf"/products/womens-hyperboom-printed-medalist-swimsuit-{slug}")
    check_visited_path(judge, traj, "visited_checkout", r"/checkout")
    check_visited_path(judge, traj, "visited_confirmation", r"/order/confirmation/SP100008")
    check_answer_phrase(judge, answer, "mentions_blue_price", "33.00")
    check_answer_phrase(judge, answer, "order_number", "SP100008")
    check_answer_number(judge, answer, "total", "38.99", "order total")

    check_only_tables_changed(judge, initial_db, after_db,
                              allowed={"orders", "order_items"})
    check_new_order(judge, initial_db, after_db,
                    email=None, subtotal=UNIT_PRICE,
                    discount=0.0, discount_code="", shipping_method="Standard Delivery",
                    shipping=SHIPPING, total=TOTAL, card_last4="4242",
                    items=[(PRODUCT_NAME, "38", 1, UNIT_PRICE)])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
