#!/usr/bin/env python3
"""Verify Speedo--9.

Carol (carol.d@test.com / TestPass123!) is close to free UK delivery. Sign in,
check her basket, and work out how much more she needs to spend for free
shipping. Then add every in-stock adult swim cap in purple to the basket,
complete checkout with Standard Delivery, and report the final total and
whether delivery was free.
"""
from verify_lib import (Judge, check_answer_number, check_new_order,
                        check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier,
                        table_diff)

TASK_ID = "Speedo--9"

CAROL_ID = 3
# Carol's seed basket: Girls' Endurance+ Medalist Swimsuit Navy (13.88) +
# Biofuse 2.0 Junior Goggles Clear/Blue (20.00) = 33.88; £16.12 short of £50.
# Every in-stock ADULT swim cap in PURPLE (colour facet Purple, adult):
# Adult Bubble Cap Pink £15.00 (colour attribute Purple, verified verbatim
# against upstream speedo.com) + Adult Long Hair Pace Cap Purple £11.25 +
# Adult Silicone Cap Purple £6.75.
CAPS = [("Adult Bubble Cap Pink", "One Size", 1, 15.00),
        ("Adult Long Hair Pace Cap Purple", "One Size", 1, 11.25),
        ("Adult Silicone Cap Purple", "One Size", 1, 6.75)]
PREEXISTING = [("Girls' Endurance+ Medalist Swimsuit Navy", "4", 1, 13.88),
               ("Biofuse 2.0 Junior Goggles Clear/Blue", "One Size", 1, 20.0)]
SUBTOTAL = 66.88
SHIPPING = 0.0            # Standard Delivery free over £50
TOTAL = 66.88


def run_checks(judge, traj, initial_db, after_db):
    from state_review import check_existing_state
    check_existing_state(judge, initial_db, after_db, TASK_ID)
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_login", r"/login")
    check_visited_path(judge, traj, "visited_cart", r"/cart")
    check_visited_path(judge, traj, "visited_cap_pdp",
                       r"/products/adult-silicone-cap-purple|/products/adult-long-hair-pace-cap-purple|/products/adult-bubble-cap-pink")
    check_visited_path(judge, traj, "visited_checkout", r"/checkout")
    check_visited_path(judge, traj, "visited_confirmation", r"/order/confirmation/SP100008")
    check_answer_number(judge, answer, "total", "66.88", "final total")

    check_only_tables_changed(judge, initial_db, after_db,
                              allowed={"cart_items", "orders", "order_items"})
    added, removed, _ = table_diff(initial_db, after_db, "cart_items")
    judge.check("basket_emptied_by_checkout",
                len(removed) == 2 and len(added) == 0,
                f"removed={list(removed.values())!r} added={list(added.values())!r}")
    check_new_order(judge, initial_db, after_db,
                    email="carol.d@test.com", subtotal=SUBTOTAL,
                    discount=0.0, discount_code="",
                    shipping_method="Standard Delivery", shipping=SHIPPING,
                    total=TOTAL, card_last4=None,   # the task does not pin a card
                    items=PREEXISTING + CAPS)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
