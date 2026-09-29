#!/usr/bin/env python3
"""Verify Speedo--1.

Bob (bob.c@test.com / TestPass123!) is narrowing down race jammers. Sign in,
open his wishlist, and remove the jammer that does not belong to the Fastskin
LZR collection. Then find the Men's Fastskin LZR Pure Valor 2.0 Jammer in Blue
and save it to the wishlist. Report which jammer was removed, which items
remain on the wishlist, and the new wishlist count.
"""
from verify_lib import (Judge, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier,
                        table_diff)

TASK_ID = "Speedo--1"

REMOVED_PRODUCT_ID = 553    # Men's Hyperboom Jammer Black/Red (not Fastskin LZR)
ADDED_PRODUCT_ID = 540      # Men's Fastskin LZR Pure Valor 2.0 Jammer Blue
BOB_ID = 2
# Bob's final wishlist (5 rows): the four surviving seeded items + the added
# Valor Blue jammer.
EXPECTED_FINAL_IDS = {527, 815, 4, 951, ADDED_PRODUCT_ID}


def run_checks(judge, traj, initial_db, after_db):
    from state_review import check_existing_state
    check_existing_state(judge, initial_db, after_db, TASK_ID)
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_login", r"/login")
    check_visited_path(judge, traj, "visited_bob_wishlist", r"/account/wishlist|/wishlist")
    check_visited_path(judge, traj, "visited_valor_jammer_pdp",
                       r"/products/mens-fastskin-lzr-pure-valor-2-0-jammer-blue")
    check_answer_phrase(judge, answer, "mentions_removed", "Hyperboom Jammer")
    # the new question also requires reporting the items remaining on the
    # wishlist — the answer must name each survivor, not just the count
    check_answer_phrase(judge, answer, "mentions_remaining_intent", "Pure Intent")
    check_answer_phrase(judge, answer, "mentions_remaining_vanquisher", "Vanquisher")
    check_answer_phrase(judge, answer, "mentions_remaining_bag", "Flex Bag")
    check_answer_phrase(judge, answer, "mentions_remaining_bikini", "Bikini")
    check_answer_phrase(judge, answer, "mentions_added_valor", "Pure Valor")
    check_answer_number(judge, answer, "wishlist_count", 5, "new wishlist count")

    check_only_tables_changed(judge, initial_db, after_db,
                              allowed={"wishlist_items"})
    added, removed, _ = table_diff(initial_db, after_db, "wishlist_items")
    judge.check("one_removed", len(removed) == 1 and len(added) == 1,
                f"added={list(added.values())!r} removed={list(removed.values())!r}")
    if removed:
        row = list(removed.values())[0]
        judge.check("removed_is_hyperboom_jammer",
                    row["user_id"] == BOB_ID and row["product_id"] == REMOVED_PRODUCT_ID,
                    f"removed row={dict(row)}")
    if added:
        row = list(added.values())[0]
        judge.check("added_is_valor_blue",
                    row["user_id"] == BOB_ID and row["product_id"] == ADDED_PRODUCT_ID,
                    f"added row={dict(row)}")
    # final wishlist content: the 4 surviving seeded rows + the Valor Blue jammer
    final = {r[0] for r in after_db.execute(
        "SELECT product_id FROM wishlist_items WHERE user_id = ?", (BOB_ID,))}
    judge.check("final_wishlist_content",
                final == EXPECTED_FINAL_IDS,
                f"final wishlist product_ids={sorted(final)} "
                f"expected={sorted(EXPECTED_FINAL_IDS)}")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
