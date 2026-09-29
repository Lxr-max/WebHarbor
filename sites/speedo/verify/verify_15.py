#!/usr/bin/env python3
"""Verify Speedo--15.

I only remember that the newsletter welcome code starts with WELCOME. Sign up
for the Speedo community newsletter with your own email address (any valid
address) to receive the full code, then add the Adult Bubble Active+ Cap in
White to the basket, apply the code at checkout, and complete the purchase
with Standard Delivery to Alex Novak, 118 Sefton Park Road, Liverpool, L17
1BQ, paying with Visa 4242424242424242 exp 05/28, CVC 444. Report the code,
the discount amount and the order total.
"""
from verify_lib import (Judge, check_answer_number, check_answer_phrase,
                        check_new_order, check_only_tables_changed,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier, table_diff)

TASK_ID = "Speedo--15"

CODE = "WELCOME15"          # revealed by the newsletter signup
PRODUCT_NAME = "Adult Bubble Active+ Cap White"
UNIT_PRICE = 15.0
DISCOUNT = 2.25             # 15% of £15.00
SHIPPING = 5.99             # Standard Delivery
TOTAL = 18.74


def run_checks(judge, traj, initial_db, after_db):
    from verify_lib import check_order_recipient
    check_order_recipient(judge, initial_db, after_db, 'Alex Novak', '118 Sefton Park Road', 'Liverpool', 'L17 1BQ')
    from state_review import check_existing_state
    check_existing_state(judge, initial_db, after_db, TASK_ID)
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_cap_pdp",
                       r"/products/adult-bubble-active-cap-white")
    check_visited_path(judge, traj, "visited_cart", r"/cart")
    check_visited_path(judge, traj, "visited_checkout", r"/checkout")
    check_visited_path(judge, traj, "visited_confirmation", r"/order/confirmation/SP100008")
    check_answer_phrase(judge, answer, "mentions_code", CODE)
    check_answer_number(judge, answer, "discount", "2.25", "discount amount")
    check_answer_number(judge, answer, "total", "18.74", "order total")

    check_only_tables_changed(judge, initial_db, after_db,
                              allowed={"newsletter_signups", "orders", "order_items"})
    a, r, _ = table_diff(initial_db, after_db, "newsletter_signups")
    judge.check("one_signup", len(a) == 1 and len(r) == 0,
                f"added={list(a.values())!r}")
    check_new_order(judge, initial_db, after_db,
                    email=None, subtotal=UNIT_PRICE,
                    discount=DISCOUNT, discount_code=CODE,
                    shipping_method="Standard Delivery", shipping=SHIPPING,
                    total=TOTAL, card_last4="4242",
                    items=[(PRODUCT_NAME, "One Size", 1, UNIT_PRICE)])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
