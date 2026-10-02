#!/usr/bin/env python3
"""Deterministic verifier for TourRadar task TourRadar--3.

Bob: remove the Bali tour from saved adventures; wishlist the cheapest Vietnam tour; report name + per-person price.

Ground truth is HARDCODED below (frozen from the reviewer's independent
DOM-asserted walkthrough + SQLite reads; never present in tasks.jsonl).
Deterministic only — no LLM calls.
Input/Output: see verify_lib.parse_args / verify_lib.run_verifier.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_lib import (Judge, run_verifier, final_answer, navigated_to,
                        trajectory_urls,
                        navigated_to_path, navigated_booking_confirmation,
                        contains_all, contains_any, contains_amount,
                        contains_int, check_trajectory_identity, check_read_only,
                        check_only_tables_changed, check_signed_in_as,
                        check_booking_row, added_bookings, booking_travelers,
                        added_rows, removed_rows, db_query, wishlist_tour_ids,
                        tour_qa_for_tour, reviews_for_tour, user_by_email)

TASK_ID = "TourRadar--3"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_signed_in_as(judge, traj, "bob.c@test.com")
    judge.check("nav_wishlists", navigated_to_path(traj, "/wishlists"),
                "required: /wishlists (saved adventures)")
    judge.check("nav_vietnam_listing",
                any("vietnam" in u.lower()
                    for u in trajectory_urls(traj)),
                "required: a Vietnam tours listing")
    judge.check("nav_tour_page", navigated_to(traj, "/t/271536"),
                "required: /t/271536 (Astonishing Vietnam In 11 Days)")
    judge.check("answer_tour_name",
                contains_all(answer, ["Astonishing Vietnam"]),
                f"final={answer[:120]!r}")
    judge.check("answer_price", contains_amount(answer, 609),
                "expected US$609 per person")
    # DB: Bali Experience (93833) removed from bob's wishlist, 271536 saved
    before_ids = wishlist_tour_ids(initial_db, "bob.c@test.com")
    after_ids = wishlist_tour_ids(after_db, "bob.c@test.com")
    judge.check("db_bali_removed", 93833 not in after_ids,
                f"wishlist before={before_ids!r} after={after_ids!r}")
    judge.check("db_vietnam_saved", 271536 in after_ids,
                f"wishlist after={after_ids!r}")
    judge.check("db_no_other_wishlist_writes",
                len(after_ids) == len(before_ids),
                f"before={len(before_ids)} after={len(after_ids)}")
    check_only_tables_changed(judge, initial_db, after_db,
                              allowed=("wishlist_items",))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
