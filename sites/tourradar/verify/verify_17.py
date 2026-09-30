#!/usr/bin/env python3
"""Deterministic verifier for TourRadar task TourRadar--17.

Thailand 7-10 day group tour: cheapest, book 2 travelers shared with 7 installments; report reference + charged today.

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

TASK_ID = "TourRadar--17"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_thailand_listing",
                any("thailand" in u.lower()
                    for u in trajectory_urls(traj)),
                "required: a Thailand tours listing")
    judge.check("nav_tour_page", navigated_to(traj, "/t/185625"),
                "required: /t/185625 (Amazing Thailand In 9 Days)")
    judge.check("nav_book_now", navigated_to(traj, "/book-now/185625"),
                "required: /book-now/185625")
    judge.check("nav_confirmation", navigated_booking_confirmation(traj),
                "required: /booking/TR-...")
    judge.check("answer_ref", bool(re.search(r"TR-18562502\d{4}", answer)),
                f"final={answer[:120]!r}")
    judge.check("answer_charged_today", contains_amount(answer, 133.20),
                "expected US$133.20 charged today (10% of 2x US$666, installments)")
    check_booking_row(judge, after_db, initial_db,
                      tour_id=185625, travelers=2, room_type="Double Room",
                      insurance="none", schedule="installments", total=1332.00,
                      due_today=133.20, lead_email="thailand@example.com",
                      departure_date="2026-09-30")
    check_only_tables_changed(judge, initial_db, after_db,
                              allowed=("bookings", "users"))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
