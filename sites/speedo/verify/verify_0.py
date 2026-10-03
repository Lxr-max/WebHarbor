#!/usr/bin/env python3
"""Verify Speedo--0.

My daughter needs her first serious race suit. Use the swimwear quiz shopping
for a woman who does racing, choose the Fastskin Ignite route, and buy the
cheapest recommended kneeskin in size 26. Pay with Visa 4242424242424242 exp
12/28, CVC 123, express delivery to Maya Torres, 22 Harbour Reach, Portsmouth,
PO1 3XY. Report the order number and the total charged.
"""
from verify_lib import (Judge, check_answer_number, check_answer_phrase,
                        check_new_order, check_only_tables_changed,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Speedo--0"

PRODUCT = "Women's Fastskin LZR Ignite Kneeskin Black/Grey"   # cheapest recommended kneeskin (£114, on sale)
UNIT_PRICE = 114.0
SHIPPING = 8.99                                                # Express Delivery
TOTAL = 122.99


def run_checks(judge, traj, initial_db, after_db):
    from verify_lib import check_order_recipient
    check_order_recipient(judge, initial_db, after_db, 'Maya Torres', '22 Harbour Reach', 'Portsmouth', 'PO1 3XY')
    from state_review import check_existing_state
    check_existing_state(judge, initial_db, after_db, TASK_ID)
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_swimsuit_quiz", r"/pages/swimsuit-quiz")
    check_visited_path(judge, traj, "visited_quiz_results", r"/pages/swimsuit-quiz/results")
    check_visited_path(judge, traj, "visited_kneeskin_pdp",
                       r"/products/womens-fastskin-lzr-ignite-kneeskin")
    check_visited_path(judge, traj, "visited_checkout", r"/checkout")
    check_visited_path(judge, traj, "visited_confirmation", r"/order/confirmation/SP100008")
    check_answer_phrase(judge, answer, "mentions_product", "Kneeskin")
    check_answer_phrase(judge, answer, "order_number", "SP100008")
    check_answer_number(judge, answer, "total", "122.99", "total charged")

    check_only_tables_changed(judge, initial_db, after_db,
                              allowed={"orders", "order_items"})
    candidates = initial_db.execute("SELECT id, name, price FROM products WHERE department_slug='women' AND activity='Racing' AND sold_out=0 AND name LIKE '%Ignite%' ORDER BY sort LIMIT 3").fetchall()
    best = {r[0]:r[1] for r in candidates if r[2] == min(x[2] for x in candidates)}
    added_items = after_db.execute("SELECT product_id, product_name FROM order_items WHERE id > 11").fetchall()
    judge.check("cheapest_recommended", len(added_items)==1 and added_items[0][0] in best)
    product_name = added_items[0][1] if len(added_items)==1 else PRODUCT
    check_new_order(judge, initial_db, after_db,
                    email=None, subtotal=UNIT_PRICE,
                    discount=0.0, discount_code="", shipping_method="Express Delivery",
                    shipping=SHIPPING, total=TOTAL, card_last4="4242",
                    items=[(product_name, "26", 1, UNIT_PRICE)])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
