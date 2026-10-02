#!/usr/bin/env python3
"""Deterministic verifier for TourRadar task TourRadar--0.

Cheapest Japan tour under $2,500: book 2 travelers, shared room, 10% deposit. Report the booking reference and the amount charged today.

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

TASK_ID = "TourRadar--0"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_japan_tours",
                any("japan" in u.lower() for u in trajectory_urls(traj)),
                "required: a Japan tours listing (SERP or search)")
    judge.check("nav_tour_page", navigated_to(traj, "/t/244895"),
                "required: /t/244895 (8D Splendid Japan)")
    judge.check("nav_book_now", navigated_to(traj, "/book-now/244895"),
                "required: /book-now/244895")
    judge.check("nav_confirmation", navigated_booking_confirmation(traj),
                "required: /booking/TR-...")
    # answer: booking reference + amount charged today
    judge.check("answer_ref", bool(re.search(r"TR-24489502\d{4}", answer)),
                f"final={answer[:120]!r}")
    judge.check("answer_charged_today", contains_amount(answer, 359.80),
                "expected US$359.80 charged today (10% deposit of 2x US$1,799)")
    # DB: exactly one new booking row
    check_booking_row(judge, after_db, initial_db,
                      tour_id=244895, travelers=2, room_type="Double Room",
                      insurance="none", schedule="deposit", total=3598.00,
                      due_today=359.80, lead_email="spring@example.com",
                      departure_date="2027-03-06")
    check_only_tables_changed(judge, initial_db, after_db,
                              allowed=("bookings", "users"))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
