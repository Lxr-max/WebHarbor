#!/usr/bin/env python3
"""Verify Speedo--18.

Use the goggles quiz to find goggles for an adult who swims for fitness and
wants a clear lens. From the recommendations, buy the cheapest pair that is
in stock, with Standard Delivery to Marta Nowak, 61 Castle View, Edinburgh,
EH1 2NB, paying with Visa 4500123456789012 exp 02/28, CVC 555. Report the
product, order number and total.
"""
from verify_lib import (Judge, check_answer_number, check_answer_phrase,
                        check_new_order, check_only_tables_changed,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Speedo--18"

# The quiz (Adults -> Fitness -> Clear) recommends: Adult Biofuse 2.0 Optical
# Goggles Clear/Blue £30.00, Adult Hydrosity 2.0 Goggles Teal/Clear £18.00,
# Biofuse 2.0 Goggles Red £25.00. Cheapest in stock: Hydrosity 2.0 £18.00.
PRODUCT_NAME = "Adult Hydrosity 2.0 Goggles Teal/Clear"
UNIT_PRICE = 18.0
SHIPPING = 5.99            # Standard Delivery
TOTAL = 23.99


def run_checks(judge, traj, initial_db, after_db):
    from verify_lib import check_order_recipient
    check_order_recipient(judge, initial_db, after_db, 'Marta Nowak', '61 Castle View', 'Edinburgh', 'EH1 2NB')
    from state_review import check_existing_state
    check_existing_state(judge, initial_db, after_db, TASK_ID)
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_goggles_quiz", r"/pages/goggles-quiz")
    check_visited_path(judge, traj, "visited_quiz_results", r"/pages/goggles-quiz/results")
    check_visited_path(judge, traj, "visited_hydrosity_pdp",
                       r"/products/adult-hydrosity-2-0-goggles-teal-clear")
    check_visited_path(judge, traj, "visited_checkout", r"/checkout")
    check_visited_path(judge, traj, "visited_confirmation", r"/order/confirmation/SP100008")
    check_answer_phrase(judge, answer, "mentions_product", "Hydrosity")
    check_answer_phrase(judge, answer, "order_number", "SP100008")
    check_answer_number(judge, answer, "total", "23.99", "order total")

    check_only_tables_changed(judge, initial_db, after_db,
                              allowed={"orders", "order_items"})
    check_new_order(judge, initial_db, after_db,
                    email=None, subtotal=UNIT_PRICE,
                    discount=0.0, discount_code="", shipping_method="Standard Delivery",
                    shipping=SHIPPING, total=TOTAL, card_last4="9012",
                    items=[(PRODUCT_NAME, "One Size", 1, UNIT_PRICE)])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
