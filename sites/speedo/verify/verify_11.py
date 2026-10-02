#!/usr/bin/env python3
"""Verify Speedo--11.

The Women's Endurance+ Medalist Swimsuit comes in several colourways. Compare
them: report each colourway's current price, which colourways are on sale and
how much each saves versus the regular price, and which colourways are the
most expensive. Then add the Navy colourway in size 34 to Alice's wishlist
(alice.j@test.com / TestPass123!).
"""
from verify_lib import (Judge, check_answer_number, check_answer_phrase,
    check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier,
                        table_diff)

TASK_ID = "Speedo--11"

ALICE_ID = 1
NAVY_PRODUCT_ID = 961      # Women's Endurance+ Medalist Swimsuit Navy £23.25
# Standard plain colourways: Black/Red £31; Blue/Green/Navy £23.25.
# Printed and Plus Size variants are outside this task's comparison.


def run_checks(judge, traj, initial_db, after_db):
    from state_review import check_existing_state
    check_existing_state(judge, initial_db, after_db, TASK_ID)
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_search", r"/search\?[^ ]*[Ee]ndurance")
    check_visited_path(judge, traj, "visited_navy_pdp",
                       r"/products/womens-endurance-medalist-swimsuit-navy")
    check_visited_path(judge, traj, "visited_login", r"/login")
    check_answer_number(judge, answer, "mentions_navy_price", 23.25)
    check_answer_number(judge, answer, "mentions_black_price", 31)

    import re
    for colour, price in [("Black",31),("Red",31),("Blue",23.25),("Green",23.25),("Navy",23.25)]:
        segments = re.findall(rf"\b{colour}\b[^;\n]*", answer, re.I)
        judge.check("price_"+colour, any(re.search(rf"(?:£|GBP\s*){price:g}(?:0)?(?!\d)", segment, re.I) for segment in segments))
    judge.check("sale_savings", all(re.search(rf"{c}[^;\n]*7\.75", answer, re.I) for c in ["Blue","Green","Navy"]))
    judge.check("most_expensive", bool(re.search(r"(?:Black[^;\n]*Red|Red[^;\n]*Black)[^;\n]*(?:most expensive|highest)|(?:most expensive|highest)[^;\n]*(?:Black[^;\n]*Red|Red[^;\n]*Black)", answer, re.I)))
    check_only_tables_changed(judge, initial_db, after_db,
                              allowed={"wishlist_items"})
    added, removed, _ = table_diff(initial_db, after_db, "wishlist_items")
    judge.check("navy_added_for_alice",
                len(added) == 1 and len(removed) == 0
                and list(added.values())[0]["user_id"] == ALICE_ID
                and list(added.values())[0]["product_id"] == NAVY_PRODUCT_ID,
                f"added={list(added.values())!r} removed={list(removed.values())!r}")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
