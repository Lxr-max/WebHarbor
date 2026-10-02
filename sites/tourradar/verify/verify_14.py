#!/usr/bin/env python3
"""Deterministic verifier for TourRadar task TourRadar--14.

Apply TRAVEL50 to the cheapest Europe tour over $1,000, 1 traveler shared room, deposit; report reference + total after discount.

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

TASK_ID = "TourRadar--14"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_europe_listing",
                any("europe" in u.lower()
                    for u in trajectory_urls(traj)),
                "required: a Europe tours listing")
    judge.check("nav_tour_page", navigated_to(traj, "/t/46923"),
                "required: /t/46923 (Europe Taster, cheapest Europe tour > $1,000)")
    judge.check("nav_book_now", navigated_to(traj, "/book-now/46923"),
                "required: /book-now/46923")
    judge.check("nav_confirmation", navigated_booking_confirmation(traj),
                "required: /booking/TR-...")
    judge.check("answer_ref", bool(re.search(r"TR-4692301\d{4}", answer)),
                f"final={answer[:120]!r}")
    judge.check("answer_total_after_discount", contains_amount(answer, 1585.00),
                "expected US$1,585.00 total after the $50 TRAVEL50 discount")
    check_booking_row(judge, after_db, initial_db,
                      tour_id=46923, travelers=1, room_type="Double Room",
                      insurance="none", schedule="deposit", total=1585.00,
                      due_today=158.50, lead_email="promo@example.com",
                      departure_date="2027-03-28", promo_code="TRAVEL50")
    check_only_tables_changed(judge, initial_db, after_db,
                              allowed=("bookings", "users"))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
