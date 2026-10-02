#!/usr/bin/env python3
"""Verify Speedo--6.

I need prescription goggles for lane swimming and my optician says -4.5
dioptres. Using the All Goggles catalogue and its lens-type facet, find the
cheapest in-stock prescription goggles offered in a -4.5 lens for under £25,
and buy them with Standard Delivery to Nina Petrova, 15 Riverside Court,
London, SE1 9RE, paying with Visa 4012881288128812 exp 06/28, CVC 111. Report
the product, order number and total.
"""
from verify_lib import (Judge, check_answer_number, check_answer_phrase,
                        check_new_order, check_only_tables_changed,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Speedo--6"

# The lens-type facet value is "Prescription". The cheapest in-stock -4.5
# prescription goggles under £25: Adult Hydropure Optical Goggles Black £21.75
# (on sale from £29.00).
PRODUCT_NAME = "Adult Hydropure Optical Goggles Black"
UNIT_PRICE = 21.75
SHIPPING = 5.99            # Standard Delivery
TOTAL = 27.74


def run_checks(judge, traj, initial_db, after_db):
    from verify_lib import check_order_recipient
    check_order_recipient(judge, initial_db, after_db, 'Nina Petrova', '15 Riverside Court', 'London', 'SE1 9RE')
    from state_review import check_existing_state
    check_existing_state(judge, initial_db, after_db, TASK_ID)
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_goggles_all", r"/collections/goggles-all")
    check_visited_path(judge, traj, "used_lens_facet",
                       r"/collections/goggles-all\?[^ ]*lens_type=Prescription")
    check_visited_path(judge, traj, "visited_hydropure_pdp",
                       r"/products/adult-hydropure-optical-goggles-black")
    check_visited_path(judge, traj, "visited_checkout", r"/checkout")
    check_visited_path(judge, traj, "visited_confirmation", r"/order/confirmation/SP100008")
    check_answer_phrase(judge, answer, "mentions_product", "Hydropure")
    check_answer_phrase(judge, answer, "order_number", "SP100008")
    check_answer_number(judge, answer, "total", "27.74", "order total")

    check_only_tables_changed(judge, initial_db, after_db,
                              allowed={"orders", "order_items"})
    check_new_order(judge, initial_db, after_db,
                    email=None, subtotal=UNIT_PRICE,
                    discount=0.0, discount_code="", shipping_method="Standard Delivery",
                    shipping=SHIPPING, total=TOTAL, card_last4="8812",
                    items=[(PRODUCT_NAME, "-4.5", 1, UNIT_PRICE)])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
