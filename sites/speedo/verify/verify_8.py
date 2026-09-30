#!/usr/bin/env python3
"""Verify Speedo--8.

Alice (alice.j@test.com / TestPass123!) is curating her wishlist for race
season. Sign in, remove every saved item that is not a swimsuit, then find
the Women's Sculpture Boom Back Swimsuit in Black and save it to the
wishlist. Report which items you removed, which items remain on the
wishlist, and the final wishlist count.
"""
from verify_lib import (Judge, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier,
                        table_diff)

TASK_ID = "Speedo--8"

ALICE_ID = 1
# Alice's seeded wishlist (wishlist_items ids 1-4):
#   1030 Women's Fastskin LZR Pure Valor 2.0 Openback Kneeskin Red/Black  (Swimsuit -> keep)
#   470  Men's Endurance+ Jammer Black                                   (Jammer  -> remove)
#   53   Adult Fastskin Hyper Elite Mirrored Goggles Smoke/Red           (Goggles -> remove)
#   1052 Women's Hyperboom Printed Medalist Swimsuit Blue/Pink           (Swimsuit -> keep)
NON_SWIMSUIT_IDS = {470, 53}
# ... then the Women's Sculpture Boom Back Swimsuit Black is added:
SCULPTURE_PRODUCT_ID = 1154
EXPECTED_FINAL_IDS = {1030, 1052, SCULPTURE_PRODUCT_ID}
EXPECTED_FINAL_COUNT = 3


def run_checks(judge, traj, initial_db, after_db):
    from state_review import check_existing_state
    check_existing_state(judge, initial_db, after_db, TASK_ID)
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_login", r"/login")
    check_visited_path(judge, traj, "visited_wishlist", r"/account/wishlist|/wishlist")
    check_visited_path(judge, traj, "visited_sculpture_pdp",
                       r"/products/womens-sculpture-boom-back-swimsuit-black")

    # answer must report the removed non-swimsuits (both), the remaining
    # swimsuits, and the final count
    check_answer_phrase(judge, answer, "mentions_removed_jammer", "Endurance+ Jammer")
    check_answer_phrase(judge, answer, "mentions_removed_goggles", "Goggles")
    check_answer_phrase(judge, answer, "mentions_remaining_kneeskin", "Kneeskin")
    check_answer_phrase(judge, answer, "mentions_remaining_medalist", "Medalist")
    check_answer_phrase(judge, answer, "mentions_added_sculpture", "Sculpture Boom Back")
    check_answer_number(judge, answer, "final_wishlist_count", EXPECTED_FINAL_COUNT,
                        "final wishlist count")

    check_only_tables_changed(judge, initial_db, after_db,
                              allowed={"wishlist_items"})
    added, removed, _ = table_diff(initial_db, after_db, "wishlist_items")
    judge.check("two_removed_one_added",
                len(removed) == 2 and len(added) == 1,
                f"added={list(added.values())!r} removed={list(removed.values())!r}")
    removed_ids = {r["product_id"] for r in removed.values() if r["user_id"] == ALICE_ID}
    judge.check("removed_are_alice_non_swimsuits",
                all(r["user_id"] == ALICE_ID for r in removed.values())
                and removed_ids == NON_SWIMSUIT_IDS,
                f"removed product_ids={sorted(removed_ids)} expected {sorted(NON_SWIMSUIT_IDS)}")
    if added:
        row = list(added.values())[0]
        judge.check("added_is_sculpture_black",
                    row["user_id"] == ALICE_ID
                    and row["product_id"] == SCULPTURE_PRODUCT_ID,
                    f"added row={dict(row)}")
    # final wishlist content: Alice keeps both seeded swimsuits + the new one
    final = {r[0] for r in after_db.execute(
        "SELECT product_id FROM wishlist_items WHERE user_id = ?", (ALICE_ID,))}
    judge.check("final_wishlist_content",
                final == EXPECTED_FINAL_IDS,
                f"final wishlist product_ids={sorted(final)} "
                f"expected={sorted(EXPECTED_FINAL_IDS)}")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
