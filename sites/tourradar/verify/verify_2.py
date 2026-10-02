#!/usr/bin/env python3
"""Deterministic verifier for TourRadar task TourRadar--2.

Alice: cancel the booking departing first, reopen Tour Management to confirm,
save the cancelled tour to her wishlist, and set profile nationality/phone.
Report the cancelled reference, the remaining trip's departure date, and the
wishlist count.

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

TASK_ID = "TourRadar--2"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_signed_in_as(judge, traj, "alice.j@test.com")
    judge.check("nav_account", navigated_to_path(traj, "/account"),
                "required: /account (Tour Management, opened at least twice: "
                "before and after the cancellation)")
    judge.check("nav_account_reopened",
                sum(1 for u in trajectory_urls(traj) if u.rstrip("/").endswith("/account")) >= 2,
                "the cancellation must be re-verified in Tour Management")
    judge.check("nav_booking_detail", navigated_to(traj, "/booking/TR-000010101"),
                "required: /booking/TR-000010101 (the booking departing first)")
    judge.check("nav_cancelled_tour_page", navigated_to(traj, "/t/22237"),
                "required: /t/22237 (the cancelled booking's tour page)")
    judge.check("nav_wishlists", navigated_to_path(traj, "/wishlists"),
                "required: /wishlists (her Saved adventures)")
    judge.check("answer_cancelled_ref", "TR-000010101" in answer,
                f"final={answer[:120]!r}")
    judge.check("answer_remaining_departure",
                contains_any(answer, ["October 15, 2026", "October 15,2026",
                                      "15 October 2026", "Oct 15, 2026"]),
                "expected remaining trip departure October 15, 2026")
    judge.check("answer_wishlist_count", contains_int(answer, 4),
                "expected 4 saved adventures after adding the cancelled tour "
                "(3 seeded + Thai Intro 9 Day)")
    # DB: first confirmed booking flipped to cancelled, the other untouched
    rows = db_query(after_db, "SELECT ref, status, departure_date FROM bookings "
                              "WHERE user_id=1 ORDER BY departure_date")
    by_ref = {r["ref"]: r for r in rows}
    judge.check("db_first_booking_cancelled",
                by_ref.get("TR-000010101", {}).get("status") == "cancelled",
                f"TR-000010101 status={by_ref.get('TR-000010101', {}).get('status')!r}")
    judge.check("db_second_booking_confirmed",
                by_ref.get("TR-000010102", {}).get("status") == "confirmed",
                f"TR-000010102 status={by_ref.get('TR-000010102', {}).get('status')!r}")
    judge.check("db_completed_untouched",
                by_ref.get("TR-000010103", {}).get("status") == "completed",
                f"TR-000010103 status={by_ref.get('TR-000010103', {}).get('status')!r}")
    # DB: the cancelled tour saved to alice's wishlist
    saved = wishlist_tour_ids(after_db, "alice.j@test.com")
    judge.check("db_wishlist_has_cancelled_tour", 22237 in saved,
                f"alice wishlist={saved!r}, expected to contain 22237")
    judge.check("db_wishlist_count", len(saved) == 4,
                f"wishlist count={len(saved)!r}, expected 4")
    # DB: profile updated
    alice_rows = db_query(after_db, "SELECT id, email, nationality, phone "
                                 "FROM users WHERE email=?",
                         ("alice.j@test.com",))
    alice = alice_rows[0] if alice_rows else None
    check_only_tables_changed(judge, initial_db, after_db,
                              allowed=("bookings", "wishlist_items"))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
