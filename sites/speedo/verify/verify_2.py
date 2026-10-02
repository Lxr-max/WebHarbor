#!/usr/bin/env python3
"""Verify Speedo--2.

Alice (alice.j@test.com / TestPass123!) is placing a club order. Sign in, clear
her current basket, then add the Women's Endurance+ Medalist Swimsuit in Black
and in Navy, both size 34. Apply the newsletter welcome discount code, then
check out with Standard Delivery to 12 Marina Way, Flat 3, Brighton, BN1 1AA,
paying with Visa 4242424242424242 exp 11/28, CVC 321. Report the order number
and total.
"""
from verify_lib import (Judge, check_answer_number, check_answer_phrase, check_new_order,
                        check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier,
                        table_diff)

TASK_ID = "Speedo--2"

ALICE_ID = 1
BLACK = ("Women's Endurance+ Medalist Swimsuit Black", "34", 1, 31.0)
NAVY = ("Women's Endurance+ Medalist Swimsuit Navy", "34", 1, 23.25)
SUBTOTAL = 54.25
DISCOUNT = 8.14          # WELCOME15 = 15% of 54.25
SHIPPING = 5.99          # Standard Delivery
TOTAL = 52.10


def run_checks(judge, traj, initial_db, after_db):
    from verify_lib import check_order_recipient
    check_order_recipient(judge, initial_db, after_db, 'Alice Johnson', '12 Marina Way', 'Brighton', 'BN1 1AA', 'Flat 3')
    from state_review import check_existing_state
    check_existing_state(judge, initial_db, after_db, TASK_ID)
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_login", r"/login")
    check_visited_path(judge, traj, "visited_cart", r"/cart")
    check_visited_path(judge, traj, "visited_black_pdp",
                       r"/products/womens-endurance-medalist-swimsuit-black")
    check_visited_path(judge, traj, "visited_navy_pdp",
                       r"/products/womens-endurance-medalist-swimsuit-navy")
    check_visited_path(judge, traj, "visited_checkout", r"/checkout")
    check_visited_path(judge, traj, "visited_confirmation", r"/order/confirmation/SP100008")
    check_answer_phrase(judge, answer, "order_number", "SP100008")
    check_answer_number(judge, answer, "total", "52.10", "order total")

    check_only_tables_changed(judge, initial_db, after_db,
                              allowed={"cart_items", "orders", "order_items"})
    # Alice's two seed cart rows must be gone (cleared) and none re-added
    added, removed, _ = table_diff(initial_db, after_db, "cart_items")
    judge.check("basket_cleared", len(removed) == 2 and len(added) == 0,
                f"removed={list(removed.values())!r} added={list(added.values())!r}")
    check_new_order(judge, initial_db, after_db,
                    email="alice.j@test.com", subtotal=SUBTOTAL,
                    discount=DISCOUNT, discount_code="WELCOME15",
                    shipping_method="Standard Delivery", shipping=SHIPPING,
                    total=TOTAL, card_last4="4242", items=[BLACK, NAVY])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
