#!/usr/bin/env python3
"""Deterministic verifier for TourRadar task TourRadar--11.

Create an account (autumn@example.com), read the Japan guide (fall/autumn
text, the month with the most departing tours, budget tour count), open the
full Japan list sorted by most reviewed, open the top tour, save it to the
wishlist and report the saved count.

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
                        trajectory_urls, input_texts,
                        navigated_to_path, navigated_booking_confirmation,
                        contains_all, contains_any, contains_amount,
                        contains_int, check_trajectory_identity, check_read_only,
                        check_only_tables_changed, check_signed_in_as,
                        check_booking_row, added_bookings, booking_travelers,
                        added_rows, removed_rows, db_query, wishlist_tour_ids,
                        tour_qa_for_tour, reviews_for_tour, user_by_email)

TASK_ID = "TourRadar--11"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_signup", navigated_to_path(traj, "/signup"),
                "required: /signup (the account must be created on-site)")
    judge.check("entered_signup_identity",
                "autumn@example.com" in " ".join(input_texts(traj)).lower(),
                "expected autumn@example.com in the signup form inputs")
    judge.check("nav_japan_guide", navigated_to(traj, "/d/japan"),
                "required: /d/japan (the Japan destination guide)")
    judge.check("nav_japan_serp", navigated_to(traj, "/srp/d-japan"),
                "required: the full Japan tour list")
    judge.check("nav_top_tour", navigated_to(traj, "/t/111527"),
                "required: /t/111527 (Japan Classic 10 Day, the most-reviewed "
                "Japan tour)")
    judge.check("nav_wishlists", navigated_to_path(traj, "/wishlists"),
                "required: /wishlists (the account's Saved adventures)")
    judge.check("answer_autumn_text",
                contains_any(answer, ["maple leaves", "deep reds and golds",
                                      "September through November"]),
                "expected the guide's fall/autumn description")
    judge.check("answer_month", contains_all(answer, ["November"]),
                "expected November 2026 (526 tours — the most of the three months)")
    judge.check("answer_month_count", contains_int(answer, 526),
                "expected the guide's 526-tour count for November 2026")
    judge.check("answer_budget_tours", contains_int(answer, 35),
                "expected 35 budget tours listed by the guide")
    judge.check("answer_top_tour",
                contains_all(answer, ["Japan Classic 10 Day"]),
                "expected Japan Classic 10 Day - One Life Adventures as the "
                "most-reviewed Japan tour")
    judge.check("answer_top_rating", contains_all(answer, ["4.8"]),
                "expected the top tour's rating 4.8")
    judge.check("answer_top_departure",
                contains_any(answer, ["November 2, 2026", "2 November 2026",
                                      "Nov 2, 2026"]),
                "expected the top tour's first available departure November 2, 2026")
    judge.check("answer_saved_count", contains_int(answer, 1),
                "expected 1 saved adventure on the new account")
    # DB: the account exists and the wishlist row was written
    new_user = user_by_email(after_db, "autumn@example.com")
    judge.check("db_account_created", bool(new_user),
                "expected a users row for autumn@example.com")
    if new_user:
        saved = db_query(after_db,
                         "SELECT tour_id FROM wishlist_items WHERE user_id=?",
                         (new_user["id"],))
        judge.check("db_wishlist_row",
                    [r["tour_id"] for r in saved] == [111527],
                    f"expected wishlist=[111527], got {[r['tour_id'] for r in saved]!r}")
        check_only_tables_changed(judge, initial_db, after_db,
                                  allowed=("users", "wishlist_items"))
    else:
        judge.check("db_wishlist_row", False, "no account row to check")


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
