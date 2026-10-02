#!/usr/bin/env python3
"""Verify Speedo--3.

Carol's measurements are bust 91cm, waist 77cm, hips 102cm. Using the women's
size guide, work out her Speedo size, then buy the Women's Sculpture Boom Back
Swimsuit in Black in that size with Standard Delivery to Carol Davis, 5 Lido
Terrace, Bristol, BS1 4TR, paying with Mastercard 5309125034239183 exp 03/29,
CVC 456. Report the size you chose, the order number and the total.
"""
from verify_lib import (Judge, check_answer_number, check_answer_phrase,
                        check_new_order, check_only_tables_changed,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Speedo--3"

# women's cm table: bust 86-91 / waist 72 / hips 97 -> size 34;
# bust 91-96 / waist 77 / hips 102 -> size 36 (UK 14). Carol's 91/77/102 -> 36.
SIZE = "36"
PRODUCT = ("Women's Sculpture Boom Back Swimsuit Black", SIZE, 1, 72.0)
SHIPPING = 0.0            # Standard Delivery free over £50
TOTAL = 72.00


def run_checks(judge, traj, initial_db, after_db):
    from verify_lib import check_order_recipient
    check_order_recipient(judge, initial_db, after_db, 'Carol Davis', '5 Lido Terrace', 'Bristol', 'BS1 4TR')
    from state_review import check_existing_state
    check_existing_state(judge, initial_db, after_db, TASK_ID)
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_size_guide", r"/pages/size-guides")
    check_visited_path(judge, traj, "visited_sculpture_pdp",
                       r"/products/womens-sculpture-boom-back-swimsuit-black")
    check_visited_path(judge, traj, "visited_checkout", r"/checkout")
    check_visited_path(judge, traj, "visited_confirmation", r"/order/confirmation/SP100008")
    check_answer_phrase(judge, answer, "mentions_size", "36")
    check_answer_phrase(judge, answer, "order_number", "SP100008")
    check_answer_number(judge, answer, "total", "72.00", "order total")

    check_only_tables_changed(judge, initial_db, after_db,
                              allowed={"orders", "order_items"})
    check_new_order(judge, initial_db, after_db,
                    email=None, subtotal=72.0,
                    discount=0.0, discount_code="",
                    shipping_method="Standard Delivery", shipping=SHIPPING,
                    total=TOTAL, card_last4="9183", items=[PRODUCT])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
