#!/usr/bin/env python3
"""Verify StubHub--4.

Sign in as alice.j@test.com (TestPass123!). List two tickets together for the November 2 Bears at Seahawks game: section 220, row 14, seats 5-6, priced at $195 each. From My Listings, update the new listing's price to $180 and confirm the new price is shown. Then report the game's date and venue as displayed, the total number of listings Alice has for sale, and their combined asking value.
"""
from verify_lib import (Judge, check_answer_any, check_answer_number, check_answer_phrase,
                        check_answer_regex, check_answer_one_of, check_read_only,
                        check_only_tables_changed, check_table_deltas, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier)

TASK_ID = "StubHub--4"

import re


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_sell_landing", r"/selltickets(\?|$)")
    check_visited_path(judge, traj, "visited_sell_form", r"/selltickets/event/160436503")
    check_visited_path(judge, traj, "visited_my_listings", r"/secure/myaccount/listings")
    
    check_answer_number(judge, answer, "new_price_shown", 180)
    check_answer_number(judge, answer, "alice_listing_count", 2)
    check_answer_number(judge, answer, "seeded_listing_price", 89)
    judge.check("combined_asking_value",
                bool(re.search(r"269|716", answer)),
                "answer must report the combined asking value ($269 per-ticket sum / $716 total)")
    check_answer_phrase(judge, answer, "game_venue", "Lumen Field")
    judge.check("game_date_displayed",
                "Nov 2" in answer or "November 2" in answer or "Nov 3" in answer,
                "answer must report the game's displayed date (Mon, Nov 2 as shown on the "
                "site post-F5; the pre-fix UTC display said Nov 3)")
    check_table_deltas(judge, initial_db, after_db, {
        "listings": {"added": [(20886,)]},
        # r2 sync (2026-09-26): the F9 fix removed the +1 double-count, so a
        # new listing moves event 132's listing_count 10 -> 11 (the r1 contract
        # froze the pre-fix inflated 10 -> 12). Repricing now also refreshes the
        # event stats, so the $180 repriced listing becomes the new get-in:
        # min_price 298 -> 180 (verified against the live unsold rows).
        "events": {"changed": {(132,): {"listing_count": (10, 11),
                                       "min_price": (298, 180)}}},
    })
    row = after_db.execute("SELECT * FROM listings WHERE id=20886").fetchone()
    judge.check("new_listing_row_exact",
                row is not None and row["event_id"] == 132 and row["section"] == "220"
                and row["row"] == "14" and row["quantity"] == 2 and row["price"] == 180
                and row["seller_id"] == 1,
                f"repriced listing must be 220/row 14/qty 2/$180: {dict(row) if row else None}")
    check_only_tables_changed(judge, initial_db, after_db, ("listings", "events"))


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
